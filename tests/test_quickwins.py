"""
Pruebas funcionales de los quick wins:
- Retención/purga de métricas
- Checks agentless (HTTP/TCP/ICMP) configurables y ejecutados server-side
- Canales de notificación reales (Slack/Telegram/Discord/Webhook)

Las primitivas de red (requests/socket) se mockean: no hay salida real a Internet.
"""
import os
import sys
import uuid
from pathlib import Path
from datetime import datetime, timedelta

import pytest
from cryptography.fernet import Fernet
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

sys.path.append(str(Path(__file__).resolve().parent.parent))
os.environ["ENV"] = "testing"
os.environ.setdefault("ENCRYPTION_KEY", Fernet.generate_key().decode())

from src.server.app.main import app, engine, get_password_hash  # noqa: E402
from src.server.app.models import (  # noqa: E402
    Base, User, UserSession, Metric, MonitoringCheck, MonitoringCheckResult, NotificationChannel,
)
from src.server.app.security import decrypt_password  # noqa: E402
from src.server.app import maintenance  # noqa: E402
from src.server.app.monitoring import checks as mon_checks  # noqa: E402
from src.server.app.notifications import channels as notif_channels  # noqa: E402

client = TestClient(app)


@pytest.fixture(scope="module", autouse=True)
def setup_db():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    with Session(engine) as sess:
        sess.add(User(email="admin@example.com", password_hash=get_password_hash("admin"),
                      is_admin=True, must_change_password=False))
        sess.add(User(email="user@example.com", password_hash=get_password_hash("user"),
                      is_admin=False, must_change_password=False))
        sess.commit()
    yield


def _token(email):
    with Session(engine) as sess:
        u = sess.execute(select(User).where(User.email == email)).scalar_one()
        token = uuid.uuid4().hex
        sess.add(UserSession(token=token, user_id=u.id))
        sess.commit()
        return token


@pytest.fixture(scope="module")
def admin_headers():
    return {"X-Dashboard-Token": _token("admin@example.com")}


@pytest.fixture(scope="module")
def user_headers():
    return {"X-Dashboard-Token": _token("user@example.com")}


class FakeResp:
    def __init__(self, status=200):
        self.status_code = status


# --- Retención ---

def test_purge_old_metrics():
    with Session(engine) as sess:
        old = Metric(server_id="s1")
        old.ts = datetime.utcnow() - timedelta(days=40)
        recent = Metric(server_id="s1")
        recent.ts = datetime.utcnow() - timedelta(days=1)
        sess.add_all([old, recent])
        sess.commit()
    deleted = maintenance.purge_old_data(metrics_days=30, checks_days=30)
    assert deleted["metrics"] >= 1
    with Session(engine) as sess:
        remaining = sess.execute(select(Metric).where(Metric.server_id == "s1")).scalars().all()
        assert all((datetime.utcnow() - (m.ts.replace(tzinfo=None) if m.ts.tzinfo else m.ts)).days < 30 for m in remaining)


def test_purge_endpoint_admin_only(admin_headers, user_headers):
    assert client.post("/api/admin/maintenance/purge").status_code == 401
    assert client.post("/api/admin/maintenance/purge", headers=user_headers).status_code == 403
    r = client.post("/api/admin/maintenance/purge", headers=admin_headers)
    assert r.status_code == 200 and "deleted" in r.json()


# --- Checks agentless ---

def test_http_check_executor(monkeypatch):
    monkeypatch.setattr(mon_checks.requests, "get", lambda *a, **k: FakeResp(200))
    res = mon_checks.run_http_check("http://example.com", 5)
    assert res["status"] == "up" and "HTTP 200" in res["message"]
    monkeypatch.setattr(mon_checks.requests, "get", lambda *a, **k: FakeResp(503))
    assert mon_checks.run_http_check("http://example.com", 5)["status"] == "down"


def test_tcp_check_executor(monkeypatch):
    class FakeConn:
        def __enter__(self): return self
        def __exit__(self, *a): return False
    monkeypatch.setattr(mon_checks.socket, "create_connection", lambda *a, **k: FakeConn())
    res = mon_checks.run_tcp_check("10.0.0.1", 22, 5)
    assert res["status"] == "up"


def test_check_crud_and_run(admin_headers, user_headers, monkeypatch):
    # No admin no puede crear
    payload = {"name": "web", "check_type": "http", "target": "http://example.com", "expected_status": 200}
    assert client.post("/api/monitoring/checks", json=payload, headers=user_headers).status_code == 403

    r = client.post("/api/monitoring/checks", json=payload, headers=admin_headers)
    assert r.status_code == 200, r.text
    check_id = r.json()["id"]

    # Ejecutar (mock del ejecutor) y verificar que se guarda resultado + estado
    monkeypatch.setattr(mon_checks, "run_check", lambda c: {"status": "up", "latency_ms": 12.5, "message": "HTTP 200"})
    r = client.post(f"/api/monitoring/checks/{check_id}/run", headers=admin_headers)
    assert r.status_code == 200 and r.json()["result"]["status"] == "up"

    r = client.get(f"/api/monitoring/checks/{check_id}/results", headers=admin_headers)
    assert r.status_code == 200 and len(r.json()) >= 1 and r.json()[0]["status"] == "up"

    # last_status denormalizado actualizado
    r = client.get("/api/monitoring/checks", headers=admin_headers)
    c = next(c for c in r.json() if c["id"] == check_id)
    assert c["last_status"] == "up" and c["last_latency_ms"] == 12.5

    client.delete(f"/api/monitoring/checks/{check_id}", headers=admin_headers)


def test_run_all_due_checks(monkeypatch):
    with Session(engine) as sess:
        sess.add(MonitoringCheck(name="due", check_type="icmp", target="1.1.1.1",
                                 interval_seconds=60, enabled=True))
        sess.commit()
    monkeypatch.setattr(mon_checks, "run_check", lambda c: {"status": "up", "latency_ms": 1.0, "message": "ok"})
    ran = mon_checks.run_all_due_checks()
    assert ran >= 1


# --- Canales de notificación ---

def test_channel_create_hides_secret(admin_headers):
    payload = {"name": "ops-slack", "channel_type": "slack", "target": "https://hooks.slack.com/SECRET"}
    r = client.post("/api/admin/notification-channels", json=payload, headers=admin_headers)
    assert r.status_code == 200, r.text
    data = r.json()
    assert "target" not in data and "target_encrypted" not in data
    # El secreto se guardó cifrado y es recuperable
    with Session(engine) as sess:
        ch = sess.get(NotificationChannel, data["id"])
        assert decrypt_password(ch.target_encrypted) == "https://hooks.slack.com/SECRET"


def test_channel_send_and_dispatch(monkeypatch):
    calls = []
    monkeypatch.setattr(notif_channels.requests, "post",
                        lambda url, **k: (calls.append((url, k)), FakeResp(200))[1])
    with Session(engine) as sess:
        from src.server.app.security import encrypt_password
        sess.add(NotificationChannel(name="dc", channel_type="discord",
                                     target_encrypted=encrypt_password("https://discord.com/api/webhooks/x"),
                                     enabled=True))
        sess.commit()
    sent = notif_channels.dispatch_alert("ALERTA", "CPU alta")
    assert sent >= 1
    # Discord usa 'content'
    assert any("discord.com" in url for url, _ in calls)
    assert any(k.get("json", {}).get("content") for _, k in calls)


def test_telegram_requires_chat_id():
    ch = NotificationChannel(name="tg", channel_type="telegram",
                             target_encrypted=None, extra=None)
    # send sin chat_id -> error controlado (sin lanzar)
    ok, detail = notif_channels._send_telegram("bottoken", "msg", None)
    assert ok is False and "chat_id" in detail

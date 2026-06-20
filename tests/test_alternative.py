"""
Pruebas de los incrementos "alternativa a Proxmox + Zabbix":

  - Fase 1: validación/seguridad de checks agentless y canales (anti-inyección, URLs).
  - Fase 2: ciclo de vida (power) de guests Proxmox por SSH (mockeado).
  - Fase 3: auto-descubrimiento de red (primitivas de sondeo mockeadas).
  - Fase 4: inventario unificado (agente + agentless + Proxmox).

La capa SSH y las primitivas de red se mockean: no hay infraestructura real en CI.
"""
import os
import sys
import uuid
from pathlib import Path

import pytest
from cryptography.fernet import Fernet
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

sys.path.append(str(Path(__file__).resolve().parent.parent))

os.environ["ENV"] = "testing"
os.environ.setdefault("ENCRYPTION_KEY", Fernet.generate_key().decode())

from src.server.app.main import app, engine, get_password_hash  # noqa: E402
from src.server.app import main as main_module  # noqa: E402
from src.server.app.models import (  # noqa: E402
    Base, User, UserSession, ProxmoxNode, ProxmoxGuest, MonitoringCheck, Server, Metric,
)
from src.server.app.security import encrypt_password  # noqa: E402
from src.server.app.proxmox import ssh_executor  # noqa: E402
from src.server.app.monitoring import checks as mon_checks, discovery as mon_discovery  # noqa: E402

client = TestClient(app)


class FakeSSH:
    def __init__(self):
        self.calls = []
        self.responses = []
        self.default = (0, "ok", "")

    def __call__(self, node, args, timeout=60):
        self.calls.append((list(args), timeout))
        if self.responses:
            return self.responses.pop(0)
        return self.default


@pytest.fixture(autouse=True)
def fake_ssh(monkeypatch):
    f = FakeSSH()
    monkeypatch.setattr(ssh_executor, "run_command", f)
    return f


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


def _token_for(email: str) -> str:
    with Session(engine) as sess:
        u = sess.execute(select(User).where(User.email == email)).scalar_one()
        token = uuid.uuid4().hex
        sess.add(UserSession(token=token, user_id=u.id))
        sess.commit()
        return token


@pytest.fixture(scope="module")
def admin_headers():
    return {"X-Dashboard-Token": _token_for("admin@example.com")}


@pytest.fixture(scope="module")
def user_headers():
    return {"X-Dashboard-Token": _token_for("user@example.com")}


def _make_node(name="pve1", hostname="10.0.0.1"):
    with Session(engine) as sess:
        node = ProxmoxNode(name=name, hostname=hostname, ssh_user="root",
                            auth_type="password", secret_encrypted=encrypt_password("secret"))
        sess.add(node)
        sess.commit()
        sess.refresh(node)
        return node.id


def _make_guest(node_id, vmid=100, guest_type="qemu", name="vm"):
    with Session(engine) as sess:
        g = ProxmoxGuest(node_id=node_id, vmid=vmid, guest_type=guest_type, name=name)
        sess.add(g)
        sess.commit()
        sess.refresh(g)
        return g.id


# ====================== FASE 1: seguridad de checks =========================

def test_icmp_check_rejects_argument_injection(admin_headers):
    for bad in ["-f", "-O 127.0.0.1", "- -c 100"]:
        r = client.post("/api/monitoring/checks",
                        json={"name": "x", "check_type": "icmp", "target": bad},
                        headers=admin_headers)
        assert r.status_code == 422, f"esperaba 422 para {bad!r}: {r.text}"


def test_tcp_check_requires_port(admin_headers):
    r = client.post("/api/monitoring/checks",
                    json={"name": "x", "check_type": "tcp", "target": "10.0.0.5"},
                    headers=admin_headers)
    assert r.status_code == 422


def test_http_check_requires_url(admin_headers):
    r = client.post("/api/monitoring/checks",
                    json={"name": "x", "check_type": "http", "target": "not-a-url"},
                    headers=admin_headers)
    assert r.status_code == 422


def test_valid_checks_accepted(admin_headers):
    ok = [
        {"name": "icmp-ok", "check_type": "icmp", "target": "8.8.8.8"},
        {"name": "http-ok", "check_type": "http", "target": "https://example.com/health"},
        {"name": "tcp-ok", "check_type": "tcp", "target": "10.0.0.9", "port": 5432},
    ]
    for payload in ok:
        r = client.post("/api/monitoring/checks", json=payload, headers=admin_headers)
        assert r.status_code == 200, r.text


def test_update_check_revalidates_target(admin_headers):
    r = client.post("/api/monitoring/checks",
                    json={"name": "upd", "check_type": "icmp", "target": "1.1.1.1"},
                    headers=admin_headers)
    cid = r.json()["id"]
    r = client.put(f"/api/monitoring/checks/{cid}",
                   json={"target": "-f"}, headers=admin_headers)
    assert r.status_code == 422


def test_icmp_executor_defense_in_depth():
    # Defensa en profundidad: aunque se cuele un host con '-', no se ejecuta ping.
    assert mon_checks.run_icmp_check("-f")["status"] == "unknown"
    assert mon_checks.run_icmp_check("")["status"] == "unknown"


def test_notification_channel_url_validation(admin_headers):
    # slack/discord/webhook exigen https
    r = client.post("/api/admin/notification-channels",
                    json={"name": "s", "channel_type": "slack", "target": "http://insecure"},
                    headers=admin_headers)
    assert r.status_code == 422
    # telegram exige token con forma <id>:<secreto>
    r = client.post("/api/admin/notification-channels",
                    json={"name": "t", "channel_type": "telegram", "target": "no-token", "extra": "1"},
                    headers=admin_headers)
    assert r.status_code == 422
    # válido
    r = client.post("/api/admin/notification-channels",
                    json={"name": "w", "channel_type": "webhook",
                          "target": "https://hooks.example.com/abc"},
                    headers=admin_headers)
    assert r.status_code == 200, r.text


# ====================== FASE 2: power lifecycle Proxmox =====================

def test_power_start_builds_command(admin_headers, fake_ssh):
    node_id = _make_node("pwr1", "10.1.0.1")
    guest_id = _make_guest(node_id, vmid=300, guest_type="qemu")
    r = client.post(f"/api/proxmox/guests/{guest_id}/power",
                    json={"action": "start"}, headers=admin_headers)
    assert r.status_code == 200, r.text
    assert fake_ssh.calls[-1][0] == ["qm", "start", "300"]


def test_power_reboot_lxc(admin_headers, fake_ssh):
    node_id = _make_node("pwr2", "10.1.0.2")
    guest_id = _make_guest(node_id, vmid=301, guest_type="lxc")
    r = client.post(f"/api/proxmox/guests/{guest_id}/power",
                    json={"action": "reboot"}, headers=admin_headers)
    assert r.status_code == 200, r.text
    assert fake_ssh.calls[-1][0] == ["pct", "reboot", "301"]


def test_power_invalid_action_rejected(admin_headers, fake_ssh):
    node_id = _make_node("pwr3", "10.1.0.3")
    guest_id = _make_guest(node_id, vmid=302)
    before = len(fake_ssh.calls)
    r = client.post(f"/api/proxmox/guests/{guest_id}/power",
                    json={"action": "destroy; rm -rf /"}, headers=admin_headers)
    assert r.status_code == 422
    assert len(fake_ssh.calls) == before


def test_power_requires_admin(user_headers):
    assert client.post("/api/proxmox/guests/1/power",
                       json={"action": "start"}, headers=user_headers).status_code == 403


def test_guest_status_parses_output(admin_headers, fake_ssh):
    node_id = _make_node("pwr4", "10.1.0.4")
    guest_id = _make_guest(node_id, vmid=303)
    fake_ssh.responses = [(0, "status: running\n", "")]
    r = client.get(f"/api/proxmox/guests/{guest_id}/status", headers=admin_headers)
    assert r.status_code == 200, r.text
    assert r.json()["status"] == "running"


# ====================== FASE 3: auto-descubrimiento =========================

def test_discovery_invalid_cidr(admin_headers):
    r = client.post("/api/discovery/scan", json={"cidr": "not-a-cidr"}, headers=admin_headers)
    assert r.status_code == 422


def test_discovery_range_too_large(admin_headers):
    r = client.post("/api/discovery/scan", json={"cidr": "10.0.0.0/16"}, headers=admin_headers)
    assert r.status_code == 422


def test_discovery_finds_hosts_and_auto_creates(admin_headers, monkeypatch):
    # Solo .0.0.5 tiene el 22 abierto; el resto cerrado.
    def fake_tcp(host, port, timeout):
        return host == "192.168.50.5" and int(port) == 22
    monkeypatch.setattr(mon_discovery, "_probe_tcp", fake_tcp)
    monkeypatch.setattr(mon_discovery, "_probe_icmp", lambda host, timeout: False)

    r = client.post("/api/discovery/scan",
                    json={"cidr": "192.168.50.0/29", "ports": [22], "use_icmp": False,
                          "auto_create": True},
                    headers=admin_headers)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["found"] == 1
    assert body["hosts"][0]["host"] == "192.168.50.5"
    assert body["created_checks"] == 1
    # El check agentless quedó persistido.
    with Session(engine) as sess:
        created = sess.execute(
            select(MonitoringCheck).where(MonitoringCheck.target == "192.168.50.5")
        ).scalar_one()
        assert created.check_type == "tcp" and created.port == 22


def test_discovery_requires_admin(user_headers):
    assert client.post("/api/discovery/scan", json={"cidr": "10.0.0.0/30"},
                       headers=user_headers).status_code == 403


# ====================== FASE 4: inventario unificado ========================

def test_inventory_aggregates_all_sources(admin_headers):
    with Session(engine) as sess:
        sess.add(Server(server_id="inv-srv", token="t", group_name="prod"))
        sess.add(Metric(server_id="inv-srv", cpu_total=10.0))
        sess.commit()
    node_id = _make_node("inv-node", "10.2.0.1")
    _make_guest(node_id, vmid=400, guest_type="qemu", name="inv-vm")
    client.post("/api/monitoring/checks",
                json={"name": "inv-check", "check_type": "icmp", "target": "9.9.9.9"},
                headers=admin_headers)

    r = client.get("/api/inventory", headers=admin_headers)
    assert r.status_code == 200, r.text
    sources = {i["source"] for i in r.json()}
    assert {"agent", "agentless", "proxmox"}.issubset(sources)
    agent_item = next(i for i in r.json() if i["identifier"] == "inv-srv")
    assert agent_item["status"] == "online"  # métrica recién insertada


def test_inventory_requires_auth():
    assert client.get("/api/inventory").status_code == 401

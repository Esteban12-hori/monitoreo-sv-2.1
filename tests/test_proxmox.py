"""
Pruebas funcionales de la gestión Proxmox.

La capa SSH (`ssh_executor.run_command`) y la huella de host se mockean: no hay
un Proxmox real en CI. Se valida construcción de comandos, prevención de
inyección, autorización, snapshots, backups, autodetección de BD y migración por
el túnel WireGuard.
"""
import os
import sys
import json
from pathlib import Path

import pytest
from cryptography.fernet import Fernet
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

sys.path.append(str(Path(__file__).resolve().parent.parent))

# Entorno de pruebas + clave de cifrado determinista ANTES de importar la app.
os.environ["ENV"] = "testing"
os.environ.setdefault("ENCRYPTION_KEY", Fernet.generate_key().decode())

from src.server.app.main import app, engine, get_password_hash, get_host_fingerprint  # noqa: E402
from src.server.app import main as main_module  # noqa: E402
from src.server.app.models import (  # noqa: E402
    Base, User, UserSession, ProxmoxNode, ProxmoxGuest, BackupSchedule, BackupJob, NodeLink, Metric, Server,
)
from src.server.app.security import encrypt_password, decrypt_password  # noqa: E402
from src.server.app.proxmox import ssh_executor, dbdetect, scheduler  # noqa: E402

client = TestClient(app)


# --- Mock de ejecución SSH -------------------------------------------------

class FakeSSH:
    """Captura llamadas a run_command y devuelve respuestas programadas."""
    def __init__(self):
        self.calls = []          # lista de (args, timeout)
        self.responses = []      # cola de (rc, out, err)
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
    # Evitar SSH real al registrar la huella de host del nodo.
    monkeypatch.setattr(main_module, "get_host_fingerprint", lambda node: "SHA256:test")
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
    """Crea una sesión directamente en DB para evitar el rate-limit del login."""
    import uuid
    with Session(engine) as sess:
        u = sess.execute(select_user(email)).scalar_one()
        token = uuid.uuid4().hex
        sess.add(UserSession(token=token, user_id=u.id))
        sess.commit()
        return token


def select_user(email):
    from sqlalchemy import select
    return select(User).where(User.email == email)


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


def _make_guest(node_id, vmid=100, guest_type="qemu", name="db-server", linked=None, is_db=False):
    with Session(engine) as sess:
        g = ProxmoxGuest(node_id=node_id, vmid=vmid, guest_type=guest_type, name=name,
                         linked_server_id=linked, is_db=is_db)
        sess.add(g)
        sess.commit()
        sess.refresh(g)
        return g.id


# --- Autorización -----------------------------------------------------------

def test_requires_auth():
    assert client.get("/api/proxmox/nodes").status_code == 401


def test_requires_admin(user_headers):
    assert client.get("/api/proxmox/nodes", headers=user_headers).status_code == 403


# --- Nodos ------------------------------------------------------------------

def test_create_node_hides_secret(admin_headers):
    payload = {"name": "node-a", "hostname": "10.1.1.1", "ssh_user": "root",
               "auth_type": "password", "secret": "supersecret"}
    r = client.post("/api/proxmox/nodes", json=payload, headers=admin_headers)
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["name"] == "node-a"
    # El secreto nunca se devuelve
    assert "secret" not in data and "secret_encrypted" not in data
    assert data["host_key_fingerprint"] == "SHA256:test"


# --- 1. Recursos ------------------------------------------------------------

def test_update_resources_builds_correct_command(admin_headers, fake_ssh):
    node_id = _make_node("res-node", "10.2.2.2")
    guest_id = _make_guest(node_id, vmid=101, guest_type="qemu")
    r = client.put(f"/api/proxmox/guests/{guest_id}/resources",
                   json={"cores": 4, "memory": 2048}, headers=admin_headers)
    assert r.status_code == 200, r.text
    args = fake_ssh.calls[-1][0]
    assert args == ["qm", "set", "101", "--cores", "4", "--memory", "2048"]


def test_resources_out_of_range_rejected(admin_headers, fake_ssh):
    node_id = _make_node("res-node2", "10.2.2.3")
    guest_id = _make_guest(node_id, vmid=102)
    before = len(fake_ssh.calls)
    r = client.put(f"/api/proxmox/guests/{guest_id}/resources",
                   json={"cores": 99999}, headers=admin_headers)
    assert r.status_code == 422
    # No se construyó ningún comando
    assert len(fake_ssh.calls) == before


# --- 3. Snapshots + inyección ----------------------------------------------

def test_snapshot_injection_rejected(admin_headers, fake_ssh):
    node_id = _make_node("snap-node", "10.3.3.3")
    guest_id = _make_guest(node_id, vmid=103)
    before = len(fake_ssh.calls)
    for bad in ["x; rm -rf /", "$(reboot)", "a`id`", "a b"]:
        r = client.post(f"/api/proxmox/guests/{guest_id}/snapshots",
                        json={"name": bad}, headers=admin_headers)
        assert r.status_code == 422, f"esperaba 422 para {bad!r}"
    assert len(fake_ssh.calls) == before  # nunca se ejecutó nada


def test_snapshot_create_and_list(admin_headers, fake_ssh):
    node_id = _make_node("snap-node2", "10.3.3.4")
    guest_id = _make_guest(node_id, vmid=104)
    r = client.post(f"/api/proxmox/guests/{guest_id}/snapshots",
                    json={"name": "pre-update"}, headers=admin_headers)
    assert r.status_code == 200, r.text
    assert fake_ssh.calls[-1][0] == ["qm", "snapshot", "104", "pre-update"]

    fake_ssh.responses = [(0, "`-> pre-update 2024-01-01 backup\ncurrent", "")]
    r = client.get(f"/api/proxmox/guests/{guest_id}/snapshots", headers=admin_headers)
    assert r.status_code == 200
    names = [s["name"] for s in r.json()]
    assert "pre-update" in names and "current" not in names


def test_snapshot_rollback_and_delete(admin_headers, fake_ssh):
    node_id = _make_node("snap-node3", "10.3.3.5")
    guest_id = _make_guest(node_id, vmid=105, guest_type="lxc")
    r = client.post(f"/api/proxmox/guests/{guest_id}/snapshots/snap1/rollback", headers=admin_headers)
    assert r.status_code == 200
    assert fake_ssh.calls[-1][0] == ["pct", "rollback", "105", "snap1"]
    r = client.delete(f"/api/proxmox/guests/{guest_id}/snapshots/snap1", headers=admin_headers)
    assert r.status_code == 200
    assert fake_ssh.calls[-1][0] == ["pct", "delsnapshot", "105", "snap1"]


# --- 2. Backups + autodetección de BD --------------------------------------

def test_manual_backup_run(admin_headers, fake_ssh):
    node_id = _make_node("bk-node", "10.4.4.4")
    fake_ssh.responses = [(0, "INFO: Backup finished", "")]
    r = client.post("/api/proxmox/backups/run",
                    json={"node_id": node_id, "vmid": 110, "storage": "local"}, headers=admin_headers)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["status"] == "ok"
    assert fake_ssh.calls[-1][0] == ["vzdump", "110", "--storage", "local", "--mode", "snapshot"]


def test_backup_schedule_crud(admin_headers):
    node_id = _make_node("sched-api-node", "10.4.4.5")
    r = client.post("/api/proxmox/backup-schedules",
                    json={"name": "diario", "node_id": node_id, "cron_expr": "0 2 * * *",
                          "storage": "local", "only_db": True}, headers=admin_headers)
    assert r.status_code == 200, r.text
    sched = r.json()
    assert sched["name"] == "diario" and sched["cron_expr"] == "0 2 * * *"
    r = client.get("/api/proxmox/backup-schedules", headers=admin_headers)
    assert r.status_code == 200
    assert any(s["id"] == sched["id"] for s in r.json())
    r = client.delete(f"/api/proxmox/backup-schedules/{sched['id']}", headers=admin_headers)
    assert r.status_code == 200


def test_dbdetect_marks_db_guest():
    node_id = _make_node("det-node", "10.5.5.5")
    with Session(engine) as sess:
        sess.add(Server(server_id="srv-db", token="t"))
        sess.add(Metric(server_id="srv-db", services=json.dumps([{"port": 5432, "name": "postgres"}]),
                        processes="[]"))
        sess.commit()
        assert dbdetect.server_runs_db(sess, "srv-db") is True
    guest_id = _make_guest(node_id, vmid=120, name="srv-db", linked="srv-db")
    with Session(engine) as sess:
        dbdetect.detect_db_guests(sess)
        g = sess.get(ProxmoxGuest, guest_id)
        assert g.is_db is True


def test_scheduled_backup_only_db(fake_ssh):
    node_id = _make_node("sch-node", "10.6.6.6")
    with Session(engine) as sess:
        # Servidor con BD y otro sin BD
        sess.add(Server(server_id="srv-pg", token="t1"))
        sess.add(Metric(server_id="srv-pg", services=json.dumps([{"port": 5432, "name": "postgres"}]), processes="[]"))
        sess.add(Server(server_id="srv-web", token="t2"))
        sess.add(Metric(server_id="srv-web", services=json.dumps([{"port": 80, "name": "nginx"}]), processes="[]"))
        sess.commit()
    db_guest = _make_guest(node_id, vmid=201, name="srv-pg", linked="srv-pg")
    _make_guest(node_id, vmid=202, name="srv-web", linked="srv-web")

    with Session(engine) as sess:
        sched = BackupSchedule(name="nightly", node_id=node_id, cron_expr="0 3 * * *",
                               storage="local", only_db=True, enabled=True)
        sess.add(sched)
        sess.commit()
        sched_id = sched.id

    fake_ssh.default = (0, "INFO ok", "")
    count = scheduler.run_backup_schedule(sched_id)
    assert count == 1  # solo el guest de BD
    with Session(engine) as sess:
        jobs = sess.query(BackupJob).filter(BackupJob.vmid == 201).all()
        assert jobs and jobs[-1].status == "ok"
        assert sess.query(BackupJob).filter(BackupJob.vmid == 202).count() == 0


# --- 4. Túnel WireGuard + migración ----------------------------------------

def test_create_link_encrypts_keys(admin_headers, fake_ssh):
    src = _make_node("wg-src", "10.7.7.1")
    dst = _make_node("wg-dst", "10.7.7.2")
    fake_ssh.default = (0, "wg up", "")
    r = client.post("/api/proxmox/links",
                    json={"source_node_id": src, "target_node_id": dst}, headers=admin_headers)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["status"] == "up"
    # La respuesta no expone claves privadas
    assert "source_wg_privkey_encrypted" not in body
    assert body["source_wg_pubkey"] and body["target_wg_pubkey"]
    with Session(engine) as sess:
        link = sess.get(NodeLink, body["id"])
        # Las privadas están cifradas y son recuperables como clave WireGuard base64
        assert link.source_wg_privkey_encrypted and "PrivateKey" not in link.source_wg_privkey_encrypted
        priv = decrypt_password(link.source_wg_privkey_encrypted)
        import base64
        assert len(base64.b64decode(priv)) == 32


def test_migration_uses_tunnel(admin_headers, fake_ssh):
    src = _make_node("mig-src", "10.8.8.1")
    dst = _make_node("mig-dst", "10.8.8.2")
    with Session(engine) as sess:
        link = NodeLink(source_node_id=src, target_node_id=dst, status="up",
                        source_tunnel_ip="10.99.99.1", target_tunnel_ip="10.99.99.2")
        sess.add(link)
        sess.commit()
        link_id = link.id

    fake_ssh.responses = [
        (0, "INFO: creating vzdump archive '/var/lib/vz/dump/vzdump-qemu-100-2024.vma.zst'", ""),
        (0, "sent 1 bytes", ""),   # rsync por el túnel
        (0, "restore ok", ""),     # qmrestore en destino
    ]
    r = client.post("/api/proxmox/migrate",
                    json={"link_id": link_id, "vmid": 100, "guest_type": "qemu", "storage": "local"},
                    headers=admin_headers)
    assert r.status_code == 200, r.text
    # La transferencia (segunda llamada) usa la IP del túnel WireGuard del destino
    transfer_cmd = " ".join(fake_ssh.calls[-2][0])
    assert "10.99.99.2" in transfer_cmd and "rsync" in transfer_cmd
    # El restore se ejecuta en destino
    assert fake_ssh.calls[-1][0][0] in ("qmrestore", "pct")

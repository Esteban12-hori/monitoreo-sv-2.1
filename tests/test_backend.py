import os
import pytest
import sys
from pathlib import Path
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from sqlalchemy import create_engine, text

# Add root directory to sys.path to allow importing src
sys.path.append(str(Path(__file__).resolve().parent.parent))

# Set environment to testing before importing app
os.environ["ENV"] = "testing"

from src.server.app.main import app, engine, get_password_hash
from src.server.app.models import Base, User

client = TestClient(app)

@pytest.fixture(scope="module", autouse=True)
def setup_db():
    # Reset DB
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    
    # Create admin user
    with Session(engine) as sess:
        user = User(
            email="admin@example.com",
            password_hash=get_password_hash("admin"),
            is_admin=True,
            must_change_password=False
        )
        sess.add(user)
        sess.commit()
    
    yield
    
    # Cleanup (optional)
    # Base.metadata.drop_all(bind=engine)

def test_health():
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"ok": True}

def test_login():
    response = client.post("/api/login", json={"email": "admin@example.com", "password": "admin"})
    assert response.status_code == 200
    data = response.json()
    assert "token" in data
    return data["token"]

def test_smtp_config_access_denied_without_auth():
    response = client.get("/api/admin/smtp/config")
    assert response.status_code == 401 # Unauthorized

def test_smtp_config_flow():
    # Login
    token = test_login()
    headers = {"X-Dashboard-Token": token}
    
    # Get Config (should be 404 initially or empty)
    response = client.get("/api/admin/smtp/config", headers=headers)
    # Depending on implementation, might be 404
    assert response.status_code in [200, 404]
    
    # Set Config
    payload = {
        "host": "smtp.test.com",
        "port": 587,
        "username": "testuser",
        "password": "testpassword",
        "sender_email": "test@test.com",
        "use_tls": True
    }
    response = client.post("/api/admin/smtp/config", json=payload, headers=headers)
    assert response.status_code == 200
    
    # Get Config again
    response = client.get("/api/admin/smtp/config", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["host"] == "smtp.test.com"
    assert data["username"] == "testuser"
    # Password should not be returned in clear text usually, or schema might mask it? 
    # Schema SMTPConfigResponse doesn't have password field!
    assert "password" not in data

def test_user_management_flow():
    # Login as admin
    token = test_login()
    headers = {"X-Dashboard-Token": token}
    
    # Create User
    new_user_email = "user@example.com"
    payload = {
        "email": new_user_email,
        "password": "user123",
        "name": "Test User",
        "is_admin": False,
        "receive_alerts": True
    }
    response = client.post("/api/admin/users", json=payload, headers=headers)
    assert response.status_code == 200
    user_data = response.json()
    assert user_data["email"] == new_user_email
    user_id = user_data["id"]
    
    # List Users
    response = client.get("/api/admin/users", headers=headers)
    assert response.status_code == 200
    users = response.json()
    assert len(users) >= 2 # Admin + New User
    
    # Update User
    update_payload = {"name": "Updated Name", "is_admin": True}
    response = client.put(f"/api/admin/users/{user_id}", json=update_payload, headers=headers)
    assert response.status_code == 200
    updated_user = response.json()
    assert updated_user["name"] == "Updated Name"
    assert updated_user["is_admin"] is True
    
    # Delete User
    response = client.delete(f"/api/admin/users/{user_id}", headers=headers)
    assert response.status_code == 200
    
    # Verify Deletion
    response = client.get("/api/admin/users", headers=headers)
    users = response.json()
    assert not any(u["id"] == user_id for u in users)


def test_change_password_flow():
    admin_token = test_login()
    admin_headers = {"X-Dashboard-Token": admin_token}

    new_user_email = "changepw@example.com"
    create_payload = {
        "email": new_user_email,
        "password": "Initial123",
        "name": "Change Pw User",
        "is_admin": False,
        "receive_alerts": True
    }
    response = client.post("/api/admin/users", json=create_payload, headers=admin_headers)
    assert response.status_code == 200

    response = client.post("/api/login", json={"email": new_user_email, "password": "Initial123"})
    assert response.status_code == 200
    data = response.json()
    user_token = data["token"]
    assert data["must_change_password"] is True

    user_headers = {"X-Dashboard-Token": user_token}
    change_payload = {
        "current_password": "Initial123",
        "new_password": "NewPassword123"
    }
    response = client.post("/api/users/change-password", json=change_payload, headers=user_headers)
    assert response.status_code == 200

    response = client.post("/api/login", json={"email": new_user_email, "password": "Initial123"})
    assert response.status_code in [401, 429]

    response = client.post("/api/login", json={"email": new_user_email, "password": "NewPassword123"})
    assert response.status_code in [200, 429]
    if response.status_code == 200:
        data = response.json()
        assert data["must_change_password"] is False

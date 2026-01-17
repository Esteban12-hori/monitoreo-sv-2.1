import sys
import os
import requests
import json
import time

# Add project root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))

from src.server.app.database import SessionLocal
from src.server.app.models import Server

def get_or_create_server():
    db = SessionLocal()
    server_id = "test-server-processes"
    token = "test-token-123"
    
    srv = db.query(Server).filter(Server.server_id == server_id).first()
    if not srv:
        srv = Server(server_id=server_id, token=token)
        db.add(srv)
        db.commit()
        print(f"Created server {server_id}")
    else:
        srv.token = token
        db.commit()
        print(f"Using existing server {server_id}")
    
    db.close()
    return server_id, token

def send_metrics(server_id, token):
    url = "http://localhost:8000/api/metrics"
    payload = {
        "server_id": server_id,
        "memory": {
            "total": 16000,
            "used": 8000,
            "free": 8000,
            "cache": 2000
        },
        "cpu": {
            "total": 15.5,
            "per_core": [10.0, 20.0, 15.0, 17.0]
        },
        "disk": {
            "total": 500,
            "used": 250,
            "free": 250,
            "percent": 50.0
        },
        "docker": {
            "running_containers": 1,
            "containers": [{"name": "test-container", "image": "nginx", "status": "running"}]
        },
        "services": [
            {"port": 80, "name": "http", "proto": "tcp"}
        ],
        "processes": [
            {
                "pid": 1234,
                "name": "python.exe",
                "username": "user",
                "cpu_percent": 5.5,
                "memory_percent": 1.2,
                "status": "running"
            },
            {
                "pid": 5678,
                "name": "chrome.exe",
                "username": "user",
                "cpu_percent": 2.1,
                "memory_percent": 4.5,
                "status": "running"
            }
        ]
    }
    
    headers = {"X-Auth-Token": token}
    try:
        resp = requests.post(url, json=payload, headers=headers)
        print(f"Status: {resp.status_code}")
        print(f"Response: {resp.text}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    sid, tok = get_or_create_server()
    send_metrics(sid, tok)

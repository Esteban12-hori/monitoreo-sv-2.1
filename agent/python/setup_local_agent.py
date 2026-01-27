import requests
import json
import uuid
import platform

SERVER_URL = "http://localhost:8000"
CONFIG_PATH = "agent.config.json"

def register_local():
    server_id = "local-dev-agent"
    token = "local-dev-token-123"

    print(f"Registering {server_id} to {SERVER_URL}...")
    try:
        resp = requests.post(f"{SERVER_URL}/api/register", json={
            "server_id": server_id,
            "token": token
        })
        if resp.status_code == 200:
            print("✅ Registered successfully.")
        else:
            print(f"⚠️ Registration response: {resp.status_code} - {resp.text}")
            # Continue anyway, maybe it's already registered or we can just use the config
    except Exception as e:
        print(f"❌ Connection error: {e}")
        return

    config = {
        "server": SERVER_URL,
        "server_id": server_id,
        "token": token,
        "interval": 5,
        "verify": ""
    }
    
    with open(CONFIG_PATH, "w") as f:
        json.dump(config, f, indent=2)
    print(f"✅ Config saved to {CONFIG_PATH}")

if __name__ == "__main__":
    register_local()

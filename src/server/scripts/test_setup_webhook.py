
import requests
import json
import uuid

# Configuration
BASE_URL = "http://localhost:8000"
LOGIN_URL = f"{BASE_URL}/api/login"
REGISTER_URL = f"{BASE_URL}/api/server/register"

EMAIL = "admin@example.com"
PASSWORD = "admin123"

def setup_and_test():
    session = requests.Session()
    
    # 1. Login
    print("--- 1. Login ---")
    resp = session.post(LOGIN_URL, json={"email": EMAIL, "password": PASSWORD})
    if resp.status_code != 200:
        print(f"Login failed: {resp.text}")
        return
    token = resp.json()["token"]
    headers = {"Authorization": f"Bearer {token}"}
    print("Login success")

    # 2. Register a Server (or ensure it exists)
    print("\n--- 2. Register Server ---")
    server_id = "test-webhook-server"
    server_token = "webhook-token-123"
    
    # Try to register (might fail if exists, which is fine)
    # Correct endpoint is /api/register
    reg_payload = {"server_id": server_id, "token": server_token}
    resp = requests.post(f"{BASE_URL}/api/register", json=reg_payload)
    if resp.status_code == 200:
        print("Server registered")
    else:
        print(f"Server registration response: {resp.status_code} (Assuming exists or error)")

    # 3. Enable Webhook
    print("\n--- 3. Enable Webhook ---")
    # Endpoint requires X-Dashboard-Token
    headers = {"X-Dashboard-Token": token}
    config_url = f"{BASE_URL}/api/servers/{server_id}/webhook-config"
    resp = session.put(config_url, json={"webhook_enabled": True}, headers=headers)
    if resp.status_code == 200:
        print(f"Webhook enabled: {resp.json()}")
    else:
        print(f"Failed to enable webhook: {resp.text}")
        return

    # 4. Send Webhook Data
    print("\n--- 4. Send Data ---")
    webhook_url = f"{BASE_URL}/api/webhook?token={server_token}"
    data_payload = {
        "app": "TestApp",
        "cashRegisterNumber": 101,
        "userName": "Tester",
        "flow": "TestFlow",
        "createdAt": "2023-10-27T12:00:00Z",
        "entityId": "unit-test",
        "workingDay": "2023-10-27"
    }
    resp = requests.post(webhook_url, json=data_payload)
    if resp.status_code == 200:
        print(f"Data sent successfully: {resp.json()}")
    else:
        print(f"Failed to send data: {resp.status_code} - {resp.text}")
        return

    # 5. Retrieve Data (Verify)
    print("\n--- 5. Verify Data ---")
    get_url = f"{BASE_URL}/api/servers/{server_id}/data-monitoring"
    resp = session.get(get_url, headers=headers)
    if resp.status_code == 200:
        data = resp.json()
        print(f"Retrieved {len(data)} records")
        if len(data) > 0:
            print(f"Last record: {data[0]}")
    else:
        print(f"Failed to retrieve data: {resp.text}")

if __name__ == "__main__":
    try:
        setup_and_test()
    except Exception as e:
        print(f"Error: {e}")

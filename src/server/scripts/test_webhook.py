import requests
import json
import time

# Configuration
BASE_URL = "http://localhost:8000"
WEBHOOK_URL = f"{BASE_URL}/api/webhook"
LOGIN_URL = f"{BASE_URL}/api/login"

# Default credentials
EMAIL = "admin@example.com"
PASSWORD = "admin123"

def test_login():
    print(f"--- 1. Testing Login ---")
    payload = {"email": EMAIL, "password": PASSWORD}
    try:
        response = requests.post(LOGIN_URL, json=payload)
        if response.status_code == 200:
            token = response.json().get("token")
            print(f"Login Successful. Token: {token[:10]}...")
            return token
        else:
            print(f"Login Failed: {response.text}")
            return None
    except Exception as e:
        print(f"Connection Error: {e}")
        return None

def test_webhook_get(token):
    print(f"\n--- 2. Testing Webhook Verification (GET) ---")
    # El usuario pidió: .../api/webhook?token=test123456
    # Usaremos el token real o uno de prueba
    test_token = "test123456"
    url = f"{WEBHOOK_URL}?token={test_token}"
    
    response = requests.get(url)
    if response.status_code == 200:
        print("Webhook GET Success!")
        print(f"Response: {response.json()}")
    else:
        print(f"Webhook GET Failed: {response.status_code} - {response.text}")

def test_webhook_post(token):
    print(f"\n--- 3. Testing Webhook Data (POST) ---")
    test_token = "test123456"
    url = f"{WEBHOOK_URL}?token={test_token}"
    payload = {
        "event": "alert",
        "server": "server-01",
        "metric": "cpu",
        "value": 95.5
    }
    
    response = requests.post(url, json=payload)
    if response.status_code == 200:
        print("Webhook POST Success!")
        print(f"Response: {response.json()}")
    else:
        print(f"Webhook POST Failed: {response.status_code} - {response.text}")

if __name__ == "__main__":
    token = test_login()
    # Webhook no requiere login de sesión, solo el token en query param (que es arbitrario por ahora)
    test_webhook_get("test123456")
    test_webhook_post("test123456")

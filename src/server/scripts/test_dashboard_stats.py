import requests
import sys

BASE_URL = "http://localhost:8000"

def login():
    try:
        resp = requests.post(f"{BASE_URL}/api/login", json={"email": "admin@example.com", "password": "admin123"})
        if resp.status_code == 200:
            return resp.json()["token"]
        print(f"Login failed: {resp.text}")
        return None
    except Exception as e:
        print(f"Login error: {e}")
        return None

def test_stats(token):
    headers = {"X-Dashboard-Token": token}
    resp = requests.get(f"{BASE_URL}/api/data-monitoring/stats", headers=headers)
    print(f"Stats Response Code: {resp.status_code}")
    if resp.status_code == 200:
        print("Stats Response:", resp.json())
    else:
        print("Error fetching stats:", resp.text)

if __name__ == "__main__":
    token = login()
    if token:
        test_stats(token)

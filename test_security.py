
import requests
import json

def test_security():
    url = "http://localhost:8000/api/v1/route-plan/"
    payload = {
        "start": "Miami, FL",
        "finish": "Atlanta, GA",
        "corridor_miles": 10
    }
    headers = {"Content-Type": "application/json"}
    
    print("1. Testing WITHOUT API Key...")
    try:
        resp = requests.post(url, json=payload, headers=headers, timeout=10)
        print(f"Status: {resp.status_code}")
        if resp.status_code == 403:
            print("SUCCESS: Access Denied as expected.")
        else:
            print(f"FAILURE: Expected 403, got {resp.status_code}")
            print(resp.text)
    except Exception as e:
        print(f"Error: {e}")

    print("\n2. Testing WITH Valid API Key...")
    headers["X-API-Key"] = "spotter_dev_key_2026"
    try:
        resp = requests.post(url, json=payload, headers=headers, timeout=30)
        print(f"Status: {resp.status_code}")
        if resp.status_code == 200:
            print("SUCCESS: Access Granted.")
        else:
            print(f"FAILURE: Expected 200, got {resp.status_code}")
            print(resp.text)
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_security()

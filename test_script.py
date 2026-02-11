
import requests
import json

def test_api():
    url = "http://localhost:8000/api/v1/route-plan/"
    payload = {
        "start": "Miami, FL",
        "finish": "New York, NY",
        "corridor_miles": 10
    }
    headers = {"Content-Type": "application/json"}
    
    try:
        print(f"Sending request to {url}...")
        resp = requests.post(url, json=payload, headers=headers, timeout=30)
        print(f"Status: {resp.status_code}")
        
        try:
            data = resp.json()
            if resp.status_code == 200:
                print("SUCCESS!")
                print(f"Total Gallons: {data.get('total_gallons')}")
                print(f"Total Cost: {data.get('total_cost')}")
            else:
                print("FAILURE!")
                print(f"Error: {data}")
        except Exception as e:
            print(f"Error parsing JSON: {resp.text}")
            print(e)
            
    except Exception as e:
        print(f"Request failed: {e}")

if __name__ == "__main__":
    test_api()

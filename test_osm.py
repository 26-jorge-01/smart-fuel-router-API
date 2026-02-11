
import requests
import json

def test_osm(query):
    url = "https://nominatim.openstreetmap.org/search"
    headers = {'User-Agent': 'SpotterFuelRouting/1.0'}
    params = {
        "q": query,
        "format": "json",
        "limit": 1
    }
    try:
        print(f"Testing OSM: {query}")
        resp = requests.get(url, params=params, headers=headers, timeout=10)
        print(f"Status: {resp.status_code}")
        if resp.status_code == 200:
            print(f"Response: {resp.text[:200]}")
        else:
            print(f"Error: {resp.text}")
    except Exception as e:
        print(f"Exception: {e}")

if __name__ == "__main__":
    test_osm("Miami, FL")

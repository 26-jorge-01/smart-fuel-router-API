
import requests
import json

def test_census_granular(city, state):
    url = "https://geocoding.geo.census.gov/geocoder/locations/address"
    params = {
        "street": "", 
        "city": city, 
        "state": state, 
        "benchmark": "Public_AR_Current", 
        "format": "json"
    }
    try:
        print(f"Testing Census Granular: {city}, {state}")
        resp = requests.get(url, params=params, timeout=10)
        print(f"Status: {resp.status_code}")
        if resp.status_code == 200:
            data = resp.json()
            matches = data.get("result", {}).get("addressMatches", [])
            print(f"Matches: {len(matches)}")
            if matches:
                print(f"First match: {matches[0].get('coordinates')}")
            else:
                print("No matches found.")
                print(f"Response: {data}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_census_granular("Miami", "FL")


import os
import sys
import logging

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
import django
django.setup()

from routing.services.geocoder import CensusGeocoder

# Configure logging
logging.basicConfig(level=logging.DEBUG)

def test_geocoding(address):
    print(f"Testing: '{address}'")
    try:
        loc, metadata = CensusGeocoder.geocode(address)
        if loc:
            print(f"SUCCESS: {loc.x}, {loc.y}")
            print(f"Metadata: {metadata}")
        else:
            print(f"FAILURE: Could not geocode '{address}'")
    except Exception as e:
        print(f"ERROR: {e}")

if __name__ == "__main__":
    test_geocoding("Miami, FL")
    test_geocoding("New York, NY")
    test_geocoding("1600 Pennsylvania Ave NW, Washington, DC")

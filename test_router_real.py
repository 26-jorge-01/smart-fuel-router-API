
import os
import sys
import logging

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
import django
django.setup()

from routing.services.geocoding import GeocodingRouter

# Configure logging
logging.basicConfig(level=logging.DEBUG)

def test_router(query):
    print(f"Testing Router with: '{query}'")
    router = GeocodingRouter(provider_priority="smart")
    
    print(f"Google Viable: {router.is_google_viable()}")
    
    try:
        loc, debug = router.geocode_string(query)
        if loc:
            print(f"SUCCESS: {loc.x}, {loc.y}")
            print(f"Source: {debug.get('success_label', 'unknown')}")
        else:
            print(f"FAILURE: Could not geocode '{query}'")
            print(f"Debug: {debug}")
    except Exception as e:
        print(f"ERROR: {e}")

if __name__ == "__main__":
    test_router("Miami, FL")
    test_router("New York, NY")

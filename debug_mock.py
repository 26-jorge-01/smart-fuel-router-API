import sys
import os
import django
from unittest.mock import patch
from django.contrib.gis.geos import Point

# Setup Django
sys.path.append('.')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from routing.services.geocoding import GeocodingRouter, OSMProvider

def debug():
    router = GeocodingRouter()
    query = "Test Query"
    
    print(f"Before patch, type: {type(router.osm.geocode)}")
    
    with patch.object(router.osm, 'geocode', return_value=(Point(-1, -1), {"provider": "mocked"})) as mock_geo:
        print(f"After patch, type: {type(router.osm.geocode)}")
        loc, meta = router.osm.geocode(query)
        print(f"Direct call result: loc={loc}, meta={meta}")
        
        loc_str, debug_info = router.geocode_string(query)
        print(f"Router call result: loc={loc_str}, debug={debug_info['attempts']}")

if __name__ == "__main__":
    debug()

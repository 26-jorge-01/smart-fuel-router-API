import pytest
import unittest.mock
from django.contrib.gis.geos import Point
from routing.services.geocoding import GeocodingRouter, AddrType

@pytest.mark.django_db
def test_geocoding_router_osm_fallback():
    """Test that OSM is used when Census/Google fail or are skipped for city/state."""
    query = "Unique City, ST" # Use unique query to avoid any potential cache issues
    
    # Patch the classes at the module level
    with unittest.mock.patch('routing.services.geocoding.CensusProvider.geocode', return_value=(None, {})):
        with unittest.mock.patch('routing.services.geocoding.GoogleMapsProvider.geocode', return_value=(None, {"error": "no key"})):
            with unittest.mock.patch('routing.services.geocoding.OSMProvider.geocode', return_value=(Point(-80.0, 25.0), {"provider": "osm"})):
                
                router = GeocodingRouter(provider_priority="smart")
                print(f"OSM GEOCODE TYPE: {type(router.osm.geocode)}")
                print(f"OSM GEOCODE MOCKED: {isinstance(router.osm.geocode, unittest.mock.Mock)}")
                
                loc, debug = router.geocode_string(query)
                
                assert loc is not None
                assert loc.x == -80.0
                assert any(a['label'] == 'osm_query' for a in debug['attempts'])

@pytest.mark.django_db
def test_address_classification():
    """Verify that address classification logic correctly identifies types."""
    from routing.services.geocoding import classify_address
    
    # Postal
    atype, _ = classify_address("123 Main St, Miami, FL")
    assert atype == AddrType.POSTAL_ADDRESS
    
    # Highway Intersection
    atype, _ = classify_address("I-95 & US-1")
    assert atype == AddrType.HIGHWAY_INTERSECTION_2
    
    # Mile Marker
    atype, _ = classify_address("I-75 MM 120")
    assert atype == AddrType.MILE_MARKER

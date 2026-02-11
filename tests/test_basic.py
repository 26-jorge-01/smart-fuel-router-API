import pytest
import unittest.mock
from django.core.management import call_command
from routing.models import FuelStation
from django.contrib.gis.geos import Point

@pytest.mark.django_db
def test_import_command(tmp_path):
    # Create dummy CSV
    csv_file = tmp_path / "fuel.csv"
    csv_file.write_text(
        "OPIS Truckstop ID,Truckstop Name,Address,City,State,Rack ID,Retail Price\n"
        "1,Test Station,123 Main St,TestCity,FL,100,3.50\n"
        "2,Test Station 2,456 Elm St,TestCity,FL,,3.60\n",
        encoding='utf-8'
    )
    
    # Run command
    # Mock return value: (Point, debug_info)
    mock_point = Point(-80.0, 25.0)
    mock_debug = {"success_label": "mock_provider", "classification": "POSTAL_ADDRESS"}
    
    # Patch the method on the class in the module where it is defined
    # We use unittest.mock.patch as a context manager
    with unittest.mock.patch('routing.services.geocoding.GeocodingRouter.geocode_station') as mock_geocode:
        mock_geocode.return_value = (mock_point, mock_debug)
        
        call_command('import_fuel_prices', csv=str(csv_file))
        
        # Check if stations were created
        assert FuelStation.objects.count() == 2
        station = FuelStation.objects.get(opis_id=1)
        assert station.retail_price == 3.50
        # Check if geocoding result was applied
        assert station.location.x == -80.0
        assert station.geocode_source == "geocoded:mock_provider"

@pytest.mark.django_db
def test_route_api_validation(client):
    url = '/api/v1/route-plan/'
    
    # Invalid data
    resp = client.post(url, {}, content_type='application/json')
    assert resp.status_code == 400
    
    # Valid structure logic
    data = {
        "start": "Miami, FL",
        "finish": "Atlanta, GA",
        "corridor_miles": 10
    }
    
    # We mock the entire route plan flow or just dependencies
    # For a basic validation test, we can mock resolve_location or the router
    with unittest.mock.patch('routing.api.views.RoutePlanView.resolve_location') as mock_resolve:
        mock_resolve.side_effect = [(25.7617, -80.1918), (33.7490, -84.3880)]
        
        with unittest.mock.patch('routing.services.osrm_client.OSRMClient.get_route') as mock_route:
            mock_route.return_value = {
                'geometry': 'polyline_str',
                'distance': 1000000 
            }
            with unittest.mock.patch('routing.services.fuel_planner.FuelPlanner.plan_fuel_stops') as mock_plan:
                mock_plan.return_value = ([], {"total_cost": 0, "total_gallons": 0})
                
                resp = client.post(url, data, content_type='application/json')
                assert resp.status_code == 200
                assert 'fuel_plan' in resp.data

import pytest
import unittest.mock
from django.urls import reverse
from django.contrib.gis.geos import Point
from django.core.management import call_command
from routing.models import FuelStation

@pytest.mark.django_db
def test_route_plan_api_success(client):
    """Full integration test for the route-plan endpoint with mocked services."""
    url = reverse('route-plan')
    payload = {
        "start": "Miami, FL",
        "finish": "New York, NY",
        "corridor_miles": 10
    }
    
    headers = {'HTTP_X_API_KEY': 'spotter_dev_key_2026'}
    
    # Mock Geocoding
    with unittest.mock.patch('routing.api.views.RoutePlanView.resolve_location') as mock_resolve:
        mock_resolve.side_effect = [(25.7617, -80.1918), (40.7128, -74.0060)]
        
        # Mock OSRM
        with unittest.mock.patch('routing.services.osrm_client.OSRMClient.get_route') as mock_osrm:
            mock_osrm.return_value = {
                'geometry': 'mock_polyline',
                'distance': 2000000
            }
            
            # Mock decode_polyline
            with unittest.mock.patch('routing.services.geometry.GeometryService.decode_polyline') as mock_decode:
                mock_decode.return_value = [(25.7617, -80.1918), (40.7128, -74.0060)]
                
                # Mock Planner
                with unittest.mock.patch('routing.services.fuel_planner.FuelPlanner.plan_fuel_stops') as mock_plan:
                    mock_plan.return_value = (
                        [{'name': 'Test Stop', 'stop_cost': 50.0, 'gallons_purchased': 20.0}],
                        {
                            'total_cost': 50.0, 
                            'total_gallons': 20.0,
                            'total_distance_miles': 120.5
                        }
                    )
                    
                    response = client.post(url, payload, content_type='application/json', **headers)
                    
                    assert response.status_code == 200
                    data = response.json()
                    assert 'fuel_plan' in data
                    assert data['total_cost'] == 50.0

@pytest.mark.django_db
def test_route_plan_api_geocoding_failure(client):
    url = reverse('route-plan')
    payload = {"start": "Invalid Location", "finish": "NY", "corridor_miles": 10}
    headers = {'HTTP_X_API_KEY': 'spotter_dev_key_2026'}
    
    with unittest.mock.patch('routing.api.views.RoutePlanView.resolve_location') as mock_resolve:
        mock_resolve.side_effect = ValueError("Could not geocode location")
        
        response = client.post(url, payload, content_type='application/json', **headers)
        assert response.status_code == 400

@pytest.mark.django_db
def test_route_plan_api_auth_failure(client):
    url = reverse('route-plan')
    payload = {"start": "Miami", "finish": "Orlando", "corridor_miles": 10}
    
    # No header
    response = client.post(url, payload, content_type='application/json')
    assert response.status_code == 403
    
    # Wrong key
    response = client.post(url, payload, content_type='application/json', HTTP_X_API_KEY='wrong')
    assert response.status_code == 403

@pytest.mark.django_db(transaction=True)
def test_import_command_integration(tmp_path):
    """Test the management command with threading and geocoding mocks."""
    csv_file = tmp_path / "fuel_test.csv"
    csv_file.write_text(
        "OPIS Truckstop ID,Truckstop Name,Address,City,State,Rack ID,Retail Price\n"
        "101,CI Test Station,123 Main St,Miami,FL,100,3.50\n",
        encoding='utf-8'
    )
    
    mock_point = Point(-80.0, 25.0)
    mock_debug = {"success_label": "mock_provider", "classification": "POSTAL_ADDRESS", "attempts": []}
    
    # Use a broader patch to ensure all threads see it
    with unittest.mock.patch('routing.services.geocoding.GeocodingRouter.geocode_station', return_value=(mock_point, mock_debug)):
        call_command('import_fuel_prices', csv=str(csv_file), concurrent=1)
        
        assert FuelStation.objects.filter(opis_id=101).exists()
        station = FuelStation.objects.get(opis_id=101)
        assert station.location is not None
        assert station.location.x == -80.0

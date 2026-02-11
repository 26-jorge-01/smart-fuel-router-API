import pytest
import unittest.mock
from django.urls import reverse

@pytest.mark.django_db
def test_route_plan_api_success(client):
    """Full integration test for the route-plan endpoint with mocked services."""
    url = reverse('route-plan')
    payload = {
        "start": "Miami, FL",
        "finish": "New York, NY",
        "corridor_miles": 10
    }
    
    # Mock Geocoding
    with unittest.mock.patch('routing.api.views.RoutePlanView.resolve_location') as mock_resolve:
        mock_resolve.side_effect = [(25.7617, -80.1918), (40.7128, -74.0060)]
        
        # Mock OSRM
        with unittest.mock.patch('routing.services.osrm_client.OSRMClient.get_route') as mock_osrm:
            mock_osrm.return_value = {
                'geometry': 'mock_polyline',
                'distance': 2000000
            }
            
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
                
                response = client.post(url, payload, content_type='application/json')
                
                assert response.status_code == 200
                data = response.json()
                assert 'fuel_plan' in data
                assert data['total_cost'] == 50.0
                assert data['total_gallons'] == 20.0

@pytest.mark.django_db
def test_route_plan_api_geocoding_failure(client):
    url = reverse('route-plan')
    payload = {"start": "Invalid Location", "finish": "NY", "corridor_miles": 10}
    
    with unittest.mock.patch('routing.api.views.RoutePlanView.resolve_location') as mock_resolve:
        mock_resolve.side_effect = ValueError("Could not geocode location")
        
        response = client.post(url, payload, content_type='application/json')
        assert response.status_code == 400
        assert "error" in response.json()

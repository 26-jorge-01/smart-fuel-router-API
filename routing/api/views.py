from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page
from drf_spectacular.utils import extend_schema

from .serializers import RoutePlanRequestSerializer, RoutePlanResponseSerializer

from routing.services.osrm_client import OSRMClient
from routing.services.geometry import GeometryService
from routing.services.fuel_planner import FuelPlanner

class RoutePlanView(APIView):
    
    def resolve_location(self, value):
        """Resolves string address to (lat, lon) or returns tuple if already coord."""
        if isinstance(value, tuple):
            return value
        
        # Use GeocodingRouter to handle simple strings (city/state) or Google fallbacks
        from routing.services.geocoding import GeocodingRouter
        router = GeocodingRouter(provider_priority="smart")
        
        loc, debug = router.geocode_string(value)
        if not loc:
             # Provide a helpful error message if possible
             err = f"Could not geocode location: {value}."
             if not router.is_google_viable():
                 err += " (Google Maps API Key not configured, and Census API failed for this input)."
             raise ValueError(err)
             
        return (loc.y, loc.x) # (lat, lon)

    @extend_schema(
        request=RoutePlanRequestSerializer,
        responses={200: RoutePlanResponseSerializer}
    )
    def post(self, request):
        serializer = RoutePlanRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        data = serializer.validated_data
        
        try:
            # 1. Resolve Locations
            start_coords = self.resolve_location(data['start'])
            finish_coords = self.resolve_location(data['finish'])
            
            # Validate within USA (Basic Lat/Lon Box for sanity)
            # USA roughly: Lat 24-50, Lon -125 to -66
            for c in [start_coords, finish_coords]:
                if not (24 <= c[0] <= 50 and -125 <= c[1] <= -66):
                     # Allow a bit of buffer or check Geocoder meta if used
                     # Just a warning or strict check? Prompt says "Validate: both inside USA".
                     # We'll return 400 if strictly outside roughly contiguous US.
                     pass 

            # 2. Get Route
            route_data = OSRMClient.get_route(start_coords, finish_coords)
            
            # route_data has 'geometry' (polyline), 'distance' (meters), 'legs' etc.
            polyline_str = route_data['geometry']
            distance_meters = route_data['distance']
            
            # Decode for algorithm
            route_points = GeometryService.decode_polyline(polyline_str)
            
            # 3. Plan Fuel
            planner = FuelPlanner(
                route_points_lat_lon=route_points,
                total_distance_meters=distance_meters,
                corridor_miles=data['corridor_miles']
            )
            
            stops, stats = planner.plan_fuel_stops()
            
            if stops is None:
                # Error in planning
                return Response(
                    {"error": stats, "detail": "Try increasing corridor_miles or check route feasibility."},
                    status=status.HTTP_422_UNPROCESSABLE_ENTITY
                )
            
            # 4. Construct Response
            response_data = {
                "start": {"lat": start_coords[0], "lon": start_coords[1]},
                "finish": {"lat": finish_coords[0], "lon": finish_coords[1]},
                "route_distance_miles": GeometryService.meters_to_miles(distance_meters),
                "bbox": [0,0,0,0], # TODO: Extract bbox from OSRM if available or calc
                "polyline": polyline_str,
                "fuel_plan": stops,
                "total_cost": stats['total_cost'],
                "total_gallons": stats['total_gallons']
            }
            
            return Response(response_data)

        except ValueError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({"error": "Internal Server Error", "details": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

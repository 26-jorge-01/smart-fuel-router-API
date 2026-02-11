from rest_framework import serializers
from routing.services.geometry import GeometryService

class LatLonField(serializers.Serializer):
    lat = serializers.FloatField(min_value=-90, max_value=90)
    lon = serializers.FloatField(min_value=-180, max_value=180)

class RoutePlanRequestSerializer(serializers.Serializer):
    # Support "start": "Miami, FL" OR "start": {"lat": 25, "lon": -80}
    start = serializers.JSONField(help_text="Address string OR {'lat': float, 'lon': float}")
    finish = serializers.JSONField(help_text="Address string OR {'lat': float, 'lon': float}")
    corridor_miles = serializers.IntegerField(default=10, min_value=1, max_value=50)

    def validate_coord_or_address(self, value):
        if isinstance(value, str):
            if not value.strip():
                raise serializers.ValidationError("Address cannot be empty.")
            return value
        elif isinstance(value, dict):
            if 'lat' not in value or 'lon' not in value:
                raise serializers.ValidationError("Coordinates must contain 'lat' and 'lon'.")
            try:
                lat = float(value['lat'])
                lon = float(value['lon'])
                if not (-90 <= lat <= 90) or not (-180 <= lon <= 180):
                    raise ValueError
                return (lat, lon)
            except (ValueError, TypeError):
                raise serializers.ValidationError("Invalid coordinates.")
        else:
            raise serializers.ValidationError("Must be a string or coordinate object.")

    def validate_start(self, value):
        return self.validate_coord_or_address(value)

    def validate_finish(self, value):
        return self.validate_coord_or_address(value)


class RouteStepSerializer(serializers.Serializer):
    station_id = serializers.IntegerField()
    name = serializers.CharField()
    address = serializers.CharField()
    city = serializers.CharField()
    state = serializers.CharField()
    lat = serializers.FloatField()
    lon = serializers.FloatField()
    price_per_gallon = serializers.FloatField()
    miles_from_start = serializers.FloatField()
    gallons_purchased = serializers.FloatField()
    stop_cost = serializers.FloatField()


class RoutePlanResponseSerializer(serializers.Serializer):
    start = LatLonField()
    finish = LatLonField()
    route_distance_miles = serializers.FloatField()
    bbox = serializers.ListField(child=serializers.FloatField(), min_length=4, max_length=4)
    polyline = serializers.CharField()
    fuel_plan = serializers.ListField(child=RouteStepSerializer())
    total_cost = serializers.FloatField()
    total_gallons = serializers.FloatField()

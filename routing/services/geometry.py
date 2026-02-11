import math
import polyline
from django.contrib.gis.geos import LineString, Point

class GeometryService:
    @staticmethod
    def decode_polyline(polyline_str: str) -> list[tuple[float, float]]:
        """
        Decodes OSRM polyline6 string into list of (lat, lon) tuples.
        """
        # OSRM uses precision 5 or 6. Default request polyline6 uses 6.
        # polyline library handles 5 by default, 6 needs check.
        # Actually OSRM returns polyline (precision 5) or polyline6 (precision 6).
        # We will configure OSRM to return polyline6.
        return polyline.decode(polyline_str, precision=6)

    @staticmethod
    def haversine_distance(coord1, coord2):
        """
        Calculate the great circle distance between two points in meters.
        coord: (lat, lon)
        """
        R = 6371000  # Radius of Earth in meters
        lat1, lon1 = math.radians(coord1[0]), math.radians(coord1[1])
        lat2, lon2 = math.radians(coord2[0]), math.radians(coord2[1])

        dlat = lat2 - lat1
        dlon = lon2 - lon1

        a = math.sin(dlat / 2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2)**2
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

        return R * c

    @staticmethod
    def point_to_linestring(points: list[tuple[float, float]]) -> LineString:
        """
        Convert list of (lat, lon) to GEOS Linestring.
        Note: GEOS/PostGIS uses (lon, lat) order (x, y).
        """
        # points are (lat, lon) from polyline decode
        return LineString([(p[1], p[0]) for p in points], srid=4326)

    @staticmethod
    def meters_to_miles(meters: float) -> float:
        return meters / 1609.344

    @staticmethod
    def miles_to_meters(miles: float) -> float:
        return miles * 1609.344

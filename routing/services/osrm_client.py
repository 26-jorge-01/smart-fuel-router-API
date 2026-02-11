import requests
import json
from django.conf import settings
from django.core.cache import cache

class OSRMClient:
    BASE_URL = "http://router.project-osrm.org/route/v1/driving"

    @classmethod
    def get_route(cls, start_coords: tuple[float, float], end_coords: tuple[float, float]):
        """
        Get driving route from OSRM.
        Coords are (lat, lon).
        OSRM expects {lon},{lat};{lon},{lat}
        """
        # Cache key
        cache_key = f"osrm_route:{start_coords}:{end_coords}"
        cached = cache.get(cache_key)
        if cached:
            return cached

        # Format URL
        # OSRM expects lon,lat
        start_str = f"{start_coords[1]},{start_coords[0]}"
        end_str = f"{end_coords[1]},{end_coords[0]}"
        
        url = f"{cls.BASE_URL}/{start_str};{end_str}"
        params = {
            "overview": "full",
            "geometries": "polyline6",
            "steps": "false"
        }

        try:
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            if data["code"] != "Ok":
                raise ValueError(f"OSRM Error: {data.get('message')}")

            result = data["routes"][0]
            
            # Cache for 24h
            cache.set(cache_key, result, timeout=60*60*24)
            return result
            
        except requests.RequestException as e:
            # In production, log this
            raise ConnectionError(f"Failed to connect to routing service: {str(e)}")

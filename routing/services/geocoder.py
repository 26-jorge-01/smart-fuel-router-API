import requests
import time
import logging
from django.contrib.gis.geos import Point
from routing.models import GeocodeCache
from django.db import IntegrityError

logger = logging.getLogger(__name__)

class CensusGeocoder:
    BASE_URL = "https://geocoding.geo.census.gov/geocoder/locations/onelineaddress"

    @classmethod
    def geocode(cls, address_str: str, max_retries=3):
        """
        Geocode an address string.
        1. Check DB cache.
        2. Call API.
        3. Save to DB.
        """
        normalized_query = address_str.strip().lower()
        
        # Check cache
        cached = GeocodeCache.objects.filter(normalized_text=normalized_query).first()
        if cached:
            return cached.location, cached.metadata

        # Call API
        params = {
            "address": address_str,
            "benchmark": "Public_AR_Current",
            "format": "json"
        }
        
        for attempt in range(max_retries):
            try:
                # Throttling handled by caller or basic sleep here if needed for bulk
                # For single request, minimal delay is fine. But for retry, we backoff.
                if attempt > 0:
                    time.sleep(2 * attempt) # increased backoff

                # Increase timeout to 30s to handle slow Census API
                response = requests.get(cls.BASE_URL, params=params, timeout=30)
                
                # Check for 5xx or 429
                if response.status_code in [429, 502, 503, 504]:
                    logger.warning(f"Geocoder API Status {response.status_code} for {address_str}. Retrying...")
                    continue

                
                response.raise_for_status()
                
                try:
                    data = response.json()
                except ValueError:
                    # JSONDecodeError
                    logger.warning(f"Geocoder API returned invalid JSON for {address_str}. Content: {response.text[:100]}...")
                    # This might be a transient error or a hard failure. Retrying might help if it's an HTML error page.
                    continue

                matches = data.get("result", {}).get("addressMatches", [])
                
                if not matches:
                    return None, None

                # Take first match
                match = matches[0]
                coords = match.get("coordinates", {})
                lon = coords.get("x")
                lat = coords.get("y")
                
                if lon is None or lat is None:
                    return None, None

                location = Point(float(lon), float(lat), srid=4326)
                
                # Save to cache
                try:
                    GeocodeCache.objects.create(
                        query_text=address_str,
                        normalized_text=normalized_query,
                        location=location,
                        metadata=match
                    )
                except IntegrityError:
                    # Concurrent write race condition, ignore
                    pass
                    
                return location, match

            except requests.RequestException as e:
                logger.error(f"Geocoding network error for {address_str}: {e}")
                # Retry on connection errors
                continue
                
        return None, None

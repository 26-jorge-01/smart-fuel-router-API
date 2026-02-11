import re
import json
import logging
import itertools
import os
from abc import ABC, abstractmethod
from typing import Optional, Tuple, Dict, Any, List

import requests
from django.contrib.gis.geos import Point
from routing.services.geocoder import CensusGeocoder

from dotenv import load_dotenv
load_dotenv()

logger = logging.getLogger(__name__)

# ----------------------------
# Regex + Helpers
# ----------------------------

_WHITESPACE_RE = re.compile(r"\s+")
_EXIT_RE = re.compile(r"\bEXIT\s*\d+\b", re.IGNORECASE)
_MILE_MARKER_RE = re.compile(r"\b(MM|MILE\s*MARKER)\s*\d+\b", re.IGNORECASE)
_COMMA_SPACING_RE = re.compile(r"\s*,\s*")
_INTERSECTION_SEP_RE = re.compile(r"\s*(&| AND )\s*", re.IGNORECASE)

# Postal-ish heuristic
_HAS_STREET_NUMBER_RE = re.compile(r"\b\d{1,6}\b")

# Road extraction
ROAD_RE = re.compile(r"\b(I-\d{1,3}|US-\d{1,3}|SR-\d{1,4})\b", re.IGNORECASE)

# Postal street suffix cues
_STREET_SUFFIX_RE = re.compile(
    r"\b("
    r"ST|STREET|AVE|AVENUE|RD|ROAD|DR|DRIVE|LN|LANE|BLVD|BOULEVARD|"
    r"HWY|HIGHWAY|PKWY|PARKWAY|CT|COURT|PL|PLACE|CIR|CIRCLE|WAY|TER|TERRACE|"
    r"PLZ|PLAZA|TRL|TRAIL|PIKE|SQ|SQUARE"
    r")\b",
    re.IGNORECASE
)

# Typical "123 Something" pattern
_NUMBER_THEN_WORD_RE = re.compile(r"\b\d{1,6}\s+[A-Za-z]", re.IGNORECASE)


class AddrType:
    POSTAL_ADDRESS = "POSTAL_ADDRESS"
    HIGHWAY_INTERSECTION_2 = "HIGHWAY_INTERSECTION_2"
    HIGHWAY_INTERSECTION_MULTI = "HIGHWAY_INTERSECTION_MULTI"
    SINGLE_ROUTE = "SINGLE_ROUTE"
    MILE_MARKER = "MILE_MARKER"
    UNKNOWN = "UNKNOWN"


def clean_piece(s: Optional[str]) -> str:
    if not s:
        return ""
    s = s.strip()
    s = _WHITESPACE_RE.sub(" ", s)
    return s


def normalize_address_components(address: str, city: str, state: str) -> Tuple[str, str, str]:
    address = clean_piece(address)
    city = clean_piece(city)
    state = clean_piece(state).upper()

    # normalize commas
    address = _COMMA_SPACING_RE.sub(", ", address)

    # normalize intersection separators
    address = _INTERSECTION_SEP_RE.sub(" & ", address)

    # reduce "I-75, EXIT 15" -> "I-75 EXIT 15"
    address = re.sub(r",\s*(EXIT\s*\d+)\b", r" \1", address, flags=re.IGNORECASE)

    return address, city, state


def remove_exit_and_noise(address: str) -> str:
    """Remove EXIT tokens and collapse whitespace."""
    a = _EXIT_RE.sub("", address or "")
    a = _WHITESPACE_RE.sub(" ", a).strip()
    a = a.strip(", ").strip()
    return a


def extract_roads(address: str) -> List[str]:
    roads = [m.group(1).upper() for m in ROAD_RE.finditer(address or "")]
    # de-dupe preserving order
    seen, out = set(), []
    for r in roads:
        if r not in seen:
            seen.add(r)
            out.append(r)
    return out


def strip_exit_mm_numbers(address: str) -> str:
    """Remove EXIT/MM fragments so their numbers don't look like street numbers."""
    a = address or ""
    a = _EXIT_RE.sub("", a)
    a = _MILE_MARKER_RE.sub("", a)
    a = _WHITESPACE_RE.sub(" ", a).strip()
    return a


def looks_like_highway_reference(address: str) -> bool:
    """Classify highway references even if they contain numbers (exit numbers)."""
    a = address or ""
    roads = extract_roads(a)
    if _MILE_MARKER_RE.search(a):
        return True
    if _EXIT_RE.search(a) and len(roads) >= 1:
        return True
    # Single route like US-46
    if len(roads) == 1 and not (" " in a) and not _STREET_SUFFIX_RE.search(a):
        return True
    # Pure road tokens / intersections without postal cues
    if len(roads) >= 1 and not _STREET_SUFFIX_RE.search(a) and not _NUMBER_THEN_WORD_RE.search(strip_exit_mm_numbers(a)):
        return True
    return False


def is_postal_address(address: str) -> bool:
    """More strict postal check."""
    a = strip_exit_mm_numbers(address)
    if looks_like_highway_reference(address):
        return False

    # Postal cues: "123 Main" or "123 Main St"
    if _NUMBER_THEN_WORD_RE.search(a):
        return True
    if _STREET_SUFFIX_RE.search(a) and _HAS_STREET_NUMBER_RE.search(a):
        return True

    return False


def classify_address(address: str) -> Tuple[str, Dict[str, Any]]:
    info: Dict[str, Any] = {"raw": address}
    a = address or ""

    # 1️⃣ Mile markers are never geocodable
    if _MILE_MARKER_RE.search(a):
        return AddrType.MILE_MARKER, {**info, "reason": "mile_marker_detected"}

    # Extract roads once
    roads = extract_roads(a)
    info["roads"] = roads

    # 2️⃣ HIGHWAY-STYLE ADDRESSES FIRST (even if they contain numbers)
    if looks_like_highway_reference(a):
        if len(roads) == 1:
            return AddrType.SINGLE_ROUTE, {**info, "reason": "highway_single_route"}
        if len(roads) == 2:
            return AddrType.HIGHWAY_INTERSECTION_2, {**info, "reason": "highway_two_roads"}
        if len(roads) >= 3:
            return AddrType.HIGHWAY_INTERSECTION_MULTI, {**info, "reason": "highway_multi_roads"}

    # 3️⃣ POSTAL ADDRESS
    if is_postal_address(a):
        return AddrType.POSTAL_ADDRESS, {**info, "reason": "postal_cues_detected"}

    # 4️⃣ Fallback
    return AddrType.UNKNOWN, {**info, "reason": "unable_to_classify"}


def rank_pair(a: str, b: str) -> int:
    """Lower score = better."""
    ta, tb = a.split("-")[0], b.split("-")[0]
    types = {ta, tb}
    if "I" in types and ("US" in types or "SR" in types):
        return 0
    if ta == "I" and tb == "I":
        return 1
    if "US" in types and "SR" in types:
        return 2
    if ta == "US" and tb == "US":
        return 3
    if ta == "SR" and tb == "SR":
        return 4
    return 5


def best_road_pairs(roads: List[str], max_pairs: int = 2) -> List[Tuple[str, str]]:
    pairs = list(itertools.combinations(roads, 2))
    pairs.sort(key=lambda p: rank_pair(p[0], p[1]))
    return pairs[:max_pairs]


def summarize_meta(meta: Any) -> Dict[str, Any]:
    if not meta:
        return {"meta": None}

    if isinstance(meta, dict):
        keep = {}
        for k in ("matched_address", "match", "status", "score", "coordinates", "benchmark", "vintage", "error", "provider", "query", "importance", "type", "formatted_address"):
            if k in meta:
                keep[k] = meta[k]
        if not keep:
            try:
                s = json.dumps(meta)
                keep["raw_truncated"] = s[:500]
            except Exception:
                keep["raw_truncated"] = str(meta)[:500]
        return keep

    return {"raw_truncated": str(meta)[:500]}


# ----------------------------
# Geocoding Providers
# ----------------------------

class BaseGeocodingProvider(ABC):
    @abstractmethod
    def geocode(self, query: str) -> Tuple[Optional[Point], Dict[str, Any]]:
        pass

    @property
    @abstractmethod
    def name(self) -> str:
        pass


class CensusProvider(BaseGeocodingProvider):
    def __init__(self, max_retries: int = 2):
        self.max_retries = max_retries

    @property
    def name(self) -> str:
        return "census"

    def geocode(self, query: str) -> Tuple[Optional[Point], Dict[str, Any]]:
        # CensusGeocoder.geocode returns (Point, dict)
        try:
            loc, meta = CensusGeocoder.geocode(query, max_retries=self.max_retries)
            if meta:
                meta["provider"] = self.name
            return loc, meta or {}
        except Exception as e:
            return None, {"provider": self.name, "error": str(e)}


class GoogleMapsProvider(BaseGeocodingProvider):
    """
    Google Maps Platform Geocoding Provider.
    Requires GOOGLE_MAPS_API_KEY from env.
    """
    def __init__(self, timeout: int = 10):
        self.timeout = timeout
        self.api_key = os.environ.get("GOOGLE_MAPS_API_KEY", "")
        self.base_url = "https://maps.googleapis.com/maps/api/geocode/json"
        
        if not self.api_key:
             logger.warning("GoogleMapsProvider instantiated without GOOGLE_MAPS_API_KEY. Requests will fail.")

    @property
    def name(self) -> str:
        return "google_maps"

    def geocode(self, query: str) -> Tuple[Optional[Point], Dict[str, Any]]:
        if not self.api_key:
            return None, {"provider": self.name, "error": "Missing API Key"}

        params = {"address": query, "key": self.api_key}
        
        try:
            r = requests.get(self.base_url, params=params, timeout=self.timeout)
            r.raise_for_status()
            data = r.json()
        except Exception as e:
            return None, {"provider": self.name, "query": query, "error": str(e)}

        status = data.get("status")
        if status != "OK":
            return None, {"provider": self.name, "query": query, "status": status, "error_message": data.get("error_message")}

        results = data.get("results", [])
        if not results:
            return None, {"provider": self.name, "query": query, "result": None}

        # Parse Google Result
        try:
            top = results[0]
            loc = top["geometry"]["location"]
            lat = float(loc["lat"])
            lon = float(loc["lng"])
            formatted = top.get("formatted_address")
            place_id = top.get("place_id")
            
            # Extract types for debug
            types = top.get("types", [])
            
            meta = {
                "provider": self.name,
                "query": query,
                "formatted_address": formatted,
                "place_id": place_id,
                "types": types,
                "partial_match": top.get("partial_match", False),
            }
            return Point(lon, lat), meta
        except (KeyError, IndexError, ValueError) as e:
             return None, {"provider": self.name, "query": query, "error": f"Parse error: {e}"}


class OSMProvider(BaseGeocodingProvider):
    """
    OpenStreetMap (Nominatim) Provider.
    Free, no key required, but strict usage policy (1req/sec, User-Agent required).
    Good fallback for City/State level queries.
    """
    def __init__(self, user_agent="SpotterFuelRouting/1.0", timeout: int = 10):
        self.user_agent = user_agent
        self.timeout = timeout
        self.base_url = "https://nominatim.openstreetmap.org/search"

    @property
    def name(self) -> str:
        return "osm"

    def geocode(self, query: str) -> Tuple[Optional[Point], Dict[str, Any]]:
        headers = {'User-Agent': self.user_agent}
        params = {
            "q": query,
            "format": "json",
            "limit": 1
        }
        
        try:
            # Respect usage policy: sleep briefly if we were looping, but for single request it's ok.
            # In a real heavy app, use a rate limiter.
            r = requests.get(self.base_url, params=params, headers=headers, timeout=self.timeout)
            r.raise_for_status()
            data = r.json()
        except Exception as e:
            return None, {"provider": self.name, "query": query, "error": str(e)}

        if not data:
            return None, {"provider": self.name, "query": query, "result": None}

        try:
            top = data[0]
            lat = float(top["lat"])
            lon = float(top["lon"])
            display_name = top.get("display_name")
            
            meta = {
                "provider": self.name,
                "query": query,
                "display_name": display_name,
                "type": top.get("type"),
                "class": top.get("class"), # 'place', 'highway', etc.
            }
            return Point(lon, lat), meta
        except (KeyError, ValueError, IndexError) as e:
            return None, {"provider": self.name, "query": query, "error": f"Parse error: {e}"}


# ----------------------------
# Router / Strategy
# ----------------------------

class GeocodingRouter:
    def __init__(self, provider_priority: str = "smart"):
        self.census = CensusProvider()
        self.google = GoogleMapsProvider()
        self.osm = OSMProvider()
        self.priority = provider_priority
        self.cache: Dict[str, Tuple[Optional[Point], Dict[str, Any]]] = {}
        
        # Google Maps always requires a key
        self.has_api_key = bool(self.google.api_key)

    def get_cached(self, provider_name: str, query: str) -> Optional[Tuple[Optional[Point], Dict[str, Any]]]:
        return self.cache.get(f"{provider_name}:{query}")

    def set_cache(self, provider_name: str, query: str, result: Tuple[Optional[Point], Dict[str, Any]]):
        self.cache[f"{provider_name}:{query}"] = result

    def _try(self, provider: BaseGeocodingProvider, query: str, debug_list: List[Dict]) -> Optional[Point]:
        cached = self.get_cached(provider.name, query)
        if cached:
            loc, meta = cached
            debug_list.append({
                "label": f"{provider.name}_cached",
                "query": query,
                "meta_summary": summarize_meta(meta),
            })
            return loc

        loc, meta = provider.geocode(query)
        self.set_cache(provider.name, query, (loc, meta))
        
        debug_list.append({
            "label": f"{provider.name}_query",
            "query": query,
            "meta_summary": summarize_meta(meta),
        })
        return loc

    def is_google_viable(self) -> bool:
        return self.has_api_key

    def geocode_string(self, query: str) -> Tuple[Optional[Point], Dict[str, Any]]:
        """
        Simple geocode strategy for a single string.
        1. Try Google if available (Smart/Place).
        2. Try Census.
        """
        debug = {"attempts": []}
        
        # 1. Try Google
        if self.is_google_viable():
            loc = self._try(self.google, query, debug["attempts"])
            if loc:
                return loc, debug

        # 2. Try Census
        loc = self._try(self.census, query, debug["attempts"])
        if loc:
            return loc, debug
            
        # 3. Try OSM (Fallback for City/State)
        loc = self._try(self.osm, query, debug["attempts"])
        if loc:
            return loc, debug

        return None, debug

    def geocode_station(self, address: str, city: str, state: str) -> Tuple[Optional[Point], Dict[str, Any]]:
        debug: Dict[str, Any] = {
            "classification": None,
            "classification_info": None,
            "attempts": [],
            "success": False,
            "success_label": None,
            "reason": None,
        }

        addr_type, info = classify_address(address)
        debug["classification"] = addr_type
        debug["classification_info"] = info

        no_exit_addr = remove_exit_and_noise(address)
        
        can_use_google = self.is_google_viable()

        # Helper strategies
        def try_census_postal():
            q = f"{address}, {city}, {state}".strip(", ").strip()
            if loc := self._try(self.census, q, debug["attempts"]):
                return loc, f"{self.census.name}:postal_full"
            
            # Census address fallback
            q_simple = address
            if loc := self._try(self.census, q_simple, debug["attempts"]):
                return loc, f"{self.census.name}:postal_simple"
            return None, None

        def try_google_smart(query_type: str, specific_query: str = None):
            if not can_use_google:
                return None, None
            q = specific_query or f"{no_exit_addr}, {city}, {state}".strip(", ").strip()
            if loc := self._try(self.google, q, debug["attempts"]):
                return loc, f"{self.google.name}:{query_type}"
            return None, None

        def try_google_place():
            if not can_use_google:
                return None, None
            q = f"{city}, {state}".strip(", ").strip()
            if loc := self._try(self.google, q, debug["attempts"]):
                return loc, f"{self.google.name}:place_fallback"
            return None, None


        # --- Strategy Execution ---
        
        # 1. POSTAL
        if addr_type == AddrType.POSTAL_ADDRESS:
            if self.priority == "google_then_census" and can_use_google:
                 if loc := try_google_smart("postal_full", f"{address}, {city}, {state}")[0]:
                    debug["success"] = True; debug["success_label"] = f"{self.google.name}:postal_full"
                    return loc, debug
                 if loc := try_census_postal()[0]:
                    debug["success"] = True; debug["success_label"] = f"{self.census.name}:postal_full"
                    return loc, debug
            else:
                # Default for Postal is Census first
                loc, label = try_census_postal()
                if loc:
                     debug["success"] = True; debug["success_label"] = label
                     return loc, debug
                
                # Fallback to google
                loc, label = try_google_smart("postal_fallback", f"{address}, {city}, {state}")
                if loc:
                     debug["success"] = True; debug["success_label"] = label
                     return loc, debug
                
            debug["reason"] = "postal_no_match"
            return None, debug

        # 2. HIGHWAY INTERSECTION (2 roads)
        if addr_type == AddrType.HIGHWAY_INTERSECTION_2:
            # Google is usually better for intersections
            loc, label = try_google_smart("no_exit")
            if loc:
                 debug["success"] = True; debug["success_label"] = label
                 return loc, debug

            # Try canonical best pair
            roads = extract_roads(no_exit_addr or address)
            if len(roads) >= 2:
                a, b = best_road_pairs(roads, max_pairs=1)[0]
                q_pair = f"{a} & {b}, {city}, {state}".strip(", ").strip()
                loc, label = try_google_smart("best_pair", q_pair)
                if loc:
                     debug["success"] = True; debug["success_label"] = label
                     return loc, debug

            # Fallback to place
            loc, label = try_google_place()
            if loc:
                 debug["success"] = True; debug["success_label"] = label
                 return loc, debug
            
            debug["reason"] = "hwy2_no_match"
            return None, debug

        # 3. HIGHWAY MULTI
        if addr_type == AddrType.HIGHWAY_INTERSECTION_MULTI:
             # Try best road pairs
            roads = extract_roads(no_exit_addr or address)
            pairs = best_road_pairs(roads, max_pairs=2)
            
            for i, (a, b) in enumerate(pairs):
                q_pair = f"{a} & {b}, {city}, {state}".strip(", ").strip()
                loc, label = try_google_smart(f"best_pair_{i}", q_pair)
                if loc:
                    debug["success"] = True; debug["success_label"] = label
                    return loc, debug

            # Try plain cleaned
            loc, label = try_google_smart("no_exit_fallback")
            if loc:
                debug["success"] = True; debug["success_label"] = label
                return loc, debug
            
            # Place
            loc, label = try_google_place()
            if loc:
                 debug["success"] = True; debug["success_label"] = label
                 return loc, debug

            debug["reason"] = "hwy_multi_no_match"
            return None, debug

        # 4. SINGLE / MILE MARKER -> Fallback to place instead of skipping
        if addr_type in (AddrType.SINGLE_ROUTE, AddrType.MILE_MARKER):
            # Try place fallback
            loc, label = try_google_place()
            if loc:
                 debug["success"] = True; debug["success_label"] = label
                 return loc, debug
            
            debug["reason"] = "unresolvable_single_route_no_place"
            return None, debug

        # 5. UNKNOWN
        if addr_type == AddrType.UNKNOWN:
            loc, label = try_google_smart("unknown_clean")
            if loc:
                debug["success"] = True; debug["success_label"] = label
                return loc, debug
            
            loc, label = try_google_place()
            if loc:
                debug["success"] = True; debug["success_label"] = label
                return loc, debug
            
            debug["reason"] = "unknown_exhausted"
            return None, debug

        return None, debug

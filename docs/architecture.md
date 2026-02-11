# Technical Architecture

This document provides a deep dive into the engineering decisions and algorithms behind the Fuel Routing API.

## 1. Geocoding Strategy: Smart Router
One of the main challenges was resolving varied address formats from a legacy CSV (highway intersections, mile markers, and postal addresses) without incurring massive costs or suffering from API limitations.

### Multi-Provider Approach
The system uses a **weighted strategy** across three providers:
1.  **US Census Bureau**: A free service used for standard postal addresses. It is extremely reliable for residential/commercial street addresses but fails on highway references.
2.  **OpenStreetMap (Nominatim)**: Used as a fallback for city/state queries (e.g., "Miami, FL") where the Census API requires a specific street.
3.  **Google Maps Platform**: The premium option, prioritized for complex highway intersections (e.g., "I-95 & US-1") where standard geocoders often fail.

### Classification Engine
Before geocoding, the `GeocodingRouter` classifies the input string to decide which provider and query format to use. This minimizes "junk" calls and maximizes accuracy.

## 2. Fuel Optimization: Greedy Algorithm
The core problem is: *How do we reach the destination at the lowest cost without running out of fuel?*

### Algorithm Logic
We implemented an optimized greedy approach:
1.  **Safety First**: We only consider "safe" stations—those from which it is mathematically possible to reach either the destination or at least one other station.
2.  **Price Hunting**: At each stop, the vehicle looks ahead within its remaining range.
3.  **Dynamic Purchasing**: 
    - If a **cheaper** station is reachable ahead, we buy *only enough* fuel to reach that cheaper station.
    - If no cheaper station is reachable, we fill up the tank to maximize the distance we can travel at the current "local minimum" price.

### Why Greedy?
While this problem can be solved with dynamic programming, the greedy approach is more performant for typical long-haul routes (2,000+ miles) and handles the "corridor search" constraints efficiently with O(N) time complexity.

## 3. Data Infrastructure
- **PostGIS**: Used for geographic queries. The fuel station search uses `ST_DWithin` on the route's linestring, combined with GIST indexing for sub-second performance even with thousands of stations.
- **Redis Cache**: Both OSRM routes and geocoding results are cached to ensure that repeated queries (common in user sessions) are instantaneous.

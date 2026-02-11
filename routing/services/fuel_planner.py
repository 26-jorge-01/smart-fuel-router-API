from decimal import Decimal
from django.contrib.gis.geos import LineString
from django.contrib.gis.measure import D
from routing.models import FuelStation
from routing.services.geometry import GeometryService

class FuelPlanner:
    VEHICLE_MPG = 10
    MAX_RANGE_MILES = 500
    TANK_CAPACITY_GALLONS = MAX_RANGE_MILES / VEHICLE_MPG  # 50 gallons

    def __init__(self, route_points_lat_lon, total_distance_meters, corridor_miles=10):
        self.route_points = route_points_lat_lon
        self.total_distance_meters = total_distance_meters
        self.corridor_miles = corridor_miles
        # Precompute route line
        self.route_linestring = GeometryService.point_to_linestring(self.route_points)

    def plan_fuel_stops(self):
        """
        Execute the fuel planning algorithm.
        Returns:
            - stops: List of stop details
            - stats: total_cost, total_gallons
        """
        
        # 1. Fetch Candidate Stations
        # This can be heavy, but ST_DWithin is efficient locally.
        # Ensure we cover the whole route corridor.
        candidates = FuelStation.objects.filter(
            location__dwithin=(self.route_linestring, D(mi=self.corridor_miles))
        ).values(
            'id', 'opis_id', 'name', 'address', 'city', 'state', 'retail_price', 'location'
        )

        # 2. Map candidates to "distance from start"
        # We need to project each station onto the route to know "where" it is linearly.
        # PostGIS ST_LineLocatePoint gives a fraction (0.0 to 1.0).
        # We can do this in Python or DB. DB is cleaner but we already have objects.
        # Let's do a hybrid or DB query annotation for 'fraction'.
        
        # Re-query with annotation is better for accuracy
        candidates_with_pos = FuelStation.objects.filter(
            location__dwithin=(self.route_linestring, D(mi=self.corridor_miles))
        ).annotate(
            fraction=models.Func(
                models.Value(self.route_linestring.wkt),
                models.F('location'),
                function='ST_LineLocatePoint',
                output_field=models.FloatField()
            )
        ).order_by('fraction')

        # Convert queryset to list of dicts for processing
        stations = []
        total_dist_miles = GeometryService.meters_to_miles(self.total_distance_meters)
        
        for cand in candidates_with_pos:
            dist_from_start = cand.fraction * total_dist_miles
            stations.append({
                'obj': cand,
                'dist': dist_from_start,
                'price': float(cand.retail_price),
                'id': cand.opis_id,
            })
            
        # 3. Greedy Algorithm
        current_pos = 0.0
        current_fuel_miles = self.MAX_RANGE_MILES # Start full
        stops = []
        
        # Destination is the conceptual last "station"
        destination_dist = total_dist_miles
        
        while True:
            # Check if we can reach destination
            dist_remaining = destination_dist - current_pos
            if current_fuel_miles >= dist_remaining:
                break # We made it!
            
            # Current max reach
            max_reach = current_pos + current_fuel_miles
            
            # Find reachable stations AHEAD of current_pos
            reachable = [s for s in stations if s['dist'] > current_pos and s['dist'] <= max_reach]
            
            if not reachable:
                # Dead end
                return None, "No stations within range to continue trip."
                
            # Filter reachable to ensure they are not dead ends themselves.
            # (Simple heuristic: look ahead? Or just trust the roadmap implies density?)
            # The prompt asks for: "choose a station that is cheap but also ensures there exists at least one next reachable station"
            
            safe_choices = []
            for cand in reachable:
                # Check feasibility from 'cand'
                cand_reach = cand['dist'] + self.MAX_RANGE_MILES
                if cand_reach >= destination_dist:
                    safe_choices.append(cand)
                    continue
                
                # Check if ANY station exists after cand within range
                next_hop_exists = any(s for s in stations if s['dist'] > cand['dist'] and s['dist'] <= cand_reach)
                if next_hop_exists:
                    safe_choices.append(cand)
            
            if not safe_choices:
                 # If no safe choice, we might still have to pick the furthest one and hope, 
                 # or fail. Requirement says "avoids dead-ends".
                 # If we are strictly blocked, return error.
                 return None, "No safe reachable stations found (dead-end detected)."
                 
            # Strategy: "Find the next reachable station ahead with price lower than current"
            # Since we haven't bought fuel at 'current_pos' (unless it was a previous stop),
            # this logic usually applies *at the pump*.
            # But here we are deciding WHERE to stop.
            # Optimal greedy (simplified):
            # 1. Look for cheapest reachable station.
            # 2. If cheapest is cheaper than "current potential cost" (?? no "current" cost if we are driving),
            #    actually standard strategy is:
            #    - If we can reach a cheaper station than X, go there? 
            #    The prompt says: "At each chosen stop... Find next reachable station ahead with price lower..."
            #    This implies we first CHOOSE a stop, THEN decide how much to buy.
            
            # Correct flow for "Where to stop?":
            # Just pick the cheapest SAFE station within range.
            best_stop = min(safe_choices, key=lambda x: x['price'])
            
            # --- Move to this stop ---
            miles_traveled = best_stop['dist'] - current_pos
            current_fuel_miles -= miles_traveled
            current_pos = best_stop['dist']
            
            # --- At the stop: Decide usage ---
            # Rule: "Find the next reachable station ahead with price lower than current. If exists, buy just enough..."
            # "reachable" here means reachable from THIS stop with a FULL tank (max potential).
            
            # Refetch reachable from NEW current_pos (the stop)
            future_reach_limit = current_pos + self.MAX_RANGE_MILES
            future_stations = [s for s in stations if s['dist'] > current_pos and s['dist'] <= future_reach_limit]
            
            cheaper_target = None
            for fs in future_stations:
                if fs['price'] < best_stop['price']:
                    cheaper_target = fs
                    break # Found the first cheaper one? Or best cheaper one? Usually "first reachable cheaper" avoids carrying heavy fuel.
                    # Prompt says: "Find the next reachable station... If exists, buy just enough to reach that"
            
            gallons_needed = 0
            if cheaper_target:
                dist_to_cheaper = cheaper_target['dist'] - current_pos
                needed_miles = dist_to_cheaper
                # We need 'needed_miles' in tank. We have 'current_fuel_miles'.
                # Buy diff.
                if needed_miles > current_fuel_miles:
                    buy_miles = needed_miles - current_fuel_miles
                    gallons_needed = buy_miles / self.VEHICLE_MPG
                else:
                    gallons_needed = 0 # We have enough to reach the cheaper one
            else:
                # No cheaper station.
                # Fill up to reach success or full.
                # If destination within range of full tank:
                dist_to_dest = destination_dist - current_pos
                if dist_to_dest <= self.MAX_RANGE_MILES:
                     # Buy enough for destination
                     if dist_to_dest > current_fuel_miles:
                         buy_miles = dist_to_dest - current_fuel_miles
                         gallons_needed = buy_miles / self.VEHICLE_MPG
                     else:
                         gallons_needed = 0
                else:
                    # Fill to max
                    space_in_tank = self.TANK_CAPACITY_GALLONS - (current_fuel_miles / self.VEHICLE_MPG)
                    gallons_needed = space_in_tank
            
            # Execute purchase
            cost = gallons_needed * best_stop['price']
            
            stops.append({
                "station_id": best_stop['id'],
                "name": best_stop['obj'].name,
                "address": best_stop['obj'].address,
                "city": best_stop['obj'].city,
                "state": best_stop['obj'].state,
                "lat": best_stop['obj'].location.y,
                "lon": best_stop['obj'].location.x,
                "price_per_gallon": best_stop['price'],
                "miles_from_start": round(current_pos, 1),
                "gallons_purchased": round(gallons_needed, 2),
                "stop_cost": round(cost, 2),
            })
            
            # Update state
            current_fuel_miles += (gallons_needed * self.VEHICLE_MPG)
        
        # Calculate totals
        total_cost = sum(s['stop_cost'] for s in stops)
        total_gallons = sum(s['gallons_purchased'] for s in stops)
        
        return stops, {
            "total_distance_miles": round(destination_dist, 1),
            "total_gallons": round(total_gallons, 2),
            "total_cost": round(total_cost, 2)
        }
        
from django.db import models

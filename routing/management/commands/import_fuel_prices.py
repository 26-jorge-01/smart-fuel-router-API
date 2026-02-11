import csv
import time
import logging
import concurrent.futures
import os
from django.core.management.base import BaseCommand
from routing.models import FuelStation
from routing.services.geocoding import (
    GeocodingRouter, 
    normalize_address_components, 
    clean_piece
)

from dotenv import load_dotenv
load_dotenv()

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = "Import fuel prices and geocode with smart multi-provider routing (Census + Google Maps). Requires GOOGLE_MAPS_API_KEY."

    def add_arguments(self, parser):
        parser.add_argument("--csv", type=str, default="/app/data/fuel-prices-for-be-assessment.csv", help="Path to CSV file")
        parser.add_argument("--sleep", type=float, default=0.1, help="Sleep seconds between requests")
        parser.add_argument("--max", type=int, default=0, help="Max stations to geocode (0 = no limit)")
        parser.add_argument("--concurrent", type=int, default=5, help="Number of worker threads")
        parser.add_argument("--skip_attempted", action="store_true", help="Skip stations that already have geocode_source set")
        parser.add_argument("--provider", type=str, default="smart", choices=["smart", "google_then_census"], help="Provider priority strategy")

    def handle(self, *args, **options):
        csv_path = options["csv"]
        sleep_s = options["sleep"]
        max_n = options["max"]
        max_workers = options["concurrent"]
        skip_attempted = options["skip_attempted"]
        provider_strategy = options["provider"]
        
        # Security Verification & User Notification
        api_key = os.environ.get("GOOGLE_MAPS_API_KEY")
        if not api_key:
            self.stdout.write(self.style.WARNING(
                "NOTICE: GOOGLE_MAPS_API_KEY is missing. "
                "Only US Census geocoder will be used. Highway intersections and single routes may be unresolved. "
                "For full coverage, set GOOGLE_MAPS_API_KEY in your environment."
            ))
        else:
             self.stdout.write(self.style.SUCCESS("✓ GOOGLE_MAPS_API_KEY found. Google Maps Platform enabled."))

        # Initialize Router
        router = GeocodingRouter(provider_priority=provider_strategy)

        self.stdout.write(f"Reading CSV from {csv_path}...")
        stations_to_create = []
        seen_ids = set()

        # 1) Parse CSV
        try:
            with open(csv_path, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    opis_id = int(row["OPIS Truckstop ID"])
                    if opis_id in seen_ids:
                        continue
                    seen_ids.add(opis_id)

                    address, city, state = normalize_address_components(
                        row.get("Address", ""),
                        row.get("City", ""),
                        row.get("State", ""),
                    )

                    station = FuelStation(
                        opis_id=opis_id,
                        name=clean_piece(row.get("Truckstop Name", "")),
                        address=address,
                        city=city,
                        state=state,
                        rack_id=int(row["Rack ID"]) if row.get("Rack ID") else None,
                        retail_price=row.get("Retail Price"),
                    )
                    stations_to_create.append(station)
        except Exception as e:
            self.stderr.write(f"Error reading CSV: {e}")
            return

        # 2) Bulk Insert
        existing_ids = set(FuelStation.objects.values_list("opis_id", flat=True))
        to_insert = [s for s in stations_to_create if s.opis_id not in existing_ids]

        if to_insert:
            FuelStation.objects.bulk_create(to_insert, batch_size=2000)
            self.stdout.write(f"Inserted {len(to_insert)} new records.")
        else:
            self.stdout.write("No new records to insert.")

        # 3) Geocode
        qs = FuelStation.objects.filter(location__isnull=True)
        if skip_attempted:
            qs = qs.filter(geocode_source__isnull=True)
            
        qs = qs.order_by('opis_id')
        station_ids = list(qs.values_list('id', flat=True))
        
        if max_n and max_n > 0:
            station_ids = station_ids[:max_n]
        
        total = len(station_ids)
        self.stdout.write(f"Geocoding {total} stations with {max_workers} workers (Strategy: {provider_strategy})...")

        if total == 0:
            return

        successes = 0
        unresolved = 0
        attempted = 0
        
        def process_station(sid):
            try:
                # Re-fetch only necessary fields if possible, or full object
                s = FuelStation.objects.get(id=sid)
                if sleep_s > 0:
                    time.sleep(sleep_s)
                
                loc, debug = router.geocode_station(s.address, s.city, s.state)
                
                result_source = ""
                success = False
                
                if loc:
                    success = True
                    result_source = f"geocoded:{debug['success_label']}"
                else:
                    success = False
                    result_source = f"unresolved:{debug['classification']}:{debug.get('reason')}"

                return (sid, loc, result_source, debug, success)
            except Exception as e:
                return (sid, None, f"error:{str(e)}", {}, False)

        batch_size = 50
        updated_batch = []

        def save_batch(batch):
            objs = []
            for item in batch:
                sid, loc, src, dbg, _ = item
                s = FuelStation(id=sid)
                s.geocode_source = src
                if loc:
                    s.location = loc
                if hasattr(s, "geocode_meta"):
                    s.geocode_meta = dbg
                objs.append(s)
            
            if objs:
                fields = ["geocode_source", "location"]
                if hasattr(objs[0], "geocode_meta"):
                    fields.append("geocode_meta")
                FuelStation.objects.bulk_update(objs, fields=fields)

        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_sid = {executor.submit(process_station, sid): sid for sid in station_ids}
            
            for future in concurrent.futures.as_completed(future_to_sid):
                attempted += 1
                try:
                    res = future.result()
                    sid, loc, src, dbg, success = res
                    
                    if success:
                        successes += 1
                        self.stdout.write(self.style.SUCCESS(f"✓ {src}"))
                    else:
                        unresolved += 1
                        self.stdout.write(self.style.WARNING(f"✗ {src}"))

                    updated_batch.append(res)

                    if len(updated_batch) >= batch_size:
                        save_batch(updated_batch)
                        updated_batch = []
                    
                    if attempted % 100 == 0:
                        self.stdout.write(f"Progress: {attempted}/{total}")

                except Exception as exc:
                    self.stdout.write(self.style.ERROR(f"Exception: {exc}"))

            if updated_batch:
                save_batch(updated_batch)

        self.stdout.write(self.style.SUCCESS(f"Done. Attempted: {attempted}, Success: {successes}, Unresolved: {unresolved}"))

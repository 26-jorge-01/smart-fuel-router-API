import os
import sys
import unittest.mock
from django.core.management import call_command
from django.conf import settings
from django.contrib.gis.geos import Point

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
import django
django.setup()

from routing.models import FuelStation
try:
    # Create dummy CSV
    with open("fuel_test.csv", "w") as f:
        f.write("OPIS Truckstop ID,Truckstop Name,Address,City,State,Rack ID,Retail Price\n")
        f.write("99999,Test Station,123 Main St,TestCity,FL,100,3.50\n")

    print("Running manual test...")
    
    mock_point = Point(-80.0, 25.0)
    mock_debug = {"success_label": "mock_provider", "classification": "POSTAL_ADDRESS"}
    
    with unittest.mock.patch('routing.management.commands.import_fuel_prices.GeocodingRouter.geocode_station') as mock_geocode:
        mock_geocode.return_value = (mock_point, mock_debug)
        
        call_command('import_fuel_prices', csv="fuel_test.csv")
        
        print(f"Station count: {FuelStation.objects.filter(opis_id=99999).count()}")
        s = FuelStation.objects.get(opis_id=99999)
        print(f"Station source: {s.geocode_source}")
        
    print("Manual test finished successfully.")

except Exception as e:
    import traceback
    traceback.print_exc()
    sys.exit(1)

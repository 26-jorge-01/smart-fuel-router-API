from django.contrib.gis.db import models

class FuelStation(models.Model):
    opis_id = models.IntegerField(help_text="OPIS Truckstop ID")
    name = models.TextField()
    address = models.TextField()
    city = models.TextField()
    state = models.CharField(max_length=2)
    rack_id = models.IntegerField(null=True, blank=True)
    retail_price = models.DecimalField(max_digits=10, decimal_places=3)
    
    # Spatial field
    location = models.PointField(geography=True, null=True, blank=True) # geography=True for better distance calcs
    
    geocode_source = models.CharField(max_length=50, default='census', null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=['state', 'opis_id']),
            models.Index(fields=['opis_id']),
        ]
        # Although opis_id should be unique, the dataset might have duplicates/updates.
        # We'll use ID as primary key and handle opis_id logic in import.

    def __str__(self):
        return f"{self.name} ({self.city}, {self.state})"


class GeocodeCache(models.Model):
    """Cache for geocoding results (e.g., specific addresses or city names)."""
    query_text = models.CharField(max_length=255, unique=True, db_index=True)
    normalized_text = models.CharField(max_length=255, help_text="Lowercased/Stripped for matching")
    location = models.PointField(srid=4326)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.query_text} -> {self.location}"

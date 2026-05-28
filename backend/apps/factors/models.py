import uuid
from django.db import models


class EmissionFactor(models.Model):
    SOURCE_CHOICES = [('DEFRA', 'DEFRA'), ('EPA', 'EPA'), ('CEA', 'CEA'), ('CUSTOM', 'Custom')]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    source = models.CharField(max_length=20, choices=SOURCE_CHOICES)
    vintage_year = models.IntegerField()
    activity_type = models.CharField(max_length=100, db_index=True)
    country_code = models.CharField(max_length=2, null=True, blank=True)
    value = models.DecimalField(max_digits=20, decimal_places=10)
    numerator_unit = models.CharField(max_length=20, default='kgCO2e')
    denominator_unit = models.CharField(max_length=20)
    notes = models.TextField(blank=True)

    class Meta:
        indexes = [
            models.Index(fields=['activity_type', 'country_code', 'vintage_year']),
        ]

    def __str__(self):
        return f"{self.activity_type} ({self.country_code or 'global'}) {self.vintage_year}"


class PlantLookup(models.Model):
    plant_code = models.CharField(max_length=10, primary_key=True)
    name = models.CharField(max_length=255)
    city = models.CharField(max_length=100)
    country_code = models.CharField(max_length=2)

    def __str__(self):
        return f"{self.plant_code} — {self.name}"


class MaterialGroupLookup(models.Model):
    CLASSIFICATION_CHOICES = [
        ('FUEL', 'Fuel'),
        ('NON_FUEL', 'Non-Fuel'),
        ('UNKNOWN', 'Unknown'),
    ]
    code = models.CharField(max_length=50, primary_key=True)
    description = models.CharField(max_length=255)
    classification = models.CharField(max_length=20, choices=CLASSIFICATION_CHOICES)
    fuel_type = models.CharField(max_length=50, null=True, blank=True)

    def __str__(self):
        return f"{self.code} — {self.description}"


class UoMConversion(models.Model):
    from_unit = models.CharField(max_length=10)
    material_type = models.CharField(max_length=50, null=True, blank=True)
    to_unit = models.CharField(max_length=10)
    multiplier = models.DecimalField(max_digits=20, decimal_places=10)

    class Meta:
        unique_together = ('from_unit', 'material_type', 'to_unit')

    def __str__(self):
        return f"{self.from_unit} ({self.material_type}) → {self.to_unit} ×{self.multiplier}"


class AirportLookup(models.Model):
    iata_code = models.CharField(max_length=3, primary_key=True)
    name = models.CharField(max_length=255)
    city = models.CharField(max_length=100)
    country_code = models.CharField(max_length=2)
    latitude = models.DecimalField(max_digits=10, decimal_places=6)
    longitude = models.DecimalField(max_digits=10, decimal_places=6)

    def __str__(self):
        return f"{self.iata_code} — {self.name}"

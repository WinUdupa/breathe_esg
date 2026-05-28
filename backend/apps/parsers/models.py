import uuid
from django.db import models
from apps.ingestion.models import IngestionBatch


class RawActivityRow(models.Model):
    PARSE_STATUS_CHOICES = [('OK', 'OK'), ('PARSE_ERROR', 'Parse Error')]
    CLASSIFICATION_CHOICES = [
        ('FUEL', 'Fuel'),
        ('NON_FUEL', 'Non-Fuel'),
        ('ELECTRICITY', 'Electricity'),
        ('TRAVEL_FLIGHT', 'Travel Flight'),
        ('TRAVEL_HOTEL', 'Travel Hotel'),
        ('TRAVEL_GROUND', 'Travel Ground'),
        ('OUT_OF_SCOPE', 'Out of Scope'),
        ('PENDING', 'Pending'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    batch = models.ForeignKey(IngestionBatch, on_delete=models.CASCADE, related_name='rows')
    row_number = models.IntegerField()
    raw_data = models.JSONField()
    parse_status = models.CharField(max_length=20, choices=PARSE_STATUS_CHOICES, default='OK')
    parse_error = models.TextField(blank=True)
    classification = models.CharField(max_length=20, choices=CLASSIFICATION_CHOICES, default='PENDING')

    class Meta:
        indexes = [
            models.Index(fields=['batch', 'parse_status']),
            models.Index(fields=['batch', 'classification']),
        ]

    def __str__(self):
        return f"Row {self.row_number} of batch {self.batch_id}"

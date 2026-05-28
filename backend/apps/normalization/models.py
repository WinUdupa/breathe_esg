import uuid
from django.db import models
from django.contrib.auth.models import User
from apps.clients.models import Client, ReportingPeriod
from apps.ingestion.models import IngestionBatch
from apps.parsers.models import RawActivityRow
from apps.factors.models import EmissionFactor


class NormalizedActivity(models.Model):
    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('FLAGGED', 'Flagged'),
        ('ACCEPTED', 'Accepted'),
        ('REJECTED', 'Rejected'),
        ('LOCKED', 'Locked'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    raw_row = models.OneToOneField(RawActivityRow, on_delete=models.CASCADE, related_name='normalized')
    client = models.ForeignKey(Client, on_delete=models.CASCADE, related_name='normalized_activities')
    batch = models.ForeignKey(IngestionBatch, on_delete=models.CASCADE, related_name='normalized_rows')
    source_type = models.CharField(max_length=20)
    reporting_period = models.ForeignKey(
        ReportingPeriod, null=True, blank=True, on_delete=models.SET_NULL, related_name='activities'
    )
    scope = models.IntegerField()
    scope_3_category = models.IntegerField(null=True, blank=True)
    activity_subtype = models.CharField(max_length=50)

    raw_quantity = models.CharField(max_length=50, blank=True)
    raw_unit = models.CharField(max_length=20, blank=True)
    raw_date_text = models.CharField(max_length=50, blank=True)
    raw_location_code = models.CharField(max_length=50, blank=True)

    activity_period_start = models.DateField(null=True, blank=True)
    activity_period_end = models.DateField(null=True, blank=True)

    normalized_quantity = models.DecimalField(max_digits=20, decimal_places=6, null=True, blank=True)
    normalized_unit = models.CharField(max_length=20, blank=True)
    resolved_location = models.CharField(max_length=255, blank=True)
    resolved_country_code = models.CharField(max_length=2, blank=True)
    resolved_material_name = models.CharField(max_length=255, blank=True)
    resolved_material_category = models.CharField(max_length=100, blank=True)

    emission_factor = models.ForeignKey(
        EmissionFactor, null=True, blank=True, on_delete=models.SET_NULL, related_name='activities'
    )
    co2e_kg = models.DecimalField(max_digits=20, decimal_places=6, null=True, blank=True)
    conversion_display = models.CharField(max_length=500, blank=True)
    co2e_display = models.CharField(max_length=500, blank=True)

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    flags = models.JSONField(default=list)
    flag_summary = models.TextField(blank=True)

    reviewed_by = models.ForeignKey(
        User, null=True, blank=True, on_delete=models.SET_NULL, related_name='reviewed_rows'
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)
    review_note = models.TextField(blank=True)
    locked_at = models.DateTimeField(null=True, blank=True)
    is_edited = models.BooleanField(default=False)
    edit_history = models.JSONField(default=list)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=['client', 'status']),
            models.Index(fields=['client', 'scope']),
            models.Index(fields=['batch', 'status']),
            models.Index(fields=['batch', 'scope']),
        ]

    def __str__(self):
        return f"{self.activity_subtype} row {self.raw_row.row_number} ({self.status})"

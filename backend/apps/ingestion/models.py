import uuid
from django.db import models
from django.contrib.auth.models import User
from apps.clients.models import Client


class Submission(models.Model):
    STATUS_CHOICES = [
        ('OPEN', 'Open'),
        ('PENDING_REVIEW', 'Pending Review'),
        ('IN_REVIEW', 'In Review'),
        ('ANALYST_APPROVED', 'Analyst Approved'),
        ('FINALIZED', 'Finalized'),
        ('REJECTED', 'Rejected'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    client = models.ForeignKey(Client, on_delete=models.CASCADE, related_name='submissions')
    batch_number = models.PositiveIntegerField()
    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default='OPEN')
    created_by = models.ForeignKey(
        User, null=True, on_delete=models.SET_NULL, related_name='submissions_created'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    submitted_at = models.DateTimeField(null=True, blank=True)
    reviewed_by = models.ForeignKey(
        User, null=True, blank=True, on_delete=models.SET_NULL, related_name='submissions_reviewed'
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)
    analyst_note = models.TextField(blank=True)
    finalized_by = models.ForeignKey(
        User, null=True, blank=True, on_delete=models.SET_NULL, related_name='submissions_finalized'
    )
    finalized_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']
        unique_together = [('client', 'batch_number')]

    def __str__(self):
        return f"Batch #{self.batch_number} ({self.status})"


class IngestionBatch(models.Model):
    SOURCE_CHOICES = [('SAP', 'SAP'), ('UTILITY', 'Utility'), ('TRAVEL', 'Travel')]
    STATUS_CHOICES = [
        ('PROCESSING', 'Processing'),
        ('FAILED', 'Failed'),
        ('PENDING_REVIEW', 'Pending Review'),
        ('IN_REVIEW', 'In Review'),
        ('ANALYST_APPROVED', 'Analyst Approved'),
        ('FINALIZED', 'Finalized'),
        ('REJECTED', 'Rejected'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    client = models.ForeignKey(Client, on_delete=models.CASCADE, related_name='batches')
    submission = models.ForeignKey(
        Submission, null=True, blank=True, on_delete=models.CASCADE, related_name='files'
    )
    source_type = models.CharField(max_length=10, choices=SOURCE_CHOICES)
    uploaded_by = models.ForeignKey(User, null=True, on_delete=models.SET_NULL, related_name='uploads')
    uploaded_at = models.DateTimeField(auto_now_add=True)
    file_name = models.CharField(max_length=255)
    file_path = models.CharField(max_length=500)
    file_hash = models.CharField(max_length=64)
    file_size_bytes = models.BigIntegerField()
    row_count = models.IntegerField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PROCESSING')
    error_log = models.JSONField(default=list)
    reviewed_by = models.ForeignKey(
        User, null=True, blank=True, on_delete=models.SET_NULL, related_name='reviewed_batches'
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)
    analyst_note = models.TextField(blank=True)
    finalized_by = models.ForeignKey(
        User, null=True, blank=True, on_delete=models.SET_NULL, related_name='finalized_batches'
    )
    finalized_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = ('client', 'file_hash')
        ordering = ['-uploaded_at']

    def __str__(self):
        return f"{self.source_type} — {self.file_name} ({self.status})"

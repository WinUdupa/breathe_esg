import uuid
from django.db import models
from django.contrib.auth.models import User
from apps.clients.models import Client


class AuditLog(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    timestamp = models.DateTimeField(auto_now_add=True)
    actor = models.ForeignKey(User, null=True, on_delete=models.SET_NULL, related_name='audit_logs')
    client = models.ForeignKey(Client, null=True, on_delete=models.SET_NULL, related_name='audit_logs')
    action = models.CharField(max_length=60)
    target_type = models.CharField(max_length=50, blank=True)
    target_id = models.CharField(max_length=100, blank=True)
    detail = models.JSONField(default=dict)

    class Meta:
        ordering = ['-timestamp']

    def __str__(self):
        return f"{self.action} by {self.actor} at {self.timestamp}"

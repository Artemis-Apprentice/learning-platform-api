from django.db import models
from django.contrib.auth.models import User
import uuid

class PocJob(models.Model):
    """
    Minimal job model for POC testing.
    Just tracks job ID, status, and message.
    """
    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('IN_PROGRESS', 'In Progress'),
        ('COMPLETED', 'Completed'),
        ('FAILED', 'Failed'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    message_data = models.JSONField(default=dict)  # Store the message we sent
    result_data = models.JSONField(default=dict, blank=True)  # Store consumer results
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'poc_jobs'
        ordering = ['-created_at']

    def __str__(self):
        return f"POC Job {self.id} - {self.status}"

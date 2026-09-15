# guest_sessions/models.py

from django.db import models
from core.models import BaseModel
from django.utils import timezone


class GuestSession(BaseModel):
    """
    Represents a guest's session in the system.
    Used to track anonymous or authenticated users across bookings and orders.
    """
    SESSION_STATUS_CHOICES = [
        ('active', 'Active'),
        ('expired', 'Expired'),
        ('completed', 'Completed'),
    ]

    user = models.ForeignKey(
        'users.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='guest_sessions',
        help_text="Authenticated user (null for anonymous)"
    )
    venue = models.ForeignKey(
        'venues.Venue',
        on_delete=models.CASCADE,
        related_name='guest_sessions',
        help_text="Venue where the session was initiated"
    )
    session_token = models.CharField(
        max_length=255,
        unique=True,
        help_text="Unique token for anonymous session (UUID or JWT)"
    )
    status = models.CharField(
        max_length=20,
        choices=SESSION_STATUS_CHOICES,
        default='active',
    )
    start_time = models.DateTimeField(default=timezone.now)
    end_time = models.DateTimeField(null=True, blank=True)

    # Optional fields for future use
    device_fingerprint = models.CharField(max_length=255, blank=True, null=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)

    # Settlement tracking (NEW)
    is_settled = models.BooleanField(
        default=False,
        help_text="Whether the guest session (and its table) is fully settled"
    )
    settled_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'guest_sessions'
        ordering = ['-start_time']

    def __str__(self):
        return f"Session {self.id} - {self.venue.business_name}"

    def is_active(self):
        return self.status == 'active'

    def expire(self):
        self.status = 'expired'
        self.end_time = timezone.now()
        self.save()

    def mark_settled(self):
        """Mark the session as settled."""
        self.is_settled = True
        self.settled_at = timezone.now()
        self.save(update_fields=['is_settled', 'settled_at'])
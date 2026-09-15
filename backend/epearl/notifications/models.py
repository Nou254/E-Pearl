# notifications/models.py

from django.db import models
from core.models import BaseModel
from django.utils import timezone


class NotificationTemplate(BaseModel):
    """
    Predefined templates for notifications.
    """
    CHANNEL_CHOICES = [
        ('email', 'Email'),
        ('sms', 'SMS'),
        ('push', 'Push Notification'),
    ]

    name = models.CharField(max_length=100, unique=True, help_text="e.g., booking_confirmation")
    channel = models.CharField(max_length=20, choices=CHANNEL_CHOICES)
    subject = models.CharField(max_length=255, blank=True, null=True, help_text="For email")
    body_template = models.TextField(help_text="Use {{ placeholders }} for dynamic content")
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = 'notification_templates'

    def __str__(self):
        return f"{self.name} ({self.channel})"


class Notification(BaseModel):
    """
    Individual notification record.
    """
    CHANNEL_CHOICES = [
        ('email', 'Email'),
        ('sms', 'SMS'),
        ('push', 'Push'),
    ]
    TYPE_CHOICES = [
        ('booking_confirmation', 'Booking Confirmation'),
        ('booking_cancellation', 'Booking Cancellation'),
        ('order_ready', 'Order Ready'),
        ('payment_success', 'Payment Success'),
        ('payment_failed', 'Payment Failed'),
        ('no_show_alert', 'No-Show Alert'),
        ('staff_cash_outstanding', 'Staff Cash Outstanding'),
        ('vip_arrived', 'VIP Arrived'),
        ('shift_reminder', 'Shift Reminder'),
        ('welcome', 'Welcome'),
        ('ticket_confirmation', 'Ticket Confirmation'),
    ]
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('sent', 'Sent'),
        ('failed', 'Failed'),
        ('retry', 'Retry'),
    ]

    venue = models.ForeignKey(
        'venues.Venue',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='notifications'
    )
    recipient_user = models.ForeignKey(
        'users.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='notifications'
    )
    recipient_email = models.EmailField(null=True, blank=True)
    recipient_phone = models.CharField(max_length=20, null=True, blank=True)

    notification_type = models.CharField(max_length=50, choices=TYPE_CHOICES)
    channel = models.CharField(max_length=20, choices=CHANNEL_CHOICES)
    subject = models.CharField(max_length=255, blank=True, null=True)
    body = models.TextField()
    metadata = models.JSONField(default=dict, blank=True)

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    error_message = models.TextField(blank=True, null=True)
    sent_at = models.DateTimeField(null=True, blank=True)
    retry_count = models.PositiveIntegerField(default=0)

    class Meta:
        db_table = 'notifications'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.notification_type} to {self.recipient_email or self.recipient_phone or self.recipient_user}"
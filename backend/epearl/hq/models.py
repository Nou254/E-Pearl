# hq/models.py

from django.db import models
from core.models import BaseModel
from django.utils import timezone
from django.contrib.postgres.search import SearchVectorField
from django.contrib.postgres.indexes import GinIndex


# =============================================================================
# Soft Delete Manager
# =============================================================================

class SoftDeleteManager(models.Manager):
    """Manager that filters out soft-deleted records by default."""
    def get_queryset(self):
        return super().get_queryset().filter(is_deleted=False)

    def all_with_deleted(self):
        """Return all records including soft-deleted ones."""
        return super().get_queryset()

    def deleted_only(self):
        """Return only soft-deleted records."""
        return super().get_queryset().filter(is_deleted=True)


# =============================================================================
# Existing models
# =============================================================================

class PlatformSetting(BaseModel):
    SETTING_TYPE = [
        ('string', 'String'),
        ('integer', 'Integer'),
        ('boolean', 'Boolean'),
        ('json', 'JSON'),
    ]
    setting_key = models.CharField(max_length=100, unique=True)
    setting_value = models.TextField()
    setting_type = models.CharField(max_length=50, choices=SETTING_TYPE, default='string')
    description = models.TextField(blank=True, null=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.setting_key


class SMSCredit(BaseModel):
    venue = models.ForeignKey('venues.Venue', on_delete=models.CASCADE, related_name='sms_credits')
    initial_credits = models.PositiveIntegerField()
    credits_used = models.PositiveIntegerField(default=0)
    credits_remaining = models.PositiveIntegerField()
    last_top_up = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.venue.business_name} - {self.credits_remaining} credits"


class APIKey(BaseModel):
    venue = models.ForeignKey('venues.Venue', on_delete=models.CASCADE, related_name='api_keys')
    name = models.CharField(max_length=255)
    api_key_hash = models.CharField(max_length=255)
    permissions = models.JSONField(default=dict, blank=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    last_used = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"API Key {self.name} - {self.venue.business_name}"


# =============================================================================
# Monitoring, Logging, Billing, Feature Flags
# =============================================================================

class ServiceStatus(BaseModel):
    SERVICE_TYPES = [
        ('mpesa', 'M-Pesa Daraja API'),
        ('card_gateway', 'Card Gateway (Pesapal/Flutterwave)'),
        ('sms_gateway', 'SMS Gateway'),
        ('email_service', 'Email Service'),
        ('redis', 'Redis Cache'),
        ('database', 'PostgreSQL Database'),
    ]
    STATUS_CHOICES = [
        ('operational', 'Operational'),
        ('degraded', 'Degraded'),
        ('offline', 'Offline'),
        ('maintenance', 'Maintenance'),
    ]

    service = models.CharField(max_length=50, choices=SERVICE_TYPES, unique=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='operational')
    response_time_ms = models.FloatField(null=True, blank=True)
    last_checked = models.DateTimeField(auto_now=True)
    error_message = models.TextField(blank=True, null=True)

    class Meta:
        db_table = 'hq_service_status'
        ordering = ['service']

    def __str__(self):
        return f"{self.get_service_display()}: {self.get_status_display()}"


class RequestLog(BaseModel):
    """
    Logs every API request for analytics and debugging.
    Supports soft delete: records can be restored within 90 days.
    """
    user = models.ForeignKey('users.User', on_delete=models.SET_NULL, null=True, blank=True)
    venue = models.ForeignKey('venues.Venue', on_delete=models.SET_NULL, null=True, blank=True)
    method = models.CharField(max_length=10)
    path = models.CharField(max_length=500)
    endpoint = models.CharField(max_length=255)
    status_code = models.PositiveIntegerField()
    response_time_ms = models.FloatField()
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True, null=True)
    request_body = models.JSONField(default=dict, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    # Soft delete fields
    is_deleted = models.BooleanField(default=False)
    deleted_at = models.DateTimeField(null=True, blank=True)

    # Full‑text search vector (PostgreSQL)
    search_vector = SearchVectorField(null=True, blank=True)

    # Custom manager
    objects = SoftDeleteManager()
    all_objects = models.Manager()  # includes soft-deleted

    class Meta:
        db_table = 'hq_request_logs'
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['timestamp']),
            models.Index(fields=['venue']),
            models.Index(fields=['status_code']),
            models.Index(fields=['is_deleted']),
            GinIndex(fields=['search_vector']),
        ]

    def __str__(self):
        return f"{self.method} {self.path} - {self.status_code}"

    def soft_delete(self):
        """Soft delete the record."""
        self.is_deleted = True
        self.deleted_at = timezone.now()
        self.save(update_fields=['is_deleted', 'deleted_at'])

    def restore(self):
        """Restore a soft-deleted record."""
        self.is_deleted = False
        self.deleted_at = None
        self.save(update_fields=['is_deleted', 'deleted_at'])

    def hard_delete(self):
        """Permanently delete the record."""
        self.delete()


class FeatureFlag(BaseModel):
    venue = models.ForeignKey('venues.Venue', on_delete=models.CASCADE, related_name='feature_flags')
    feature_code = models.CharField(max_length=100)
    is_enabled = models.BooleanField(default=False)
    description = models.TextField(blank=True, null=True)

    class Meta:
        db_table = 'hq_feature_flags'
        unique_together = ['venue', 'feature_code']

    def __str__(self):
        return f"{self.venue.business_name}: {self.feature_code} = {self.is_enabled}"


class Subscription(BaseModel):
    venue = models.OneToOneField('venues.Venue', on_delete=models.CASCADE, related_name='subscription')
    tier = models.CharField(max_length=50, default='seed')
    billing_cycle_start = models.DateField(default=timezone.now)
    last_billing_date = models.DateField(null=True, blank=True)
    next_billing_date = models.DateField(null=True, blank=True)
    arrears = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    is_active = models.BooleanField(default=True)
    payment_method_token = models.TextField(blank=True, null=True)

    class Meta:
        db_table = 'hq_subscriptions'

    def __str__(self):
        return f"Subscription: {self.venue.business_name} ({self.tier})"
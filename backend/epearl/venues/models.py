# venues/models.py

from django.db import models
from core.models import BaseModel


class Venue(BaseModel):
    """
    Represents a registered venue (restaurant, bar, hotel, etc.)
    """
    SUBSCRIPTION_TIERS = [
        ('seed', 'Seed'),
        ('spark', 'Spark'),
        ('rose', 'Rose'),
        ('summit', 'Summit'),
        ('elite', 'Elite'),
        ('legacy', 'Legacy'),
    ]
    SUBSCRIPTION_STATUS = [
        ('trial', 'Trial'),
        ('active', 'Active'),
        ('suspended', 'Suspended'),
        ('cancelled', 'Cancelled'),
    ]
    DOCUMENT_STATUS = [
        ('pending', 'Pending'),
        ('verified', 'Verified'),
        ('rejected', 'Rejected'),
    ]
    DEPOSIT_TYPES = [
        ('percentage', 'Percentage'),
        ('fixed', 'Fixed Amount'),
    ]

    # ---------- Core Business Information ----------
    business_name = models.CharField(max_length=255)
    registration_number = models.CharField(
        max_length=100,
        unique=True,
        null=True,
        blank=True
    )
    kra_pin = models.CharField(
        max_length=50,
        unique=True
    )
    contact_phone = models.CharField(max_length=20)
    contact_email = models.EmailField(max_length=255)
    physical_address = models.TextField(blank=True, null=True)
    gps_coordinates = models.CharField(max_length=100, blank=True, null=True)
    sub_domain = models.CharField(max_length=100, unique=True)

    # ---------- Subscription & Billing ----------
    subscription_tier = models.CharField(max_length=50, choices=SUBSCRIPTION_TIERS, default='seed')
    subscription_status = models.CharField(max_length=50, choices=SUBSCRIPTION_STATUS, default='trial')
    billing_cycle_start = models.DateField(null=True, blank=True)
    next_billing_date = models.DateField(null=True, blank=True)
    trial_start_date = models.DateField(null=True, blank=True)
    tax_rate = models.DecimalField(max_digits=5, decimal_places=2, default=16.00)
    currency = models.CharField(max_length=3, default='KES')

    # ---------- Public Profile (Explore) ----------
    public_listing = models.BooleanField(default=False)
    operating_hours = models.JSONField(default=dict, blank=True)
    description = models.TextField(blank=True, null=True)
    cover_image_url = models.CharField(max_length=255, blank=True, null=True)
    logo_url = models.CharField(max_length=255, blank=True, null=True)

    # ---------- KYC Documents ----------
    documents = models.JSONField(default=dict, blank=True)
    document_verification_status = models.CharField(
        max_length=50, choices=DOCUMENT_STATUS, default='pending'
    )

    # ---------- Owner (Legal) ----------
    owner = models.ForeignKey(
        'users.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='venues'
    )

    # ---------- Booking & Cancellation Rules (for Explore) ----------
    booking_deposit_type = models.CharField(
        max_length=20,
        choices=DEPOSIT_TYPES,
        default='percentage',
        help_text="Whether deposit is a percentage of total or a fixed amount."
    )
    booking_deposit_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=10.00,
        help_text="Percentage (e.g., 20.00) or fixed amount (e.g., 1000.00)."
    )
    booking_cancellation_hours = models.PositiveIntegerField(
        default=24,
        help_text="Free cancellation window in hours before booking time."
    )
    table_booking_advance_days = models.PositiveIntegerField(
        default=7,
        help_text="How many days in advance a table can be booked."
    )
    max_party_size = models.PositiveIntegerField(
        null=True, blank=True,
        help_text="Global maximum party size (overrides table capacity). Leave blank for no limit."
    )
    min_hire_period_hours = models.PositiveIntegerField(
        default=4,
        help_text="Minimum hire duration in hours for full venue hire."
    )
    hire_blackout_dates = models.JSONField(
        default=list, blank=True,
        help_text="List of dates (ISO format) when the venue is not available for hire."
    )

    # ---------- Owner Verification & Legal Details ----------
    legal_owner_name = models.CharField(max_length=255, blank=True, null=True)
    legal_owner_email = models.EmailField(blank=True, null=True)
    legal_owner_phone = models.CharField(max_length=20, blank=True, null=True)
    owner_verified_at = models.DateTimeField(null=True, blank=True)
    owner_invitation_sent_at = models.DateTimeField(null=True, blank=True)
    owner_invitation_token = models.CharField(max_length=255, blank=True, null=True)
    auto_capture_enabled = models.BooleanField(default=False)

    # ---------- Refund Policy (one-to-one) ----------
    # FIXED: changed related_name to avoid clash with VenueRefundPolicy.venue field
    refund_policy = models.OneToOneField(
        'VenueRefundPolicy',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='venue_refund_policy'  # <-- UNIQUE NAME
    )

    def __str__(self):
        return self.business_name

    def is_active(self):
        return self.subscription_status in ['trial', 'active']

    # ---------- Tier helper methods ----------
    def can_add_table(self):
        from .services.tier_service import TierService
        return TierService.can_add_table(self)

    def can_add_staff(self):
        from .services.tier_service import TierService
        return TierService.can_add_staff(self)

    def has_module(self, module_name):
        from .services.tier_service import TierService
        return TierService.has_module_access(self, module_name)

    def get_tier_dashboard(self):
        from .services.tier_service import TierService
        return TierService.get_usage_dashboard(self)


class VenueRefundPolicy(BaseModel):
    """
    Defines refund and cancellation policy for a venue.
    """
    CANCELLATION_POLICY_CHOICES = [
        ('flexible', 'Flexible'),
        ('moderate', 'Moderate'),
        ('strict', 'Strict'),
    ]

    venue = models.OneToOneField(
        Venue,
        on_delete=models.CASCADE,
        related_name='refund_policy_config'  # reverse name to avoid conflict with OneToOneField above
    )

    cancellation_policy = models.CharField(
        max_length=20,
        choices=CANCELLATION_POLICY_CHOICES,
        default='flexible'
    )
    full_refund_window_hours = models.PositiveIntegerField(
        default=48,
        help_text="Hours before booking start for 100% refund"
    )
    partial_refund_window_hours = models.PositiveIntegerField(
        default=24,
        help_text="Hours before booking start for partial refund (will apply partial percentage)"
    )
    partial_refund_percentage = models.DecimalField(
        max_digits=5, decimal_places=2, default=50.00,
        help_text="Percentage to refund during the partial window (e.g., 50.00 for 50%)"
    )
    no_show_charge_percentage = models.DecimalField(
        max_digits=5, decimal_places=2, default=100.00,
        help_text="Percentage charged for no-show (e.g., 100.00 means full charge)"
    )
    venue_cancellation_refund = models.BooleanField(
        default=True,
        help_text="If venue cancels, refund 100%"
    )
    rescheduling_allowed = models.BooleanField(default=True)
    rescheduling_fee = models.DecimalField(
        max_digits=10, decimal_places=2, default=0.00,
        help_text="Fee for rescheduling (0 = free)"
    )
    force_majeure_policy = models.TextField(
        blank=True, null=True,
        help_text="Custom policy for force majeure events"
    )

    class Meta:
        db_table = 'venue_refund_policies'

    def __str__(self):
        return f"Refund policy for {self.venue.business_name}"
# payments/models.py

from django.db import models
from core.models import BaseModel
from django.utils import timezone
import uuid


class PaymentGatewayConfig(BaseModel):
    """
    Stores encrypted payment gateway credentials per venue.
    """
    GATEWAY_PROVIDERS = [
        ('daraja', 'M-Pesa Daraja'),
        ('flutterwave', 'Flutterwave'),
        ('pesapal', 'Pesapal'),
        ('paystack', 'Paystack'),
    ]
    ENVIRONMENTS = [
        ('sandbox', 'Sandbox'),
        ('production', 'Production'),
    ]
    STATUS_CHOICES = [
        ('inactive', 'Inactive'),
        ('active', 'Active'),
        ('failed', 'Failed'),
    ]

    venue = models.OneToOneField(
        'venues.Venue',
        on_delete=models.CASCADE,
        related_name='payment_config'
    )
    gateway_provider = models.CharField(max_length=50, choices=GATEWAY_PROVIDERS)
    merchant_id = models.CharField(max_length=255, blank=True, null=True)
    consumer_key = models.TextField(blank=True, null=True, help_text="Encrypted Consumer Key")
    consumer_secret = models.TextField(blank=True, null=True, help_text="Encrypted Consumer Secret")
    passkey = models.TextField(blank=True, null=True, help_text="Encrypted Passkey")
    shortcode = models.CharField(max_length=50, blank=True, null=True, help_text="Paybill or Till number")
    environment = models.CharField(max_length=20, choices=ENVIRONMENTS, default='sandbox')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='inactive')
    last_tested = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.venue.business_name} - {self.gateway_provider} ({self.environment})"

    class Meta:
        db_table = 'payment_gateway_configs'
        verbose_name = 'Payment Gateway Config'
        verbose_name_plural = 'Payment Gateway Configs'


class Transaction(BaseModel):
    """
    Core financial record. Links to all modules (Booking, Ticket, Order, etc.).
    Now includes refund tracking fields.
    """
    TRANSACTION_TYPES = [
        ('hold', 'Pre-Authorization Hold'),
        ('capture', 'Capture'),
        ('void', 'Void'),
        ('top_up', 'Top Up'),
        ('refund', 'Refund'),
        ('payment', 'Direct Payment'),
        ('deposit', 'Deposit'),
        ('withdrawal', 'Withdrawal'),
    ]
    PAYMENT_METHODS = [
        ('mpesa', 'M-Pesa'),
        ('card', 'Card'),
        ('cash', 'Cash'),
    ]
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('success', 'Success'),
        ('failed', 'Failed'),
        ('reversed', 'Reversed'),
    ]
    REFUND_STATUS_CHOICES = [
        ('none', 'No Refund'),
        ('partial', 'Partial Refund'),
        ('full', 'Full Refund'),
    ]

    venue = models.ForeignKey(
        'venues.Venue',
        on_delete=models.CASCADE,
        related_name='transactions'
    )
    guest_session = models.ForeignKey(
        'guest_sessions.GuestSession',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='transactions'
    )
    user = models.ForeignKey(
        'users.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='transactions'
    )

    # Polymorphic links to other modules
    booking = models.ForeignKey(
        'explore.Booking',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='transactions'
    )
    ticket = models.ForeignKey(
        'events.Ticket',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='transactions'
    )
    pre_auth_hold = models.ForeignKey(
        'PreAuthHold',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='transactions'
    )
    order = models.ForeignKey(
        'orders.Order',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='transactions'
    )

    transaction_type = models.CharField(max_length=20, choices=TRANSACTION_TYPES)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=3, default='KES')
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHODS)

    gateway_reference_id = models.CharField(max_length=255, blank=True, null=True)
    gateway_response_code = models.CharField(max_length=50, blank=True, null=True)
    gateway_response_message = models.TextField(blank=True, null=True)

    transaction_status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    transaction_time = models.DateTimeField(default=timezone.now)

    # Metadata
    metadata = models.JSONField(default=dict, blank=True)

    # Idempotency & analytics
    idempotency_key = models.CharField(max_length=255, unique=True, null=True, blank=True)
    gateway_latency_ms = models.PositiveIntegerField(null=True, blank=True)
    retry_count = models.PositiveSmallIntegerField(default=0)

    # ----- NEW REFUND FIELDS -----
    refund_status = models.CharField(
        max_length=20,
        choices=REFUND_STATUS_CHOICES,
        default='none',
        help_text="Status of any refund applied to this transaction"
    )
    amount_refunded = models.DecimalField(
        max_digits=10, decimal_places=2, default=0,
        help_text="Total amount refunded so far"
    )

    def __str__(self):
        return f"{self.transaction_type} - {self.amount} {self.currency} ({self.transaction_status})"

    class Meta:
        db_table = 'transactions'
        ordering = ['-transaction_time']


class PreAuthHold(BaseModel):
    """
    Tracks pre-authorization holds for Host mode.
    """
    HOLD_STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('active', 'Active'),
        ('captured', 'Captured'),
        ('voided', 'Voided'),
        ('expired', 'Expired'),
        ('failed', 'Failed'),
    ]
    PAYMENT_METHODS = [
        ('card', 'Card'),
        ('mpesa', 'M-Pesa'),
    ]

    venue = models.ForeignKey(
        'venues.Venue',
        on_delete=models.CASCADE,
        related_name='pre_auth_holds'
    )
    guest_session = models.ForeignKey(
        'guest_sessions.GuestSession',
        on_delete=models.CASCADE,
        related_name='pre_auth_holds'
    )
    declared_amount = models.DecimalField(max_digits=10, decimal_places=2)
    consumed_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    remaining_balance = models.DecimalField(max_digits=10, decimal_places=2)
    hold_status = models.CharField(max_length=20, choices=HOLD_STATUS_CHOICES, default='pending')
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHODS)
    gateway_reference_id = models.CharField(max_length=255, blank=True, null=True)
    payment_token = models.TextField(blank=True, null=True, help_text="Tokenized payment reference")
    hold_time = models.DateTimeField(default=timezone.now)
    capture_time = models.DateTimeField(null=True, blank=True)
    void_time = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"Hold {self.id} - {self.declared_amount} ({self.hold_status})"

    def is_active(self):
        return self.hold_status == 'active'

    def can_capture(self):
        return self.hold_status in ['pending', 'active']

    def capture(self):
        self.hold_status = 'captured'
        self.capture_time = timezone.now()
        self.save()

    def void(self):
        self.hold_status = 'voided'
        self.void_time = timezone.now()
        self.save()

    class Meta:
        db_table = 'pre_auth_holds'
        ordering = ['-hold_time']


class WebhookLog(BaseModel):
    """
    Records incoming webhooks from payment gateways.
    """
    venue = models.ForeignKey(
        'venues.Venue',
        on_delete=models.CASCADE,
        related_name='webhook_logs'
    )
    provider = models.CharField(max_length=50)
    event_type = models.CharField(max_length=100)
    payload = models.JSONField()
    signature = models.TextField(blank=True, null=True)
    is_verified = models.BooleanField(default=False)
    is_processed = models.BooleanField(default=False)
    processed_at = models.DateTimeField(null=True, blank=True)
    error_message = models.TextField(blank=True, null=True)
    received_at = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return f"{self.provider} - {self.event_type} ({self.received_at})"

    class Meta:
        db_table = 'webhook_logs'
        ordering = ['-received_at']


# ========== NEW REFUND MODELS ==========

class RefundRequest(BaseModel):
    """
    Represents a request for a refund initiated by a customer or venue.
    """
    REASON_CHOICES = [
        ('venue_cancelled', 'Venue Cancelled'),
        ('venue_failed_service', 'Venue Failed to Provide Service'),
        ('customer_cancellation', 'Customer Changed Mind'),
        ('technical_issue', 'Technical Issue / Double Charge'),
        ('other', 'Other'),
    ]
    CLASSIFICATION_CHOICES = [
        ('venue_fault', 'Venue Fault'),
        ('nou_fault', 'N.O.U. Fault'),
        ('gateway_issue', 'Payment Gateway Issue'),
        ('customer_cancellation', 'Customer Cancellation'),
    ]
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('processing', 'Processing'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
    ]

    booking = models.ForeignKey(
        'explore.Booking',
        on_delete=models.CASCADE,
        related_name='refund_requests'
    )
    transaction = models.ForeignKey(
        Transaction,
        on_delete=models.CASCADE,
        related_name='refund_requests'
    )
    customer = models.ForeignKey(
        'users.User',
        on_delete=models.CASCADE,
        related_name='refund_requests'
    )
    venue = models.ForeignKey(
        'venues.Venue',
        on_delete=models.CASCADE,
        related_name='refund_requests'
    )

    reason = models.CharField(max_length=50, choices=REASON_CHOICES)
    classification = models.CharField(max_length=50, choices=CLASSIFICATION_CHOICES)
    requested_amount = models.DecimalField(max_digits=10, decimal_places=2)
    approved_amount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')

    reviewed_by = models.ForeignKey(
        'users.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='reviewed_refunds'
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)
    resolution_notes = models.TextField(blank=True)

    # Optional: metadata for audit
    metadata = models.JSONField(default=dict, blank=True)

    def __str__(self):
        return f"Refund #{self.id} - {self.booking} ({self.status})"

    class Meta:
        db_table = 'refund_requests'
        ordering = ['-created_at']


class RefundTransaction(BaseModel):
    """
    Records the actual refund transaction processed via the payment gateway.
    """
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('success', 'Success'),
        ('failed', 'Failed'),
        ('reversed', 'Reversed'),
    ]

    original_transaction = models.ForeignKey(
        Transaction,
        on_delete=models.CASCADE,
        related_name='refund_transactions'
    )
    refund_request = models.ForeignKey(
        RefundRequest,
        on_delete=models.CASCADE,
        related_name='refund_transactions'
    )
    amount = models.DecimalField(max_digits=10, decimal_places=2)  # negative amount (refund)

    gateway_reference_id = models.CharField(max_length=255)
    gateway_response_code = models.CharField(max_length=50, blank=True, null=True)
    gateway_response_message = models.TextField(blank=True, null=True)

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    processed_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"RefundTransaction {self.id} - {self.amount} ({self.status})"

    class Meta:
        db_table = 'refund_transactions'
        ordering = ['-processed_at']
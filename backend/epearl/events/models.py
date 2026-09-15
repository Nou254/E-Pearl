# events/models.py

from django.db import models
from core.models import BaseModel
from django.utils import timezone
import uuid


class Event(BaseModel):
    """
    Event created by a venue.
    """
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('published', 'Published'),
        ('active', 'Active'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ]

    venue = models.ForeignKey(
        'venues.Venue',
        on_delete=models.CASCADE,
        related_name='events'
    )
    event_name = models.CharField(max_length=255)
    event_description = models.TextField(blank=True, null=True)
    event_date = models.DateField()
    event_start_time = models.TimeField()
    event_end_time = models.TimeField(null=True, blank=True)
    max_capacity = models.PositiveIntegerField()
    ticket_sales_start = models.DateTimeField()
    ticket_sales_end = models.DateTimeField()
    door_policy = models.TextField(blank=True, null=True)
    flyer_image_url = models.CharField(max_length=255, blank=True, null=True)

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    checked_in_count = models.PositiveIntegerField(default=0)
    total_tickets_sold = models.PositiveIntegerField(default=0)
    gross_revenue = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    platform_fee_collected = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    # NEW: Computed field for no-shows (derived from total_tickets_sold - checked_in_count)
    # We'll compute this on the fly, but we can add a field if needed.

    class Meta:
        db_table = 'events'
        ordering = ['-event_date', '-event_start_time']

    def __str__(self):
        return f"{self.event_name} ({self.event_date})"

    def is_ticket_sales_active(self):
        now = timezone.now()
        return self.ticket_sales_start <= now <= self.ticket_sales_end

    def tickets_remaining(self):
        return self.max_capacity - self.total_tickets_sold

    def no_show_count(self):
        return self.total_tickets_sold - self.checked_in_count


class TicketTier(BaseModel):
    """
    Ticket tiers for an event.
    """
    venue = models.ForeignKey(
        'venues.Venue',
        on_delete=models.CASCADE,
        related_name='ticket_tiers'
    )
    event = models.ForeignKey(
        Event,
        on_delete=models.CASCADE,
        related_name='ticket_tiers'
    )
    tier_name = models.CharField(max_length=100)
    tier_description = models.TextField(blank=True, null=True)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    quantity_limit = models.PositiveIntegerField()
    quantity_sold = models.PositiveIntegerField(default=0)

    is_vip = models.BooleanField(default=False)
    reserved_table = models.ForeignKey(
        'tables.Table',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='ticket_tiers',
        help_text="Table reserved for VIP bundle"
    )

    class Meta:
        db_table = 'ticket_tiers'
        ordering = ['price']

    def __str__(self):
        return f"{self.tier_name} - {self.event.event_name}"


class Ticket(BaseModel):
    """
    Individual ticket purchase.
    """
    STATUS_CHOICES = [
        ('purchased', 'Purchased'),
        ('checked_in', 'Checked In'),
        ('exited', 'Exited'),
        ('cancelled', 'Cancelled'),
        ('refunded', 'Refunded'),
    ]

    venue = models.ForeignKey(
        'venues.Venue',
        on_delete=models.CASCADE,
        related_name='tickets'
    )
    event = models.ForeignKey(
        Event,
        on_delete=models.CASCADE,
        related_name='tickets'
    )
    ticket_tier = models.ForeignKey(
        TicketTier,
        on_delete=models.CASCADE,
        related_name='tickets'
    )
    guest_session = models.ForeignKey(
        'guest_sessions.GuestSession',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='tickets'
    )
    user = models.ForeignKey(
        'users.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='tickets'
    )

    ticket_code = models.CharField(max_length=100, unique=True)
    ticket_qr = models.UUIDField(unique=True, default=uuid.uuid4, editable=False)

    customer_name = models.CharField(max_length=255)
    customer_email = models.EmailField(blank=True, null=True)
    customer_phone = models.CharField(max_length=20)

    price = models.DecimalField(max_digits=10, decimal_places=2)
    platform_fee = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    manual_exit_code = models.CharField(max_length=10, null=True, blank=True)
    is_digital = models.BooleanField(default=True)

    checked_in = models.BooleanField(default=False)
    checked_in_time = models.DateTimeField(null=True, blank=True)
    exited = models.BooleanField(default=False)
    exited_time = models.DateTimeField(null=True, blank=True)

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='purchased')
    purchase_time = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = 'tickets'
        ordering = ['-purchase_time']

    def __str__(self):
        return f"Ticket {self.ticket_code} - {self.event.event_name}"
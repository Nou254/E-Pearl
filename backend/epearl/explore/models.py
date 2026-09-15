# explore/models.py

import uuid
from django.db import models
from core.models import BaseModel
from django.utils import timezone


class Booking(BaseModel):
    """
    Represents a booking made through Explore.
    Can be for a table, hotel room, or venue hire.
    """
    BOOKING_TYPES = [
        ('table', 'Table Reservation'),
        ('room', 'Hotel Room'),
        ('hire', 'Venue Hire'),
    ]

    STATUS_CHOICES = [
        ('pending', 'Pending Payment'),
        ('confirmed', 'Confirmed'),
        ('checked_in', 'Checked In'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ]

    # ----- NEW: Refund status for the booking -----
    REFUND_STATUS_CHOICES = [
        ('none', 'No Refund'),
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('processed', 'Processed'),
    ]

    venue = models.ForeignKey(
        'venues.Venue',
        on_delete=models.CASCADE,
        related_name='bookings'
    )
    guest_session = models.ForeignKey(
        'guest_sessions.GuestSession',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='bookings'
    )
    user = models.ForeignKey(
        'users.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='bookings'
    )
    booking_type = models.CharField(max_length=20, choices=BOOKING_TYPES)
    booking_date = models.DateField()
    start_time = models.TimeField()
    end_time = models.TimeField(null=True, blank=True)
    party_size = models.PositiveIntegerField(default=1)
    notes = models.TextField(blank=True, null=True)

    # Table reservation specific
    table = models.ForeignKey(
        'tables.Table',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='bookings'
    )

    # Room booking specific
    room_type = models.ForeignKey(
        'RoomType',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='bookings'
    )

    # Venue hire specific
    venue_hiring = models.OneToOneField(
        'VenueHiring',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='booking'
    )

    # Financial
    total_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    paid_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    payment_status = models.CharField(
        max_length=20,
        default='pending',
        choices=[
            ('pending', 'Pending'),
            ('paid', 'Paid'),
            ('failed', 'Failed'),
            ('refunded', 'Refunded'),
        ]
    )
    transaction_id = models.CharField(max_length=255, blank=True, null=True)

    # QR and check-in
    booking_qr = models.UUIDField(
        unique=True,
        default=uuid.uuid4,
        editable=False
    )
    checked_in = models.BooleanField(default=False)
    checked_in_time = models.DateTimeField(null=True, blank=True)
    checked_out = models.BooleanField(default=False)
    checked_out_time = models.DateTimeField(null=True, blank=True)

    # Status and timestamps
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')

    # ----- NEW: Refund status -----
    refund_status = models.CharField(
        max_length=20,
        choices=REFUND_STATUS_CHOICES,
        default='none',
        help_text="Current refund status for this booking"
    )

    class Meta:
        db_table = 'bookings'
        ordering = ['-booking_date', '-start_time']

    def __str__(self):
        return f"{self.booking_type} booking for {self.venue.business_name} on {self.booking_date}"


class RoomType(BaseModel):
    """
    Hotel room types (e.g., Deluxe Suite, Standard Double).
    """
    venue = models.ForeignKey(
        'venues.Venue',
        on_delete=models.CASCADE,
        related_name='room_types'
    )
    room_type = models.CharField(max_length=100)
    description = models.TextField(blank=True, null=True)
    base_price = models.DecimalField(max_digits=10, decimal_places=2)
    max_occupancy = models.PositiveIntegerField(default=2)
    amenities = models.JSONField(default=list, blank=True)
    image_urls = models.JSONField(default=list, blank=True)
    status = models.CharField(
        max_length=20,
        default='active',
        choices=[('active', 'Active'), ('inactive', 'Inactive')]
    )

    class Meta:
        db_table = 'room_types'
        unique_together = ['venue', 'room_type']

    def __str__(self):
        return f"{self.venue.business_name} - {self.room_type}"


class RoomAvailability(BaseModel):
    """
    Tracks room availability by date.
    """
    room_type = models.ForeignKey(
        RoomType,
        on_delete=models.CASCADE,
        related_name='availabilities'
    )
    date = models.DateField()
    available_rooms = models.PositiveIntegerField()
    total_rooms = models.PositiveIntegerField()
    price = models.DecimalField(max_digits=10, decimal_places=2)

    class Meta:
        db_table = 'room_availability'
        unique_together = ['room_type', 'date']

    def __str__(self):
        return f"{self.room_type.room_type} - {self.date} ({self.available_rooms} available)"


class VenueHiring(BaseModel):
    """
    Venue hire bookings (renting the entire venue for an event).
    """
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('confirmed', 'Confirmed'),
        ('checked_in', 'Checked In'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ]

    venue = models.ForeignKey(
        'venues.Venue',
        on_delete=models.CASCADE,
        related_name='hirings'
    )
    renter_name = models.CharField(max_length=255)
    renter_phone = models.CharField(max_length=20)
    renter_email = models.EmailField()
    hire_date = models.DateField()
    hire_start_time = models.TimeField()
    hire_end_time = models.TimeField()
    hire_duration = models.CharField(max_length=50)
    hire_price = models.DecimalField(max_digits=10, decimal_places=2)
    deposit_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    deposit_status = models.CharField(
        max_length=20,
        default='not_required',
        choices=[
            ('not_required', 'Not Required'),
            ('paid', 'Paid'),
            ('refunded', 'Refunded'),
        ]
    )
    hire_qr = models.UUIDField(
        unique=True,
        default=uuid.uuid4,
        editable=False
    )
    hire_rules = models.TextField(blank=True, null=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')

    checked_in = models.BooleanField(default=False)
    checked_in_time = models.DateTimeField(null=True, blank=True)
    checked_out = models.BooleanField(default=False)
    checked_out_time = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'venue_hiring'
        ordering = ['-hire_date']

    def __str__(self):
        return f"Hire of {self.venue.business_name} by {self.renter_name} on {self.hire_date}"


# =============================================================================
# NEW: Ratings & Reviews Models
# =============================================================================

class Rating(BaseModel):
    """
    Customer rating for a venue.
    """
    venue = models.ForeignKey(
        'venues.Venue',
        on_delete=models.CASCADE,
        related_name='ratings'
    )
    user = models.ForeignKey(
        'users.User',
        on_delete=models.SET_NULL,
        null=True,
        related_name='ratings'
    )
    booking = models.ForeignKey(
        Booking,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='ratings'
    )
    rating = models.PositiveSmallIntegerField(
        choices=[(i, i) for i in range(1, 6)],
        help_text="Rating from 1 (poor) to 5 (excellent)"
    )
    review = models.TextField(blank=True, null=True)
    is_verified = models.BooleanField(
        default=False,
        help_text="Verified purchase (they actually visited the venue)"
    )
    is_visible = models.BooleanField(
        default=True,
        help_text="Admin can hide inappropriate reviews"
    )

    class Meta:
        db_table = 'ratings'
        ordering = ['-created_at']
        unique_together = ['venue', 'user']

    def __str__(self):
        return f"{self.user.full_name} rated {self.venue.business_name}: {self.rating}/5"


class RatingSummary(BaseModel):
    """
    Aggregated rating summary per venue (cached for performance).
    """
    venue = models.OneToOneField(
        'venues.Venue',
        on_delete=models.CASCADE,
        related_name='rating_summary'
    )
    average_rating = models.DecimalField(max_digits=3, decimal_places=2, default=0)
    total_reviews = models.PositiveIntegerField(default=0)
    rating_distribution = models.JSONField(
        default=dict,
        help_text="Distribution of ratings: {1: count, 2: count, ...}"
    )
    last_updated = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'rating_summaries'

    def __str__(self):
        return f"{self.venue.business_name}: {self.average_rating} ({self.total_reviews} reviews)"
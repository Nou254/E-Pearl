# tables/models.py

from django.db import models
from core.models import BaseModel
import uuid


class Zone(BaseModel):
    """
    A logical area within a venue (e.g., Patio, VIP Area, Indoor).
    Used to group tables and assign waiters to specific zones.
    """
    venue = models.ForeignKey(
        'venues.Venue',
        on_delete=models.CASCADE,
        related_name='zones'
    )
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True, null=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = 'zones'
        ordering = ['name']
        unique_together = ['venue', 'name']

    def __str__(self):
        return f"{self.venue.business_name} - {self.name}"


class Table(BaseModel):
    """
    A physical table within a venue.
    """
    TABLE_STATUS_CHOICES = [
        ('available', 'Available'),
        ('occupied', 'Occupied'),
        ('reserved', 'Reserved'),
        ('cleaning', 'Cleaning'),
        ('suspended', 'Suspended'),
    ]

    venue = models.ForeignKey(
        'venues.Venue',
        on_delete=models.CASCADE,
        related_name='tables'
    )
    zone = models.ForeignKey(
        Zone,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='tables'
    )
    table_number = models.CharField(max_length=50)
    max_capacity = models.PositiveIntegerField(default=4)
    current_headcount = models.PositiveIntegerField(default=0)
    status = models.CharField(
        max_length=20,
        choices=TABLE_STATUS_CHOICES,
        default='available'
    )
    qr_code = models.UUIDField(
        unique=True,
        default=uuid.uuid4,
        editable=False,
        help_text="Unique QR code identifier for this table"
    )
    qr_code_label = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text="Human-readable label for the QR code (e.g., 'Table 1')"
    )
    table_type = models.CharField(
        max_length=50,
        default='regular',
        choices=[
            ('regular', 'Regular'),
            ('vip', 'VIP'),
            ('booth', 'Booth'),
            ('outdoor', 'Outdoor'),
        ]
    )
    is_active = models.BooleanField(default=True)

    # Reservation specific fields
    reservation_status = models.CharField(
        max_length=20,
        default='available',
        choices=[
            ('available', 'Available'),
            ('booked', 'Booked'),
            ('held', 'Held'),
        ]
    )

    class Meta:
        db_table = 'tables'
        ordering = ['table_number']
        unique_together = ['venue', 'table_number']

    def __str__(self):
        return f"{self.venue.business_name} - Table {self.table_number}"

    def is_available(self):
        return self.status == 'available' and self.is_active

    def can_seat(self, party_size):
        return self.max_capacity >= party_size and self.is_available()

    def occupy(self, headcount=1):
        self.status = 'occupied'
        self.current_headcount = headcount
        self.save()

    def free(self):
        self.status = 'available'
        self.current_headcount = 0
        self.save()

    def reserve(self):
        self.status = 'reserved'
        self.save()


# =============================================================================
# Table Reservation for VIP Bundles & Status Change Log (NEW)
# =============================================================================

class TableReservation(BaseModel):
    """
    Logs table reservations for events (VIP bundles).
    """
    event = models.ForeignKey('events.Event', on_delete=models.CASCADE, related_name='table_reservations')
    table = models.ForeignKey(Table, on_delete=models.CASCADE, related_name='reservations')
    ticket_tier = models.ForeignKey('events.TicketTier', on_delete=models.SET_NULL, null=True, blank=True, related_name='table_reservations')
    status = models.CharField(
        max_length=20,
        choices=[
            ('reserved', 'Reserved'),
            ('occupied', 'Occupied'),
            ('released', 'Released'),
        ],
        default='reserved'
    )
    reserved_at = models.DateTimeField(auto_now_add=True)
    occupied_at = models.DateTimeField(null=True, blank=True)
    released_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'table_reservations'
        ordering = ['-reserved_at']
        unique_together = ['event', 'table']

    def __str__(self):
        return f"{self.table.table_number} - {self.event.event_name} ({self.status})"


class TableStatusChange(BaseModel):
    """
    Logs every status change of a table for real‑time WebSocket updates.
    """
    table = models.ForeignKey(Table, on_delete=models.CASCADE, related_name='status_changes')
    previous_status = models.CharField(max_length=20, choices=Table.TABLE_STATUS_CHOICES)
    new_status = models.CharField(max_length=20, choices=Table.TABLE_STATUS_CHOICES)
    changed_by = models.ForeignKey('users.User', on_delete=models.SET_NULL, null=True, blank=True, related_name='table_status_changes')
    reason = models.TextField(blank=True, null=True)
    changed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'table_status_changes'
        ordering = ['-changed_at']

    def __str__(self):
        return f"{self.table.table_number}: {self.previous_status} → {self.new_status} @ {self.changed_at}"
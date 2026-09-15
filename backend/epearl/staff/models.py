# staff/models.py

from django.db import models
from core.models import BaseModel
from django.utils import timezone
import uuid


class Shift(BaseModel):
    """
    Shift definition (e.g., Day Shift, Night Shift).
    """
    DAYS_OF_WEEK = [
        ('monday', 'Monday'), ('tuesday', 'Tuesday'), ('wednesday', 'Wednesday'),
        ('thursday', 'Thursday'), ('friday', 'Friday'), ('saturday', 'Saturday'),
        ('sunday', 'Sunday')
    ]

    venue = models.ForeignKey(
        'venues.Venue',
        on_delete=models.CASCADE,
        related_name='shifts'
    )
    shift_name = models.CharField(max_length=100)
    start_time = models.TimeField()
    end_time = models.TimeField()
    days_of_week = models.JSONField(
        default=list,
        help_text="List of days this shift applies to (e.g., ['monday', 'tuesday'])"
    )
    zone = models.ForeignKey(
        'tables.Zone',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='shifts'
    )
    status = models.CharField(max_length=20, default='active', choices=[
        ('active', 'Active'),
        ('inactive', 'Inactive')
    ])

    class Meta:
        db_table = 'shifts'
        ordering = ['start_time']

    def __str__(self):
        return f"{self.shift_name} ({self.start_time} - {self.end_time})"


class Staff(BaseModel):
    """
    Staff member associated with a user account.
    """
    ROLES = [
        ('waiter', 'Waiter'),
        ('chef', 'Chef'),
        ('bartender', 'Bartender'),
        ('security', 'Security'),
        ('receptionist', 'Receptionist'),
        ('manager', 'Manager'),
        ('owner', 'Owner'),
        ('admin', 'Admin'),
        ('support', 'Support'),
    ]

    user = models.OneToOneField(
        'users.User',
        on_delete=models.CASCADE,
        related_name='staff_profile'
    )
    venue = models.ForeignKey(
        'venues.Venue',
        on_delete=models.CASCADE,
        related_name='staff_members'
    )
    role = models.CharField(max_length=50, choices=ROLES)
    assigned_zone = models.ForeignKey(
        'tables.Zone',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='staff_members'
    )
    staff_qr = models.UUIDField(
        unique=True,
        default=uuid.uuid4,
        editable=False,
        help_text="QR code for scan-in/scan-out"
    )
    is_active = models.BooleanField(default=True)

    # Shift assignment (many-to-many via ShiftStaff)
    shifts = models.ManyToManyField(
        Shift,
        through='ShiftStaff',
        related_name='staff_members'
    )

    # ----- NEW: Busy tracking for overflow logic -----
    is_busy = models.BooleanField(default=False)
    busy_until = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'staff'
        ordering = ['user__full_name']

    def __str__(self):
        return f"{self.user.full_name} ({self.role})"

    def is_on_shift(self, at_time=None):
        """Check if staff is scheduled to be on shift at a given time."""
        if at_time is None:
            at_time = timezone.now().time()
        shift_staff = ShiftStaff.objects.filter(
            staff=self,
            shift__status='active'
        ).first()
        if not shift_staff:
            return False
        shift = shift_staff.shift
        return shift.start_time <= at_time <= shift.end_time

    def get_current_attendance(self):
        """Get today's attendance record if exists."""
        today = timezone.now().date()
        return StaffAttendance.objects.filter(
            staff=self,
            scan_in_time__date=today
        ).order_by('-scan_in_time').first()

    # ----- NEW: Availability methods -----
    def is_available(self):
        """Check if staff is available for a new task."""
        if not self.is_active:
            return False
        if self.is_busy and self.busy_until and timezone.now() < self.busy_until:
            return False
        return True

    def set_busy(self, duration_seconds=300):
        """Mark staff as busy for a given duration."""
        self.is_busy = True
        self.busy_until = timezone.now() + timezone.timedelta(seconds=duration_seconds)
        self.save(update_fields=['is_busy', 'busy_until'])

    def set_available(self):
        """Mark staff as available."""
        self.is_busy = False
        self.busy_until = None
        self.save(update_fields=['is_busy', 'busy_until'])


class ShiftStaff(BaseModel):
    """
    Junction table linking staff to shifts with additional metadata.
    """
    staff = models.ForeignKey(Staff, on_delete=models.CASCADE)
    shift = models.ForeignKey(Shift, on_delete=models.CASCADE)
    is_primary = models.BooleanField(default=False)  # Primary waiter for zone

    class Meta:
        db_table = 'shift_staff'
        unique_together = ['staff', 'shift']


class StaffAttendance(BaseModel):
    """
    Records staff scan-in and scan-out for shift tracking and cash reconciliation.
    """
    staff = models.ForeignKey(
        Staff,
        on_delete=models.CASCADE,
        related_name='attendances'
    )
    shift = models.ForeignKey(
        Shift,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='attendances'
    )
    scan_in_time = models.DateTimeField()
    scan_out_time = models.DateTimeField(null=True, blank=True)

    # Cash reconciliation
    cash_collected = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    cash_reconciled = models.BooleanField(default=False)
    reconciled_by = models.ForeignKey(
        Staff,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='reconciled_attendances'
    )
    reconciled_at = models.DateTimeField(null=True, blank=True)

    # Device info
    scan_in_device = models.CharField(max_length=255, blank=True, null=True)
    scan_out_device = models.CharField(max_length=255, blank=True, null=True)

    # Status
    attendance_status = models.CharField(
        max_length=20,
        default='present',
        choices=[
            ('present', 'Present'),
            ('absent', 'Absent'),
            ('late', 'Late'),
        ]
    )

    class Meta:
        db_table = 'staff_attendance'
        ordering = ['-scan_in_time']

    def __str__(self):
        return f"{self.staff.user.full_name} - {self.scan_in_time}"

    def is_active(self):
        return self.scan_out_time is None

    def reconcile_cash(self, amount, reconciled_by):
        self.cash_collected = amount
        self.cash_reconciled = True
        self.reconciled_by = reconciled_by
        self.reconciled_at = timezone.now()
        self.save()


# =============================================================================
# Shift Handover, Cash Collection, Performance Metric
# =============================================================================

class ShiftHandover(BaseModel):
    """
    Logs shift handover events (from → to, zone, tables).
    """
    venue = models.ForeignKey('venues.Venue', on_delete=models.CASCADE, related_name='handovers')
    from_staff = models.ForeignKey(Staff, on_delete=models.CASCADE, related_name='handovers_from')
    to_staff = models.ForeignKey(Staff, on_delete=models.CASCADE, related_name='handovers_to')
    zone = models.CharField(max_length=100, blank=True, null=True)
    tables_transferred = models.PositiveIntegerField(default=0)
    handed_over_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'staff_shift_handovers'
        ordering = ['-handed_over_at']

    def __str__(self):
        return f"{self.from_staff.user.full_name} → {self.to_staff.user.full_name} @ {self.handed_over_at}"


class CashCollection(BaseModel):
    """
    Logs each cash collection made by a staff member.
    """
    staff = models.ForeignKey(Staff, on_delete=models.CASCADE, related_name='cash_collections')
    venue = models.ForeignKey('venues.Venue', on_delete=models.CASCADE, related_name='cash_collections')
    table = models.ForeignKey('tables.Table', on_delete=models.SET_NULL, null=True, blank=True, related_name='cash_collections')
    guest_session = models.ForeignKey('guest_sessions.GuestSession', on_delete=models.SET_NULL, null=True, blank=True, related_name='cash_collections')
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    collected_at = models.DateTimeField(auto_now_add=True)
    reconciled = models.BooleanField(default=False)
    reconciled_at = models.DateTimeField(null=True, blank=True)
    reconciled_by = models.ForeignKey('users.User', on_delete=models.SET_NULL, null=True, blank=True)

    class Meta:
        db_table = 'staff_cash_collections'
        ordering = ['-collected_at']

    def __str__(self):
        return f"{self.staff.user.full_name}: KES {self.amount} @ {self.collected_at}"


class PerformanceMetric(BaseModel):
    """
    Cached aggregated performance metrics for staff (for fast retrieval).
    """
    staff = models.ForeignKey(Staff, on_delete=models.CASCADE, related_name='performance_metrics')
    venue = models.ForeignKey('venues.Venue', on_delete=models.CASCADE, related_name='performance_metrics')
    period_start = models.DateTimeField()
    period_end = models.DateTimeField()
    total_orders = models.PositiveIntegerField(default=0)
    total_revenue = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    avg_turnaround_minutes = models.FloatField(default=0)
    satisfaction_score = models.FloatField(default=0)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'staff_performance_metrics'
        ordering = ['-period_start']

    def __str__(self):
        return f"{self.staff.user.full_name} - {self.period_start} to {self.period_end}"
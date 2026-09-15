from django.db import models

# Create your models here.
from django.db import models
from core.models import BaseModel
from venues.models import Venue
from staff.models import Staff
from guest_sessions.models import GuestSession
from tables.models import Table

class StaffAttendance(BaseModel):
    """
    Staff Scan-In and Scan-Out records.
    """
    attendance_status = [
        ('present', 'Present'),
        ('absent', 'Absent'),
        ('late', 'Late'),
    ]
    
    venue = models.ForeignKey(Venue, on_delete=models.CASCADE, related_name='staff_attendance')
    staff = models.ForeignKey(Staff, on_delete=models.CASCADE, related_name='attendance')
    shift = models.ForeignKey('staff.Shift', on_delete=models.SET_NULL, null=True, blank=True, related_name='attendance')
    scan_in_time = models.DateTimeField()
    scan_out_time = models.DateTimeField(null=True, blank=True)
    scan_in_device = models.CharField(max_length=255, blank=True, null=True)
    scan_out_device = models.CharField(max_length=255, blank=True, null=True)
    cash_collected = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    cash_reconciled = models.BooleanField(default=False)
    reconciled_by = models.ForeignKey(Staff, on_delete=models.SET_NULL, null=True, blank=True, related_name='reconciled_attendance')
    reconciled_at = models.DateTimeField(null=True, blank=True)
    shift_start = models.DateTimeField()
    shift_end = models.DateTimeField()
    attendance_status = models.CharField(max_length=50, choices=attendance_status, default='present')
    
    def __str__(self):
        return f"{self.staff.name} - {self.shift_start.date()}"
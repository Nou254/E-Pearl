# staff/services/overflow_service.py

from django.core.exceptions import ValidationError
from django.db.models import Q
from django.utils import timezone
from staff.models import Staff, ShiftStaff, StaffAttendance
from tables.models import Table
import logging

logger = logging.getLogger(__name__)


class OverflowService:
    """
    Handles cooperative overflow logic: detecting busy waiters and reassigning tasks.
    """

    @classmethod
    def get_available_waiter(cls, venue, zone=None, exclude_staff_ids=None):
        """
        Find an available waiter in the given venue/zone.
        Returns a Staff object or None.
        """
        if exclude_staff_ids is None:
            exclude_staff_ids = []

        # Get all active waiters in the venue, optionally filtered by zone
        qs = Staff.objects.filter(
            venue=venue,
            role='waiter',
            is_active=True,
            is_busy=False
        ).exclude(id__in=exclude_staff_ids)

        if zone:
            qs = qs.filter(assigned_zone=zone)

        # Prefer those currently on shift
        now = timezone.now().time()
        on_shift = qs.filter(
            shifts__shiftstaff__shift__status='active',
            shifts__shiftstaff__shift__start_time__lte=now,
            shifts__shiftstaff__shift__end_time__gte=now
        ).distinct()

        if on_shift.exists():
            return on_shift.first()

        # Fallback to any available waiter
        return qs.first()

    @classmethod
    def set_busy(cls, staff_id, duration_seconds=300):
        """
        Mark a waiter as busy for a set duration.
        """
        try:
            staff = Staff.objects.get(id=staff_id)
        except Staff.DoesNotExist:
            raise ValidationError("Staff not found.")

        staff.set_busy(duration_seconds)
        logger.info(f"Staff {staff.user.full_name} marked busy for {duration_seconds}s")
        return staff

    @classmethod
    def set_available(cls, staff_id):
        """
        Mark a waiter as available again.
        """
        try:
            staff = Staff.objects.get(id=staff_id)
        except Staff.DoesNotExist:
            raise ValidationError("Staff not found.")

        staff.set_available()
        logger.info(f"Staff {staff.user.full_name} marked available")
        return staff

    @classmethod
    def request_cover(cls, venue, table_id, from_staff_id=None):
        """
        Request cover for a specific table.
        Finds the next available waiter and assigns the table to them.
        """
        table = Table.objects.get(id=table_id, venue=venue)
        if not table:
            raise ValidationError("Table not found.")

        exclude = [from_staff_id] if from_staff_id else []
        # Try to find a waiter in the same zone first
        available = cls.get_available_waiter(venue, table.zone, exclude)
        if not available:
            # If none, try any zone
            available = cls.get_available_waiter(venue, zone=None, exclude=exclude)

        if not available:
            raise ValidationError("No available waiters to cover.")

        # Assign the table to the new waiter
        table.assigned_waiter = available
        table.save(update_fields=['assigned_waiter'])

        logger.info(f"Table {table.table_number} reassigned to {available.user.full_name} for cover")
        return available

    @classmethod
    def auto_assign(cls, venue, zone, table_id):
        """
        Automatically assign an available waiter to a table.
        Used for new orders and critical alerts.
        """
        table = Table.objects.get(id=table_id, venue=venue)
        if not table:
            raise ValidationError("Table not found.")

        # If table already has a waiter, check if they are busy
        existing_waiter = table.assigned_waiter
        if existing_waiter and existing_waiter.is_available():
            return existing_waiter  # existing waiter is available

        # Otherwise, find a new one
        new_waiter = cls.get_available_waiter(venue, zone)
        if not new_waiter:
            raise ValidationError("No available waiters to assign.")

        table.assigned_waiter = new_waiter
        table.save(update_fields=['assigned_waiter'])

        # If the previous waiter was busy, we might log it
        if existing_waiter and existing_waiter.is_busy:
            logger.info(f"Auto-assigned table {table.table_number} from busy waiter {existing_waiter.user.full_name} to {new_waiter.user.full_name}")

        return new_waiter
# staff/services/handover_service.py

from django.utils import timezone
from django.core.exceptions import ValidationError
from datetime import timedelta
from staff.models import Shift, ShiftStaff, Staff, ShiftHandover
from tables.models import Table
import logging

logger = logging.getLogger(__name__)


class HandoverService:
    GRACE_MINUTES = 15  # configurable

    @classmethod
    def initiate_handover(cls, from_staff_id, to_staff_id, zone_id):
        """
        Transfer all tables in a zone from one waiter to another.
        """
        try:
            from_staff = Staff.objects.get(id=from_staff_id, is_active=True)
            to_staff = Staff.objects.get(id=to_staff_id, is_active=True)
        except Staff.DoesNotExist:
            raise ValidationError("Invalid staff ID(s).")

        # Ensure both belong to same venue
        if from_staff.venue != to_staff.venue:
            raise ValidationError("Staff belong to different venues.")

        # Ensure incoming staff is scheduled for this zone
        now = timezone.now()
        shift_staff = ShiftStaff.objects.filter(
            staff=to_staff,
            shift__zone_id=zone_id,
            shift__status='active',
            shift__start_time__lte=now.time(),
            shift__end_time__gte=now.time()
        ).first()
        if not shift_staff:
            raise ValidationError("Incoming staff is not scheduled for this zone.")

        # Transfer tables
        tables = Table.objects.filter(
            venue=from_staff.venue,
            assigned_waiter=from_staff,
            zone_id=zone_id
        )
        count = tables.count()
        if count == 0:
            raise ValidationError("No tables to transfer.")

        for table in tables:
            table.assigned_waiter = to_staff
            table.save(update_fields=['assigned_waiter'])

        # Log handover
        handover = ShiftHandover.objects.create(
            venue=from_staff.venue,
            from_staff=from_staff,
            to_staff=to_staff,
            zone_id=zone_id,
            tables_transferred=count
        )

        logger.info(f"Handover: {from_staff.user.full_name} → {to_staff.user.full_name}, {count} tables")
        return tables

    @classmethod
    def get_active_shift_for_staff(cls, staff):
        now = timezone.now()
        shift_staff = ShiftStaff.objects.filter(
            staff=staff,
            shift__status='active',
            shift__start_time__lte=now.time(),
            shift__end_time__gte=now.time()
        ).first()
        return shift_staff.shift if shift_staff else None
# staff/services/reconciliation_service.py

from django.core.exceptions import ValidationError
from staff.models import StaffAttendance, CashCollection
from decimal import Decimal
from django.utils import timezone


class ReconciliationService:
    @classmethod
    def check_staff_cash_reconciled(cls, attendance_id):
        """
        Returns True if all cash collected by this staff member during the shift
        has been reconciled.
        """
        try:
            attendance = StaffAttendance.objects.get(id=attendance_id)
        except StaffAttendance.DoesNotExist:
            return False

        # Sum of cash collected during this shift
        total_collected = CashCollection.objects.filter(
            staff=attendance.staff,
            collected_at__gte=attendance.scan_in_time,
            collected_at__lte=attendance.scan_out_time or timezone.now()
        ).aggregate(total=Sum('amount'))['total'] or Decimal('0')

        # Check if reconciled amount matches
        reconciled = attendance.cash_collected or Decimal('0')
        return total_collected == reconciled

    @classmethod
    def reconcile_cash(cls, attendance_id, amount, manager_id):
        """
        Marks cash as reconciled for a staff attendance record.
        """
        attendance = StaffAttendance.objects.get(id=attendance_id)
        from staff.models import Staff
        manager = Staff.objects.get(id=manager_id)
        attendance.cash_collected = amount
        attendance.cash_reconciled = True
        attendance.reconciled_by = manager
        attendance.reconciled_at = timezone.now()
        attendance.save()
        return attendance
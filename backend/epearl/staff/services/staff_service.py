# staff/services/staff_service.py

from django.core.exceptions import ValidationError
from django.utils import timezone
from django.db import transaction
from django.db import models
from django.conf import settings
from users.models import User
from users.services.permission_service import PermissionService  # ADDED: RBAC integration
from ..models import Staff, Shift, ShiftStaff, StaffAttendance
from venues.services.tier_service import TierService
from core.websocket_utils import notify_control
from notifications.services.notification_service import NotificationService
import uuid
from datetime import datetime, timedelta


class StaffService:
    """Service for staff management operations."""

    EARLY_GRACE_MINUTES = 30
    HIGH_VALUE_CASH_THRESHOLD = 20000

    @classmethod
    @transaction.atomic
    def create_staff(cls, venue, user_data, role, zone=None, shift_ids=None):
        if not TierService.can_add_staff(venue):
            raise ValidationError(
                f"Maximum staff limit reached for {venue.subscription_tier} tier. "
                "Please upgrade."
            )

        phone = user_data.get('phone')
        email = user_data.get('email')
        if not phone and not email:
            raise ValidationError("Either phone or email is required.")

        user, created = User.objects.get_or_create(
            phone=phone,
            defaults={
                'email': email,
                'full_name': user_data.get('full_name', ''),
                'user_type': 'staff',
                'venue': venue,
            }
        )
        temp_password = None
        if created:
            temp_password = User.objects.make_random_password()
            user.set_password(temp_password)
            user.save()

        staff = Staff.objects.create(
            user=user,
            venue=venue,
            role=role,
            assigned_zone=zone,
        )

        if shift_ids:
            shifts = Shift.objects.filter(id__in=shift_ids, venue=venue)
            for shift in shifts:
                ShiftStaff.objects.create(staff=staff, shift=shift)

        # --- RBAC: Assign default permissions based on staff role ---
        if staff.role:
            perm_codes = PermissionService.get_default_permissions_for_staff_role(staff.role)
            for code in perm_codes:
                try:
                    PermissionService.assign_permission(user, venue, code, granted=True)
                except ValueError:
                    # Permission may not exist yet; skip silently
                    pass

            # Assign a role (if it exists)
            role_map = {
                'waiter': 'Waiter',
                'chef': 'Chef',
                'bartender': 'Bartender',
                'security': 'Security',
                'receptionist': 'Receptionist',
                'cashier': 'Cashier',
                'event_coordinator': 'Event Coordinator',
                'inventory_officer': 'Inventory Officer',
                'accountant': 'Accountant',
                'assistant_manager': 'Assistant Manager',
                'manager': 'Manager',
                'owner': 'Owner',
            }
            role_name = role_map.get(staff.role, staff.role.capitalize())
            try:
                PermissionService.assign_role(user, venue, role_name)
            except ValueError:
                # Role may not exist yet; skip silently
                pass

        # Send staff welcome notification
        if temp_password:
            NotificationService.send_staff_welcome(user, temp_password)

        return staff

    @classmethod
    def get_staff_by_user(cls, user):
        try:
            return Staff.objects.get(user=user)
        except Staff.DoesNotExist:
            return None

    @classmethod
    @transaction.atomic
    def scan_in(cls, staff, device_fingerprint=None):
        today = timezone.now().date()
        existing = StaffAttendance.objects.filter(
            staff=staff,
            scan_in_time__date=today,
            scan_out_time__isnull=True
        ).first()
        if existing:
            raise ValidationError("Staff already scanned in today.")

        shift_staff = ShiftStaff.objects.filter(
            staff=staff,
            shift__status='active'
        ).order_by('-is_primary').first()
        if not shift_staff:
            raise ValidationError("No active shift assigned for this staff.")

        shift = shift_staff.shift
        now = timezone.now().time()
        shift_start = shift.start_time
        shift_end = shift.end_time

        shift_start_dt = datetime.combine(timezone.now().date(), shift_start)
        grace_start = shift_start_dt - timedelta(minutes=cls.EARLY_GRACE_MINUTES)
        grace_end = datetime.combine(timezone.now().date(), shift_end)

        now_dt = datetime.combine(timezone.now().date(), now)

        if not (grace_start <= now_dt <= grace_end):
            raise ValidationError(
                f"Scan-in not allowed. Shift is {shift_start} - {shift_end}. "
                f"You can only scan in from {grace_start.time()} onwards."
            )

        attendance_status = 'present'
        if now > shift_start_dt.time():
            attendance_status = 'late'

        attendance = StaffAttendance.objects.create(
            staff=staff,
            shift=shift,
            scan_in_time=timezone.now(),
            scan_in_device=device_fingerprint,
            attendance_status=attendance_status,
        )

        return attendance

    @classmethod
    @transaction.atomic
    def scan_out(cls, staff, device_fingerprint=None, override_manager=None):
        attendance = StaffAttendance.objects.filter(
            staff=staff,
            scan_out_time__isnull=True
        ).order_by('-scan_in_time').first()
        if not attendance:
            raise ValidationError("No active scan-in found.")

        if attendance.cash_collected > 0 and not attendance.cash_reconciled:
            if attendance.cash_collected > cls.HIGH_VALUE_CASH_THRESHOLD:
                if not override_manager:
                    raise ValidationError(
                        f"High-value cash amount ({attendance.cash_collected}) "
                        f"exceeds threshold ({cls.HIGH_VALUE_CASH_THRESHOLD}). "
                        "Manager override required."
                    )
                attendance.reconciled_by = override_manager
                attendance.reconciled_at = timezone.now()
                attendance.save(update_fields=['reconciled_by', 'reconciled_at'])
            else:
                notify_control(str(staff.venue.id), 'staff.cash.outstanding', {
                    'staff_id': str(staff.id),
                    'staff_name': staff.user.full_name,
                    'cash_amount': float(attendance.cash_collected),
                })
                raise ValidationError(
                    f"Outstanding cash: {attendance.cash_collected} not reconciled. "
                    "See manager."
                )

        attendance.scan_out_time = timezone.now()
        attendance.scan_out_device = device_fingerprint
        attendance.save(update_fields=['scan_out_time', 'scan_out_device'])
        return attendance

    @classmethod
    @transaction.atomic
    def reconcile_cash(cls, staff_id, amount, reconciled_by):
        staff = Staff.objects.get(id=staff_id)
        attendance = StaffAttendance.objects.filter(
            staff=staff,
            scan_out_time__isnull=True
        ).order_by('-scan_in_time').first()
        if not attendance:
            raise ValidationError("No active shift found.")

        if attendance.cash_reconciled:
            raise ValidationError("Cash already reconciled.")

        if amount is not None:
            attendance.cash_collected = amount

        attendance.reconcile_cash(
            amount=amount or attendance.cash_collected,
            reconciled_by=reconciled_by
        )

        # Send cash reconciled notification
        if staff.user:
            NotificationService.send_cash_reconciled(staff.user, attendance.cash_collected)

        return attendance

    @classmethod
    def get_no_show_staff(cls, venue, date=None):
        if date is None:
            date = timezone.now().date()

        active_shifts = ShiftStaff.objects.filter(
            staff__venue=venue,
            staff__is_active=True,
            shift__status='active',
            shift__days_of_week__contains=date.strftime('%A').lower()
        ).select_related('staff', 'shift')

        no_show_list = []
        managers = User.objects.filter(venue=venue, user_type='manager', is_active=True)

        for shift_staff in active_shifts:
            staff = shift_staff.staff
            shift = shift_staff.shift

            attendance = StaffAttendance.objects.filter(
                staff=staff,
                scan_in_time__date=date
            ).exists()
            if not attendance:
                shift_start_dt = datetime.combine(date, shift.start_time)
                grace_end = shift_start_dt + timedelta(minutes=15)
                if timezone.now() > grace_end:
                    no_show_list.append({
                        'staff': staff,
                        'shift': shift,
                        'scheduled_start': shift.start_time,
                    })
                    for manager in managers:
                        NotificationService.send_no_show_alert(manager, staff, shift)
        return no_show_list

    @classmethod
    def get_attendance_report(cls, venue, start_date, end_date, role=None):
        queryset = StaffAttendance.objects.filter(
            staff__venue=venue,
            scan_in_time__date__gte=start_date,
            scan_in_time__date__lte=end_date
        ).select_related('staff', 'shift')

        if role:
            queryset = queryset.filter(staff__role=role)

        total_scans = queryset.count()
        present = queryset.filter(attendance_status='present').count()
        late = queryset.filter(attendance_status='late').count()
        total_cash = queryset.aggregate(total=models.Sum('cash_collected'))['total'] or 0

        staff_breakdown = {}
        for att in queryset:
            staff_key = att.staff.id
            if staff_key not in staff_breakdown:
                staff_breakdown[staff_key] = {
                    'staff_id': att.staff.id,
                    'staff_name': att.staff.user.full_name,
                    'role': att.staff.role,
                    'total_days': 0,
                    'present_days': 0,
                    'late_days': 0,
                    'total_hours': 0,
                    'cash_collected': 0,
                }
            staff_breakdown[staff_key]['total_days'] += 1
            if att.attendance_status == 'present':
                staff_breakdown[staff_key]['present_days'] += 1
            elif att.attendance_status == 'late':
                staff_breakdown[staff_key]['late_days'] += 1
            if att.scan_out_time:
                hours = (att.scan_out_time - att.scan_in_time).total_seconds() / 3600
                staff_breakdown[staff_key]['total_hours'] += hours
            staff_breakdown[staff_key]['cash_collected'] += float(att.cash_collected)

        return {
            'total_scans': total_scans,
            'present': present,
            'late': late,
            'total_cash': total_cash,
            'staff_breakdown': list(staff_breakdown.values())
        }
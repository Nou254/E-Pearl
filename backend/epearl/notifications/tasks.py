# notifications/tasks.py

from celery import shared_task
from django.utils import timezone
from datetime import timedelta
from staff.models import ShiftStaff, StaffAttendance
from explore.models import Booking
from notifications.services.notification_service import NotificationService
import logging

logger = logging.getLogger(__name__)


@shared_task
def send_shift_reminders():
    now = timezone.now()
    one_hour_later = now + timedelta(hours=1)
    shifts = ShiftStaff.objects.filter(
        shift__start_time__hour=one_hour_later.hour,
        shift__start_time__minute=one_hour_later.minute,
        staff__is_active=True,
        shift__status='active'
    ).select_related('staff', 'shift')
    for shift_staff in shifts:
        has_scanned = StaffAttendance.objects.filter(
            staff=shift_staff.staff,
            scan_in_time__date=timezone.now().date()
        ).exists()
        if not has_scanned:
            NotificationService.send_shift_reminder(shift_staff.staff.user, shift_staff.shift)


@shared_task
def send_booking_reminders():
    now = timezone.now()
    reminder_time = now + timedelta(hours=24)
    bookings = Booking.objects.filter(
        booking_date=reminder_time.date(),
        start_time__hour=reminder_time.hour,
        start_time__minute=reminder_time.minute,
        status='confirmed',
        user__isnull=False
    ).select_related('user', 'venue')
    for booking in bookings:
        NotificationService.send_booking_reminder(booking, booking.user)


# Low stock notification task (existing)
@shared_task
def send_low_stock_notification(venue_id, item_ids):
    from control.models import StockAlertLog, MenuItem
    from django.core.mail import send_mail
    from django.conf import settings
    from venues.models import Venue
    from staff.models import Staff

    try:
        venue = Venue.objects.get(id=venue_id)
    except Venue.DoesNotExist:
        logger.error(f"Venue {venue_id} not found for low stock notification")
        return

    items = MenuItem.objects.filter(id__in=item_ids)
    if not items:
        return

    for item in items:
        StockAlertLog.objects.create(
            venue=venue,
            menu_item=item,
            stock_count_at_alert=item.stock_count,
            threshold_at_alert=item.low_stock_threshold
        )

    managers = Staff.objects.filter(venue=venue, role='manager', is_active=True)
    if not managers:
        logger.warning(f"No managers found for venue {venue.business_name}")
        return

    subject = f"Low Stock Alert: {venue.business_name}"
    message = f"The following items are running low:\n\n"
    for item in items:
        message += f"- {item.name}: {item.stock_count} remaining (threshold: {item.low_stock_threshold})\n"
    message += "\nPlease review and restock as needed."

    for manager in managers:
        if manager.user.email:
            send_mail(
                subject=subject,
                message=message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[manager.user.email],
                fail_silently=True,
            )
            logger.info(f"Low stock notification sent to {manager.user.email}")


# =============================================================================
# NEW: Trial Reminder Tasks
# =============================================================================

@shared_task
def send_trial_reminders():
    """
    Send reminders to venue managers about trial expiration.
    Runs daily to check for trials ending in 7, 3, and 1 day.
    """
    from venues.models import Venue
    from staff.models import Staff

    today = timezone.now().date()
    remind_days = [7, 3, 1]

    for days in remind_days:
        target_date = today + timedelta(days=days)
        venues = Venue.objects.filter(
            subscription_status='trial',
            next_billing_date=target_date
        ).select_related('owner')

        for venue in venues:
            # Find manager(s) for this venue
            managers = Staff.objects.filter(venue=venue, role='manager', is_active=True).select_related('user')
            for manager in managers:
                if manager.user:
                    NotificationService.send_trial_will_end_soon(venue, manager.user, days_remaining=days)

            # Also notify the owner if they exist and are different from manager
            if venue.owner and venue.owner != (managers.first().user if managers else None):
                NotificationService.send_trial_will_end_soon(venue, venue.owner, days_remaining=days)

    logger.info(f"Trial reminders sent for {days} days ahead.")


@shared_task
def send_trial_expired_notification(venue_id):
    """
    Send notification that trial has expired and venue has been suspended.
    Triggered by billing_service when trial ends.
    """
    from venues.models import Venue
    from staff.models import Staff

    try:
        venue = Venue.objects.get(id=venue_id)
    except Venue.DoesNotExist:
        logger.error(f"Venue {venue_id} not found for trial expired notification")
        return

    managers = Staff.objects.filter(venue=venue, role='manager', is_active=True).select_related('user')
    for manager in managers:
        if manager.user:
            NotificationService.send_trial_ended(venue, manager.user, paid=False)

    if venue.owner:
        NotificationService.send_trial_ended(venue, venue.owner, paid=False)

    logger.info(f"Trial expired notification sent for {venue.business_name}")
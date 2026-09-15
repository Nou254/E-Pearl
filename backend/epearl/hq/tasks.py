# hq/tasks.py

from celery import shared_task
from django.utils import timezone
from django.conf import settings
from datetime import timedelta
from .services.health_service import HealthService
from .services.billing_service import BillingService
from venues.models import Venue
from notifications.services.notification_service import NotificationService
import logging

logger = logging.getLogger(__name__)


@shared_task
def check_service_health():
    HealthService.check_all_services(force=True)


@shared_task
def charge_subscriptions():
    BillingService.charge_subscriptions()


# =============================================================================
# NEW: Trial Expiry and Reminder Tasks
# =============================================================================

@shared_task
def check_trial_expiry():
    """
    Daily task to check for trial expirations and send reminders.
    1. Send reminders for trials ending soon (3 days before, 1 day before).
    2. Actually process expired trials (transition to active/suspended) via billing service.
    """
    today = timezone.now().date()

    # 1. Send reminders for trials ending in 3 days and 1 day
    remind_days = [3, 1]
    for days in remind_days:
        target_date = today + timedelta(days=days)
        venues = Venue.objects.filter(
            subscription_status='trial',
            next_billing_date=target_date
        )
        for venue in venues:
            if days == 3:
                NotificationService.send_trial_will_end_soon(venue, days_remaining=3)
            elif days == 1:
                NotificationService.send_trial_will_end_soon(venue, days_remaining=1)

    # 2. Process trials that have already expired (next_billing_date < today)
    # This will be handled by billing_service.charge_subscriptions(),
    # which calls process_trial_expirations.
    # But we can also call it separately if needed.
    # We'll call it here to ensure it runs daily.
    BillingService.process_trial_expirations(today)

    logger.info("Trial expiry check completed.")


@shared_task
def send_trial_reminders():
    """
    Dedicated task for sending trial reminders (can be called separately).
    """
    today = timezone.now().date()
    remind_days = [7, 3, 1]  # also 7 days before
    for days in remind_days:
        target_date = today + timedelta(days=days)
        venues = Venue.objects.filter(
            subscription_status='trial',
            next_billing_date=target_date
        )
        for venue in venues:
            NotificationService.send_trial_will_end_soon(venue, days_remaining=days)
    logger.info("Trial reminder emails sent.")
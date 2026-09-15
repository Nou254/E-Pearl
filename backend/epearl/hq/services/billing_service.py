# hq/services/billing_service.py

from django.utils import timezone
from django.db import transaction
from decimal import Decimal
from datetime import timedelta
from ..models import Subscription
from payments.models import Transaction
from venues.models import Venue
from notifications.services.notification_service import NotificationService
import logging

logger = logging.getLogger(__name__)


class BillingService:
    GRACE_PERIOD_DAYS = 7
    RETRY_ATTEMPTS = 3

    @classmethod
    def charge_subscriptions(cls):
        """
        Find all active venues whose billing is due, attempt to charge,
        and suspend if payment fails after grace period.
        Also handle trial expirations.
        """
        today = timezone.now().date()

        # 1. Handle trial expirations
        cls.process_trial_expirations(today)

        # 2. Handle active subscriptions
        subscriptions = Subscription.objects.filter(
            is_active=True,
            next_billing_date__lte=today
        )

        for sub in subscriptions:
            cls.process_subscription(sub, today)

    @classmethod
    def process_trial_expirations(cls, today):
        """
        Find venues in trial whose next_billing_date < today.
        Attempt to charge for first month; if successful, move to 'active';
        otherwise suspend.
        """
        trial_venues = Venue.objects.filter(
            subscription_status='trial',
            next_billing_date__lt=today
        )

        for venue in trial_venues:
            logger.info(f"Processing trial expiration for {venue.business_name}")
            price = cls.get_tier_price(venue.subscription_tier)

            # Attempt to charge first month
            success = cls.attempt_payment(venue, price)

            if success:
                venue.subscription_status = 'active'
                venue.next_billing_date = today + timedelta(days=30)
                venue.billing_cycle_start = today
                venue.save()
                NotificationService.send_trial_ended(venue, paid=True)
                logger.info(f"Trial ended for {venue.business_name}, first payment successful.")
            else:
                venue.subscription_status = 'suspended'
                venue.save()
                NotificationService.send_trial_ended(venue, paid=False)
                logger.warning(f"Trial ended for {venue.business_name}, payment failed. Venue suspended.")

    @classmethod
    def process_subscription(cls, subscription, today):
        """
        Attempt to charge a single active subscription.
        """
        venue = subscription.venue
        tier = subscription.tier
        price = cls.get_tier_price(tier)

        success = cls.attempt_payment(venue, price)

        if success:
            subscription.last_billing_date = today
            subscription.next_billing_date = today + timedelta(days=30)
            subscription.arrears = Decimal('0.00')
            subscription.save()
            logger.info(f"Charged {venue.business_name} KES {price}")
        else:
            subscription.arrears += Decimal(str(price))
            subscription.save()
            if subscription.arrears >= price * cls.GRACE_PERIOD_DAYS:
                cls.suspend_venue(venue)
                logger.warning(f"Suspended {venue.business_name} for non-payment")

    @classmethod
    def attempt_payment(cls, venue, amount):
        """
        Attempt to charge the venue's saved payment method.
        Returns True if successful, False otherwise.
        """
        # Placeholder: implement actual gateway call using venue.payment_config
        # For now, simulate success/failure based on random
        # In production, call your payment gateway
        try:
            # Example: use payment_method_token stored in Subscription
            # sub = Subscription.objects.get(venue=venue)
            # gateway = PaymentService.charge_token(sub.payment_method_token, amount)
            # return True if successful
            return True
        except Exception:
            return False

    @classmethod
    def suspend_venue(cls, venue):
        venue.subscription_status = 'suspended'
        venue.save()

    @classmethod
    def reactivate_venue(cls, venue):
        venue.subscription_status = 'active'
        venue.save()

    @classmethod
    def get_tier_price(cls, tier):
        prices = {
            'seed': 5000,
            'spark': 10000,
            'rose': 15000,
            'summit': 20000,
            'elite': 25000,
            'legacy': 30000,
        }
        return Decimal(str(prices.get(tier, 0)))

    @classmethod
    def get_reconciliation_summary(cls, start_date, end_date):
        # Placeholder: implement actual query
        return {
            'total_platform_fees': Decimal('100000.00'),
            'total_ticket_revenue': Decimal('500000.00'),
            'total_venue_payouts': Decimal('400000.00'),
            'period_start': start_date,
            'period_end': end_date,
            'venues_breakdown': {}
        }
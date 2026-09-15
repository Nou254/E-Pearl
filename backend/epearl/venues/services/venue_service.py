# venues/services/venue_service.py

from django.utils import timezone
from django.conf import settings
from datetime import timedelta
from ..models import Venue
from .subdomain_service import SubdomainService


class VenueService:
    @staticmethod
    def create_venue(validated_data, **extra_fields):
        """
        Create a new venue, starting a trial period.
        """
        business_name = validated_data.get('business_name')
        sub_domain = SubdomainService.generate_subdomain(business_name)
        
        # Calculate trial dates
        trial_days = getattr(settings, 'TRIAL_PERIOD_DAYS', 14)
        trial_start = timezone.now().date()
        next_billing = trial_start + timedelta(days=trial_days)
        
        venue = Venue.objects.create(
            sub_domain=sub_domain,
            subscription_status='trial',
            document_verification_status='pending',
            trial_start_date=trial_start,
            next_billing_date=next_billing,
            billing_cycle_start=trial_start,
            **validated_data,
            **extra_fields
        )
        return venue

    @staticmethod
    def update_venue(venue, validated_data):
        for attr, value in validated_data.items():
            setattr(venue, attr, value)
        venue.save()
        return venue

    @staticmethod
    def get_booking_rules(venue):
        """Return a dict of booking rules for this venue."""
        return {
            'deposit_type': venue.booking_deposit_type,
            'deposit_amount': float(venue.booking_deposit_amount),
            'cancellation_hours': venue.booking_cancellation_hours,
            'advance_days': venue.table_booking_advance_days,
            'max_party_size': venue.max_party_size,
            'min_hire_hours': venue.min_hire_period_hours,
            'blackout_dates': venue.hire_blackout_dates,
        }

    @staticmethod
    def start_trial(venue):
        """
        Manually start or restart a trial for a venue.
        Sets trial_start_date and next_billing_date.
        """
        trial_days = getattr(settings, 'TRIAL_PERIOD_DAYS', 14)
        trial_start = timezone.now().date()
        venue.trial_start_date = trial_start
        venue.next_billing_date = trial_start + timedelta(days=trial_days)
        venue.billing_cycle_start = trial_start
        venue.subscription_status = 'trial'
        venue.save(update_fields=[
            'trial_start_date', 'next_billing_date',
            'billing_cycle_start', 'subscription_status'
        ])
        return venue
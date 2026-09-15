# venues/serializers.py

from rest_framework import serializers
from .models import Venue, VenueRefundPolicy


class VenueRefundPolicySerializer(serializers.ModelSerializer):
    class Meta:
        model = VenueRefundPolicy
        fields = [
            'id', 'venue', 'cancellation_policy', 'full_refund_window_hours',
            'partial_refund_window_hours', 'partial_refund_percentage',
            'no_show_charge_percentage', 'venue_cancellation_refund',
            'rescheduling_allowed', 'rescheduling_fee', 'force_majeure_policy',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class VenueSerializer(serializers.ModelSerializer):
    """Default read-only serializer."""
    refund_policy = VenueRefundPolicySerializer(read_only=True)

    class Meta:
        model = Venue
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at']


class VenueRegistrationSerializer(serializers.ModelSerializer):
    """
    Serializer used when registering a new venue.
    All booking rules are optional and can be set later.
    """
    class Meta:
        model = Venue
        fields = [
            'business_name',
            'registration_number',
            'kra_pin',
            'contact_phone',
            'contact_email',
            'physical_address',
            'gps_coordinates',
            'subscription_tier',
            'public_listing',
            'operating_hours',
            'description',
            'cover_image_url',
            'logo_url',
            # Booking rules (optional at registration)
            'booking_deposit_type',
            'booking_deposit_amount',
            'booking_cancellation_hours',
            'table_booking_advance_days',
            'max_party_size',
            'min_hire_period_hours',
            'hire_blackout_dates',
        ]
        read_only_fields = [
            'sub_domain',
            'document_verification_status',
            'subscription_status',
            'next_billing_date',
            'trial_start_date',
        ]

    def validate_kra_pin(self, value):
        if not value or len(value) < 5:
            raise serializers.ValidationError("KRA PIN must be at least 5 characters.")
        return value.upper()

    def validate_contact_phone(self, value):
        if not value:
            raise serializers.ValidationError("Contact phone is required.")
        return value


class VenueUpdateSerializer(serializers.ModelSerializer):
    """For updating venue details after registration."""
    class Meta:
        model = Venue
        fields = [
            'business_name', 'contact_phone', 'contact_email',
            'physical_address', 'gps_coordinates', 'operating_hours',
            'description', 'cover_image_url', 'logo_url', 'public_listing',
            # Booking rules (editable by manager)
            'booking_deposit_type',
            'booking_deposit_amount',
            'booking_cancellation_hours',
            'table_booking_advance_days',
            'max_party_size',
            'min_hire_period_hours',
            'hire_blackout_dates',
            'auto_capture_enabled',
        ]
        read_only_fields = [
            'sub_domain',
            'document_verification_status',
            'subscription_status',
            'next_billing_date',
            'trial_start_date',
        ]


class VenueRefundPolicyUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating refund policy via Control."""
    class Meta:
        model = VenueRefundPolicy
        fields = [
            'cancellation_policy', 'full_refund_window_hours',
            'partial_refund_window_hours', 'partial_refund_percentage',
            'no_show_charge_percentage', 'venue_cancellation_refund',
            'rescheduling_allowed', 'rescheduling_fee', 'force_majeure_policy',
        ]


class VenueTrialStatusSerializer(serializers.Serializer):
    """Return trial days remaining and status."""
    trial_days_remaining = serializers.IntegerField()
    trial_days_total = serializers.IntegerField()
    status = serializers.CharField()
    trial_start_date = serializers.DateField()
    next_billing_date = serializers.DateField()
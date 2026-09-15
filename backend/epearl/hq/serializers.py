# hq/serializers.py

from rest_framework import serializers
from .models import (
    PlatformSetting, SMSCredit, APIKey,
    ServiceStatus, RequestLog, FeatureFlag, Subscription
)
from payments.models import RefundRequest, RefundTransaction
from venues.models import Venue


# Existing serializers
class PlatformSettingSerializer(serializers.ModelSerializer):
    class Meta:
        model = PlatformSetting
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at']


class SMSCreditSerializer(serializers.ModelSerializer):
    class Meta:
        model = SMSCredit
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at']


class APIKeySerializer(serializers.ModelSerializer):
    class Meta:
        model = APIKey
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at']


# New serializers
class ServiceStatusSerializer(serializers.ModelSerializer):
    class Meta:
        model = ServiceStatus
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at']


class RequestLogSerializer(serializers.ModelSerializer):
    user_email = serializers.CharField(source='user.email', read_only=True, allow_null=True)
    venue_name = serializers.CharField(source='venue.business_name', read_only=True, allow_null=True)

    class Meta:
        model = RequestLog
        fields = [
            'id', 'user', 'user_email', 'venue', 'venue_name', 'method', 'path',
            'endpoint', 'status_code', 'response_time_ms', 'ip_address',
            'user_agent', 'request_body', 'timestamp', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'timestamp', 'created_at', 'updated_at']


class RequestLogSearchSerializer(serializers.ModelSerializer):
    user_email = serializers.CharField(source='user.email', read_only=True, allow_null=True)
    venue_name = serializers.CharField(source='venue.business_name', read_only=True, allow_null=True)
    relevance = serializers.FloatField(read_only=True)

    class Meta:
        model = RequestLog
        fields = [
            'id', 'user', 'user_email', 'venue', 'venue_name', 'method', 'path',
            'endpoint', 'status_code', 'response_time_ms', 'ip_address',
            'user_agent', 'request_body', 'timestamp', 'relevance',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'timestamp', 'created_at', 'updated_at']


class FeatureFlagSerializer(serializers.ModelSerializer):
    venue_name = serializers.CharField(source='venue.business_name', read_only=True)

    class Meta:
        model = FeatureFlag
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at']


class SubscriptionSerializer(serializers.ModelSerializer):
    venue_name = serializers.CharField(source='venue.business_name', read_only=True)

    class Meta:
        model = Subscription
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at']


# Financial reconciliation serializers
class ReconciliationSummarySerializer(serializers.Serializer):
    total_platform_fees = serializers.DecimalField(max_digits=12, decimal_places=2)
    total_ticket_revenue = serializers.DecimalField(max_digits=12, decimal_places=2)
    total_venue_payouts = serializers.DecimalField(max_digits=12, decimal_places=2)
    period_start = serializers.DateField()
    period_end = serializers.DateField()
    venues_breakdown = serializers.DictField()


class SystemStatusSerializer(serializers.Serializer):
    cpu_usage = serializers.FloatField()
    memory_usage = serializers.FloatField()
    disk_usage = serializers.FloatField()
    db_connections = serializers.IntegerField()
    redis_connections = serializers.IntegerField()
    last_updated = serializers.DateTimeField()


# =============================================================================
# NEW: Refund Review Serializers
# =============================================================================

class RefundTransactionBriefSerializer(serializers.ModelSerializer):
    class Meta:
        model = RefundTransaction
        fields = ['id', 'amount', 'status', 'gateway_reference_id', 'processed_at']


class RefundReviewListSerializer(serializers.ModelSerializer):
    """
    Lightweight serializer for list view of refund requests.
    """
    customer_name = serializers.CharField(source='customer.get_full_name', read_only=True)
    customer_email = serializers.CharField(source='customer.email', read_only=True)
    venue_name = serializers.CharField(source='venue.business_name', read_only=True)
    booking_id = serializers.UUIDField(source='booking.id', read_only=True)

    class Meta:
        model = RefundRequest
        fields = [
            'id', 'booking', 'booking_id', 'customer', 'customer_name', 'customer_email',
            'venue', 'venue_name', 'reason', 'classification', 'requested_amount',
            'approved_amount', 'status', 'created_at', 'updated_at'
        ]
        read_only_fields = fields


class RefundReviewSerializer(serializers.ModelSerializer):
    """
    Detailed serializer for single refund request review.
    Includes transaction and refund transactions.
    """
    customer_name = serializers.CharField(source='customer.get_full_name', read_only=True)
    customer_email = serializers.CharField(source='customer.email', read_only=True)
    customer_phone = serializers.CharField(source='customer.phone', read_only=True)
    venue_name = serializers.CharField(source='venue.business_name', read_only=True)
    booking_details = serializers.SerializerMethodField()
    original_transaction = serializers.SerializerMethodField()
    refund_transactions = RefundTransactionBriefSerializer(many=True, read_only=True)

    class Meta:
        model = RefundRequest
        fields = [
            'id', 'booking', 'customer', 'customer_name', 'customer_email', 'customer_phone',
            'venue', 'venue_name', 'reason', 'classification', 'requested_amount',
            'approved_amount', 'status', 'resolution_notes', 'reviewed_by',
            'reviewed_at', 'metadata', 'booking_details', 'original_transaction',
            'refund_transactions', 'created_at', 'updated_at'
        ]
        read_only_fields = fields

    def get_booking_details(self, obj):
        from explore.serializers import BookingSerializer
        return BookingSerializer(obj.booking).data

    def get_original_transaction(self, obj):
        from payments.serializers import TransactionSerializer
        return TransactionSerializer(obj.transaction).data


# =============================================================================
# NEW: Trial Management Serializer
# =============================================================================

class TrialManagementSerializer(serializers.ModelSerializer):
    trial_days_remaining = serializers.SerializerMethodField()
    trial_days_total = serializers.IntegerField(default=14)

    class Meta:
        model = Venue
        fields = [
            'id', 'business_name', 'sub_domain', 'subscription_status',
            'trial_start_date', 'next_billing_date', 'trial_days_remaining',
            'trial_days_total', 'contact_email', 'contact_phone'
        ]

    def get_trial_days_remaining(self, obj):
        if not obj.trial_start_date:
            return 0
        trial_days_total = getattr(settings, 'TRIAL_PERIOD_DAYS', 14)
        days_used = (timezone.now().date() - obj.trial_start_date).days
        return max(0, trial_days_total - days_used)
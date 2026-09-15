# payments/serializers.py

from rest_framework import serializers
from .models import (
    Transaction, PreAuthHold, PaymentGatewayConfig,
    RefundRequest, RefundTransaction
)


class TransactionSerializer(serializers.ModelSerializer):
    venue_name = serializers.CharField(source='venue.business_name', read_only=True)

    class Meta:
        model = Transaction
        fields = [
            'id', 'venue', 'venue_name', 'guest_session', 'user',
            'booking', 'ticket', 'pre_auth_hold', 'order',
            'transaction_type', 'amount', 'currency', 'payment_method',
            'gateway_reference_id', 'gateway_response_code', 'gateway_response_message',
            'transaction_status', 'transaction_time', 'metadata',
            'idempotency_key', 'gateway_latency_ms', 'retry_count',
            'refund_status', 'amount_refunded',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class PreAuthHoldSerializer(serializers.ModelSerializer):
    venue_name = serializers.CharField(source='venue.business_name', read_only=True)
    guest_session_id = serializers.UUIDField(source='guest_session.id', read_only=True)

    class Meta:
        model = PreAuthHold
        fields = [
            'id', 'venue', 'venue_name', 'guest_session', 'guest_session_id',
            'declared_amount', 'consumed_amount', 'remaining_balance',
            'hold_status', 'payment_method', 'gateway_reference_id',
            'payment_token', 'hold_time', 'capture_time', 'void_time',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class PaymentGatewayConfigSerializer(serializers.ModelSerializer):
    venue_name = serializers.CharField(source='venue.business_name', read_only=True)

    class Meta:
        model = PaymentGatewayConfig
        fields = [
            'id', 'venue', 'venue_name', 'gateway_provider',
            'merchant_id', 'consumer_key', 'consumer_secret',
            'passkey', 'shortcode', 'environment', 'status',
            'last_tested', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'last_tested']
        extra_kwargs = {
            'consumer_key': {'write_only': True},
            'consumer_secret': {'write_only': True},
            'passkey': {'write_only': True},
        }


# ========== REFUND SERIALIZERS ==========

class RefundTransactionSerializer(serializers.ModelSerializer):
    class Meta:
        model = RefundTransaction
        fields = [
            'id', 'original_transaction', 'refund_request', 'amount',
            'gateway_reference_id', 'gateway_response_code', 'gateway_response_message',
            'status', 'processed_at', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'processed_at', 'created_at', 'updated_at']


class RefundRequestSerializer(serializers.ModelSerializer):
    customer_name = serializers.CharField(source='customer.get_full_name', read_only=True)
    venue_name = serializers.CharField(source='venue.business_name', read_only=True)
    refund_transactions = RefundTransactionSerializer(many=True, read_only=True)

    class Meta:
        model = RefundRequest
        fields = [
            'id', 'booking', 'transaction', 'customer', 'customer_name',
            'venue', 'venue_name', 'reason', 'classification',
            'requested_amount', 'approved_amount', 'status',
            'reviewed_by', 'reviewed_at', 'resolution_notes',
            'metadata', 'refund_transactions',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'customer', 'venue', 'classification']


class RefundRequestCreateSerializer(serializers.Serializer):
    booking_id = serializers.UUIDField()
    reason = serializers.ChoiceField(choices=RefundRequest.REASON_CHOICES)
    requested_amount = serializers.DecimalField(max_digits=10, decimal_places=2)
    notes = serializers.CharField(required=False, allow_blank=True)


class RefundRequestReviewSerializer(serializers.Serializer):
    action = serializers.ChoiceField(choices=[('approve', 'Approve'), ('reject', 'Reject')])
    approved_amount = serializers.DecimalField(max_digits=10, decimal_places=2, required=False)
    resolution_notes = serializers.CharField(required=False, allow_blank=True)


# ========== ANALYTICS SERIALIZERS (existing) ==========

class PaymentAnalyticsSerializer(serializers.Serializer):
    total_transactions = serializers.IntegerField()
    successful = serializers.IntegerField()
    failed = serializers.IntegerField()
    pending = serializers.IntegerField()
    success_rate = serializers.FloatField()
    total_amount = serializers.CharField()
    by_payment_method = serializers.ListField()
    top_venues = serializers.ListField()
    daily_trend = serializers.ListField()
    avg_latency_ms = serializers.FloatField()


class UserSpendingSerializer(serializers.Serializer):
    total_spent = serializers.CharField()
    transaction_count = serializers.IntegerField()
    by_type = serializers.ListField()
    recent_transactions = TransactionSerializer(many=True)
# events/serializers.py

from rest_framework import serializers
from .models import Event, TicketTier, Ticket


class EventSerializer(serializers.ModelSerializer):
    venue_name = serializers.CharField(source='venue.business_name', read_only=True)
    tickets_remaining = serializers.SerializerMethodField()

    class Meta:
        model = Event
        fields = [
            'id', 'venue', 'venue_name', 'event_name', 'event_description',
            'event_date', 'event_start_time', 'event_end_time',
            'max_capacity', 'ticket_sales_start', 'ticket_sales_end',
            'door_policy', 'flyer_image_url', 'status',
            'checked_in_count', 'total_tickets_sold',
            'gross_revenue', 'platform_fee_collected',
            'tickets_remaining', 'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'checked_in_count', 'total_tickets_sold',
            'gross_revenue', 'platform_fee_collected', 'created_at', 'updated_at'
        ]

    def get_tickets_remaining(self, obj):
        return obj.tickets_remaining()


class EventCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Event
        fields = [
            'event_name', 'event_description', 'event_date',
            'event_start_time', 'event_end_time', 'max_capacity',
            'ticket_sales_start', 'ticket_sales_end',
            'door_policy', 'flyer_image_url'
        ]
        read_only_fields = ['id', 'status']


class TicketTierSerializer(serializers.ModelSerializer):
    event_name = serializers.CharField(source='event.event_name', read_only=True)
    quantity_remaining = serializers.SerializerMethodField()

    class Meta:
        model = TicketTier
        fields = [
            'id', 'venue', 'event', 'event_name',
            'tier_name', 'tier_description', 'price',
            'quantity_limit', 'quantity_sold', 'quantity_remaining',
            'is_vip', 'reserved_table',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'quantity_sold', 'created_at', 'updated_at']

    def get_quantity_remaining(self, obj):
        return obj.quantity_limit - obj.quantity_sold


class TicketSerializer(serializers.ModelSerializer):
    event_name = serializers.CharField(source='event.event_name', read_only=True)
    tier_name = serializers.CharField(source='ticket_tier.tier_name', read_only=True)

    class Meta:
        model = Ticket
        fields = [
            'id', 'venue', 'event', 'event_name',
            'ticket_tier', 'tier_name', 'guest_session', 'user',
            'ticket_code', 'ticket_qr', 'customer_name',
            'customer_email', 'customer_phone', 'price',
            'platform_fee', 'manual_exit_code', 'is_digital',
            'checked_in', 'checked_in_time', 'exited',
            'exited_time', 'status', 'purchase_time',
            'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'ticket_code', 'ticket_qr', 'price',
            'platform_fee', 'checked_in', 'checked_in_time',
            'exited', 'exited_time', 'status', 'purchase_time',
            'created_at', 'updated_at'
        ]


class TicketPurchaseSerializer(serializers.Serializer):
    venue_id = serializers.UUIDField()
    event_id = serializers.UUIDField()
    tier_id = serializers.UUIDField()
    customer = serializers.DictField(child=serializers.CharField())


# =============================================================================
# NEW: Reporting Serializers
# =============================================================================

class TierBreakdownSerializer(serializers.Serializer):
    tier_id = serializers.CharField()
    tier_name = serializers.CharField()
    price = serializers.FloatField()
    quantity_sold = serializers.IntegerField()
    revenue = serializers.FloatField()
    is_vip = serializers.BooleanField()


class AttendeeSerializer(serializers.Serializer):
    ticket_code = serializers.CharField()
    customer_name = serializers.CharField()
    customer_email = serializers.EmailField()
    customer_phone = serializers.CharField()
    tier_name = serializers.CharField()
    checked_in_time = serializers.DateTimeField()
    exited = serializers.BooleanField()


class SalesTrendSerializer(serializers.Serializer):
    date = serializers.CharField()
    tickets_sold = serializers.IntegerField()
    revenue = serializers.FloatField()


class EventReportSerializer(serializers.Serializer):
    event_id = serializers.CharField()
    event_name = serializers.CharField()
    event_date = serializers.DateField()
    event_start_time = serializers.TimeField()
    event_end_time = serializers.TimeField(required=False)
    max_capacity = serializers.IntegerField()
    total_tickets_sold = serializers.IntegerField()
    checked_in_count = serializers.IntegerField()
    no_show_count = serializers.IntegerField()
    gross_revenue = serializers.FloatField()
    platform_fee_collected = serializers.FloatField()
    net_revenue = serializers.FloatField()
    tier_breakdown = TierBreakdownSerializer(many=True)
    attendees = AttendeeSerializer(many=True)
    sales_trend = SalesTrendSerializer(many=True)


class PlatformReportSerializer(serializers.Serializer):
    period_start = serializers.DateField()
    period_end = serializers.DateField()
    total_events = serializers.IntegerField()
    total_tickets_sold = serializers.IntegerField()
    total_checkins = serializers.IntegerField()
    total_gross_revenue = serializers.FloatField()
    total_platform_fees = serializers.FloatField()
    total_net_revenue = serializers.FloatField()
    event_breakdown = serializers.ListField()
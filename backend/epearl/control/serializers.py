# control/serializers.py

from rest_framework import serializers
from .models import (
    PlatformAuditLog, VenueHealthMetrics, HQNotification,
    SupportTicket, VenueAuditLog,
    MenuCategory, MenuItem, Modifier,
    OnboardingProgress, StockAlertLog,
    WastageLog, MenuVersion
)
from venues.models import VenueRefundPolicy


class PlatformAuditLogSerializer(serializers.ModelSerializer):
    actor_email = serializers.CharField(source='actor.email', read_only=True)

    class Meta:
        model = PlatformAuditLog
        fields = [
            'id', 'actor', 'actor_email', 'action_type', 'target_model',
            'target_id', 'description', 'metadata', 'ip_address',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class VenueAuditLogSerializer(serializers.ModelSerializer):
    staff_name = serializers.CharField(source='staff.user.full_name', read_only=True)
    venue_name = serializers.CharField(source='venue.business_name', read_only=True)

    class Meta:
        model = VenueAuditLog
        fields = [
            'id', 'venue', 'venue_name', 'staff', 'staff_name',
            'guest_session', 'table', 'action_type', 'action_description',
            'amount', 'reason', 'ip_address', 'metadata', 'timestamp',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'timestamp', 'created_at', 'updated_at']


class VenueHealthMetricsSerializer(serializers.ModelSerializer):
    venue_name = serializers.CharField(source='venue.business_name', read_only=True)
    occupancy_rate = serializers.SerializerMethodField()

    class Meta:
        model = VenueHealthMetrics
        fields = [
            'id', 'venue', 'venue_name', 'active_guests',
            'occupied_tables', 'total_tables', 'occupancy_rate',
            'pending_orders', 'revenue_today', 'transactions_today',
            'staff_on_duty', 'open_tickets', 'avg_turnaround_minutes',
            'last_updated'
        ]
        read_only_fields = ['id', 'last_updated']

    def get_occupancy_rate(self, obj):
        return obj.occupancy_rate()


class HQNotificationSerializer(serializers.ModelSerializer):
    venue_name = serializers.CharField(source='venue.business_name', read_only=True, allow_null=True)
    resolved_by_email = serializers.CharField(source='resolved_by.email', read_only=True, allow_null=True)

    class Meta:
        model = HQNotification
        fields = [
            'id', 'title', 'message', 'category', 'priority',
            'venue', 'venue_name', 'is_read', 'resolved_by',
            'resolved_by_email', 'resolved_at', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class SupportTicketSerializer(serializers.ModelSerializer):
    venue_name = serializers.CharField(source='venue.business_name', read_only=True)
    raised_by_email = serializers.CharField(source='raised_by.email', read_only=True)
    assigned_to_email = serializers.CharField(source='assigned_to.email', read_only=True, allow_null=True)

    class Meta:
        model = SupportTicket
        fields = [
            'id', 'venue', 'venue_name', 'raised_by', 'raised_by_email',
            'assigned_to', 'assigned_to_email', 'subject', 'description',
            'category', 'status', 'priority', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class KPISerializer(serializers.Serializer):
    active_tables = serializers.IntegerField()
    total_tables = serializers.IntegerField()
    occupancy = serializers.IntegerField()
    gross_revenue = serializers.FloatField()
    pending_interventions = serializers.IntegerField()
    bookings_total = serializers.IntegerField()
    bookings_today = serializers.IntegerField()


class PlatformDashboardSerializer(serializers.Serializer):
    total_venues = serializers.IntegerField()
    active_venues = serializers.IntegerField()
    pending_verifications = serializers.IntegerField()
    total_users = serializers.IntegerField()
    active_users = serializers.IntegerField()
    total_revenue = serializers.DecimalField(max_digits=12, decimal_places=2)
    revenue_this_month = serializers.DecimalField(max_digits=12, decimal_places=2)
    open_tickets = serializers.IntegerField()
    unread_notifications = serializers.IntegerField()
    venues_by_tier = serializers.DictField()
    recent_audit_logs = PlatformAuditLogSerializer(many=True)
    top_venues_by_revenue = serializers.ListField()


# =============================================================================
# Menu Builder Serializers
# =============================================================================

class MenuCategorySerializer(serializers.ModelSerializer):
    item_count = serializers.SerializerMethodField()

    class Meta:
        model = MenuCategory
        fields = [
            'id', 'venue', 'name', 'description', 'display_order',
            'is_active', 'item_count', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

    def get_item_count(self, obj):
        return obj.items.filter(is_active=True).count()


class MenuItemSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source='category.name', read_only=True)
    venue_name = serializers.CharField(source='venue.business_name', read_only=True)
    is_low_stock = serializers.BooleanField(read_only=True)
    is_out_of_stock = serializers.BooleanField(read_only=True)

    class Meta:
        model = MenuItem
        fields = [
            'id', 'venue', 'venue_name', 'category', 'category_name',
            'name', 'description', 'price', 'image_url', 'item_type',
            'is_active', 'is_available', 'display_order',
            'stock_count', 'low_stock_threshold', 'is_low_stock', 'is_out_of_stock',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class ModifierSerializer(serializers.ModelSerializer):
    menu_item_name = serializers.CharField(source='menu_item.name', read_only=True)

    class Meta:
        model = Modifier
        fields = [
            'id', 'venue', 'menu_item', 'menu_item_name',
            'name', 'options', 'is_required', 'is_active',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class MenuItemPublicSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source='category.name', read_only=True)
    modifiers = ModifierSerializer(many=True, read_only=True)

    class Meta:
        model = MenuItem
        fields = [
            'id', 'name', 'description', 'price', 'image_url',
            'item_type', 'category_name', 'modifiers'
        ]


class OnboardingSerializer(serializers.ModelSerializer):
    class Meta:
        model = OnboardingProgress
        fields = [
            'id', 'venue', 'step', 'documents_uploaded', 'owner_verified',
            'profile_configured', 'floor_plan_configured', 'menu_configured',
            'payment_configured', 'completed_at', 'last_error'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


# =============================================================================
# Wastage & Menu Versioning Serializers
# =============================================================================

class WastageLogSerializer(serializers.ModelSerializer):
    venue_name = serializers.CharField(source='venue.business_name', read_only=True)
    menu_item_name = serializers.CharField(source='menu_item.name', read_only=True)
    created_by_name = serializers.CharField(source='created_by.full_name', read_only=True)
    written_off_by_name = serializers.CharField(source='written_off_by.full_name', read_only=True)

    class Meta:
        model = WastageLog
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at']


class MenuVersionSerializer(serializers.ModelSerializer):
    menu_item_name = serializers.CharField(source='menu_item.name', read_only=True)
    changed_by_name = serializers.CharField(source='changed_by.full_name', read_only=True)

    class Meta:
        model = MenuVersion
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at']


# =============================================================================
# Full‑Text Search Serializer
# =============================================================================

class MenuItemSearchSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source='category.name', read_only=True)
    relevance = serializers.FloatField(read_only=True)

    class Meta:
        model = MenuItem
        fields = [
            'id', 'name', 'description', 'price', 'image_url',
            'item_type', 'category_name', 'is_active', 'is_available',
            'stock_count', 'relevance'
        ]


class VenueAuditLogSearchSerializer(serializers.ModelSerializer):
    staff_name = serializers.CharField(source='staff.user.full_name', read_only=True)
    venue_name = serializers.CharField(source='venue.business_name', read_only=True)
    relevance = serializers.FloatField(read_only=True)

    class Meta:
        model = VenueAuditLog
        fields = [
            'id', 'venue', 'venue_name', 'staff', 'staff_name',
            'action_type', 'action_description', 'amount', 'reason',
            'timestamp', 'relevance'
        ]


# =============================================================================
# NEW: Refund Policy Serializer
# =============================================================================

class VenueRefundPolicySerializer(serializers.ModelSerializer):
    venue_name = serializers.CharField(source='venue.business_name', read_only=True)

    class Meta:
        model = VenueRefundPolicy
        fields = [
            'id', 'venue', 'venue_name', 'cancellation_policy',
            'full_refund_window_hours', 'partial_refund_window_hours',
            'partial_refund_percentage', 'no_show_charge_percentage',
            'venue_cancellation_refund', 'rescheduling_allowed',
            'rescheduling_fee', 'force_majeure_policy',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'venue', 'created_at', 'updated_at']


# =============================================================================
# NEW: Trial Status Serializer
# =============================================================================

class TrialStatusSerializer(serializers.Serializer):
    trial_days_remaining = serializers.IntegerField()
    trial_days_total = serializers.IntegerField()
    subscription_status = serializers.CharField()
    trial_start_date = serializers.DateField(allow_null=True)
    next_billing_date = serializers.DateField(allow_null=True)
    is_trial_ending_soon = serializers.BooleanField()
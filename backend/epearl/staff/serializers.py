# staff/serializers.py

from rest_framework import serializers
from .models import (
    Staff, Shift, ShiftStaff, StaffAttendance,
    ShiftHandover, CashCollection, PerformanceMetric
)
from users.models import StaffPermission, User
from users.serializers import UserSerializer


class StaffSerializer(serializers.ModelSerializer):
    user_detail = UserSerializer(source='user', read_only=True)
    venue_name = serializers.CharField(source='venue.business_name', read_only=True)
    zone_name = serializers.CharField(source='assigned_zone.name', read_only=True)

    class Meta:
        model = Staff
        fields = [
            'id', 'user', 'user_detail', 'venue', 'venue_name',
            'role', 'assigned_zone', 'zone_name', 'staff_qr',
            'is_active', 'shifts', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'staff_qr', 'created_at', 'updated_at']


class StaffCreateSerializer(serializers.ModelSerializer):
    phone = serializers.CharField(write_only=True)
    email = serializers.EmailField(required=False, write_only=True)
    full_name = serializers.CharField(required=False, write_only=True)
    shift_ids = serializers.ListField(
        child=serializers.UUIDField(),
        required=False,
        write_only=True
    )

    class Meta:
        model = Staff
        fields = [
            'phone', 'email', 'full_name', 'role', 'assigned_zone', 'shift_ids'
        ]

    def validate(self, data):
        if not data.get('phone') and not data.get('email'):
            raise serializers.ValidationError("Either phone or email is required.")
        return data


class ShiftSerializer(serializers.ModelSerializer):
    class Meta:
        model = Shift
        fields = [
            'id', 'venue', 'shift_name', 'start_time', 'end_time',
            'days_of_week', 'zone', 'status', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class ShiftStaffSerializer(serializers.ModelSerializer):
    staff_name = serializers.CharField(source='staff.user.full_name', read_only=True)
    shift_name = serializers.CharField(source='shift.shift_name', read_only=True)

    class Meta:
        model = ShiftStaff
        fields = [
            'id', 'staff', 'staff_name', 'shift', 'shift_name',
            'is_primary', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class StaffAttendanceSerializer(serializers.ModelSerializer):
    staff_name = serializers.CharField(source='staff.user.full_name', read_only=True)
    shift_name = serializers.CharField(source='shift.shift_name', read_only=True)
    reconciled_by_name = serializers.CharField(source='reconciled_by.user.full_name', read_only=True)

    class Meta:
        model = StaffAttendance
        fields = [
            'id', 'staff', 'staff_name', 'shift', 'shift_name',
            'scan_in_time', 'scan_out_time',
            'cash_collected', 'cash_reconciled',
            'reconciled_by', 'reconciled_by_name', 'reconciled_at',
            'scan_in_device', 'scan_out_device',
            'attendance_status', 'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'cash_reconciled', 'reconciled_by', 'reconciled_at',
            'created_at', 'updated_at'
        ]


# =============================================================================
# Staff Permission Serializer
# =============================================================================

class StaffPermissionSerializer(serializers.ModelSerializer):
    staff_name = serializers.CharField(source='staff.user.full_name', read_only=True)
    granted_by_name = serializers.CharField(source='granted_by.full_name', read_only=True)

    class Meta:
        model = StaffPermission
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at', 'granted_at', 'granted_by']


# =============================================================================
# Shift Handover Serializer
# =============================================================================

class ShiftHandoverSerializer(serializers.ModelSerializer):
    from_staff_name = serializers.CharField(source='from_staff.user.full_name', read_only=True)
    to_staff_name = serializers.CharField(source='to_staff.user.full_name', read_only=True)

    class Meta:
        model = ShiftHandover
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at', 'handed_over_at']


# =============================================================================
# Cash Collection Serializer
# =============================================================================

class CashCollectionSerializer(serializers.ModelSerializer):
    staff_name = serializers.CharField(source='staff.user.full_name', read_only=True)
    table_number = serializers.CharField(source='table.table_number', read_only=True)
    reconciled_by_name = serializers.CharField(source='reconciled_by.full_name', read_only=True)

    class Meta:
        model = CashCollection
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at', 'collected_at']


# =============================================================================
# Staff Performance Serializer
# =============================================================================

class StaffPerformanceSerializer(serializers.Serializer):
    waiter_id = serializers.UUIDField()
    waiter_name = serializers.CharField()
    total_orders = serializers.IntegerField()
    total_revenue = serializers.FloatField()
    avg_turnaround_minutes = serializers.FloatField()
    satisfaction = serializers.FloatField()

    period_start = serializers.DateTimeField(required=False)
    period_end = serializers.DateTimeField(required=False)


# =============================================================================
# NEW: Full‑text Search Serializer for Staff
# =============================================================================

class StaffSearchSerializer(serializers.ModelSerializer):
    full_name = serializers.CharField(source='user.full_name', read_only=True)
    phone = serializers.CharField(source='user.phone', read_only=True)
    email = serializers.CharField(source='user.email', read_only=True)
    relevance = serializers.FloatField(read_only=True)
    venue_name = serializers.CharField(source='venue.business_name', read_only=True)

    class Meta:
        model = Staff
        fields = [
            'id', 'full_name', 'phone', 'email', 'role',
            'venue', 'venue_name', 'assigned_zone', 'is_active',
            'relevance'
        ]
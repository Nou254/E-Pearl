# staff/admin.py

from django.contrib import admin
from .models import (
    Staff, Shift, ShiftStaff, StaffAttendance,
    ShiftHandover, CashCollection, PerformanceMetric  # NEW
)


@admin.register(Staff)
class StaffAdmin(admin.ModelAdmin):
    list_display = ['user', 'venue', 'role', 'is_active']
    list_filter = ['venue', 'role', 'is_active']
    search_fields = ['user__full_name', 'user__phone']


@admin.register(Shift)
class ShiftAdmin(admin.ModelAdmin):
    list_display = ['shift_name', 'venue', 'start_time', 'end_time', 'status']
    list_filter = ['venue', 'status']
    search_fields = ['shift_name']


@admin.register(ShiftStaff)
class ShiftStaffAdmin(admin.ModelAdmin):
    list_display = ['staff', 'shift', 'is_primary']
    list_filter = ['is_primary']
    search_fields = ['staff__user__full_name', 'shift__shift_name']


@admin.register(StaffAttendance)
class StaffAttendanceAdmin(admin.ModelAdmin):
    list_display = ['staff', 'scan_in_time', 'scan_out_time', 'attendance_status']
    list_filter = ['attendance_status']
    search_fields = ['staff__user__full_name']
    readonly_fields = ['scan_in_time', 'scan_out_time', 'reconciled_at']


# =============================================================================
# NEW: Admin registrations for ShiftHandover, CashCollection, PerformanceMetric
# =============================================================================

@admin.register(ShiftHandover)
class ShiftHandoverAdmin(admin.ModelAdmin):
    list_display = ['from_staff', 'to_staff', 'tables_transferred', 'handed_over_at']
    list_filter = ['venue']
    search_fields = ['from_staff__user__full_name', 'to_staff__user__full_name']
    readonly_fields = ['handed_over_at']


@admin.register(CashCollection)
class CashCollectionAdmin(admin.ModelAdmin):
    list_display = ['staff', 'amount', 'collected_at', 'reconciled']
    list_filter = ['reconciled', 'venue']
    search_fields = ['staff__user__full_name', 'table__table_number']
    readonly_fields = ['collected_at']


@admin.register(PerformanceMetric)
class PerformanceMetricAdmin(admin.ModelAdmin):
    list_display = ['staff', 'period_start', 'period_end', 'total_orders', 'total_revenue']
    list_filter = ['venue']
    search_fields = ['staff__user__full_name']
    readonly_fields = ['updated_at']
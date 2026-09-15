# control/admin.py

from django.contrib import admin
from .models import (
    PlatformAuditLog, VenueHealthMetrics, HQNotification, 
    SupportTicket, VenueAuditLog,
    MenuCategory, MenuItem, Modifier  # <-- ADDED
)


@admin.register(PlatformAuditLog)
class PlatformAuditLogAdmin(admin.ModelAdmin):
    list_display = ['action_type', 'actor', 'target_model', 'target_id', 'created_at']
    list_filter = ['action_type']
    search_fields = ['description', 'target_model']
    readonly_fields = ['id', 'created_at', 'updated_at']


@admin.register(VenueAuditLog)
class VenueAuditLogAdmin(admin.ModelAdmin):
    list_display = ['action_type', 'venue', 'staff', 'table', 'timestamp']
    list_filter = ['action_type', 'venue']
    search_fields = ['action_description']
    readonly_fields = ['id', 'timestamp', 'created_at', 'updated_at']


@admin.register(VenueHealthMetrics)
class VenueHealthMetricsAdmin(admin.ModelAdmin):
    list_display = ['venue', 'active_guests', 'occupied_tables', 'total_tables', 'revenue_today', 'last_updated']
    list_filter = ['venue']
    readonly_fields = ['id', 'created_at', 'updated_at', 'last_updated']


@admin.register(HQNotification)
class HQNotificationAdmin(admin.ModelAdmin):
    list_display = ['title', 'category', 'priority', 'venue', 'is_read', 'created_at']
    list_filter = ['category', 'priority', 'is_read']
    search_fields = ['title', 'message']


@admin.register(SupportTicket)
class SupportTicketAdmin(admin.ModelAdmin):
    list_display = ['subject', 'venue', 'raised_by', 'assigned_to', 'status', 'priority', 'created_at']
    list_filter = ['status', 'priority', 'category']
    search_fields = ['subject', 'description']


# =============================================================================
# Menu Builder Admin (NEW)
# =============================================================================

@admin.register(MenuCategory)
class MenuCategoryAdmin(admin.ModelAdmin):
    list_display = ['id', 'venue', 'name', 'display_order', 'is_active']
    list_filter = ['venue', 'is_active']
    search_fields = ['name']
    ordering = ['venue', 'display_order']


@admin.register(MenuItem)
class MenuItemAdmin(admin.ModelAdmin):
    list_display = ['id', 'venue', 'category', 'name', 'price', 'item_type', 'is_active', 'is_available']
    list_filter = ['venue', 'category', 'item_type', 'is_active', 'is_available']
    search_fields = ['name', 'description']
    ordering = ['venue', 'category', 'name']


@admin.register(Modifier)
class ModifierAdmin(admin.ModelAdmin):
    list_display = ['id', 'venue', 'menu_item', 'name', 'is_required', 'is_active']
    list_filter = ['venue', 'is_required', 'is_active']
    search_fields = ['name']
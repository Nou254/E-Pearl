# tables/admin.py

from django.contrib import admin
from .models import Zone, Table


@admin.register(Zone)
class ZoneAdmin(admin.ModelAdmin):
    list_display = ['name', 'venue', 'is_active']
    list_filter = ['venue', 'is_active']
    search_fields = ['name']


@admin.register(Table)
class TableAdmin(admin.ModelAdmin):
    list_display = ['table_number', 'venue', 'zone', 'status', 'max_capacity', 'current_headcount']
    list_filter = ['venue', 'zone', 'status', 'table_type']
    search_fields = ['table_number', 'qr_code_label']
    readonly_fields = ['qr_code']
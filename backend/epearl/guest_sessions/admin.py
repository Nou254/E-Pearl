# guest_sessions/admin.py

from django.contrib import admin
from .models import GuestSession


@admin.register(GuestSession)
class GuestSessionAdmin(admin.ModelAdmin):
    list_display = [
        'id',
        'user',
        'venue',
        'session_token',
        'status',
        'start_time',
        'end_time',
    ]
    list_filter = ['status', 'venue']
    search_fields = ['user__email', 'user__phone', 'session_token']
    readonly_fields = ['id', 'session_token', 'start_time']
    ordering = ['-start_time']
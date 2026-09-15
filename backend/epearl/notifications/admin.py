# notifications/admin.py

from django.contrib import admin
from .models import Notification, NotificationTemplate


@admin.register(NotificationTemplate)
class NotificationTemplateAdmin(admin.ModelAdmin):
    list_display = ['name', 'channel', 'subject', 'is_active']
    list_filter = ['channel', 'is_active']
    search_fields = ['name', 'subject']


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ['id', 'notification_type', 'channel', 'recipient_email', 'status', 'sent_at']
    list_filter = ['notification_type', 'channel', 'status']
    search_fields = ['recipient_email', 'recipient_phone']
    readonly_fields = ['created_at', 'updated_at']
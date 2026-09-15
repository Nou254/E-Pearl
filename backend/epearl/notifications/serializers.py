# notifications/serializers.py

from rest_framework import serializers
from .models import Notification


class NotificationSerializer(serializers.ModelSerializer):
    recipient_name = serializers.CharField(source='recipient_user.full_name', read_only=True)

    class Meta:
        model = Notification
        fields = [
            'id', 'venue', 'recipient_user', 'recipient_name',
            'recipient_email', 'recipient_phone',
            'notification_type', 'channel', 'subject', 'body',
            'metadata', 'status', 'error_message', 'sent_at',
            'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'status', 'error_message', 'sent_at',
            'created_at', 'updated_at'
        ]
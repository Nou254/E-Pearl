# guest_sessions/serializers.py

from rest_framework import serializers
from .models import GuestSession
import uuid


class GuestSessionSerializer(serializers.ModelSerializer):
    class Meta:
        model = GuestSession
        fields = [
            'id', 'user', 'venue', 'session_token', 'status',
            'start_time', 'end_time', 'device_fingerprint', 'ip_address'
        ]
        read_only_fields = ['id', 'session_token', 'start_time', 'end_time']


class GuestSessionCreateSerializer(serializers.Serializer):
    """Serializer for creating a new guest session."""
    venue_id = serializers.UUIDField(help_text="UUID of the venue")
    device_fingerprint = serializers.CharField(max_length=255, required=False)
    ip_address = serializers.IPAddressField(required=False)

    def validate_venue_id(self, value):
        from venues.models import Venue
        try:
            venue = Venue.objects.get(id=value)
        except Venue.DoesNotExist:
            raise serializers.ValidationError("Venue not found")
        return venue

    def create(self, validated_data):
        venue = validated_data['venue_id']
        user = self.context.get('request').user if self.context.get('request') else None
        if user and not user.is_authenticated:
            user = None

        session_token = str(uuid.uuid4())

        session = GuestSession.objects.create(
            user=user,
            venue=venue,
            session_token=session_token,
            device_fingerprint=validated_data.get('device_fingerprint', ''),
            ip_address=validated_data.get('ip_address', ''),
        )
        return session
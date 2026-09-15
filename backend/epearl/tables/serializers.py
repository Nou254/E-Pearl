# tables/serializers.py

from rest_framework import serializers
from .models import Zone, Table


class ZoneSerializer(serializers.ModelSerializer):
    class Meta:
        model = Zone
        fields = ['id', 'venue', 'name', 'description', 'is_active', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']


class TableSerializer(serializers.ModelSerializer):
    zone_name = serializers.CharField(source='zone.name', read_only=True)
    venue_name = serializers.CharField(source='venue.business_name', read_only=True)

    class Meta:
        model = Table
        fields = [
            'id', 'venue', 'venue_name', 'zone', 'zone_name',
            'table_number', 'max_capacity', 'current_headcount',
            'status', 'qr_code', 'qr_code_label', 'table_type',
            'is_active', 'reservation_status', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'qr_code', 'created_at', 'updated_at']


class TableCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Table
        fields = [
            'table_number', 'max_capacity', 'zone',
            'table_type', 'qr_code_label'
        ]

    def create(self, validated_data):
        # Automatically set the venue from the request user
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            validated_data['venue'] = request.user.venue
        return super().create(validated_data)


class TableUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Table
        fields = [
            'table_number', 'max_capacity', 'zone',
            'status', 'table_type', 'is_active',
            'reservation_status', 'qr_code_label'
        ]
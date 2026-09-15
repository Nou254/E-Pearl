# gate/serializers.py

from rest_framework import serializers


class ExitScanRequestSerializer(serializers.Serializer):
    qr_data = serializers.CharField(help_text="JWT token from Exit QR")
    device_fingerprint = serializers.CharField(required=False)


class ExitScanResponseSerializer(serializers.Serializer):
    allowed = serializers.BooleanField()
    reason = serializers.CharField()
    requires_escort = serializers.BooleanField(default=False)


class TicketScanRequestSerializer(serializers.Serializer):
    ticket_code = serializers.CharField()
    event_id = serializers.UUIDField(required=False)


class TicketScanResponseSerializer(serializers.Serializer):
    allowed = serializers.BooleanField()
    reason = serializers.CharField()
    vip_table = serializers.UUIDField(required=False)


class StaffScanRequestSerializer(serializers.Serializer):
    staff_qr = serializers.CharField()
    device_fingerprint = serializers.CharField(required=False)


class StaffScanOutOverrideRequestSerializer(serializers.Serializer):
    staff_qr = serializers.CharField()
    device_fingerprint = serializers.CharField(required=False)
    override = serializers.BooleanField(default=False)
    manager_pin = serializers.CharField(required=False)


class ManualOverrideRequestSerializer(serializers.Serializer):
    table_number = serializers.CharField()
    guest_alias = serializers.CharField()
    manager_pin = serializers.CharField()
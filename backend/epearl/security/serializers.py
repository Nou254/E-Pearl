from rest_framework import serializers
from .models import SecurityEvent, SecurityRule, SecurityAnalytics, IPReputationCache


class SecurityEventSerializer(serializers.ModelSerializer):
    user_email = serializers.CharField(source='user.email', read_only=True)
    venue_name = serializers.CharField(source='venue.business_name', read_only=True)
    rule_name = serializers.CharField(source='rule.name', read_only=True)

    class Meta:
        model = SecurityEvent
        fields = '__all__'
        read_only_fields = ['id', 'timestamp', 'created_at', 'updated_at']


class SecurityRuleSerializer(serializers.ModelSerializer):
    class Meta:
        model = SecurityRule
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at', 'last_triggered_at', 'trigger_count']


class SecurityAnalyticsSerializer(serializers.ModelSerializer):
    class Meta:
        model = SecurityAnalytics
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at']


class IPReputationCacheSerializer(serializers.ModelSerializer):
    class Meta:
        model = IPReputationCache
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at']
from django.contrib import admin
from .models import SecurityRule, SecurityEvent, SecurityAnalytics, IPReputationCache

@admin.register(SecurityRule)
class SecurityRuleAdmin(admin.ModelAdmin):
    list_display = ['name', 'rule_type', 'severity', 'enabled', 'priority', 'trigger_count']
    list_filter = ['rule_type', 'severity', 'enabled']
    search_fields = ['name', 'description']

@admin.register(SecurityEvent)
class SecurityEventAdmin(admin.ModelAdmin):
    list_display = ['timestamp', 'ip_address', 'method', 'endpoint', 'rule_type', 'severity']
    list_filter = ['severity', 'rule_type', 'timestamp']
    search_fields = ['ip_address', 'endpoint']

@admin.register(SecurityAnalytics)
class SecurityAnalyticsAdmin(admin.ModelAdmin):
    list_display = ['date', 'hour', 'rule_type', 'severity', 'count']
    list_filter = ['date', 'rule_type']

@admin.register(IPReputationCache)
class IPReputationCacheAdmin(admin.ModelAdmin):
    list_display = ['ip_address', 'abuse_score', 'is_malicious', 'last_checked']
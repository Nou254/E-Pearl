from django.db import models
from core.models import BaseModel
from django.utils import timezone


class SecurityRule(BaseModel):
    """
    Security rule definitions – used by the middleware.
    """
    RULE_TYPES = [
        ('ip_blocklist', 'IP Blocklist'),
        ('ip_allowlist', 'IP Allowlist'),
        ('rate_limit', 'Rate Limit'),
        ('path_restriction', 'Path Restriction'),
        ('method_restriction', 'Method Restriction'),
        ('sql_injection', 'SQL Injection'),
        ('xss', 'XSS'),
        ('path_traversal', 'Path Traversal'),
        ('geo_block', 'Geo Block'),
        ('user_agent_block', 'User-Agent Block'),
        ('behavioural', 'Behavioural Anomaly'),
        ('request_size', 'Request Size Limit'),
        ('role_endpoint', 'Role-Endpoint Restriction'),
    ]

    SEVERITY_CHOICES = [
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('critical', 'Critical'),
    ]

    name = models.CharField(max_length=100)
    rule_type = models.CharField(max_length=50, choices=RULE_TYPES)
    severity = models.CharField(max_length=20, choices=SEVERITY_CHOICES, default='medium')
    priority = models.PositiveSmallIntegerField(default=100)  # Lower number = higher priority
    enabled = models.BooleanField(default=True)

    # Conditions – JSON field for rule-specific configuration
    conditions = models.JSONField(default=dict, help_text="Rule-specific parameters")

    # Description
    description = models.TextField(blank=True, null=True)

    # Stats
    last_triggered_at = models.DateTimeField(null=True, blank=True)
    trigger_count = models.PositiveIntegerField(default=0)

    class Meta:
        db_table = 'security_rules'
        ordering = ['priority', 'id']

    def __str__(self):
        return f"{self.name} ({self.get_rule_type_display()})"


class SecurityEvent(BaseModel):
    """
    Log every blocked request with full context.
    """
    user = models.ForeignKey('users.User', on_delete=models.SET_NULL, null=True, blank=True, related_name='security_events')
    venue = models.ForeignKey('venues.Venue', on_delete=models.SET_NULL, null=True, blank=True, related_name='security_events')

    ip_address = models.GenericIPAddressField()
    endpoint = models.CharField(max_length=500)
    method = models.CharField(max_length=10)
    request_headers = models.JSONField(default=dict, blank=True)  # sanitized
    request_body = models.TextField(blank=True, null=True)  # truncated

    rule = models.ForeignKey(SecurityRule, on_delete=models.SET_NULL, null=True, blank=True)
    rule_type = models.CharField(max_length=50)
    severity = models.CharField(max_length=20)

    user_agent = models.TextField(blank=True, null=True)
    geo_country = models.CharField(max_length=100, blank=True, null=True)

    resolved = models.BooleanField(default=False)
    resolved_by = models.ForeignKey('users.User', on_delete=models.SET_NULL, null=True, blank=True, related_name='resolved_security_events')
    resolved_at = models.DateTimeField(null=True, blank=True)
    resolution_notes = models.TextField(blank=True, null=True)

    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'security_events'
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['timestamp']),
            models.Index(fields=['ip_address']),
            models.Index(fields=['rule_type']),
            models.Index(fields=['severity']),
            models.Index(fields=['venue']),
            models.Index(fields=['user']),
        ]

    def __str__(self):
        return f"{self.method} {self.endpoint} - {self.rule_type} - {self.ip_address}"


class SecurityAnalytics(BaseModel):
    """
    Pre‑aggregated analytics for fast dashboard rendering.
    """
    date = models.DateField()
    hour = models.PositiveSmallIntegerField(null=True, blank=True)  # If hourly aggregation

    rule_type = models.CharField(max_length=50, blank=True, null=True)  # If by rule type
    severity = models.CharField(max_length=20, blank=True, null=True)

    count = models.PositiveIntegerField(default=0)
    unique_ips = models.PositiveIntegerField(default=0)
    unique_users = models.PositiveIntegerField(default=0)

    class Meta:
        db_table = 'security_analytics'
        unique_together = ['date', 'hour', 'rule_type', 'severity']

    def __str__(self):
        return f"{self.date} {self.hour}h - {self.rule_type or 'ALL'} - {self.count}"


class IPReputationCache(BaseModel):
    """
    Cache external IP reputation results.
    """
    ip_address = models.GenericIPAddressField(unique=True)
    abuse_score = models.FloatField(null=True, blank=True)
    is_malicious = models.BooleanField(default=False)
    source = models.CharField(max_length=50, blank=True, null=True)
    last_checked = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'ip_reputation_cache'

    def __str__(self):
        return self.ip_address
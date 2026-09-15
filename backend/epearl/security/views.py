from rest_framework import viewsets, permissions, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Count, Sum
from .models import SecurityEvent, SecurityRule, SecurityAnalytics, IPReputationCache
from .serializers import (
    SecurityEventSerializer, SecurityRuleSerializer,
    SecurityAnalyticsSerializer, IPReputationCacheSerializer
)
from .services.rule_engine import RuleEngine
from users.permissions import HQAdminPermission


class SecurityEventViewSet(viewsets.ReadOnlyModelViewSet):
    """
    View and filter security events.
    """
    queryset = SecurityEvent.objects.all().select_related('user', 'venue', 'rule')
    serializer_class = SecurityEventSerializer
    permission_classes = [permissions.IsAuthenticated, HQAdminPermission]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['rule_type', 'severity', 'ip_address', 'user', 'venue']
    search_fields = ['endpoint', 'user_agent']
    ordering_fields = ['timestamp', 'severity']
    ordering = ['-timestamp']

    @action(detail=True, methods=['post'])
    def resolve(self, request, pk=None):
        event = self.get_object()
        event.resolved = True
        event.resolved_by = request.user
        event.resolved_at = timezone.now()
        event.resolution_notes = request.data.get('notes', '')
        event.save()
        return Response({'status': 'resolved'})

    @action(detail=False, methods=['get'])
    def dashboard_stats(self, request):
        """
        Provide aggregated stats for the dashboard.
        """
        from django.db.models import Count, Sum
        total_events = SecurityEvent.objects.count()
        today = timezone.now().date()
        today_events = SecurityEvent.objects.filter(timestamp__date=today).count()
        critical_today = SecurityEvent.objects.filter(timestamp__date=today, severity='critical').count()

        by_rule_type = SecurityEvent.objects.values('rule_type').annotate(count=Count('id')).order_by('-count')[:10]
        by_ip = SecurityEvent.objects.values('ip_address').annotate(count=Count('id')).order_by('-count')[:10]
        by_endpoint = SecurityEvent.objects.values('endpoint').annotate(count=Count('id')).order_by('-count')[:10]
        by_severity = SecurityEvent.objects.values('severity').annotate(count=Count('id'))

        return Response({
            'total_events': total_events,
            'today_events': today_events,
            'critical_today': critical_today,
            'by_rule_type': by_rule_type,
            'by_ip': by_ip,
            'by_endpoint': by_endpoint,
            'by_severity': by_severity,
        })


class SecurityRuleViewSet(viewsets.ModelViewSet):
    """
    Manage security rules.
    """
    queryset = SecurityRule.objects.all()
    serializer_class = SecurityRuleSerializer
    permission_classes = [permissions.IsAuthenticated, HQAdminPermission]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['rule_type', 'enabled']
    search_fields = ['name', 'description']
    ordering_fields = ['priority', 'trigger_count']

    @action(detail=False, methods=['post'])
    def clear_cache(self, request):
        """
        Clear the rule cache to reload rules immediately.
        """
        RuleEngine.get_rules.cache_clear()  # if using lru_cache, else custom
        return Response({'status': 'cache cleared'})


class SecurityAnalyticsViewSet(viewsets.ReadOnlyModelViewSet):
    """
    View aggregated analytics.
    """
    queryset = SecurityAnalytics.objects.all()
    serializer_class = SecurityAnalyticsSerializer
    permission_classes = [permissions.IsAuthenticated, HQAdminPermission]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['date', 'rule_type', 'severity']
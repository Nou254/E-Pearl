# hq/urls.py

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    PlatformSettingViewSet, SMSCreditViewSet, APIKeyViewSet,
    HealthViewSet, RequestLogViewSet, FeatureFlagViewSet,
    SystemStatusViewSet, FinancialReconciliationViewSet, BillingViewSet,
    AnalyticsViewSet,
    RefundReviewViewSet,           # NEW
    TrialManagementViewSet,        # NEW
)

router = DefaultRouter()

# Existing views
router.register(r'platform-settings', PlatformSettingViewSet, basename='platform-settings')
router.register(r'sms-credits', SMSCreditViewSet, basename='sms-credits')
router.register(r'api-keys', APIKeyViewSet, basename='api-keys')

# New HQ views
router.register(r'health', HealthViewSet, basename='health')
router.register(r'request-logs', RequestLogViewSet, basename='request-logs')
router.register(r'feature-flags', FeatureFlagViewSet, basename='feature-flags')
router.register(r'system-status', SystemStatusViewSet, basename='system-status')
router.register(r'finance/reconciliation', FinancialReconciliationViewSet, basename='finance-reconciliation')
router.register(r'billing', BillingViewSet, basename='billing')
router.register(r'analytics', AnalyticsViewSet, basename='analytics')

# NEW: Refund and Trial management
router.register(r'refunds', RefundReviewViewSet, basename='hq-refunds')
router.register(r'trials', TrialManagementViewSet, basename='hq-trials')

urlpatterns = [
    path('', include(router.urls)),
]
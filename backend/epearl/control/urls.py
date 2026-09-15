# control/urls.py

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    ControlViewSet,
    PlatformAuditLogViewSet,
    VenueHealthMetricsViewSet,
    HQNotificationViewSet,
    SupportTicketViewSet,
    PlatformDashboardViewSet,
    # Menu Builder ViewSets
    MenuCategoryViewSet,
    MenuItemViewSet,
    ModifierViewSet,
    # Wastage & Menu Versioning
    WastageLogViewSet,
    MenuVersionViewSet,
)

router = DefaultRouter()

# Manager dashboard (includes trial_status and refund_policy endpoints)
router.register(r'manager', ControlViewSet, basename='manager')

# HQ admin
router.register(r'audit-logs', PlatformAuditLogViewSet, basename='audit-logs')
router.register(r'venue-metrics', VenueHealthMetricsViewSet, basename='venue-metrics')
router.register(r'hq-notifications', HQNotificationViewSet, basename='hq-notifications')
router.register(r'support-tickets', SupportTicketViewSet, basename='support-tickets')
router.register(r'dashboard', PlatformDashboardViewSet, basename='dashboard')

# Menu Builder
router.register(r'menu-categories', MenuCategoryViewSet, basename='menu-categories')
router.register(r'menu-items', MenuItemViewSet, basename='menu-items')
router.register(r'modifiers', ModifierViewSet, basename='modifiers')

# Wastage & Menu Versioning
router.register(r'wastage-logs', WastageLogViewSet, basename='wastage-logs')
router.register(r'menu-versions', MenuVersionViewSet, basename='menu-versions')

urlpatterns = [
    path('', include(router.urls)),
]
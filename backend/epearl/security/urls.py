from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    SecurityEventViewSet, SecurityRuleViewSet,
    SecurityAnalyticsViewSet
)

router = DefaultRouter()
router.register(r'events', SecurityEventViewSet, basename='security-events')
router.register(r'rules', SecurityRuleViewSet, basename='security-rules')
router.register(r'analytics', SecurityAnalyticsViewSet, basename='security-analytics')

urlpatterns = [
    path('', include(router.urls)),
]
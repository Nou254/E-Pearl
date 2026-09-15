# venues/urls.py

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import VenueViewSet, VenueRefundPolicyViewSet

router = DefaultRouter()
router.register(r'venues', VenueViewSet, basename='venues')
router.register(r'refund-policies', VenueRefundPolicyViewSet, basename='refund-policies')

urlpatterns = [
    path('', include(router.urls)),
]
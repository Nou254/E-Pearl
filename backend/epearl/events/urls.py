# events/urls.py

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import EventViewSet, TicketTierViewSet, TicketViewSet

router = DefaultRouter()
router.register('events', EventViewSet, basename='events')
router.register('ticket-tiers', TicketTierViewSet, basename='ticket-tiers')
router.register('tickets', TicketViewSet, basename='tickets')

urlpatterns = [
    path('', include(router.urls)),
]
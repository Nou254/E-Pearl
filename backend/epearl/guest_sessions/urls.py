# guest_sessions/urls.py

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import GuestSessionViewSet

router = DefaultRouter()
router.register('guest-sessions', GuestSessionViewSet, basename='guest-sessions')

urlpatterns = [
    path('', include(router.urls)),
]
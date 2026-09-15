# gate/urls.py

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import GateViewSet

router = DefaultRouter()
router.register('gate', GateViewSet, basename='gate')

urlpatterns = [
    path('', include(router.urls)),
]
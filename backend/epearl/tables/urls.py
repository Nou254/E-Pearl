# tables/urls.py

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ZoneViewSet, TableViewSet

router = DefaultRouter()
router.register('zones', ZoneViewSet, basename='zones')
router.register('tables', TableViewSet, basename='tables')

urlpatterns = [
    path('', include(router.urls)),
]
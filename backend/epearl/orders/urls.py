# orders/urls.py

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    MenuCategoryViewSet,
    MenuItemViewSet,
    ModifierViewSet,
    OrderViewSet,
    OrderItemViewSet,
)

router = DefaultRouter()
router.register('menu-categories', MenuCategoryViewSet, basename='menu-categories')
router.register('menu-items', MenuItemViewSet, basename='menu-items')
router.register('modifiers', ModifierViewSet, basename='modifiers')
router.register('orders', OrderViewSet, basename='orders')
router.register('order-items', OrderItemViewSet, basename='order-items')

urlpatterns = [
    path('', include(router.urls)),
]
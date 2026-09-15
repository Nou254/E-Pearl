# payments/urls.py

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    TransactionViewSet,
    PreAuthHoldViewSet,
    PaymentGatewayConfigViewSet,
    RefundRequestViewSet,
    webhook,
)

router = DefaultRouter()
router.register('transactions', TransactionViewSet, basename='transactions')
router.register('pre-auth-holds', PreAuthHoldViewSet, basename='pre-auth-holds')
router.register('payment-configs', PaymentGatewayConfigViewSet, basename='payment-configs')
router.register('refunds', RefundRequestViewSet, basename='refunds')

urlpatterns = [
    path('', include(router.urls)),
    # Webhook endpoint – receives callbacks from M-Pesa, Flutterwave, etc.
    path('webhook/', webhook, name='webhook'),
]
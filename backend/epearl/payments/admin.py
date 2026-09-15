# payments/admin.py

from django.contrib import admin
from .models import (
    Transaction, PreAuthHold, PaymentGatewayConfig, WebhookLog,
    RefundRequest, RefundTransaction
)


@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = ['id', 'venue', 'transaction_type', 'amount', 'transaction_status', 'refund_status', 'transaction_time']
    list_filter = ['transaction_type', 'transaction_status', 'payment_method', 'refund_status']
    search_fields = ['gateway_reference_id']
    readonly_fields = ['id', 'created_at', 'updated_at']


@admin.register(PreAuthHold)
class PreAuthHoldAdmin(admin.ModelAdmin):
    list_display = ['id', 'venue', 'declared_amount', 'hold_status', 'hold_time']
    list_filter = ['hold_status', 'payment_method']
    search_fields = ['gateway_reference_id']


@admin.register(PaymentGatewayConfig)
class PaymentGatewayConfigAdmin(admin.ModelAdmin):
    list_display = ['venue', 'gateway_provider', 'environment', 'status']
    list_filter = ['gateway_provider', 'environment', 'status']


@admin.register(WebhookLog)
class WebhookLogAdmin(admin.ModelAdmin):
    list_display = ['id', 'provider', 'event_type', 'is_verified', 'is_processed', 'received_at']
    list_filter = ['provider', 'event_type', 'is_verified', 'is_processed']
    readonly_fields = ['id', 'received_at']


# ========== NEW ADMIN REGISTRATIONS ==========

@admin.register(RefundRequest)
class RefundRequestAdmin(admin.ModelAdmin):
    list_display = ['id', 'booking', 'customer', 'venue', 'classification', 'requested_amount', 'status', 'created_at']
    list_filter = ['status', 'classification', 'reason']
    search_fields = ['booking__id', 'customer__email', 'venue__business_name']
    readonly_fields = ['id', 'created_at', 'updated_at']
    fieldsets = (
        (None, {
            'fields': ('booking', 'transaction', 'customer', 'venue', 'reason', 'classification',
                       'requested_amount', 'approved_amount', 'status')
        }),
        ('Review', {
            'fields': ('reviewed_by', 'reviewed_at', 'resolution_notes')
        }),
        ('Metadata', {
            'fields': ('metadata',)
        }),
    )


@admin.register(RefundTransaction)
class RefundTransactionAdmin(admin.ModelAdmin):
    list_display = ['id', 'original_transaction', 'refund_request', 'amount', 'status', 'processed_at']
    list_filter = ['status']
    search_fields = ['gateway_reference_id']
    readonly_fields = ['id', 'processed_at', 'created_at', 'updated_at']
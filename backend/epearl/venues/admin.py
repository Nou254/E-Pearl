# venues/admin.py

from django.contrib import admin
from .models import Venue, VenueRefundPolicy


@admin.register(Venue)
class VenueAdmin(admin.ModelAdmin):
    list_display = [
        'business_name', 'sub_domain', 'subscription_tier',
        'subscription_status', 'next_billing_date', 'document_verification_status'
    ]
    search_fields = ['business_name', 'registration_number', 'contact_phone', 'sub_domain']
    list_filter = ['subscription_tier', 'subscription_status', 'document_verification_status']


@admin.register(VenueRefundPolicy)
class VenueRefundPolicyAdmin(admin.ModelAdmin):
    list_display = [
        'venue', 'cancellation_policy', 'full_refund_window_hours',
        'partial_refund_window_hours', 'partial_refund_percentage'
    ]
    list_filter = ['cancellation_policy', 'venue_cancellation_refund', 'rescheduling_allowed']
    search_fields = ['venue__business_name']
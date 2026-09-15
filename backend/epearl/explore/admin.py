# explore/admin.py

from django.contrib import admin
from .models import Booking, RoomType, RoomAvailability, VenueHiring, Rating, RatingSummary


@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    list_display = [
        'id', 'guest_session', 'user', 'venue', 'booking_type',
        'booking_date', 'status', 'refund_status'
    ]
    list_filter = ['booking_type', 'status', 'refund_status', 'venue']
    search_fields = ['guest_session__session_token', 'user__email', 'venue__business_name']
    readonly_fields = ['booking_qr']


@admin.register(RoomType)
class RoomTypeAdmin(admin.ModelAdmin):
    list_display = ['room_type', 'venue', 'base_price', 'max_occupancy', 'status']
    list_filter = ['venue', 'status']
    search_fields = ['room_type']


@admin.register(RoomAvailability)
class RoomAvailabilityAdmin(admin.ModelAdmin):
    list_display = ['room_type', 'date', 'total_rooms', 'available_rooms', 'price']
    list_filter = ['room_type', 'date']


@admin.register(VenueHiring)
class VenueHiringAdmin(admin.ModelAdmin):
    list_display = ['renter_name', 'venue', 'hire_date', 'status', 'hire_price']
    list_filter = ['venue', 'status', 'hire_duration']
    search_fields = ['renter_name', 'renter_email', 'renter_phone']
    readonly_fields = ['hire_qr']


# =============================================================================
# NEW: Ratings & Reviews Admin
# =============================================================================

@admin.register(Rating)
class RatingAdmin(admin.ModelAdmin):
    list_display = ['user', 'venue', 'rating', 'is_verified', 'is_visible', 'created_at']
    list_filter = ['rating', 'is_verified', 'is_visible', 'venue']
    search_fields = ['user__full_name', 'user__email', 'review']
    readonly_fields = ['created_at', 'updated_at']


@admin.register(RatingSummary)
class RatingSummaryAdmin(admin.ModelAdmin):
    list_display = ['venue', 'average_rating', 'total_reviews', 'last_updated']
    readonly_fields = ['last_updated']
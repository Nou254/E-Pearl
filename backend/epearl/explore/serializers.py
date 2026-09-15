# explore/serializers.py

from rest_framework import serializers
from .models import Booking, RoomType, RoomAvailability, VenueHiring, Rating, RatingSummary
from venues.serializers import VenueSerializer


class RoomTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = RoomType
        fields = [
            'id', 'venue', 'room_type', 'description', 'base_price',
            'max_occupancy', 'amenities', 'image_urls', 'status',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class RoomAvailabilitySerializer(serializers.ModelSerializer):
    class Meta:
        model = RoomAvailability
        fields = [
            'id', 'room_type', 'date', 'available_rooms',
            'total_rooms', 'price', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class VenueHiringSerializer(serializers.ModelSerializer):
    class Meta:
        model = VenueHiring
        fields = [
            'id', 'venue', 'renter_name', 'renter_phone', 'renter_email',
            'hire_date', 'hire_start_time', 'hire_end_time', 'hire_duration',
            'hire_price', 'deposit_amount', 'deposit_status', 'hire_qr',
            'hire_rules', 'status', 'checked_in', 'checked_in_time',
            'checked_out', 'checked_out_time', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'hire_qr', 'created_at', 'updated_at']


class BookingSerializer(serializers.ModelSerializer):
    venue_name = serializers.CharField(source='venue.business_name', read_only=True)
    table_number = serializers.CharField(source='table.table_number', read_only=True, allow_null=True)
    room_type_name = serializers.CharField(source='room_type.room_type', read_only=True, allow_null=True)

    class Meta:
        model = Booking
        fields = [
            'id', 'venue', 'venue_name', 'guest_session', 'user',
            'booking_type', 'booking_date', 'start_time', 'end_time',
            'party_size', 'notes', 'table', 'table_number',
            'room_type', 'room_type_name', 'venue_hiring',
            'total_amount', 'paid_amount', 'payment_status', 'transaction_id',
            'booking_qr', 'checked_in', 'checked_in_time',
            'checked_out', 'checked_out_time', 'status',
            'refund_status',  # NEW
            'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'booking_qr', 'created_at', 'updated_at',
            'transaction_id', 'payment_status', 'paid_amount'
        ]


class BookingCreateSerializer(serializers.ModelSerializer):
    total_amount = serializers.DecimalField(
        max_digits=10, decimal_places=2,
        required=False, default=0,
        help_text="Total amount for the booking (used for deposit calculation)."
    )

    class Meta:
        model = Booking
        fields = [
            'booking_type', 'booking_date', 'start_time', 'end_time',
            'party_size', 'notes', 'table', 'room_type', 'venue_hiring',
            'total_amount'
        ]

    def validate(self, data):
        booking_type = data.get('booking_type')
        if booking_type == 'table' and not data.get('table'):
            raise serializers.ValidationError("Table is required for table bookings.")
        if booking_type == 'room' and not data.get('room_type'):
            raise serializers.ValidationError("Room type is required for room bookings.")
        if booking_type == 'hire' and not data.get('venue_hiring'):
            raise serializers.ValidationError("Venue hire details are required for hire bookings.")
        return data


class BookingRefundRequestSerializer(serializers.Serializer):
    """
    Serializer for requesting a refund on a booking.
    """
    reason = serializers.ChoiceField(choices=[
        ('venue_cancelled', 'Venue Cancelled'),
        ('venue_failed_service', 'Venue Failed to Provide Service'),
        ('customer_cancellation', 'Customer Changed Mind'),
        ('technical_issue', 'Technical Issue / Double Charge'),
        ('other', 'Other'),
    ])
    requested_amount = serializers.DecimalField(max_digits=10, decimal_places=2)
    notes = serializers.CharField(required=False, allow_blank=True)


class PublicVenueListSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    business_name = serializers.CharField()
    description = serializers.CharField()
    cover_image_url = serializers.CharField()
    logo_url = serializers.CharField()
    gps_coordinates = serializers.CharField()
    operating_hours = serializers.JSONField()
    distance = serializers.FloatField(required=False)
    subscription_tier = serializers.CharField()


class PublicVenueDetailSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    business_name = serializers.CharField()
    description = serializers.CharField()
    cover_image_url = serializers.CharField()
    logo_url = serializers.CharField()
    gps_coordinates = serializers.CharField()
    operating_hours = serializers.JSONField()
    physical_address = serializers.CharField()
    contact_phone = serializers.CharField()
    contact_email = serializers.EmailField()
    public_listing = serializers.BooleanField()
    upcoming_events = serializers.ListField(required=False)
    available_tables = serializers.IntegerField(required=False)
    hiring_available = serializers.BooleanField(required=False)


# =============================================================================
# NEW: Ratings & Reviews Serializers
# =============================================================================

class RatingSerializer(serializers.ModelSerializer):
    user_name = serializers.CharField(source='user.full_name', read_only=True)
    venue_name = serializers.CharField(source='venue.business_name', read_only=True)

    class Meta:
        model = Rating
        fields = [
            'id', 'venue', 'venue_name', 'user', 'user_name',
            'booking', 'rating', 'review', 'is_verified',
            'is_visible', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'is_verified', 'is_visible']


class RatingCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Rating
        fields = ['venue', 'booking', 'rating', 'review']


class RatingSummarySerializer(serializers.ModelSerializer):
    class Meta:
        model = RatingSummary
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at', 'last_updated']


class RatingDistributionSerializer(serializers.Serializer):
    total_reviews = serializers.IntegerField()
    average_rating = serializers.DecimalField(max_digits=3, decimal_places=2)
    distribution = serializers.DictField()
    percentages = serializers.DictField()
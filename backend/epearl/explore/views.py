# explore/views.py

from decimal import Decimal
from rest_framework import viewsets, permissions, status, filters
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db import transaction as db_transaction
from django.core.exceptions import ValidationError
from django.db.models import Q, Avg, Count
from django.utils import timezone
from .models import Booking, RoomType, RoomAvailability, VenueHiring, Rating, RatingSummary
from .serializers import (
    BookingSerializer, BookingCreateSerializer,
    RoomTypeSerializer, RoomAvailabilitySerializer,
    VenueHiringSerializer,
    PublicVenueListSerializer, PublicVenueDetailSerializer,
    RatingSerializer, RatingCreateSerializer,
    RatingSummarySerializer, RatingDistributionSerializer,
    BookingRefundRequestSerializer,
)
from venues.models import Venue
from venues.services.tier_service import TierService
from payments.services.payment_service import PaymentService
from payments.services.refund_service import RefundService
from payments.services.refund_classification import RefundClassification
from payments.models import RefundRequest
from core.websocket_utils import notify_control
from notifications.services.notification_service import NotificationService
import logging

logger = logging.getLogger(__name__)


class BookingViewSet(viewsets.ModelViewSet):
    serializer_class = BookingSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['booking_type', 'status', 'booking_date', 'refund_status']
    search_fields = ['notes']
    ordering_fields = ['booking_date', 'start_time', 'created_at']

    def get_queryset(self):
        user = self.request.user
        if user.user_type in ['admin', 'support']:
            return Booking.objects.all()
        if user.venue:
            return Booking.objects.filter(venue=user.venue)
        return Booking.objects.filter(user=user)

    def get_serializer_class(self):
        if self.action == 'create':
            return BookingCreateSerializer
        return BookingSerializer

    def perform_create(self, serializer):
        user = self.request.user
        venue = self.request.user.venue

        if not venue:
            venue_id = self.request.data.get('venue')
            if venue_id:
                venue = Venue.objects.get(id=venue_id)
            else:
                raise PermissionError("Venue is required for booking.")

        if not venue.is_active():
            raise PermissionError("Venue is not currently active.")

        booking_type = self.request.data.get('booking_type')
        party_size = int(self.request.data.get('party_size', 1))
        booking_date = self.request.data.get('booking_date')
        start_time = self.request.data.get('start_time')
        table = None
        room_type = None
        venue_hiring = None

        if booking_type == 'table':
            table_id = self.request.data.get('table')
            if table_id:
                from tables.models import Table
                table = Table.objects.get(id=table_id, venue=venue)
                if not table.is_available():
                    raise PermissionError("Table is not available.")
                if table.max_capacity < party_size:
                    raise PermissionError("Table capacity exceeded.")
                existing = Booking.objects.filter(
                    table=table,
                    booking_date=booking_date,
                    start_time__lt=start_time,
                    end_time__gt=start_time
                ).exists()
                if existing:
                    raise PermissionError("Table already booked for that time.")
            else:
                raise PermissionError("Table is required for table bookings.")

        elif booking_type == 'room':
            room_type_id = self.request.data.get('room_type')
            if room_type_id:
                room_type = RoomType.objects.get(id=room_type_id, venue=venue)
                if booking_date:
                    availability = RoomAvailability.objects.filter(
                        room_type=room_type,
                        date=booking_date
                    ).first()
                    if not availability or availability.available_rooms < 1:
                        raise PermissionError("No rooms available for the selected date.")
                else:
                    raise PermissionError("Booking date is required for room bookings.")
            else:
                raise PermissionError("Room type is required for room bookings.")

        elif booking_type == 'hire':
            venue_hiring_id = self.request.data.get('venue_hiring')
            if not venue_hiring_id:
                raise PermissionError("Venue hire details are required.")

        total_amount = Decimal(str(self.request.data.get('total_amount', 0)))
        if total_amount == 0:
            total_amount = Decimal(party_size * 500)

        deposit = PaymentService.calculate_deposit(venue, total_amount)

        booking = serializer.save(
            user=user if user.is_authenticated else None,
            venue=venue,
            status='pending',
            total_amount=total_amount,
            paid_amount=Decimal(0),
            refund_status='none'
        )

        transaction = PaymentService.create_transaction(
            venue=venue,
            amount=deposit,
            transaction_type='deposit',
            payment_method='mpesa',
            booking=booking,
            guest_session=user.guest_sessions.first() if user.is_authenticated else None,
            user=user if user.is_authenticated else None,
            metadata={
                'booking_id': str(booking.id),
                'party_size': party_size,
                'booking_type': booking_type
            }
        )

        if booking.user:
            NotificationService.send_booking_pending_payment(booking, booking.user)

        try:
            phone = request.user.phone if request.user.is_authenticated else '254700000000'
            PaymentService.process_mpesa_payment(
                venue=venue,
                phone=phone,
                amount=deposit,
                reference=f"BOOK-{str(booking.id)[:6]}",
                transaction_id=str(transaction.id)
            )
            booking.transaction_id = str(transaction.id)
            booking.payment_status = 'pending'
            booking.save(update_fields=['transaction_id', 'payment_status'])
            logger.info(f"Deposit payment initiated for booking {booking.id}")
        except Exception as e:
            booking.status = 'cancelled'
            booking.save(update_fields=['status'])
            PaymentService.mark_transaction_failed(transaction, str(e))
            raise ValidationError(f"Payment initiation failed: {e}")

    @action(detail=True, methods=['post'])
    def confirm_booking(self, request, pk=None):
        booking = self.get_object()
        if booking.status == 'confirmed':
            return Response({'message': 'Booking already confirmed.'}, status=400)
        booking.status = 'confirmed'
        booking.payment_status = 'paid'
        booking.save()
        if booking.table:
            notify_control(str(booking.venue.id), 'table.reserved', {
                'table_id': str(booking.table.id),
                'table_number': booking.table.table_number,
                'booking_id': str(booking.id),
                'guest_name': booking.user.full_name if booking.user else 'Guest',
                'party_size': booking.party_size,
            })
        if booking.user:
            NotificationService.send_booking_confirmation(booking, booking.user)
        return Response({'status': 'confirmed', 'message': 'Booking confirmed and notifications sent.'})

    @action(detail=True, methods=['post'])
    def check_in(self, request, pk=None):
        booking = self.get_object()
        if booking.status != 'confirmed':
            return Response(
                {'error': 'Booking must be confirmed before check-in.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        booking.checked_in = True
        booking.checked_in_time = timezone.now()
        booking.status = 'checked_in'
        booking.save()
        if booking.user:
            NotificationService.send_check_in_confirmation(booking, booking.user)
        return Response({'status': 'checked_in', 'message': 'Check-in successful.'})

    @action(detail=True, methods=['post'])
    def check_out(self, request, pk=None):
        booking = self.get_object()
        if not booking.checked_in:
            return Response(
                {'error': 'Booking must be checked in before check-out.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        booking.checked_out = True
        booking.checked_out_time = timezone.now()
        booking.status = 'completed'
        booking.save()
        if booking.user:
            NotificationService.send_check_out_confirmation(booking, booking.user)
        return Response({'status': 'checked_out', 'message': 'Check-out successful.'})

    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        booking = self.get_object()
        if booking.status in ['checked_in', 'completed']:
            return Response(
                {'error': 'Cannot cancel a booking that has already been checked in or completed.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        booking.status = 'cancelled'
        booking.save()
        if booking.user:
            NotificationService.send_booking_cancelled(booking, booking.user)
        return Response({'status': 'cancelled', 'message': 'Booking cancelled successfully.'})

    @action(detail=True, methods=['post'], permission_classes=[permissions.IsAuthenticated])
    def request_refund(self, request, pk=None):
        """
        Customer initiates a refund request for this booking.
        """
        booking = self.get_object()

        if request.user != booking.user and request.user.user_type not in ['admin', 'support']:
            return Response(
                {'error': 'You do not have permission to request a refund for this booking.'},
                status=status.HTTP_403_FORBIDDEN
            )

        if booking.payment_status != 'paid':
            return Response(
                {'error': 'This booking has not been paid for.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        if booking.refund_status in ['pending', 'approved', 'processed']:
            return Response(
                {'error': f'A refund request is already {booking.refund_status}.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        if booking.status == 'cancelled' and booking.refund_status == 'none':
            pass
        if booking.status == 'completed' and booking.refund_status == 'none':
            pass

        serializer = BookingRefundRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        reason = serializer.validated_data['reason']
        requested_amount = serializer.validated_data['requested_amount']
        notes = serializer.validated_data.get('notes', '')

        transaction = booking.transactions.filter(
            transaction_type='payment',
            transaction_status='success'
        ).first()
        if not transaction:
            transaction = booking.transactions.filter(
                transaction_type='deposit',
                transaction_status='success'
            ).first()
        if not transaction:
            return Response(
                {'error': 'No successful payment transaction found for this booking.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        if requested_amount > transaction.amount:
            return Response(
                {'error': 'Requested amount exceeds the paid amount.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        classification = RefundClassification.classify(booking, reason)

        refund_request = RefundRequest.objects.create(
            booking=booking,
            transaction=transaction,
            customer=request.user,
            venue=booking.venue,
            reason=reason,
            classification=classification,
            requested_amount=requested_amount,
            status='pending',
            metadata={'notes': notes}
        )

        booking.refund_status = 'pending'
        booking.save(update_fields=['refund_status'])

        NotificationService.send_refund_requested(refund_request, booking.venue.owner)

        return Response({
            'message': 'Refund request submitted successfully.',
            'refund_request_id': str(refund_request.id),
            'status': 'pending'
        }, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=['get'], permission_classes=[permissions.IsAuthenticated])
    def history(self, request):
        bookings = Booking.objects.filter(user=request.user).order_by('-booking_date', '-start_time')
        serializer = self.get_serializer(bookings, many=True)
        return Response(serializer.data)


class RoomTypeViewSet(viewsets.ModelViewSet):
    serializer_class = RoomTypeSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ['status']
    search_fields = ['room_type', 'description']

    def get_queryset(self):
        user = self.request.user
        if user.user_type in ['admin', 'support']:
            return RoomType.objects.all()
        if user.venue:
            return RoomType.objects.filter(venue=user.venue, status='active')
        return RoomType.objects.none()

    def perform_create(self, serializer):
        user = self.request.user
        if not user.venue:
            raise PermissionError("You are not associated with a venue.")
        serializer.save(venue=user.venue)


class RoomAvailabilityViewSet(viewsets.ModelViewSet):
    serializer_class = RoomAvailabilitySerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['room_type', 'date']

    def get_queryset(self):
        user = self.request.user
        if user.user_type in ['admin', 'support']:
            return RoomAvailability.objects.all()
        if user.venue:
            return RoomAvailability.objects.filter(room_type__venue=user.venue)
        return RoomAvailability.objects.none()

    def perform_create(self, serializer):
        user = self.request.user
        if not user.venue:
            raise PermissionError("You are not associated with a venue.")
        room_type = serializer.validated_data.get('room_type')
        if room_type.venue != user.venue:
            raise PermissionError("Room type does not belong to your venue.")
        serializer.save()


class VenueHiringViewSet(viewsets.ModelViewSet):
    serializer_class = VenueHiringSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ['status', 'hire_date']
    search_fields = ['renter_name', 'renter_phone', 'renter_email']

    def get_queryset(self):
        user = self.request.user
        if user.user_type in ['admin', 'support']:
            return VenueHiring.objects.all()
        if user.venue:
            return VenueHiring.objects.filter(venue=user.venue)
        return VenueHiring.objects.none()

    def perform_create(self, serializer):
        user = self.request.user
        if not user.venue:
            raise PermissionError("You are not associated with a venue.")
        if not TierService.has_module_access(user.venue, 'Explore'):
            raise PermissionError(
                f"Your {user.venue.subscription_tier} tier does not include venue hiring. "
                "Please upgrade to Rose or higher."
            )
        serializer.save(venue=user.venue)


class PublicExploreViewSet(viewsets.GenericViewSet):
    """
    Public endpoints for the Explore landing page.
    No authentication required.
    """
    permission_classes = [permissions.AllowAny]

    @action(detail=False, methods=['get'])
    def venues(self, request):
        queryset = Venue.objects.filter(
            public_listing=True,
            subscription_status__in=['trial', 'active']
        )

        search = request.query_params.get('search')
        if search:
            queryset = queryset.filter(
                Q(business_name__icontains=search) |
                Q(description__icontains=search)
            )

        open_now = request.query_params.get('open_now')
        if open_now and open_now.lower() == 'true':
            pass

        order_by = request.query_params.get('order_by', '-created_at')
        queryset = queryset.order_by(order_by)

        limit = int(request.query_params.get('limit', 20))
        queryset = queryset[:limit]

        serializer = PublicVenueListSerializer(queryset, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['get'])
    def venue_detail(self, request, pk=None):
        try:
            venue = Venue.objects.get(
                id=pk,
                public_listing=True,
                subscription_status__in=['trial', 'active']
            )
        except Venue.DoesNotExist:
            return Response(
                {'error': 'Venue not found or not publicly listed.'},
                status=status.HTTP_404_NOT_FOUND
            )

        from tables.models import Table
        from events.models import Event

        available_tables = Table.objects.filter(venue=venue, status='available').count()
        upcoming_events = Event.objects.filter(
            venue=venue,
            event_date__gte=timezone.now().date()
        ).order_by('event_date')[:5]

        serializer = PublicVenueDetailSerializer(venue)
        data = serializer.data
        data['available_tables'] = available_tables
        data['upcoming_events'] = [
            {
                'id': event.id,
                'name': event.event_name,
                'date': event.event_date,
                'tickets_available': event.max_capacity - event.checked_in_count
            }
            for event in upcoming_events
        ]
        data['hiring_available'] = TierService.has_module_access(venue, 'Explore')

        return Response(data)


# =============================================================================
# NEW: Ratings & Reviews Views
# =============================================================================

class RatingViewSet(viewsets.ModelViewSet):
    """
    Manage venue ratings and reviews.
    """
    serializer_class = RatingSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ['venue', 'rating', 'is_visible', 'is_verified']
    search_fields = ['review']

    def get_queryset(self):
        user = self.request.user
        if user.user_type in ['admin', 'support']:
            return Rating.objects.all()
        return Rating.objects.filter(is_visible=True)

    def get_serializer_class(self):
        if self.action == 'create':
            return RatingCreateSerializer
        return RatingSerializer

    def perform_create(self, serializer):
        user = self.request.user
        venue_id = self.request.data.get('venue')
        if not venue_id:
            raise ValidationError("Venue is required.")

        if Rating.objects.filter(user=user, venue_id=venue_id).exists():
            raise ValidationError("You have already rated this venue.")

        has_booking = Booking.objects.filter(
            user=user,
            venue_id=venue_id,
            status='completed'
        ).exists()

        rating = serializer.save(
            user=user,
            is_verified=has_booking,
            is_visible=True
        )

        self._update_rating_summary(rating.venue)

    def _update_rating_summary(self, venue):
        ratings = Rating.objects.filter(venue=venue, is_visible=True)
        total_reviews = ratings.count()
        if total_reviews == 0:
            return

        average = ratings.aggregate(avg=Avg('rating'))['avg'] or 0
        distribution = {}
        for i in range(1, 6):
            distribution[str(i)] = ratings.filter(rating=i).count()

        summary, created = RatingSummary.objects.update_or_create(
            venue=venue,
            defaults={
                'average_rating': round(average, 2),
                'total_reviews': total_reviews,
                'rating_distribution': distribution
            }
        )

    @action(detail=False, methods=['get'])
    def venue_ratings(self, request):
        venue_id = request.query_params.get('venue_id')
        if not venue_id:
            return Response({'error': 'venue_id is required.'}, status=400)

        ratings = Rating.objects.filter(venue_id=venue_id, is_visible=True).order_by('-created_at')
        serializer = self.get_serializer(ratings, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def summary(self, request):
        venue_id = request.query_params.get('venue_id')
        if not venue_id:
            return Response({'error': 'venue_id is required.'}, status=400)

        try:
            summary = RatingSummary.objects.get(venue_id=venue_id)
            serializer = RatingSummarySerializer(summary)
            return Response(serializer.data)
        except RatingSummary.DoesNotExist:
            return Response({
                'venue_id': venue_id,
                'average_rating': 0,
                'total_reviews': 0,
                'rating_distribution': {},
            })

    @action(detail=True, methods=['post'], permission_classes=[permissions.IsAdminUser])
    def toggle_visibility(self, request, pk=None):
        rating = self.get_object()
        rating.is_visible = not rating.is_visible
        rating.save(update_fields=['is_visible'])
        self._update_rating_summary(rating.venue)
        return Response({'is_visible': rating.is_visible})
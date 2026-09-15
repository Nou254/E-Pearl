# events/views.py

from rest_framework import viewsets, permissions, status, filters
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.decorators import action
from rest_framework.response import Response
from django.core.exceptions import ValidationError
from .models import Event, TicketTier, Ticket
from .serializers import (
    EventSerializer,
    EventCreateSerializer,
    TicketTierSerializer,
    TicketSerializer,
    TicketPurchaseSerializer,
    EventReportSerializer,
    PlatformReportSerializer,
)
from .services.ticket_service import TicketService
from .services.report_service import ReportService  # NEW
from venues.services.tier_service import TierService
from core.websocket_utils import notify_waiter, notify_control
from notifications.services.notification_service import NotificationService
import uuid


class EventViewSet(viewsets.ModelViewSet):
    """ViewSet for managing events."""
    serializer_class = EventSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['status', 'event_date']
    search_fields = ['event_name', 'event_description']
    ordering_fields = ['event_date', 'event_start_time']

    def get_queryset(self):
        user = self.request.user
        if user.user_type in ['admin', 'support']:
            return Event.objects.all()
        if user.venue:
            return Event.objects.filter(venue=user.venue)
        return Event.objects.filter(status__in=['published', 'active'])

    def get_serializer_class(self):
        if self.action == 'create':
            return EventCreateSerializer
        return EventSerializer

    def perform_create(self, serializer):
        user = self.request.user
        if not user.venue:
            raise PermissionError("You are not associated with a venue.")

        if not TierService.has_module_access(user.venue, 'Explore'):
            raise PermissionError(
                f"Your {user.venue.subscription_tier} tier does not support event creation. "
                "Please upgrade to Rose or higher."
            )

        serializer.save(venue=user.venue)

    @action(detail=True, methods=['post'])
    def publish(self, request, pk=None):
        event = self.get_object()
        if event.status != 'draft':
            return Response({'error': 'Event must be in draft status.'}, status=400)
        event.status = 'published'
        event.save()
        return Response({'status': 'published'})

    @action(detail=True, methods=['post'])
    def complete(self, request, pk=None):
        event = self.get_object()
        event.status = 'completed'
        event.save()
        return Response({'status': 'completed'})

    # =========================================================================
    # NEW: Post‑Event Reporting
    # =========================================================================
    @action(detail=True, methods=['get'])
    def report(self, request, pk=None):
        """
        Generate a detailed post‑event report.
        """
        event = self.get_object()
        try:
            report = ReportService.get_event_report(event.id)
            serializer = EventReportSerializer(report)
            return Response(serializer.data)
        except ValueError as e:
            return Response({'error': str(e)}, status=404)


class TicketTierViewSet(viewsets.ModelViewSet):
    """ViewSet for managing ticket tiers."""
    serializer_class = TicketTierSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['event', 'is_vip']

    def get_queryset(self):
        user = self.request.user
        if user.user_type in ['admin', 'support']:
            return TicketTier.objects.all()
        if user.venue:
            return TicketTier.objects.filter(venue=user.venue)
        return TicketTier.objects.none()

    def perform_create(self, serializer):
        user = self.request.user
        if not user.venue:
            raise PermissionError("You are not associated with a venue.")
        serializer.save(venue=user.venue)


class TicketViewSet(viewsets.ModelViewSet):
    """ViewSet for managing tickets."""
    serializer_class = TicketSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ['event', 'status', 'ticket_tier']
    search_fields = ['ticket_code', 'customer_name', 'customer_phone']

    def get_queryset(self):
        user = self.request.user
        if user.user_type in ['admin', 'support']:
            return Ticket.objects.all()
        if user.venue:
            return Ticket.objects.filter(venue=user.venue)
        return Ticket.objects.filter(user=user)

    def get_serializer_class(self):
        if self.action == 'purchase':
            return TicketPurchaseSerializer
        return TicketSerializer

    @action(detail=False, methods=['post'])
    def purchase(self, request):
        serializer = TicketPurchaseSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=400)

        user = request.user if request.user.is_authenticated else None
        venue_id = serializer.validated_data.get('venue_id')
        event_id = serializer.validated_data.get('event_id')
        tier_id = serializer.validated_data.get('tier_id')

        try:
            from venues.models import Venue
            venue = Venue.objects.get(id=venue_id)

            guest_session = None
            if not user:
                from guest_sessions.models import GuestSession
                guest_session = GuestSession.objects.create(
                    venue=venue,
                    session_token=str(uuid.uuid4()),
                    status='active'
                )

            ticket = TicketService.purchase_ticket(
                venue=venue,
                event_id=event_id,
                tier_id=tier_id,
                customer_data=serializer.validated_data['customer'],
                guest_session=guest_session,
                user=user
            )

            if user:
                NotificationService.send_templated_notification(
                    template_name='ticket_confirmation',
                    context_data={
                        'ticket_code': ticket.ticket_code,
                        'event_name': ticket.event.event_name,
                        'venue_name': ticket.venue.business_name,
                        'tier_name': ticket.ticket_tier.tier_name,
                        'price': ticket.price,
                    },
                    recipient_user=user,
                    venue=ticket.venue,
                    notification_type='ticket_confirmation',
                    channel='email'
                )

            return Response(TicketSerializer(ticket).data, status=201)

        except ValidationError as e:
            return Response({'error': str(e)}, status=400)
        except Exception as e:
            return Response({'error': str(e)}, status=500)

    @action(detail=True, methods=['post'])
    def check_in(self, request, pk=None):
        ticket = self.get_object()
        try:
            TicketService.check_in_ticket(ticket)
            if ticket.ticket_tier.is_vip and ticket.ticket_tier.reserved_table:
                if ticket.ticket_tier.reserved_table.assigned_waiter:
                    notify_waiter(str(ticket.ticket_tier.reserved_table.assigned_waiter.user.id), 'vip.arrived', {
                        'ticket_code': ticket.ticket_code,
                        'customer_name': ticket.customer_name,
                        'table_number': ticket.ticket_tier.reserved_table.table_number,
                    })
                notify_control(str(ticket.venue.id), 'table.reserved', {
                    'table_id': str(ticket.ticket_tier.reserved_table.id),
                    'table_number': ticket.ticket_tier.reserved_table.table_number,
                    'ticket_code': ticket.ticket_code,
                    'guest_name': ticket.customer_name,
                })
            return Response({'status': 'checked_in'})
        except ValidationError as e:
            return Response({'error': str(e)}, status=400)

    @action(detail=True, methods=['post'])
    def exit(self, request, pk=None):
        ticket = self.get_object()
        try:
            TicketService.exit_ticket(ticket)
            return Response({'status': 'exited'})
        except ValidationError as e:
            return Response({'error': str(e)}, status=400)

    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        ticket = self.get_object()
        reason = request.data.get('reason')
        try:
            TicketService.cancel_ticket(ticket, reason)
            return Response({'status': 'cancelled'})
        except ValidationError as e:
            return Response({'error': str(e)}, status=400)
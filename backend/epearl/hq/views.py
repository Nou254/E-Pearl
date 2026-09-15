# hq/views.py

from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters
from django.utils import timezone
from decimal import Decimal
from django.contrib.postgres.search import SearchVector, SearchQuery, SearchRank
from django.db.models import Q
from django.conf import settings

from .models import (
    PlatformSetting, SMSCredit, APIKey,
    ServiceStatus, RequestLog, FeatureFlag, Subscription
)
from .serializers import (
    PlatformSettingSerializer, SMSCreditSerializer, APIKeySerializer,
    ServiceStatusSerializer, RequestLogSerializer, RequestLogSearchSerializer,
    FeatureFlagSerializer, SubscriptionSerializer,
    ReconciliationSummarySerializer, SystemStatusSerializer,
    RefundReviewSerializer, RefundReviewListSerializer,  # NEW
    TrialManagementSerializer,  # NEW
)
from .services.health_service import HealthService
from .services.billing_service import BillingService
from .services.system_monitor import SystemMonitor
from .services.analytics_service import AnalyticsService
from users.permissions import HQAdminPermission, CanReviewRefunds
from payments.models import RefundRequest, RefundTransaction
from payments.services.refund_service import RefundService
from payments.services.refund_classification import RefundClassification
from venues.models import Venue
from notifications.services.notification_service import NotificationService


# =============================================================================
# Existing ViewSets
# =============================================================================

class PlatformSettingViewSet(viewsets.ModelViewSet):
    queryset = PlatformSetting.objects.all()
    serializer_class = PlatformSettingSerializer
    permission_classes = [permissions.IsAuthenticated, HQAdminPermission]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ['setting_type', 'is_active']
    search_fields = ['setting_key', 'description']


class SMSCreditViewSet(viewsets.ModelViewSet):
    queryset = SMSCredit.objects.all()
    serializer_class = SMSCreditSerializer
    permission_classes = [permissions.IsAuthenticated, HQAdminPermission]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['venue']


class APIKeyViewSet(viewsets.ModelViewSet):
    queryset = APIKey.objects.all()
    serializer_class = APIKeySerializer
    permission_classes = [permissions.IsAuthenticated, HQAdminPermission]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['venue', 'is_active']


# =============================================================================
# New ViewSets for HQ Completion
# =============================================================================

class HealthViewSet(viewsets.GenericViewSet):
    permission_classes = [permissions.IsAuthenticated, HQAdminPermission]

    @action(detail=False, methods=['get'])
    def status(self, request):
        services = HealthService.check_all_services()
        serializer = ServiceStatusSerializer(services, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['post'])
    def refresh(self, request):
        services = HealthService.check_all_services(force=True)
        serializer = ServiceStatusSerializer(services, many=True)
        return Response(serializer.data)


class RequestLogViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = RequestLog.objects.all()
    serializer_class = RequestLogSerializer
    permission_classes = [permissions.IsAuthenticated, HQAdminPermission]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['method', 'status_code', 'venue', 'user']
    ordering_fields = ['timestamp', 'response_time_ms', 'status_code']
    ordering = ['-timestamp']

    def get_queryset(self):
        qs = super().get_queryset()
        qs = qs.filter(is_deleted=False)
        start_date = self.request.query_params.get('start_date')
        end_date = self.request.query_params.get('end_date')
        if start_date:
            qs = qs.filter(timestamp__date__gte=start_date)
        if end_date:
            qs = qs.filter(timestamp__date__lte=end_date)
        return qs

    @action(detail=False, methods=['get'])
    def search(self, request):
        query = request.query_params.get('q')
        if not query:
            return Response({'error': 'Search term "q" is required.'}, status=400)

        qs = self.get_queryset()
        vector = SearchVector('path', 'endpoint', 'method', 'user_agent', 'request_body')
        search_query = SearchQuery(query, config='english')
        qs = qs.annotate(
            rank=SearchRank(vector, search_query)
        ).filter(rank__gt=0).order_by('-rank')

        status_code = request.query_params.get('status_code')
        if status_code:
            qs = qs.filter(status_code=status_code)

        page = self.paginate_queryset(qs)
        if page is not None:
            serializer = RequestLogSearchSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = RequestLogSearchSerializer(qs, many=True)
        return Response(serializer.data)


class FeatureFlagViewSet(viewsets.ModelViewSet):
    queryset = FeatureFlag.objects.all()
    serializer_class = FeatureFlagSerializer
    permission_classes = [permissions.IsAuthenticated, HQAdminPermission]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ['venue', 'feature_code', 'is_enabled']
    search_fields = ['feature_code', 'description']

    @action(detail=False, methods=['post'])
    def enable(self, request):
        venue_id = request.data.get('venue')
        feature_code = request.data.get('feature_code')
        try:
            flag = FeatureFlag.objects.get(venue_id=venue_id, feature_code=feature_code)
            flag.is_enabled = True
            flag.save()
        except FeatureFlag.DoesNotExist:
            flag = FeatureFlag.objects.create(
                venue_id=venue_id,
                feature_code=feature_code,
                is_enabled=True
            )
        serializer = self.get_serializer(flag)
        return Response(serializer.data)

    @action(detail=False, methods=['post'])
    def disable(self, request):
        venue_id = request.data.get('venue')
        feature_code = request.data.get('feature_code')
        try:
            flag = FeatureFlag.objects.get(venue_id=venue_id, feature_code=feature_code)
            flag.is_enabled = False
            flag.save()
        except FeatureFlag.DoesNotExist:
            flag = FeatureFlag.objects.create(
                venue_id=venue_id,
                feature_code=feature_code,
                is_enabled=False
            )
        serializer = self.get_serializer(flag)
        return Response(serializer.data)


class SystemStatusViewSet(viewsets.GenericViewSet):
    permission_classes = [permissions.IsAuthenticated, HQAdminPermission]

    @action(detail=False, methods=['get'])
    def overview(self, request):
        data = SystemMonitor.get_status()
        serializer = SystemStatusSerializer(data)
        return Response(serializer.data)


class FinancialReconciliationViewSet(viewsets.GenericViewSet):
    permission_classes = [permissions.IsAuthenticated, HQAdminPermission]

    @action(detail=False, methods=['get'])
    def summary(self, request):
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')
        if not start_date or not end_date:
            today = timezone.now().date()
            start_date = today.replace(day=1)
            end_date = today
        else:
            start_date = timezone.datetime.strptime(start_date, '%Y-%m-%d').date()
            end_date = timezone.datetime.strptime(end_date, '%Y-%m-%d').date()

        summary = BillingService.get_reconciliation_summary(start_date, end_date)
        serializer = ReconciliationSummarySerializer(summary)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def venue_breakdown(self, request):
        return Response({"detail": "Venue breakdown not yet implemented"})


class BillingViewSet(viewsets.GenericViewSet):
    permission_classes = [permissions.IsAuthenticated, HQAdminPermission]

    @action(detail=False, methods=['post'])
    def run_charge(self, request):
        from .management.commands.charge_subscriptions import Command
        cmd = Command()
        cmd.handle()
        return Response({"status": "Billing run completed."})


# =============================================================================
# Analytics ViewSet
# =============================================================================

class AnalyticsViewSet(viewsets.GenericViewSet):
    permission_classes = [permissions.IsAuthenticated, HQAdminPermission]

    @action(detail=False, methods=['get'])
    def overview(self, request):
        data = AnalyticsService.get_platform_overview()
        return Response(data)

    @action(detail=False, methods=['get'])
    def growth(self, request):
        days = int(request.query_params.get('days', 30))
        data = AnalyticsService.get_growth_analytics(days)
        return Response(data)

    @action(detail=False, methods=['get'])
    def financial(self, request):
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')
        data = AnalyticsService.get_financial_analytics(start_date, end_date)
        return Response(data)

    @action(detail=False, methods=['get'])
    def request_logs(self, request):
        days = int(request.query_params.get('days', 7))
        data = AnalyticsService.get_request_log_analytics(days)
        return Response(data)


# =============================================================================
# NEW: Refund Review ViewSet (HQ Admin)
# =============================================================================

class RefundReviewViewSet(viewsets.ModelViewSet):
    """
    HQ Admin view for reviewing and managing refund requests.
    """
    permission_classes = [permissions.IsAuthenticated, CanReviewRefunds]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['status', 'classification', 'reason', 'venue']
    search_fields = ['booking__id', 'customer__email', 'venue__business_name']
    ordering_fields = ['created_at', 'requested_amount']
    ordering = ['-created_at']

    def get_queryset(self):
        user = self.request.user
        if user.user_type in ['admin', 'support', 'finance'] or user.is_superuser:
            return RefundRequest.objects.all()
        # Venue owners/managers can only see their own venue's refunds
        if user.venue:
            return RefundRequest.objects.filter(venue=user.venue)
        return RefundRequest.objects.none()

    def get_serializer_class(self):
        if self.action == 'list':
            return RefundReviewListSerializer
        return RefundReviewSerializer

    @action(detail=True, methods=['post'])
    def approve(self, request, pk=None):
        """
        Approve a refund request with optional approved_amount override.
        Payload: {"approved_amount": 500.00, "resolution_notes": "..."}
        """
        refund_request = self.get_object()
        if refund_request.status != 'pending':
            return Response(
                {'error': f'Refund request is already {refund_request.status}.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        approved_amount = request.data.get('approved_amount')
        if approved_amount is not None:
            try:
                approved_amount = Decimal(str(approved_amount))
            except (ValueError, TypeError):
                return Response(
                    {'error': 'Invalid approved_amount value.'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            if approved_amount > refund_request.transaction.amount:
                return Response(
                    {'error': 'Approved amount cannot exceed original transaction amount.'},
                    status=status.HTTP_400_BAD_REQUEST
                )
        else:
            approved_amount = refund_request.requested_amount

        resolution_notes = request.data.get('resolution_notes', '')

        try:
            # Process refund via RefundService
            refund_transaction = RefundService.process_refund(
                refund_request,
                approved_amount,
                reviewed_by=request.user,
                notes=resolution_notes
            )
            refund_request.status = 'completed'
            refund_request.approved_amount = approved_amount
            refund_request.reviewed_by = request.user
            refund_request.reviewed_at = timezone.now()
            refund_request.resolution_notes = resolution_notes
            refund_request.save()

            # Update original transaction refund status
            original_txn = refund_request.transaction
            original_txn.amount_refunded += approved_amount
            if original_txn.amount_refunded >= original_txn.amount:
                original_txn.refund_status = 'full'
            else:
                original_txn.refund_status = 'partial'
            original_txn.save()

            # Update booking refund_status
            booking = refund_request.booking
            booking.refund_status = 'processed'
            booking.save(update_fields=['refund_status'])

            # Notify customer
            NotificationService.send_refund_approved(refund_request, refund_request.customer)

            return Response({
                'status': 'approved',
                'refund_request_id': str(refund_request.id),
                'refund_transaction_id': str(refund_transaction.id),
                'approved_amount': str(approved_amount)
            })
        except Exception as e:
            refund_request.status = 'failed'
            refund_request.resolution_notes = f"Processing failed: {str(e)}"
            refund_request.save()
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'])
    def reject(self, request, pk=None):
        """
        Reject a refund request.
        Payload: {"resolution_notes": "Reason for rejection"}
        """
        refund_request = self.get_object()
        if refund_request.status != 'pending':
            return Response(
                {'error': f'Refund request is already {refund_request.status}.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        resolution_notes = request.data.get('resolution_notes', 'Rejected by HQ admin.')

        refund_request.status = 'rejected'
        refund_request.reviewed_by = request.user
        refund_request.reviewed_at = timezone.now()
        refund_request.resolution_notes = resolution_notes
        refund_request.save()

        # Update booking refund_status
        booking = refund_request.booking
        booking.refund_status = 'rejected'
        booking.save(update_fields=['refund_status'])

        NotificationService.send_refund_rejected(refund_request, refund_request.customer)

        return Response({
            'status': 'rejected',
            'refund_request_id': str(refund_request.id)
        })


# =============================================================================
# NEW: Trial Management ViewSet (HQ Admin)
# =============================================================================

class TrialManagementViewSet(viewsets.GenericViewSet):
    """
    HQ Admin view for managing trial subscriptions.
    """
    permission_classes = [permissions.IsAuthenticated, HQAdminPermission]

    @action(detail=False, methods=['get'])
    def expiring_soon(self, request):
        """
        List venues whose trial will expire within the next N days.
        Query param: days (default 3)
        """
        days = int(request.query_params.get('days', 3))
        today = timezone.now().date()
        threshold = today + timezone.timedelta(days=days)
        venues = Venue.objects.filter(
            subscription_status='trial',
            next_billing_date__lte=threshold,
            next_billing_date__gte=today
        ).order_by('next_billing_date')
        serializer = TrialManagementSerializer(venues, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def expired(self, request):
        """
        List venues whose trial has expired (next_billing_date < today) but still in trial status.
        """
        today = timezone.now().date()
        venues = Venue.objects.filter(
            subscription_status='trial',
            next_billing_date__lt=today
        ).order_by('next_billing_date')
        serializer = TrialManagementSerializer(venues, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def extend_trial(self, request, pk=None):
        """
        Extend trial for a venue by a number of days.
        Payload: {"extra_days": 7}
        """
        venue = self.get_object()
        extra_days = int(request.data.get('extra_days', 7))
        if venue.subscription_status != 'trial':
            return Response(
                {'error': 'Venue is not in trial status.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        venue.next_billing_date = venue.next_billing_date + timezone.timedelta(days=extra_days)
        venue.save(update_fields=['next_billing_date'])
        return Response({
            'status': 'trial_extended',
            'venue_id': str(venue.id),
            'new_next_billing_date': venue.next_billing_date
        })

    @action(detail=True, methods=['post'])
    def end_trial(self, request, pk=None):
        """
        Manually end trial and transition to active (charge immediately).
        """
        venue = self.get_object()
        if venue.subscription_status != 'trial':
            return Response(
                {'error': 'Venue is not in trial status.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        # Attempt to charge first month
        from .services.billing_service import BillingService
        success = BillingService.attempt_payment(venue, BillingService.get_tier_price(venue.subscription_tier))
        if success:
            venue.subscription_status = 'active'
            venue.next_billing_date = timezone.now().date() + timezone.timedelta(days=30)
            venue.billing_cycle_start = timezone.now().date()
            venue.save()
            return Response({'status': 'active', 'message': 'Trial ended and first payment collected.'})
        else:
            venue.subscription_status = 'suspended'
            venue.save()
            return Response({'status': 'suspended', 'message': 'Trial ended but payment failed. Venue suspended.'})
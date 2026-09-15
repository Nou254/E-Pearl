# control/views.py

from rest_framework import viewsets, permissions, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from django.utils import timezone
from decimal import Decimal
from django.db import models as db_models
from django.core.exceptions import ValidationError
from datetime import timedelta
from django.conf import settings
import csv
from io import StringIO
from django.http import HttpResponse
from django.contrib.postgres.search import SearchVector, SearchQuery, SearchRank

from venues.models import Venue, VenueRefundPolicy
from users.models import User
from users.permissions import HasPermission, IsManager
from payments.models import Transaction
from orders.models import Order
from guest_sessions.models import GuestSession
from staff.models import Staff, StaffAttendance
from tables.models import Table
from .models import (
    PlatformAuditLog, VenueHealthMetrics, HQNotification,
    SupportTicket, VenueAuditLog,
    MenuCategory, MenuItem, Modifier,
    OnboardingProgress, StockAlertLog,
    WastageLog, MenuVersion
)
from .serializers import (
    PlatformAuditLogSerializer,
    VenueAuditLogSerializer,
    VenueHealthMetricsSerializer,
    HQNotificationSerializer,
    SupportTicketSerializer,
    KPISerializer,
    MenuCategorySerializer,
    MenuItemSerializer,
    ModifierSerializer,
    MenuItemPublicSerializer,
    OnboardingSerializer,
    WastageLogSerializer,
    MenuVersionSerializer,
    MenuItemSearchSerializer,
    VenueAuditLogSearchSerializer,
    VenueRefundPolicySerializer,
    TrialStatusSerializer,
)
from .services.dashboard_service import DashboardService
from .services.override_service import OverrideService
from .services.inventory_service import InventoryService


# =============================================================================
# HQ Admin Permissions
# =============================================================================

class HQAdminPermission(permissions.BasePermission):
    """Only platform admins, support, finance, and superusers can access Control."""

    def has_permission(self, request, view):
        user = request.user
        if not user or not user.is_authenticated:
            return False
        return user.is_superuser or user.user_type in ['admin', 'support', 'finance']


# =============================================================================
# Manager Dashboard (E-Pearl Control)
# =============================================================================

class ControlViewSet(viewsets.GenericViewSet):
    """
    E-Pearl Control – Manager Dashboard and Financial Overrides.
    """
    permission_classes = [permissions.IsAuthenticated, IsManager]

    def get_queryset(self):
        return VenueAuditLog.objects.none()

    @action(detail=False, methods=['get'])
    def dashboard(self, request):
        venue = request.user.venue
        if not venue:
            return Response({'error': 'You are not associated with a venue.'}, status=400)
        kpis = DashboardService.get_kpis(venue)
        serializer = KPISerializer(kpis)
        return Response(serializer.data)

    # ========== Trial Status ==========
    @action(detail=False, methods=['get'])
    def trial_status(self, request):
        """
        Get trial days remaining for the logged-in venue manager.
        """
        venue = request.user.venue
        if not venue:
            return Response({'error': 'You are not associated with a venue.'}, status=400)

        trial_days_total = getattr(settings, 'TRIAL_PERIOD_DAYS', 14)
        trial_days_remaining = 0
        trial_start_date = venue.trial_start_date
        next_billing_date = venue.next_billing_date

        if trial_start_date:
            days_used = (timezone.now().date() - trial_start_date).days
            trial_days_remaining = max(0, trial_days_total - days_used)

        data = {
            'trial_days_remaining': trial_days_remaining,
            'trial_days_total': trial_days_total,
            'subscription_status': venue.subscription_status,
            'trial_start_date': trial_start_date,
            'next_billing_date': next_billing_date,
            'is_trial_ending_soon': trial_days_remaining <= 3 and venue.subscription_status == 'trial',
        }
        serializer = TrialStatusSerializer(data)
        return Response(serializer.data)

    # ========== Refund Policy Management (GET, PUT, PATCH) ==========
    @action(detail=False, methods=['get', 'put', 'patch'])
    def refund_policy(self, request):
        """
        Get or update the refund policy for the logged-in venue.
        """
        venue = request.user.venue
        if not venue:
            return Response({'error': 'You are not associated with a venue.'}, status=400)

        # GET – return policy
        if request.method == 'GET':
            try:
                policy = venue.refund_policy_config
            except VenueRefundPolicy.DoesNotExist:
                # Create default policy if it doesn't exist
                policy = VenueRefundPolicy.objects.create(venue=venue)
            serializer = VenueRefundPolicySerializer(policy)
            return Response(serializer.data)

        # PUT/PATCH – update policy
        try:
            policy = venue.refund_policy_config
        except VenueRefundPolicy.DoesNotExist:
            policy = VenueRefundPolicy.objects.create(venue=venue)

        serializer = VenueRefundPolicySerializer(policy, data=request.data, partial=request.method == 'PATCH')
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['get'])
    def floor_plan(self, request):
        venue = request.user.venue
        if not venue:
            return Response({'error': 'You are not associated with a venue.'}, status=400)
        data = DashboardService.get_floor_plan(venue)
        return Response(data)

    @action(detail=False, methods=['get'])
    def activity_feed(self, request):
        venue = request.user.venue
        if not venue:
            return Response({'error': 'You are not associated with a venue.'}, status=400)
        limit = request.query_params.get('limit', 20)
        try:
            limit = int(limit)
        except ValueError:
            limit = 20
        data = DashboardService.get_staff_activity_feed(venue, limit)
        return Response(data)

    @action(detail=False, methods=['get'])
    def audit_log(self, request):
        venue = request.user.venue
        if not venue:
            return Response({'error': 'You are not associated with a venue.'}, status=400)
        queryset = VenueAuditLog.objects.filter(venue=venue).select_related('staff__user')
        action_type = request.query_params.get('action_type')
        if action_type:
            queryset = queryset.filter(action_type=action_type)
        start_date = request.query_params.get('start_date')
        if start_date:
            queryset = queryset.filter(timestamp__date__gte=start_date)
        end_date = request.query_params.get('end_date')
        if end_date:
            queryset = queryset.filter(timestamp__date__lte=end_date)
        order_by = request.query_params.get('order_by', '-timestamp')
        queryset = queryset.order_by(order_by)

        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = VenueAuditLogSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = VenueAuditLogSerializer(queryset, many=True)
        return Response(serializer.data)

    # ---------- Financial Overrides ----------

    @action(detail=False, methods=['post'], permission_classes=[HasPermission('force_capture')])
    def force_capture(self, request):
        venue = request.user.venue
        if not venue:
            return Response({'error': 'You are not associated with a venue.'}, status=400)
        manager_pin = request.data.get('manager_pin')
        if not request.user.check_pin(manager_pin):
            return Response({'error': 'Invalid manager PIN.'}, status=403)

        table_id = request.data.get('table_id')
        reason = request.data.get('reason', '')
        try:
            manager_staff = Staff.objects.get(user=request.user)
        except Staff.DoesNotExist:
            return Response({'error': 'Staff profile not found.'}, status=404)

        try:
            hold, transaction = OverrideService.force_capture(
                venue, table_id, manager_staff, reason
            )
            return Response({
                'status': 'success',
                'hold_id': str(hold.id),
                'transaction_id': str(transaction.id),
                'amount': float(hold.consumed_amount),
            })
        except ValidationError as e:
            return Response({'error': str(e)}, status=400)

    @action(detail=False, methods=['post'], permission_classes=[HasPermission('void_hold')])
    def void_hold(self, request):
        venue = request.user.venue
        if not venue:
            return Response({'error': 'You are not associated with a venue.'}, status=400)
        manager_pin = request.data.get('manager_pin')
        if not request.user.check_pin(manager_pin):
            return Response({'error': 'Invalid manager PIN.'}, status=403)

        table_id = request.data.get('table_id')
        reason = request.data.get('reason', '')
        try:
            manager_staff = Staff.objects.get(user=request.user)
        except Staff.DoesNotExist:
            return Response({'error': 'Staff profile not found.'}, status=404)

        try:
            hold, transaction = OverrideService.void_hold(
                venue, table_id, manager_staff, reason
            )
            return Response({
                'status': 'success',
                'hold_id': str(hold.id),
                'transaction_id': str(transaction.id),
                'amount': float(hold.declared_amount),
            })
        except ValidationError as e:
            return Response({'error': str(e)}, status=400)

    @action(detail=False, methods=['post'], permission_classes=[HasPermission('override_exit')])
    def manual_override_exit(self, request):
        venue = request.user.venue
        if not venue:
            return Response({'error': 'You are not associated with a venue.'}, status=400)
        manager_pin = request.data.get('manager_pin')
        if not request.user.check_pin(manager_pin):
            return Response({'error': 'Invalid manager PIN.'}, status=403)

        table_id = request.data.get('table_id')
        guest_session_id = request.data.get('guest_session_id')
        reason = request.data.get('reason', '')
        try:
            manager_staff = Staff.objects.get(user=request.user)
        except Staff.DoesNotExist:
            return Response({'error': 'Staff profile not found.'}, status=404)

        try:
            session = OverrideService.manual_override_exit(
                venue, table_id, guest_session_id, manager_staff, reason
            )
            return Response({
                'status': 'success',
                'guest_session_id': str(session.id),
                'headcount': session.table.current_headcount,
            })
        except ValidationError as e:
            return Response({'error': str(e)}, status=400)

    @action(detail=False, methods=['post'], permission_classes=[HasPermission('suspend_table')])
    def suspend_table(self, request):
        venue = request.user.venue
        if not venue:
            return Response({'error': 'You are not associated with a venue.'}, status=400)
        manager_pin = request.data.get('manager_pin')
        if not request.user.check_pin(manager_pin):
            return Response({'error': 'Invalid manager PIN.'}, status=403)

        table_id = request.data.get('table_id')
        reason = request.data.get('reason', '')
        try:
            manager_staff = Staff.objects.get(user=request.user)
        except Staff.DoesNotExist:
            return Response({'error': 'Staff profile not found.'}, status=404)

        try:
            table = OverrideService.suspend_table(
                venue, table_id, manager_staff, reason
            )
            return Response({
                'status': 'success',
                'table_id': str(table.id),
                'table_status': table.status,
            })
        except ValidationError as e:
            return Response({'error': str(e)}, status=400)

    # ---------- Audit Analytics ----------

    @action(detail=False, methods=['get'])
    def audit_analytics(self, request):
        user = request.user
        if user.is_superuser:
            queryset = VenueAuditLog.objects.all()
        else:
            venue = user.venue
            if not venue:
                return Response({'error': 'You are not associated with a venue.'}, status=400)
            queryset = VenueAuditLog.objects.filter(venue=venue)

        total = queryset.count()
        by_action = queryset.values('action_type').annotate(count=db_models.Count('id')).order_by('-count')
        financial_actions = queryset.filter(action_type__in=['force_capture', 'void_hold'])
        total_captured = financial_actions.filter(action_type='force_capture').aggregate(total=db_models.Sum('amount'))['total'] or Decimal('0.00')
        total_voided = financial_actions.filter(action_type='void_hold').aggregate(total=db_models.Sum('amount'))['total'] or Decimal('0.00')
        by_staff = queryset.values('staff__user__full_name').annotate(count=db_models.Count('id')).order_by('-count')[:10]
        seven_days_ago = timezone.now() - timedelta(days=7)
        daily_trend = queryset.filter(timestamp__gte=seven_days_ago).extra(
            {'day': "date_trunc('day', timestamp)"}
        ).values('day').annotate(count=db_models.Count('id')).order_by('day')
        suspicious = queryset.filter(
            action_type__in=['force_capture', 'void_hold', 'manual_override_exit', 'suspend_table'],
            reason__isnull=True
        ).count()

        return Response({
            'total_actions': total,
            'by_action_type': by_action,
            'financial': {
                'total_captured': str(total_captured),
                'total_voided': str(total_voided),
                'net_collected': str(total_captured - total_voided),
            },
            'top_staff': by_staff,
            'daily_trend': daily_trend,
            'suspicious_actions': suspicious,
            'warning': 'Actions without reason are flagged for review' if suspicious > 0 else None,
        })

    # ---------- Onboarding ----------
    @action(detail=False, methods=['get'])
    def onboarding_status(self, request):
        venue = request.user.venue
        if not venue:
            return Response({'error': 'You are not associated with a venue.'}, status=400)
        progress, created = OnboardingProgress.objects.get_or_create(venue=venue)
        serializer = OnboardingSerializer(progress)
        return Response(serializer.data)

    @action(detail=False, methods=['post'])
    def update_onboarding_step(self, request):
        venue = request.user.venue
        if not venue:
            return Response({'error': 'You are not associated with a venue.'}, status=400)
        progress, created = OnboardingProgress.objects.get_or_create(venue=venue)
        step = request.data.get('step')
        field = request.data.get('field')
        value = request.data.get('value', True)
        if field and hasattr(progress, field):
            setattr(progress, field, value)
            if step is not None:
                progress.step = step
            progress.save()
            serializer = OnboardingSerializer(progress)
            return Response(serializer.data)
        if step is not None:
            progress.step = step
            progress.save()
        serializer = OnboardingSerializer(progress)
        return Response(serializer.data)


# =============================================================================
# HQ Admin Views
# =============================================================================

class PlatformAuditLogViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = PlatformAuditLogSerializer
    permission_classes = [permissions.IsAuthenticated, HQAdminPermission]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['action_type']
    search_fields = ['description', 'target_model', 'target_id']
    ordering_fields = ['created_at']

    def get_queryset(self):
        return PlatformAuditLog.objects.all().order_by('-created_at')


class VenueHealthMetricsViewSet(viewsets.ModelViewSet):
    serializer_class = VenueHealthMetricsSerializer
    permission_classes = [permissions.IsAuthenticated, HQAdminPermission]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['venue']

    def get_queryset(self):
        return VenueHealthMetrics.objects.select_related('venue').all()

    @action(detail=False, methods=['post'])
    def refresh_all(self, request):
        venues = Venue.objects.filter(subscription_status__in=['trial', 'active'])
        updated = 0
        now = timezone.now()
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        for venue in venues:
            total_tables = Table.objects.filter(venue=venue).count()
            occupied_tables = Table.objects.filter(venue=venue, status='occupied').count()
            active_guests = GuestSession.objects.filter(venue=venue, status='active').count()
            pending_orders = Order.objects.filter(venue=venue, order_status__in=['pending', 'in_progress']).count()
            today_revenue = Transaction.objects.filter(
                venue=venue,
                transaction_status='success',
                transaction_time__gte=today_start
            ).aggregate(total=db_models.Sum('amount'))['total'] or Decimal('0')
            today_txns = Transaction.objects.filter(
                venue=venue,
                transaction_status='success',
                transaction_time__gte=today_start
            ).count()
            staff_on_duty = StaffAttendance.objects.filter(
                staff__venue=venue,
                scan_out_time__isnull=True
            ).count()
            open_tickets_count = SupportTicket.objects.filter(
                venue=venue, status__in=['open', 'in_progress']
            ).count()
            VenueHealthMetrics.objects.update_or_create(
                venue=venue,
                defaults={
                    'active_guests': active_guests,
                    'occupied_tables': occupied_tables,
                    'total_tables': total_tables,
                    'pending_orders': pending_orders,
                    'revenue_today': today_revenue,
                    'transactions_today': today_txns,
                    'staff_on_duty': staff_on_duty,
                    'open_tickets': open_tickets_count,
                }
            )
            updated += 1
        return Response({'message': f'Metrics refreshed for {updated} venues.'})

    @action(detail=True, methods=['post'])
    def refresh(self, request, pk=None):
        metrics = self.get_object()
        venue = metrics.venue
        today_start = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0)
        total_tables = Table.objects.filter(venue=venue).count()
        occupied_tables = Table.objects.filter(venue=venue, status='occupied').count()
        active_guests = GuestSession.objects.filter(venue=venue, status='active').count()
        pending_orders = Order.objects.filter(venue=venue, order_status__in=['pending', 'in_progress']).count()
        today_revenue = Transaction.objects.filter(
            venue=venue,
            transaction_status='success',
            transaction_time__gte=today_start
        ).aggregate(total=db_models.Sum('amount'))['total'] or Decimal('0')
        today_txns = Transaction.objects.filter(
            venue=venue,
            transaction_status='success',
            transaction_time__gte=today_start
        ).count()
        staff_on_duty = StaffAttendance.objects.filter(
            staff__venue=venue,
            scan_out_time__isnull=True
        ).count()
        open_tickets_count = SupportTicket.objects.filter(
            venue=venue, status__in=['open', 'in_progress']
        ).count()
        VenueHealthMetrics.objects.update_or_create(
            venue=venue,
            defaults={
                'active_guests': active_guests,
                'occupied_tables': occupied_tables,
                'total_tables': total_tables,
                'pending_orders': pending_orders,
                'revenue_today': today_revenue,
                'transactions_today': today_txns,
                'staff_on_duty': staff_on_duty,
                'open_tickets': open_tickets_count,
            }
        )
        metrics.refresh_from_db()
        serializer = self.get_serializer(metrics)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def summary(self, request):
        queryset = self.get_queryset()
        total_active_guests = sum(m.active_guests for m in queryset)
        total_occupied = sum(m.occupied_tables for m in queryset)
        total_tables = sum(m.total_tables for m in queryset)
        total_revenue = sum(m.revenue_today for m in queryset)
        total_open_tickets = sum(m.open_tickets for m in queryset)
        return Response({
            'total_active_guests': total_active_guests,
            'total_occupied_tables': total_occupied,
            'total_tables': total_tables,
            'occupancy_rate': round((total_occupied / total_tables * 100) if total_tables > 0 else 0, 1),
            'total_revenue_today': str(total_revenue),
            'total_open_tickets': total_open_tickets,
            'venues_count': queryset.count(),
        })


class HQNotificationViewSet(viewsets.ModelViewSet):
    serializer_class = HQNotificationSerializer
    permission_classes = [permissions.IsAuthenticated, HQAdminPermission]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['category', 'priority', 'is_read']
    search_fields = ['title', 'message']
    ordering_fields = ['created_at', 'priority']

    def get_queryset(self):
        return HQNotification.objects.select_related('venue', 'resolved_by').all()

    @action(detail=True, methods=['post'])
    def mark_read(self, request, pk=None):
        notification = self.get_object()
        notification.is_read = True
        notification.read_at = timezone.now()
        notification.save(update_fields=['is_read', 'read_at'])
        return Response({'status': 'marked read'})

    @action(detail=True, methods=['post'])
    def resolve(self, request, pk=None):
        notification = self.get_object()
        notification.is_read = True
        notification.read_at = timezone.now()
        notification.resolved_by = request.user
        notification.resolved_at = timezone.now()
        if notification.created_at:
            notification.resolution_time_seconds = (
                notification.resolved_at - notification.created_at
            ).total_seconds()
        notification.save(update_fields=['is_read', 'read_at', 'resolved_by', 'resolved_at', 'resolution_time_seconds'])
        return Response({'status': 'resolved'})

    @action(detail=False, methods=['get'])
    def unread_count(self, request):
        count = HQNotification.objects.filter(is_read=False).count()
        return Response({'unread_count': count})

    @action(detail=False, methods=['get'])
    def analytics(self, request):
        total = HQNotification.objects.count()
        unread = HQNotification.objects.filter(is_read=False).count()
        resolved = HQNotification.objects.filter(resolved_at__isnull=False).count()
        avg_resolution = HQNotification.objects.filter(
            resolution_time_seconds__gt=0
        ).aggregate(avg=db_models.Avg('resolution_time_seconds'))['avg'] or 0
        by_category = HQNotification.objects.values('category').annotate(count=db_models.Count('id'))
        by_priority = HQNotification.objects.values('priority').annotate(count=db_models.Count('id'))
        seven_days_ago = timezone.now() - timedelta(days=7)
        daily_trend = HQNotification.objects.filter(
            created_at__gte=seven_days_ago
        ).extra({'day': "date_trunc('day', created_at)"}).values('day').annotate(count=db_models.Count('id')).order_by('day')
        return Response({
            'total': total,
            'unread': unread,
            'resolved': resolved,
            'unresolved': total - resolved,
            'avg_resolution_hours': round(avg_resolution / 3600, 2) if avg_resolution else 0,
            'by_category': by_category,
            'by_priority': by_priority,
            'daily_trend': daily_trend,
        })


class SupportTicketViewSet(viewsets.ModelViewSet):
    serializer_class = SupportTicketSerializer
    permission_classes = [permissions.IsAuthenticated, HQAdminPermission]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['status', 'priority', 'category', 'venue']
    search_fields = ['subject', 'description']
    ordering_fields = ['created_at', 'priority']

    def get_queryset(self):
        return SupportTicket.objects.select_related('venue', 'raised_by', 'assigned_to').all()

    @action(detail=True, methods=['post'])
    def assign(self, request, pk=None):
        ticket = self.get_object()
        assignee_id = request.data.get('assigned_to')
        if not assignee_id:
            return Response({'error': 'assigned_to is required.'}, status=400)
        try:
            assignee = User.objects.get(id=assignee_id, user_type__in=['admin', 'support'])
        except User.DoesNotExist:
            return Response({'error': 'Invalid assignee.'}, status=400)
        ticket.assigned_to = assignee
        ticket.assigned_at = timezone.now()
        ticket.status = 'in_progress'
        ticket.save(update_fields=['assigned_to', 'assigned_at', 'status'])
        return Response({'status': 'assigned'})

    @action(detail=True, methods=['post'])
    def resolve_ticket(self, request, pk=None):
        ticket = self.get_object()
        ticket.status = 'resolved'
        ticket.resolved_at = timezone.now()
        if ticket.created_at:
            ticket.resolution_time_seconds = (ticket.resolved_at - ticket.created_at).total_seconds()
        ticket.save(update_fields=['status', 'resolved_at', 'resolution_time_seconds'])
        return Response({'status': 'resolved'})

    @action(detail=True, methods=['post'])
    def close_ticket(self, request, pk=None):
        ticket = self.get_object()
        ticket.status = 'closed'
        ticket.closed_at = timezone.now()
        ticket.save(update_fields=['status', 'closed_at'])
        return Response({'status': 'closed'})

    @action(detail=False, methods=['get'])
    def analytics(self, request):
        total = SupportTicket.objects.count()
        open_tickets = SupportTicket.objects.filter(status__in=['open', 'in_progress']).count()
        resolved = SupportTicket.objects.filter(status='resolved').count()
        closed = SupportTicket.objects.filter(status='closed').count()
        avg_resolution = SupportTicket.objects.filter(
            resolution_time_seconds__gt=0
        ).aggregate(avg=db_models.Avg('resolution_time_seconds'))['avg'] or 0
        by_priority = SupportTicket.objects.values('priority').annotate(count=db_models.Count('id'))
        by_venue = SupportTicket.objects.values('venue__business_name').annotate(
            count=db_models.Count('id')
        ).order_by('-count')[:10]
        sla_compliant = SupportTicket.objects.filter(
            status__in=['resolved', 'closed'],
            resolution_time_seconds__lte=86400
        ).count()
        sla_compliance_rate = round((sla_compliant / resolved * 100) if resolved > 0 else 0, 2)
        seven_days_ago = timezone.now() - timedelta(days=7)
        daily_trend = SupportTicket.objects.filter(
            created_at__gte=seven_days_ago
        ).extra({'day': "date_trunc('day', created_at)"}).values('day').annotate(count=db_models.Count('id')).order_by('day')
        return Response({
            'total': total,
            'open': open_tickets,
            'resolved': resolved,
            'closed': closed,
            'avg_resolution_hours': round(avg_resolution / 3600, 2) if avg_resolution else 0,
            'sla_compliance_rate': sla_compliance_rate,
            'by_priority': by_priority,
            'top_venues': by_venue,
            'daily_trend': daily_trend,
        })


class PlatformDashboardViewSet(viewsets.GenericViewSet):
    permission_classes = [permissions.IsAuthenticated, HQAdminPermission]

    @action(detail=False, methods=['get'])
    def overview(self, request):
        now = timezone.now()
        month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        total_venues = Venue.objects.count()
        active_venues = Venue.objects.filter(subscription_status__in=['trial', 'active']).count()
        pending_verifications = Venue.objects.filter(document_verification_status='pending').count()
        total_users = User.objects.count()
        active_users = User.objects.filter(is_active=True).count()
        total_revenue = Transaction.objects.filter(
            transaction_status='success'
        ).aggregate(total=db_models.Sum('amount'))['total'] or Decimal('0')
        revenue_this_month = Transaction.objects.filter(
            transaction_status='success',
            transaction_time__gte=month_start
        ).aggregate(total=db_models.Sum('amount'))['total'] or Decimal('0')
        open_tickets = SupportTicket.objects.filter(status__in=['open', 'in_progress']).count()
        unread_notifications = HQNotification.objects.filter(is_read=False).count()
        venues_by_tier = {}
        for tier_label, _ in Venue.SUBSCRIPTION_TIERS:
            venues_by_tier[tier_label] = Venue.objects.filter(subscription_tier=tier_label).count()
        recent_logs = PlatformAuditLog.objects.select_related('actor').order_by('-created_at')[:10]
        top_venues = list(
            Transaction.objects.filter(
                transaction_status='success',
                transaction_time__gte=month_start
            ).values('venue__business_name').annotate(
                total=db_models.Sum('amount')
            ).order_by('-total')[:5]
        )
        return Response({
            'total_venues': total_venues,
            'active_venues': active_venues,
            'pending_verifications': pending_verifications,
            'total_users': total_users,
            'active_users': active_users,
            'total_revenue': str(total_revenue),
            'revenue_this_month': str(revenue_this_month),
            'open_tickets': open_tickets,
            'unread_notifications': unread_notifications,
            'venues_by_tier': venues_by_tier,
            'recent_audit_logs': PlatformAuditLogSerializer(recent_logs, many=True).data,
            'top_venues_by_revenue': top_venues,
        })


# =============================================================================
# Menu Builder Views (with full‑text search)
# =============================================================================

class MenuCategoryViewSet(viewsets.ModelViewSet):
    serializer_class = MenuCategorySerializer
    permission_classes = [permissions.IsAuthenticated, IsManager]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['venue', 'is_active']
    search_fields = ['name']
    ordering_fields = ['display_order', 'name']

    def get_queryset(self):
        user = self.request.user
        if user.is_superuser or user.user_type in ['admin', 'support']:
            return MenuCategory.objects.all()
        if user.venue:
            return MenuCategory.objects.filter(venue=user.venue)
        return MenuCategory.objects.none()


class MenuItemViewSet(viewsets.ModelViewSet):
    serializer_class = MenuItemSerializer
    permission_classes = [permissions.IsAuthenticated, IsManager]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['venue', 'category', 'item_type', 'is_active', 'is_available']
    search_fields = ['name', 'description']
    ordering_fields = ['display_order', 'price', 'name']

    def get_queryset(self):
        user = self.request.user
        if user.is_superuser or user.user_type in ['admin', 'support']:
            return MenuItem.objects.all()
        if user.venue:
            return MenuItem.objects.filter(venue=user.venue)
        return MenuItem.objects.none()

    def perform_update(self, serializer):
        old_instance = self.get_object()
        instance = serializer.save()
        last_version = MenuVersion.objects.filter(menu_item=instance).order_by('-version_number').first()
        version_number = last_version.version_number + 1 if last_version else 1
        MenuVersion.objects.create(
            menu_item=instance,
            venue=instance.venue,
            name=instance.name,
            description=instance.description,
            price=instance.price,
            is_active=instance.is_active,
            is_available=instance.is_available,
            stock_count=instance.stock_count,
            low_stock_threshold=instance.low_stock_threshold,
            changed_by=self.request.user,
            change_reason=self.request.data.get('change_reason', ''),
            version_number=version_number
        )

    @action(detail=True, methods=['post'])
    def toggle_active(self, request, pk=None):
        item = self.get_object()
        item.is_active = not item.is_active
        item.save(update_fields=['is_active'])
        return Response({'status': 'toggled', 'is_active': item.is_active})

    @action(detail=True, methods=['post'])
    def toggle_available(self, request, pk=None):
        item = self.get_object()
        item.is_available = not item.is_available
        item.save(update_fields=['is_available'])
        return Response({'status': 'toggled', 'is_available': item.is_available})

    @action(detail=True, methods=['post'])
    def deplete_stock(self, request, pk=None):
        item = self.get_object()
        quantity = request.data.get('quantity', 1)
        if item.stock_count < quantity:
            return Response({'error': 'Insufficient stock'}, status=400)
        item.stock_count -= quantity
        item.save(update_fields=['stock_count'])
        return Response({
            'status': 'depleted',
            'stock_count': item.stock_count,
            'is_low_stock': item.is_low_stock,
            'is_out_of_stock': item.is_out_of_stock,
        })

    @action(detail=True, methods=['post'])
    def restore_stock(self, request, pk=None):
        item = self.get_object()
        quantity = request.data.get('quantity', 1)
        item.stock_count += quantity
        item.save(update_fields=['stock_count'])
        return Response({'status': 'restored', 'stock_count': item.stock_count})

    @action(detail=False, methods=['get'])
    def public_menu(self, request):
        venue_id = request.query_params.get('venue')
        if not venue_id:
            return Response({'error': 'venue parameter is required'}, status=400)
        items = MenuItem.objects.filter(
            venue_id=venue_id,
            is_active=True,
            is_available=True
        ).select_related('category', 'venue')
        serializer = MenuItemPublicSerializer(items, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def check_low_stock(self, request):
        venue = request.user.venue
        if not venue:
            return Response({'error': 'You are not associated with a venue.'}, status=400)
        items = InventoryService.get_low_stock_items(venue.id)
        serializer = MenuItemSerializer(items, many=True)
        return Response(serializer.data)

    # ---------- Bulk Import/Export ----------
    @action(detail=False, methods=['post'])
    def bulk_import(self, request):
        if 'file' not in request.FILES:
            return Response({'error': 'file required.'}, status=400)
        csv_file = request.FILES['file']
        decoded = csv_file.read().decode('utf-8')
        io_string = StringIO(decoded)
        reader = csv.DictReader(io_string)

        venue = request.user.venue
        if not venue:
            return Response({'error': 'You are not associated with a venue.'}, status=400)

        created_count = 0
        errors = []
        for row in reader:
            try:
                category_name = row.get('category_name')
                category, _ = MenuCategory.objects.get_or_create(venue=venue, name=category_name, defaults={'is_active': True})
                MenuItem.objects.create(
                    venue=venue,
                    category=category,
                    name=row['name'],
                    description=row.get('description', ''),
                    price=row['price'],
                    item_type=row.get('item_type', 'food'),
                    stock_count=int(row.get('stock_count', 0)),
                    is_active=row.get('is_active', 'True').lower() == 'true'
                )
                created_count += 1
            except Exception as e:
                errors.append(f"Row {reader.line_num}: {str(e)}")

        return Response({
            'status': 'import_complete',
            'created': created_count,
            'errors': errors
        })

    @action(detail=False, methods=['get'])
    def bulk_export(self, request):
        venue = request.user.venue
        if not venue:
            return Response({'error': 'You are not associated with a venue.'}, status=400)
        items = MenuItem.objects.filter(venue=venue).select_related('category')
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="menu_export_{venue.id}.csv"'
        writer = csv.writer(response)
        writer.writerow(['name', 'description', 'price', 'item_type', 'category_name', 'stock_count', 'is_active'])
        for item in items:
            writer.writerow([
                item.name,
                item.description,
                str(item.price),
                item.item_type,
                item.category.name if item.category else '',
                item.stock_count,
                'True' if item.is_active else 'False'
            ])
        return response

    # ---------- Full‑text Search ----------
    @action(detail=False, methods=['get'])
    def search(self, request):
        query = request.query_params.get('q')
        if not query:
            return Response({'error': 'Search term "q" is required.'}, status=400)

        user = request.user
        if user.is_superuser or user.user_type in ['admin', 'support']:
            qs = MenuItem.objects.all()
        elif user.venue:
            qs = MenuItem.objects.filter(venue=user.venue)
        else:
            return Response({'error': 'You are not associated with a venue.'}, status=400)

        venue_id = request.query_params.get('venue_id')
        if venue_id:
            qs = qs.filter(venue_id=venue_id)

        is_active = request.query_params.get('is_active')
        if is_active is not None:
            qs = qs.filter(is_active=is_active.lower() == 'true')

        item_type = request.query_params.get('item_type')
        if item_type:
            qs = qs.filter(item_type=item_type)

        vector = SearchVector('name', 'description', 'category__name')
        search_query = SearchQuery(query, config='english')
        qs = qs.annotate(
            rank=SearchRank(vector, search_query)
        ).filter(rank__gt=0).order_by('-rank')

        page = self.paginate_queryset(qs)
        if page is not None:
            serializer = MenuItemSearchSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = MenuItemSearchSerializer(qs, many=True)
        return Response(serializer.data)


class ModifierViewSet(viewsets.ModelViewSet):
    serializer_class = ModifierSerializer
    permission_classes = [permissions.IsAuthenticated, IsManager]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ['venue', 'menu_item', 'is_active', 'is_required']
    search_fields = ['name']

    def get_queryset(self):
        user = self.request.user
        if user.is_superuser or user.user_type in ['admin', 'support']:
            return Modifier.objects.all()
        if user.venue:
            return Modifier.objects.filter(venue=user.venue)
        return Modifier.objects.none()

    @action(detail=True, methods=['post'])
    def toggle_active(self, request, pk=None):
        modifier = self.get_object()
        modifier.is_active = not modifier.is_active
        modifier.save(update_fields=['is_active'])
        return Response({'status': 'toggled', 'is_active': modifier.is_active})


# =============================================================================
# Wastage Log Views
# =============================================================================

class WastageLogViewSet(viewsets.ModelViewSet):
    serializer_class = WastageLogSerializer
    permission_classes = [permissions.IsAuthenticated, IsManager]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['venue', 'status', 'menu_item']
    search_fields = ['reason']
    ordering_fields = ['created_at', 'amount']

    def get_queryset(self):
        user = self.request.user
        if user.is_superuser or user.user_type in ['admin', 'support']:
            return WastageLog.objects.all()
        if user.venue:
            return WastageLog.objects.filter(venue=user.venue)
        return WastageLog.objects.none()

    def perform_create(self, serializer):
        user = self.request.user
        if not user.venue:
            raise PermissionError("You are not associated with a venue.")
        serializer.save(venue=user.venue, created_by=user)

    @action(detail=True, methods=['post'])
    def write_off(self, request, pk=None):
        wastage = self.get_object()
        status = request.data.get('status')
        if status not in ['approved', 'rejected']:
            return Response({'error': 'status must be "approved" or "rejected".'}, status=400)

        wastage.status = status
        wastage.written_off_by = request.user
        wastage.written_off_at = timezone.now()
        wastage.resolution_notes = request.data.get('resolution_notes', '')
        wastage.save()

        return Response({'status': 'written_off'})


# =============================================================================
# Menu Version Views
# =============================================================================

class MenuVersionViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = MenuVersionSerializer
    permission_classes = [permissions.IsAuthenticated, IsManager]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['menu_item', 'venue']
    search_fields = ['name']
    ordering_fields = ['-created_at']

    def get_queryset(self):
        user = self.request.user
        if user.is_superuser or user.user_type in ['admin', 'support']:
            return MenuVersion.objects.all()
        if user.venue:
            return MenuVersion.objects.filter(venue=user.venue)
        return MenuVersion.objects.none()
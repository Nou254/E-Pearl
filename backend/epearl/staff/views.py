# staff/views.py

from rest_framework import viewsets, permissions, status, filters
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.decorators import action
from rest_framework.response import Response
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.db import models as db_models
from datetime import datetime
from django.contrib.postgres.search import SearchVector, SearchQuery, SearchRank

from .models import (
    Staff, Shift, ShiftStaff, StaffAttendance,
    ShiftHandover, CashCollection, PerformanceMetric
)
from .serializers import (
    StaffSerializer, StaffCreateSerializer,
    ShiftSerializer, ShiftStaffSerializer, StaffAttendanceSerializer,
    ShiftHandoverSerializer, StaffPerformanceSerializer,
    StaffPermissionSerializer,
    StaffSearchSerializer,  # NEW
)
from .services.staff_service import StaffService
from .services.qr_service import QRService
from .services.handover_service import HandoverService
from .services.performance_service import PerformanceService
from .services.reconciliation_service import ReconciliationService
from .services.overflow_service import OverflowService
from venues.services.tier_service import TierService
from users.models import StaffPermission, User
from tables.models import Table, Zone


class StaffViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing staff members.
    Only managers and owners can create/update/delete staff.
    """
    serializer_class = StaffSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['role', 'is_active', 'assigned_zone']
    search_fields = ['user__full_name', 'user__phone', 'user__email']
    ordering_fields = ['user__full_name', 'created_at']

    def get_queryset(self):
        user = self.request.user
        if user.user_type in ['admin', 'support']:
            return Staff.objects.all()
        if user.venue:
            return Staff.objects.filter(venue=user.venue)
        return Staff.objects.none()

    def get_serializer_class(self):
        if self.action == 'create':
            return StaffCreateSerializer
        return StaffSerializer

    def perform_create(self, serializer):
        user = self.request.user
        if not user.venue:
            raise PermissionError("You are not associated with a venue.")

        if user.user_type not in ['manager', 'owner']:
            raise PermissionError("You do not have permission to create staff.")

        staff_data = {
            'phone': serializer.validated_data.get('phone'),
            'email': serializer.validated_data.get('email'),
            'full_name': serializer.validated_data.get('full_name', ''),
        }
        role = serializer.validated_data.get('role')
        zone = serializer.validated_data.get('assigned_zone')
        shift_ids = serializer.validated_data.get('shift_ids', [])

        staff = StaffService.create_staff(
            venue=user.venue,
            user_data=staff_data,
            role=role,
            zone=zone,
            shift_ids=shift_ids
        )
        serializer.instance = staff

    @action(detail=True, methods=['post'])
    def assign_shift(self, request, pk=None):
        staff = self.get_object()
        shift_id = request.data.get('shift_id')
        if not shift_id:
            return Response({'error': 'shift_id required'}, status=400)
        try:
            shift = Shift.objects.get(id=shift_id, venue=staff.venue)
        except Shift.DoesNotExist:
            return Response({'error': 'Shift not found'}, status=404)
        shift_staff, created = ShiftStaff.objects.get_or_create(staff=staff, shift=shift)
        return Response({'status': 'assigned'})

    @action(detail=True, methods=['post'])
    def remove_shift(self, request, pk=None):
        staff = self.get_object()
        shift_id = request.data.get('shift_id')
        if not shift_id:
            return Response({'error': 'shift_id required'}, status=400)
        ShiftStaff.objects.filter(staff=staff, shift_id=shift_id).delete()
        return Response({'status': 'removed'})

    @action(detail=True, methods=['post'])
    def deactivate(self, request, pk=None):
        staff = self.get_object()
        staff.is_active = False
        staff.save()
        return Response({'status': 'deactivated'})

    @action(detail=True, methods=['post'])
    def activate(self, request, pk=None):
        staff = self.get_object()
        staff.is_active = True
        staff.save()
        return Response({'status': 'activated'})

    @action(detail=True, methods=['get'])
    def qr_code(self, request, pk=None):
        staff = self.get_object()
        qr_base64 = QRService.get_staff_qr_base64(staff)
        return Response({
            'staff_id': staff.id,
            'staff_name': staff.user.full_name,
            'qr_code': qr_base64
        })

    @action(detail=False, methods=['get'])
    def no_show(self, request):
        user = request.user
        if not user.venue:
            return Response({'error': 'You are not associated with a venue.'}, status=400)

        no_show_list = StaffService.get_no_show_staff(user.venue)
        data = [{
            'staff_id': item['staff'].id,
            'staff_name': item['staff'].user.full_name,
            'role': item['staff'].role,
            'shift_name': item['shift'].shift_name,
            'scheduled_start': item['scheduled_start'],
        } for item in no_show_list]
        return Response(data)

    @action(detail=False, methods=['post'])
    def scan_out_with_override(self, request):
        staff_id = request.data.get('staff_id')
        device_fingerprint = request.data.get('device_fingerprint')
        override = request.data.get('override', False)

        try:
            staff = Staff.objects.get(id=staff_id)
        except Staff.DoesNotExist:
            return Response({'error': 'Staff not found'}, status=404)

        manager_staff = None
        if override:
            if request.user.user_type not in ['manager', 'owner']:
                return Response({'error': 'Only managers can override high-value cash.'}, status=403)
            try:
                manager_staff = Staff.objects.get(user=request.user)
            except Staff.DoesNotExist:
                return Response({'error': 'Manager profile not found.'}, status=404)

        try:
            attendance = StaffService.scan_out(
                staff,
                device_fingerprint,
                override_manager=manager_staff if override else None
            )
            return Response(StaffAttendanceSerializer(attendance).data)
        except ValidationError as e:
            return Response({'error': str(e)}, status=400)

    # =========================================================================
    # NEW: Overflow / Busy Logic
    # =========================================================================

    @action(detail=True, methods=['post'])
    def set_busy(self, request, pk=None):
        staff = self.get_object()
        duration = request.data.get('duration', 300)
        try:
            duration = int(duration)
        except ValueError:
            duration = 300
        updated = OverflowService.set_busy(staff.id, duration)
        return Response({'status': 'busy', 'busy_until': updated.busy_until})

    @action(detail=True, methods=['post'])
    def set_available(self, request, pk=None):
        staff = self.get_object()
        OverflowService.set_available(staff.id)
        return Response({'status': 'available'})

    @action(detail=False, methods=['post'])
    def request_cover(self, request):
        user = request.user
        if not user.venue:
            return Response({'error': 'You are not associated with a venue.'}, status=400)

        table_id = request.data.get('table_id')
        from_staff_id = request.data.get('from_staff_id')
        if not table_id:
            return Response({'error': 'table_id required.'}, status=400)

        try:
            available = OverflowService.request_cover(user.venue, table_id, from_staff_id)
            return Response({
                'status': 'cover_assigned',
                'assigned_waiter_id': str(available.id),
                'assigned_waiter_name': available.user.full_name
            })
        except ValidationError as e:
            return Response({'error': str(e)}, status=400)

    @action(detail=False, methods=['post'])
    def auto_assign(self, request):
        user = request.user
        if not user.venue:
            return Response({'error': 'You are not associated with a venue.'}, status=400)

        table_id = request.data.get('table_id')
        zone_id = request.data.get('zone_id')
        if not table_id:
            return Response({'error': 'table_id required.'}, status=400)

        try:
            table = Table.objects.get(id=table_id, venue=user.venue)
            zone = table.zone if not zone_id else None
            if zone_id:
                zone = Zone.objects.get(id=zone_id, venue=user.venue)

            assigned = OverflowService.auto_assign(user.venue, zone, table_id)
            return Response({
                'status': 'auto_assigned',
                'assigned_waiter_id': str(assigned.id),
                'assigned_waiter_name': assigned.user.full_name
            })
        except ValidationError as e:
            return Response({'error': str(e)}, status=400)

    # =========================================================================
    # NEW: Full‑text Search for Staff
    # =========================================================================
    @action(detail=False, methods=['get'])
    def search(self, request):
        """
        Full‑text search over staff members (name, phone, email, role).
        Query param: q (search term)
        Optional: venue_id, role, is_active
        """
        query = request.query_params.get('q')
        if not query:
            return Response({'error': 'Search term "q" is required.'}, status=400)

        # Start with base queryset (venue scoped)
        user = request.user
        if user.is_superuser or user.user_type in ['admin', 'support']:
            qs = Staff.objects.all()
        elif user.venue:
            qs = Staff.objects.filter(venue=user.venue)
        else:
            return Response({'error': 'You are not associated with a venue.'}, status=400)

        # Additional filters
        venue_id = request.query_params.get('venue_id')
        if venue_id:
            qs = qs.filter(venue_id=venue_id)

        role = request.query_params.get('role')
        if role:
            qs = qs.filter(role=role)

        is_active = request.query_params.get('is_active')
        if is_active is not None:
            qs = qs.filter(is_active=is_active.lower() == 'true')

        # Full‑text search with ranking
        vector = SearchVector('user__full_name', 'user__phone', 'user__email', 'role')
        search_query = SearchQuery(query, config='english')
        qs = qs.annotate(
            rank=SearchRank(vector, search_query)
        ).filter(rank__gt=0).order_by('-rank')

        # Paginate
        page = self.paginate_queryset(qs)
        if page is not None:
            serializer = StaffSearchSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = StaffSearchSerializer(qs, many=True)
        return Response(serializer.data)


class ShiftViewSet(viewsets.ModelViewSet):
    serializer_class = ShiftSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.user_type in ['admin', 'support']:
            return Shift.objects.all()
        if user.venue:
            return Shift.objects.filter(venue=user.venue)
        return Shift.objects.none()

    def perform_create(self, serializer):
        user = self.request.user
        if not user.venue:
            raise PermissionError("You are not associated with a venue.")
        serializer.save(venue=user.venue)


class ShiftStaffViewSet(viewsets.ModelViewSet):
    serializer_class = ShiftStaffSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.user_type in ['admin', 'support']:
            return ShiftStaff.objects.all()
        if user.venue:
            return ShiftStaff.objects.filter(staff__venue=user.venue)
        return ShiftStaff.objects.none()


class StaffAttendanceViewSet(viewsets.ModelViewSet):
    serializer_class = StaffAttendanceSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['staff', 'attendance_status']

    def get_queryset(self):
        user = self.request.user
        if user.user_type in ['admin', 'support']:
            return StaffAttendance.objects.all()
        if user.venue:
            return StaffAttendance.objects.filter(staff__venue=user.venue)
        return StaffAttendance.objects.none()

    @action(detail=False, methods=['post'])
    def scan_in(self, request):
        staff_id = request.data.get('staff_id')
        device_fingerprint = request.data.get('device_fingerprint')
        try:
            staff = Staff.objects.get(id=staff_id)
        except Staff.DoesNotExist:
            return Response({'error': 'Staff not found'}, status=404)

        try:
            attendance = StaffService.scan_in(staff, device_fingerprint)
            return Response(StaffAttendanceSerializer(attendance).data)
        except ValidationError as e:
            return Response({'error': str(e)}, status=400)

    @action(detail=False, methods=['post'])
    def scan_out(self, request):
        staff_id = request.data.get('staff_id')
        device_fingerprint = request.data.get('device_fingerprint')

        try:
            staff = Staff.objects.get(id=staff_id)
        except Staff.DoesNotExist:
            return Response({'error': 'Staff not found'}, status=404)

        attendance = staff.get_current_attendance()
        if not attendance:
            return Response({'error': 'No active attendance record found.'}, status=400)

        # Check cash reconciliation before allowing exit
        if not ReconciliationService.check_staff_cash_reconciled(attendance.id):
            return Response(
                {'error': 'Cash not reconciled. Please see manager.'},
                status=400
            )

        try:
            attendance = StaffService.scan_out(staff, device_fingerprint)
            return Response(StaffAttendanceSerializer(attendance).data)
        except ValidationError as e:
            return Response({'error': str(e)}, status=400)

    @action(detail=True, methods=['post'])
    def reconcile_cash(self, request, pk=None):
        attendance = self.get_object()
        amount = request.data.get('amount')
        if amount is None:
            return Response({'error': 'amount required'}, status=400)

        try:
            manager_staff = Staff.objects.get(user=request.user)
            attendance.reconcile_cash(amount, manager_staff)
            return Response(StaffAttendanceSerializer(attendance).data)
        except ValidationError as e:
            return Response({'error': str(e)}, status=400)


# =============================================================================
# Staff Permission Management (Granular RBAC)
# =============================================================================

class StaffPermissionViewSet(viewsets.ModelViewSet):
    """
    Manage granular staff permissions (overrides).
    """
    serializer_class = StaffPermissionSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['staff', 'permission_code', 'is_granted']

    def get_queryset(self):
        user = self.request.user
        if user.is_superuser or user.user_type in ['admin', 'support']:
            return StaffPermission.objects.all()
        if user.venue:
            return StaffPermission.objects.filter(staff__venue=user.venue)
        return StaffPermission.objects.none()

    def perform_create(self, serializer):
        if self.request.user.user_type not in ['manager', 'owner']:
            raise PermissionError("You do not have permission to manage staff permissions.")
        serializer.save(granted_by=self.request.user)


# =============================================================================
# Shift Handover Management
# =============================================================================

class ShiftHandoverViewSet(viewsets.GenericViewSet):
    """
    Manage shift handovers.
    """
    permission_classes = [permissions.IsAuthenticated]

    @action(detail=False, methods=['post'])
    def initiate(self, request):
        from_staff_id = request.data.get('from_staff_id')
        to_staff_id = request.data.get('to_staff_id')
        zone_id = request.data.get('zone_id')

        if not all([from_staff_id, to_staff_id, zone_id]):
            return Response({'error': 'from_staff_id, to_staff_id, and zone_id are required.'}, status=400)

        try:
            tables = HandoverService.initiate_handover(from_staff_id, to_staff_id, zone_id)
            return Response({
                'status': 'handover initiated',
                'tables_transferred': tables.count()
            })
        except ValidationError as e:
            return Response({'error': str(e)}, status=400)

    @action(detail=False, methods=['get'])
    def history(self, request):
        user = request.user
        if not user.venue:
            return Response({'error': 'You are not associated with a venue.'}, status=400)

        handovers = ShiftHandover.objects.filter(venue=user.venue).order_by('-handed_over_at')
        serializer = ShiftHandoverSerializer(handovers, many=True)
        return Response(serializer.data)


# =============================================================================
# Staff Performance Reporting
# =============================================================================

class StaffReportViewSet(viewsets.GenericViewSet):
    permission_classes = [permissions.IsAuthenticated]

    @action(detail=False, methods=['get'])
    def attendance(self, request):
        user = request.user
        if not user.venue:
            return Response({'error': 'You are not associated with a venue.'}, status=400)

        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')
        if not start_date or not end_date:
            return Response({'error': 'start_date and end_date required.'}, status=400)

        try:
            start = datetime.strptime(start_date, '%Y-%m-%d').date()
            end = datetime.strptime(end_date, '%Y-%m-%d').date()
        except ValueError:
            return Response({'error': 'Invalid date format. Use YYYY-MM-DD.'}, status=400)

        role = request.query_params.get('role')
        report = StaffService.get_attendance_report(user.venue, start, end, role)
        return Response(report)

    @action(detail=False, methods=['get'])
    def performance(self, request):
        user = request.user
        if not user.venue:
            return Response({'error': 'You are not associated with a venue.'}, status=400)

        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')
        data = PerformanceService.get_waiter_metrics(user.venue.id, start_date, end_date)
        serializer = StaffPerformanceSerializer(data, many=True)
        return Response(serializer.data)


# =============================================================================
# Cached Performance Metrics
# =============================================================================

class StaffPerformanceViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = StaffPerformanceSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['staff', 'period_start', 'period_end']

    def get_queryset(self):
        user = self.request.user
        if user.is_superuser or user.user_type in ['admin', 'support']:
            return PerformanceMetric.objects.all()
        if user.venue:
            return PerformanceMetric.objects.filter(venue=user.venue)
        return PerformanceMetric.objects.none()
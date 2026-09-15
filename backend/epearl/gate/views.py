# gate/views.py

from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.core.exceptions import ValidationError
from django.utils import timezone
from .services.gate_service import GateService
from .serializers import (
    ExitScanRequestSerializer,
    TicketScanRequestSerializer,
    StaffScanRequestSerializer,
    StaffScanOutOverrideRequestSerializer,
    ManualOverrideRequestSerializer,
)
from staff.models import Staff
from staff.services.reconciliation_service import ReconciliationService  # NEW
from users.models import User
from guest_sessions.models import GuestSession  # NEW
from payments.services.payment_service import PaymentService  # NEW
import logging

logger = logging.getLogger(__name__)


class GateViewSet(viewsets.GenericViewSet):
    """
    E-Pearl Gate – Digital Bouncer.
    """
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = None  # No default serializer

    @action(detail=False, methods=['post'])
    def exit_scan(self, request):
        """
        Scan a guest's Exit QR.
        Returns green (allowed) or red (blocked) with reason.
        """
        serializer = ExitScanRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        qr_data = serializer.validated_data['qr_data']
        device_fingerprint = serializer.validated_data.get('device_fingerprint')
        venue = request.user.venue
        if not venue:
            return Response({'error': 'User not associated with a venue.'}, status=400)

        result = GateService.validate_exit_qr(qr_data, device_fingerprint, venue)

        # If allowed and requires escort, we need to handle the escort confirmation later
        if result['allowed'] and result.get('requires_escort'):
            # Return a special response indicating escort required
            return Response({
                'allowed': True,
                'requires_escort': True,
                'reason': result['reason'],
                'session_id': str(result['data']['session'].id)
            })

        # If allowed, we should decrement headcount and possibly auto-capture
        if result['allowed']:
            session = result['data']['session']
            # Decrement headcount on table
            table = session.table
            if table:
                table.current_headcount = max(table.current_headcount - 1, 0)
                table.save()
                # If headcount reaches zero, inactivate table (Last Man Out)
                if table.current_headcount == 0:
                    table.status = 'available'
                    table.save()
                    # TODO: Send WebSocket notification to Control

            # Auto-capture if enabled and hold exists
            auto_capture_result = self._execute_auto_capture(session)
            if auto_capture_result['success']:
                logger.info(f"Auto-capture successful for session {session.id}")
            elif auto_capture_result.get('message'):
                logger.warning(f"Auto-capture failed: {auto_capture_result['message']}")

        # Return response
        return Response({
            'allowed': result['allowed'],
            'reason': result['reason'],
            'requires_escort': result.get('requires_escort', False)
        })

    def _execute_auto_capture(self, session):
        """
        Helper to perform auto-capture if venue has it enabled.
        Returns dict with 'success' and 'message'.
        """
        venue = session.venue
        if not venue.auto_capture_enabled:
            return {'success': False, 'message': 'Auto-capture not enabled'}

        # Check if there is an active hold
        from payments.models import PreAuthHold
        hold = PreAuthHold.objects.filter(
            guest_session=session,
            hold_status='active'
        ).first()
        if not hold:
            return {'success': False, 'message': 'No active hold found'}

        # Capture the hold
        try:
            captured_hold, transaction = PaymentService.capture_hold(hold, hold.remaining_balance)
            # Update session financial status
            session.is_financially_cleared = True
            session.save(update_fields=['is_financially_cleared'])
            return {'success': True, 'message': 'Auto-capture successful'}
        except Exception as e:
            return {'success': False, 'message': str(e)}

    @action(detail=False, methods=['post'])
    def ticket_scan(self, request):
        """
        Scan a Ticket QR for event entry.
        """
        serializer = TicketScanRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        ticket_code = serializer.validated_data['ticket_code']
        event_id = serializer.validated_data.get('event_id')
        venue = request.user.venue
        if not venue:
            return Response({'error': 'User not associated with a venue.'}, status=400)

        result = GateService.validate_ticket_qr(ticket_code, venue, event_id)

        # If allowed, mark ticket as checked in
        if result['allowed']:
            ticket = result['ticket']
            ticket.checked_in = True
            ticket.checked_in_time = timezone.now()
            ticket.status = 'checked_in'
            ticket.save()

            # Update event checked-in count
            event = ticket.event
            event.checked_in_count += 1
            event.save()

            # If VIP table, reserve it
            if result.get('vip_table'):
                vip_table = result['vip_table']
                vip_table.status = 'reserved'
                vip_table.save()
                # TODO: Send WebSocket notification to Control and Waiter

        return Response({
            'allowed': result['allowed'],
            'reason': result['reason'],
            'vip_table_id': str(result.get('vip_table').id) if result.get('vip_table') else None
        })

    @action(detail=False, methods=['post'])
    def staff_scan_in(self, request):
        """
        Scan in a staff member using their Staff QR.
        """
        serializer = StaffScanRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        staff_qr = serializer.validated_data['staff_qr']
        device_fingerprint = serializer.validated_data.get('device_fingerprint')

        try:
            attendance = GateService.staff_scan_in(staff_qr, device_fingerprint)
            return Response({
                'status': 'scanned_in',
                'attendance_id': str(attendance.id),
                'staff_name': attendance.staff.user.full_name,
                'scan_in_time': attendance.scan_in_time
            })
        except ValidationError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['post'])
    def staff_scan_out(self, request):
        """
        Scan out a staff member using their Staff QR.
        Supports manager override for high-value cash.
        Also checks cash reconciliation before allowing exit.
        """
        serializer = StaffScanOutOverrideRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        staff_qr = serializer.validated_data['staff_qr']
        device_fingerprint = serializer.validated_data.get('device_fingerprint')
        override = serializer.validated_data.get('override', False)
        manager_pin = serializer.validated_data.get('manager_pin')

        override_manager = None
        if override:
            if not manager_pin:
                return Response({'error': 'manager_pin required for override.'}, status=400)
            # Verify manager PIN
            try:
                manager = User.objects.get(venue=request.user.venue, user_type='manager', is_active=True)
                if not manager.check_pin(manager_pin):
                    return Response({'error': 'Invalid manager PIN.'}, status=400)
                override_manager = Staff.objects.get(user=manager)
            except (User.DoesNotExist, Staff.DoesNotExist):
                return Response({'error': 'Manager not found.'}, status=400)

        # Retrieve the staff member and their current attendance
        try:
            staff = Staff.objects.get(staff_qr=staff_qr, venue=request.user.venue)
        except Staff.DoesNotExist:
            return Response({'error': 'Staff not found.'}, status=404)

        attendance = staff.get_current_attendance()
        if not attendance:
            return Response({'error': 'No active attendance record found.'}, status=400)

        # Check cash reconciliation before allowing exit (unless override)
        if not override:
            if not ReconciliationService.check_staff_cash_reconciled(attendance.id):
                return Response(
                    {'error': 'Cash not reconciled. Please see manager or use override.'},
                    status=400
                )

        try:
            # Call GateService to perform scan-out
            attendance = GateService.staff_scan_out(staff_qr, device_fingerprint, override_manager)
            return Response({
                'status': 'scanned_out',
                'attendance_id': str(attendance.id),
                'staff_name': attendance.staff.user.full_name,
                'scan_out_time': attendance.scan_out_time
            })
        except ValidationError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['post'])
    def manual_override(self, request):
        """
        Manual override for guest exit (lost phone, etc.).
        Requires manager PIN.
        """
        serializer = ManualOverrideRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        table_number = serializer.validated_data['table_number']
        guest_alias = serializer.validated_data['guest_alias']
        manager_pin = serializer.validated_data['manager_pin']
        venue = request.user.venue
        if not venue:
            return Response({'error': 'User not associated with a venue.'}, status=400)

        try:
            session = GateService.manual_override(table_number, guest_alias, manager_pin, venue)
            return Response({
                'status': 'override_successful',
                'session_id': str(session.id),
                'message': 'Guest cleared manually.'
            })
        except ValidationError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['post'])
    def cache_sessions(self, request):
        """
        Cache active sessions for offline mode.
        Called when guard logs in.
        """
        venue = request.user.venue
        if not venue:
            return Response({'error': 'User not associated with a venue.'}, status=400)
        GateService.cache_active_sessions(venue)
        return Response({'status': 'sessions cached for offline mode.'})

    @action(detail=False, methods=['post'])
    def confirm_escort(self, request):
        """
        Confirm that a drunk guest has been escorted.
        """
        session_id = request.data.get('session_id')
        if not session_id:
            return Response({'error': 'session_id required.'}, status=400)
        try:
            session = GuestSession.objects.get(id=session_id)
        except GuestSession.DoesNotExist:
            return Response({'error': 'Session not found.'}, status=404)
        # Mark escort as done – we could store a flag on the session or log it.
        # For now, we'll just log and proceed.
        logger.info(f"Escort confirmed for guest session {session_id} by guard {request.user.id}")
        # Decrement headcount as per normal exit
        table = session.table
        if table:
            table.current_headcount = max(table.current_headcount - 1, 0)
            table.save()
            if table.current_headcount == 0:
                table.status = 'available'
                table.save()
        return Response({'status': 'escort_confirmed'})
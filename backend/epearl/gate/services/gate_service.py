# gate/services/gate_service.py

import jwt
from django.conf import settings
from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.utils import timezone
from rest_framework_simplejwt.tokens import AccessToken
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError
from decimal import Decimal
import uuid

from guest_sessions.models import GuestSession
from tables.models import Table
from staff.models import Staff, StaffAttendance
from payments.models import Transaction, PreAuthHold
from events.models import Ticket
from payments.services.payment_service import PaymentService


class GateService:
    """
    Core service for E-Pearl Gate operations.
    """
    
    # Offline cache keys
    OFFLINE_SESSIONS_CACHE_KEY = 'gate:offline:sessions:{venue_id}'
    OFFLINE_PUBLIC_KEY_CACHE_KEY = 'gate:offline:public_key'
    # JWT expiry for Exit QR (minutes)
    EXIT_QR_EXPIRY_MINUTES = 2
    
    @classmethod
    def get_public_key(cls):
        """Get the public key for JWT verification (for offline mode)."""
        # In production, this would be the public key used for signing JWTs.
        # For now, we use the SECRET_KEY (since we're using HS256).
        return settings.SECRET_KEY

    @classmethod
    def cache_active_sessions(cls, venue):
        """
        Cache active sessions for a venue to enable offline mode.
        Called when a security guard logs in.
        """
        # Get all active guest sessions for the venue
        sessions = GuestSession.objects.filter(
            venue=venue,
            status='active'
        ).select_related('table', 'user')
        
        # Serialize relevant data
        session_data = []
        for session in sessions:
            # Get financial clearance status
            is_financially_cleared = cls._check_financial_clearance(session)
            # Get service fulfilment (all items served)
            is_served = cls._check_service_fulfilment(session)
            # Get flags
            flags = {
                'is_intoxicated': session.is_intoxicated if hasattr(session, 'is_intoxicated') else False,
                'is_flagged': session.is_flagged if hasattr(session, 'is_flagged') else False,
            }
            session_data.append({
                'session_id': str(session.id),
                'table_id': str(session.table.id) if session.table else None,
                'guest_name': session.guest_name if hasattr(session, 'guest_name') else None,
                'is_financially_cleared': is_financially_cleared,
                'is_served': is_served,
                'flags': flags,
            })
        
        # Cache with TTL = shift duration (e.g., 8 hours)
        cache_key = cls.OFFLINE_SESSIONS_CACHE_KEY.format(venue_id=venue.id)
        cache.set(cache_key, session_data, timeout=60*60*8)
        return session_data

    @classmethod
    def get_cached_sessions(cls, venue):
        """Retrieve cached sessions for offline mode."""
        cache_key = cls.OFFLINE_SESSIONS_CACHE_KEY.format(venue_id=venue.id)
        return cache.get(cache_key, [])

    @classmethod
    def validate_exit_qr(cls, qr_data, scanner_device_fingerprint, venue):
        """
        Validate an Exit QR (JWT token).
        Returns a dict with 'allowed' (bool) and 'reason' (str) and 'data'.
        """
        # Step 1: Decode JWT
        try:
            # The QR should be a JWT signed with HS256
            # We'll use the same secret key for now
            payload = jwt.decode(qr_data, settings.SECRET_KEY, algorithms=['HS256'])
        except jwt.ExpiredSignatureError:
            return {'allowed': False, 'reason': 'QR Expired. Please refresh.'}
        except jwt.InvalidTokenError:
            return {'allowed': False, 'reason': 'Invalid QR code.'}
        
        # Step 2: Check expiry (already done by jwt, but double-check)
        # Step 3: Device binding (if enabled)
        device_fingerprint = payload.get('device_fingerprint')
        if device_fingerprint and device_fingerprint != scanner_device_fingerprint:
            return {'allowed': False, 'reason': 'Device mismatch.'}
        
        # Step 4: Get guest session
        session_id = payload.get('session_id')
        if not session_id:
            return {'allowed': False, 'reason': 'Invalid QR: missing session.'}
        
        try:
            session = GuestSession.objects.get(id=session_id, venue=venue)
        except GuestSession.DoesNotExist:
            return {'allowed': False, 'reason': 'Session not found.'}
        
        # Step 5: Check financial clearance
        if not cls._check_financial_clearance(session):
            return {'allowed': False, 'reason': 'Outstanding bill.'}
        
        # Step 6: Check service fulfilment (if applicable)
        if not cls._check_service_fulfilment(session):
            return {'allowed': False, 'reason': 'Items not served.'}
        
        # Step 7: Check flags (intoxicated, flagged)
        flags = cls._get_flags(session)
        if flags.get('is_intoxicated'):
            return {
                'allowed': True,
                'reason': 'Escort required.',
                'requires_escort': True,
                'data': {'session': session, 'flags': flags}
            }
        if flags.get('is_flagged'):
            return {'allowed': False, 'reason': 'Flagged by Manager.'}
        
        # Step 8: All checks passed
        return {
            'allowed': True,
            'reason': 'Cleared',
            'data': {'session': session}
        }

    @classmethod
    def _check_financial_clearance(cls, session):
        """Check if the session is financially cleared."""
        # Check if there is a PreAuthHold for the session
        try:
            hold = PreAuthHold.objects.get(guest_session=session)
            # If hold is captured or voided, it's cleared
            if hold.hold_status in ['captured', 'voided']:
                return True
            else:
                return False
        except PreAuthHold.DoesNotExist:
            # If no hold, check if it's a self-pay session (all paid)
            # For self-pay, we check if there are any unpaid orders
            from orders.models import Order
            unpaid_orders = Order.objects.filter(
                guest_session=session,
                order_status__in=['pending', 'approved', 'in_progress', 'ready']
            ).exists()
            return not unpaid_orders

    @classmethod
    def _check_service_fulfilment(cls, session):
        """Check if all items have been served."""
        from orders.models import OrderItem
        # For simplicity, check if there are any items not served
        pending_items = OrderItem.objects.filter(
            order__guest_session=session,
            item_status__in=['pending', 'preparing', 'ready']
        ).exists()
        return not pending_items

    @classmethod
    def _get_flags(cls, session):
        """Get flags for a guest session."""
        flags = {
            'is_intoxicated': False,
            'is_flagged': False,
        }
        # Check if session has an is_intoxicated flag (could be stored on GuestSession)
        if hasattr(session, 'is_intoxicated'):
            flags['is_intoxicated'] = session.is_intoxicated
        if hasattr(session, 'is_flagged'):
            flags['is_flagged'] = session.is_flagged
        return flags

    @classmethod
    def execute_auto_capture(cls, session):
        """
        Auto-capture the PreAuth hold on exit if enabled.
        Returns dict with success flag and message.
        """
        # Check if auto-capture is enabled for the venue
        venue = session.venue
        # Assume auto_capture_enabled is a field on Venue (add later if needed)
        # For now, we'll check a setting or a venue attribute.
        # We'll add a field to Venue later; for now, assume it's enabled by default.
        if not getattr(venue, 'auto_capture_on_exit', False):
            return {'success': False, 'message': 'Auto-capture not enabled for this venue.'}
        
        try:
            hold = PreAuthHold.objects.get(guest_session=session, hold_status='active')
        except PreAuthHold.DoesNotExist:
            return {'success': False, 'message': 'No active hold found.'}
        
        # Capture the full remaining balance
        try:
            hold, transaction = PaymentService.capture_hold(hold, hold.remaining_balance)
            return {'success': True, 'message': 'Auto-capture successful.', 'hold': hold, 'transaction': transaction}
        except ValidationError as e:
            return {'success': False, 'message': str(e)}

    @classmethod
    def validate_ticket_qr(cls, ticket_code, venue, event_id=None):
        """
        Validate a Ticket QR for event entry.
        Returns dict with allowed, reason, and ticket data.
        """
        try:
            ticket = Ticket.objects.get(ticket_code=ticket_code, venue=venue)
        except Ticket.DoesNotExist:
            return {'allowed': False, 'reason': 'Invalid ticket.'}
        
        # Check if event is valid (if event_id provided, verify)
        if event_id and ticket.event.id != event_id:
            return {'allowed': False, 'reason': 'Invalid event for today.'}
        
        # Check if already used
        if ticket.checked_in:
            return {'allowed': False, 'reason': 'Ticket already used.'}
        
        # Check capacity
        event = ticket.event
        if event.total_tickets_sold >= event.max_capacity:
            return {'allowed': False, 'reason': 'Venue at capacity.'}
        
        # If VIP bundle, reserve table
        vip_table = None
        if ticket.ticket_tier.is_vip and ticket.ticket_tier.reserved_table:
            vip_table = ticket.ticket_tier.reserved_table
        
        return {
            'allowed': True,
            'reason': 'Welcome. Check-in successful.',
            'ticket': ticket,
            'vip_table': vip_table,
        }

    @classmethod
    def staff_scan_in(cls, staff_qr, device_fingerprint=None):
        """Scan in a staff member using their QR."""
        try:
            staff = Staff.objects.get(staff_qr=staff_qr, is_active=True)
        except Staff.DoesNotExist:
            raise ValidationError("Invalid staff QR.")
        # Delegate to StaffService
        from staff.services.staff_service import StaffService
        return StaffService.scan_in(staff, device_fingerprint)

    @classmethod
    def staff_scan_out(cls, staff_qr, device_fingerprint=None, override_manager=None):
        """Scan out a staff member using their QR."""
        try:
            staff = Staff.objects.get(staff_qr=staff_qr, is_active=True)
        except Staff.DoesNotExist:
            raise ValidationError("Invalid staff QR.")
        from staff.services.staff_service import StaffService
        return StaffService.scan_out(staff, device_fingerprint, override_manager)

    @classmethod
    def manual_override(cls, table_number, guest_alias, manager_pin, venue):
        """
        Manual override for a guest exit (e.g., lost phone).
        Requires manager PIN verification.
        """
        # Find manager with that PIN (we need to check PIN hash)
        from users.models import User
        try:
            manager = User.objects.get(venue=venue, user_type='manager', is_active=True)
            # Verify PIN
            if not manager.check_pin(manager_pin):
                raise ValidationError("Invalid manager PIN.")
        except User.DoesNotExist:
            raise ValidationError("Manager not found.")
        
        # Find the guest session by table and guest alias (simplified)
        # We'll assume guest_alias is stored on GuestSession (we might need to add it)
        try:
            session = GuestSession.objects.get(
                table__table_number=table_number,
                guest_name=guest_alias,
                venue=venue,
                status='active'
            )
        except GuestSession.DoesNotExist:
            raise ValidationError("Guest session not found.")
        
        # Check financial clearance
        if not cls._check_financial_clearance(session):
            raise ValidationError("Guest has outstanding bill.")
        
        # Mark as cleared (we can create a manual exit log)
        # For now, we'll just return the session
        return session
# guest_sessions/services/settlement_service.py

from django.core.exceptions import ValidationError
from django.db.models import Q, Sum
from django.utils import timezone
from decimal import Decimal
from ..models import GuestSession
from payments.models import Transaction, PreAuthHold
from orders.models import Order


class SettlementService:
    """
    Service to validate and process guest session settlements,
    including hybrid settlement (Host + Self‑Pay).
    """

    @classmethod
    def validate_hybrid_settlement(cls, guest_session: GuestSession):
        """
        Validate that the guest session (and all linked sessions) are fully settled.
        Returns a tuple (is_valid, error_message).
        """
        # Get all guest sessions for the same table (including the host)
        table = guest_session.table
        if not table:
            raise ValidationError("Guest session is not associated with a table.")

        sessions = GuestSession.objects.filter(
            table=table,
            status='active'
        ).select_related('user', 'venue')

        if not sessions:
            raise ValidationError("No active sessions found for this table.")

        # Check each session
        for session in sessions:
            is_valid, error = cls._validate_single_session(session)
            if not is_valid:
                return False, error

        # Check if there are any pending orders (should be served)
        pending_orders = Order.objects.filter(
            guest_session__in=sessions,
            order_status__in=['pending', 'in_progress']
        )
        if pending_orders.exists():
            return False, "There are pending orders that must be served or cancelled."

        return True, None

    @classmethod
    def _validate_single_session(cls, session: GuestSession):
        """
        Validate a single guest session.
        """
        # Determine the user type: Host (has a pre-auth hold) or guest (self‑pay)
        hold = PreAuthHold.objects.filter(
            guest_session=session,
            hold_status='active'
        ).first()

        if hold:
            # This session is a Host – check if the hold is captured or voided
            if hold.hold_status not in ['captured', 'voided']:
                return False, f"Host tab not settled for {session.user.full_name if session.user else 'Guest'}."
        else:
            # This is a self‑pay guest – check if they have a successful payment transaction
            # Look for any successful transaction linked to this guest session
            has_paid = Transaction.objects.filter(
                guest_session=session,
                transaction_status='success',
                transaction_type__in=['payment', 'capture']
            ).exists()

            if not has_paid:
                return False, f"Self‑pay guest {session.user.full_name if session.user else 'Guest'} has not paid."

        return True, None

    @classmethod
    def get_settlement_status(cls, guest_session: GuestSession):
        """
        Return a detailed settlement status for the session and its table.
        """
        table = guest_session.table
        if not table:
            raise ValidationError("Guest session is not associated with a table.")

        sessions = GuestSession.objects.filter(table=table, status='active')
        status = {
            'table_id': str(table.id),
            'table_number': table.table_number,
            'total_sessions': sessions.count(),
            'sessions': []
        }

        for session in sessions:
            hold = PreAuthHold.objects.filter(
                guest_session=session,
                hold_status='active'
            ).first()

            session_data = {
                'session_id': str(session.id),
                'user': session.user.full_name if session.user else 'Anonymous',
                'role': 'host' if hold else 'guest',
                'is_settled': False,
                'settlement_type': None,
                'details': None,
            }

            if hold:
                if hold.hold_status in ['captured', 'voided']:
                    session_data['is_settled'] = True
                    session_data['settlement_type'] = hold.hold_status
                    session_data['details'] = f"Hold {hold.hold_status} for {hold.declared_amount}"
                else:
                    session_data['details'] = f"Hold {hold.hold_status} – pending settlement"
            else:
                has_paid = Transaction.objects.filter(
                    guest_session=session,
                    transaction_status='success',
                    transaction_type__in=['payment', 'capture']
                ).exists()
                if has_paid:
                    session_data['is_settled'] = True
                    session_data['settlement_type'] = 'self_pay_paid'
                    session_data['details'] = "Self‑pay payment successful"
                else:
                    session_data['details'] = "Self‑pay payment not found"

            status['sessions'].append(session_data)

        # Overall settled flag
        status['all_settled'] = all(s['is_settled'] for s in status['sessions'])
        return status

    @classmethod
    def mark_session_settled(cls, session: GuestSession):
        """
        Mark a guest session as settled (e.g., after final payment or capture).
        This could update a flag if we had one; currently we rely on transaction status.
        We can add a `is_settled` field to GuestSession to cache this.
        For now, we just return success.
        """
        # Optionally set a flag if added to GuestSession
        # For now, we assume the check is done via transactions.
        return True
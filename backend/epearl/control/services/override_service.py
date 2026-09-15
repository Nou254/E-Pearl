# control/services/override_service.py

from django.core.exceptions import ValidationError
from django.utils import timezone
from payments.services.payment_service import PaymentService
from tables.models import Table
from guest_sessions.models import GuestSession
from staff.models import Staff
from control.models import VenueAuditLog
import logging

logger = logging.getLogger(__name__)


class OverrideService:
    """
    Handles manager financial overrides with audit logging.
    """

    @classmethod
    def force_capture(cls, venue, table_id, manager_staff, reason=None):
        table = Table.objects.get(id=table_id, venue=venue)
        session = GuestSession.objects.filter(
            table=table,
            status='active'
        ).first()
        if not session:
            raise ValidationError("No active guest session found for this table.")

        from payments.models import PreAuthHold
        hold = PreAuthHold.objects.filter(
            guest_session=session,
            hold_status='active'
        ).first()
        if not hold:
            raise ValidationError("No active hold found for this session.")

        amount = hold.remaining_balance
        hold, transaction = PaymentService.capture_hold(hold, amount)

        VenueAuditLog.objects.create(
            venue=venue,
            staff=manager_staff,
            guest_session=session,
            table=table,
            action_type='force_capture',
            action_description=f"Force captured KES {amount} from Table {table.table_number}",
            amount=amount,
            reason=reason,
        )

        table.status = 'available'
        table.save()

        return hold, transaction

    @classmethod
    def void_hold(cls, venue, table_id, manager_staff, reason=None):
        table = Table.objects.get(id=table_id, venue=venue)
        session = GuestSession.objects.filter(
            table=table,
            status='active'
        ).first()
        if not session:
            raise ValidationError("No active guest session found.")

        from payments.models import PreAuthHold
        hold = PreAuthHold.objects.filter(
            guest_session=session,
            hold_status='active'
        ).first()
        if not hold:
            raise ValidationError("No active hold found.")

        hold, transaction = PaymentService.void_hold(hold)

        VenueAuditLog.objects.create(
            venue=venue,
            staff=manager_staff,
            guest_session=session,
            table=table,
            action_type='void_hold',
            action_description=f"Voided hold (KES {hold.declared_amount}) for Table {table.table_number}",
            amount=hold.declared_amount,
            reason=reason,
        )

        table.status = 'available'
        table.save()

        return hold, transaction

    @classmethod
    def manual_override_exit(cls, venue, table_id, guest_session_id, manager_staff, reason=None):
        session = GuestSession.objects.get(id=guest_session_id, venue=venue, table__id=table_id)
        if session.session_status == 'exited':
            raise ValidationError("Guest already exited.")

        session.session_status = 'exited'
        session.end_time = timezone.now()
        session.save()

        table = session.table
        table.current_headcount = max(table.current_headcount - 1, 0)
        table.save()
        if table.current_headcount == 0:
            table.status = 'available'
            table.save()

        VenueAuditLog.objects.create(
            venue=venue,
            staff=manager_staff,
            guest_session=session,
            table=table,
            action_type='manual_override_exit',
            action_description=f"Manually overrode exit for guest from Table {table.table_number}",
            reason=reason,
        )

        return session

    @classmethod
    def suspend_table(cls, venue, table_id, manager_staff, reason=None):
        table = Table.objects.get(id=table_id, venue=venue)
        if table.status == 'suspended':
            raise ValidationError("Table already suspended.")

        table.status = 'suspended'
        table.save()

        VenueAuditLog.objects.create(
            venue=venue,
            staff=manager_staff,
            table=table,
            action_type='suspend_table',
            action_description=f"Suspended Table {table.table_number}",
            reason=reason,
        )

        return table
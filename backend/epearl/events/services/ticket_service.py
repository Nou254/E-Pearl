# events/services/ticket_service.py

from decimal import Decimal
from django.db import transaction
from django.core.exceptions import ValidationError
from django.utils import timezone
from payments.services.payment_service import PaymentService
from notifications.services.notification_service import NotificationService
from ..models import Event, TicketTier, Ticket
import uuid


class TicketService:
    """Service for ticket-related operations."""

    PLATFORM_FEE_PERCENTAGE = 2

    @classmethod
    @transaction.atomic
    def purchase_ticket(cls, venue, event_id, tier_id, customer_data, guest_session=None, user=None):
        try:
            event = Event.objects.get(id=event_id, venue=venue, status__in=['published', 'active'])
        except Event.DoesNotExist:
            raise ValidationError("Event not available.")

        if not event.is_ticket_sales_active():
            raise ValidationError("Ticket sales are not active for this event.")

        try:
            tier = TicketTier.objects.get(id=tier_id, event=event)
        except TicketTier.DoesNotExist:
            raise ValidationError("Ticket tier not found.")

        if tier.quantity_sold >= tier.quantity_limit:
            raise ValidationError("This ticket tier is sold out.")

        if event.tickets_remaining() <= 0:
            raise ValidationError("Event is sold out.")

        # Create transaction for payment (stub)
        platform_fee = tier.price * Decimal(cls.PLATFORM_FEE_PERCENTAGE / 100)

        ticket = Ticket.objects.create(
            venue=venue,
            event=event,
            ticket_tier=tier,
            guest_session=guest_session,
            user=user,
            ticket_code=str(uuid.uuid4())[:8].upper(),
            customer_name=customer_data.get('name'),
            customer_email=customer_data.get('email'),
            customer_phone=customer_data.get('phone'),
            price=tier.price,
            platform_fee=platform_fee,
            is_digital=True,
            status='purchased'
        )

        tier.quantity_sold += 1
        tier.save()

        event.total_tickets_sold += 1
        event.gross_revenue += tier.price
        event.platform_fee_collected += platform_fee
        event.save()

        # Send ticket purchase confirmation
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

        return ticket

    @classmethod
    def check_in_ticket(cls, ticket):
        if ticket.checked_in:
            raise ValidationError("Ticket already checked in.")

        if ticket.status in ['cancelled', 'refunded']:
            raise ValidationError("Ticket is not valid.")

        ticket.checked_in = True
        ticket.checked_in_time = timezone.now()
        ticket.status = 'checked_in'
        ticket.save()

        ticket.event.checked_in_count += 1
        ticket.event.save()

        if ticket.ticket_tier.is_vip and ticket.ticket_tier.reserved_table:
            table = ticket.ticket_tier.reserved_table
            table.reserve()
            table.save()

        return ticket

    @classmethod
    def exit_ticket(cls, ticket):
        if ticket.exited:
            raise ValidationError("Ticket already exited.")

        ticket.exited = True
        ticket.exited_time = timezone.now()
        ticket.status = 'exited'
        ticket.save()

        if ticket.ticket_tier.is_vip and ticket.ticket_tier.reserved_table:
            table = ticket.ticket_tier.reserved_table
            table.free()
            table.save()

        return ticket

    @classmethod
    def cancel_ticket(cls, ticket, reason=None):
        if ticket.status in ['cancelled', 'refunded']:
            raise ValidationError("Ticket already cancelled.")

        if ticket.checked_in:
            raise ValidationError("Cannot cancel a checked-in ticket.")

        ticket.status = 'cancelled'
        ticket.save()

        # Send ticket refunded notification
        if ticket.user:
            NotificationService.send_ticket_refunded(ticket, ticket.user)

        ticket.event.total_tickets_sold -= 1
        ticket.event.gross_revenue -= ticket.price
        ticket.event.platform_fee_collected -= ticket.platform_fee
        ticket.event.save()

        ticket.ticket_tier.quantity_sold -= 1
        ticket.ticket_tier.save()

        return ticket
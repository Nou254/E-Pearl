# events/services/report_service.py

from django.db.models import Count, Sum, Q
from django.utils import timezone
from decimal import Decimal
from ..models import Event, Ticket, TicketTier


class ReportService:
    """
    Service to generate post‑event reports for ticket sales, check‑ins, no‑shows, and platform fees.
    """

    @classmethod
    def get_event_report(cls, event_id):
        """
        Generate a comprehensive report for a single event.
        """
        try:
            event = Event.objects.get(id=event_id)
        except Event.DoesNotExist:
            raise ValueError("Event not found")

        # Ticket totals
        total_tickets = event.total_tickets_sold
        checked_in_count = event.checked_in_count
        no_show_count = total_tickets - checked_in_count
        if no_show_count < 0:
            no_show_count = 0

        # Revenue breakdown by tier
        tiers = TicketTier.objects.filter(event=event)
        tier_breakdown = []
        for tier in tiers:
            sold = tier.quantity_sold
            tier_breakdown.append({
                'tier_id': str(tier.id),
                'tier_name': tier.tier_name,
                'price': float(tier.price),
                'quantity_sold': sold,
                'revenue': float(sold * tier.price),
                'is_vip': tier.is_vip,
            })

        # Platform fees
        platform_fee_total = event.platform_fee_collected

        # Check‑in details (list of attendees)
        checked_in_tickets = Ticket.objects.filter(
            event=event,
            checked_in=True
        ).select_related('user', 'ticket_tier')

        attendees = [
            {
                'ticket_code': t.ticket_code,
                'customer_name': t.customer_name,
                'customer_email': t.customer_email,
                'customer_phone': t.customer_phone,
                'tier_name': t.ticket_tier.tier_name if t.ticket_tier else None,
                'checked_in_time': t.checked_in_time,
                'exited': t.exited,
            }
            for t in checked_in_tickets
        ]

        return {
            'event_id': str(event.id),
            'event_name': event.event_name,
            'event_date': event.event_date,
            'event_start_time': event.event_start_time,
            'event_end_time': event.event_end_time,
            'max_capacity': event.max_capacity,
            'total_tickets_sold': total_tickets,
            'checked_in_count': checked_in_count,
            'no_show_count': no_show_count,
            'gross_revenue': float(event.gross_revenue),
            'platform_fee_collected': float(platform_fee_total),
            'net_revenue': float(event.gross_revenue - platform_fee_total),
            'tier_breakdown': tier_breakdown,
            'attendees': attendees,
            'sales_trend': cls._get_sales_trend(event),
        }

    @classmethod
    def _get_sales_trend(cls, event):
        """
        Get daily sales trend for the event (tickets sold per day).
        """
        # Group tickets by purchase date
        tickets = Ticket.objects.filter(event=event)
        trend = tickets.extra(
            {'day': "date_trunc('day', purchase_time)"}
        ).values('day').annotate(
            count=Count('id'),
            revenue=Sum('price')
        ).order_by('day')

        return [
            {
                'date': t['day'].strftime('%Y-%m-%d') if t['day'] else None,
                'tickets_sold': t['count'],
                'revenue': float(t['revenue']) if t['revenue'] else 0,
            }
            for t in trend
        ]

    @classmethod
    def get_platform_report(cls, start_date=None, end_date=None):
        """
        Generate aggregated report across all events in a date range.
        """
        if not start_date:
            start_date = timezone.now().date() - timezone.timedelta(days=30)
        if not end_date:
            end_date = timezone.now().date()

        events = Event.objects.filter(
            event_date__gte=start_date,
            event_date__lte=end_date
        )

        total_events = events.count()
        total_tickets = sum(e.total_tickets_sold for e in events)
        total_checkins = sum(e.checked_in_count for e in events)
        total_revenue = sum(e.gross_revenue for e in events)
        total_fees = sum(e.platform_fee_collected for e in events)

        return {
            'period_start': start_date,
            'period_end': end_date,
            'total_events': total_events,
            'total_tickets_sold': total_tickets,
            'total_checkins': total_checkins,
            'total_gross_revenue': float(total_revenue),
            'total_platform_fees': float(total_fees),
            'total_net_revenue': float(total_revenue - total_fees),
            'event_breakdown': [
                {
                    'event_id': str(e.id),
                    'event_name': e.event_name,
                    'event_date': e.event_date,
                    'tickets_sold': e.total_tickets_sold,
                    'checkins': e.checked_in_count,
                    'revenue': float(e.gross_revenue),
                    'fees': float(e.platform_fee_collected),
                }
                for e in events
            ],
        }
# control/services/metrics_service.py

from django.utils import timezone
from django.db.models import Count, Sum, Q
from decimal import Decimal
from venues.models import Venue
from tables.models import Table
from guest_sessions.models import GuestSession
from payments.models import Transaction
from orders.models import Order
from staff.models import StaffAttendance
from control.models import VenueHealthMetrics, SupportTicket
from explore.models import Booking
import logging

logger = logging.getLogger(__name__)


class MetricsService:
    """Service to compute venue health metrics."""

    @classmethod
    def refresh_all_venues(cls):
        """Refresh metrics for all active venues."""
        venues = Venue.objects.filter(subscription_status__in=['trial', 'active'])
        updated = 0
        now = timezone.now()
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)

        for venue in venues:
            cls.refresh_venue(venue, today_start)
            updated += 1

        logger.info(f"Refreshed metrics for {updated} venues")
        return updated

    @classmethod
    def refresh_venue(cls, venue, today_start=None):
        """Refresh metrics for a single venue."""
        if today_start is None:
            today_start = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0)

        # Active guests
        active_guests = GuestSession.objects.filter(
            venue=venue,
            session_status='active'
        ).count()

        # Tables
        total_tables = Table.objects.filter(venue=venue).count()
        occupied_tables = Table.objects.filter(venue=venue, status='occupied').count()

        # Orders
        pending_orders = Order.objects.filter(
            venue=venue,
            order_status__in=['pending', 'in_progress']
        ).count()

        # Revenue today
        revenue_today = Transaction.objects.filter(
            venue=venue,
            transaction_status='success',
            transaction_time__gte=today_start,
            transaction_type__in=['capture', 'payment', 'deposit']
        ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')

        # Transactions today
        transactions_today = Transaction.objects.filter(
            venue=venue,
            transaction_status='success',
            transaction_time__gte=today_start,
            transaction_type__in=['capture', 'payment', 'deposit']
        ).count()

        # Staff on duty (attendance scan-in without scan-out)
        staff_on_duty = StaffAttendance.objects.filter(
            staff__venue=venue,
            scan_out_time__isnull=True
        ).count()

        # Open support tickets
        open_tickets = SupportTicket.objects.filter(
            venue=venue,
            status__in=['open', 'in_progress']
        ).count()

        # Average turnaround time (minutes between order creation and ready)
        from orders.models import OrderItem
        avg_turnaround = OrderItem.objects.filter(
            order__venue=venue,
            item_status='ready'
        ).exclude(
            created_at__isnull=True,
            updated_at__isnull=True
        ).extra(
            select={'turnaround': 'EXTRACT(EPOCH FROM (updated_at - created_at)) / 60'}
        ).aggregate(avg=Sum('turnaround'))['avg'] or 0

        # Update or create
        metrics, created = VenueHealthMetrics.objects.update_or_create(
            venue=venue,
            defaults={
                'active_guests': active_guests,
                'occupied_tables': occupied_tables,
                'total_tables': total_tables,
                'pending_orders': pending_orders,
                'revenue_today': revenue_today,
                'transactions_today': transactions_today,
                'staff_on_duty': staff_on_duty,
                'open_tickets': open_tickets,
                'avg_turnaround_minutes': int(round(avg_turnaround or 0)),
            }
        )

        return metrics
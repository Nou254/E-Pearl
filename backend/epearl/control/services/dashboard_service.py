# control/services/dashboard_service.py

from django.utils import timezone
from django.db.models import Count, Sum, Q
from decimal import Decimal
from venues.models import Venue
from tables.models import Table
from guest_sessions.models import GuestSession
from payments.models import Transaction
from orders.models import Order
from staff.models import StaffAttendance
from explore.models import Booking


class DashboardService:
    """
    Service to compute manager dashboard KPIs.
    """

    @classmethod
    def get_kpis(cls, venue):
        active_tables = Table.objects.filter(venue=venue, status='occupied').count()
        total_tables = Table.objects.filter(venue=venue).count()

        occupancy = GuestSession.objects.filter(
            venue=venue,
            status='active'
        ).aggregate(total=Sum('table__current_headcount'))['total'] or 0

        today = timezone.now().date()
        gross_revenue = Transaction.objects.filter(
            venue=venue,
            transaction_time__date=today,
            transaction_status='success',
            transaction_type__in=['capture', 'payment', 'deposit']
        ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')

        pending_interventions = Order.objects.filter(
            venue=venue,
            order_status='pending',
        ).count()

        total_bookings = Booking.objects.filter(venue=venue).count()
        bookings_today = Booking.objects.filter(
            venue=venue,
            created_at__date=today
        ).count()

        return {
            'active_tables': active_tables,
            'total_tables': total_tables,
            'occupancy': occupancy,
            'gross_revenue': float(gross_revenue),
            'pending_interventions': pending_interventions,
            'bookings_total': total_bookings,
            'bookings_today': bookings_today,
        }

    @classmethod
    def get_floor_plan(cls, venue):
        tables = Table.objects.filter(venue=venue).select_related('zone', 'assigned_waiter__user')
        result = []
        for table in tables:
            result.append({
                'id': str(table.id),
                'table_number': table.table_number,
                'zone': table.zone.name if table.zone else None,
                'status': table.status,
                'headcount': table.current_headcount,
                'assigned_waiter': {
                    'id': str(table.assigned_waiter.id) if table.assigned_waiter else None,
                    'name': table.assigned_waiter.user.full_name if table.assigned_waiter else None,
                } if table.assigned_waiter else None,
                'is_reserved': table.reservation_status == 'booked',
                'qr_code': str(table.qr_code),
            })
        return result

    @classmethod
    def get_staff_activity_feed(cls, venue, limit=20):
        from control.models import VenueAuditLog
        logs = VenueAuditLog.objects.filter(venue=venue).select_related('staff__user')[:limit]
        return [
            {
                'timestamp': log.timestamp,
                'staff_name': log.staff.user.full_name if log.staff else 'System',
                'action': log.get_action_type_display(),
                'description': log.action_description,
                'amount': float(log.amount) if log.amount else None,
            }
            for log in logs
        ]
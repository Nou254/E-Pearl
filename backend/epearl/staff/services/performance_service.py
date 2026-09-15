# staff/services/performance_service.py

from django.db.models import Count, Sum, Avg
from django.utils import timezone
from datetime import timedelta
from orders.models import Order, OrderItem
from payments.models import Transaction
from staff.models import Staff
from decimal import Decimal


class PerformanceService:
    @classmethod
    def get_waiter_metrics(cls, venue_id, start_date=None, end_date=None):
        """
        Returns aggregated performance data for all waiters in a venue.
        """
        if not start_date:
            start_date = timezone.now() - timedelta(days=30)
        if not end_date:
            end_date = timezone.now()

        # Ensure dates are timezone-aware
        if not timezone.is_aware(start_date):
            start_date = timezone.make_aware(start_date)
        if not timezone.is_aware(end_date):
            end_date = timezone.make_aware(end_date)

        staff = Staff.objects.filter(venue_id=venue_id, role='waiter', is_active=True)

        results = []
        for waiter in staff:
            # Orders taken by this waiter (via assigned tables)
            orders = Order.objects.filter(
                venue_id=venue_id,
                table__assigned_waiter=waiter,
                order_time__gte=start_date,
                order_time__lte=end_date
            )
            total_orders = orders.count()

            # Revenue from these orders
            total_revenue = Transaction.objects.filter(
                venue_id=venue_id,
                transaction_type__in=['capture', 'payment'],
                transaction_status='success',
                order__in=orders
            ).aggregate(total=Sum('amount'))['total'] or Decimal('0')

            # Average turnaround time (from order to ready)
            avg_turnaround = OrderItem.objects.filter(
                order__in=orders,
                item_status='ready'
            ).exclude(
                created_at__isnull=True,
                updated_at__isnull=True
            ).extra(
                select={'turnaround': 'EXTRACT(EPOCH FROM (updated_at - created_at)) / 60'}
            ).aggregate(avg=Avg('turnaround'))['avg'] or 0

            results.append({
                'waiter_id': waiter.id,
                'waiter_name': waiter.user.full_name,
                'total_orders': total_orders,
                'total_revenue': float(total_revenue),
                'avg_turnaround_minutes': round(avg_turnaround, 1),
                'satisfaction': 0,  # placeholder for future feedback
            })

        return results
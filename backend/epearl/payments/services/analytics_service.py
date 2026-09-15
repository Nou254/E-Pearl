# payments/services/analytics_service.py

from django.db.models import Count, Sum, Avg, Q
from django.utils import timezone
from datetime import timedelta
from decimal import Decimal
from ..models import Transaction


class PaymentAnalyticsService:
    @classmethod
    def get_admin_dashboard_stats(cls, start_date=None, end_date=None):
        """
        Returns aggregated stats for admin dashboard.
        """
        if not start_date:
            start_date = timezone.now() - timedelta(days=30)
        if not end_date:
            end_date = timezone.now()

        qs = Transaction.objects.filter(
            transaction_time__gte=start_date,
            transaction_time__lte=end_date
        )

        total_transactions = qs.count()
        successful = qs.filter(transaction_status='success').count()
        failed = qs.filter(transaction_status='failed').count()
        pending = qs.filter(transaction_status='pending').count()

        total_amount = qs.filter(transaction_status='success').aggregate(total=Sum('amount'))['total'] or Decimal('0')

        # Success rate
        success_rate = (successful / total_transactions * 100) if total_transactions > 0 else 0

        # By payment method
        by_method = qs.filter(transaction_status='success').values('payment_method').annotate(
            count=Count('id'),
            total=Sum('amount')
        ).order_by('-total')

        # By venue (top 10)
        by_venue = qs.filter(transaction_status='success').values('venue__business_name').annotate(
            count=Count('id'),
            total=Sum('amount')
        ).order_by('-total')[:10]

        # Daily trend (last 30 days)
        daily_trend = qs.filter(transaction_status='success').extra(
            {'day': "date_trunc('day', transaction_time)"}
        ).values('day').annotate(
            count=Count('id'),
            total=Sum('amount')
        ).order_by('day')

        # Average latency
        avg_latency = qs.filter(gateway_latency_ms__isnull=False).aggregate(avg=Avg('gateway_latency_ms'))['avg'] or 0

        return {
            'total_transactions': total_transactions,
            'successful': successful,
            'failed': failed,
            'pending': pending,
            'success_rate': round(success_rate, 2),
            'total_amount': str(total_amount),
            'by_payment_method': by_method,
            'top_venues': by_venue,
            'daily_trend': daily_trend,
            'avg_latency_ms': round(avg_latency, 2),
        }

    @classmethod
    def get_user_spending(cls, user, start_date=None, end_date=None):
        """
        Returns user's transaction history and aggregated spending.
        """
        if not start_date:
            start_date = timezone.now() - timedelta(days=90)
        if not end_date:
            end_date = timezone.now()

        qs = Transaction.objects.filter(
            user=user,
            transaction_time__gte=start_date,
            transaction_time__lte=end_date,
            transaction_status='success'
        )

        total_spent = qs.aggregate(total=Sum('amount'))['total'] or Decimal('0')
        transaction_count = qs.count()

        # Group by type
        by_type = qs.values('transaction_type').annotate(count=Count('id'), total=Sum('amount'))

        # Recent transactions
        recent = qs.order_by('-transaction_time')[:20]

        return {
            'total_spent': str(total_spent),
            'transaction_count': transaction_count,
            'by_type': by_type,
            'recent_transactions': recent,
        }
# hq/services/analytics_service.py

from django.db.models import Count, Sum, Avg
from django.utils import timezone
from datetime import timedelta
from decimal import Decimal
from venues.models import Venue
from users.models import User
from payments.models import Transaction
from orders.models import Order
from control.models import SupportTicket, HQNotification
from ..models import RequestLog


class AnalyticsService:
    """
    Provides aggregated analytics for the HQ dashboard.
    """

    @classmethod
    def get_platform_overview(cls):
        now = timezone.now()
        month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

        total_venues = Venue.objects.count()
        active_venues = Venue.objects.filter(
            subscription_status__in=['trial', 'active']
        ).count()
        pending_verifications = Venue.objects.filter(
            document_verification_status='pending'
        ).count()

        total_users = User.objects.count()
        active_users = User.objects.filter(is_active=True).count()

        total_revenue = Transaction.objects.filter(
            transaction_status='success'
        ).aggregate(total=Sum('amount'))['total'] or Decimal('0')
        revenue_this_month = Transaction.objects.filter(
            transaction_status='success',
            transaction_time__gte=month_start
        ).aggregate(total=Sum('amount'))['total'] or Decimal('0')

        open_tickets = SupportTicket.objects.filter(
            status__in=['open', 'in_progress']
        ).count()
        unread_notifications = HQNotification.objects.filter(
            is_read=False
        ).count()

        venues_by_tier = {}
        for tier_label, _ in Venue.SUBSCRIPTION_TIERS:
            venues_by_tier[tier_label] = Venue.objects.filter(
                subscription_tier=tier_label
            ).count()

        from control.models import PlatformAuditLog
        recent_logs = PlatformAuditLog.objects.select_related('actor').order_by(
            '-created_at'
        )[:10]

        top_venues = list(
            Transaction.objects.filter(
                transaction_status='success',
                transaction_time__gte=month_start
            ).values('venue__business_name').annotate(
                total=Sum('amount')
            ).order_by('-total')[:5]
        )

        return {
            'total_venues': total_venues,
            'active_venues': active_venues,
            'pending_verifications': pending_verifications,
            'total_users': total_users,
            'active_users': active_users,
            'total_revenue': str(total_revenue),
            'revenue_this_month': str(revenue_this_month),
            'open_tickets': open_tickets,
            'unread_notifications': unread_notifications,
            'venues_by_tier': venues_by_tier,
            'recent_audit_logs': recent_logs,
            'top_venues_by_revenue': top_venues,
        }

    @classmethod
    def get_growth_analytics(cls, days=30):
        end_date = timezone.now().date()
        start_date = end_date - timedelta(days=days)

        venue_creation = Venue.objects.filter(
            created_at__date__gte=start_date,
            created_at__date__lte=end_date
        ).extra(
            {'day': "date_trunc('day', created_at)"}
        ).values('day').annotate(count=Count('id')).order_by('day')

        user_signups = User.objects.filter(
            created_at__date__gte=start_date,
            created_at__date__lte=end_date
        ).extra(
            {'day': "date_trunc('day', created_at)"}
        ).values('day').annotate(count=Count('id')).order_by('day')

        daily_revenue = Transaction.objects.filter(
            transaction_status='success',
            transaction_time__date__gte=start_date,
            transaction_time__date__lte=end_date
        ).extra(
            {'day': "date_trunc('day', transaction_time)"}
        ).values('day').annotate(
            total=Sum('amount'),
            count=Count('id')
        ).order_by('day')

        return {
            'venue_creation': venue_creation,
            'user_signups': user_signups,
            'daily_revenue': daily_revenue,
            'period_start': start_date,
            'period_end': end_date,
        }

    @classmethod
    def get_financial_analytics(cls, start_date=None, end_date=None):
        if not start_date:
            start_date = timezone.now().date() - timedelta(days=30)
        if not end_date:
            end_date = timezone.now().date()

        qs = Transaction.objects.filter(
            transaction_status='success',
            transaction_time__date__gte=start_date,
            transaction_time__date__lte=end_date
        )

        total_revenue = qs.aggregate(total=Sum('amount'))['total'] or Decimal('0')
        total_transactions = qs.count()

        by_method = qs.values('payment_method').annotate(
            count=Count('id'),
            total=Sum('amount')
        ).order_by('-total')

        by_type = qs.values('transaction_type').annotate(
            count=Count('id'),
            total=Sum('amount')
        ).order_by('-total')

        by_venue = qs.values('venue__business_name').annotate(
            count=Count('id'),
            total=Sum('amount')
        ).order_by('-total')[:10]

        return {
            'total_revenue': str(total_revenue),
            'total_transactions': total_transactions,
            'by_payment_method': by_method,
            'by_transaction_type': by_type,
            'top_venues': by_venue,
            'period_start': start_date,
            'period_end': end_date,
        }

    @classmethod
    def get_request_log_analytics(cls, days=7):
        end_date = timezone.now()
        start_date = end_date - timedelta(days=days)

        total = RequestLog.objects.filter(
            timestamp__gte=start_date,
            timestamp__lte=end_date,
            is_deleted=False
        ).count()

        by_status = RequestLog.objects.filter(
            timestamp__gte=start_date,
            timestamp__lte=end_date,
            is_deleted=False
        ).values('status_code').annotate(count=Count('id')).order_by('-count')

        avg_response = RequestLog.objects.filter(
            timestamp__gte=start_date,
            timestamp__lte=end_date,
            is_deleted=False
        ).aggregate(avg=Avg('response_time_ms'))['avg'] or 0

        top_endpoints = RequestLog.objects.filter(
            timestamp__gte=start_date,
            timestamp__lte=end_date,
            is_deleted=False
        ).values('endpoint').annotate(count=Count('id')).order_by('-count')[:10]

        deleted_count = RequestLog.objects.filter(
            timestamp__gte=start_date,
            timestamp__lte=end_date,
            is_deleted=True,
            deleted_at__isnull=False
        ).count()

        return {
            'total_requests': total,
            'by_status_code': by_status,
            'avg_response_time_ms': round(avg_response, 2),
            'top_endpoints': top_endpoints,
            'soft_deleted_count': deleted_count,
            'period_start': start_date,
            'period_end': end_date,
        }
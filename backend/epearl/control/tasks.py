# control/tasks.py

from celery import shared_task
from django.core.cache import cache
from .services.inventory_service import InventoryService
from notifications.tasks import send_low_stock_notification
import logging

logger = logging.getLogger(__name__)


@shared_task
def check_low_stock():
    """
    Scheduled task to scan for low‑stock items and send alerts.
    Runs every hour by default.
    """
    low_stock_items = InventoryService.get_low_stock_items()
    if low_stock_items:
        # Group by venue to send one notification per venue
        from django.db.models import Count
        venues = low_stock_items.values('venue_id').annotate(count=Count('id'))
        for v in venues:
            venue_id = v['venue_id']
            items = low_stock_items.filter(venue_id=venue_id)
            # Avoid duplicate alerts: cache last sent time for this venue
            cache_key = f"low_stock_alert_{venue_id}"
            last_sent = cache.get(cache_key)
            if not last_sent:
                # Send notification
                send_low_stock_notification.delay(venue_id, list(items.values_list('id', flat=True)))
                cache.set(cache_key, True, timeout=3600)  # don't send again for 1 hour
    logger.info(f"Low‑stock check completed. Found {low_stock_items.count()} items.")


@shared_task
def auto_disable_out_of_stock_items():
    """
    Disable any items that have reached zero stock.
    """
    from .models import MenuItem
    items = MenuItem.objects.filter(stock_count=0, is_available=True)
    count = 0
    for item in items:
        item.is_available = False
        item.save(update_fields=['is_available'])
        count += 1
    logger.info(f"Auto-disabled {count} out‑of‑stock items.")
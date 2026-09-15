# control/services/inventory_service.py

from django.db import models  # <-- ADDED
from django.db import transaction
from django.core.exceptions import ValidationError
from ..models import MenuItem
import logging

logger = logging.getLogger(__name__)


class InventoryService:
    @classmethod
    def deplete_stock(cls, item_id, quantity=1):
        try:
            item = MenuItem.objects.select_for_update().get(id=item_id)
        except MenuItem.DoesNotExist:
            raise ValidationError("Menu item not found")

        if item.stock_count < quantity:
            raise ValidationError(f"Insufficient stock for {item.name}. Available: {item.stock_count}")

        item.stock_count -= quantity
        item.save(update_fields=['stock_count'])

        logger.info(f"Depleted {quantity} of {item.name} (new stock: {item.stock_count})")
        return item

    @classmethod
    def restore_stock(cls, item_id, quantity=1):
        item = MenuItem.objects.get(id=item_id)
        item.stock_count += quantity
        item.save(update_fields=['stock_count'])
        logger.info(f"Restored {quantity} of {item.name} (new stock: {item.stock_count})")
        return item

    @classmethod
    def get_low_stock_items(cls, venue_id=None):
        qs = MenuItem.objects.filter(is_active=True)
        if venue_id:
            qs = qs.filter(venue_id=venue_id)
        return qs.filter(stock_count__lte=models.F('low_stock_threshold'))

    @classmethod
    def check_and_auto_disable(cls, item):
        if item.stock_count <= 0 and item.is_available:
            item.is_available = False
            item.save(update_fields=['is_available'])
            logger.warning(f"Auto-disabled {item.name} due to zero stock")
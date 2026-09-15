# orders/services/order_service.py

from decimal import Decimal
from django.db import transaction
from django.core.exceptions import ValidationError
from django.utils import timezone
from ..models import Order, OrderItem, MenuItem
from notifications.services.notification_service import NotificationService


class OrderService:
    @staticmethod
    @transaction.atomic
    def create_order(guest_session, table=None, items_data=None):
        venue = guest_session.venue
        if not venue.is_active():
            raise ValidationError("Venue is not active.")

        order = Order.objects.create(
            venue=venue,
            guest_session=guest_session,
            table=table,
            order_status='pending'
        )

        if items_data:
            for item_data in items_data:
                menu_item_id = item_data.get('menu_item_id')
                quantity = item_data.get('quantity', 1)
                modifiers = item_data.get('modifiers', [])

                try:
                    menu_item = MenuItem.objects.get(
                        id=menu_item_id,
                        venue=venue,
                        is_active=True,
                        is_available=True
                    )
                except MenuItem.DoesNotExist:
                    raise ValidationError(f"Menu item {menu_item_id} not available.")

                OrderItem.objects.create(
                    order=order,
                    venue=venue,
                    menu_item=menu_item,
                    item_name=menu_item.item_name,
                    item_type=menu_item.item_type,
                    quantity=quantity,
                    unit_price=menu_item.price,
                    total_price=menu_item.price * quantity,
                    modifiers=modifiers,
                    item_status='pending'
                )

            order.calculate_total()

        if guest_session and guest_session.user:
            NotificationService.send_order_placed_guest(order, guest_session.user)

        return order

    @staticmethod
    @transaction.atomic
    def add_item_to_order(order, menu_item_id, quantity=1, modifiers=None):
        try:
            menu_item = MenuItem.objects.get(
                id=menu_item_id,
                venue=order.venue,
                is_active=True,
                is_available=True
            )
        except MenuItem.DoesNotExist:
            raise ValidationError("Menu item not available.")

        order_item = OrderItem.objects.create(
            order=order,
            venue=order.venue,
            menu_item=menu_item,
            item_name=menu_item.item_name,
            item_type=menu_item.item_type,
            quantity=quantity,
            unit_price=menu_item.price,
            total_price=menu_item.price * quantity,
            modifiers=modifiers or [],
            item_status='pending'
        )

        order.calculate_total()
        return order_item

    @staticmethod
    @transaction.atomic
    def update_item_status(order_item, status):
        if status not in ['pending', 'preparing', 'ready', 'served', 'cancelled']:
            raise ValidationError("Invalid status.")

        order_item.item_status = status
        order_item.save()

        order = order_item.order
        all_served = all(
            item.item_status in ['served', 'cancelled']
            for item in order.items.all()
        )
        if all_served and order.order_status != 'served':
            order.order_status = 'served'
            order.served_time = timezone.now()
            order.save()

        return order_item

    @staticmethod
    @transaction.atomic
    def cancel_order(order):
        if order.order_status in ['served', 'cancelled']:
            raise ValidationError("Order cannot be cancelled.")

        order.order_status = 'cancelled'
        for item in order.items.all():
            if item.item_status not in ['served', 'cancelled']:
                item.item_status = 'cancelled'
                item.save()
        order.save()

        if order.guest_session and order.guest_session.user:
            NotificationService.send_order_cancelled(order, order.guest_session.user)

        return order

    @staticmethod
    @transaction.atomic
    def mark_ready(order_item, ready_time=None):
        if order_item.item_status in ['ready', 'served', 'cancelled']:
            raise ValidationError("Item cannot be marked ready.")

        order_item.item_status = 'ready'
        order_item.save()

        order = order_item.order
        all_ready = all(
            item.item_status in ['ready', 'served', 'cancelled']
            for item in order.items.all()
        )
        if all_ready and order.order_status not in ['served', 'cancelled']:
            order.order_status = 'ready'
            order.ready_time = ready_time or timezone.now()
            order.save()

        return order_item

    @staticmethod
    @transaction.atomic
    def fire_item(order_item, priority_increment=10):
        if order_item.item_status in ['served', 'cancelled']:
            raise ValidationError("Cannot change priority of served/cancelled item.")
        order_item.priority += priority_increment
        order_item.save(update_fields=['priority'])
        return order_item

    @staticmethod
    @transaction.atomic
    def hold_item(order_item, priority_decrement=10):
        if order_item.item_status in ['served', 'cancelled']:
            raise ValidationError("Cannot change priority of served/cancelled item.")
        order_item.priority = max(0, order_item.priority - priority_decrement)
        order_item.save(update_fields=['priority'])
        return order_item

    # NEW: Reassign item from host to a specific guest (self‑pay)
    @staticmethod
    @transaction.atomic
    def reassign_item_to_guest(order_item, target_guest_session):
        """
        Reassign an order item from the host's order to a specific guest's self‑pay order.
        The item is moved from the current order to a new order under the target guest session.
        If the guest doesn't have an order, a new pending order is created.
        """
        if order_item.item_status in ['served', 'cancelled']:
            raise ValidationError("Cannot reassign a served or cancelled item.")

        # The current order's guest session is the host (or the one who placed it)
        host_order = order_item.order
        host_session = host_order.guest_session

        # Ensure the target guest is not the same as the host
        if target_guest_session == host_session:
            raise ValidationError("Cannot reassign to the same guest (host).")

        # Ensure the target guest belongs to the same venue
        if target_guest_session.venue != host_session.venue:
            raise ValidationError("Guest session does not belong to the same venue.")

        # Check if the target guest already has an order (pending)
        target_order = Order.objects.filter(
            guest_session=target_guest_session,
            order_status__in=['pending', 'in_progress']
        ).first()

        if not target_order:
            # Create a new order for the guest
            target_order = Order.objects.create(
                venue=host_session.venue,
                guest_session=target_guest_session,
                table=host_order.table,  # same table as host
                order_status='pending'
            )

        # Copy item details and create a new OrderItem under the target order
        new_item = OrderItem.objects.create(
            order=target_order,
            venue=host_session.venue,
            menu_item=order_item.menu_item,
            item_name=order_item.item_name,
            item_type=order_item.item_type,
            quantity=order_item.quantity,
            unit_price=order_item.unit_price,
            total_price=order_item.total_price,
            modifiers=order_item.modifiers,
            item_status='pending',
            guest=target_guest_session,
            priority=order_item.priority,
            reassigned_from_host=True  # mark as reassigned
        )

        # Remove the item from the host's order (mark as cancelled or delete)
        order_item.item_status = 'cancelled'
        order_item.save(update_fields=['item_status'])

        # Recalculate totals for both orders
        host_order.calculate_total()
        target_order.calculate_total()

        # Notify the guest (if user exists) about the reassignment
        if target_guest_session.user:
            NotificationService.send_templated_notification(
                template_name='item_reassigned_to_guest',
                context_data={
                    'item_name': new_item.item_name,
                    'quantity': new_item.quantity,
                    'total_price': new_item.total_price,
                    'order_id': str(target_order.id),
                },
                recipient_user=target_guest_session.user,
                venue=host_session.venue,
                notification_type='item_reassigned',
                channel='email'
            )

        return new_item
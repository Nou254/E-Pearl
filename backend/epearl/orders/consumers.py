# orders/consumers.py

import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth.models import AnonymousUser
from users.models import User
from orders.models import OrderItem


class OrderPriorityConsumer(AsyncWebsocketConsumer):
    """
    WebSocket consumer for real‑time priority updates.
    Broadcasts priority changes to kitchen/bar displays.
    """
    async def connect(self):
        self.venue_id = self.scope['url_route']['kwargs']['venue_id']
        self.room_group_name = f'order_priority_{self.venue_id}'

        # Check authentication (allow only staff with permission)
        user = self.scope.get('user', AnonymousUser())
        if user.is_anonymous:
            await self.close()
            return

        # Check if user belongs to this venue and has appropriate role
        if user.venue_id != int(self.venue_id):
            await self.close()
            return

        if user.user_type not in ['admin', 'manager', 'owner', 'chef', 'bartender']:
            await self.close()
            return

        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )

    async def receive(self, text_data):
        # Client might send requests, but we mainly broadcast
        data = json.loads(text_data)
        if data.get('type') == 'get_initial_priorities':
            # Send current priority list for all pending items
            items = await self.get_pending_items()
            await self.send(text_data=json.dumps({
                'type': 'initial_priorities',
                'items': items
            }))

    @database_sync_to_async
    def get_pending_items(self):
        from orders.models import OrderItem
        items = OrderItem.objects.filter(
            order__venue_id=self.venue_id,
            item_status__in=['pending', 'preparing', 'ready']
        ).values(
            'id', 'item_name', 'quantity', 'item_status',
            'priority', 'order__table__table_number'
        )
        return list(items)

    # Called when a priority update is broadcast
    async def priority_update(self, event):
        await self.send(text_data=json.dumps({
            'type': 'priority_update',
            'item_id': event['item_id'],
            'priority': event['priority'],
            'action': event['action'],
        }))
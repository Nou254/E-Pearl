# control/consumers.py

import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth.models import AnonymousUser
from users.models import User
from tables.models import Table


class FloorPlanConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.venue_id = self.scope['url_route']['kwargs']['venue_id']
        self.room_group_name = f'floor_plan_{self.venue_id}'

        # Check authentication
        user = self.scope.get('user', AnonymousUser())
        if user.is_anonymous:
            await self.close()
            return

        # Check if user belongs to this venue
        if user.venue_id != int(self.venue_id):
            await self.close()
            return

        # Join group
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
        # Client can send messages (e.g., request initial state)
        data = json.loads(text_data)
        if data.get('type') == 'get_initial':
            tables = await self.get_tables()
            await self.send(text_data=json.dumps({
                'type': 'initial_state',
                'tables': tables
            }))

    @database_sync_to_async
    def get_tables(self):
        from tables.models import Table
        tables = Table.objects.filter(venue_id=self.venue_id).values(
            'id', 'table_number', 'status', 'current_headcount', 'zone',
            'assigned_waiter__user__full_name'
        )
        return list(tables)

    # Called when a table status changes (from other parts of the system)
    async def table_update(self, event):
        await self.send(text_data=json.dumps({
            'type': 'table_update',
            'table': event['table']
        }))
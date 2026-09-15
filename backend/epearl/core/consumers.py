# core/consumers.py

import json
import logging
from channels.generic.websocket import AsyncJsonWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth.models import AnonymousUser
from rest_framework_simplejwt.tokens import AccessToken
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError
from users.models import User
from staff.models import Staff
from venues.models import Venue

logger = logging.getLogger(__name__)


class EpearlConsumer(AsyncJsonWebsocketConsumer):
    """
    Generic WebSocket consumer for E-Pearl real-time updates.
    Authenticates via JWT token passed in query string: ?token=...
    """

    async def connect(self):
        self.user = None
        self.venue_id = None
        self.groups_to_join = []

        # Extract token from query string
        query_string = self.scope['query_string'].decode()
        token = None
        for param in query_string.split('&'):
            if param.startswith('token='):
                token = param.split('=')[1]
                break

        if token:
            try:
                access_token = AccessToken(token)
                user_id = access_token['user_id']
                self.user = await self.get_user(user_id)
            except (InvalidToken, TokenError, KeyError):
                logger.warning("Invalid WebSocket token")
                await self.close(code=4001)
                return
        else:
            await self.close(code=4000)  # missing token
            return

        if not self.user or not self.user.is_authenticated:
            await self.close(code=4002)
            return

        # Determine groups based on user role and venue
        if self.user.venue:
            self.venue_id = str(self.user.venue.id)
            self.groups_to_join.append(f"venue_{self.venue_id}")

            # Role-specific groups
            if self.user.user_type in ['manager', 'owner']:
                self.groups_to_join.append(f"control_{self.venue_id}")
            elif self.user.user_type == 'staff':
                staff = await self.get_staff_profile(self.user)
                if staff:
                    if staff.role in ['chef', 'cook']:
                        self.groups_to_join.append(f"kitchen_{self.venue_id}")
                    elif staff.role in ['bartender']:
                        self.groups_to_join.append(f"bar_{self.venue_id}")
                    elif staff.role in ['waiter']:
                        self.groups_to_join.append(f"waiter_{self.user.id}")
                    # Security/gate
                    if staff.role in ['security']:
                        self.groups_to_join.append(f"gate_{self.venue_id}")
                # Always add staff group for personal notifications
                self.groups_to_join.append(f"staff_{self.user.id}")
        else:
            # Users without venue (e.g., HQ admins) could join admin group
            if self.user.user_type in ['admin', 'support']:
                self.groups_to_join.append("admin")

        # Accept connection and join groups
        await self.accept()
        for group in self.groups_to_join:
            await self.channel_layer.group_add(group, self.channel_name)
        logger.info(f"WebSocket connected: user={self.user.id}, groups={self.groups_to_join}")

    async def disconnect(self, close_code):
        # Leave all groups
        for group in self.groups_to_join:
            await self.channel_layer.group_discard(group, self.channel_name)
        logger.info(f"WebSocket disconnected: user={self.user.id if self.user else 'unknown'}")

    async def receive_json(self, content):
        """
        Handle incoming JSON messages from client.
        """
        # For now, we only handle acknowledgements or simple pings
        if content.get('type') == 'ping':
            await self.send_json({'type': 'pong'})
        else:
            # Echo back or just log
            logger.debug(f"Received WebSocket message: {content}")

    # -------------------------------------------------------------------------
    # Helper methods to send messages to this connection
    # -------------------------------------------------------------------------

    async def send_notification(self, event):
        """Send a notification to the client."""
        await self.send_json(event['data'])

    # -------------------------------------------------------------------------
    # Database helpers
    # -------------------------------------------------------------------------

    @database_sync_to_async
    def get_user(self, user_id):
        try:
            return User.objects.get(id=user_id)
        except User.DoesNotExist:
            return None

    @database_sync_to_async
    def get_staff_profile(self, user):
        try:
            return Staff.objects.get(user=user)
        except Staff.DoesNotExist:
            return None
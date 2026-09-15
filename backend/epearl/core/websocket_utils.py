# core/websocket_utils.py

from django.utils import timezone
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
import json

channel_layer = get_channel_layer()


def send_to_group(group_name, message_data):
    """
    Send a message to all clients in a group.
    """
    async_to_sync(channel_layer.group_send)(
        group_name,
        {
            'type': 'send_notification',
            'data': message_data
        }
    )


def notify_control(venue_id, event_type, payload):
    """
    Send notification to E-Pearl Control dashboard.
    """
    send_to_group(
        f"control_{venue_id}",
        {
            'type': event_type,
            'timestamp': str(timezone.now()),
            'payload': payload
        }
    )


def notify_waiter(waiter_user_id, event_type, payload):
    """
    Send notification to a specific waiter.
    """
    send_to_group(
        f"waiter_{waiter_user_id}",
        {
            'type': event_type,
            'timestamp': str(timezone.now()),
            'payload': payload
        }
    )


def notify_staff(staff_user_id, event_type, payload):
    """
    Send notification to a specific staff member.
    """
    send_to_group(
        f"staff_{staff_user_id}",
        {
            'type': event_type,
            'timestamp': str(timezone.now()),
            'payload': payload
        }
    )


def notify_venue(venue_id, event_type, payload):
    """
    Broadcast to all staff/managers in a venue.
    """
    send_to_group(
        f"venue_{venue_id}",
        {
            'type': event_type,
            'timestamp': str(timezone.now()),
            'payload': payload
        }
    )


def notify_kitchen(venue_id, event_type, payload):
    """
    Send notification to kitchen display.
    """
    send_to_group(
        f"kitchen_{venue_id}",
        {
            'type': event_type,
            'timestamp': str(timezone.now()),
            'payload': payload
        }
    )


def notify_bar(venue_id, event_type, payload):
    """
    Send notification to bar display.
    """
    send_to_group(
        f"bar_{venue_id}",
        {
            'type': event_type,
            'timestamp': str(timezone.now()),
            'payload': payload
        }
    )


def notify_gate(venue_id, event_type, payload):
    """
    Send notification to security gate.
    """
    send_to_group(
        f"gate_{venue_id}",
        {
            'type': event_type,
            'timestamp': str(timezone.now()),
            'payload': payload
        }
    )
# control/routing.py

from django.urls import re_path
from . import consumers

websocket_urlpatterns = [
    re_path(r'ws/floor-plan/(?P<venue_id>\w+)/$', consumers.FloorPlanConsumer.as_asgi()),
]
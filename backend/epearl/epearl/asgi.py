# epearl/asgi.py

import os
from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack
from django.urls import path, include

# Set default settings module
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'epearl.settings')

# Import WebSocket routing from apps
from core.consumers import EpearlConsumer
from orders.routing import websocket_urlpatterns as order_websocket_urlpatterns
from control.routing import websocket_urlpatterns as control_websocket_urlpatterns

# Combine all WebSocket URL patterns
websocket_urlpatterns = [
    path("ws/", EpearlConsumer.as_asgi()),  # fallback / general consumer
] + order_websocket_urlpatterns + control_websocket_urlpatterns

application = ProtocolTypeRouter({
    "http": get_asgi_application(),
    "websocket": AuthMiddlewareStack(
        URLRouter(websocket_urlpatterns)
    ),
})
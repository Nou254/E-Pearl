# guest_sessions/apps.py

from django.apps import AppConfig

class GuestSessionsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'guest_sessions'
    verbose_name = 'Guest Sessions'
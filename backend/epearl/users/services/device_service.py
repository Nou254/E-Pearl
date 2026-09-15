# users/services/device_service.py

from django.core.cache import cache
from users.models import User


class DeviceService:
    @staticmethod
    def get_device_key(user_id):
        return f"device:{user_id}"

    @staticmethod
    def store_device(user, fingerprint):
        user.device_fingerprint = fingerprint
        user.is_device_trusted = True
        user.save(update_fields=['device_fingerprint', 'is_device_trusted'])

    @staticmethod
    def is_device_trusted(user, fingerprint):
        return user.device_fingerprint == fingerprint

    @staticmethod
    def revoke_device(user):
        user.device_fingerprint = None
        user.is_device_trusted = False
        user.save(update_fields=['device_fingerprint', 'is_device_trusted'])
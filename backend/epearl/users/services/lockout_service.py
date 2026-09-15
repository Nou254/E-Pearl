# users/services/lockout_service.py

from django.core.cache import cache
from django.conf import settings
import time

class LockoutService:
    MAX_ATTEMPTS = 5
    LOCKOUT_DURATION = 900  # 15 minutes

    @staticmethod
    def get_attempts_key(identifier):
        return f"login_attempts:{identifier}"

    @staticmethod
    def increment_attempts(identifier):
        key = LockoutService.get_attempts_key(identifier)
        attempts = cache.get(key, 0)
        attempts += 1
        cache.set(key, attempts, timeout=LockoutService.LOCKOUT_DURATION)
        return attempts

    @staticmethod
    def reset_attempts(identifier):
        key = LockoutService.get_attempts_key(identifier)
        cache.delete(key)

    @staticmethod
    def is_locked(identifier):
        key = LockoutService.get_attempts_key(identifier)
        attempts = cache.get(key, 0)
        return attempts >= LockoutService.MAX_ATTEMPTS

    @staticmethod
    def get_lockout_remaining(identifier):
        key = LockoutService.get_attempts_key(identifier)
        ttl = cache.ttl(key)
        if ttl is None:
            return 0
        return ttl
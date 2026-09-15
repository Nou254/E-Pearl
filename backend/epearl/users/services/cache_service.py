from django.core.cache import cache
from django.conf import settings
import json
import secrets
from django.utils import timezone


class CacheService:
    """Handles all Redis caching operations for authentication."""

    @staticmethod
    def get_cache_key(prefix, identifier):
        return f"{prefix}:{identifier}"

    # --- OTP Management ---
    @staticmethod
    def store_otp(identifier, otp_code, otp_type, ttl=300):
        """Store OTP in Redis with TTL (default 5 minutes)."""
        key = f"otp:{otp_type}:{identifier}"
        cache.set(key, otp_code, timeout=ttl)
        return True

    @staticmethod
    def verify_otp(identifier, otp_code, otp_type):
        """Verify OTP and delete if valid."""
        key = f"otp:{otp_type}:{identifier}"
        stored = cache.get(key)
        if stored and stored == otp_code:
            cache.delete(key)
            return True
        return False

    @staticmethod
    def delete_otp(identifier, otp_type):
        key = f"otp:{otp_type}:{identifier}"
        cache.delete(key)

    # --- Admin Login Tokens ---
    @staticmethod
    def generate_admin_token(user_id):
        """Generate a secure token and store it in Redis with expiry."""
        token = secrets.token_hex(32)
        key = f"admin_token:{token}"
        expiry = settings.ADMIN_LOGIN_TOKEN_EXPIRY  # 1200 seconds (20 mins)
        payload = {
            'user_id': user_id,
            'created_at': timezone.now().isoformat(),
            'is_used': False
        }
        cache.set(key, json.dumps(payload), timeout=expiry)
        return token

    @staticmethod
    def validate_admin_token(token):
        """Validate admin login token."""
        key = f"admin_token:{token}"
        data = cache.get(key)
        if not data:
            return None
        payload = json.loads(data)
        if payload.get('is_used'):
            cache.delete(key)
            return None
        return payload

    @staticmethod
    def mark_admin_token_used(token):
        """Mark admin token as used."""
        key = f"admin_token:{token}"
        data = cache.get(key)
        if data:
            payload = json.loads(data)
            payload['is_used'] = True
            cache.set(key, json.dumps(payload), timeout=60)

    # --- Login Attempts (Rate Limiting) ---
    @staticmethod
    def get_login_attempts(identifier):
        key = f"login_attempts:{identifier}"
        attempts = cache.get(key)
        return int(attempts) if attempts else 0

    @staticmethod
    def increment_login_attempts(identifier, ttl=900):
        key = f"login_attempts:{identifier}"
        attempts = cache.get(key)
        if attempts is None:
            attempts = 1
        else:
            attempts = int(attempts) + 1
        cache.set(key, attempts, timeout=ttl)
        return attempts

    @staticmethod
    def reset_login_attempts(identifier):
        key = f"login_attempts:{identifier}"
        cache.delete(key)

    @staticmethod
    def is_account_locked(identifier):
        attempts = CacheService.get_login_attempts(identifier)
        return attempts >= 5

    # --- User Session ---
    @staticmethod
    def set_user_session(user_id, user_data, ttl=None):
        if ttl is None:
            ttl = settings.USER_SESSION_TIMEOUT  # 8 hours
        key = f"user_session:{user_id}"
        cache.set(key, json.dumps(user_data), timeout=ttl)

    @staticmethod
    def get_user_session(user_id):
        key = f"user_session:{user_id}"
        data = cache.get(key)
        if data:
            return json.loads(data)
        return None

    @staticmethod
    def invalidate_user_session(user_id):
        key = f"user_session:{user_id}"
        cache.delete(key)

    # --- Device Binding ---
    @staticmethod
    def store_device_fingerprint(user_id, fingerprint, ttl=None):
        if ttl is None:
            ttl = settings.USER_SESSION_TIMEOUT
        key = f"device:{user_id}"
        cache.set(key, fingerprint, timeout=ttl)

    @staticmethod
    def get_device_fingerprint(user_id):
        key = f"device:{user_id}"
        return cache.get(key)

    @staticmethod
    def is_device_trusted(user_id, fingerprint):
        stored = CacheService.get_device_fingerprint(user_id)
        return stored == fingerprint

    # --- Staff PIN Reset Token ---
    @staticmethod
    def generate_pin_reset_token(user_id):
        token = secrets.token_hex(16)
        key = f"pin_reset:{token}"
        cache.set(key, user_id, timeout=600)  # 10 minutes
        return token

    @staticmethod
    def validate_pin_reset_token(token):
        key = f"pin_reset:{token}"
        user_id = cache.get(key)
        if user_id:
            cache.delete(key)
            return user_id
        return None
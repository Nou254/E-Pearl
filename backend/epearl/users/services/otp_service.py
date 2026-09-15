# users/services/otp_service.py

import random
from django.core.cache import cache
from django.utils import timezone
import datetime


class OTPService:
    OTP_TYPES = ['login', 'registration', 'password_reset', '2fa', 'email_verification', 'device_verification']
    OTP_LENGTH = 6
    OTP_EXPIRY = 300  # seconds

    @staticmethod
    def generate_otp(identifier, otp_type):
        """Generate OTP and store in Redis"""
        if otp_type not in OTPService.OTP_TYPES:
            raise ValueError(f"Invalid OTP type. Allowed: {OTPService.OTP_TYPES}")

        otp = ''.join([str(random.randint(0, 9)) for _ in range(OTPService.OTP_LENGTH)])
        key = f"otp:{otp_type}:{identifier}"
        cache.set(key, otp, timeout=OTPService.OTP_EXPIRY)
        return otp

    @staticmethod
    def verify_otp(identifier, otp_code, otp_type):
        key = f"otp:{otp_type}:{identifier}"
        stored = cache.get(key)
        if stored and stored == otp_code:
            cache.delete(key)
            return True
        return False

    @staticmethod
    def send_otp(identifier, otp_code, otp_type, delivery_method='sms'):
        """Send OTP via SMS or email"""
        from users.services.notification_service import NotificationService
        if delivery_method == 'sms':
            NotificationService.send_sms(identifier, f"Your {otp_type} OTP is: {otp_code}")
        elif delivery_method == 'email':
            NotificationService.send_email(identifier, f"Your {otp_type} OTP", f"Your OTP is: {otp_code}")
        else:
            raise ValueError("Invalid delivery method")
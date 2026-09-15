# users/services/twofa_service.py

import pyotp
import qrcode
from io import BytesIO
import base64
from django.conf import settings
from users.models import User


class TwoFAService:
    @staticmethod
    def generate_secret(user):
        """Generate TOTP secret for a user"""
        secret = pyotp.random_base32()
        return secret

    @staticmethod
    def get_qr_code(user, secret):
        """Generate QR code URI for authenticator app"""
        issuer = settings.APP_NAME or 'E-Pearl'
        label = user.email or user.phone or str(user.id)
        totp = pyotp.TOTP(secret)
        provisioning_uri = totp.provisioning_uri(name=label, issuer_name=issuer)
        # Generate QR code image
        qr = qrcode.make(provisioning_uri)
        buffer = BytesIO()
        qr.save(buffer, format='PNG')
        b64 = base64.b64encode(buffer.getvalue()).decode()
        return f"data:image/png;base64,{b64}"

    @staticmethod
    def verify_code(secret, code):
        """Verify TOTP code"""
        totp = pyotp.TOTP(secret)
        return totp.verify(code)

    @staticmethod
    def generate_recovery_codes(user, count=10):
        """Generate and store recovery codes"""
        import secrets
        codes = []
        for _ in range(count):
            code = secrets.token_hex(4).upper()
            codes.append(code)
        # Store encrypted in DB or Redis
        key = f"recovery_codes:{user.id}"
        from django.core.cache import cache
        cache.set(key, codes, timeout=None)
        return codes
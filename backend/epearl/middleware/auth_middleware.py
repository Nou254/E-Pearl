# middleware/auth_middleware.py

from django.http import JsonResponse
from django.contrib.auth.models import AnonymousUser  # ✅ Added missing import
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError
import jwt
from django.conf import settings


class AuthMiddleware:
    """
    Middleware to validate JWT token for all requests except public endpoints.
    Adds user object to request if token is valid.
    """
    def __init__(self, get_response):
        self.get_response = get_response
        self.jwt_authenticator = JWTAuthentication()

    def __call__(self, request):
        # Skip authentication for public endpoints
        public_paths = [
            '/api/auth/',
            '/admin/',
            '/api/auth/register_customer/',
            '/api/auth/staff_login/',
            '/api/auth/manager_login/',
            '/api/auth/admin_login_request/',
            '/api/auth/admin_login_confirm/',
            '/api/auth/request_otp/',
            '/api/auth/verify_otp/',
            '/api/auth/password_reset_request/',
            '/api/auth/password_reset_confirm/',
            '/api/auth/staff_set_pin/',
            '/api/auth/staff_change_pin/',
            '/api/auth/staff_reset_pin_request/',
            '/api/auth/staff_reset_pin_confirm/',
            '/api/auth/refresh_token/',
        ]

        if any(request.path.startswith(path) for path in public_paths):
            return self.get_response(request)

        # Try to authenticate with JWT
        try:
            auth_header = request.headers.get('Authorization')
            if auth_header and auth_header.startswith('Bearer '):
                token = auth_header.split(' ')[1]
                validated_token = self.jwt_authenticator.get_validated_token(token)
                user = self.jwt_authenticator.get_user(validated_token)
                request.user = user
            else:
                # No token, set AnonymousUser
                request.user = AnonymousUser()
        except (InvalidToken, TokenError, jwt.ExpiredSignatureError):
            # Invalid token, but we allow the request to continue; the view will handle 401 if needed
            request.user = AnonymousUser()

        response = self.get_response(request)
        return response
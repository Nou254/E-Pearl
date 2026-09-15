from django.http import JsonResponse
from django.utils.deprecation import MiddlewareMixin
from users.services.cache_service import CacheService
import json


class RedisSessionMiddleware(MiddlewareMixin):
    """
    Middleware to validate and attach Redis session data to the request.
    Also handles session expiry and invalidation.
    """
    def process_request(self, request):
        # Skip for public endpoints and admin
        if any(request.path.startswith(p) for p in [
            '/api/auth/', '/admin/',
            '/api/auth/register_customer/', '/api/auth/staff_login/',
            '/api/auth/manager_login/', '/api/auth/admin_login_request/',
            '/api/auth/admin_login_confirm/', '/api/auth/request_otp/',
            '/api/auth/verify_otp/', '/api/auth/password_reset_request/',
            '/api/auth/password_reset_confirm/', '/api/auth/staff_set_pin/',
            '/api/auth/staff_change_pin/', '/api/auth/staff_reset_pin_request/',
            '/api/auth/staff_reset_pin_confirm/', '/api/auth/refresh_token/',
        ]):
            return None

        if request.user and request.user.is_authenticated:
            user_id = str(request.user.id)
            user_data = CacheService.get_user_session(user_id)

            if user_data:
                # Attach to request for quick access
                request.user_data = user_data
            else:
                # Session expired; we might force logout
                # But we allow the request to proceed; views will handle 401 if needed
                pass
        return None
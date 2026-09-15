# middleware/timezone_middleware.py

from django.utils import timezone
from django.utils.deprecation import MiddlewareMixin
from users.services.timezone_service import TimezoneService
import pytz


class TimezoneMiddleware(MiddlewareMixin):
    """
    Middleware to set the active timezone based on the user's preference.
    """
    def process_request(self, request):
        if request.user and request.user.is_authenticated and request.user.timezone:
            try:
                timezone.activate(pytz.timezone(request.user.timezone))
            except pytz.UnknownTimeZoneError:
                timezone.activate(pytz.timezone('Africa/Nairobi'))
        else:
            # Detect from IP or use default
            timezone.activate(pytz.timezone('Africa/Nairobi'))

    def process_response(self, request, response):
        timezone.deactivate()
        return response
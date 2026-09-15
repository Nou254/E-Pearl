# users/services/timezone_service.py

from django.utils import timezone
import pytz
from datetime import datetime


class TimezoneService:
    @staticmethod
    def get_user_timezone(user):
        """Get the timezone for a user, fallback to default."""
        if user and user.timezone:
            try:
                return pytz.timezone(user.timezone)
            except pytz.UnknownTimeZoneError:
                return pytz.timezone('Africa/Nairobi')
        return pytz.timezone('Africa/Nairobi')

    @staticmethod
    def to_user_timezone(user, dt):
        """Convert a datetime to the user's local timezone."""
        if dt is None:
            return None
        if timezone.is_aware(dt):
            return dt.astimezone(TimezoneService.get_user_timezone(user))
        return timezone.make_aware(dt, TimezoneService.get_user_timezone(user))

    @staticmethod
    def now_in_user_timezone(user):
        """Get current time in the user's timezone."""
        return timezone.now().astimezone(TimezoneService.get_user_timezone(user))

    @staticmethod
    def get_timezone_list():
        """Get list of common timezones for dropdown."""
        return [(tz, tz) for tz in pytz.common_timezones]

    @staticmethod
    def format_datetime(user, dt, format_string="%Y-%m-%d %H:%M:%S"):
        """Format a datetime in the user's timezone."""
        if dt is None:
            return ""
        local_dt = TimezoneService.to_user_timezone(user, dt)
        return local_dt.strftime(format_string)

    @staticmethod
    def detect_timezone_from_ip(ip_address):
        """
        Detect timezone from IP address using a geolocation service.
        This is a placeholder. In production, use a geolocation API.
        """
        # Default to Nairobi if detection fails
        return 'Africa/Nairobi'
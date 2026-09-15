# hq/services/request_logger.py

from ..models import RequestLog
from django.utils import timezone


class RequestLogger:
    @classmethod
    def log_request(cls, request, response):
        """
        Log an HTTP request and response to the RequestLog model.
        """
        # Only log API requests (skip admin, static, etc.)
        if not request.path.startswith('/api/'):
            return

        # Calculate response time if available
        response_time = getattr(request, 'response_time_ms', None)
        if response_time is None:
            response_time = 0.0

        try:
            RequestLog.objects.create(
                user=request.user if request.user.is_authenticated else None,
                venue=getattr(request.user, 'venue', None) if request.user.is_authenticated else None,
                method=request.method,
                path=request.path,
                endpoint=request.path.split('?')[0],  # strip query params
                status_code=response.status_code,
                response_time_ms=response_time,
                ip_address=cls.get_client_ip(request),
                user_agent=request.META.get('HTTP_USER_AGENT', ''),
                request_body=request.data if hasattr(request, 'data') else {}
            )
        except Exception as e:
            # Log error but don't break the request
            import logging
            logging.getLogger(__name__).error(f"Failed to log request: {e}")

    @classmethod
    def get_client_ip(cls, request):
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip
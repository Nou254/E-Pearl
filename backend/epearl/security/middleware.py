from django.http import JsonResponse
from django.utils.deprecation import MiddlewareMixin
from .services.rule_engine import RuleEngine
from .tasks import log_security_event  # Celery task
import json


class SecurityMiddleware(MiddlewareMixin):
    """
    Intercept every request, evaluate rules, and block if needed.
    Runs after authentication so request.user is available.
    """
    def process_request(self, request):
        # Skip security checks for certain paths (optional whitelist)
        skip_paths = [
            '/api/health/',
            '/api/security/health/',
            '/admin/',
            '/api-auth/',
        ]
        if any(request.path.startswith(p) for p in skip_paths):
            return None

        # Skip if method is OPTIONS (preflight)
        if request.method == 'OPTIONS':
            return None

        blocked, rule, message = RuleEngine.evaluate(request)
        if blocked:
            # Log the event asynchronously
            user = request.user if request.user.is_authenticated else None
            log_security_event.delay(
                user_id=user.id if user else None,
                venue_id=user.venue_id if user and hasattr(user, 'venue_id') else None,
                ip_address=request.META.get('REMOTE_ADDR'),
                endpoint=request.path,
                method=request.method,
                request_headers=dict(request.headers),
                request_body=request.body.decode('utf-8', errors='ignore')[:1024],
                rule_id=rule.id,
                rule_type=rule.rule_type,
                severity=rule.severity,
                user_agent=request.META.get('HTTP_USER_AGENT', ''),
                geo_country=request.META.get('HTTP_CF_IPCOUNTRY', ''),
            )
            # Return a generic 403 or 429 response
            if rule.rule_type == 'rate_limit':
                status_code = 429
                response_data = {"error": "Too many requests"}
            else:
                status_code = 403
                response_data = {"error": "Access denied"}

            return JsonResponse(response_data, status=status_code)

        return None
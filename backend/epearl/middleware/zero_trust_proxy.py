from django.http import JsonResponse
from django.conf import settings
from django.utils.deprecation import MiddlewareMixin
import ipaddress


class ZeroTrustProxyMiddleware(MiddlewareMixin):
    """
    Zero-trust proxy middleware that enforces IP whitelisting for admin endpoints.
    """
    def process_request(self, request):
        # Only enforce for admin endpoints
        if not request.path.startswith('/admin/') and not request.path.startswith('/api/admin/'):
            return None

        # Skip if IP whitelist is not enabled or not configured
        if not getattr(settings, 'ADMIN_IP_WHITELIST', []):
            return None

        # Get client IP
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            client_ip = x_forwarded_for.split(',')[0].strip()
        else:
            client_ip = request.META.get('REMOTE_ADDR')

        # Validate IP
        allowed_ips = settings.ADMIN_IP_WHITELIST
        if client_ip not in allowed_ips:
            # Check if IP is in a subnet
            allowed = False
            for ip_range in allowed_ips:
                try:
                    if ipaddress.ip_address(client_ip) in ipaddress.ip_network(ip_range):
                        allowed = True
                        break
                except Exception:
                    pass
            if not allowed:
                return JsonResponse({
                    'error': 'Access denied. IP not whitelisted.',
                    'code': 'IP_WHITELIST_DENIED'
                }, status=403)

        return None
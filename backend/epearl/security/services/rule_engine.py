# security/services/rule_engine.py

from django.core.cache import cache
from django.conf import settings
from .rate_limiter import RateLimiter
from .pattern_matcher import PatternMatcher
from ..models import SecurityRule
import json
import ipaddress


class RuleEngine:
    CACHE_KEY = 'security_rules_cache'
    CACHE_TIMEOUT = 60  # seconds

    @classmethod
    def get_client_ip(cls, request):
        """
        Get client IP address from request, handling proxies and load balancers.
        
        Checks in order:
        1. HTTP_X_FORWARDED_FOR (common for proxies/load balancers)
        2. HTTP_X_REAL_IP (common for nginx)
        3. REMOTE_ADDR (fallback)
        """
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            # X-Forwarded-For can contain multiple IPs (client, proxy1, proxy2)
            # Take the first one (original client IP)
            ip = x_forwarded_for.split(',')[0].strip()
        else:
            ip = request.META.get('HTTP_X_REAL_IP')
            if not ip:
                ip = request.META.get('REMOTE_ADDR')
        return ip

    @classmethod
    def get_rules(cls):
        """
        Get all enabled rules, ordered by priority, with caching.
        """
        rules = cache.get(cls.CACHE_KEY)
        if rules is None:
            rules = list(SecurityRule.objects.filter(enabled=True).order_by('priority', 'id'))
            cache.set(cls.CACHE_KEY, rules, cls.CACHE_TIMEOUT)
        return rules

    @classmethod
    def evaluate(cls, request):
        """
        Evaluate request against all enabled rules.
        Returns (blocked, rule, message) if blocked, else (False, None, None).
        """
        user = request.user if request.user.is_authenticated else None
        ip = cls.get_client_ip(request)
        method = request.method
        path = request.path
        headers = request.headers
        body = request.body.decode('utf-8', errors='ignore')[:1024]  # first 1KB

        for rule in cls.get_rules():
            if not rule.enabled:
                continue
            # Evaluate rule based on type
            blocked, message = cls._evaluate_rule(rule, request, ip, user, method, path, headers, body)
            if blocked:
                return True, rule, message
        return False, None, None

    @classmethod
    def _evaluate_rule(cls, rule, request, ip, user, method, path, headers, body):
        rule_type = rule.rule_type
        conditions = rule.conditions

        if rule_type == 'ip_blocklist':
            blocked_ips = conditions.get('ips', [])
            if ip in blocked_ips:
                return True, f"IP {ip} is blocked"
            # Also check CIDR ranges if needed
            for cidr in conditions.get('cidrs', []):
                if ipaddress.ip_address(ip) in ipaddress.ip_network(cidr):
                    return True, f"IP {ip} in blocked range {cidr}"

        elif rule_type == 'ip_allowlist':
            allowed_ips = conditions.get('ips', [])
            if ip not in allowed_ips:
                return True, f"IP {ip} not allowed"

        elif rule_type == 'rate_limit':
            # Rate limit key can be per IP or per user or combination
            key = conditions.get('key', 'ip')
            limit = conditions.get('limit', 100)
            window = conditions.get('window', 60)  # seconds
            if key == 'ip':
                rate_key = f"rate_limit:{ip}"
            elif key == 'user' and user:
                rate_key = f"rate_limit:user:{user.id}"
            elif key == 'user_ip' and user:
                rate_key = f"rate_limit:user:{user.id}:{ip}"
            else:
                rate_key = f"rate_limit:{ip}"  # fallback
            # Add endpoint specificity
            endpoint_specific = conditions.get('endpoint_specific', False)
            if endpoint_specific:
                rate_key += f":{path}"
            allowed, current = RateLimiter.is_allowed(rate_key, limit, window)
            if not allowed:
                return True, f"Rate limit exceeded: {current}/{limit} per {window}s"

        elif rule_type == 'path_restriction':
            # Block specific paths or patterns
            blocked_paths = conditions.get('paths', [])
            for blocked in blocked_paths:
                if blocked in path:
                    return True, f"Path {path} is blocked"

        elif rule_type == 'method_restriction':
            allowed_methods = conditions.get('allowed_methods', [])
            if method not in allowed_methods:
                return True, f"Method {method} not allowed on this endpoint"

        elif rule_type == 'sql_injection':
            # Check request body and query parameters
            query_string = request.META.get('QUERY_STRING', '')
            combined = body + query_string
            if PatternMatcher.contains_sql_injection(combined):
                return True, "SQL injection pattern detected"

        elif rule_type == 'xss':
            combined = body + request.META.get('QUERY_STRING', '')
            if PatternMatcher.contains_xss(combined):
                return True, "XSS pattern detected"

        elif rule_type == 'path_traversal':
            combined = body + request.META.get('QUERY_STRING', '')
            if PatternMatcher.contains_path_traversal(combined):
                return True, "Path traversal pattern detected"

        elif rule_type == 'geo_block':
            # Requires geo_ip lookup – we'll implement placeholder
            geo_country = request.META.get('HTTP_CF_IPCOUNTRY') or request.META.get('GEOIP_COUNTRY_CODE')
            if not geo_country:
                geo_country = 'Unknown'
            blocked_countries = conditions.get('countries', [])
            if geo_country in blocked_countries:
                return True, f"Country {geo_country} is blocked"

        elif rule_type == 'user_agent_block':
            user_agent = request.META.get('HTTP_USER_AGENT', '')
            blocked_agents = conditions.get('agents', [])
            for agent in blocked_agents:
                if agent.lower() in user_agent.lower():
                    return True, f"User-agent {user_agent} is blocked"

        elif rule_type == 'request_size':
            # Block if request body exceeds limit (in bytes)
            limit_bytes = conditions.get('limit_bytes', 1024 * 1024)  # default 1MB
            content_length = request.META.get('CONTENT_LENGTH', 0)
            if content_length and int(content_length) > limit_bytes:
                return True, f"Request body too large: {content_length} > {limit_bytes}"

        elif rule_type == 'role_endpoint':
            # Only applies if user is authenticated
            if user:
                allowed_roles = conditions.get('allowed_roles', [])
                # user.user_type is the role (e.g., 'manager', 'waiter', 'admin')
                user_role = user.user_type
                if user_role not in allowed_roles:
                    # Also check if path pattern matches
                    path_patterns = conditions.get('paths', [])
                    for pattern in path_patterns:
                        if pattern in path:
                            return True, f"Role {user_role} not allowed on {path}"

        elif rule_type == 'behavioural':
            # Simplified: check if user logs in from a new device (requires stored device fingerprint)
            # This can be enhanced.
            if user and conditions.get('check_new_device', False):
                # compare device fingerprint from request with stored one
                device_fingerprint = request.META.get('HTTP_USER_AGENT', '')  # placeholder
                stored = getattr(user, 'device_fingerprint', None)  # from User model
                if stored and device_fingerprint != stored:
                    return True, "New device detected"

        return False, None
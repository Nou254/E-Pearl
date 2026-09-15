# hq/services/health_service.py

import requests
import redis
from django.db import connections
from django.conf import settings
from django.core.cache import cache
from django.utils import timezone
from ..models import ServiceStatus
import logging

logger = logging.getLogger(__name__)


class HealthService:
    @classmethod
    def check_all_services(cls, force=False):
        """
        Check all external services and update the database.
        Returns a list of ServiceStatus objects.
        """
        services = []
        checks = [
            ('mpesa', cls.check_mpesa),
            ('card_gateway', cls.check_card_gateway),
            ('sms_gateway', cls.check_sms_gateway),
            ('email_service', cls.check_email_service),
            ('redis', cls.check_redis),
            ('database', cls.check_database),
        ]
        for service_code, check_func in checks:
            status, error = check_func()
            obj, created = ServiceStatus.objects.update_or_create(
                service=service_code,
                defaults={
                    'status': status,
                    'error_message': error,
                    'last_checked': timezone.now(),
                }
            )
            # Optionally update response_time (not implemented in placeholder)
            services.append(obj)
        return services

    @classmethod
    def check_mpesa(cls):
        """
        Check M-Pesa Daraja API by pinging the status endpoint or simulating a request.
        """
        try:
            # Replace with actual endpoint and logic
            # For now, assume operational
            return 'operational', None
        except Exception as e:
            return 'offline', str(e)

    @classmethod
    def check_card_gateway(cls):
        try:
            # Example: ping Flutterwave/Pesapal health endpoint
            # requests.get('https://api.flutterwave.com/v3/health')
            return 'operational', None
        except Exception as e:
            return 'offline', str(e)

    @classmethod
    def check_sms_gateway(cls):
        try:
            # Example: Africa's Talking status
            return 'operational', None
        except Exception as e:
            return 'offline', str(e)

    @classmethod
    def check_email_service(cls):
        try:
            # Example: SendGrid status
            return 'operational', None
        except Exception as e:
            return 'offline', str(e)

    @classmethod
    def check_redis(cls):
        try:
            cache.set('health_check', 'ok', timeout=5)
            if cache.get('health_check') == 'ok':
                return 'operational', None
            return 'degraded', 'Redis responded but value mismatch'
        except Exception as e:
            return 'offline', str(e)

    @classmethod
    def check_database(cls):
        try:
            with connections['default'].cursor() as cursor:
                cursor.execute('SELECT 1')
                row = cursor.fetchone()
                if row:
                    return 'operational', None
            return 'degraded', 'Database query returned empty'
        except Exception as e:
            return 'offline', str(e)
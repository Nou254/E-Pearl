# hq/services/system_monitor.py

import psutil
from django.db import connections
from django.core.cache import cache
from django.utils import timezone


class SystemMonitor:
    @classmethod
    def get_status(cls):
        """
        Collect system resource metrics.
        """
        return {
            'cpu_usage': psutil.cpu_percent(interval=1),
            'memory_usage': psutil.virtual_memory().percent,
            'disk_usage': psutil.disk_usage('/').percent,
            'db_connections': cls.get_db_connections(),
            'redis_connections': cls.get_redis_connections(),
            'last_updated': timezone.now().isoformat(),
        }

    @classmethod
    def get_db_connections(cls):
        """
        Return the number of active database connections.
        """
        try:
            with connections['default'].cursor() as cursor:
                cursor.execute("SELECT count(*) FROM pg_stat_activity")
                row = cursor.fetchone()
                return row[0] if row else 0
        except Exception:
            return -1

    @classmethod
    def get_redis_connections(cls):
        """
        Return the number of active Redis connections (approximate).
        """
        try:
            # Assuming Redis is used for cache
            info = cache._client.info()
            return info.get('connected_clients', 0)
        except Exception:
            return -1
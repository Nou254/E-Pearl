import redis
from django.conf import settings
import time

# Get Redis URL from settings – fallback to cache LOCATION
REDIS_URL = getattr(settings, 'REDIS_URL', None)
if not REDIS_URL:
    # Try to extract from CACHES
    cache_location = settings.CACHES.get('default', {}).get('LOCATION', '')
    if cache_location.startswith('redis://'):
        REDIS_URL = cache_location
    else:
        REDIS_URL = 'redis://127.0.0.1:6379/1'  # fallback

redis_client = redis.Redis.from_url(REDIS_URL)


class RateLimiter:
    @classmethod
    def is_allowed(cls, key, limit, window_seconds):
        """
        Check if request is allowed under rate limit.
        Returns tuple (allowed, current_count).
        """
        now = int(time.time())
        window_start = now - window_seconds
        pipe = redis_client.pipeline()
        pipe.zremrangebyscore(key, 0, window_start)  # remove old entries
        pipe.zcard(key)  # count remaining
        current_count = pipe.execute()[1]
        if current_count >= limit:
            return False, current_count
        pipe = redis_client.pipeline()
        pipe.zadd(key, {str(now): now})
        pipe.expire(key, window_seconds + 1)
        pipe.execute()
        return True, current_count + 1
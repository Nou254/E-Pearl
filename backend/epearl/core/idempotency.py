# core/idempotency.py

from django.core.cache import cache
from django.http import JsonResponse
from rest_framework.response import Response
import hashlib
import json


class Idempotency:
    """
    Central idempotency handling for payment and other sensitive operations.
    Uses Redis/Django cache to store request results.
    """

    @classmethod
    def process_request(cls, request, key_prefix):
        """
        Check idempotency key in request header.
        If a cached result exists, return a Response object with the cached data.
        If no key is provided, return None (proceed without idempotency).
        If key is provided and no cached result, store a placeholder and return None.
        """
        idempotency_key = request.headers.get('Idempotency-Key')
        if not idempotency_key:
            return None  # proceed without idempotency

        cache_key = f"{key_prefix}:{idempotency_key}"
        cached = cache.get(cache_key)
        if cached:
            # Return a DRF Response with cached data
            return Response(cached, status=200)

        # Store a placeholder to indicate processing (prevents duplicate simultaneous requests)
        cache.set(cache_key, {'status': 'processing'}, timeout=300)
        return None

    @classmethod
    def store_result(cls, key_prefix, idempotency_key, result_data):
        """
        Store successful result in cache for idempotency.
        """
        if idempotency_key:
            cache_key = f"{key_prefix}:{idempotency_key}"
            # Store result with longer timeout (e.g., 1 hour)
            cache.set(cache_key, result_data, timeout=3600)

    @classmethod
    def generate_key(cls, request, suffix=""):
        """
        Generate an idempotency key from request data if one is not provided.
        Useful for cases where the client does not send a key.
        """
        # Create a hash from the request path, user, and body
        # This is a fallback; ideally clients provide their own key.
        body_hash = hashlib.md5(request.body).hexdigest() if request.body else ""
        user_id = request.user.id if request.user.is_authenticated else "anonymous"
        raw = f"{request.path}:{user_id}:{body_hash}:{suffix}"
        return hashlib.sha256(raw.encode()).hexdigest()[:32]
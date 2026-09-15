# hq/middleware.py

import time
from .services.request_logger import RequestLogger


class RequestLogMiddleware:
    """
    Middleware to log API requests and measure response time.
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        start_time = time.time()
        response = self.get_response(request)
        duration = (time.time() - start_time) * 1000  # ms
        request.response_time_ms = duration

        # Log asynchronously or synchronously
        RequestLogger.log_request(request, response)
        return response
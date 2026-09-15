# core/exceptions.py

from rest_framework.views import exception_handler
from rest_framework.response import Response
from rest_framework import status


def custom_exception_handler(exc, context):
    """
    Custom exception handler for REST Framework.
    """
    response = exception_handler(exc, context)

    if response is not None:
        # Customize the error response format
        response.data = {
            'success': False,
            'error': {
                'code': response.status_code,
                'message': response.data.get('detail', 'An error occurred'),
                'details': response.data
            }
        }

    return response
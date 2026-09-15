# payments/services/gateway_service.py

import requests
import json
from django.conf import settings
from decimal import Decimal
from django.core.exceptions import ValidationError
import base64
import uuid


class GatewayService:
    """
    Handles actual communication with payment gateways.
    This is a stub for now – replace with real API calls.
    """

    @staticmethod
    def get_gateway_config(venue, gateway_provider='daraja'):
        """Retrieve gateway credentials from the database."""
        from payments.models import PaymentGatewayConfig
        try:
            config = PaymentGatewayConfig.objects.get(
                venue=venue,
                gateway_provider=gateway_provider,
                status='active'
            )
            return config
        except PaymentGatewayConfig.DoesNotExist:
            raise ValidationError(f"{gateway_provider} credentials not configured for this venue.")

    @staticmethod
    def mpesa_stk_push(phone, amount, reference, config):
        """
        Send M-Pesa STK Push (Lipa Na M-Pesa Online).
        This is a stub – replace with actual Daraja API calls.
        """
        # Stub: simulate success
        # In production, call Safaricom Daraja API
        # https://developer.safaricom.co.ke/APIs/STKPush
        return {
            'success': True,
            'gateway_reference_id': f"MPESA_{uuid.uuid4().hex[:10]}",
            'message': 'STK Push sent successfully.'
        }

    @staticmethod
    def mpesa_query_status(gateway_reference_id, config):
        """
        Query M-Pesa transaction status.
        Stub – returns success.
        """
        return {
            'success': True,
            'status': 'completed',
            'message': 'Transaction completed successfully.'
        }

    @staticmethod
    def mpesa_b2c(phone, amount, reference, config):
        """
        Send M-Pesa B2C (Business to Customer) – for refunds.
        Stub – returns success.
        """
        return {
            'success': True,
            'gateway_reference_id': f"B2C_{uuid.uuid4().hex[:10]}",
            'message': 'Refund sent successfully.'
        }

    @staticmethod
    def flutterwave_card_payment(card_details, amount, currency, config):
        """
        Process card payment via Flutterwave.
        Stub – returns success.
        """
        return {
            'success': True,
            'gateway_reference_id': f"FW_{uuid.uuid4().hex[:10]}",
            'message': 'Card payment processed successfully.',
            'payment_token': 'token_123'
        }

    @staticmethod
    def flutterwave_query_status(gateway_reference_id, config):
        """
        Query Flutterwave transaction status.
        Stub – returns success.
        """
        return {
            'success': True,
            'status': 'completed',
            'message': 'Transaction completed successfully.'
        }

    @staticmethod
    def flutterwave_refund(transaction_id, amount, config):
        """
        Refund via Flutterwave.
        Stub – returns success.
        """
        return {
            'success': True,
            'gateway_reference_id': f"REF_{uuid.uuid4().hex[:10]}",
            'message': 'Refund processed successfully.'
        }
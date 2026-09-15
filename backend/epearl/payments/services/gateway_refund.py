# payments/services/gateway_refund.py

import logging
from decimal import Decimal
from django.utils import timezone
from django.conf import settings

logger = logging.getLogger(__name__)


class GatewayRefundError(Exception):
    pass


class GatewayRefundService:
    """
    Abstraction layer for calling payment gateway refund APIs.
    Supports M-Pesa and Card gateways.
    """

    @classmethod
    def process_refund(cls, transaction, amount, gateway_reference=None):
        """
        Process a refund for a given transaction.
        Returns a gateway reference ID.
        """
        payment_method = transaction.payment_method
        if payment_method == 'mpesa':
            return cls._refund_mpesa(transaction, amount, gateway_reference)
        elif payment_method == 'card':
            return cls._refund_card(transaction, amount, gateway_reference)
        else:
            raise GatewayRefundError(f"Unsupported payment method: {payment_method}")

    @classmethod
    def _refund_mpesa(cls, transaction, amount, gateway_reference):
        """
        Refund via M-Pesa B2C or reversal.
        This is a stub – implement actual Daraja API call.
        """
        # Simulate refund processing
        # In production, call Safaricom B2C API or reverse transaction
        logger.info(f"Processing M-Pesa refund for transaction {transaction.id} amount {amount}")
        # Simulate success
        return f"MPESA_REF_{timezone.now().timestamp()}"

    @classmethod
    def _refund_card(cls, transaction, amount, gateway_reference):
        """
        Refund via card gateway (Flutterwave, Pesapal, etc.)
        This is a stub – implement actual gateway refund API.
        """
        # Simulate refund processing
        logger.info(f"Processing Card refund for transaction {transaction.id} amount {amount}")
        # Simulate success
        return f"CARD_REF_{timezone.now().timestamp()}"
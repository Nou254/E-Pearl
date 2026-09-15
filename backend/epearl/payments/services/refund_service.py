# payments/services/refund_service.py

import logging
from decimal import Decimal
from django.utils import timezone
from django.db import transaction as db_transaction
from .gateway_refund import GatewayRefundService, GatewayRefundError
from .refund_classification import RefundClassification

logger = logging.getLogger(__name__)


class RefundService:
    """
    Core logic for processing refunds.
    """

    @classmethod
    def process_refund(cls, refund_request, approved_amount, reviewed_by=None, notes=""):
        """
        Process a refund for a given refund request.
        Returns a RefundTransaction object.
        """
        if refund_request.status not in ['pending', 'approved']:
            raise ValueError("Refund request is not in a processable state.")

        original_transaction = refund_request.transaction

        # Ensure approved amount does not exceed remaining balance
        max_refundable = original_transaction.amount - original_transaction.amount_refunded
        if approved_amount > max_refundable:
            raise ValueError(f"Approved amount {approved_amount} exceeds remaining refundable amount {max_refundable}")

        with db_transaction.atomic():
            # Call gateway to process refund
            try:
                gateway_ref_id = GatewayRefundService.process_refund(
                    original_transaction,
                    approved_amount,
                    gateway_reference=original_transaction.gateway_reference_id
                )
            except GatewayRefundError as e:
                # Mark refund request as failed
                refund_request.status = 'failed'
                refund_request.resolution_notes = f"Gateway error: {str(e)}"
                refund_request.save()
                raise

            # Create refund transaction record
            refund_transaction = refund_request.refund_transactions.create(
                original_transaction=original_transaction,
                amount=-approved_amount,  # negative amount
                gateway_reference_id=gateway_ref_id,
                status='pending'  # will be updated by webhook
            )

            # Update refund request status (will be completed via webhook)
            refund_request.status = 'processing'
            refund_request.approved_amount = approved_amount
            refund_request.reviewed_by = reviewed_by
            refund_request.reviewed_at = timezone.now()
            if notes:
                refund_request.resolution_notes = notes
            refund_request.save()

            # Optionally update original transaction refund status (but we'll do it after webhook confirmation)
            # For now, we just record the refund_transaction.

            return refund_transaction

    @classmethod
    def calculate_eligible_refund(cls, booking):
        """
        Calculate the maximum refundable amount for a booking.
        Considers venue refund policy and amount paid.
        """
        # Placeholder: implement policy logic
        # For now, return full amount of the payment transaction
        transaction = booking.transactions.filter(transaction_type='payment', transaction_status='success').first()
        if transaction:
            return transaction.amount - transaction.amount_refunded
        return Decimal('0')
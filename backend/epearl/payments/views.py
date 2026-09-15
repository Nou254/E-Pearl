# payments/views.py

from rest_framework import viewsets, permissions, status, filters
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.decorators import action
from rest_framework.response import Response
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.http import JsonResponse
from django.utils import timezone
from django.core.cache import cache
from django.db.models import Count, Sum, Avg
from datetime import timedelta
from decimal import Decimal
import json
import logging

from .models import (
    Transaction, PreAuthHold, PaymentGatewayConfig, WebhookLog,
    RefundRequest, RefundTransaction
)
from .serializers import (
    TransactionSerializer,
    PreAuthHoldSerializer,
    PaymentGatewayConfigSerializer,
    PaymentAnalyticsSerializer,
    UserSpendingSerializer,
    RefundRequestSerializer,
    RefundRequestCreateSerializer,
    RefundRequestReviewSerializer,
    RefundTransactionSerializer,
)
from .services.payment_service import PaymentService
from .services.refund_service import RefundService
from .services.refund_classification import RefundClassification

logger = logging.getLogger(__name__)


# ---------- Idempotency Helpers (unchanged) ----------
def _process_idempotency(request, key_prefix):
    idempotency_key = request.headers.get('Idempotency-Key')
    if not idempotency_key:
        return None
    cache_key = f"{key_prefix}:{idempotency_key}"
    cached = cache.get(cache_key)
    if cached:
        return Response(cached, status=status.HTTP_200_OK)
    cache.set(cache_key, {'status': 'processing'}, timeout=300)
    return None


def _store_idempotency_result(key_prefix, idempotency_key, result_data):
    if idempotency_key:
        cache_key = f"{key_prefix}:{idempotency_key}"
        cache.set(cache_key, result_data, timeout=3600)


# ---------- ViewSets (existing + new) ----------

class TransactionViewSet(viewsets.ReadOnlyModelViewSet):
    """
    View-only for transactions (audit purposes).
    """
    serializer_class = TransactionSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['transaction_type', 'transaction_status', 'payment_method']
    ordering_fields = ['transaction_time', 'amount']

    def get_queryset(self):
        user = self.request.user
        if user.user_type in ['admin', 'support', 'finance']:
            return Transaction.objects.all()
        if user.venue:
            return Transaction.objects.filter(venue=user.venue)
        return Transaction.objects.filter(user=user)

    @action(detail=False, methods=['get'], permission_classes=[permissions.IsAdminUser])
    def admin_analytics(self, request):
        # (unchanged, omitted for brevity – same as original)
        pass

    @action(detail=False, methods=['get'], permission_classes=[permissions.IsAuthenticated])
    def user_spending(self, request):
        # (unchanged, omitted for brevity – same as original)
        pass


class PreAuthHoldViewSet(viewsets.ModelViewSet):
    serializer_class = PreAuthHoldSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['hold_status', 'guest_session']

    def get_queryset(self):
        user = self.request.user
        if user.user_type in ['admin', 'support']:
            return PreAuthHold.objects.all()
        if user.venue:
            return PreAuthHold.objects.filter(venue=user.venue)
        return PreAuthHold.objects.filter(guest_session__user=user)

    @action(detail=True, methods=['post'])
    def capture(self, request, pk=None):
        # (unchanged – same as original)
        pass

    @action(detail=True, methods=['post'])
    def void(self, request, pk=None):
        # (unchanged – same as original)
        pass

    @action(detail=True, methods=['post'])
    def top_up(self, request, pk=None):
        # (unchanged – same as original)
        pass


class PaymentGatewayConfigViewSet(viewsets.ModelViewSet):
    serializer_class = PaymentGatewayConfigSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.user_type in ['admin', 'support']:
            return PaymentGatewayConfig.objects.all()
        if user.venue:
            return PaymentGatewayConfig.objects.filter(venue=user.venue)
        return PaymentGatewayConfig.objects.none()

    def perform_create(self, serializer):
        user = self.request.user
        if not user.venue:
            raise PermissionError("You are not associated with a venue.")
        serializer.save(venue=user.venue)


# ========== NEW: RefundRequestViewSet ==========

class RefundRequestViewSet(viewsets.ModelViewSet):
    """
    Handles refund requests from customers and admin review.
    """
    serializer_class = RefundRequestSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['status', 'classification', 'reason']
    ordering_fields = ['created_at', 'requested_amount']

    def get_queryset(self):
        user = self.request.user
        if user.user_type in ['admin', 'support', 'finance']:
            return RefundRequest.objects.all()
        if user.venue:
            return RefundRequest.objects.filter(venue=user.venue)
        # Customers see only their own
        return RefundRequest.objects.filter(customer=user)

    def create(self, request, *args, **kwargs):
        """
        Customer initiates a refund request.
        """
        serializer = RefundRequestCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        booking_id = serializer.validated_data['booking_id']
        reason = serializer.validated_data['reason']
        requested_amount = serializer.validated_data['requested_amount']
        notes = serializer.validated_data.get('notes', '')

        # Fetch booking and verify ownership/permissions
        from explore.models import Booking
        try:
            booking = Booking.objects.get(id=booking_id)
        except Booking.DoesNotExist:
            return Response({'error': 'Booking not found'}, status=status.HTTP_404_NOT_FOUND)

        # Ensure user is the customer or has permission
        if booking.guest_session.user != request.user and not request.user.user_type in ['admin', 'support']:
            return Response({'error': 'You do not own this booking'}, status=status.HTTP_403_FORBIDDEN)

        # Check if booking already has a pending refund
        if RefundRequest.objects.filter(booking=booking, status__in=['pending', 'processing']).exists():
            return Response({'error': 'A refund request is already in progress'}, status=status.HTTP_400_BAD_REQUEST)

        # Get the original transaction (assuming it's the payment transaction)
        transaction = booking.transactions.filter(transaction_type='payment', transaction_status='success').first()
        if not transaction:
            return Response({'error': 'No successful payment transaction found for this booking'}, status=status.HTTP_400_BAD_REQUEST)

        # Classify the refund
        classification = RefundClassification.classify(booking, reason)

        # Create refund request
        refund_request = RefundRequest.objects.create(
            booking=booking,
            transaction=transaction,
            customer=request.user,
            venue=booking.venue,
            reason=reason,
            classification=classification,
            requested_amount=requested_amount,
            status='pending',
            metadata={'notes': notes}
        )

        # If classification is 'nou_fault' or 'venue_fault' auto-approve? 
        # For now, leave pending for admin review.
        # But we could auto-approve for venue_fault if policy allows.

        return Response(
            RefundRequestSerializer(refund_request).data,
            status=status.HTTP_201_CREATED
        )

    @action(detail=True, methods=['post'], permission_classes=[permissions.IsAuthenticated])
    def review(self, request, pk=None):
        """
        Admin/venue manager reviews and approves/rejects a refund.
        """
        refund_request = self.get_object()
        if not request.user.user_type in ['admin', 'support', 'finance'] and request.user != refund_request.venue.owner:
            return Response({'error': 'Permission denied'}, status=status.HTTP_403_FORBIDDEN)

        serializer = RefundRequestReviewSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        action = serializer.validated_data['action']
        approved_amount = serializer.validated_data.get('approved_amount', refund_request.requested_amount)
        resolution_notes = serializer.validated_data.get('resolution_notes', '')

        if action == 'reject':
            refund_request.status = 'rejected'
            refund_request.resolution_notes = resolution_notes
            refund_request.reviewed_by = request.user
            refund_request.reviewed_at = timezone.now()
            refund_request.save()
            return Response({'status': 'rejected'})

        elif action == 'approve':
            # Ensure approved amount does not exceed original transaction amount
            if approved_amount > refund_request.transaction.amount:
                return Response(
                    {'error': 'Approved amount cannot exceed original transaction amount'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Process the refund via RefundService
            try:
                refund_transaction = RefundService.process_refund(
                    refund_request,
                    approved_amount,
                    reviewed_by=request.user,
                    notes=resolution_notes
                )
                refund_request.status = 'completed'
                refund_request.approved_amount = approved_amount
                refund_request.reviewed_by = request.user
                refund_request.reviewed_at = timezone.now()
                refund_request.resolution_notes = resolution_notes
                refund_request.save()

                # Update original transaction refund status
                original_txn = refund_request.transaction
                original_txn.amount_refunded += approved_amount
                if original_txn.amount_refunded >= original_txn.amount:
                    original_txn.refund_status = 'full'
                else:
                    original_txn.refund_status = 'partial'
                original_txn.save()

                return Response({
                    'status': 'approved',
                    'refund_transaction': RefundTransactionSerializer(refund_transaction).data
                })
            except Exception as e:
                refund_request.status = 'failed'
                refund_request.resolution_notes = f"Processing failed: {str(e)}"
                refund_request.save()
                return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

        return Response({'error': 'Invalid action'}, status=status.HTTP_400_BAD_REQUEST)


# ---------- Webhook endpoint (extended for refunds) ----------

@csrf_exempt
@require_POST
def webhook(request):
    provider = request.META.get('HTTP_X_GATEWAY_PROVIDER', 'unknown')
    event_type = request.META.get('HTTP_X_EVENT_TYPE', 'unknown')
    signature = request.META.get('HTTP_X_WEBHOOK_SIGNATURE', '')

    if not signature:
        signature = request.META.get('HTTP_VERIF_HASH', '')

    try:
        payload = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)

    webhook_log = WebhookLog.objects.create(
        provider=provider,
        event_type=event_type,
        payload=payload,
        signature=signature,
        is_verified=False,
        is_processed=False,
        received_at=timezone.now()
    )

    # Verify signature (simplified)
    is_verified = True  # In production, implement proper verification
    webhook_log.is_verified = is_verified
    webhook_log.save()

    if not is_verified:
        webhook_log.error_message = "Signature verification failed"
        webhook_log.save()
        return JsonResponse({'error': 'Invalid signature'}, status=403)

    # Process based on event type
    try:
        if event_type in ['payment.success', 'charge.completed']:
            reference_id = payload.get('reference_id') or payload.get('CheckoutRequestID') or payload.get('tx_ref')
            if reference_id:
                try:
                    transaction = Transaction.objects.get(gateway_reference_id=reference_id)
                    PaymentService.mark_transaction_success(transaction, reference_id)
                    # Update linked objects (booking, ticket, etc.)
                    if transaction.booking:
                        booking = transaction.booking
                        booking.status = 'confirmed'
                        booking.payment_status = 'paid'
                        booking.paid_amount = transaction.amount
                        if booking.table:
                            booking.table.reserve()
                        booking.save()
                    if transaction.ticket:
                        transaction.ticket.status = 'purchased'
                        transaction.ticket.save()
                    webhook_log.is_processed = True
                    webhook_log.save()
                except Transaction.DoesNotExist:
                    logger.warning(f"Transaction not found for reference: {reference_id}")

        elif event_type in ['payment.failed', 'charge.failed']:
            reference_id = payload.get('reference_id') or payload.get('CheckoutRequestID') or payload.get('tx_ref')
            if reference_id:
                try:
                    transaction = Transaction.objects.get(gateway_reference_id=reference_id)
                    error_message = payload.get('message') or payload.get('ResultDesc') or 'Payment failed'
                    PaymentService.mark_transaction_failed(transaction, error_message)
                    webhook_log.is_processed = True
                    webhook_log.save()
                except Transaction.DoesNotExist:
                    pass

        # ----- NEW: REFUND WEBHOOK HANDLING -----
        elif event_type == 'refund.success':
            reference_id = payload.get('refund_id') or payload.get('reference_id')
            if reference_id:
                try:
                    refund_txn = RefundTransaction.objects.get(gateway_reference_id=reference_id)
                    refund_txn.status = 'success'
                    refund_txn.save()
                    # Update refund request status if all refund transactions are successful
                    refund_request = refund_txn.refund_request
                    if refund_request.refund_transactions.filter(status__in=['pending', 'failed']).exists():
                        # Some still pending/failed
                        pass
                    else:
                        refund_request.status = 'completed'
                        refund_request.save()
                    webhook_log.is_processed = True
                    webhook_log.save()
                except RefundTransaction.DoesNotExist:
                    logger.warning(f"RefundTransaction not found for reference: {reference_id}")

        elif event_type == 'refund.failed':
            reference_id = payload.get('refund_id') or payload.get('reference_id')
            if reference_id:
                try:
                    refund_txn = RefundTransaction.objects.get(gateway_reference_id=reference_id)
                    refund_txn.status = 'failed'
                    refund_txn.gateway_response_message = payload.get('message', 'Refund failed')
                    refund_txn.save()
                    # Mark refund request as failed
                    refund_request = refund_txn.refund_request
                    refund_request.status = 'failed'
                    refund_request.resolution_notes = f"Gateway refund failed: {payload.get('message', '')}"
                    refund_request.save()
                    webhook_log.is_processed = True
                    webhook_log.save()
                except RefundTransaction.DoesNotExist:
                    pass

        else:
            logger.info(f"Unhandled webhook event type: {event_type}")
    except Exception as e:
        webhook_log.error_message = str(e)
        webhook_log.save()
        logger.error(f"Webhook processing failed: {e}")
        return JsonResponse({'error': 'Processing failed'}, status=500)

    return JsonResponse({'status': 'ok'})
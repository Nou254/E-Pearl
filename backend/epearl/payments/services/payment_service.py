# payments/services/payment_service.py

from decimal import Decimal
from django.utils import timezone
from django.core.exceptions import ValidationError
from ..models import Transaction, PreAuthHold, PaymentGatewayConfig
from .gateway_service import GatewayService
from notifications.services.notification_service import NotificationService


class PaymentService:
    PLATFORM_FEE_PERCENTAGE = 2

    @classmethod
    def calculate_platform_fee(cls, amount):
        return amount * Decimal(cls.PLATFORM_FEE_PERCENTAGE / 100)

    @classmethod
    def create_transaction(cls, venue, amount, transaction_type, payment_method, **kwargs):
        transaction = Transaction.objects.create(
            venue=venue,
            amount=amount,
            transaction_type=transaction_type,
            payment_method=payment_method,
            currency=venue.currency or 'KES',
            transaction_status='pending',
            **kwargs
        )
        return transaction

    @classmethod
    def mark_transaction_success(cls, transaction, gateway_reference_id, response_code=None):
        transaction.transaction_status = 'success'
        transaction.gateway_reference_id = gateway_reference_id
        transaction.gateway_response_code = response_code
        transaction.save()
        # Send payment success notification
        if transaction.user:
            NotificationService.send_payment_success(transaction, transaction.user)
        return transaction

    @classmethod
    def mark_transaction_failed(cls, transaction, error_message, response_code=None):
        transaction.transaction_status = 'failed'
        transaction.gateway_response_message = error_message
        transaction.gateway_response_code = response_code
        transaction.save()
        # Send payment failed notification
        if transaction.user:
            NotificationService.send_payment_failed(transaction, transaction.user, error_message)
        return transaction

    # ---------- Payment Processing ----------

    @classmethod
    def process_mpesa_payment(cls, venue, phone, amount, reference, **kwargs):
        config = GatewayService.get_gateway_config(venue, 'daraja')
        response = GatewayService.mpesa_stk_push(phone, amount, reference, config)

        if response['success']:
            transaction = cls.create_transaction(
                venue=venue,
                amount=amount,
                transaction_type='payment',
                payment_method='mpesa',
                metadata={'phone': phone, 'reference': reference, **kwargs}
            )
            cls.mark_transaction_success(
                transaction,
                gateway_reference_id=response['gateway_reference_id']
            )
            return transaction
        else:
            raise ValidationError("Payment failed.")

    @classmethod
    def process_card_payment(cls, venue, card_details, amount, **kwargs):
        config = GatewayService.get_gateway_config(venue, 'flutterwave')
        response = GatewayService.flutterwave_card_payment(
            card_details, amount, venue.currency, config
        )

        if response['success']:
            transaction = cls.create_transaction(
                venue=venue,
                amount=amount,
                transaction_type='payment',
                payment_method='card',
                metadata={'card_details': '***', **kwargs}
            )
            cls.mark_transaction_success(
                transaction,
                gateway_reference_id=response['gateway_reference_id']
            )
            return transaction
        else:
            raise ValidationError("Card payment failed.")

    # ---------- Pre-Authorization (Host Mode) ----------

    @classmethod
    def create_hold(cls, guest_session, declared_amount, payment_method):
        if declared_amount <= 0:
            raise ValidationError("Declared amount must be greater than 0.")

        hold = PreAuthHold.objects.create(
            venue=guest_session.venue,
            guest_session=guest_session,
            declared_amount=declared_amount,
            remaining_balance=declared_amount,
            hold_status='pending',
            payment_method=payment_method,
        )
        return hold

    @classmethod
    def activate_hold(cls, hold, gateway_reference_id, payment_token):
        hold.hold_status = 'active'
        hold.gateway_reference_id = gateway_reference_id
        hold.payment_token = payment_token
        hold.save()
        return hold

    @classmethod
    def capture_hold(cls, hold, amount):
        if not hold.can_capture():
            raise ValidationError("Hold cannot be captured in its current state.")
        if amount > hold.remaining_balance:
            raise ValidationError("Capture amount exceeds remaining balance.")

        hold.remaining_balance -= amount
        hold.consumed_amount += amount

        if hold.remaining_balance == 0:
            hold.hold_status = 'captured'
        else:
            hold.hold_status = 'active'

        hold.capture_time = timezone.now()
        hold.save()

        transaction = cls.create_transaction(
            venue=hold.venue,
            amount=amount,
            transaction_type='capture',
            payment_method=hold.payment_method,
            pre_auth_hold=hold,
            guest_session=hold.guest_session,
        )
        cls.mark_transaction_success(transaction, hold.gateway_reference_id)

        # Check budget depletion (if remaining balance <= 20% of declared)
        if hold.remaining_balance <= hold.declared_amount * Decimal('0.2'):
            if hold.guest_session and hold.guest_session.user:
                NotificationService.send_budget_depletion(hold, hold.guest_session.user)

        return hold, transaction

    @classmethod
    def void_hold(cls, hold):
        if hold.hold_status in ['captured', 'voided']:
            raise ValidationError("Hold cannot be voided in its current state.")

        hold.hold_status = 'voided'
        hold.void_time = timezone.now()
        hold.save()

        transaction = cls.create_transaction(
            venue=hold.venue,
            amount=hold.declared_amount - hold.consumed_amount,
            transaction_type='void',
            payment_method=hold.payment_method,
            pre_auth_hold=hold,
            guest_session=hold.guest_session,
        )
        cls.mark_transaction_success(transaction, hold.gateway_reference_id)
        return hold, transaction

    @classmethod
    def top_up_hold(cls, hold, additional_amount):
        if hold.hold_status not in ['active', 'pending']:
            raise ValidationError("Hold must be active to top up.")

        hold.declared_amount += additional_amount
        hold.remaining_balance += additional_amount
        hold.save()

        transaction = cls.create_transaction(
            venue=hold.venue,
            amount=additional_amount,
            transaction_type='top_up',
            payment_method=hold.payment_method,
            pre_auth_hold=hold,
            guest_session=hold.guest_session,
        )
        cls.mark_transaction_success(transaction, hold.gateway_reference_id)

        # Send top-up confirmation
        if hold.guest_session and hold.guest_session.user:
            NotificationService.send_top_up_confirmation(hold, additional_amount, hold.guest_session.user)

        return hold, transaction

    # ---------- Deposit Calculation ----------

    @classmethod
    def calculate_deposit(cls, venue, total_amount):
        if venue.booking_deposit_type == 'percentage':
            deposit = total_amount * Decimal(venue.booking_deposit_amount / 100)
        else:
            deposit = Decimal(venue.booking_deposit_amount)
        return min(deposit, total_amount)

    # ---------- Refund ----------

    @classmethod
    def process_refund(cls, transaction, amount=None, reason=None):
        if transaction.transaction_status != 'success':
            raise ValidationError("Only successful transactions can be refunded.")

        refund_amount = amount or transaction.amount
        if refund_amount > transaction.amount:
            raise ValidationError("Refund amount exceeds transaction amount.")

        config = GatewayService.get_gateway_config(transaction.venue,
            'daraja' if transaction.payment_method == 'mpesa' else 'flutterwave')
        if transaction.payment_method == 'mpesa':
            response = GatewayService.mpesa_b2c(
                transaction.metadata.get('phone'),
                refund_amount,
                transaction.gateway_reference_id,
                config
            )
        else:
            response = GatewayService.flutterwave_refund(
                transaction.gateway_reference_id,
                refund_amount,
                config
            )

        if response['success']:
            refund = cls.create_transaction(
                venue=transaction.venue,
                amount=refund_amount,
                transaction_type='refund',
                payment_method=transaction.payment_method,
                guest_session=transaction.guest_session,
                user=transaction.user,
                metadata={'original_transaction': str(transaction.id), 'reason': reason}
            )
            cls.mark_transaction_success(refund, response['gateway_reference_id'])
            # Send refund notification
            if transaction.user:
                NotificationService.send_refund_processed(refund, transaction.user)
            return refund
        else:
            raise ValidationError("Refund failed.")
# notifications/services/notification_service.py

import logging
from django.core.mail import send_mail
from django.conf import settings
from django.template import Template, Context
from django.utils import timezone
from ..models import Notification, NotificationTemplate
import africastalking

logger = logging.getLogger(__name__)


class NotificationEngine:
    """
    Core notification engine that sends messages via email, SMS, or push.
    """

    @classmethod
    def send_notification(cls, notification):
        """
        Send a single notification based on its channel.
        """
        if notification.channel == 'email':
            return cls._send_email(notification)
        elif notification.channel == 'sms':
            return cls._send_sms(notification)
        elif notification.channel == 'push':
            return cls._send_push(notification)
        else:
            raise ValueError(f"Unsupported channel: {notification.channel}")

    @classmethod
    def _send_email(cls, notification):
        try:
            send_mail(
                subject=notification.subject,
                message=notification.body,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[notification.recipient_email],
                fail_silently=False,
            )
            notification.status = 'sent'
            notification.sent_at = timezone.now()
            notification.save()
            logger.info(f"Email sent to {notification.recipient_email}: {notification.subject}")
            return True
        except Exception as e:
            notification.status = 'failed'
            notification.error_message = str(e)
            notification.save()
            logger.error(f"Email failed: {e}")
            return False

    @classmethod
    def _send_sms(cls, notification):
        try:
            if not settings.AFRICASTALKING_USERNAME or not settings.AFRICASTALKING_API_KEY:
                logger.warning("SMS credentials not configured.")
                notification.status = 'failed'
                notification.error_message = "SMS credentials missing"
                notification.save()
                return False
            africastalking.initialize(settings.AFRICASTALKING_USERNAME, settings.AFRICASTALKING_API_KEY)
            sms = africastalking.SMS
            response = sms.send(notification.body, [notification.recipient_phone])
            notification.status = 'sent'
            notification.sent_at = timezone.now()
            notification.save()
            logger.info(f"SMS sent to {notification.recipient_phone}: {response}")
            return True
        except Exception as e:
            notification.status = 'failed'
            notification.error_message = str(e)
            notification.save()
            logger.error(f"SMS failed: {e}")
            return False

    @classmethod
    def _send_push(cls, notification):
        # Placeholder – integrate Firebase Cloud Messaging later
        logger.info(f"Push notification would be sent: {notification.body}")
        notification.status = 'sent'
        notification.sent_at = timezone.now()
        notification.save()
        return True


class NotificationService:
    """
    High-level service to create and send notifications from templates.
    """

    @classmethod
    def render_template(cls, template_name, context_data):
        try:
            template = NotificationTemplate.objects.get(name=template_name, is_active=True)
        except NotificationTemplate.DoesNotExist:
            logger.warning(f"Template {template_name} not found")
            return None, None

        body = Template(template.body_template).render(Context(context_data))
        subject = ''
        if template.subject:
            subject = Template(template.subject).render(Context(context_data))
        return subject, body

    @classmethod
    def create_notification(cls, venue, recipient_user, notification_type, channel, subject, body, metadata=None):
        notification = Notification.objects.create(
            venue=venue,
            recipient_user=recipient_user,
            recipient_email=recipient_user.email if recipient_user else None,
            recipient_phone=recipient_user.phone if recipient_user else None,
            notification_type=notification_type,
            channel=channel,
            subject=subject,
            body=body,
            metadata=metadata or {},
            status='pending',
        )
        return notification

    @classmethod
    def send_templated_notification(cls, template_name, context_data, recipient_user, venue=None, notification_type=None, channel='email', metadata=None):
        subject, body = cls.render_template(template_name, context_data)
        if not body:
            logger.error(f"Failed to render template {template_name}")
            return None

        if not notification_type:
            notification_type = template_name

        if channel == 'email' and not recipient_user.email:
            logger.warning(f"User {recipient_user.id} has no email")
            return None

        if channel == 'sms' and not recipient_user.phone:
            logger.warning(f"User {recipient_user.id} has no phone")
            return None

        notification = cls.create_notification(
            venue=venue or recipient_user.venue,
            recipient_user=recipient_user,
            notification_type=notification_type,
            channel=channel,
            subject=subject,
            body=body,
            metadata=metadata,
        )
        NotificationEngine.send_notification(notification)
        return notification

    # ---------- Existing Methods ----------
    @classmethod
    def send_booking_confirmation(cls, booking, user):
        context = {
            'booking_id': booking.id,
            'venue_name': booking.venue.business_name,
            'booking_date': booking.booking_date,
            'start_time': booking.start_time,
            'party_size': booking.party_size,
            'total_amount': booking.total_amount,
            'booking_qr': booking.booking_qr,
        }
        return cls.send_templated_notification(
            template_name='booking_confirmation',
            context_data=context,
            recipient_user=user,
            venue=booking.venue,
            notification_type='booking_confirmation',
            channel='email'
        )

    @classmethod
    def send_order_ready(cls, order, waiter_user):
        context = {
            'order_id': order.id,
            'table_number': order.table.table_number if order.table else 'Unknown',
            'items': [{'name': item.item_name, 'quantity': item.quantity} for item in order.items.all()],
            'venue_name': order.venue.business_name,
        }
        return cls.send_templated_notification(
            template_name='order_ready',
            context_data=context,
            recipient_user=waiter_user,
            venue=order.venue,
            notification_type='order_ready',
            channel='push'
        )

    @classmethod
    def send_no_show_alert(cls, manager_user, staff, shift):
        context = {
            'staff_name': staff.user.full_name,
            'shift_name': shift.shift_name,
            'start_time': shift.start_time,
            'venue_name': staff.venue.business_name,
        }
        return cls.send_templated_notification(
            template_name='no_show_alert',
            context_data=context,
            recipient_user=manager_user,
            venue=staff.venue,
            notification_type='no_show_alert',
            channel='email'
        )

    @classmethod
    def send_vip_arrived(cls, waiter_user, ticket, table):
        context = {
            'ticket_code': ticket.ticket_code,
            'customer_name': ticket.customer_name,
            'table_number': table.table_number,
            'venue_name': ticket.venue.business_name,
        }
        return cls.send_templated_notification(
            template_name='vip_arrived',
            context_data=context,
            recipient_user=waiter_user,
            venue=ticket.venue,
            notification_type='vip_arrived',
            channel='push'
        )

    # ---------- Payment Notifications ----------
    @classmethod
    def send_payment_success(cls, transaction, recipient_user):
        context = {
            'transaction_id': transaction.id,
            'amount': transaction.amount,
            'currency': transaction.currency,
            'transaction_type': transaction.transaction_type,
            'payment_method': transaction.payment_method,
            'venue_name': transaction.venue.business_name,
        }
        return cls.send_templated_notification(
            template_name='payment_success',
            context_data=context,
            recipient_user=recipient_user,
            venue=transaction.venue,
            notification_type='payment_success',
            channel='email'
        )

    @classmethod
    def send_payment_failed(cls, transaction, recipient_user, error_message):
        context = {
            'transaction_id': transaction.id,
            'amount': transaction.amount,
            'currency': transaction.currency,
            'transaction_type': transaction.transaction_type,
            'payment_method': transaction.payment_method,
            'error_message': error_message,
            'venue_name': transaction.venue.business_name,
        }
        return cls.send_templated_notification(
            template_name='payment_failed',
            context_data=context,
            recipient_user=recipient_user,
            venue=transaction.venue,
            notification_type='payment_failed',
            channel='email'
        )

    @classmethod
    def send_refund_processed(cls, refund_transaction, recipient_user):
        context = {
            'refund_id': refund_transaction.id,
            'amount': refund_transaction.amount,
            'currency': 'KES',
            'original_transaction_id': refund_transaction.original_transaction.id,
            'venue_name': refund_transaction.refund_request.venue.business_name,
        }
        return cls.send_templated_notification(
            template_name='refund_processed',
            context_data=context,
            recipient_user=recipient_user,
            venue=refund_transaction.refund_request.venue,
            notification_type='refund_processed',
            channel='email'
        )

    @classmethod
    def send_auto_capture_executed(cls, hold, recipient_user):
        context = {
            'hold_id': hold.id,
            'amount': hold.consumed_amount,
            'venue_name': hold.venue.business_name,
            'guest_session_id': hold.guest_session.id,
        }
        return cls.send_templated_notification(
            template_name='auto_capture_executed',
            context_data=context,
            recipient_user=recipient_user,
            venue=hold.venue,
            notification_type='auto_capture_executed',
            channel='email'
        )

    # ---------- Order Notifications ----------
    @classmethod
    def send_order_placed_guest(cls, order, guest_user):
        context = {
            'order_id': order.id,
            'table_number': order.table.table_number if order.table else 'Unknown',
            'items': [{'name': item.item_name, 'quantity': item.quantity} for item in order.items.all()],
            'total_amount': order.total_amount,
            'venue_name': order.venue.business_name,
        }
        return cls.send_templated_notification(
            template_name='order_placed_guest',
            context_data=context,
            recipient_user=guest_user,
            venue=order.venue,
            notification_type='order_placed_guest',
            channel='email'
        )

    @classmethod
    def send_order_cancelled(cls, order, recipient_user):
        context = {
            'order_id': order.id,
            'table_number': order.table.table_number if order.table else 'Unknown',
            'venue_name': order.venue.business_name,
        }
        return cls.send_templated_notification(
            template_name='order_cancelled',
            context_data=context,
            recipient_user=recipient_user,
            venue=order.venue,
            notification_type='order_cancelled',
            channel='email'
        )

    # ---------- Explore / Booking Notifications ----------
    @classmethod
    def send_booking_pending_payment(cls, booking, user):
        context = {
            'booking_id': booking.id,
            'venue_name': booking.venue.business_name,
            'booking_date': booking.booking_date,
            'start_time': booking.start_time,
            'party_size': booking.party_size,
            'total_amount': booking.total_amount,
            'deposit_amount': booking.paid_amount,
        }
        return cls.send_templated_notification(
            template_name='booking_pending_payment',
            context_data=context,
            recipient_user=user,
            venue=booking.venue,
            notification_type='booking_pending_payment',
            channel='email'
        )

    @classmethod
    def send_booking_cancelled(cls, booking, user):
        context = {
            'booking_id': booking.id,
            'venue_name': booking.venue.business_name,
            'booking_date': booking.booking_date,
            'start_time': booking.start_time,
            'party_size': booking.party_size,
        }
        return cls.send_templated_notification(
            template_name='booking_cancelled',
            context_data=context,
            recipient_user=user,
            venue=booking.venue,
            notification_type='booking_cancelled',
            channel='email'
        )

    @classmethod
    def send_booking_reminder(cls, booking, user):
        context = {
            'booking_id': booking.id,
            'venue_name': booking.venue.business_name,
            'booking_date': booking.booking_date,
            'start_time': booking.start_time,
            'party_size': booking.party_size,
            'booking_qr': booking.booking_qr,
        }
        return cls.send_templated_notification(
            template_name='booking_reminder',
            context_data=context,
            recipient_user=user,
            venue=booking.venue,
            notification_type='booking_reminder',
            channel='email'
        )

    @classmethod
    def send_check_in_confirmation(cls, booking, user):
        context = {
            'booking_id': booking.id,
            'venue_name': booking.venue.business_name,
            'booking_date': booking.booking_date,
            'start_time': booking.start_time,
            'party_size': booking.party_size,
        }
        return cls.send_templated_notification(
            template_name='check_in_confirmation',
            context_data=context,
            recipient_user=user,
            venue=booking.venue,
            notification_type='check_in_confirmation',
            channel='push'
        )

    @classmethod
    def send_check_out_confirmation(cls, booking, user):
        context = {
            'booking_id': booking.id,
            'venue_name': booking.venue.business_name,
            'booking_date': booking.booking_date,
        }
        return cls.send_templated_notification(
            template_name='check_out_confirmation',
            context_data=context,
            recipient_user=user,
            venue=booking.venue,
            notification_type='check_out_confirmation',
            channel='push'
        )

    # ---------- Staff Notifications ----------
    @classmethod
    def send_shift_reminder(cls, staff_user, shift):
        context = {
            'staff_name': staff_user.full_name,
            'shift_name': shift.shift_name,
            'start_time': shift.start_time,
            'end_time': shift.end_time,
            'venue_name': staff_user.venue.business_name,
        }
        return cls.send_templated_notification(
            template_name='shift_reminder',
            context_data=context,
            recipient_user=staff_user,
            venue=staff_user.venue,
            notification_type='shift_reminder',
            channel='sms'
        )

    @classmethod
    def send_staff_welcome(cls, staff_user, temp_password):
        context = {
            'staff_name': staff_user.full_name,
            'venue_name': staff_user.venue.business_name,
            'temp_password': temp_password,
            'login_url': settings.FRONTEND_URL,
        }
        return cls.send_templated_notification(
            template_name='staff_welcome',
            context_data=context,
            recipient_user=staff_user,
            venue=staff_user.venue,
            notification_type='staff_welcome',
            channel='email'
        )

    @classmethod
    def send_pin_set(cls, staff_user):
        context = {
            'staff_name': staff_user.full_name,
            'venue_name': staff_user.venue.business_name,
        }
        return cls.send_templated_notification(
            template_name='pin_set',
            context_data=context,
            recipient_user=staff_user,
            venue=staff_user.venue,
            notification_type='pin_set',
            channel='email'
        )

    @classmethod
    def send_cash_reconciled(cls, staff_user, amount):
        context = {
            'staff_name': staff_user.full_name,
            'amount': amount,
            'venue_name': staff_user.venue.business_name,
        }
        return cls.send_templated_notification(
            template_name='cash_reconciled',
            context_data=context,
            recipient_user=staff_user,
            venue=staff_user.venue,
            notification_type='cash_reconciled',
            channel='push'
        )

    # ---------- Event Notifications ----------
    @classmethod
    def send_event_reminder(cls, ticket, user):
        context = {
            'event_name': ticket.event.event_name,
            'event_date': ticket.event.event_date,
            'venue_name': ticket.venue.business_name,
            'ticket_code': ticket.ticket_code,
        }
        return cls.send_templated_notification(
            template_name='event_reminder',
            context_data=context,
            recipient_user=user,
            venue=ticket.venue,
            notification_type='event_reminder',
            channel='email'
        )

    @classmethod
    def send_ticket_refunded(cls, ticket, user):
        context = {
            'ticket_code': ticket.ticket_code,
            'event_name': ticket.event.event_name,
            'venue_name': ticket.venue.business_name,
            'refund_amount': ticket.price,
        }
        return cls.send_templated_notification(
            template_name='ticket_refunded',
            context_data=context,
            recipient_user=user,
            venue=ticket.venue,
            notification_type='ticket_refunded',
            channel='email'
        )

    @classmethod
    def send_event_sold_out(cls, event, manager_user):
        context = {
            'event_name': event.event_name,
            'event_date': event.event_date,
            'venue_name': event.venue.business_name,
            'total_tickets_sold': event.total_tickets_sold,
            'max_capacity': event.max_capacity,
        }
        return cls.send_templated_notification(
            template_name='event_sold_out',
            context_data=context,
            recipient_user=manager_user,
            venue=event.venue,
            notification_type='event_sold_out',
            channel='email'
        )

    # ---------- Venue/Onboarding Notifications ----------
    @classmethod
    def send_document_verified(cls, venue, manager_user):
        context = {
            'venue_name': venue.business_name,
            'control_url': f"{settings.FRONTEND_URL}/control/{venue.sub_domain}",
        }
        return cls.send_templated_notification(
            template_name='document_verified',
            context_data=context,
            recipient_user=manager_user,
            venue=venue,
            notification_type='document_verified',
            channel='email'
        )

    @classmethod
    def send_document_rejected(cls, venue, manager_user, reason):
        context = {
            'venue_name': venue.business_name,
            'reason': reason,
        }
        return cls.send_templated_notification(
            template_name='document_rejected',
            context_data=context,
            recipient_user=manager_user,
            venue=venue,
            notification_type='document_rejected',
            channel='email'
        )

    @classmethod
    def send_venue_suspended(cls, venue, manager_user):
        context = {
            'venue_name': venue.business_name,
        }
        return cls.send_templated_notification(
            template_name='venue_suspended',
            context_data=context,
            recipient_user=manager_user,
            venue=venue,
            notification_type='venue_suspended',
            channel='email'
        )

    @classmethod
    def send_venue_reactivated(cls, venue, manager_user):
        context = {
            'venue_name': venue.business_name,
        }
        return cls.send_templated_notification(
            template_name='venue_reactivated',
            context_data=context,
            recipient_user=manager_user,
            venue=venue,
            notification_type='venue_reactivated',
            channel='email'
        )

    @classmethod
    def send_subscription_expiry(cls, venue, manager_user, days_remaining):
        context = {
            'venue_name': venue.business_name,
            'days_remaining': days_remaining,
            'billing_cycle_start': venue.billing_cycle_start,
            'subscription_tier': venue.subscription_tier,
        }
        return cls.send_templated_notification(
            template_name='subscription_expiry',
            context_data=context,
            recipient_user=manager_user,
            venue=venue,
            notification_type='subscription_expiry',
            channel='email'
        )

    @classmethod
    def send_subscription_payment_failed(cls, venue, manager_user, error_message):
        context = {
            'venue_name': venue.business_name,
            'error_message': error_message,
        }
        return cls.send_templated_notification(
            template_name='subscription_payment_failed',
            context_data=context,
            recipient_user=manager_user,
            venue=venue,
            notification_type='subscription_payment_failed',
            channel='email'
        )

    # ---------- Host Mode Notifications ----------
    @classmethod
    def send_budget_depletion(cls, hold, host_user):
        context = {
            'remaining_balance': hold.remaining_balance,
            'declared_amount': hold.declared_amount,
            'venue_name': hold.venue.business_name,
            'guest_session_id': hold.guest_session.id,
        }
        return cls.send_templated_notification(
            template_name='budget_depletion',
            context_data=context,
            recipient_user=host_user,
            venue=hold.venue,
            notification_type='budget_depletion',
            channel='push'
        )

    @classmethod
    def send_top_up_confirmation(cls, hold, top_up_amount, host_user):
        context = {
            'top_up_amount': top_up_amount,
            'new_balance': hold.remaining_balance,
            'venue_name': hold.venue.business_name,
        }
        return cls.send_templated_notification(
            template_name='top_up_confirmation',
            context_data=context,
            recipient_user=host_user,
            venue=hold.venue,
            notification_type='top_up_confirmation',
            channel='push'
        )

    # ---------- System/Admin Notifications ----------
    @classmethod
    def send_system_health_alert(cls, service_name, status, message):
        from users.models import User
        admins = User.objects.filter(is_superuser=True)
        for admin in admins:
            context = {
                'service_name': service_name,
                'status': status,
                'message': message,
            }
            cls.send_templated_notification(
                template_name='system_health_alert',
                context_data=context,
                recipient_user=admin,
                venue=None,
                notification_type='system_health_alert',
                channel='email'
            )

    @classmethod
    def send_new_venue_registration(cls, venue, manager_user):
        from users.models import User
        admins = User.objects.filter(user_type='admin')
        for admin in admins:
            context = {
                'venue_name': venue.business_name,
                'venue_subdomain': venue.sub_domain,
                'manager_email': manager_user.email,
                'manager_phone': manager_user.phone,
                'registration_date': venue.created_at,
            }
            cls.send_templated_notification(
                template_name='new_venue_registration',
                context_data=context,
                recipient_user=admin,
                venue=venue,
                notification_type='new_venue_registration',
                channel='email'
            )

    @classmethod
    def send_sms_credits_low(cls, venue, remaining_credits):
        manager_user = venue.owner
        if manager_user:
            context = {
                'venue_name': venue.business_name,
                'remaining_credits': remaining_credits,
                'threshold': settings.SMS_CREDITS_THRESHOLD,
            }
            cls.send_templated_notification(
                template_name='sms_credits_low',
                context_data=context,
                recipient_user=manager_user,
                venue=venue,
                notification_type='sms_credits_low',
                channel='email'
            )

    # =========================================================================
    # NEW: Refund Notifications
    # =========================================================================

    @classmethod
    def send_refund_requested(cls, refund_request, recipient_user):
        context = {
            'refund_request_id': refund_request.id,
            'booking_id': refund_request.booking.id,
            'venue_name': refund_request.venue.business_name,
            'requested_amount': refund_request.requested_amount,
            'reason': refund_request.get_reason_display(),
            'classification': refund_request.get_classification_display(),
            'status': refund_request.get_status_display(),
        }
        return cls.send_templated_notification(
            template_name='refund_requested',
            context_data=context,
            recipient_user=recipient_user,
            venue=refund_request.venue,
            notification_type='refund_requested',
            channel='email'
        )

    @classmethod
    def send_refund_approved(cls, refund_request, recipient_user):
        context = {
            'refund_request_id': refund_request.id,
            'booking_id': refund_request.booking.id,
            'venue_name': refund_request.venue.business_name,
            'approved_amount': refund_request.approved_amount,
            'requested_amount': refund_request.requested_amount,
            'resolution_notes': refund_request.resolution_notes,
        }
        return cls.send_templated_notification(
            template_name='refund_approved',
            context_data=context,
            recipient_user=recipient_user,
            venue=refund_request.venue,
            notification_type='refund_approved',
            channel='email'
        )

    @classmethod
    def send_refund_rejected(cls, refund_request, recipient_user):
        context = {
            'refund_request_id': refund_request.id,
            'booking_id': refund_request.booking.id,
            'venue_name': refund_request.venue.business_name,
            'requested_amount': refund_request.requested_amount,
            'resolution_notes': refund_request.resolution_notes,
        }
        return cls.send_templated_notification(
            template_name='refund_rejected',
            context_data=context,
            recipient_user=recipient_user,
            venue=refund_request.venue,
            notification_type='refund_rejected',
            channel='email'
        )

    @classmethod
    def send_refund_processed(cls, refund_transaction, recipient_user):
        context = {
            'refund_transaction_id': refund_transaction.id,
            'refund_request_id': refund_transaction.refund_request.id,
            'booking_id': refund_transaction.refund_request.booking.id,
            'venue_name': refund_transaction.refund_request.venue.business_name,
            'amount': refund_transaction.amount,
            'gateway_reference_id': refund_transaction.gateway_reference_id,
            'processed_at': refund_transaction.processed_at,
        }
        return cls.send_templated_notification(
            template_name='refund_processed',
            context_data=context,
            recipient_user=recipient_user,
            venue=refund_transaction.refund_request.venue,
            notification_type='refund_processed',
            channel='email'
        )

    # =========================================================================
    # NEW: Trial Subscription Notifications
    # =========================================================================

    @classmethod
    def send_trial_will_end_soon(cls, venue, recipient_user, days_remaining):
        context = {
            'venue_name': venue.business_name,
            'days_remaining': days_remaining,
            'next_billing_date': venue.next_billing_date,
            'subscription_tier': venue.get_subscription_tier_display(),
            'control_url': f"{settings.FRONTEND_URL}/control/{venue.sub_domain}",
        }
        return cls.send_templated_notification(
            template_name='trial_will_end_soon',
            context_data=context,
            recipient_user=recipient_user,
            venue=venue,
            notification_type='trial_will_end_soon',
            channel='email'
        )

    @classmethod
    def send_trial_ended(cls, venue, recipient_user, paid=True):
        context = {
            'venue_name': venue.business_name,
            'paid': paid,
            'next_billing_date': venue.next_billing_date,
            'subscription_tier': venue.get_subscription_tier_display(),
            'control_url': f"{settings.FRONTEND_URL}/control/{venue.sub_domain}",
            'support_email': settings.DEFAULT_FROM_EMAIL,
        }
        if paid:
            template_name = 'trial_ended_paid'
        else:
            template_name = 'trial_ended_suspended'

        return cls.send_templated_notification(
            template_name=template_name,
            context_data=context,
            recipient_user=recipient_user,
            venue=venue,
            notification_type='trial_ended',
            channel='email'
        )
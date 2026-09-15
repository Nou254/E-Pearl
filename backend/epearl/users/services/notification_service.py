# users/services/notification_service.py

from django.core.mail import send_mail
from django.conf import settings
import logging
import africastalking

logger = logging.getLogger(__name__)


class NotificationService:
    @staticmethod
    def _initialize_africastalking():
        """Initialize Africa's Talking SDK"""
        username = settings.AFRICASTALKING_USERNAME
        api_key = settings.AFRICASTALKING_API_KEY
        if username and api_key:
            africastalking.initialize(username, api_key)
            return True
        return False

    @staticmethod
    def send_email(to_email, subject, message, html_message=None):
        """Send email using Django's SMTP backend."""
        try:
            if not settings.EMAIL_HOST_USER or not settings.EMAIL_HOST_PASSWORD:
                logger.warning("Email credentials not configured. Email not sent.")
                return None

            send_mail(
                subject=subject,
                message=message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[to_email],
                html_message=html_message or message,
                fail_silently=False,
            )
            logger.info(f"Email sent to {to_email}: {subject}")
            return True
        except Exception as e:
            logger.error(f"Failed to send email to {to_email}: {e}")
            return None

    @staticmethod
    def send_sms(phone_number, message):
        """Send SMS via Africa's Talking"""
        try:
            if not NotificationService._initialize_africastalking():
                logger.warning("Africa's Talking credentials not set. SMS not sent.")
                return None

            sms = africastalking.SMS
            response = sms.send(message, [phone_number])
            logger.info(f"SMS sent to {phone_number}: {response}")
            return response
        except Exception as e:
            logger.error(f"Failed to send SMS to {phone_number}: {e}")
            return None

    @staticmethod
    def send_otp_via_email(email, otp_code, otp_type):
        """Send OTP via email."""
        subject = f"E-Pearl {otp_type.replace('_', ' ').title()} OTP"
        message = f"Your {otp_type} OTP is: {otp_code}\n\nThis OTP expires in 5 minutes."
        html_message = f"""
        <html>
        <body>
            <h2>E-Pearl OTP</h2>
            <p>Your {otp_type} OTP is:</p>
            <h1 style="font-size: 32px; letter-spacing: 4px;">{otp_code}</h1>
            <p>This OTP expires in <strong>5 minutes</strong>.</p>
            <p>If you did not request this, please ignore this email.</p>
        </body>
        </html>
        """
        return NotificationService.send_email(email, subject, message, html_message)

    @staticmethod
    def send_otp_via_sms(phone, otp_code, otp_type):
        """Send OTP via SMS."""
        message = f"E-Pearl {otp_type} OTP: {otp_code}. Valid for 5 minutes."
        return NotificationService.send_sms(phone, message)

    @staticmethod
    def send_admin_login_link(email, login_url, expiry_minutes=20):
        """Send admin login link via email."""
        subject = "E-Pearl Admin Login Link"
        message = f"""
        Click the link below to log in to E-Pearl HQ.
        This link expires in {expiry_minutes} minutes and can only be used once.

        {login_url}

        If you did not request this, please ignore this email.
        """
        html_message = f"""
        <html>
        <body>
            <h2>E-Pearl Admin Login</h2>
            <p>Click the button below to log in:</p>
            <p><a href="{login_url}" style="display: inline-block; padding: 12px 24px; background: #1a56db; color: white; text-decoration: none; border-radius: 6px;">Log In to HQ</a></p>
            <p>This link expires in <strong>{expiry_minutes} minutes</strong> and can only be used once.</p>
            <p>If you did not request this, please ignore this email.</p>
        </body>
        </html>
        """
        return NotificationService.send_email(email, subject, message, html_message)

    @staticmethod
    def send_password_reset_email(email, otp_code):
        """Send password reset OTP via email."""
        return NotificationService.send_otp_via_email(email, otp_code, 'password_reset')

    @staticmethod
    def send_password_reset_sms(phone, otp_code):
        """Send password reset OTP via SMS."""
        return NotificationService.send_otp_via_sms(phone, otp_code, 'password_reset')

    @staticmethod
    def mask_identifier(identifier):
        """Mask email or phone for display."""
        if '@' in identifier:
            local, domain = identifier.split('@')
            masked_local = local[:4] + '*****' if len(local) > 4 else '*****'
            return f"{masked_local}@{domain}"
        else:
            if len(identifier) > 6:
                return identifier[:6] + '***' + identifier[-2:]
            return identifier
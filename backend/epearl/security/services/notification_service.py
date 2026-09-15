from django.core.mail import send_mail
from django.conf import settings
from django.template.loader import render_to_string
from venues.models import Venue
from users.models import User
import africastalking

# Initialize Africa's Talking (if configured)
africastalking.initialize(
    username=settings.AFRICASTALKING_USERNAME,
    api_key=settings.AFRICASTALKING_API_KEY
)
sms = africastalking.SMS


class SecurityNotificationService:
    @classmethod
    def notify_admin(cls, event):
        """
        Send SMS and email to the admin(s) about a security event.
        """
        # Determine recipients – you can configure a list of admin emails/phones
        admin_emails = getattr(settings, 'SECURITY_ADMIN_EMAILS', ['admin@epearl.co.ke'])
        admin_phones = getattr(settings, 'SECURITY_ADMIN_PHONES', ['+2547XXXXXXXX'])

        # Build context
        context = {
            'event': event,
            'ip': event.ip_address,
            'endpoint': event.endpoint,
            'method': event.method,
            'rule_type': event.rule_type,
            'severity': event.severity,
            'user': event.user.email if event.user else 'Anonymous',
            'venue': event.venue.business_name if event.venue else 'N/A',
            'timestamp': event.timestamp.strftime('%Y-%m-%d %H:%M:%S UTC'),
        }

        # Email subject and message
        subject = f"[E-Pearl Security] {event.severity.upper()} - {event.rule_type} attack blocked"
        html_body = render_to_string('security/alert_email.html', context)
        plain_body = f"""
E-Pearl Security Alert

Severity: {event.severity.upper()}
Time: {context['timestamp']}
IP: {event.ip_address}
Endpoint: {event.method} {event.endpoint}
Rule: {event.rule_type}
User: {context['user']}
Venue: {context['venue']}

Full details available in the admin dashboard.
"""

        # Send email
        try:
            send_mail(
                subject=subject,
                message=plain_body,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=admin_emails,
                html_message=html_body,
                fail_silently=False,
            )
        except Exception as e:
            # Log email failure
            import logging
            logging.getLogger(__name__).error(f"Failed to send security alert email: {e}")

        # Send SMS – only for Critical/High severity (to avoid SMS spam)
        if event.severity in ['critical', 'high']:
            try:
                sms_message = f"E-Pearl SECURITY: {event.severity.upper()} - {event.rule_type} blocked from {event.ip_address} on {event.endpoint}. Check dashboard."
                for phone in admin_phones:
                    sms.send(sms_message, [phone])
            except Exception as e:
                import logging
                logging.getLogger(__name__).error(f"Failed to send security alert SMS: {e}")
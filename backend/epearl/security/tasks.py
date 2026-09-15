from celery import shared_task
from .models import SecurityEvent, SecurityRule
from django.utils import timezone
from venues.models import Venue
from users.models import User
from .services.notification_service import SecurityNotificationService  # new import


@shared_task
def log_security_event(user_id, venue_id, ip_address, endpoint, method,
                       request_headers, request_body, rule_id, rule_type,
                       severity, user_agent, geo_country):
    """
    Asynchronously create a SecurityEvent record and notify admin.
    """
    user = User.objects.filter(id=user_id).first() if user_id else None
    venue = Venue.objects.filter(id=venue_id).first() if venue_id else None
    rule = SecurityRule.objects.filter(id=rule_id).first() if rule_id else None

    safe_headers = {k: v for k, v in request_headers.items()
                    if k.lower() not in ['authorization', 'cookie']}

    event = SecurityEvent.objects.create(
        user=user,
        venue=venue,
        ip_address=ip_address,
        endpoint=endpoint,
        method=method,
        request_headers=safe_headers,
        request_body=request_body,
        rule=rule,
        rule_type=rule_type,
        severity=severity,
        user_agent=user_agent,
        geo_country=geo_country,
    )

    if rule:
        rule.trigger_count += 1
        rule.last_triggered_at = timezone.now()
        rule.save(update_fields=['trigger_count', 'last_triggered_at'])

    # Send notifications – this will send email always, SMS for critical/high
    SecurityNotificationService.notify_admin(event)

    return event.id
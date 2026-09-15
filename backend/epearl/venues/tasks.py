# venues/tasks.py

from celery import shared_task
from django.core.mail import send_mail
from django.conf import settings
from django.template.loader import render_to_string
from django.contrib.auth.tokens import default_token_generator
from django.utils import timezone
from .models import Venue
from .services.ocr_service import OCRService
from users.models import User
from notifications.services.notification_service import NotificationService
import logging

logger = logging.getLogger(__name__)


@shared_task
def process_document_verification(venue_id, document_path):
    """
    Asynchronous task to process document OCR and send owner invitation.
    """
    try:
        venue = Venue.objects.get(id=venue_id)
    except Venue.DoesNotExist:
        logger.error(f"Venue {venue_id} not found")
        return

    # Perform OCR extraction
    success, data, error = OCRService.verify_and_extract(document_path)
    if not success:
        logger.error(f"OCR failed for venue {venue_id}: {error}")
        venue.document_verification_status = 'rejected'
        venue.save(update_fields=['document_verification_status'])
        # Notify HQ admin about failure
        NotificationService.send_ocr_failure(venue, error)
        return

    # Update venue with extracted details
    venue.legal_owner_name = data.get('owner_name')
    venue.legal_owner_email = data.get('owner_email')
    venue.legal_owner_phone = data.get('owner_phone')
    venue.owner_invitation_sent_at = timezone.now()
    venue.save(update_fields=[
        'legal_owner_name', 'legal_owner_email', 'legal_owner_phone',
        'owner_invitation_sent_at'
    ])

    # Create or update owner user account
    user, created = User.objects.get_or_create(
        email=data.get('owner_email'),
        defaults={
            'full_name': data.get('owner_name'),
            'phone': data.get('owner_phone'),
            'user_type': 'owner',
            'venue': venue,
            'is_active': False,  # Needs verification
        }
    )

    if created:
        # Generate verification token
        token = default_token_generator.make_token(user)
        venue.owner_invitation_token = token
        venue.save(update_fields=['owner_invitation_token'])

        # Send invitation email
        invite_url = f"{settings.FRONTEND_URL}/verify-owner/{venue.id}/{token}"
        context = {
            'user': user,
            'invite_url': invite_url,
            'venue': venue,
            'owner_name': data.get('owner_name')
        }
        html_body = render_to_string('venues/owner_invitation_email.html', context)
        plain_body = f"""
Dear {data.get('owner_name')},

You have been registered as the legal owner of {venue.business_name} on the E-Pearl platform.

Please verify your ownership by clicking the link below:
{invite_url}

If you did not register this venue, please ignore this email.

Thank you,
E-Pearl Team
"""
        send_mail(
            subject=f"Verify your ownership of {venue.business_name}",
            message=plain_body,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            html_message=html_body,
            fail_silently=False,
        )
        logger.info(f"Owner invitation sent to {user.email} for venue {venue.business_name}")
    else:
        # User already exists – send reminder
        logger.info(f"Owner user already exists for {venue.business_name}, skipping invitation")


@shared_task
def send_owner_invitation_reminder(venue_id):
    """
    Reminder task for owner invitations that haven't been verified after 7 days.
    """
    venue = Venue.objects.get(id=venue_id)
    if venue.owner_verified_at is None and venue.owner_invitation_sent_at:
        # Check if more than 7 days ago
        delta = timezone.now() - venue.owner_invitation_sent_at
        if delta.days >= 7:
            # Send reminder
            user = User.objects.filter(email=venue.legal_owner_email).first()
            if user:
                token = venue.owner_invitation_token
                invite_url = f"{settings.FRONTEND_URL}/verify-owner/{venue.id}/{token}"
                send_mail(
                    subject=f"Reminder: Verify your ownership of {venue.business_name}",
                    message=f"Please click the link to verify: {invite_url}",
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[user.email],
                    fail_silently=True,
                )
                logger.info(f"Owner invitation reminder sent to {user.email}")
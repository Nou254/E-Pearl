# venues/services/verification_service.py

from django.conf import settings
from users.services.notification_service import NotificationService

class VerificationService:
    @staticmethod
    def approve_venue(venue, admin_user=None):
        """
        Verify the venue's documents, activate subscription, and send the venue URL.
        """
        if venue.document_verification_status == 'verified':
            raise ValueError("Documents already verified.")

        venue.document_verification_status = 'verified'
        venue.subscription_status = 'active'
        venue.save(update_fields=['document_verification_status', 'subscription_status'])

        # Send venue URL to manager
        venue_url = f"{settings.FRONTEND_URL}/control/{venue.sub_domain}"
        subject = f"Your E-Pearl Venue '{venue.business_name}' is Now Active!"
        message = f"""
        Congratulations! Your venue has been verified and is now active.
        You can access your management dashboard at:
        {venue_url}

        Please log in using your manager credentials.
        """
        NotificationService.send_email(venue.contact_email, subject, message)

        return {'venue_url': venue_url}

    @staticmethod
    def reject_venue(venue, reason, admin_user=None):
        """
        Reject the venue's documents, cancel subscription, and send rejection email.
        """
        if venue.document_verification_status == 'rejected':
            raise ValueError("Documents already rejected.")

        venue.document_verification_status = 'rejected'
        venue.subscription_status = 'cancelled'
        venue.save(update_fields=['document_verification_status', 'subscription_status'])

        # Send rejection email
        subject = f"E-Pearl Venue Verification Failed: {venue.business_name}"
        message = f"""
        Your venue "{venue.business_name}" verification was rejected.
        Reason: {reason}

        Please correct the issues and resubmit your documents.
        """
        NotificationService.send_email(venue.contact_email, subject, message)

        return {'message': 'Rejection email sent.'}
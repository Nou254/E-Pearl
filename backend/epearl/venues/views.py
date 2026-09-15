# venues/views.py

from rest_framework import viewsets, permissions, status, filters, parsers
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.decorators import action
from rest_framework.response import Response
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.contrib.auth.tokens import default_token_generator
from django.conf import settings
from datetime import timedelta
from .models import Venue, VenueRefundPolicy
from .serializers import (
    VenueSerializer,
    VenueRegistrationSerializer,
    VenueUpdateSerializer,
    VenueRefundPolicySerializer,
    VenueRefundPolicyUpdateSerializer,
    VenueTrialStatusSerializer,
)
from .services import VenueService, DocumentService, VerificationService
from .services.ocr_service import OCRService
from .tasks import process_document_verification
from notifications.services.notification_service import NotificationService
from users.models import User


class VenueViewSet(viewsets.ModelViewSet):
    queryset = Venue.objects.all().order_by('-created_at')
    serializer_class = VenueSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['subscription_tier', 'subscription_status', 'document_verification_status']
    search_fields = ['business_name', 'registration_number', 'contact_phone']
    ordering_fields = ['created_at', 'business_name']

    def get_serializer_class(self):
        if self.action == 'register':
            return VenueRegistrationSerializer
        elif self.action in ['update', 'partial_update']:
            return VenueUpdateSerializer
        return VenueSerializer

    # ---------- Phase 1: Initial Registration (with trial start) ----------
    @action(detail=False, methods=['post'], permission_classes=[permissions.IsAuthenticated])
    def register(self, request):
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            # Use VenueService to create venue, which now starts trial
            venue = VenueService.create_venue(serializer.validated_data)
            # Create default refund policy
            VenueRefundPolicy.objects.get_or_create(venue=venue)
            NotificationService.send_new_venue_registration(venue, request.user)
            return Response(
                VenueSerializer(venue).data,
                status=status.HTTP_201_CREATED
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    # ---------- Phase 2: Document Upload (unchanged) ----------
    @action(detail=True, methods=['post'], permission_classes=[permissions.IsAuthenticated],
            parser_classes=[parsers.MultiPartParser, parsers.FormParser])
    def upload_document(self, request, pk=None):
        venue = self.get_object()
        document_type = request.data.get('document_type')
        uploaded_file = request.FILES.get('file')

        if not document_type or not uploaded_file:
            return Response(
                {'error': 'document_type and file are required.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        allowed_types = ['kra_pin', 'business_permit', 'certificate_of_incorporation']
        if document_type not in allowed_types:
            return Response(
                {'error': f'document_type must be one of {allowed_types}'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            saved_path = DocumentService.upload_document(venue, document_type, uploaded_file)
            if document_type == 'kra_pin':
                process_document_verification.delay(venue.id, saved_path)
            return Response({
                'message': f'Document {document_type} uploaded successfully.',
                'file_path': saved_path,
                'processing': document_type == 'kra_pin'
            })
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

    # ---------- Phase 3: HQ Verification (unchanged) ----------
    @action(detail=True, methods=['post'], permission_classes=[permissions.IsAdminUser])
    def verify_documents(self, request, pk=None):
        venue = self.get_object()
        try:
            result = VerificationService.approve_venue(venue)
            NotificationService.send_document_verified(venue, venue.owner)
            return Response(result, status=status.HTTP_200_OK)
        except ValueError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'], permission_classes=[permissions.IsAdminUser])
    def reject_documents(self, request, pk=None):
        venue = self.get_object()
        reason = request.data.get('reason', 'Documents did not meet our verification requirements.')
        try:
            result = VerificationService.reject_venue(venue, reason)
            NotificationService.send_document_rejected(venue, venue.owner, reason)
            return Response(result, status=status.HTTP_200_OK)
        except ValueError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

    # ---------- Phase 4: Owner Verification (unchanged) ----------
    @action(detail=True, methods=['post'], permission_classes=[permissions.AllowAny])
    def verify_owner(self, request, pk=None):
        venue = self.get_object()
        token = request.data.get('token')
        if not token:
            return Response({'error': 'Token required.'}, status=status.HTTP_400_BAD_REQUEST)
        if venue.owner_invitation_token != token:
            return Response({'error': 'Invalid token.'}, status=status.HTTP_400_BAD_REQUEST)
        venue.owner_verified_at = timezone.now()
        venue.document_verification_status = 'verified'
        venue.save(update_fields=['owner_verified_at', 'document_verification_status'])
        if venue.legal_owner_email:
            try:
                user = User.objects.get(email=venue.legal_owner_email)
                user.is_active = True
                user.save(update_fields=['is_active'])
            except User.DoesNotExist:
                pass
        return Response({'status': 'owner verified'})

    # ---------- Admin Actions (unchanged) ----------
    @action(detail=True, methods=['post'], permission_classes=[permissions.IsAdminUser])
    def suspend(self, request, pk=None):
        venue = self.get_object()
        venue.subscription_status = 'suspended'
        venue.save(update_fields=['subscription_status'])
        NotificationService.send_venue_suspended(venue, venue.owner)
        return Response({'status': 'venue suspended'})

    @action(detail=True, methods=['post'], permission_classes=[permissions.IsAdminUser])
    def reactivate(self, request, pk=None):
        venue = self.get_object()
        venue.subscription_status = 'active'
        venue.save(update_fields=['subscription_status'])
        NotificationService.send_venue_reactivated(venue, venue.owner)
        return Response({'status': 'venue reactivated'})

    # ---------- NEW: Trial Status ----------
    @action(detail=True, methods=['get'], permission_classes=[permissions.IsAuthenticated])
    def trial_status(self, request, pk=None):
        venue = self.get_object()
        trial_days_total = getattr(settings, 'TRIAL_PERIOD_DAYS', 14)
        trial_days_remaining = 0
        if venue.trial_start_date:
            days_used = (timezone.now().date() - venue.trial_start_date).days
            trial_days_remaining = max(0, trial_days_total - days_used)
        data = {
            'trial_days_remaining': trial_days_remaining,
            'trial_days_total': trial_days_total,
            'status': venue.subscription_status,
            'trial_start_date': venue.trial_start_date,
            'next_billing_date': venue.next_billing_date,
        }
        serializer = VenueTrialStatusSerializer(data)
        return Response(serializer.data)


# ========== NEW: Refund Policy ViewSet ==========

class VenueRefundPolicyViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing venue refund policies (Control).
    """
    serializer_class = VenueRefundPolicySerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.user_type in ['admin', 'support']:
            return VenueRefundPolicy.objects.all()
        if user.venue:
            return VenueRefundPolicy.objects.filter(venue=user.venue)
        return VenueRefundPolicy.objects.none()

    def get_serializer_class(self):
        if self.action in ['update', 'partial_update', 'create']:
            return VenueRefundPolicyUpdateSerializer
        return VenueRefundPolicySerializer

    def perform_create(self, serializer):
        user = self.request.user
        if not user.venue:
            raise PermissionError("You are not associated with a venue.")
        # Ensure only one policy per venue
        if VenueRefundPolicy.objects.filter(venue=user.venue).exists():
            raise ValidationError("Refund policy already exists for this venue.")
        serializer.save(venue=user.venue)

    def perform_update(self, serializer):
        user = self.request.user
        if not user.venue:
            raise PermissionError("You are not associated with a venue.")
        instance = self.get_object()
        if instance.venue != user.venue and not user.user_type in ['admin', 'support']:
            raise PermissionError("You can only update your own venue's policy.")
        serializer.save()
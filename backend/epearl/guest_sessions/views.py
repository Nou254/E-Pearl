# guest_sessions/views.py

from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from django.core.exceptions import ValidationError
from .models import GuestSession
from .serializers import GuestSessionSerializer, GuestSessionCreateSerializer
from .services.settlement_service import SettlementService


class GuestSessionViewSet(viewsets.GenericViewSet):
    queryset = GuestSession.objects.all()
    serializer_class = GuestSessionSerializer
    permission_classes = [permissions.AllowAny]

    def get_serializer_class(self):
        if self.action == 'create':
            return GuestSessionCreateSerializer
        return GuestSessionSerializer

    def create(self, request):
        """
        Create a new guest session for the given venue.
        If user is authenticated, associate the session with the user.
        """
        serializer = self.get_serializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            session = serializer.save()
            return Response(
                GuestSessionSerializer(session).data,
                status=status.HTTP_201_CREATED
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['get'])
    def me(self, request):
        """
        Get the current active session for the authenticated user.
        If anonymous, look up by device_fingerprint or ip.
        """
        if request.user.is_authenticated:
            session = GuestSession.objects.filter(
                user=request.user,
                status='active'
            ).order_by('-start_time').first()
            if session:
                return Response(GuestSessionSerializer(session).data)
            return Response({'detail': 'No active session found.'}, status=404)

        fingerprint = request.query_params.get('device_fingerprint')
        if fingerprint:
            session = GuestSession.objects.filter(
                device_fingerprint=fingerprint,
                status='active'
            ).order_by('-start_time').first()
            if session:
                return Response(GuestSessionSerializer(session).data)
        return Response({'detail': 'No active session found.'}, status=404)

    @action(detail=True, methods=['post'])
    def expire(self, request, pk=None):
        """
        Manually expire a session.
        Validates hybrid settlement before allowing expiration.
        """
        session = self.get_object()
        if session.status != 'active':
            return Response({'error': 'Session already expired.'}, status=400)

        # Validate hybrid settlement (host + self‑pay)
        try:
            valid, error = SettlementService.validate_hybrid_settlement(session)
            if not valid:
                return Response({'error': error}, status=400)
        except ValidationError as e:
            return Response({'error': str(e)}, status=400)

        # Mark session as settled if not already
        if not session.is_settled:
            session.mark_settled()

        # Expire the session
        session.expire()
        return Response({'status': 'session expired'})

    @action(detail=True, methods=['get'])
    def settlement_status(self, request, pk=None):
        """
        Get detailed settlement status for the session's table.
        """
        session = self.get_object()
        try:
            status_data = SettlementService.get_settlement_status(session)
            return Response(status_data)
        except ValidationError as e:
            return Response({'error': str(e)}, status=400)
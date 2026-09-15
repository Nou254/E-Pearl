# users/views.py

from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.token_blacklist.models import OutstandingToken, BlacklistedToken
from django.contrib.auth import authenticate
from django.utils import timezone
import pyotp

from .models import User
from .serializers import (
    UserSerializer,
    RegisterCustomerSerializer,
    StaffLoginSerializer,
    ManagerLoginSerializer,
    AdminLoginRequestSerializer,
    AdminLoginConfirmSerializer,
    OTPRequestSerializer,
    OTPVerifySerializer,
    PasswordResetRequestSerializer,
    PasswordResetConfirmSerializer,
    StaffPINSetSerializer,
    StaffPINChangeSerializer,
    StaffPINResetRequestSerializer,
    StaffPINResetConfirmSerializer,
    TwoFASetupSerializer,
    TwoFAVerifySerializer,
    TwoFADisableSerializer,
    PasswordChangeSerializer,
    PINSetSerializer,
    PINChangeSerializer,
    DeviceBindingSerializer,
)
from .services.cache_service import CacheService
from .services.twofa_service import TwoFAService
from .services.lockout_service import LockoutService
from .services.device_service import DeviceService


class AuthViewSet(viewsets.GenericViewSet):
    permission_classes = [permissions.AllowAny]

    @action(detail=False, methods=['post'])
    def register_customer(self, request):
        serializer = RegisterCustomerSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            refresh = RefreshToken.for_user(user)
            user_data = {
                'id': str(user.id),
                'email': user.email,
                'user_type': user.user_type,
                'full_name': user.full_name,
            }
            CacheService.set_user_session(user.id, user_data)
            return Response({
                'user': UserSerializer(user).data,
                'access': str(refresh.access_token),
                'refresh': str(refresh),
            })
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['post'])
    def staff_login(self, request):
        serializer = StaffLoginSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.validated_data['user']
            refresh = RefreshToken.for_user(user)
            user_data = {
                'id': str(user.id),
                'phone': user.phone,
                'user_type': user.user_type,
                'venue_id': str(user.venue_id) if user.venue else None,
                'staff_role': user.staff_role,
            }
            CacheService.set_user_session(user.id, user_data)
            return Response({
                'user': UserSerializer(user).data,
                'access': str(refresh.access_token),
                'refresh': str(refresh),
            })
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['post'])
    def manager_login(self, request):
        serializer = ManagerLoginSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.validated_data['user']
            refresh = RefreshToken.for_user(user)
            return Response({
                'user': UserSerializer(user).data,
                'access': str(refresh.access_token),
                'refresh': str(refresh),
            })
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['post'])
    def admin_login_request(self, request):
        serializer = AdminLoginRequestSerializer(data=request.data)
        if serializer.is_valid():
            return Response({
                'message': 'Login link sent to your email',
                'login_url': serializer.validated_data['login_url']
            })
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['post'])
    def admin_login_confirm(self, request):
        # Pass request context for IP whitelist check
        serializer = AdminLoginConfirmSerializer(
            data=request.data,
            context={'request': request}
        )
        if serializer.is_valid():
            user = serializer.validated_data['user']
            refresh = RefreshToken.for_user(user)
            return Response({
                'user': UserSerializer(user).data,
                'access': str(refresh.access_token),
                'refresh': str(refresh),
            })
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['post'])
    def request_otp(self, request):
        serializer = OTPRequestSerializer(data=request.data)
        if serializer.is_valid():
            otp = serializer.create_otp()
            return Response({'message': 'OTP sent', 'otp': otp})
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['post'])
    def verify_otp(self, request):
        serializer = OTPVerifySerializer(data=request.data)
        if serializer.is_valid():
            return Response({'message': 'OTP verified'})
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['post'])
    def password_reset_request(self, request):
        serializer = PasswordResetRequestSerializer(data=request.data)
        if serializer.is_valid():
            return Response(serializer.validated_data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['post'])
    def password_reset_confirm(self, request):
        serializer = PasswordResetConfirmSerializer(data=request.data)
        if serializer.is_valid():
            user = None
            # Find the user from the identifier
            identifier = request.data.get('identifier')
            if identifier:
                try:
                    if '@' in identifier:
                        user = User.objects.get(email=identifier)
                    else:
                        user = User.objects.get(phone=identifier)
                except User.DoesNotExist:
                    pass

            # Blacklist all existing refresh tokens for this user
            if user:
                tokens = OutstandingToken.objects.filter(user=user)
                for token in tokens:
                    BlacklistedToken.objects.get_or_create(token=token)

            return Response({'message': 'Password reset successfully'})
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['post'])
    def staff_set_pin(self, request):
        serializer = StaffPINSetSerializer(data=request.data)
        if serializer.is_valid():
            return Response(serializer.validated_data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['post'])
    def staff_change_pin(self, request):
        serializer = StaffPINChangeSerializer(data=request.data)
        if serializer.is_valid():
            return Response(serializer.validated_data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['post'])
    def staff_reset_pin_request(self, request):
        serializer = StaffPINResetRequestSerializer(data=request.data)
        if serializer.is_valid():
            return Response(serializer.validated_data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['post'])
    def staff_reset_pin_confirm(self, request):
        serializer = StaffPINResetConfirmSerializer(data=request.data)
        if serializer.is_valid():
            return Response({'message': 'PIN reset successfully'})
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    # =========================================================================
    # 2FA Endpoints (unchanged)
    # =========================================================================

    @action(detail=False, methods=['get'], permission_classes=[permissions.IsAuthenticated])
    def setup_2fa(self, request):
        user = request.user
        if user.is_2fa_enabled:
            return Response({'error': '2FA already enabled'}, status=status.HTTP_400_BAD_REQUEST)
        secret = TwoFAService.generate_secret(user)
        qr_code = TwoFAService.get_qr_code(user, secret)
        request.session['2fa_secret'] = secret
        return Response({'secret': secret, 'qr_code': qr_code})

    @action(detail=False, methods=['post'], permission_classes=[permissions.IsAuthenticated])
    def verify_2fa(self, request):
        serializer = TwoFAVerifySerializer(data=request.data)
        if serializer.is_valid():
            secret = request.session.get('2fa_secret')
            if not secret:
                return Response({'error': '2FA setup not initiated'}, status=status.HTTP_400_BAD_REQUEST)
            user = request.user
            user.enable_2fa(secret)
            codes = TwoFAService.generate_recovery_codes(user)
            return Response({'message': '2FA enabled', 'recovery_codes': codes})
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['post'], permission_classes=[permissions.IsAuthenticated])
    def disable_2fa(self, request):
        serializer = TwoFADisableSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            user = request.user
            user.disable_2fa()
            return Response({'message': '2FA disabled'})
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    # =========================================================================
    # Password and PIN Management (unchanged)
    # =========================================================================

    @action(detail=False, methods=['post'], permission_classes=[permissions.IsAuthenticated])
    def change_password(self, request):
        serializer = PasswordChangeSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            user = request.user
            user.set_password(serializer.validated_data['new_password'])
            user.password_updated_at = timezone.now()
            user.save()
            # Blacklist all existing refresh tokens for this user
            tokens = OutstandingToken.objects.filter(user=user)
            for token in tokens:
                BlacklistedToken.objects.get_or_create(token=token)
            return Response({'message': 'Password changed successfully'})
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['post'], permission_classes=[permissions.IsAuthenticated])
    def set_pin(self, request):
        serializer = PINSetSerializer(data=request.data)
        if serializer.is_valid():
            user = request.user
            user.set_pin(serializer.validated_data['new_pin'])
            user.save()
            return Response({'message': 'PIN set successfully'})
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['post'], permission_classes=[permissions.IsAuthenticated])
    def change_pin(self, request):
        serializer = PINChangeSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            user = request.user
            user.set_pin(serializer.validated_data['new_pin'])
            user.save()
            return Response({'message': 'PIN changed successfully'})
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    # =========================================================================
    # Device Binding (unchanged)
    # =========================================================================

    @action(detail=False, methods=['post'], permission_classes=[permissions.IsAuthenticated])
    def bind_device(self, request):
        serializer = DeviceBindingSerializer(data=request.data)
        if serializer.is_valid():
            user = request.user
            DeviceService.store_device(user, serializer.validated_data['device_fingerprint'])
            return Response({'message': 'Device bound successfully'})
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    # =========================================================================
    # Logout and Refresh (unchanged)
    # =========================================================================

    @action(detail=False, methods=['post'])
    def logout(self, request):
        try:
            refresh_token = request.data.get('refresh')
            if refresh_token:
                token = RefreshToken(refresh_token)
                token.blacklist()
            if request.user.is_authenticated:
                CacheService.invalidate_user_session(request.user.id)
            return Response({'message': 'Logged out successfully'})
        except Exception:
            return Response({'message': 'Logged out'}, status=status.HTTP_200_OK)

    @action(detail=False, methods=['post'])
    def refresh_token(self, request):
        refresh_token = request.data.get('refresh')
        if not refresh_token:
            return Response({'error': 'Refresh token required'}, status=status.HTTP_400_BAD_REQUEST)
        try:
            refresh = RefreshToken(refresh_token)
            return Response({'access': str(refresh.access_token)})
        except Exception:
            return Response({'error': 'Invalid refresh token'}, status=status.HTTP_400_BAD_REQUEST)


class UserViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = UserSerializer
    queryset = User.objects.all()

    def get_queryset(self):
        user = self.request.user
        if user.user_type in ['admin', 'support', 'finance']:
            return User.objects.all()
        if user.venue:
            return User.objects.filter(venue=user.venue)
        return User.objects.none()

    @action(detail=False, methods=['get'])
    def me(self, request):
        serializer = UserSerializer(request.user)
        return Response(serializer.data)
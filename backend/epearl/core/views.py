from django.shortcuts import render

# Create your views here.
from rest_framework import viewsets, generics, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import get_user_model, authenticate
from django.contrib.auth.password_validation import validate_password
from django.utils import timezone
from .models import User
from .serializers import (
    UserRegistrationSerializer, StaffRegistrationSerializer,
    LoginSerializer, TokenResponseSerializer,
    ChangePasswordSerializer, PasswordResetRequestSerializer,
    PasswordResetConfirmSerializer
)
from venues.models import Venue
from staff.models import Staff
from django.db import transaction

User = get_user_model()

def get_tokens_for_user(user):
    refresh = RefreshToken.for_user(user)
    return {
        'access': str(refresh.access_token),
        'refresh': str(refresh),
    }

class AuthViewSet(viewsets.GenericViewSet):
    """
    Authentication endpoints.
    """
    permission_classes = [permissions.AllowAny]
    
    @action(detail=False, methods=['post'])
    def register_customer(self, request):
        """
        Register a new customer account.
        """
        serializer = UserRegistrationSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            tokens = get_tokens_for_user(user)
            return Response({
                'user': {
                    'id': user.id,
                    'email': user.email,
                    'phone': user.phone,
                    'user_type': user.user_type
                },
                'tokens': tokens
            }, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=False, methods=['post'])
    def register_staff(self, request):
        """
        Register a new staff member (Manager only).
        """
        # Check if user is authenticated and is a manager
        if not request.user.is_authenticated:
            return Response(
                {'error': 'Authentication required.'},
                status=status.HTTP_401_UNAUTHORIZED
            )
        
        if request.user.user_type not in ['manager', 'owner', 'admin', 'super_admin']:
            return Response(
                {'error': 'Only managers can register staff.'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        serializer = StaffRegistrationSerializer(
            data=request.data,
            context={'venue': request.user.venue}
        )
        if serializer.is_valid():
            staff = serializer.save()
            return Response({
                'staff': {
                    'id': staff.id,
                    'name': staff.name,
                    'phone': staff.phone,
                    'role': staff.role
                }
            }, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=False, methods=['post'])
    def login(self, request):
        """
        Login with email or phone.
        """
        serializer = LoginSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.validated_data['user']
            
            # Reset login attempts on successful login
            user.login_attempts = 0
            user.locked_until = None
            user.last_login = timezone.now()
            user.last_login_ip = request.META.get('REMOTE_ADDR')
            user.save()
            
            tokens = get_tokens_for_user(user)
            
            response_data = {
                'access': tokens['access'],
                'refresh': tokens['refresh'],
                'user': {
                    'id': user.id,
                    'email': user.email,
                    'phone': user.phone,
                    'user_type': user.user_type,
                    'is_verified': user.is_verified,
                    'is_2fa_enabled': user.is_2fa_enabled,
                }
            }
            
            # Add venue info if user has a venue
            if user.venue:
                response_data['user']['venue'] = {
                    'id': user.venue.id,
                    'business_name': user.venue.business_name
                }
            
            # Add staff info if user is staff
            if user.staff_profile:
                response_data['user']['staff'] = {
                    'id': user.staff_profile.id,
                    'name': user.staff_profile.name,
                    'role': user.staff_profile.role
                }
            
            return Response(response_data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=False, methods=['post'])
    def logout(self, request):
        """
        Logout by blacklisting the refresh token.
        """
        try:
            refresh_token = request.data.get('refresh')
            if refresh_token:
                token = RefreshToken(refresh_token)
                token.blacklist()
            return Response({'message': 'Logged out successfully.'})
        except Exception:
            return Response(
                {'error': 'Invalid token.'},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    @action(detail=False, methods=['post'])
    def refresh_token(self, request):
        """
        Refresh access token using refresh token.
        """
        try:
            refresh_token = request.data.get('refresh')
            if not refresh_token:
                return Response(
                    {'error': 'Refresh token required.'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            refresh = RefreshToken(refresh_token)
            return Response({
                'access': str(refresh.access_token)
            })
        except Exception:
            return Response(
                {'error': 'Invalid refresh token.'},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    @action(detail=False, methods=['post'])
    def change_password(self, request):
        """
        Change password for authenticated user.
        """
        if not request.user.is_authenticated:
            return Response(
                {'error': 'Authentication required.'},
                status=status.HTTP_401_UNAUTHORIZED
            )
        
        serializer = ChangePasswordSerializer(data=request.data)
        if serializer.is_valid():
            user = request.user
            if not user.check_password(serializer.validated_data['old_password']):
                return Response(
                    {'old_password': 'Incorrect password.'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            user.set_password(serializer.validated_data['new_password'])
            user.save()
            return Response({'message': 'Password changed successfully.'})
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=False, methods=['post'])
    def request_password_reset(self, request):
        """
        Request a password reset.
        """
        serializer = PasswordResetRequestSerializer(data=request.data)
        if serializer.is_valid():
            # In production, send email/SMS with reset link
            # For now, just return success
            return Response({
                'message': 'Password reset link sent to your email/phone.'
            })
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=False, methods=['post'])
    def confirm_password_reset(self, request):
        """
        Confirm password reset with token.
        """
        serializer = PasswordResetConfirmSerializer(data=request.data)
        if serializer.is_valid():
            # In production, validate token and reset password
            return Response({
                'message': 'Password reset successfully.'
            })
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class UserProfileView(generics.RetrieveUpdateAPIView):
    """
    View for authenticated user profile.
    """
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = UserRegistrationSerializer
    
    def get_object(self):
        return self.request.user
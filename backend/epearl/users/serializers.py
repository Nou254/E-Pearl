# users/serializers.py

from rest_framework import serializers
from django.contrib.auth import authenticate
from django.utils import timezone
from django.conf import settings
from .models import User
from .services.cache_service import CacheService
from .services.lockout_service import LockoutService
from .services.device_service import DeviceService
from .services.notification_service import NotificationService
import pyotp
import bcrypt


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = [
            'id', 'email', 'phone', 'full_name', 'user_type',
            'venue', 'staff_role', 'assigned_zone', 'is_active',
            'is_2fa_enabled', 'last_login', 'created_at'
        ]
        read_only_fields = ['id', 'created_at', 'last_login']


class RegisterCustomerSerializer(serializers.Serializer):
    email = serializers.EmailField(required=False)
    phone = serializers.CharField(max_length=20, required=False)
    password = serializers.CharField(write_only=True, min_length=8)
    full_name = serializers.CharField(max_length=255, required=False)

    def validate(self, data):
        if not data.get('email') and not data.get('phone'):
            raise serializers.ValidationError("Either email or phone is required")
        if data.get('email') and User.objects.filter(email=data['email']).exists():
            raise serializers.ValidationError("Email already registered")
        if data.get('phone') and User.objects.filter(phone=data['phone']).exists():
            raise serializers.ValidationError("Phone already registered")
        return data

    def create(self, validated_data):
        user = User.objects.create_user(
            email=validated_data.get('email'),
            phone=validated_data.get('phone'),
            password=validated_data['password'],
            full_name=validated_data.get('full_name', ''),
            user_type='registered_customer'
        )
        return user


class StaffLoginSerializer(serializers.Serializer):
    phone = serializers.CharField(max_length=20)
    pin = serializers.CharField(max_length=6, write_only=True)
    device_fingerprint = serializers.CharField(max_length=255, required=False)

    def validate(self, data):
        phone = data['phone']
        identifier = f"staff_{phone}"

        if LockoutService.is_locked(identifier):
            remaining = LockoutService.get_lockout_remaining(identifier)
            raise serializers.ValidationError(f"Account locked. Try again in {remaining} seconds.")

        try:
            user = User.objects.get(phone=phone, user_type='staff', is_active=True)
        except User.DoesNotExist:
            LockoutService.increment_attempts(identifier)
            raise serializers.ValidationError("Invalid phone or PIN")

        if not user.pin_hash:
            raise serializers.ValidationError("PIN not set. Please contact your manager.")

        if not user.check_pin(data['pin']):
            attempts = LockoutService.increment_attempts(identifier)
            if attempts >= LockoutService.MAX_ATTEMPTS:
                raise serializers.ValidationError("Account locked due to too many failed attempts. Try again later.")
            raise serializers.ValidationError("Invalid PIN")

        LockoutService.reset_attempts(identifier)

        fingerprint = data.get('device_fingerprint')
        if fingerprint:
            if user.device_fingerprint and not user.is_device_trusted_fingerprint(fingerprint):
                raise serializers.ValidationError(
                    "Untrusted device. Please bind your device first or contact support."
                )
            else:
                DeviceService.store_device(user, fingerprint)

        pin_expiry_days = getattr(settings, 'LOCKOUT_PIN_EXPIRY_DAYS', 365)
        if user.is_pin_expired(max_age_days=pin_expiry_days):
            raise serializers.ValidationError(
                "Your PIN has expired. Please change your PIN before logging in."
            )

        user.last_login = timezone.now()
        user.save(update_fields=['last_login'])

        return {'user': user}


class ManagerLoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)
    totp_code = serializers.CharField(max_length=6, required=False)

    def validate(self, data):
        email = data['email']
        identifier = f"manager_{email}"

        if LockoutService.is_locked(identifier):
            remaining = LockoutService.get_lockout_remaining(identifier)
            raise serializers.ValidationError(f"Account locked. Try again in {remaining} seconds.")

        user = authenticate(email=email, password=data['password'])
        if not user:
            LockoutService.increment_attempts(identifier)
            raise serializers.ValidationError("Invalid credentials")

        if not user.is_active:
            raise serializers.ValidationError("Account is inactive")

        if user.user_type not in ['manager', 'owner']:
            raise serializers.ValidationError("Invalid user type for this login method")

        password_expiry_days = getattr(settings, 'LOCKOUT_PASSWORD_EXPIRY_DAYS', 90)
        if user.is_password_expired(max_age_days=password_expiry_days):
            raise serializers.ValidationError(
                "Your password has expired. Please reset your password before logging in."
            )

        if user.is_2fa_enabled:
            if not data.get('totp_code'):
                raise serializers.ValidationError("2FA code required")
            totp = pyotp.TOTP(user.totp_secret)
            if not totp.verify(data['totp_code']):
                LockoutService.increment_attempts(identifier)
                raise serializers.ValidationError("Invalid 2FA code")

        LockoutService.reset_attempts(identifier)
        user.last_login = timezone.now()
        user.save(update_fields=['last_login'])

        user_data = {
            'id': str(user.id),
            'email': user.email,
            'user_type': user.user_type,
            'venue_id': str(user.venue_id) if user.venue else None,
            'full_name': user.full_name,
        }
        CacheService.set_user_session(user.id, user_data)

        return {'user': user}


class AdminLoginRequestSerializer(serializers.Serializer):
    email = serializers.EmailField()

    def validate(self, data):
        try:
            user = User.objects.get(email=data['email'], user_type__in=['admin', 'support', 'finance'], is_active=True)
        except User.DoesNotExist:
            raise serializers.ValidationError("No admin account found with this email")

        token = CacheService.generate_admin_token(str(user.id))
        login_url = f"{settings.FRONTEND_URL}/admin/login/{token}"

        NotificationService.send_admin_login_link(user.email, login_url)

        return {'login_url': login_url, 'message': 'Login link sent to your email'}


class AdminLoginConfirmSerializer(serializers.Serializer):
    token = serializers.CharField()
    password = serializers.CharField(write_only=True)
    totp_code = serializers.CharField(max_length=6)

    def validate(self, data):
        from users.services.cache_service import CacheService
        from users.services.twofa_service import TwoFAService

        payload = CacheService.validate_admin_token(data['token'])
        if not payload:
            raise serializers.ValidationError("Invalid or expired token")

        user_id = payload['user_id']
        try:
            user = User.objects.get(id=user_id, is_active=True)
        except User.DoesNotExist:
            raise serializers.ValidationError("User not found")

        if not user.check_password(data['password']):
            raise serializers.ValidationError("Invalid password")

        if user.is_2fa_enabled:
            if not TwoFAService.verify_code(user.totp_secret, data['totp_code']):
                raise serializers.ValidationError("Invalid 2FA code")

        CacheService.mark_admin_token_used(data['token'])

        if user.is_ip_whitelist_enabled:
            request = self.context.get('request')
            if request:
                x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
                if x_forwarded_for:
                    client_ip = x_forwarded_for.split(',')[0].strip()
                else:
                    client_ip = request.META.get('REMOTE_ADDR')

                if client_ip not in user.ip_whitelist:
                    raise serializers.ValidationError(
                        "Access denied. Your IP is not whitelisted for admin access."
                    )

        user.last_login = timezone.now()
        user.save(update_fields=['last_login'])

        user_data = {
            'id': str(user.id),
            'email': user.email,
            'user_type': user.user_type,
            'full_name': user.full_name,
        }
        CacheService.set_user_session(user.id, user_data)

        return {'user': user}


class OTPRequestSerializer(serializers.Serializer):
    phone = serializers.CharField(max_length=20, required=False)
    email = serializers.EmailField(required=False)
    otp_type = serializers.ChoiceField(choices=['login', 'registration', 'password_reset', '2fa', 'email_verification'])
    delivery_method = serializers.ChoiceField(choices=['email', 'sms'], default='email')

    def validate(self, data):
        if not data.get('phone') and not data.get('email'):
            raise serializers.ValidationError("Either phone or email is required")
        return data

    def create_otp(self):
        import random
        otp_code = ''.join([str(random.randint(0, 9)) for _ in range(6)])
        identifier = self.validated_data.get('phone') or self.validated_data.get('email')
        otp_type = self.validated_data['otp_type']
        delivery_method = self.validated_data.get('delivery_method', 'email')

        CacheService.store_otp(identifier, otp_code, otp_type)

        if delivery_method == 'email':
            NotificationService.send_otp_via_email(identifier, otp_code, otp_type)
        else:
            NotificationService.send_otp_via_sms(identifier, otp_code, otp_type)

        return {
            'otp_code': otp_code,
            'masked_identifier': NotificationService.mask_identifier(identifier)
        }


class OTPVerifySerializer(serializers.Serializer):
    phone = serializers.CharField(max_length=20, required=False)
    email = serializers.EmailField(required=False)
    otp_code = serializers.CharField(max_length=6)
    otp_type = serializers.ChoiceField(choices=['login', 'registration', 'password_reset', '2fa', 'email_verification'])

    def validate(self, data):
        identifier = data.get('phone') or data.get('email')
        if not identifier:
            raise serializers.ValidationError("Identifier (phone/email) required")
        if CacheService.verify_otp(identifier, data['otp_code'], data['otp_type']):
            return {'valid': True}
        raise serializers.ValidationError("Invalid or expired OTP")


class PasswordResetRequestSerializer(serializers.Serializer):
    email = serializers.EmailField(required=False)
    phone = serializers.CharField(max_length=20, required=False)
    delivery_method = serializers.ChoiceField(choices=['email', 'sms'], default='email')

    def validate(self, data):
        if not data.get('email') and not data.get('phone'):
            raise serializers.ValidationError("Either email or phone is required")

        if data.get('email'):
            try:
                user = User.objects.get(email=data['email'])
            except User.DoesNotExist:
                raise serializers.ValidationError("No user found with this email")
        else:
            try:
                user = User.objects.get(phone=data['phone'])
            except User.DoesNotExist:
                raise serializers.ValidationError("No user found with this phone")

        if user.user_type not in ['manager', 'owner', 'registered_customer']:
            raise serializers.ValidationError("Password reset not available for this user type")

        import random
        otp_code = ''.join([str(random.randint(0, 9)) for _ in range(6)])
        identifier = data.get('email') or data.get('phone')
        delivery_method = data.get('delivery_method', 'email')

        CacheService.store_otp(identifier, otp_code, 'password_reset')

        if delivery_method == 'email':
            NotificationService.send_password_reset_email(identifier, otp_code)
        else:
            NotificationService.send_password_reset_sms(identifier, otp_code)

        return {
            'message': f'OTP sent to {NotificationService.mask_identifier(identifier)}',
            'masked_identifier': NotificationService.mask_identifier(identifier),
            'delivery_method': delivery_method
        }


class PasswordResetConfirmSerializer(serializers.Serializer):
    identifier = serializers.CharField()
    otp_code = serializers.CharField(max_length=6)
    new_password = serializers.CharField(min_length=8, write_only=True)

    def validate(self, data):
        if not CacheService.verify_otp(data['identifier'], data['otp_code'], 'password_reset'):
            raise serializers.ValidationError("Invalid or expired OTP")

        try:
            if '@' in data['identifier']:
                user = User.objects.get(email=data['identifier'])
            else:
                user = User.objects.get(phone=data['identifier'])
        except User.DoesNotExist:
            raise serializers.ValidationError("User not found")

        user.set_password(data['new_password'])
        user.password_updated_at = timezone.now()
        user.save(update_fields=['password', 'password_updated_at'])
        return {'message': 'Password reset successfully'}


class StaffPINSetSerializer(serializers.Serializer):
    phone = serializers.CharField(max_length=20)
    new_pin = serializers.CharField(min_length=4, max_length=6, write_only=True)

    def validate(self, data):
        try:
            user = User.objects.get(phone=data['phone'], user_type='staff')
        except User.DoesNotExist:
            raise serializers.ValidationError("Staff user not found")
        user.set_pin(data['new_pin'])
        user.save(update_fields=['pin_hash', 'pin_updated_at'])
        return {'message': 'PIN set successfully'}


class StaffPINChangeSerializer(serializers.Serializer):
    phone = serializers.CharField(max_length=20)
    old_pin = serializers.CharField(max_length=6, write_only=True)
    new_pin = serializers.CharField(min_length=4, max_length=6, write_only=True)

    def validate(self, data):
        try:
            user = User.objects.get(phone=data['phone'], user_type='staff')
        except User.DoesNotExist:
            raise serializers.ValidationError("Staff user not found")
        if not user.check_pin(data['old_pin']):
            raise serializers.ValidationError("Old PIN is incorrect")
        user.set_pin(data['new_pin'])
        user.save(update_fields=['pin_hash', 'pin_updated_at'])
        return {'message': 'PIN changed successfully'}


class StaffPINResetRequestSerializer(serializers.Serializer):
    phone = serializers.CharField(max_length=20)

    def validate(self, data):
        try:
            user = User.objects.get(phone=data['phone'], user_type='staff')
        except User.DoesNotExist:
            raise serializers.ValidationError("Staff user not found")
        token = CacheService.generate_pin_reset_token(str(user.id))
        reset_url = f"{settings.FRONTEND_URL}/reset-pin/{token}"
        return {'reset_url': reset_url}


class StaffPINResetConfirmSerializer(serializers.Serializer):
    token = serializers.CharField()
    new_pin = serializers.CharField(min_length=4, max_length=6, write_only=True)

    def validate(self, data):
        user_id = CacheService.validate_pin_reset_token(data['token'])
        if not user_id:
            raise serializers.ValidationError("Invalid or expired token")
        try:
            user = User.objects.get(id=user_id, user_type='staff')
        except User.DoesNotExist:
            raise serializers.ValidationError("User not found")
        user.set_pin(data['new_pin'])
        user.save(update_fields=['pin_hash', 'pin_updated_at'])
        return {'message': 'PIN reset successfully'}


# =============================================================================
# 2FA Serializers
# =============================================================================

class TwoFASetupSerializer(serializers.Serializer):
    def get_secret(self, user):
        from users.services.twofa_service import TwoFAService
        secret = TwoFAService.generate_secret(user)
        qr_code = TwoFAService.get_qr_code(user, secret)
        return {'secret': secret, 'qr_code': qr_code}


class TwoFAVerifySerializer(serializers.Serializer):
    secret = serializers.CharField()
    code = serializers.CharField(max_length=6)

    def validate(self, data):
        from users.services.twofa_service import TwoFAService
        if not TwoFAService.verify_code(data['secret'], data['code']):
            raise serializers.ValidationError("Invalid code")
        return data


class TwoFADisableSerializer(serializers.Serializer):
    password = serializers.CharField(write_only=True)

    def validate(self, data):
        user = self.context['request'].user
        if not user.check_password(data['password']):
            raise serializers.ValidationError("Invalid password")
        return data


# =============================================================================
# Password and PIN Management Serializers
# =============================================================================

class PasswordChangeSerializer(serializers.Serializer):
    old_password = serializers.CharField(write_only=True)
    new_password = serializers.CharField(min_length=8, write_only=True)

    def validate(self, data):
        user = self.context['request'].user
        if not user.check_password(data['old_password']):
            raise serializers.ValidationError("Invalid old password")
        return data


class PINSetSerializer(serializers.Serializer):
    new_pin = serializers.CharField(min_length=4, max_length=6, write_only=True)


class PINChangeSerializer(serializers.Serializer):
    old_pin = serializers.CharField(write_only=True)
    new_pin = serializers.CharField(min_length=4, max_length=6, write_only=True)

    def validate(self, data):
        user = self.context['request'].user
        if not user.check_pin(data['old_pin']):
            raise serializers.ValidationError("Invalid old PIN")
        return data


# =============================================================================
# Device Binding Serializers
# =============================================================================

class DeviceBindingSerializer(serializers.Serializer):
    device_fingerprint = serializers.CharField(max_length=255)

    def validate(self, data):
        return data


# =============================================================================
# RBAC Serializers
# =============================================================================


class PermissionSerializer(serializers.ModelSerializer):
    class Meta:
        model = __import__('users.models', fromlist=['Permission']).Permission
        fields = ['id', 'code', 'name', 'description', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']


class RoleSerializer(serializers.ModelSerializer):
    permissions = PermissionSerializer(many=True, read_only=True)
    permission_count = serializers.SerializerMethodField()

    class Meta:
        model = __import__('users.models', fromlist=['Role']).Role
        fields = ['id', 'name', 'description', 'permissions', 'permission_count', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']

    def get_permission_count(self, obj):
        return obj.permissions.count()


class RoleCreateSerializer(serializers.ModelSerializer):
    permission_codes = serializers.ListField(
        child=serializers.CharField(),
        required=False,
        help_text='List of permission codes to assign to this role.'
    )

    class Meta:
        model = __import__('users.models', fromlist=['Role']).Role
        fields = ['id', 'name', 'description', 'permission_codes', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']

    def create(self, validated_data):
        from users.models import Permission
        permission_codes = validated_data.pop('permission_codes', [])
        role = __import__('users.models', fromlist=['Role']).Role.objects.create(**validated_data)
        if permission_codes:
            perms = Permission.objects.filter(code__in=permission_codes)
            role.permissions.set(perms)
        return role

    def update(self, instance, validated_data):
        from users.models import Permission
        permission_codes = validated_data.pop('permission_codes', None)
        instance.name = validated_data.get('name', instance.name)
        instance.description = validated_data.get('description', instance.description)
        instance.save()
        if permission_codes is not None:
            perms = Permission.objects.filter(code__in=permission_codes)
            instance.permissions.set(perms)
        return instance


class UserRoleSerializer(serializers.ModelSerializer):
    user_email = serializers.CharField(source='user.email', read_only=True)
    venue_name = serializers.CharField(source='venue.business_name', read_only=True)
    role_name = serializers.CharField(source='role.name', read_only=True)

    class Meta:
        model = __import__('users.models', fromlist=['UserRole']).UserRole
        fields = ['id', 'user', 'user_email', 'venue', 'venue_name', 'role', 'role_name', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']


class UserRoleCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = __import__('users.models', fromlist=['UserRole']).UserRole
        fields = ['id', 'user', 'venue', 'role', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']


class UserPermissionSerializer(serializers.ModelSerializer):
    user_email = serializers.CharField(source='user.email', read_only=True)
    venue_name = serializers.CharField(source='venue.business_name', read_only=True)
    permission_code = serializers.CharField(source='permission.code', read_only=True)

    class Meta:
        model = __import__('users.models', fromlist=['UserPermission']).UserPermission
        fields = ['id', 'user', 'user_email', 'venue', 'venue_name', 'permission', 'permission_code', 'is_granted', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']


class UserPermissionCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = __import__('users.models', fromlist=['UserPermission']).UserPermission
        fields = ['id', 'user', 'venue', 'permission', 'is_granted', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']
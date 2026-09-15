from rest_framework import serializers
from django.contrib.auth import authenticate, get_user_model
from django.contrib.auth.password_validation import validate_password
from rest_framework_simplejwt.tokens import RefreshToken
from venues.models import Venue
from staff.models import Staff

User = get_user_model()

class UserRegistrationSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, validators=[validate_password])
    password2 = serializers.CharField(write_only=True)
    
    class Meta:
        model = User
        fields = ['id', 'email', 'phone', 'password', 'password2', 'user_type', 'venue']
        read_only_fields = ['id']
    
    def validate(self, attrs):
        if attrs['password'] != attrs['password2']:
            raise serializers.ValidationError({"password": "Passwords do not match."})
        return attrs
    
    def create(self, validated_data):
        validated_data.pop('password2')
        user = User.objects.create_user(
            email=validated_data.get('email'),
            phone=validated_data.get('phone'),
            username=validated_data.get('email', validated_data.get('phone')),
            password=validated_data['password'],
            user_type=validated_data.get('user_type', 'customer'),
            venue=validated_data.get('venue')
        )
        return user

class StaffRegistrationSerializer(serializers.ModelSerializer):
    """
    Serializer for venue staff registration (created by manager).
    """
    name = serializers.CharField()
    role = serializers.CharField()
    pin = serializers.CharField(write_only=True)
    
    class Meta:
        model = Staff
        fields = ['name', 'phone', 'email', 'role', 'pin', 'assigned_zone']
    
    def create(self, validated_data):
        pin = validated_data.pop('pin')
        venue = self.context.get('venue')
        
        # Create staff record
        staff = Staff.objects.create(
            venue=venue,
            name=validated_data['name'],
            phone=validated_data['phone'],
            email=validated_data.get('email', ''),
            role=validated_data['role'],
            pin_hash=make_password(pin),  # We'll import this
            assigned_zone=validated_data.get('assigned_zone', '')
        )
        
        # Create user account for staff
        user = User.objects.create_user(
            phone=validated_data['phone'],
            username=validated_data['phone'],
            password=pin,
            user_type='staff',
            venue=venue,
            staff_profile=staff
        )
        
        return staff

class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField(required=False, allow_blank=True)
    phone = serializers.CharField(required=False, allow_blank=True)
    password = serializers.CharField(write_only=True)
    
    def validate(self, attrs):
        email = attrs.get('email')
        phone = attrs.get('phone')
        password = attrs.get('password')
        
        if not email and not phone:
            raise serializers.ValidationError("Email or phone is required.")
        
        # Try to find user
        user = None
        if email:
            try:
                user = User.objects.get(email=email)
            except User.DoesNotExist:
                pass
        
        if not user and phone:
            try:
                user = User.objects.get(phone=phone)
            except User.DoesNotExist:
                pass
        
        if not user:
            raise serializers.ValidationError("Invalid credentials.")
        
        if not user.check_password(password):
            raise serializers.ValidationError("Invalid credentials.")
        
        if not user.is_active:
            raise serializers.ValidationError("Account is inactive.")
        
        # Check if account is locked
        if user.locked_until and user.locked_until > timezone.now():
            raise serializers.ValidationError(f"Account locked until {user.locked_until}.")
        
        attrs['user'] = user
        return attrs

class TokenResponseSerializer(serializers.Serializer):
    access = serializers.CharField()
    refresh = serializers.CharField()
    user_id = serializers.CharField()
    user_type = serializers.CharField()
    venue_id = serializers.CharField(required=False, allow_null=True)

class ChangePasswordSerializer(serializers.Serializer):
    old_password = serializers.CharField(write_only=True)
    new_password = serializers.CharField(write_only=True, validators=[validate_password])
    new_password2 = serializers.CharField(write_only=True)
    
    def validate(self, attrs):
        if attrs['new_password'] != attrs['new_password2']:
            raise serializers.ValidationError({"new_password": "Passwords do not match."})
        return attrs

class PasswordResetRequestSerializer(serializers.Serializer):
    email = serializers.EmailField(required=False)
    phone = serializers.CharField(required=False)
    
    def validate(self, attrs):
        if not attrs.get('email') and not attrs.get('phone'):
            raise serializers.ValidationError("Email or phone is required.")
        return attrs

class PasswordResetConfirmSerializer(serializers.Serializer):
    token = serializers.CharField()
    password = serializers.CharField(write_only=True, validators=[validate_password])
    password2 = serializers.CharField(write_only=True)
    
    def validate(self, attrs):
        if attrs['password'] != attrs['password2']:
            raise serializers.ValidationError({"password": "Passwords do not match."})
        return attrs
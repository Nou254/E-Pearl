# users/models.py

from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from core.models import BaseModel
import bcrypt
from django.utils import timezone
import pytz


class UserManager(BaseUserManager):
    def create_user(self, email=None, phone=None, password=None, **extra_fields):
        if not email and not phone:
            raise ValueError('Either email or phone is required')
        if email:
            email = self.normalize_email(email)
        user = self.model(email=email, phone=phone, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_active', True)
        extra_fields.setdefault('user_type', 'admin')
        return self.create_user(email, password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin, BaseModel):
    USER_TYPES = [
        ('customer', 'Customer'),
        ('registered_customer', 'Registered Customer'),
        ('staff', 'Staff'),
        ('manager', 'Manager'),
        ('owner', 'Owner'),
        ('admin', 'Admin'),
        ('support', 'Support'),
        ('finance', 'Finance'),
    ]

    email = models.EmailField(unique=True, null=True, blank=True)
    phone = models.CharField(max_length=20, unique=True, null=True, blank=True)
    full_name = models.CharField(max_length=255, blank=True, null=True)

    user_type = models.CharField(max_length=50, choices=USER_TYPES, default='customer')
    venue = models.ForeignKey(
        'venues.Venue',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='users',
        db_constraint=False
    )

    # Staff specific
    staff_role = models.CharField(max_length=50, blank=True, null=True)
    assigned_zone = models.CharField(max_length=100, blank=True, null=True)

    # 2FA
    is_2fa_enabled = models.BooleanField(default=False)
    totp_secret = models.CharField(max_length=255, blank=True, null=True)

    # Admin IP whitelist
    is_ip_whitelist_enabled = models.BooleanField(default=False)
    ip_whitelist = models.JSONField(default=list, blank=True)

    # Account status
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    is_superuser = models.BooleanField(default=False)
    last_login = models.DateTimeField(null=True, blank=True)
    last_activity = models.DateTimeField(null=True, blank=True)
    password_updated_at = models.DateTimeField(null=True, blank=True)
    pin_updated_at = models.DateTimeField(null=True, blank=True)

    # Device binding
    device_fingerprint = models.CharField(max_length=255, blank=True, null=True)
    is_device_trusted = models.BooleanField(default=False)

    # PIN hashing (bcrypt)
    pin_hash = models.CharField(max_length=255, blank=True, null=True)

    # User timezone preference
    timezone = models.CharField(
        max_length=50,
        choices=[(tz, tz) for tz in pytz.common_timezones],
        default='Africa/Nairobi'
    )

    objects = UserManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []

    def __str__(self):
        return self.email or self.phone or str(self.id)

    def get_full_name(self):
        return self.full_name or self.email or self.phone

    def get_short_name(self):
        return self.full_name or self.email or self.phone

    def has_perm(self, perm, obj=None):
        return self.is_superuser

    def has_module_perms(self, app_label):
        return self.is_superuser

    # PIN methods
    def set_pin(self, raw_pin):
        if raw_pin:
            salt = bcrypt.gensalt()
            self.pin_hash = bcrypt.hashpw(raw_pin.encode('utf-8'), salt).decode('utf-8')
            self.pin_updated_at = timezone.now()
        else:
            self.pin_hash = None

    def check_pin(self, raw_pin):
        if not self.pin_hash:
            return False
        return bcrypt.checkpw(raw_pin.encode('utf-8'), self.pin_hash.encode('utf-8'))

    def is_device_trusted_fingerprint(self, fingerprint):
        return self.device_fingerprint == fingerprint

    def enable_2fa(self, secret):
        self.totp_secret = secret
        self.is_2fa_enabled = True
        self.save()

    def disable_2fa(self):
        self.totp_secret = None
        self.is_2fa_enabled = False
        self.save()

    def is_password_expired(self, max_age_days=90):
        if not self.password_updated_at:
            return True
        delta = timezone.now() - self.password_updated_at
        return delta.days > max_age_days

    def is_pin_expired(self, max_age_days=365):
        if not self.pin_updated_at:
            return True
        delta = timezone.now() - self.pin_updated_at
        return delta.days > max_age_days

    def generate_otp(self, otp_type='login'):
        from users.services.otp_service import OTPService
        return OTPService.generate_otp(self, otp_type)

    # RBAC convenience method
    def has_permission(self, permission_code, venue=None):
        from .services.permission_service import PermissionService
        if not venue and self.venue:
            venue = self.venue
        return PermissionService.user_has_permission(self, venue, permission_code)


# =============================================================================
# RBAC Models
# =============================================================================

class Permission(BaseModel):
    """
    Granular permission that can be assigned to a role or directly to a user.
    """
    code = models.CharField(max_length=100, unique=True)
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)

    class Meta:
        db_table = 'permissions'
        ordering = ['code']

    def __str__(self):
        return self.name


class Role(BaseModel):
    """
    A role groups multiple permissions.
    """
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    permissions = models.ManyToManyField(Permission, related_name='roles', blank=True)

    class Meta:
        db_table = 'roles'
        ordering = ['name']

    def __str__(self):
        return self.name


class UserRole(BaseModel):
    """
    Assigns a role to a user for a specific venue.
    """
    user = models.ForeignKey('users.User', on_delete=models.CASCADE, related_name='user_roles')
    venue = models.ForeignKey('venues.Venue', on_delete=models.CASCADE, related_name='user_roles')
    role = models.ForeignKey(Role, on_delete=models.CASCADE, related_name='user_roles')

    class Meta:
        db_table = 'user_roles'
        unique_together = ['user', 'venue', 'role']

    def __str__(self):
        return f"{self.user.email} - {self.role.name} @ {self.venue.business_name}"


class UserPermission(BaseModel):
    """
    Direct assignment of a permission to a user for a specific venue (overrides role).
    """
    user = models.ForeignKey(
        'users.User',
        on_delete=models.CASCADE,
        related_name='user_direct_permissions'   # unique name to avoid clash
    )
    venue = models.ForeignKey('venues.Venue', on_delete=models.CASCADE, related_name='user_permissions')
    permission = models.ForeignKey(Permission, on_delete=models.CASCADE, related_name='user_permissions')
    is_granted = models.BooleanField(default=True)

    class Meta:
        db_table = 'user_permissions'
        unique_together = ['user', 'venue', 'permission']

    def __str__(self):
        return f"{self.user.email} - {self.permission.code} @ {self.venue.business_name}"


# =============================================================================
# Granular Staff Permissions
# =============================================================================

class StaffPermission(BaseModel):
    """
    Granular permission overrides for specific staff members.
    """
    PERMISSION_TYPES = [
        ('override_cash', 'Override Cash Collection'),
        ('force_capture', 'Force Capture'),
        ('void_hold', 'Void Hold'),
        ('override_exit', 'Manual Override Exit'),
        ('suspend_table', 'Suspend Table'),
        ('manage_menu', 'Manage Menu'),
        ('manage_staff', 'Manage Staff'),
        ('view_reports', 'View Reports'),
    ]

    staff = models.ForeignKey('staff.Staff', on_delete=models.CASCADE, related_name='granular_permissions')
    permission_code = models.CharField(max_length=50, choices=PERMISSION_TYPES)
    is_granted = models.BooleanField(default=True)
    granted_by = models.ForeignKey('users.User', on_delete=models.SET_NULL, null=True, related_name='granted_permissions')
    granted_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'staff_granular_permissions'
        unique_together = ['staff', 'permission_code']

    def __str__(self):
        return f"{self.staff.user.full_name} - {self.permission_code}: {self.is_granted}"
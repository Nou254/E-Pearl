# users/permissions.py

from rest_framework.permissions import BasePermission
from .services.permission_service import PermissionService


class HasPermission(BasePermission):
    """
    DRF permission class to check if a user has a specific permission at their venue.
    Usage: permission_classes = [HasPermission('force_capture')]
    """

    def __init__(self, permission_code):
        self.permission_code = permission_code

    def __call__(self):
        return self

    def has_permission(self, request, view):
        user = request.user
        venue = user.venue if hasattr(user, 'venue') else None
        if not user or not user.is_authenticated:
            return False
        if not venue:
            # Users without a venue might be admins; allow if superuser or admin/support
            return user.is_superuser or user.user_type in ['admin', 'support']
        return PermissionService.user_has_permission(user, venue, self.permission_code)


class HasAnyPermission(BasePermission):
    """
    Check if user has any of the listed permissions.
    """

    def __init__(self, *permission_codes):
        self.permission_codes = permission_codes

    def __call__(self):
        return self

    def has_permission(self, request, view):
        user = request.user
        venue = user.venue if hasattr(user, 'venue') else None
        if not user or not user.is_authenticated:
            return False
        if not venue:
            return user.is_superuser or user.user_type in ['admin', 'support']
        perms = PermissionService.get_user_permissions(user, venue)
        return any(p in perms for p in self.permission_codes)


class IsOwner(BasePermission):
    """
    Check if the user is the venue owner.
    """
    def has_permission(self, request, view):
        user = request.user
        if not user or not user.is_authenticated:
            return False
        return user.user_type == 'owner'


class IsManager(BasePermission):
    """
    Check if the user is a manager, owner, superuser, or staff.
    """
    def has_permission(self, request, view):
        user = request.user
        if not user or not user.is_authenticated:
            return False
        # Allow superusers and staff for admin access
        if user.is_superuser or user.is_staff:
            return True
        return user.user_type in ['manager', 'owner']


class HQAdminPermission(BasePermission):
    """
    Allows access only to platform administrators (HQ staff).
    Users with user_type in ['admin', 'support', 'finance'] or superuser.
    """
    def has_permission(self, request, view):
        user = request.user
        if not user or not user.is_authenticated:
            return False
        if user.is_superuser or user.is_staff:
            return True
        return user.user_type in ['admin', 'support', 'finance']


# ========== NEW: Refund Review Permission ==========

class CanReviewRefunds(BasePermission):
    """
    Permission to review and approve/reject refund requests.
    Allowed for HQ admins, support, finance, and venue owners/managers with the 'review_refunds' permission.
    """
    def has_permission(self, request, view):
        user = request.user
        if not user or not user.is_authenticated:
            return False

        # Platform admins always have permission
        if user.is_superuser or user.is_staff:
            return True
        if user.user_type in ['admin', 'support', 'finance']:
            return True

        # Venue owner/manager must have the specific permission
        if user.user_type in ['owner', 'manager'] and user.venue:
            return PermissionService.user_has_permission(user, user.venue, 'review_refunds')

        return False
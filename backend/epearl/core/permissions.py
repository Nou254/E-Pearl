from rest_framework import permissions

class IsAuthenticatedAndVerified(permissions.BasePermission):
    """
    Allows access only to authenticated and verified users.
    """
    def has_permission(self, request, view):
        return (request.user and request.user.is_authenticated and 
                request.user.is_verified)

class IsStaff(permissions.BasePermission):
    """
    Allows access only to staff users (staff, manager, owner).
    """
    def has_permission(self, request, view):
        return (request.user and request.user.is_authenticated and 
                request.user.user_type in ['staff', 'manager', 'owner'])

class IsManager(permissions.BasePermission):
    """
    Allows access only to managers and owners.
    """
    def has_permission(self, request, view):
        return (request.user and request.user.is_authenticated and 
                request.user.user_type in ['manager', 'owner'])

class IsOwner(permissions.BasePermission):
    """
    Allows access only to venue owners.
    """
    def has_permission(self, request, view):
        return (request.user and request.user.is_authenticated and 
                request.user.user_type == 'owner')

class IsAdmin(permissions.BasePermission):
    """
    Allows access only to admins and super admins.
    """
    def has_permission(self, request, view):
        return (request.user and request.user.is_authenticated and 
                request.user.user_type in ['admin', 'super_admin'])

class IsSuperAdmin(permissions.BasePermission):
    """
    Allows access only to super admins.
    """
    def has_permission(self, request, view):
        return (request.user and request.user.is_authenticated and 
                request.user.user_type == 'super_admin')

class HasVenueAccess(permissions.BasePermission):
    """
    Allows access only if user belongs to the requested venue.
    """
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        
        # Super admins have access to all venues
        if request.user.user_type == 'super_admin':
            return True
        
        # Check if venue ID is in URL
        venue_id = view.kwargs.get('venue_id') or view.kwargs.get('pk')
        if venue_id:
            return request.user.venue_id == int(venue_id)
        
        # For list views, check if user has a venue
        return request.user.venue_id is not None
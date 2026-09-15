# users/rbac_views.py

from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from .models import Permission, Role, UserRole, UserPermission
from .serializers import (
    PermissionSerializer,
    RoleSerializer,
    RoleCreateSerializer,
    UserRoleSerializer,
    UserRoleCreateSerializer,
    UserPermissionSerializer,
    UserPermissionCreateSerializer,
)
from .services.permission_service import PermissionService


class PermissionViewSet(viewsets.ModelViewSet):
    """ViewSet for managing granular permissions."""
    serializer_class = PermissionSerializer
    permission_classes = [permissions.IsAuthenticated]
    queryset = Permission.objects.all().order_by('code')

    def get_permissions(self):
        if self.action in ['list', 'retrieve']:
            return [permissions.IsAuthenticated()]
        from .permission import IsManager
        return [permissions.IsAuthenticated(), IsManager()]

    @action(detail=False, methods=['post'], permission_classes=[permissions.IsAuthenticated])
    def seed(self, request):
        """Seed default permissions and roles."""
        if not request.user.is_superuser:
            return Response(
                {'error': 'Only superusers can seed permissions.'},
                status=status.HTTP_403_FORBIDDEN
            )
        PermissionService.seed_default_permissions_and_roles()
        return Response({'message': 'Default permissions and roles seeded successfully.'})


class RoleViewSet(viewsets.ModelViewSet):
    """ViewSet for managing roles."""
    serializer_class = RoleSerializer
    permission_classes = [permissions.IsAuthenticated]
    queryset = Role.objects.all().order_by('name')

    def get_permissions(self):
        if self.action in ['list', 'retrieve']:
            return [permissions.IsAuthenticated()]
        from .permission import IsManager
        return [permissions.IsAuthenticated(), IsManager()]

    def get_serializer_class(self):
        if self.action in ['create', 'update', 'partial_update']:
            return RoleCreateSerializer
        return RoleSerializer

    @action(detail=True, methods=['post'])
    def assign_permission(self, request, pk=None):
        """Assign a permission to this role."""
        role = self.get_object()
        permission_code = request.data.get('permission_code')
        if not permission_code:
            return Response(
                {'error': 'permission_code is required.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        try:
            permission = Permission.objects.get(code=permission_code)
        except Permission.DoesNotExist:
            return Response(
                {'error': f'Permission "{permission_code}" does not exist.'},
                status=status.HTTP_404_NOT_FOUND
            )
        role.permissions.add(permission)
        return Response({'message': f'Permission "{permission_code}" added to role "{role.name}".'})

    @action(detail=True, methods=['post'])
    def remove_permission(self, request, pk=None):
        """Remove a permission from this role."""
        role = self.get_object()
        permission_code = request.data.get('permission_code')
        if not permission_code:
            return Response(
                {'error': 'permission_code is required.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        try:
            permission = Permission.objects.get(code=permission_code)
        except Permission.DoesNotExist:
            return Response(
                {'error': f'Permission "{permission_code}" does not exist.'},
                status=status.HTTP_404_NOT_FOUND
            )
        role.permissions.remove(permission)
        return Response({'message': f'Permission "{permission_code}" removed from role "{role.name}".'})


class UserRoleViewSet(viewsets.ModelViewSet):
    """ViewSet for assigning roles to users per venue."""
    serializer_class = UserRoleSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.is_superuser or user.user_type in ['admin', 'support']:
            return UserRole.objects.all()
        if user.venue:
            return UserRole.objects.filter(venue=user.venue)
        return UserRole.objects.none()

    def get_serializer_class(self):
        if self.action in ['create', 'update', 'partial_update']:
            return UserRoleCreateSerializer
        return UserRoleSerializer

    def get_permissions(self):
        if self.action in ['list', 'retrieve']:
            return [permissions.IsAuthenticated()]
        from .permission import IsManager
        return [permissions.IsAuthenticated(), IsManager()]


class UserPermissionViewSet(viewsets.ModelViewSet):
    """ViewSet for direct user-permission overrides per venue."""
    serializer_class = UserPermissionSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.is_superuser or user.user_type in ['admin', 'support']:
            return UserPermission.objects.all()
        if user.venue:
            return UserPermission.objects.filter(venue=user.venue)
        return UserPermission.objects.none()

    def get_serializer_class(self):
        if self.action in ['create', 'update', 'partial_update']:
            return UserPermissionCreateSerializer
        return UserPermissionSerializer

    def get_permissions(self):
        if self.action in ['list', 'retrieve']:
            return [permissions.IsAuthenticated()]
        from .permission import IsManager
        return [permissions.IsAuthenticated(), IsManager()]

    @action(detail=False, methods=['get'])
    def my_permissions(self, request):
        """Get all permissions for the current user at their venue."""
        user = request.user
        venue = user.venue
        if not venue:
            if user.is_superuser or user.user_type in ['admin', 'support']:
                return Response({'permissions': ['*'], 'note': 'Admin/Superuser - all permissions granted.'})
            return Response({'permissions': []})
        perms = PermissionService.get_user_permissions(user, venue)
        return Response({'permissions': sorted(perms), 'venue': str(venue)})

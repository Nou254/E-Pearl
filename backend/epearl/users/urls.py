# users/urls.py

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import AuthViewSet, UserViewSet
from .rbac_views import (
    PermissionViewSet,
    RoleViewSet,
    UserRoleViewSet,
    UserPermissionViewSet,
)

# =============================================================================
# Router Configuration
# =============================================================================

router = DefaultRouter()
router.register(r'auth', AuthViewSet, basename='auth')
router.register(r'users', UserViewSet, basename='users')
router.register(r'permissions', PermissionViewSet, basename='permissions')
router.register(r'roles', RoleViewSet, basename='roles')
router.register(r'user-roles', UserRoleViewSet, basename='user-roles')
router.register(r'user-permissions', UserPermissionViewSet, basename='user-permissions')

# =============================================================================
# URL Patterns
# =============================================================================

urlpatterns = [
    path('', include(router.urls)),
]
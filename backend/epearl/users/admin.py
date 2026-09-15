from django.contrib import admin
from .models import User, Permission, Role, UserRole, UserPermission


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ['email', 'phone', 'full_name', 'user_type', 'venue', 'is_active', 'is_2fa_enabled']
    list_filter = ['user_type', 'is_active', 'is_2fa_enabled', 'is_staff']
    search_fields = ['email', 'phone', 'full_name']
    readonly_fields = ['id', 'created_at', 'updated_at', 'last_login', 'last_activity']


@admin.register(Permission)
class PermissionAdmin(admin.ModelAdmin):
    list_display = ['code', 'name', 'description']
    search_fields = ['code', 'name']
    ordering = ['code']


@admin.register(Role)
class RoleAdmin(admin.ModelAdmin):
    list_display = ['name', 'description']
    search_fields = ['name']
    filter_horizontal = ['permissions']


@admin.register(UserRole)
class UserRoleAdmin(admin.ModelAdmin):
    list_display = ['user', 'venue', 'role']
    list_filter = ['role']
    search_fields = ['user__email', 'user__full_name', 'venue__business_name']


@admin.register(UserPermission)
class UserPermissionAdmin(admin.ModelAdmin):
    list_display = ['user', 'venue', 'permission', 'is_granted']
    list_filter = ['is_granted', 'permission']
    search_fields = ['user__email', 'venue__business_name', 'permission__code']

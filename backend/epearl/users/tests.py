# users/tests.py

from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework import status
from users.models import Permission, Role, UserRole, UserPermission
from users.services.permission_service import PermissionService

User = get_user_model()


class RBACModelTests(TestCase):
    """Tests for RBAC models."""

    def setUp(self):
        self.user = User.objects.create_user(
            email='test@example.com',
            phone='0712345678',
            password='testpass123',
            full_name='Test User',
            user_type='staff'
        )
        self.permission = Permission.objects.create(
            code='view_orders',
            name='View Orders',
            description='Can view orders'
        )
        self.role = Role.objects.create(
            name='Waiter',
            description='Waiter role'
        )

    def test_permission_creation(self):
        self.assertEqual(self.permission.code, 'view_orders')
        self.assertEqual(str(self.permission), 'View Orders')

    def test_role_creation(self):
        self.assertEqual(self.role.name, 'Waiter')
        self.assertEqual(str(self.role), 'Waiter')

    def test_role_permissions(self):
        self.role.permissions.add(self.permission)
        self.assertIn(self.permission, self.role.permissions.all())

    def test_user_role_creation(self):
        from venues.models import Venue
        venue = Venue.objects.create(
            business_name='Test Venue',
            kra_pin='A123456789B',
            contact_phone='0712345678',
            contact_email='venue@test.com',
            sub_domain='test-venue'
        )
        user_role = UserRole.objects.create(
            user=self.user,
            venue=venue,
            role=self.role
        )
        self.assertEqual(user_role.user, self.user)
        self.assertEqual(user_role.venue, venue)
        self.assertEqual(user_role.role, self.role)

    def test_user_permission_creation(self):
        from venues.models import Venue
        venue = Venue.objects.create(
            business_name='Test Venue 2',
            kra_pin='A123456789C',
            contact_phone='0712345679',
            contact_email='venue2@test.com',
            sub_domain='test-venue-2'
        )
        user_perm = UserPermission.objects.create(
            user=self.user,
            venue=venue,
            permission=self.permission,
            is_granted=True
        )
        self.assertTrue(user_perm.is_granted)


class PermissionServiceTests(TestCase):
    """Tests for the PermissionService."""

    def setUp(self):
        self.user = User.objects.create_user(
            email='svc@example.com',
            phone='0711111111',
            password='testpass123',
            full_name='Service User',
            user_type='staff'
        )
        from venues.models import Venue
        self.venue = Venue.objects.create(
            business_name='Service Venue',
            kra_pin='A123456789D',
            contact_phone='0711111111',
            contact_email='svc@venue.com',
            sub_domain='svc-venue'
        )
        PermissionService.seed_default_permissions_and_roles()

    def test_seed_permissions(self):
        self.assertTrue(Permission.objects.filter(code='view_orders').exists())
        self.assertTrue(Role.objects.filter(name='Waiter').exists())

    def test_assign_role(self):
        user_role = PermissionService.assign_role(self.user, self.venue, 'Waiter')
        self.assertIsNotNone(user_role)
        self.assertEqual(user_role.role.name, 'Waiter')

    def test_user_has_permission_via_role(self):
        PermissionService.assign_role(self.user, self.venue, 'Waiter')
        self.assertTrue(
            PermissionService.user_has_permission(self.user, self.venue, 'view_orders')
        )
        self.assertFalse(
            PermissionService.user_has_permission(self.user, self.venue, 'manage_menu')
        )

    def test_user_has_permission_via_direct_override(self):
        PermissionService.assign_permission(self.user, self.venue, 'manage_menu', granted=True)
        self.assertTrue(
            PermissionService.user_has_permission(self.user, self.venue, 'manage_menu')
        )

    def test_revoke_permission(self):
        PermissionService.assign_role(self.user, self.venue, 'Waiter')
        PermissionService.assign_permission(self.user, self.venue, 'view_orders', granted=False)
        self.assertFalse(
            PermissionService.user_has_permission(self.user, self.venue, 'view_orders')
        )

    def test_get_user_permissions(self):
        PermissionService.assign_role(self.user, self.venue, 'Waiter')
        perms = PermissionService.get_user_permissions(self.user, self.venue)
        self.assertIn('view_orders', perms)
        self.assertIn('collect_cash', perms)
        self.assertIn('mark_served', perms)

    def test_superuser_has_all_permissions(self):
        superuser = User.objects.create_superuser(
            email='admin@test.com',
            password='adminpass123'
        )
        self.assertTrue(
            PermissionService.user_has_permission(superuser, self.venue, 'view_orders')
        )


class PermissionAPITests(TestCase):
    """Tests for RBAC API endpoints."""

    def setUp(self):
        self.client = APIClient()
        self.admin = User.objects.create_superuser(
            email='api_admin@test.com',
            password='adminpass123'
        )
        self.client.force_authenticate(user=self.admin)
        PermissionService.seed_default_permissions_and_roles()

    def test_list_permissions(self):
        response = self.client.get('/api/permissions/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertGreater(len(response.data['results']), 0)

    def test_list_roles(self):
        response = self.client.get('/api/roles/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertGreater(len(response.data['results']), 0)

    def test_create_role(self):
        response = self.client.post('/api/roles/', {
            'name': 'Custom Role',
            'description': 'A custom role',
            'permission_codes': ['view_orders', 'collect_cash']
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['name'], 'Custom Role')

    def test_assign_permission_to_role(self):
        role = Role.objects.first()
        response = self.client.post(f'/api/roles/{role.id}/assign_permission/', {
            'permission_code': 'view_orders'
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_remove_permission_from_role(self):
        role = Role.objects.first()
        perm = Permission.objects.get(code='view_orders')
        role.permissions.add(perm)
        response = self.client.post(f'/api/roles/{role.id}/remove_permission/', {
            'permission_code': 'view_orders'
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_my_permissions(self):
        response = self.client.get('/api/user-permissions/my_permissions/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('permissions', response.data)

    def test_seed_permissions_endpoint(self):
        # Clear existing
        Permission.objects.all().delete()
        Role.objects.all().delete()
        response = self.client.post('/api/permissions/seed/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(Permission.objects.filter(code='view_orders').exists())

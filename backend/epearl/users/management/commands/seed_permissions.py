# users/management/commands/seed_permissions.py

from django.core.management.base import BaseCommand
from users.services.permission_service import PermissionService


class Command(BaseCommand):
    help = 'Seed default permissions and roles for the E-Pearl RBAC system'

    def handle(self, *args, **options):
        self.stdout.write('Seeding default permissions and roles...')
        PermissionService.seed_default_permissions_and_roles()
        self.stdout.write(self.style.SUCCESS('Successfully seeded default permissions and roles.'))

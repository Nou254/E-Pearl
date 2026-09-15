# users/services/permission_service.py

from ..models import Permission, Role, UserRole, UserPermission


class PermissionService:
    """
    Service to check and manage user permissions per venue.
    """

    @classmethod
    def get_user_permissions(cls, user, venue):
        """
        Get all permission codes for a user at a specific venue.
        """
        if not user or not venue:
            return set()

        # Start with permissions from roles
        roles = UserRole.objects.filter(user=user, venue=venue).select_related('role')
        perm_codes = set()
        for user_role in roles:
            for perm in user_role.role.permissions.all():
                perm_codes.add(perm.code)

        # Apply direct user permissions (overrides)
        direct_perms = UserPermission.objects.filter(user=user, venue=venue)
        for up in direct_perms:
            if up.is_granted:
                perm_codes.add(up.permission.code)
            else:
                perm_codes.discard(up.permission.code)

        return perm_codes

    @classmethod
    def user_has_permission(cls, user, venue, permission_code):
        """
        Check if a user has a specific permission at a venue.
        """
        if not user or not venue:
            return False
        # Superusers have all permissions
        if user.is_superuser:
            return True
        # Platform admins have all permissions (optional)
        if user.user_type in ['admin', 'support']:
            return True
        perms = cls.get_user_permissions(user, venue)
        return permission_code in perms

    @classmethod
    def assign_role(cls, user, venue, role_name):
        """
        Assign a role to a user for a venue.
        """
        try:
            role = Role.objects.get(name=role_name)
        except Role.DoesNotExist:
            raise ValueError(f"Role '{role_name}' does not exist.")
        user_role, created = UserRole.objects.get_or_create(
            user=user, venue=venue, role=role
        )
        return user_role

    @classmethod
    def assign_permission(cls, user, venue, permission_code, granted=True):
        """
        Directly assign (or revoke) a permission for a user at a venue.
        """
        try:
            permission = Permission.objects.get(code=permission_code)
        except Permission.DoesNotExist:
            raise ValueError(f"Permission '{permission_code}' does not exist.")

        user_perm, created = UserPermission.objects.get_or_create(
            user=user, venue=venue, permission=permission,
            defaults={'is_granted': granted}
        )
        if not created and user_perm.is_granted != granted:
            user_perm.is_granted = granted
            user_perm.save()
        return user_perm

    @classmethod
    def get_default_permissions_for_staff_role(cls, staff_role):
        """
        Return a list of permission codes for a given staff role (waiter, chef, etc.)
        """
        default_map = {
            'waiter': [
                'view_assigned_tables', 'collect_cash', 'mark_served',
                'request_cover', 'cut_off_host', 'view_orders',
            ],
            'chef': [
                'access_kitchen_display', 'mark_ready', 'trigger_stock_alert',
                'view_orders',
            ],
            'bartender': [
                'access_bar_display', 'mark_poured', 'trigger_stock_alert',
                'view_orders', 'serve_directly',
            ],
            'security': [
                'scan_exit', 'scan_ticket', 'staff_scan_in', 'staff_scan_out',
            ],
            'receptionist': [
                'manage_bookings', 'check_in_guest', 'view_orders',
            ],
            'cashier': [
                'collect_cash', 'view_financial_reports', 'view_orders',
            ],
            'event_coordinator': [
                'manage_events', 'view_ticket_sales',
            ],
            'inventory_officer': [
                'trigger_stock_alert',
            ],
            'accountant': [
                'view_financial_reports', 'generate_reports',
            ],
            'assistant_manager': [
                'manage_staff', 'manage_menu', 'manage_tables',
                'reconcile_cash', 'view_all_orders', 'view_all_tables',
                'view_audit_log', 'manage_public_profile',
                # Include waiter permissions (they can cover)
                'view_assigned_tables', 'collect_cash', 'mark_served',
            ],
            'manager': [
                'manage_staff', 'manage_menu', 'manage_tables', 'manage_events',
                'view_financial_reports', 'force_capture', 'void_hold',
                'override_exit', 'suspend_table', 'reconcile_cash',
                'view_all_orders', 'view_all_tables', 'view_audit_log',
                'manage_public_profile', 'manage_shifts',
                # Include waiter permissions
                'view_assigned_tables', 'collect_cash', 'mark_served',
            ],
            'owner': [],  # Owner gets all permissions via special check
        }
        return default_map.get(staff_role, [])

    @classmethod
    def seed_default_permissions_and_roles(cls):
        """
        Seed default permissions and roles (call during initial setup).
        """
        # Define all permissions
        permission_defs = [
            # Staff/Operational
            ('view_assigned_tables', 'View assigned tables'),
            ('collect_cash', 'Collect cash from guests'),
            ('mark_served', 'Mark order items as served'),
            ('request_cover', 'Request cover from another waiter'),
            ('cut_off_host', 'Flag host as intoxicated'),
            ('view_orders', 'View orders'),
            ('access_kitchen_display', 'Access kitchen display'),
            ('mark_ready', 'Mark order as ready'),
            ('trigger_stock_alert', 'Trigger stock depletion alert'),
            ('access_bar_display', 'Access bar display'),
            ('mark_poured', 'Mark drink as poured'),
            ('serve_directly', 'Serve drinks directly to bar guests'),
            ('scan_exit', 'Scan exit QR codes'),
            ('scan_ticket', 'Scan event tickets'),
            ('staff_scan_in', 'Scan in staff'),
            ('staff_scan_out', 'Scan out staff'),
            ('manage_bookings', 'Manage bookings and check-ins'),
            ('check_in_guest', 'Check in guests'),
            # Manager/Admin
            ('manage_staff', 'Manage staff accounts'),
            ('manage_menu', 'Manage menu categories and items'),
            ('manage_tables', 'Manage tables and zones'),
            ('manage_events', 'Create and manage events'),
            ('view_financial_reports', 'View financial reports'),
            ('force_capture', 'Execute force capture'),
            ('void_hold', 'Void pre-authorization hold'),
            ('override_exit', 'Manually override guest exit'),
            ('suspend_table', 'Suspend a table'),
            ('reconcile_cash', 'Reconcile staff cash'),
            ('view_all_orders', 'View all orders in venue'),
            ('view_all_tables', 'View all tables in venue'),
            ('manage_shifts', 'Manage shift definitions'),
            # Owner-specific
            ('manage_subscription', 'Manage venue subscription'),
            ('terminate_contract', 'Terminate manager contract'),
            # Additional
            ('view_audit_log', 'View audit log'),
            ('manage_public_profile', 'Manage public venue profile'),
            ('generate_reports', 'Generate financial reports'),
        ]

        # Create permissions
        for code, name in permission_defs:
            Permission.objects.get_or_create(code=code, defaults={'name': name})

        # Define roles with permission lists
        role_defs = {
            'Waiter': ['view_assigned_tables', 'collect_cash', 'mark_served',
                       'request_cover', 'cut_off_host', 'view_orders'],
            'Chef': ['access_kitchen_display', 'mark_ready', 'trigger_stock_alert', 'view_orders'],
            'Bartender': ['access_bar_display', 'mark_poured', 'trigger_stock_alert',
                          'view_orders', 'serve_directly'],
            'Security': ['scan_exit', 'scan_ticket', 'staff_scan_in', 'staff_scan_out'],
            'Receptionist': ['manage_bookings', 'check_in_guest', 'view_orders'],
            'Cashier': ['collect_cash', 'view_financial_reports', 'view_orders'],
            'Event Coordinator': ['manage_events', 'view_ticket_sales'],
            'Inventory Officer': ['trigger_stock_alert'],
            'Accountant': ['view_financial_reports', 'generate_reports'],
            'Assistant Manager': [
                'manage_staff', 'manage_menu', 'manage_tables',
                'reconcile_cash', 'view_all_orders', 'view_all_tables',
                'view_audit_log', 'manage_public_profile',
                'view_assigned_tables', 'collect_cash', 'mark_served',
            ],
            'Manager': [
                'manage_staff', 'manage_menu', 'manage_tables', 'manage_events',
                'view_financial_reports', 'force_capture', 'void_hold',
                'override_exit', 'suspend_table', 'reconcile_cash',
                'view_all_orders', 'view_all_tables', 'view_audit_log',
                'manage_public_profile', 'manage_shifts',
                'view_assigned_tables', 'collect_cash', 'mark_served',
            ],
            'Owner': [],  # Owner gets all permissions via a special check; role can be empty
        }

        for role_name, perm_codes in role_defs.items():
            role, _ = Role.objects.get_or_create(name=role_name)
            perms = Permission.objects.filter(code__in=perm_codes)
            role.permissions.set(perms)
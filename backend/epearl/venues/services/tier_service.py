# venues/services/tier_service.py

from django.conf import settings
from django.db.models import Count


class TierService:
    """
    Service to enforce subscription tier limits.
    """
    
    # Tier definitions (matches settings.SUBSCRIPTION_TIERS)
    TIER_LIMITS = {
        'seed': {
            'max_tables': 5,
            'max_staff': 5,
            'modules': ['Guest', 'Host', 'Cook', 'Pour'],  # No Serve/Gate/Explore/Tickets
        },
        'spark': {
            'max_tables': 15,
            'max_staff': 15,
            'modules': ['Guest', 'Host', 'Cook', 'Pour', 'Serve', 'Gate'],
        },
        'rose': {
            'max_tables': 999,
            'max_staff': 999,
            'modules': ['Guest', 'Host', 'Cook', 'Pour', 'Serve', 'Gate', 'Explore', 'Tickets'],
        },
        'summit': {
            'max_tables': 999,
            'max_staff': 999,
            'modules': ['Guest', 'Host', 'Cook', 'Pour', 'Serve', 'Gate', 'Explore', 'Tickets'],
            # Summit adds advanced analytics, inventory, host mode, etc. – enforced via permissions (RBAC)
        },
        'elite': {
            'max_tables': 999,
            'max_staff': 999,
            'modules': ['Guest', 'Host', 'Cook', 'Pour', 'Serve', 'Gate', 'Explore', 'Tickets'],
            # Elite adds multi-branch, API, white-label – enforced via permissions
        },
        'legacy': {
            'max_tables': 999,
            'max_staff': 999,
            'modules': ['Guest', 'Host', 'Cook', 'Pour', 'Serve', 'Gate', 'Explore', 'Tickets'],
            # Legacy adds custom development, VIP support
        },
    }

    @classmethod
    def get_limits(cls, tier):
        """Return the limits dictionary for a given tier."""
        return cls.TIER_LIMITS.get(tier, cls.TIER_LIMITS['seed'])

    @classmethod
    def get_max_limit(cls, tier, resource):
        """
        Get the maximum allowed count for a resource.
        Resource can be 'max_tables' or 'max_staff'.
        """
        limits = cls.get_limits(tier)
        return limits.get(resource, 999)

    @classmethod
    def get_current_counts(cls, venue):
        """
        Return a dictionary with current usage counts.
        """
        from staff.models import Staff  # avoid circular import
        from tables.models import Table

        return {
            'tables': Table.objects.filter(venue=venue).count(),
            'staff': Staff.objects.filter(venue=venue, is_active=True).count(),
        }

    @classmethod
    def can_add_table(cls, venue):
        """Check if the venue can add more tables."""
        max_tables = cls.get_max_limit(venue.subscription_tier, 'max_tables')
        current = cls.get_current_counts(venue)['tables']
        return current < max_tables

    @classmethod
    def can_add_staff(cls, venue):
        """Check if the venue can add more staff."""
        max_staff = cls.get_max_limit(venue.subscription_tier, 'max_staff')
        current = cls.get_current_counts(venue)['staff']
        return current < max_staff

    @classmethod
    def has_module_access(cls, venue, module_name):
        """
        Check if the venue's tier allows access to a specific module.
        Module names should match the keys in the TIER_LIMITS (e.g., 'Serve', 'Gate').
        """
        allowed_modules = cls.get_limits(venue.subscription_tier).get('modules', [])
        return module_name in allowed_modules

    @classmethod
    def get_usage_dashboard(cls, venue):
        """
        Return a full dashboard of usage vs limits for the venue.
        """
        limits = cls.get_limits(venue.subscription_tier)
        counts = cls.get_current_counts(venue)
        return {
            'tier': venue.subscription_tier,
            'limits': {
                'tables': limits.get('max_tables'),
                'staff': limits.get('max_staff'),
            },
            'usage': {
                'tables': counts['tables'],
                'staff': counts['staff'],
            },
            'modules': limits.get('modules', []),
            'is_at_capacity': {
                'tables': counts['tables'] >= limits.get('max_tables', 999),
                'staff': counts['staff'] >= limits.get('max_staff', 999),
            }
        }
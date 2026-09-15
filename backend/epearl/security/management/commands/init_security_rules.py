from django.core.management.base import BaseCommand
from security.models import SecurityRule

class Command(BaseCommand):
    help = 'Initialize default security rules'

    def handle(self, *args, **options):
        rules = [
            {
                'name': 'Rate Limit per IP',
                'rule_type': 'rate_limit',
                'severity': 'medium',
                'priority': 10,
                'conditions': {'limit': 100, 'window': 60, 'key': 'ip'},
                'enabled': True,
            },
            {
                'name': 'Block common SQL injection patterns',
                'rule_type': 'sql_injection',
                'severity': 'high',
                'priority': 20,
                'conditions': {},
                'enabled': True,
            },
            {
                'name': 'Block XSS patterns',
                'rule_type': 'xss',
                'severity': 'high',
                'priority': 30,
                'conditions': {},
                'enabled': True,
            },
            {
                'name': 'Block path traversal attempts',
                'rule_type': 'path_traversal',
                'severity': 'high',
                'priority': 40,
                'conditions': {},
                'enabled': True,
            },
            {
                'name': 'Block curl user-agent',
                'rule_type': 'user_agent_block',
                'severity': 'low',
                'priority': 50,
                'conditions': {'agents': ['curl', 'python-requests']},
                'enabled': False,  # disabled by default
            },
            {
                'name': 'Restrict waiter role to guest endpoints',
                'rule_type': 'role_endpoint',
                'severity': 'medium',
                'priority': 60,
                'conditions': {'allowed_roles': ['admin', 'manager', 'owner'], 'paths': ['/api/manager/']},
                'enabled': True,
            },
        ]
        for rule_data in rules:
            SecurityRule.objects.get_or_create(name=rule_data['name'], defaults=rule_data)
        self.stdout.write(self.style.SUCCESS('Security rules initialized'))
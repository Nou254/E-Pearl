from django.core.management.base import BaseCommand
from django.urls import get_resolver, URLPattern, URLResolver


class Command(BaseCommand):
    help = 'List all API endpoints with paths, names, and view classes'

    def handle(self, *args, **options):
        endpoints = []

        def extract(resolver, prefix=''):
            for p in resolver.url_patterns:
                if isinstance(p, URLPattern):
                    raw = str(p.pattern)
                    if raw.startswith('^'):
                        raw = raw[1:]
                    if raw.endswith('$'):
                        raw = raw[:-1]
                    endpoints.append({
                        'path': prefix + raw,
                        'name': p.name or '--',
                        'view': str(p.callback)
                    })
                elif isinstance(p, URLResolver):
                    extract(p, prefix + str(p.pattern))

        extract(get_resolver())

        # Filter only API endpoints (paths containing 'api/')
        api_endpoints = [e for e in endpoints if 'api/' in e['path']]
        api_endpoints.sort(key=lambda x: x['path'])

        self.stdout.write('\nAPI Endpoints:\n')
        self.stdout.write('=' * 80)
        for e in api_endpoints:
            # Truncate view name if too long
            view = e['view'][:80] + '...' if len(e['view']) > 80 else e['view']
            self.stdout.write(f"{e['path']:<50} [{e['name']:<15}] -> {view}")

        self.stdout.write('\n' + '=' * 80)
        self.stdout.write(f'Total: {len(api_endpoints)} API endpoints')
# list_api.py – prints all API endpoints (fixed)

import re
from django.urls import get_resolver, URLPattern, URLResolver

endpoints = []

def extract(resolver, prefix=''):
    for p in resolver.url_patterns:
        if isinstance(p, URLPattern):
            # Get raw pattern string, strip ^ and $
            raw = str(p.pattern)
            if raw.startswith('^'):
                raw = raw[1:]
            if raw.endswith('$'):
                raw = raw[:-1]
            # Build full path
            path = prefix + raw
            endpoints.append({
                'path': path,
                'name': p.name,
                'view': str(p.callback)
            })
        elif isinstance(p, URLResolver):
            extract(p, prefix + str(p.pattern))

extract(get_resolver())

# Filter paths that contain 'api/' (anywhere)
api_endpoints = [e for e in endpoints if 'api/' in e['path']]

print("\n🔍 API Endpoints:\n")
for e in sorted(api_endpoints, key=lambda x: x['path']):
    name = e['name'] or '--'
    view = e['view'][:80] + '...' if len(e['view']) > 80 else e['view']
    print(f"{e['path']:<50} [{name:<15}] -> {view}")

print(f"\n✅ Total: {len(api_endpoints)} API endpoints")
from django.core.cache import cache
cache.set('test', 'Hello Redis!', 60)
print(cache.get('test'))  # Should print: Hello Redis!
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'PrenoPinzo.settings')
django.setup()

from django.urls import get_resolver

resolver = get_resolver()
print("All registered URLs:")
print("-" * 50)

def show_urls(urlpatterns, prefix=''):
    for pattern in urlpatterns:
        if hasattr(pattern, 'url_patterns'):
            show_urls(pattern.url_patterns, prefix + str(pattern.pattern))
        else:
            print(f"{prefix}{pattern.pattern}")

show_urls(resolver.url_patterns)

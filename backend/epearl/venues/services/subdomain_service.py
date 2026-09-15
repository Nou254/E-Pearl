# venues/services/subdomain_service.py

import re
from ..models import Venue

class SubdomainService:
    @staticmethod
    def generate_subdomain(business_name):
        """
        Generate a unique subdomain from the business name.
        If the base subdomain exists, append a number.
        """
        base = re.sub(r'[^a-zA-Z0-9]', '-', business_name).lower()
        subdomain = base
        counter = 1
        while Venue.objects.filter(sub_domain=subdomain).exists():
            subdomain = f"{base}-{counter}"
            counter += 1
        return subdomain
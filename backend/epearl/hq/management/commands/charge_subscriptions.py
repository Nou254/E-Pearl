# hq/management/commands/charge_subscriptions.py

from django.core.management.base import BaseCommand
from hq.services.billing_service import BillingService


class Command(BaseCommand):
    help = 'Charge all active venue subscriptions'

    def handle(self, *args, **options):
        self.stdout.write('Starting subscription billing...')
        BillingService.charge_subscriptions()
        self.stdout.write(self.style.SUCCESS('Billing completed.'))
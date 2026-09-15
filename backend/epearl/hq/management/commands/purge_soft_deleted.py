# hq/management/commands/purge_soft_deleted.py

from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from hq.models import RequestLog


class Command(BaseCommand):
    help = 'Permanently delete soft-deleted records older than 90 days.'

    def handle(self, *args, **options):
        cutoff = timezone.now() - timedelta(days=90)
        deleted_logs = RequestLog.objects.filter(
            is_deleted=True,
            deleted_at__lte=cutoff
        )

        count = deleted_logs.count()
        if count == 0:
            self.stdout.write(self.style.SUCCESS('No records to purge.'))
            return

        # Confirm before deletion (optional)
        self.stdout.write(f"Found {count} records to permanently delete.")
        confirm = input("Are you sure you want to permanently delete these records? [y/N]: ")
        if confirm.lower() != 'y':
            self.stdout.write("Operation cancelled.")
            return

        deleted_logs.delete()  # hard delete
        self.stdout.write(self.style.SUCCESS(f"Successfully purged {count} records."))
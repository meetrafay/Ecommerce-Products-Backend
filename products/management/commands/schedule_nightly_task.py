from django.core.management.base import BaseCommand
from django_celery_beat.models import PeriodicTask, CrontabSchedule
import json

class Command(BaseCommand):
    help = 'Schedule nightly inventory update task'

    def handle(self, *args, **options):
        # Read mock CSV content
        with open('data/mock_products.csv', 'r') as f:
            csv_content = f.read()

        # Create or update crontab schedule (run daily at midnight)
        schedule, _ = CrontabSchedule.objects.get_or_create(
            minute='0',
            hour='0',
            day_of_week='*',
            day_of_month='*',
            month_of_year='*'
        )

        # Create or update periodic task
        PeriodicTask.objects.update_or_create(
            name='Nightly Inventory Update',
            defaults={
                'crontab': schedule,
                'task': 'products.tasks.nightly_inventory_update',
                'args': json.dumps([csv_content])
            }
        )
        self.stdout.write(self.style.SUCCESS('Nightly inventory update task scheduled successfully'))
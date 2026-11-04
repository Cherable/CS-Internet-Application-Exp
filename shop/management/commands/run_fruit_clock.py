import time
from django.core.management import call_command
from django.core.management.base import BaseCommand
from django.utils import timezone
class Command(BaseCommand):
    help = "Update fruit simulation once per Beijing calendar day while this worker runs"
    def handle(self, *args, **options):
        last = None
        while True:
            today = timezone.localdate()
            if today != last:
                call_command("update_fruit_market")
                call_command("sync_exchange_rates")
                last = today
            time.sleep(30)

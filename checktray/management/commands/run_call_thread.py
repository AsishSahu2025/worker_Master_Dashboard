from django.core.management.base import BaseCommand
from checktray.daily_call_scheduler import start_daily_call_thread


class Command(BaseCommand):
    help = "Run scheduler threads"

    def handle(self, *args, **kwargs):
        print("🚀 Starting scheduler...")

        start_daily_call_thread()

        # keep process alive
        import time
        while True:
            time.sleep(60)
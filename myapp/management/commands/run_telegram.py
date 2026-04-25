from django.core.management.base import BaseCommand
import threading
import time
from myapp.telegram_worker import telegram_worker


class Command(BaseCommand):
    help = "Run MyApp Telegram notification worker"

    def handle(self, *args, **options):
        self.stdout.write("Starting MyApp Telegram worker...")

        # Start telegram_worker as daemon thread
        threading.Thread(
            target=telegram_worker,
            daemon=True
        ).start()

        self.stdout.write(self.style.SUCCESS("✅ Telegram worker started"))

        # Keep command alive
        while True:
            time.sleep(60)

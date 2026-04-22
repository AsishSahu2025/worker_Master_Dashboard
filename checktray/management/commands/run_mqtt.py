from django.core.management.base import BaseCommand
import threading
import time
# from app1.mqtt_worker import worker_loop
# from app1.db_worker import db_worker_loop

import checktray.paho_mqtt as paho_mqtt
from myapp.models import Device
from checktray.mqtt_command_worker import mqtt_command_worker
from checktray.telegram_worker import telegram_worker
from checktray.paho_mqtt import cleanup_stale_running_schedules, scheduler_loop, watchdog_loop


class Command(BaseCommand):
    help = "Run MQTT subscriber and background services"

    def handle(self, *args, **options):
        self.stdout.write("Starting MQTT services...")

        # Cleanup after restart
        cleanup_stale_running_schedules()

        # Start MQTT
        paho_mqtt.start_mqtt_client()
        while not paho_mqtt.mqtt_connected:
            print('not connected')
            time.sleep(1)
        # threading.Thread(
        #     target=start_mqtt_client,
        #     daemon=True
        # ).start()

        # Start scheduler
        threading.Thread(
            target=scheduler_loop,
            daemon=True
        ).start()

        threading.Thread(target=watchdog_loop, daemon=True).start()
        threading.Thread(
            target=mqtt_command_worker,
            daemon=True
        ).start()
        threading.Thread(
            target=telegram_worker,
            daemon=True
        ).start()

        # Keep command alive
        while True:
            time.sleep(60)

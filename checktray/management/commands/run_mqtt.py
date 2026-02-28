from django.core.management.base import BaseCommand
import threading
import time
# from app1.mqtt_worker import worker_loop
# from app1.db_worker import db_worker_loop

from checktray.paho_mqtt import *
from myapp.models import Device


class Command(BaseCommand):
    help = "Run MQTT subscriber and background services"

    def handle(self, *args, **options):
        self.stdout.write("Starting MQTT services...")

        # Cleanup after restart
        cleanup_stale_running_schedules()

        # threading.Thread(
        #     target=worker_loop,
        #     daemon=True
        # ).start()

        # print("[WORKER] Background DB worker started")

        # for _ in range(2):
        #     threading.Thread(
        #         target=worker_loop,
        #         daemon=True
        #     ).start()
        # print("[WORKER] Processing workers started")

        # # -------------------------
        # # DB workers
        # # -------------------------
        # for _ in range(3):
        #     threading.Thread(
        #         target=db_worker_loop,
        #         daemon=True
        #     ).start()
        # print("[WORKER] DB writers started")



        # Start MQTT
        threading.Thread(
            target=start_mqtt_client,
            daemon=True
        ).start()

        # Start scheduler
        threading.Thread(
            target=scheduler_loop,
            daemon=True
        ).start()

        # Start watchdog per device
        for device in Device.objects.all():
            threading.Thread(
                target=device_offline_watchdog,
                args=(device,),
                daemon=True
            ).start()

        # Keep command alive
        while True:
            time.sleep(60)

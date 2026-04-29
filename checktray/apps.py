# from django.apps import AppConfig


# class ChecktrayConfig(AppConfig):
#     default_auto_field = 'django.db.models.BigAutoField'
#     name = 'checktray'

#     def ready(self):
#         import checktray.signals

from django.apps import AppConfig
import threading
import os


class ChecktrayConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'checktray'

    def ready(self):
        # ── Prevent double execution from Django autoreloader ──
        import checktray.signals

        # ── daily morning call thread ──

        if os.environ.get("RUN_MAIN") == "true" or os.environ.get("RUN_MAIN") is None:
            from checktray.daily_call_scheduler import start_daily_call_thread
            start_daily_call_thread()
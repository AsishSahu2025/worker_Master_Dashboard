# from django.apps import AppConfig


# class ChecktrayConfig(AppConfig):
#     default_auto_field = 'django.db.models.BigAutoField'
#     name = 'checktray'

#     def ready(self):
#         import checktray.signals

from django.apps import AppConfig
import os


class ChecktrayConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'checktray'

    def ready(self):
        # ── Prevent double execution from Django autoreloader ──
        if os.environ.get("RUN_MAIN") != "true":
            return

        import checktray.signals

        # ── daily morning call thread ──
        from checktray.daily_call_scheduler import start_daily_call_thread
        start_daily_call_thread()
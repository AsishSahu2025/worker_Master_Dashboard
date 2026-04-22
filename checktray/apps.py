from django.apps import AppConfig


class ChecktrayConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'checktray'

    def ready(self):
        import checktray.debug_update_tracker
        import checktray.signals
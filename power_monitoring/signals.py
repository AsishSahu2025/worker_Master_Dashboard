# from django.db.models.signals import pre_save
# from django.dispatch import receiver
# from checktray.models import ChecktrayTask
# from power_monitoring.utils.telegram_cards import notify_power_schedule


# @receiver(pre_save, sender=ChecktrayTask)
# def trigger_on_status_change(sender, instance, **kwargs):
#     if instance.pk:
#         try:
#             old = ChecktrayTask.objects.get(pk=instance.pk)
#         except ChecktrayTask.DoesNotExist:
#             return

#         if old.status != instance.status:
#             notify_power_schedule(instance.id, instance.cycles)

from django.db.models.signals import post_save
from django.dispatch import receiver
from power_monitoring.models import MonitoringSession
from power_monitoring.utils.telegram_cards import notify_power_schedule


@receiver(post_save, sender=MonitoringSession)
def send_schedule_on_create(sender, instance, created, **kwargs):
    if created:
        notify_power_schedule(
            device_id=instance.device.device_id,
            sessions=[instance]
        )
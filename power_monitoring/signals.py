from django.db.models.signals import pre_save
from django.dispatch import receiver
from checktray.models import ChecktrayTask
from power_monitoring.utils.telegram_cards import notify_power_schedule


@receiver(pre_save, sender=ChecktrayTask)
def trigger_on_status_change(sender, instance, **kwargs):
    if instance.pk:
        try:
            old = ChecktrayTask.objects.get(pk=instance.pk)
        except ChecktrayTask.DoesNotExist:
            return

        if old.status != instance.status:
            notify_power_schedule(instance.id, instance.cycles)
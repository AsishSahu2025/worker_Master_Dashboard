from django.db import transaction
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver

from checktray.models import ChecktrayTask
from checktray.telegram_notifications import notify_checktray_task
from checktray.telegram_queue import enqueue_telegram


@receiver(pre_save, sender=ChecktrayTask)
def checktray_task_cache_prev_status(sender, instance, **kwargs):
    if not instance.pk:
        instance._checktray_prev_status = None
        return
    try:
        instance._checktray_prev_status = (
            ChecktrayTask.objects.only("status").get(pk=instance.pk).status
        )
    except ChecktrayTask.DoesNotExist:
        instance._checktray_prev_status = None


@receiver(post_save, sender=ChecktrayTask)
def checktray_task_notify_running_completed(sender, instance, created, **kwargs):
    """Send the same Telegram card whenever status becomes Running or Completed (DB save, not QuerySet.update)."""
    cur = (instance.status or "").strip()
    if cur != "Completed":
        return
    prev = getattr(instance, "_checktray_prev_status", None)

    # ✅ Only trigger on actual transition
    if prev == "Completed":
        return
    print("🚨 SIGNAL CALLED:", instance.id, instance.status, id(instance))
    updated = ChecktrayTask.objects.filter(
        id=instance.id,
        notified=False
    ).update(notified=True)

    if not updated:
        return
    transaction.on_commit(lambda: enqueue_telegram(instance.pk))

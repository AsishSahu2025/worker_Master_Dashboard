from django.db import models
from django.utils import timezone
from django.db.models import Sum, F
from datetime import timedelta

from myapp.models import Device, Worker_details


# ================= MONITORING SESSION ================= #
class MonitoringSession(models.Model):

    STATUS_CHOICES = [
        ("PENDING", "Pending"),
        ("PROCESSING", "Processing"),
        ("COMPLETED", "Completed"),
        ("FAILED", "Failed"),
        ("ABORTED", "Aborted"),
    ]

    device = models.ForeignKey(
        Device,
        on_delete=models.CASCADE,
        related_name="monitoring_sessions"
    )
    cycle_number = models.IntegerField(default=1)
    worker = models.ForeignKey(
        Worker_details,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="sessions"
    )

    start_time = models.DateTimeField(null=True, blank=True)
    end_time = models.DateTimeField(null=True, blank=True)
    duration = models.DurationField(null=True, blank=True)

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="PENDING",
        db_index=True
    )

    total_wh = models.FloatField(default=0)

    description = models.CharField(max_length=255, blank=True)

    main = models.IntegerField(default=1)

    created_at = models.DateTimeField(auto_now_add=True)


    class Meta:
        unique_together = ("device", "cycle_number")

    # ================= SAFE VALIDATION ================= #
    def save(self, *args, **kwargs):

        if not self.device:
            raise ValueError("Device is required")

        if self.start_time and self.end_time:

            if self.start_time >= self.end_time:
                raise ValueError("End time must be greater than start time")

            if self.main not in [1, 2]:
                raise ValueError("Main must be 1 or 2")

            self.duration = self.end_time - self.start_time

        super().save(*args, **kwargs)

    # ================= ABORT ================= #
    def abort(self):
        if self.status in ["COMPLETED", "FAILED", "ABORTED"]:
            return False

        now = timezone.now()

        self.status = "ABORTED"
        self.end_time = now
        self.duration = now - (self.start_time or now)

        self.save(update_fields=["status", "end_time", "duration"])

        print(f"🛑 Session {self.id} ABORTED")
        return True

    # ================= STATUS UPDATE ================= #
    def update_status(self):
        now = timezone.now()

        if self.status in ["COMPLETED", "FAILED", "ABORTED"]:
            return

        if not self.start_time or not self.end_time:
            return

        has_data = self.readings.exists()

        if now < self.start_time:
            self.status = "PENDING"

        elif self.start_time <= now <= self.end_time:
            self.status = "PROCESSING"

        else:
            if has_data:
                self.status = "COMPLETED"
            else:
                if now > self.end_time + timedelta(seconds=20):
                    self.status = "FAILED"

        self.duration = self.end_time - self.start_time
        self.save(update_fields=["status", "duration"])

    # ================= TOTAL ENERGY ================= #
    def calculate_total_energy(self):
        return self.readings.aggregate(total=Sum("wh"))["total"] or 0

    def __str__(self):
        return f"{self.device.device_id} | Cycle {self.cycle_number} | {self.status}"


# ================= SENSOR DATA ================= #
class SensorData(models.Model):

    session = models.ForeignKey(
        MonitoringSession,
        on_delete=models.CASCADE,
        related_name="readings"
    )

    timestamp = models.DateTimeField()

    voltage_r = models.FloatField()
    voltage_y = models.FloatField()
    voltage_b = models.FloatField()

    current_r = models.FloatField()
    current_y = models.FloatField()
    current_b = models.FloatField()

    wh = models.FloatField(default=0)

    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):

        if self.session.status == "ABORTED":
            print(f"⛔ Ignored: Session {self.session.id} is ABORTED")
            return

        if not self.session.start_time:
            print(f"⛔ Ignored: Session {self.session.id} not scheduled")
            return

        is_new = self.pk is None
        super().save(*args, **kwargs)

        if is_new:
            MonitoringSession.objects.filter(id=self.session.id).update(
                total_wh=F("total_wh") + self.wh
            )

            print(f"⚡ Energy added: {self.wh} to Session {self.session.id}")

    def __str__(self):
        return f"{self.session.id} | {self.timestamp}"
    
# # ================= SYSTEM CONFIG ================= #
# class Configuration(models.Model):
#     sample_interval = models.IntegerField(default=5)
#     voltage_threshold = models.FloatField(default=250)
#     current_threshold = models.FloatField(default=100)
#     created_at = models.DateTimeField(auto_now_add=True)

#     def __str__(self):
#         return "System Configuration"


# # ================= ALERT LOG ================= #
# class AlertLog(models.Model):
#     session = models.ForeignKey(
#         MonitoringSession,
#         on_delete=models.CASCADE,
#         related_name="alerts"
#     )
#     timestamp = models.DateTimeField()
#     parameter = models.CharField(max_length=20)
#     phase = models.CharField(max_length=5)
#     value = models.FloatField()
#     threshold_value = models.FloatField()
#     alert_type = models.CharField(max_length=10)
#     severity = models.CharField(max_length=10)
#     message = models.TextField()
#     status = models.CharField(max_length=20, default="ACTIVE")
#     created_at = models.DateTimeField(auto_now_add=True)
#     updated_at = models.DateTimeField(auto_now=True)

#     def __str__(self):
#         return f"{self.parameter} {self.phase} Alert"
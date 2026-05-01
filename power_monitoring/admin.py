from django.contrib import admin
from .models import MonitoringSession, SensorData


@admin.register(MonitoringSession)
class MonitoringSessionAdmin(admin.ModelAdmin):
    list_display = ("id","device", "cycle_number", "main", "start_time", "end_time", "total_wh", "status", "worker", "mqtt_sent")
    list_filter = ("start_time",)
    search_fields = ("description",)


@admin.register(SensorData)
class SensorDataAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "session",
        "timestamp",
        "voltage_r",
        "voltage_y",
        "voltage_b",
        "current_r",
        "current_y",
        "current_b",
        "wh",
    )
    list_filter = ("timestamp", "session")
    search_fields = ("session__id",)


# @admin.register(Configuration)
# class ConfigurationAdmin(admin.ModelAdmin):
#     list_display = (
#         "id",
#         "sample_interval",
#         "voltage_threshold",
#         "current_threshold",
#     )


# @admin.register(AlertLog)
# class AlertLogAdmin(admin.ModelAdmin):
#     list_display = (
#         "id",
#         "session",
#         "timestamp",
#         "parameter",
#         "phase",
#         "value",
#         "threshold_value",
#         "alert_type",
#         "severity",
#         "status",
#     )

#     list_filter = (
#         "parameter",
#         "phase",
#         "severity",
#         "status",
#     )

#     search_fields = (
#         "parameter",
#         "phase",
#         "message",
#     )
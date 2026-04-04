# monitoring/serializers.py
from rest_framework import serializers
from .models import SensorData, MonitoringSession
from myapp.models import Device

class SensorDataSerializer(serializers.ModelSerializer):
    energy = serializers.SerializerMethodField()

    class Meta:
        model = SensorData
        fields = [
            "id",
            "timestamp",
            "voltage_r",
            "voltage_y",
            "voltage_b",
            "current_r",
            "current_y",
            "current_b",
            "energy",   
        ]

    def get_energy(self, obj):
        return round(obj.wh / 1000, 6)


class MonitoringSessionSerializer(serializers.ModelSerializer):
    device_id = serializers.CharField(write_only=True)
    readings = SensorDataSerializer(many=True, read_only=True)
    energy = serializers.SerializerMethodField()

    class Meta:
        model = MonitoringSession
        fields = "__all__"

    def get_energy(self, obj):
        return round(obj.total_wh / 1000, 4)

    def create(self, validated_data):
        # Pop device_id from incoming data
        device_id = validated_data.pop("device_id", None)
        if not device_id:
            raise serializers.ValidationError({"device_id": "This field is required"})

        try:
            device = Device.objects.get(device_id=device_id)
        except Device.DoesNotExist:
            raise serializers.ValidationError({"device_id": "Invalid device_id"})

        # Assign the actual ForeignKey
        validated_data["device"] = device

        # Create the MonitoringSession
        session = MonitoringSession.objects.create(**validated_data)
        return session
from rest_framework import serializers
from myapp.models import *

class DeviceSerializer(serializers.ModelSerializer):
    class Meta:
        model=Device
        fields="__all__"

class PondSerializer(serializers.ModelSerializer):
    device=DeviceSerializer(many=True)
    class Meta:
        model=Pond
        fields=['id','name','latlong','location','area','address','device']
class ClusterPondSerializer(serializers.ModelSerializer):
    pond=PondSerializer(many=True,source='ponds')
    class Meta:
        model=Cluster
        fields=['id','pond']
        
class Task_Of_PondDeviceSerializer(serializers.Serializer):
    class Meta:
        model=Task
        fields="__all__"




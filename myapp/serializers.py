from rest_framework import serializers
from .models import *
from django.utils import timezone
from datetime import datetime, timedelta

############### clusterpond_analytic serializer #######################

class DeviceSerializer(serializers.ModelSerializer):
    class Meta:
        model=Device
        fields=['device_id','device_type','maxCycles']
#-------------------------------------------------------------------------

class PondDeviceSerializer(serializers.ModelSerializer):
    devices = serializers.SerializerMethodField()

    class Meta:
        model = Pond
        fields = ['devices']

    def get_devices(self, obj):
        devices = self.context.get('devices')
        return DeviceSerializer(devices, many=True).data
#-----------------------------------------------------------------------

class PondSerializer(serializers.ModelSerializer):
    class Meta:
        model=Pond
        fields="__all__"
class ClusterSerializer(serializers.ModelSerializer):
    pond=PondSerializer(many=True,read_only=True,source='ponds')
    class Meta:
        model=Cluster
        fields=['pond']
#-------------------------------------------------------------------------

class CycleStatusSerializer(serializers.ModelSerializer):
    class Meta:
        model=CycleStatus
        fields="__all__"
#-------------------------------------------------------------------------

class GenerateSerializer(serializers.Serializer):
    deviceName = serializers.CharField(max_length=100)
    deviceId = serializers.CharField(required=True)
    cycles = serializers.IntegerField(min_value=1, required=True)
    feedin=serializers.IntegerField(required=True)
    
#-------------------------------------------------------------------------

class FeedTryGenerateSerializer(serializers.Serializer):
    deviceName = serializers.CharField(max_length=100)
    deviceId = serializers.IntegerField(required=True)
    cycleCount = serializers.IntegerField(min_value=1, required=True)
    startTime = serializers.TimeField(required=True)
    hour_format = serializers.IntegerField(required=True)
    spray_type = serializers.CharField(max_length=20)
    def validate(self, data):
        if data['cycleCount'] > (data['hour_format'] // 2):
            raise serializers.ValidationError(
                "cycleCount must be less than (interval // 2)"
            )
        return data
    
#-------------------------------------------------------------------------
#############################################################################################################
import math
class TaskSubmitSerializer(serializers.ModelSerializer):
    worker_name = serializers.SlugRelatedField(
        queryset=Worker_details.objects.all(),
        slug_field='name',     
        required=True
    )
    from_time=serializers.TimeField()
    feed_weight = serializers.IntegerField()
    class Meta:
        model=Task
        fields = [
            'id',
            'worker_name',
            'from_time',
            'to_time',
            'feedin_percentage',
            'feed_weight',
            'status',
        ]
        read_only_fields = ['to_time', 'feedin_percentage', 'status']

    def validate(self, attrs):
        feed_weight=attrs.get('feed_weight')
        print("feed_weight",feed_weight)
        if not (feed_weight <= 100):
           raise serializers.ValidationError("Feed % not be greater the 100")
        return  attrs
    
    def update(self, instance, validated_data):
        cycleno=getattr(instance,"cycles")
        feedin_percentage = getattr(instance,"feedin_percentage")
        device=getattr(instance,'device')
        start_time=validated_data.get("from_time")
        id=getattr(instance,'id')
        feed_weight=None
        
        ###### Check the Current Cycle Completion #####################
        if Task.objects.filter(device=device, id=id).exists():
            PreTask=Task.objects.get(device=device, id=id)
            status=getattr(PreTask,'status')
            if status == "completed":
                raise serializers.ValidationError(f"C{cycleno} Already Completed")
            elif status == "abort":
                pass
        ############ Check the  Previous Cycle Completion #############
        checktime=True
        if cycleno>1:
            preid=id-1
            PreTask=Task.objects.get(device=device, id=preid)
            status=getattr(PreTask,'status')
            pre_end_time=getattr(PreTask,'to_time')
            if start_time is not None and pre_end_time is not None:
                checktime = pre_end_time < start_time
            else:
                checktime = False
            if not checktime:
                raise serializers.ValidationError(f"Plz Start the Cycle C{cycleno} After Completion of C{cycleno-1} ")
            
            if (status != "completed"):
                print(status)
                if status == "abort":
                    pass
                else:
                    raise serializers.ValidationError(f"C{cycleno-1} Till Not Completed")
            
        ####################### Validate the Feed_percentages ################
        feed_weight = validated_data.get('feed_weight')
        print('feed_weight=',feed_weight,'feedin_percentage=',feedin_percentage)
        if feed_weight > feedin_percentage:
            raise serializers.ValidationError(f"Feed_weight % Should be less then {feedin_percentage}%")
            
        ##################### Find last Task ############################ 
        last_task = Task.objects.filter(device=device).order_by('-id').first()
        cno=last_task.cycles
        last_task = Task.objects.filter(device=device,cycles=1).order_by('-id').first()
        feedin=float(getattr(last_task,"feedin"))
        print("Total Feedin:=",feedin)
        
        ################## Calculate Feedin, to_time ,time_interval############################ 
        feedin_percentage = feedin_percentage-feed_weight
        print('feed_weight=',feed_weight,'feedin_percentage=',feedin_percentage)
        
        use_feed=feedin*(feed_weight/100)*1000
        duration=math.ceil(use_feed/800)
        
        start_datetime = datetime.combine(datetime.today(), start_time)
        end_time = (start_datetime + timedelta(minutes=duration)).time()
        
        setattr(instance,"to_time",end_time)
        setattr(instance,"time_interval",duration)
        
        feedin =feedin*(feedin_percentage/100)
        print('feedin=',feedin)
        ################# Check the Feedin And Store to next Cycle #########
        task=None
        if feedin != 0 and cno != cycleno:
            task_id=id+1
            task=Task.objects.get(device=device, id=task_id)
            setattr(task,"feedin_percentage",feedin_percentage)
            setattr(instance,"restfeed",feedin)
            setattr(task,"feedin",feedin)
            task.save()
        else:
            setattr(instance,"restfeed",feedin)
        setattr(instance,"status","processing")
        ########################## Set the Given Data ########################
        for field,value in validated_data.items():
            setattr(instance,field,value)

        instance.save()
        self.context['feedin'] = feedin
        if feedin != 0:
            return instance,task
        else:
            return instance
##########################################################################################################       

class AbortSerializer(serializers.Serializer):
    status=serializers.CharField(max_length=100)
    def validate(self, attrs):
        status = attrs.get('status')
        if status != 'processing':
            raise serializers.ValidationError("Already Abort or Failed")
        return attrs


#################################### Auto Feed start ##############################################

class DeviceCommandStateSerializer(serializers.ModelSerializer):
    class Meta:
        model = DeviceCommandState
        fields = ["device_id", "step","task_id"]
        
#################################### AleartMessage start ##############################################

class AlertMessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = Alert_message
        fields = ["device_id", "alert"]
################################### Total Feed ####################################################
class TotalFeedSerializer(serializers.ModelSerializer):
    TotalFeed = serializers.CharField(source="feedin")
    class Meta:
        model = Task
        fields = ["device", "TotalFeed"]

class PondTaskSerializer(serializers.ModelSerializer):
    toggle = serializers.SerializerMethodField()
    class Meta:
        model = Task
        fields = "__all__" 
    def get_toggle(self, obj):
        # ON when status is processing
        return "ON" if obj.status.lower() == "processing" else "OFF"
    
########################################### Task Clear Serializer ##################################
class TaskClearSerializer(serializers.Serializer):
    device=serializers.CharField(max_length=50)
    
########################################## User Cluster ########################################
class ClusterSerializer(serializers.ModelSerializer):
    class Meta:
        model=Cluster
        fields="__all__"
class UserCluserSerializer(serializers.ModelSerializer):
    clusters = ClusterSerializer(many=True, read_only=True)
    class Meta:
        model=User
        fields=["clusters"]

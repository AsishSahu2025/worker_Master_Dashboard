from rest_framework import serializers
from .models import *
from datetime import datetime, timedelta
from django.db.models import Sum

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
    schedule_date = serializers.DateField(required=True)
    
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
            'time_interval',
            'feedin_percentage',
            'feed_weight',
            'status',
        ]
        read_only_fields = ['feedin_percentage']

    def validate(self, attrs):
        feed_weight=attrs.get('feed_weight')
        print("feed_weight",feed_weight)
        if not (feed_weight <= 100):
           raise serializers.ValidationError("Feed % not be greater the 100")
        return  attrs
    
    def update(self, instance, validated_data):
        instance.refresh_from_db()

        if validated_data.get("status") == "aborted":
            return instance

        cycleno = instance.cycles
        device = instance.device
        start_time = validated_data.get("from_time")
        schedule_date = instance.schedule_date

        if not schedule_date:
            raise serializers.ValidationError("schedule_date required")

        if not start_time:
            raise serializers.ValidationError("Start time required")

        now = datetime.now()
        today = schedule_date

        now_check = now.replace(second=0, microsecond=0)
        start_dt = datetime.combine(today, start_time)

        # ---------- TIME VALIDATION ----------
        if cycleno == 1:
            if today == now.date():
                min_allowed = now_check + timedelta(minutes=2)
                if start_dt < min_allowed:
                    raise serializers.ValidationError(
                        f"C1 must be after {min_allowed.time()}"
                    )
        else:
            prev = Task.objects.filter(
                device=device,
                schedule_date=schedule_date,
                batch_id=instance.batch_id,
                cycles=cycleno - 1
            ).first()

            if not prev or not prev.to_time:
                raise serializers.ValidationError("Previous cycle not ready")

            prev_dt = datetime.combine(today, prev.to_time)

            min_allowed = max(
                prev_dt + timedelta(minutes=2),
                now_check + timedelta(minutes=2)
            )

            if start_dt < min_allowed:
                raise serializers.ValidationError(
                    f"C{cycleno} must start after {min_allowed.time()}"
                )

        # ---------- OLD FEED LOGIC (UNCHANGED) ----------

        last_task = Task.objects.filter(
            device=device,
            schedule_date=schedule_date,
            batch_id=instance.batch_id,
        ).order_by("-cycles").first()

        if not last_task:
            raise serializers.ValidationError("No cycles found")

        cno = last_task.cycles

        first_task = Task.objects.filter(
            device=device,
            cycles=1,
            schedule_date=schedule_date,
            batch_id=instance.batch_id
        ).first()

        feedin = float(first_task.feedin or 0)
        total_feed = feedin

        feedin_percentage = instance.feedin_percentage
        if feedin_percentage is None:
            prev = Task.objects.filter(
                device=device,
                schedule_date=schedule_date,
                batch_id=instance.batch_id,
                cycles=cycleno - 1
            ).first()

            if prev and prev.feedin_percentage is not None:
                feedin_percentage = prev.feedin_percentage
            else:
                raise serializers.ValidationError(f"C{cycleno} not intialized")

        feed_weight = validated_data.get("feed_weight")
        if feed_weight is None:
            raise serializers.ValidationError("feed_weight required")

        # ---------- VALIDATION ----------
        if cycleno != cno and feed_weight > feedin_percentage:
            raise serializers.ValidationError("Feed weight too high")

        # ---------- LAST CYCLE (ORIGINAL LOGIC) ----------
        if cycleno == cno:
            used_percentage = Task.objects.filter(
                device=device,
                schedule_date=schedule_date,
                batch_id=instance.batch_id,
                cycles__lt=cycleno
            ).aggregate(total=Sum("feed_weight"))["total"] or 0
            remaining_percentage = max(0, 100 - float(used_percentage))

            feed_weight = remaining_percentage
            validated_data["feed_weight"] = remaining_percentage
            # 🔥 ALSO OVERRIDE TIME FOR LAST CYCLE
            use_feed = round(total_feed * (feed_weight / 100) * 1000, 2)
            duration = math.ceil(use_feed / 800)

            end_time = (
                datetime.combine(schedule_date, start_time) +
                timedelta(minutes=duration)
            ).time()

            validated_data["time_interval"] = duration
            validated_data["to_time"] = end_time

        # ---------- CALCULATION (DO NOT CHANGE) ----------
        feedin_percentage = max(0, feedin_percentage - feed_weight)
        remaining_feed = round(total_feed * (feedin_percentage / 100), 2)

        instance.to_time = validated_data.get("to_time")
        instance.time_interval = validated_data.get("time_interval")
        instance.restfeed = remaining_feed
        instance.status = "scheduled"

        # ---------- NEXT TASK (IMPORTANT: ID BASED CHAIN) ----------
        if remaining_feed != 0 and cno != cycleno:
            try:
                next_task = Task.objects.filter(
                    device=device,
                    schedule_date=schedule_date,
                    batch_id=instance.batch_id,
                    cycles=cycleno + 1
                ).first()

                next_task.feedin_percentage = feedin_percentage
                next_task.feedin = remaining_feed
                next_task.save()

                instance.restfeed = remaining_feed
            except Task.DoesNotExist:
                instance.restfeed = remaining_feed
        else:
            instance.restfeed = remaining_feed

        # ---------- SAVE ----------
        for field, value in validated_data.items():
            setattr(instance, field, value)

        instance.save()
        return instance
##################################################################################################    

class AbortSerializer(serializers.Serializer):
    status=serializers.CharField(max_length=100)
    def validate(self, attrs):
        status = attrs.get('status')
        if status != 'processing':
            raise serializers.ValidationError("Already Aborted or Failed")
        return attrs


#################################### Auto Feed start #############################################

class DeviceCommandStateSerializer(serializers.ModelSerializer):
    class Meta:
        model = DeviceCommandState
        fields = ["device_id", "step","task_id"]
        
#################################### AleartMessage start #########################################

class AlertMessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = Alert_message
        fields = ["device_id", "alert"]
################################### Total Feed ###################################################
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
    
########################################### Task Clear Serializer ################################
class TaskClearSerializer(serializers.Serializer):
    device=serializers.CharField(max_length=50)
    
########################################## User Cluster ##########################################
class ClusterSerializer(serializers.ModelSerializer):
    class Meta:
        model=Cluster
        fields="__all__"
class UserCluserSerializer(serializers.ModelSerializer):
    clusters = ClusterSerializer(many=True, read_only=True)
    class Meta:
        model=User
        fields=["clusters"]
##################################### Registration Serializers ##################################

#------------------------------- User  Serializer --------------------------

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = "__all__"
        
#------------------------------- User update Serializer ---------------------

class UserUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = "__all__"
        extra_kwargs = {
            field: {"required": False} for field in fields
        }

#---------------------------- Cluster Register Serializer -------------------

class ClusterRegisterSerializer(serializers.ModelSerializer):
    class Meta:
        model = Cluster
        fields = "__all__"
        
#------------------------------- Pond Register Serializer -----------------------

class PondRegisterSerializer(serializers.ModelSerializer):
    class Meta:
        model = Pond
        fields = "__all__"
    
#------------------------------- Manager Register Serializer ---------------------

class ManagerRegisterSerializer(serializers.ModelSerializer):
    class Meta:
        model = Manager
        fields = "__all__"
        
#------------------------------- BankDetails Register Serializer ------------------

class BankDetailsRegisterSerializer(serializers.ModelSerializer):
    class Meta:
        model = Bank_Details
        fields = "__all__"
        
        
#------------------------------- All Cluster of User Serializer ------------------

class ClusterSerializer(serializers.ModelSerializer):
    class Meta:
        model = Cluster
        fields = "__all__"

class UserClusterSerializer(serializers.ModelSerializer):
    clusters = ClusterSerializer(read_only = True, many =True)
    class Meta:
        model = User
        fields = ["Mob",'clusters']
    
#--------------------------- All Cluster and Pond of User Serializer ---------


class ClusterPondSerializer(serializers.ModelSerializer):
    ponds = PondRegisterSerializer(read_only = True,many = True)
    class Meta:
        model = Cluster
        fields = ['id','Name','ponds']

class UserClusterPondSerializer(serializers.ModelSerializer):
    clusters = ClusterPondSerializer(read_only = True,many = True)
    class Meta:
        model = User
        fields = ['Name',"clusters"]



        
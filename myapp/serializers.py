from rest_framework import serializers
from .models import *
from django.utils import timezone
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
# import math
# class TaskSubmitSerializer(serializers.ModelSerializer):
#     worker_name = serializers.SlugRelatedField(
#         queryset=Worker_details.objects.all(),
#         slug_field='name',     
#         required=True
#     )
#     from_time=serializers.TimeField()
#     feed_weight = serializers.IntegerField()
#     class Meta:
#         model=Task
#         fields = [
#             'id',
#             'worker_name',
#             'from_time',
#             'to_time',
#             'feedin_percentage',
#             'feed_weight',
#             'status',
#         ]
#         read_only_fields = ['to_time', 'feedin_percentage', 'status']

#     def validate(self, attrs):
#         feed_weight=attrs.get('feed_weight')
#         print("feed_weight",feed_weight)
#         if not (feed_weight <= 100):
#            raise serializers.ValidationError("Feed % not be greater the 100")
#         return  attrs
    
#     def update(self, instance, validated_data):
#         cycleno=getattr(instance,"cycles")
#         feedin_percentage = getattr(instance,"feedin_percentage")
#         device=getattr(instance,'device')
#         start_time=validated_data.get("from_time")
#         print(start_time)
#         id=getattr(instance,'id')
#         feed_weight=None
        
#         ###### Check the Current Cycle Completion #####################
#         if Task.objects.filter(device=device, id=id).exists():
#             PreTask=Task.objects.get(device=device, id=id)
#             status=getattr(PreTask,'status')
#             if status == "completed":
#                 raise serializers.ValidationError(f"C{cycleno} Already Completed")
#             elif status == "abort":
#                 pass
#         ############ Check the  Previous Cycle Completion #############
#         checktime=True
#         if cycleno>1:
#             preid=id-1
#             PreTask=Task.objects.get(device=device, id=preid)
#             status=getattr(PreTask,'status')
#             pre_end_time=getattr(PreTask,'to_time')
#             if start_time is not None and pre_end_time is not None:
#                 checktime = pre_end_time < start_time
#             else:
#                 checktime = False
#             if not checktime:
#                 raise serializers.ValidationError(f"Plz Start the Cycle C{cycleno} After Completion of C{cycleno-1} ")
            
#             if (status != "completed"):
#                 print(status)
#                 if status == "abort":
#                     pass
#                 else:
#                     raise serializers.ValidationError(f"C{cycleno-1} Till Not Completed")
            
#         ####################### Validate the Feed_percentages ################
#         feed_weight = validated_data.get('feed_weight')
#         print('feed_weight=',feed_weight,'feedin_percentage=',feedin_percentage)
#         if feed_weight > feedin_percentage:
#             raise serializers.ValidationError(f"Feed_weight % Should be less then {feedin_percentage}%")
            
#         ##################### Find last Task ############################ 
#         last_task = Task.objects.filter(device=device).order_by('-id').first()
#         cno=last_task.cycles
#         last_task = Task.objects.filter(device=device,cycles=1).order_by('-id').first()
#         feedin=float(getattr(last_task,"feedin"))
#         print("Total Feedin:=",feedin)
        
#         ################## Calculate Feedin, to_time ,time_interval############################ 
#         feedin_percentage = feedin_percentage-feed_weight
#         print('feed_weight=',feed_weight,'feedin_percentage=',feedin_percentage)
        
#         use_feed=feedin*(feed_weight/100)*1000
#         duration=math.ceil(use_feed/800)
#         # duration=(use_feed/800)
        
        
#         start_datetime = datetime.combine(datetime.today(), start_time)
#         end_time = (start_datetime + timedelta(minutes=duration)).time()
        
#         setattr(instance,"to_time",end_time)
#         setattr(instance,"time_interval",duration)
        
#         feedin =feedin*(feedin_percentage/100)
#         print('feedin=',feedin)
#         ################# Check the Feedin And Store to next Cycle #########
#         task=None
#         if feedin != 0 and cno != cycleno:
#             task_id=id+1
#             task=Task.objects.get(device=device, id=task_id)
#             setattr(task,"feedin_percentage",feedin_percentage)
#             setattr(instance,"restfeed",feedin)
#             setattr(task,"feedin",feedin)
#             task.save()
#         else:
#             setattr(instance,"restfeed",feedin)
#         setattr(instance,"status","processing")
#         ########################## Set the Given Data ########################
#         for field,value in validated_data.items():
#             setattr(instance,field,value)

#         instance.save()
#         self.context['feedin'] = feedin
#         if feedin != 0:
#             return instance,task
#         else:
#             return instance




import math
from .utils import apply_extra_feed_if_last_cycle
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
        read_only_fields = ['to_time', 'feedin_percentage']

    def validate(self, attrs):
        feed_weight=attrs.get('feed_weight')
        print("feed_weight",feed_weight)
        if not (feed_weight <= 100):
           raise serializers.ValidationError("Feed % not be greater the 100")
        return  attrs
    
    def update(self, instance, validated_data):
    #     cycleno=getattr(instance,"cycles")
    #     feedin_percentage = getattr(instance,"feedin_percentage")
    #     device=getattr(instance,'device')
    #     start_time=validated_data.get("from_time")
    #     print(start_time)
    #     id=getattr(instance,'id')
    #     feed_weight=None
        
    #     ###### Check the Current Cycle Completion #####################
    #     if Task.objects.filter(device=device, id=id).exists():
    #         PreTask=Task.objects.get(device=device, id=id)
    #         status=getattr(PreTask,'status')
    #         if status == "completed":
    #             raise serializers.ValidationError(f"C{cycleno} Already Completed")
    #         elif status == "abort":
    #             pass
    #     ############ Check the  Previous Cycle Completion #############
    #     now = timezone.localtime(timezone.now())
    #     today = now.date()
    #     if not start_time:
    #         raise serializers.ValidationError("Start time is required")

    #     # now_check = now.replace(second=0, microsecond=0)
    #     # start_check = start_time.replace(second=0, microsecond=0)

    #     # start_dt = datetime.combine(today, start_check)
    #     now_check = now.replace(second=0, microsecond=0).replace(tzinfo=None)
    #     start_check = start_time.replace(second=0, microsecond=0)

    #     # 🔥 make naive datetime
    #     start_dt = datetime.combine(today, start_check).replace(tzinfo=None)


    #     # -----------------------------
    #     # ✅ RULE 1 → FIRST CYCLE
    #     # -----------------------------
    #     if cycleno == 1:

    #         # min_allowed_time = now_check + timedelta(minutes=2)
    #         min_allowed_time = (now_check + timedelta(minutes=2)).replace(tzinfo=None)

    #         if start_dt < min_allowed_time:
    #             raise serializers.ValidationError(
    #                 f"C1 must be at least 2 minute ahead ({min_allowed_time.time()})"
    #             )

    #     # -----------------------------
    #     # ✅ RULE 2 → NEXT CYCLES
    #     # -----------------------------
    #     else:
    #         preid = id - 1
    #         PreTask = Task.objects.get(device=device, id=preid)

    #         pre_end_time = getattr(PreTask, 'to_time')

    #         if not pre_end_time:
    #             raise serializers.ValidationError(
    #                 f"C{cycleno-1} not scheduled properly"
    #             )

    #         # 🔥 TEMP normalize (ONLY for comparison)
    #         pre_end_check = pre_end_time.replace(second=0, microsecond=0)

    #         # prev_end_dt = datetime.combine(today, pre_end_check)

    #         # prev_condition = prev_end_dt + timedelta(minutes=2)
    #         # current_condition = now_check + timedelta(minutes=2)
    #         prev_end_dt = datetime.combine(today, pre_end_check).replace(tzinfo=None)

    #         prev_condition = (prev_end_dt + timedelta(minutes=2)).replace(tzinfo=None)
    #         current_condition = (now_check + timedelta(minutes=2)).replace(tzinfo=None)


    #         min_allowed_time = max(prev_condition, current_condition)

    #         if start_dt < min_allowed_time:
    #             raise serializers.ValidationError(
    #                 f"C{cycleno} must start after {min_allowed_time.time()}"
    #             )
        
    #     ##################### Find last Task ############################ 
    #     last_task = Task.objects.filter(device=device).order_by('-cycles').first()
    #     cno = last_task.cycles

    #     first_task = Task.objects.filter(device=device, cycles=1).first()
    #     feedin = float(first_task.feedin or 0)
    #     total_feed = feedin

        
    #     ####################### Validate the Feed_percentages ################
    #     feed_weight = validated_data.get('feed_weight')
    #     print('feed_weight=',feed_weight,'feedin_percentage=',feedin_percentage)
    #     if cycleno!=cno and feed_weight > feedin_percentage:
    #         raise serializers.ValidationError(f"Feed_weight % Should be less then {feedin_percentage}%")
            


    #     if cycleno == cno:
    #         print("🔥 Last cycle → overriding frontend feed_weight")

    #         used_percentage = Task.objects.filter(
    #             device=device,
    #             cycles__lt=cycleno
    #         ).aggregate(total=Sum("feed_weight"))["total"] or 0

    #         remaining_percentage = max(0, 100 - float(used_percentage))

    #         feed_weight = remaining_percentage
    #         validated_data['feed_weight'] = remaining_percentage
        
    #     ################## Calculate Feedin, to_time ,time_interval############################ 
    #     feedin_percentage = max(0, feedin_percentage - feed_weight)
    #     print('feed_weight=',feed_weight,'feedin_percentage=',feedin_percentage)
        
    #     use_feed=feedin*(feed_weight/100)*1000
    #     duration=math.ceil(use_feed/800)
    #     # duration=(use_feed/800)
        
    #     start_datetime = datetime.combine(now.date(), start_time)
    #     end_time = (start_datetime + timedelta(minutes=duration)).time()
        
    #     setattr(instance,"to_time",end_time)
    #     setattr(instance,"time_interval",duration)
        
    #     # feedin =feedin*(feedin_percentage/100)
    #     # print('feedin=',feedin)
    #     # total feed (from cycle 1)
    #     # total_feed = float(getattr(last_task, "feedin"))

    #     # current cycle feed (IMPORTANT)
    #     cycle_feed = total_feed * (feed_weight / 100)

    #     # remaining feed
    #     remaining_feed = total_feed * (feedin_percentage / 100)

    #     print("cycle_feed=", cycle_feed)
    #     print("remaining_feed=", remaining_feed)
    #     ################# Check the Feedin And Store to next Cycle #########
    #     # task=None
    #     # if feedin != 0 and cno != cycleno:
    #     #     task_id=id+1
    #     #     task=Task.objects.get(device=device, id=task_id)
    #     #     setattr(task,"feedin_percentage",feedin_percentage)
    #     #     setattr(instance,"restfeed",feedin)
    #     #     setattr(task,"feedin",feedin)
    #     #     task.save()
    #     # else:
    #     #     setattr(instance,"restfeed",feedin)
    #     if remaining_feed != 0 and cno != cycleno:
    #         task_id = id + 1
    #         task = Task.objects.get(device=device, id=task_id)

    #         setattr(task, "feedin_percentage", feedin_percentage)
    #         setattr(instance, "restfeed", remaining_feed)
    #         setattr(task, "feedin", remaining_feed)

    #         task.save()
    #     else:
    #         setattr(instance, "restfeed", remaining_feed)
    #     setattr(instance,"status","scheduled")
    #     # setattr(instance, "feedin", remaining_feed)
    #     ########################## Set the Given Data ########################
    #     for field,value in validated_data.items():
    #         setattr(instance,field,value)

    #     # instance = apply_extra_feed_if_last_cycle(instance)

    #     instance.save()
    #     self.context['feedin'] = feedin
    #     if feedin != 0:
    #         return instance
    #     else:
    #         return instance
        # 🔥 IMPORTANT (bulk fix)
        instance.refresh_from_db()

        if validated_data.get("status") == "abort":
            return instance

        cycleno = instance.cycles
        device = instance.device
        start_time = validated_data.get("from_time")
        schedule_date = instance.schedule_date
        id = instance.id

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
        # if feedin_percentage is None:
        #     raise serializers.ValidationError(f"C{cycleno} not initialized")
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

        # ---------- CALCULATION (DO NOT CHANGE) ----------
        feedin_percentage = max(0, feedin_percentage - feed_weight)

        cycle_feed = round(total_feed * (feed_weight / 100), 2)
        remaining_feed = round(total_feed * (feedin_percentage / 100), 2)

        use_feed = round(total_feed * (feed_weight / 100) * 1000, 2)
        duration = math.ceil(use_feed / 800)

        end_time = (
            datetime.combine(today, start_time) +
            timedelta(minutes=duration)
        ).time()

        instance.to_time = end_time
        instance.time_interval = duration
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
            raise serializers.ValidationError("Already Abort or Failed")
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

#
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
from .models import *
from rest_framework.parsers import JSONParser
from django.core.exceptions import ObjectDoesNotExist
from django.db import transaction
from rest_framework.views import APIView
from .serializers import *
from rest_framework.response import Response
from rest_framework import status
from checktray.models import *
from datetime import datetime
from django.utils import timezone


@csrf_exempt
def cluster_get(request,Mob):
    if not Mob:
            return JsonResponse({"error": "Mobile number not provided"})

    if not Manager.objects.filter(Mob=Mob):
        return JsonResponse({"error": "Mobile number not found"})
    
    if request.method == 'GET':
        clusters = Cluster.objects.all()
        return JsonResponse(clusters, safe=False)
    else:
        return JsonResponse({'message': 'Invalid request method'}, status=405)



@csrf_exempt
def userponds(request, registration_id):
    if request.method == 'GET':
        
        result = Pond.objects.filter(registration_id=registration_id)

        coordinates = []
        for item in result:
            polygon = item.location
            if polygon:  
                exterior_coords = polygon[0].coords
            else:
                exterior_coords = None  

            coordinates.append({
                'name': item.name,
                'id': item.id,
                'location': exterior_coords  
            })

        if coordinates:
            return JsonResponse({'ponds': coordinates})
        else:
            return JsonResponse({'message': 'No pond locations found for the given registration ID'}, status=404)
        

    
   
@csrf_exempt
def admin_cluster_view(request, mob):
    if request.method == 'GET':  
        if not mob:
           return JsonResponse({"error": "mob not provided"})
        # users = User.objects.get(Mob=mob)
        try:
            users = User.objects.get(Mob=mob)
            print(users, "User found")
            data = []
            # Fetch all clusters associated with this user
            clusters = Cluster.objects.filter(user=users)
            for cluster in clusters:
                data.append({
                    "Name":cluster.Name,
                    "id":cluster.id,
                    "Mob":users.Mob
                })
            return JsonResponse(data, safe=False)

        except User.DoesNotExist:
            # If not found in User, try fetching from Manager table
            try:
                managers = Manager.objects.get(Mob=mob)
                # Use the manager's related user instance
                users = managers.user  # Assuming Manager has a ForeignKey to User model
                print(managers, "Manager found, using the related User")
                data = []
                # Fetch all clusters associated with the user linked to the manager
                clusters = Cluster.objects.filter(user=users)
                for cluster in clusters:
                    data.append({
                        "Name":cluster.Name,
                        "id":cluster.id,
                        "Mob":users.Mob
                    })
                return JsonResponse(data, safe=False)

            except Manager.DoesNotExist:
                return JsonResponse({"error": "mob not found in User or Manager tables"}, status=404)
      
    else:
        return JsonResponse({"message": "Invalid request method"}, status=405)
   
   
@csrf_exempt
def adminpond_view(request,id):
    print(id)
    if request.method == 'GET':
        
        if not id:
            return JsonResponse({"error": "id not provided"})
        try:
            user = User.objects.all()
            managerss = Manager.objects.all()
            value = Cluster.objects.get(id=id)
            pond = Pond.objects.filter(registration=value)
            data = []
            for i in pond:
                data.append({
                    "id":i.id,
                    "name":i.name,
                    "latlong":i.latlong,
                    "area":i.area,
                #    "telegram_group_id":i.telegram_group_id,
                    "registration":i.registration.Name,
                    "address":i.address      
                })
               
            return JsonResponse(data, safe=False)
        except Exception as e:
            return JsonResponse({"error":str(e)})
       
   
@csrf_exempt
def common_login(request):
    try:
        # Parse JSON data
        jsondata = JSONParser().parse(request)
        Mob = jsondata.get('Mob')

        if not Mob:
            return JsonResponse({'message': 'Mobile number is required'}, status=400)

        # ----------------------------------------
        # 1. CHECK IN MASTER TABLE
        # ----------------------------------------
        try:
            master = Master.objects.get(Mobno=Mob)
            response_data = {
                'Mob': master.Mobno,
                'name': master.Name,
                'email': master.Email,
                'category': 'master'
            }
            return JsonResponse(response_data, status=200)
        except Master.DoesNotExist:
            pass

        # ----------------------------------------
        # 2. CHECK IN USER TABLE
        # ----------------------------------------
        try:
            user = User.objects.get(Mob=Mob)   # make sure mob exists
            print(user)

            serializer = UserCluserSerializer(user)

            response_data = {
                'message': 'You have successfully logged in to the owner page...',
                'Mob': user.Mob,
                'name': user.Company_name,
                'email': user.Email,
                'user_category': user.user_category,
                'category': 'owner',
                'cluster': serializer.data
            }

            return JsonResponse(response_data, status=200)


        except User.DoesNotExist:
            pass

        # ----------------------------------------
        # 3. CHECK IN MANAGER TABLE
        # ----------------------------------------
        try:
            manager = Manager.objects.get(Mob=Mob)
            users = manager.user  # FK to User model
            
            response_data = {
                'message': 'You have successfully logged in to the Manager page...',
                'Mob': manager.Mob,
                'name': manager.username,
                'email': manager.email,
                'user_category': users.user_category,
                'category': 'manager'
            }
            return JsonResponse(response_data, status=200)

        except Manager.DoesNotExist:
            return JsonResponse(
                {'message': 'No master/user/manager found with this mobile number'},
                status=404
            )

    except Exception as e:
        return JsonResponse({'message': f'An error occurred: {str(e)}'}, status=500)

    
@csrf_exempt
def workerview(request, mob):
    if request.method != 'GET':
        return JsonResponse(
            {"message": "Method not allowed"},
            status=405
        )

    try:
        user = User.objects.filter(Mob=mob).first()
        manager = None

        if not user:
            manager = Manager.objects.filter(Mob=mob).first()
            if not manager:
                return JsonResponse(
                    {"message": "Not Found any Manager or Owner"},
                    status=404
                )

        if user:
            result = Worker_details.objects.filter(user=user)
        else:
            result = Worker_details.objects.filter(manager=manager)

        response = []
        for i in result:
            response.append({
                "worker_id": i.mobno,
                "name": i.name
            })

        return JsonResponse(
            {"Employee": response},
            status=200
        )

    except Exception as e:
        return JsonResponse(
            {"error": str(e)},
            status=500
        )


class deviceid_view(APIView):
    def get(self,request,id):
        try:
            pond=Pond.objects.get(id=id)
            device_type=request.query_params.get('device_type')
            devices=Device.objects.filter(pond_id=pond)
            if device_type:
                devices=devices.filter(device_type=device_type)
            serializer=PondDeviceSerializer(pond,context={'devices':devices})
            return Response(serializer.data,status=200)
        except Pond.DoesNotExist:
            return Response("Pond Doesn't exiest")
#----------------------------------------------------------------------------------------------

#----------------------------------------------------------------------------------------------
import uuid
class FeedingGenerateview(APIView):
    def post(self, request):
        serializer = GenerateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        category_name = data['deviceName']
        device_id = data['deviceId']
        total_cycles = data['cycles']
        schedule_date = data['schedule_date']
        last_task = None
        check_sts = None
        last_task = Task.objects.filter(
            device=device_id,
            schedule_date=schedule_date
        ).order_by('-cycles').first()

        if last_task != None:
            check_sts = getattr(last_task, 'status', None) if last_task else None

        if  check_sts == "processing" or check_sts == "abort" or check_sts == "pending":
            return Response(f"{device_id} already has active cycles for this date.")
        try:
            category = Task_Category.objects.get(name__iexact=category_name)
            created_task_ids = []

            with transaction.atomic():
                batch_id = uuid.uuid4()
                for cycle_no in range(1, total_cycles + 1):
                    task = Task.objects.create(
                        taskcatagory=category,  
                        device_id=device_id,
                        cycles=cycle_no,
                        schedule_date=schedule_date,
                        batch_id=batch_id,
                        from_time=None,
                        to_time=None,
                        feed_weight=None,
                        feedin=data['feedin'] if cycle_no == 1 else None,
                        feedin_percentage=100 if cycle_no == 1 else None,
                        spray_type=None,
                        time_interval=None,
                        quantity=None,
                        depth=None,
                        image=None
                    )
                    created_task_ids.append(task.id)
            return Response(
                {
                    "message": f"{total_cycles} cycles created successfully",
                    "deviceName": category.name,
                    "task_ids": created_task_ids,
                    'status':"pending"
                },
                status=status.HTTP_201_CREATED
            )
        except Task_Category.DoesNotExist:
            return Response(
                {"error": f"Task category '{category_name}' not found"},
                status=status.HTTP_404_NOT_FOUND
            )



class FeedTimePreview(APIView):
    def post(self, request):

        from_time = request.data.get("from_time")
        feed_weight = request.data.get("feed_weight")
        total_feed = request.data.get("total_feed")  # send from frontend

        if not from_time or feed_weight is None or total_feed is None:
            return Response({"error": "from_time, feed_weight, total_feed required"}, status=400)

        # convert
        from_time = datetime.strptime(from_time, "%H:%M").time()
        feed_weight = float(feed_weight)
        total_feed = float(total_feed)

        # ---------- YOUR ORIGINAL CALCULATION ----------
        use_feed = round(total_feed * (feed_weight / 100) * 1000, 2)
        duration = math.ceil(use_feed / 800)

        end_time = (
            datetime.combine(datetime.today(), from_time) +
            timedelta(minutes=duration)
        ).time()

        return Response({
            "duration": duration,
            "end_time": end_time.strftime("%H:%M")
        })
    

#---------------------------------------------------------------------------------------------
#---------------------------------------------------------------------------------------------
from django.utils import timezone
class TaskSubmitview(APIView):
    def put(self,request):
        print('--------------------------------------------------------------------------------')
        print('see the feed weight that i get in requests', request.data.get("feed_weight"))
        print('--------------------------------------------------------------------------------')

        device_id = request.data.get("device_id")
        cycles_data = request.data.get("cycles")

        if not device_id or not cycles_data:
            return Response({"error": "device_id and cycles required"}, status=400)

        # 🔥 ONLY THIS PART CHANGED
        from django.db.models import Subquery

        latest_batch = Task.objects.filter(
            device__device_id=device_id,
            status="pending"
        ).order_by("-id").values("batch_id")[:1]

        tasks = Task.objects.filter(
            device__device_id=device_id,
            status="pending",
            batch_id=Subquery(latest_batch)
        ).order_by("cycles")

        print(tasks)

        if not tasks.exists():
            return Response({"error": "No tasks found"}, status=404)

        today = datetime.now().date()

        # Prepare data for Telegram notification
        telegram_assignments = []
        first_task_data = None
        total_feed_amount = None

        with transaction.atomic():

            for task in tasks:
                task.refresh_from_db()
                cycle_payload = cycles_data.get(str(task.cycles))

                if not cycle_payload:
                    continue

                serializer = TaskSubmitSerializer(
                    task,
                    data=cycle_payload,
                    partial=True
                )
                serializer.is_valid(raise_exception=True)
                updated_task = serializer.save()

                # Collect assignment info for Telegram
                worker_name = getattr(updated_task, 'worker_name', None)
                from_time = getattr(updated_task, 'from_time', None)
                feed_weight = getattr(updated_task, 'feed_weight', None)
                
                if worker_name and from_time:
                    telegram_assignments.append({
                        "cycle": updated_task.cycles,
                        "worker_name": str(worker_name),
                        "time": from_time.strftime("%I:%M %p").lstrip("0")
                    })
                
                # Capture first task data for notification
                if updated_task.cycles == 1:
                    first_task_data = updated_task
                    # Get total feed from first cycle
                    total_feed_amount = getattr(updated_task, 'feedin', None)

        # Send Telegram notification after successful assignment
        print(f"\n📤 [TELEGRAM] Preparing to send notification...")
        print(f"📤 [TELEGRAM] first_task_data: {first_task_data}")
        print(f"📤 [TELEGRAM] telegram_assignments: {telegram_assignments}\n")
        
        if first_task_data and telegram_assignments:
            try:
                from myapp.telegram_queue import enqueue_telegram
                
                schedule_date_str = first_task_data.schedule_date.strftime("%d %b %Y") if first_task_data.schedule_date else "—"
                generate_time_str = datetime.now().strftime("%I:%M %p").lstrip("0")
                
                telegram_data = {
                    "task_id": first_task_data.id,
                    "device_id": device_id,
                    "feed_amount": str(total_feed_amount) if total_feed_amount else "—",
                    "total_cycles": len(telegram_assignments),
                    "schedule_date": schedule_date_str,
                    "generate_time": generate_time_str,
                    "assignments": telegram_assignments
                }
                
                enqueue_telegram(telegram_data)
                print(f"[TELEGRAM] Queued notification for Task #{first_task_data.id}")
            except Exception as e:
                print(f"[TELEGRAM ERROR] Failed to queue notification: {e}")


        first_task = tasks.first()

        if first_task.schedule_date == today:
            success = trigger_device(
                first_task.device.device_id,
                first_task.id
            )

            if not success:
                return Response({"msg": "Device busy"}, status=400)

        return Response({
            "msg": "All cycles scheduled successfully",
            "first_cycle": first_task.id,
            "status": "scheduled"
        })

# ===============================================================================================================
#                                           TASK GET Total Feed 
# ===============================================================================================================
        
class PondTaskView(APIView):

    def get(self, request):
        pond_id = request.query_params.get("pond_id")
        device_id = request.query_params.get("device_id")
        date_str = request.query_params.get("date")
        Date = datetime.strptime(date_str, "%d-%m-%Y").date() if date_str else timezone.now().date()
        print(Date)
        tasks = Task.objects.select_related("device").filter()

        if pond_id:
            tasks = tasks.filter(device__pond_id__id=pond_id)

        if device_id:
            tasks = tasks.filter(device__device_id=device_id)
        if Date:
            tasks = tasks.filter(created_at__date=Date)

        if not tasks.exists():
            message = "No tasks found."

            if pond_id and device_id:
                message = f"No tasks found for pond_id={pond_id} and device_id={device_id}."
            elif pond_id:
                message = f"No tasks found for pond_id={pond_id}."
            elif device_id:
                message = f"No tasks found for device_id={device_id}."

            return Response({"message": message}, status=200)

        tasks = tasks.order_by("cycles")

        serializer = PondTaskSerializer(tasks, many=True)

        return Response(
            {
                "pond_id": pond_id,
                "device_id": device_id,
                "total_tasks": tasks.count(),
                "tasks": serializer.data,
            },
            status=200,
        )


###################################### Publish FIRST Message and abort ################################

import paho.mqtt.client as mqtt
import time
from .utils import trigger_device
BROKER = "mqttbroker.bc-pl.com"   # same as subscriber
PORT = 1883
USERNAME = "mqttuser"
PASSWORD = "Bfl@2025"

class DeviceCommandStateView(APIView):
    def post(self, request, id, tid):

        success = trigger_device(id, tid)

        if not success:
            return Response({
                "status": "blocked",
                "message": "Device already has a scheduled cycle"
            })

        return Response({
            "status": "success",
            "message": "AUTO mode command sent",
            "payload": "AUTO"
        })


def Feedcalculate(tid):
    now = datetime.now()   # local naive

    try:
        task = Task.objects.get(id=tid)
    except:
        return

    from_time = task.from_time
    if not from_time:
        return

    current_time = now.time()
    today = now.date()

    # pure naive datetime
    from_dt = datetime.combine(today, from_time)
    current_dt = datetime.combine(today, current_time)

    second = 0
    used_feed = 0

    first_task = Task.objects.filter(device=task.device,batch_id=task.batch_id, cycles=1).first()
    if not first_task:
        return

    total_feed = float(first_task.feedin or 0)
    cycle_feed = round((total_feed * float(task.feed_weight or 0)) / 100,2)

    if current_dt >= from_dt:
        duration = current_dt - from_dt
        second = round(duration.total_seconds())
        used_feed = max(0, (second * 13) / 1000)
        remaining_cycle_feed = round(max(0, cycle_feed - used_feed),2)
    else:
        remaining_cycle_feed = cycle_feed

    last_task = Task.objects.filter(device=task.device,batch_id=task.batch_id).order_by('-cycles').first()

    if last_task:
        last_task.extra_feed = float(last_task.extra_feed or 0) + remaining_cycle_feed
        last_task.save()

    print("✅ Abort Feed Calculation Done")
    print("------ DEBUG START ------")
    print("TASK ID:", task.id)
    print("FROM TIME (DB):", from_time)
    print("NOW (datetime.now):", now)
    print("CURRENT TIME:", current_time)
    print("FROM_DT:", from_dt)
    print("CURRENT_DT:", current_dt)
    print("COMPARISON current_dt > from_dt:", current_dt > from_dt)
    print("DIFF (sec):", (current_dt - from_dt).total_seconds())
    print("------ DEBUG END ------")
    
############################################################################
    

class DeviceCommandAbortView(APIView):

    def post(self, request,id,tid):
        DEVICE_ID = id
        TOPIC_Abort = f"auto_feeder/{DEVICE_ID}/auto/abort"
        client = mqtt.Client(
        client_id=f"tasksubmit_{DEVICE_ID}_{int(time.time())}",
        protocol=mqtt.MQTTv311
        )
        try:
            task = Task.objects.get(id=tid)
            task.status = "aborted"
            task.save(update_fields=["status"])
        except:
            return Response({"error": "Task not found"}, status=404)
        Feedcalculate(tid)
        def on_connect(client, userdata, flags, rc):
            print("Connected with rc:", rc)

        client.on_connect = on_connect
        if USERNAME and PASSWORD:
            client.username_pw_set(USERNAME, PASSWORD)

        client.loop_start()
        client.connect(BROKER, 1883, 60)
        # payload={"MODE": "AUTO"}

        client.publish(TOPIC_Abort,"abort", qos=1)
        time.sleep(1)

        client.loop_stop()
        client.disconnect()

        try:
            from myapp.telegram_notifications import notify_task_abort
            
            device_id_str = id
            cycle_no = getattr(task, 'cycles', '—')
            worker_name_obj = getattr(task, 'worker_name', None)
            worker_name = str(worker_name_obj) if worker_name_obj else 'Unknown'
            
            abort_data = {
                "device_id": device_id_str,
                "cycle": cycle_no,
                "worker_name": worker_name
            }
            
            notify_task_abort(abort_data)
            print(f"[TELEGRAM ABORT] Notification sent for Device {device_id_str}, Cycle {cycle_no}")
        except Exception as e:
            print(f"[TELEGRAM ABORT ERROR] {e}")
        
        return Response({
            "status": "success",
            "message": "Process Aborted"
        })
        
        return Response({
            "status": "success",
            "message": "Process Aborted"
        })
        
############################### log message ####################################

class AlertMessageView(APIView):
    def get(self,request,device_id):
        try:
            alert=Alert_message.objects.filter(device_id=device_id)[:7]
        except ObjectDoesNotExist:
            return Response({'message':"Alert Not found"},status=404)
        serializer=AlertMessageSerializer(alert,many=True)
        return Response(serializer.data,status=200)
    
############################### Task Clear #####################################

class TaskclearView(APIView):
    def post(self,request):
        serializer=TaskClearSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        device=serializer.validated_data['device']
        print(device)

        # ONLY TODAY'S TASKS
        tasks = Task.objects.filter(
            device=device
        )

        # CHECK CONDITION
        if tasks.filter(status="processing").exists():
            return Response(
                {"message": "Cannot delete tasks while a cycle is processing."},
                status=400
            )

        if not tasks.exists():
            return Response({"message": "Task NotFound.."}, status=404)

        tasks.delete()

        return Response(
            {"message": f"Today's tasks for {device} deleted successfully."},
            status=200
        )
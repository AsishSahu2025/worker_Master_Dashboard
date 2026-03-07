from django.shortcuts import render
import json, traceback
from django.http import JsonResponse
from .models import *
from django.db import transaction
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt

import paho.mqtt.client as mqtt

MQTT_BROKER = "mqttbroker.bc-pl.com"
MQTT_PORT = 1883
MQTT_USERNAME = "mqttuser"   # if required
MQTT_PASSWORD = "Bfl@2025"

# def publish_schedule_to_device(device_id, message):
#     try:
#         client = mqtt.Client(client_id=f"schedule_pub_{device_id}")

#         # remove if broker allows anonymous access
#         client.username_pw_set(MQTT_USERNAME, MQTT_PASSWORD)

#         client.connect(MQTT_BROKER, MQTT_PORT, 60)

#         topic = f"feeder/{device_id}/schedule_set"

#         client.publish(topic, message, qos=1)

#         client.disconnect()

#         print(f"Published: {topic} -> {message}")

#     except Exception as e:
#         print("MQTT Publish Error:", str(e))



@csrf_exempt
# Create your views here.
def checktrayGenerate(request):
    if request.method == "POST":
        try:
            data=json.loads(request.body)

            device_id=data.get("device_id")
            # cycle_no=data.get("cycle_no")

            if not device_id:
                return JsonResponse({'error':'device_id is required.'}, status=400)

            # prevent duplicate generation
            if ChecktrayTask.objects.filter(
                device_id=device_id,
                status__in=["No Status","Pending", "Running"]
            ).exists():
                return JsonResponse(
                    {"error": "Cycles already generated"},
                    status=409
                )

            response_rows = []

            with transaction.atomic():
                task = ChecktrayTask.objects.create(
                    device_id_id=device_id,
                    # cycle_no=int(cycle_no)+1,
                    spray_cycle="YES",
                    image_update="YES",
                    water_level=0,
                    status="No Status"
                )

                # send row back to UI
                response_rows.append({
                    "id": task.id,
                    "device_id": device_id,
                    # "cycle_no": f"C{0}",
                    # "water_level": 0,
                    "status": "No Status"
                })

            return JsonResponse({"tasks": response_rows}, status=200)


        except Exception as e:
            print("Exception:", str(e))
            traceback.print_exc()
            return JsonResponse({'error': str(e)}, status=500)

    return JsonResponse({'error': 'Invalid HTTP method. Use POST.'}, status=405)


@csrf_exempt
def scheduling(request):
    if request.method == "POST":
        try:
            data= json.loads(request.body)
            
            id= data.get("id")
            device_id = data.get('device_id')
            # cycle_no= data.get("cycle_no")
            # spray_cycle= data.get("spray_cycle")
            start_time_str= data.get("start_time")


            if not all([id, start_time_str]):
                return JsonResponse({'error': 'Missing required fields'}, status=400)
            
            try:
                start_time = timezone.datetime.strptime(start_time_str, '%Y-%m-%d %H:%M')
                print(start_time)
                start_time = timezone.make_aware(start_time)
                print()
            except ValueError:
                return JsonResponse({'error': 'Invalid time format. Use YYYY-MM-DD HH:MM'}, status=400)

            
            updated=ChecktrayTask.objects.filter(id=id).update(
                    # cycle_no=cycle_no,
                    # sparay_cycle=spray_cycle,
                    start_time=start_time,
                    status="Pending"
                )

            if updated==0:
                return JsonResponse({'error':'Task not found or already scheduled'}, status=409)
            
            # mqtt_message = f"morning_feed|{start_time_str}|1|0"
            # print(mqtt_message)
            
            # publish_schedule_to_device(device_id, mqtt_message)

            return JsonResponse({
                'status': 'success',
            }, status=200)

        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)

    
    return JsonResponse({'error':'Invalid HTTP method, Use POST'}, status=405)



def checktrayTask(request):
    if request.method == "GET":
        try:
            device_id = request.GET.get("device_id")

            if device_id:
                tasks= ChecktrayTask.objects.filter(device_id__device_id=device_id).order_by("start_time").values(
                "id",
                "device_id",
                "spray_cycle",
                "image_update",
                "water_level",
                "start_time",
                "stop_time",
                "status"
            )

                return JsonResponse({'task':list(tasks)}, status=200)
            else :
                tasks = ChecktrayTask.objects.all().order_by('start_time').values(
                    "id",
                    "device_id",
                    "spray_cycle",
                    "image_update",
                    "water_level",
                    "start_time",
                    "stop_time",
                    "status"
                )
                return JsonResponse({'task':list(tasks)}, status=200) 
        
        except Exception as e:
            return JsonResponse({'error':str(e)}, status=500)
    return JsonResponse({'error':'Invalid HTTP method, Use GET'}, status=405)


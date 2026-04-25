from django.shortcuts import render
import json, traceback
from django.http import JsonResponse
from .models import *
from django.db import transaction
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from checktray.mqtt_command_queue import enqueue_mqtt_command
from checktray.telegram_queue import enqueue_telegram

from checktray.telegram_notifications import notify_checktray_task
import time

@csrf_exempt
# Create your views here.
def checktrayGenerate(request):
    if request.method == "POST":
        try:
            data=json.loads(request.body)

            device_id=data.get("device_id")

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
                    spray_cycle="YES",
                    image_update="YES",
                    water_level=0,
                    status="No Status"
                )

                # send row back to UI
                response_rows.append({
                    "id": task.id,
                    "device_id": device_id,
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
    if request.method != "POST":
        return JsonResponse({'error':'Invalid HTTP method, Use POST.'})
    try:
        data= json.loads(request.body)
        
        task_id= data.get("id")
        device_id = data.get('device_id')
        start_time_str= data.get("from_time")
        worker = data.get('worker_name')


        if not all([task_id, device_id, start_time_str, worker]):
            return JsonResponse({'error': 'Missing required fields'}, status=400)
        
        try:
            start_time = timezone.datetime.strptime(start_time_str, '%Y-%m-%d %H:%M')
            print(start_time)
        except ValueError:
            return JsonResponse({'error': 'Invalid time format. Use YYYY-MM-DD HH:MM'}, status=400)
        
        try:
            worker_obj = Worker_details.objects.get(name=worker)
        except Worker_details.DoesNotExist:
            return JsonResponse({'error': 'Worker not found'}, status=404)

        with transaction.atomic():

            task = ChecktrayTask.objects.select_for_update().get(id=task_id)

            if task.status != "No Status":
                return JsonResponse({"error": "Already scheduled or No task found."}, status=409)

            task.start_time = start_time
            task.worker_name = worker_obj
            task.status = "ScheduleRequested"
            task.save()
        
        mqtt_message = f"morning_feed|{start_time_str}|1|0"
        topic = f"feeder/{device_id}/schedule_set"
        
        print('ser tiopic')
        enqueue_mqtt_command(topic, mqtt_message)
        print('publish topic')
        
        return JsonResponse({
            'status': 'success',
        }, status=200)

    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)
    


def checktrayTask(request):
    if request.method == "GET":
        try:
            device_id = request.GET.get("device_id")

            if device_id:
                tasks= ChecktrayTask.objects.filter(device_id__device_id=device_id).order_by("start_time").values(
                "id",
                "device_id",
                "worker_name",
                "spray_cycle",
                "image_update",
                "water_level",
                "start_time",
                "stop_time",
                "status",
                "submit"
            )

                return JsonResponse({'task':list(tasks)}, status=200)
            else :
                tasks = ChecktrayTask.objects.all().order_by('start_time').values(
                    "id",
                    "device_id",
                    "worker_name",
                    "spray_cycle",
                    "image_update",
                    "water_level",
                    "start_time",
                    "stop_time",
                    "status",
                    "submit"
                )
                return JsonResponse({'task':list(tasks)}, status=200) 
        
        except Exception as e:
            return JsonResponse({'error':str(e)}, status=500)
    return JsonResponse({'error':'Invalid HTTP method, Use GET'}, status=405)


@csrf_exempt
def deleteTask(request):
    if request.method == "DELETE":
        try:
            data = json.loads(request.body)
            task_id= data.get('id')
           
            if not task_id:
                return JsonResponse({'error':'task_id is required.'}, status=400)
            
            task = ChecktrayTask.objects.filter(id=task_id).first()
            print(task)

            if not task:
                return JsonResponse({"error": "Task not found"}, status=404)
            
            print(task.status)

            # Business rule validation
            if task.status == "Running":
                print('inside abort task')
                topic=f"feeder/{task.device_id.device_id}/cycle_abort"
                message= "Aborted"

                enqueue_mqtt_command(topic, message)

                return JsonResponse(
                    {"status": "Cycle aborted and task deleted"},
                    status=200
                )
            if task.status == "Pending":
                topic = f"feeder/{task.device_id.device_id}/schedule_cancel"
                message = "morning_feed"

                enqueue_mqtt_command(topic, message)


                return JsonResponse({"status": "schedule cancelled and task deleted"}, status=200)
            
                
            task.delete()

            return JsonResponse({'status':'success'}, status=200)
        
        except Exception as e:
            return JsonResponse({'error':str(e)}, status=500)
    return JsonResponse({'error':'Invalid HTTP method, Use DELETE'}, status=405)
from django.shortcuts import render
import json, traceback
from django.http import JsonResponse
from .models import *
from django.db import transaction

# Create your views here.
def checktryGenerate(request):
    if request.method == "POST":
        try:
            data=json.loads(request.body)

            device_id=data.get("device_id")
            cycle_count= data.get("number")

            if not [device_id, cycle_count]:
                return JsonResponse({'error':'Both device_id and cycle count is required.'}, status=400)

            # prevent duplicate generation
            # if ChecktrayTask.objects.filter(
            #     device_id=device_id,
            #     status__in=["Pending", "Running"]
            # ).exists():
            #     return JsonResponse(
            #         {"error": "Cycles already generated"},
            #         status=409
            #     )

            response_rows = []

            with transaction.atomic():

                for i in range(1, cycle_count + 1):

                    task = ChecktrayTask.objects.create(
                        device_id=device_id,
                        cycle_no=i,
                        water_level=0,
                        status="Pending"
                    )

                    # send row back to UI
                    response_rows.append({
                        "device_id": device_id,
                        "cycle_no": f"C{i}",
                        "water_level": 0,
                        "status": "Pending"
                    })

            return JsonResponse({"tasks": response_rows}, status=201)


        except Exception as e:
            print("Exception:", str(e))
            traceback.print_exc()
            return JsonResponse({'error': str(e)}, status=500)

    return JsonResponse({'error': 'Invalid HTTP method. Use POST.'}, status=405)
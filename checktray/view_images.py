from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
from django.utils.timezone import now
import json
import uuid
from myapp.models import Device
from checktray.models import *
from checktray.storage.azure import generate_upload_sas
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync


@csrf_exempt
def request_image_upload(request):
    if request.method != "POST":
        return JsonResponse({"error": "Method not allowed"}, status=405)

    try:
        data = json.loads(request.body)

        device_id = data.get("device_id")
        image_type = data.get("image_type")  # color / thermal

        if not device_id or not image_type:
            return JsonResponse({"error": "Missing fields"}, status=400)

        # Validate device
        try:
            device = Device.objects.get(Device_id=device_id)
        except Device.DoesNotExist:
            return JsonResponse({"error": "Invalid device"}, status=403)

        # Logical path (NO URL here)
        date_path = now().strftime("%Y/%m/%d")
        filename = f"{uuid.uuid4().hex}.jpg"

        logical_path = f"{device_id}/{image_type}/{date_path}/{filename}"

        # Generate temporary Azure upload URL
        upload_url = generate_upload_sas(logical_path)

        return JsonResponse({
            "upload_url": upload_url,
            "storage_mode": "azure",
            "logical_path": logical_path,
            "expires_in": 300  # seconds (informational)
        })

    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


channel_layer = get_channel_layer()

@csrf_exempt
def confirm_image_upload(request):
    if request.method != "POST":
        return JsonResponse({"error": "Method not allowed"}, status=405)

    try:
        data = json.loads(request.body)

        device_id = data.get("device_id")
        image_type = data.get("image_type")
        logical_path = data.get("logical_path")

        if not all([device_id, image_type, logical_path]):
            return JsonResponse({"error": "Missing fields"}, status=400)
        
        try:
            device = Device.objects.get(Device_id=device_id)
        except Device.DoesNotExist:
            return JsonResponse({'error': 'Invalid device.'}, status=403)

        # Store ONLY logical path
        image=Image.objects.create(
            device_id=device_id,
            image_type=image_type,
            storage_mode="azure",
            logical_path=logical_path
        )

        # Push to WebSocket group
        async_to_sync(channel_layer.group_send)(
            f"device_{device.Device_id}",
            {
                "type": "new_image",
                "data": {
                    "node_id": device_id,
                    "image_type": image_type,
                    "logical_path": logical_path,
                    "created_at": image.created_at.isoformat()
                }
            }
        )

        return JsonResponse({"status": "ok"})

    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)

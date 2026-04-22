from django.contrib import admin

from checktray.models import ChecktrayTask, Image

# Register your models here.
@admin.register(ChecktrayTask)
class ChecktrayTaskAdmin(admin.ModelAdmin):
    list_display = ['id','device_id','spray_cycle','image_update','water_level','start_time','stop_time','status','submit', 'worker_name']

@admin.register(Image)
class ImageAdmin(admin.ModelAdmin):
    list_display = ['id','device_id', 'image_type', 'storage_mode', 'logical_path', 'created_at']
from django.contrib import admin

from checktray.models import ChecktrayTask, Image

# Register your models here.
@admin.register(ChecktrayTask)
class ChecktrayTaskAdmin(admin.ModelAdmin):
    list_display = ['device_id','cycle_no','sparay_cycle','image_update','water_level','start_time','complete_time','status']

@admin.register(Image)
class ImageAdmin(admin.ModelAdmin):
    list_display = ['device_id', 'image_type', 'storage_mode', 'logical_path', 'created_at']
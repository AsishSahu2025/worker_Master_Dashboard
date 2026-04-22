from django.contrib.gis import admin
from  .models import *
# from django.contrib.gis.admin import OSMGeoAdmin
@admin.register(Master)
class Master(admin.ModelAdmin):
    list_display = ['Name','Mobno','Email','password','created_at','customer_id','token','address']
    
@admin.register(Super)
class Super(admin.ModelAdmin):
    list_display = ['Name','Mob','Email','password','avtar']

@admin.register(User)
class User(admin.ModelAdmin):
    list_display = ['Company_name','Mob','Customer_id','Email','password','address','Pan_no','GST_no','user_category','token']

@admin.register(Cluster)
class Cluster(admin.ModelAdmin):
    list_display = ['id','Name','user']

@admin.register(Pond)
class Pond(admin.GISModelAdmin):
    list_display = ['id','name','latlong','location','area','address','device_quantity','registration','telegram_group_id']

@admin.register(Draw)
class Draw(admin.ModelAdmin):
    list_display = ['id','data','cluster']

@admin.register(Parameter)
class ParameterAdmin(admin.ModelAdmin):
    list_display = ['pH','dissolved_oxygen','NDVI','NDTI','GCI','NDCI','NDWI','TSS','CDOM','AQUATIC_MACROPYTES','Phycocyanin','Chl_a','pond','created_at']

@admin.register(Task)
class Task(admin.ModelAdmin):
    list_display = ['id','created_at','device','taskcatagory','cycles',"feedin",'feedin_percentage','feed_weight','restfeed','from_time','to_time','worker_name','time_interval','auto_feed_rate','auto_sprinkle_rate','auto_door','status','is_published','extra_feed']  

@admin.register(Task_status)
class Task_statu(admin.ModelAdmin):
    list_display = ['name','time','date','latitude','longitude','status','username','pond_id','task_id','message_id','time_poll_id','shrimp_size','shrimp_color','diesese','moulting','size_poll_id', 'color_poll_id', 'dieses_poll_id', 'moulting_poll_id'] 
 
@admin.register(Task_Category)
class Task_Category(admin.ModelAdmin):
    list_display = ["id",'name']

@admin.register(Device)
class Device(admin.ModelAdmin):
    list_display = ['device_id','device_type','created_at','pond_id']


@admin.register(Worker_details)
class Worker_detail(admin.ModelAdmin):
    list_display = ['mobno','name','user','manager']
    
    
# @admin.register(Telegram_data)
# class Telegram_data(admin.ModelAdmin):
#     list_display = ['user_name','message','time']
    
############################## service payment Table ################################

@admin.register(ServicePayment)
class ServicePayment(admin.ModelAdmin):
    list_display = ('user_name', 'pond_id', 'service_name', 'amount', 'order_id', 'token', 'created_at')
    
    
@admin.register(Manager)
class Manager(admin.ModelAdmin):
    list_display = ['username', 'password','Mob','email','user','token']


class CycleStatusAdmin(admin.ModelAdmin):
    list_display = ['id','device','starttime','cycles']
admin.site.register(CycleStatus,CycleStatusAdmin)

class Alert_messageAdmin(admin.ModelAdmin):
    list_display = ['device_id','alert','Timestamp']
admin.site.register(Alert_message,Alert_messageAdmin)


class DeviceCommandState_Admin(admin.ModelAdmin):
    list_display = ['device_id','task_id','timepergm','step','updated_at']
admin.site.register(DeviceCommandState,DeviceCommandState_Admin)

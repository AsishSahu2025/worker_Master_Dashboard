from django.contrib import admin
from django.urls import path,include
from myapp import views
from myapp.views import *
import checktray.views
from django.conf import settings

from django.conf.urls.static import static

# from rest_framework_simplejwt import views as jwt_views


urlpatterns = [
    path('api/', include('mobile_app.urls')),
    path('admin/', admin.site.urls),
    path('admin_cluster_view/<mob>/',views.admin_cluster_view),   #admin side
    path('adminpond_view/<id>/',views.adminpond_view),   #admin
    path('common_login/',views.common_login),
    path('demo/',PondCreateView),
    path('devicedetails_get/',views.devicedetails_get),  #admin
    path('send_location/<id>/',views.send_location),   #admin
    path('signup/',views.user_registration),
    path('viewuser_all/',views.viewuser_all),
    path('workerview/<mob>/',views.workerview),          
    path('work_assign/',views.work_assign),
    path('deviceid_view/<id>/',deviceid_view.as_view()),     
    path('master_common_login/',views.master_common_login),
    path('clusterpond_analytic/<pk>/',clusterpond_analytic.as_view()),
#-------------------------------------------------------------------------
    path('cyclestatus/',CycleStatusview.as_view()),
    path('generate/',FeedingGenerateview.as_view()),
    path('automode/<id>/<tid>/',DeviceCommandStateView.as_view()),
    path('automodeabort/<id>/<tid>/',DeviceCommandAbortView.as_view()),
    path('tasksubmit/<id>/',TaskSubmitview.as_view()),
    path('taskclear/',TaskclearView.as_view()),
    path('abort/<id>/',Abortview.as_view()),
    path('restart/<id>/',Restartview.as_view()),
    path("alertmessage/<device_id>/",AlertMessageView.as_view()),
#**************************************************************************
    path('feedtrygenerate/',FeedTryGenerateview.as_view()),
    path("pond-task/", PondTaskView.as_view()),
#--------------------------------------------------------------------------
    path('manager_details_post/',views.manager_details_post),
    path('cluster_create/',views.cluster_create),
    path('viewuser/<id>/',views.viewuser),
    path('userponds/<registration_id>/',views.userponds),
    path('userpondsid/<id>/',views.userpondsid),
    path('deviceregistry_view/<customer_id>/',views.deviceregistry_view),     
    path('drawline/',views.drawline),  #admin
    path('deviceregistry_all/',views.deviceregistry_all),  #admin
    path('devicedetails_add/',views.devicedetails_add),  #admin
    path('user_delete/<customer_id>/',views.user_delete),
    path('feedweight_per_date/<mobno>/',views.feedweight_per_date), 
    path('feedweight_per_week/<mobno>/',views.feedweight_per_week), 
    path('feedweight_per_month/<mobno>/',views.feedweight_per_month), 
    path('feedweight_date/<clusterid>/',views.feedweight_date), 
    path('feedweight_week/<clusterid>/',views.feedweight_week), 
    path('feedweight_month/<clusterid>/',views.feedweight_month), 
    path('graph/<id>/',views.graph),  
    path('category/',views.category), 
    path('master_signup/',views.master_registration),
    path('send_otp/',views.send_otp),
    path('changepassword/<mob>/',views.changepassword),
    path('pondcount/<registration_id>/',views.pondcount),
    path('success/',views.success, name='success'),
    path('gateway/success',views.success),
    path('create_order/',views.create_order),
    path('complete_order/',views.complete_order),
    path('photoupload/<Mob>/',views.photoupload),
    path('photosend/<id>/',views.photosend , name ="photosend"),
    path('adminpond/<Mob>/',views.adminpond),
    path('accounts/', include('django.contrib.auth.urls')),
    path('trail/',views.trail),
    path('pondanalytic/<mob>/',views.pondanalytic),  
    path('task_assign_pondlist/<id>/',views.task_assign_pondlist),
    path('fetch_cluster/<Mob>/', views.fetch_cluster),   
    path('admin_cluster_delete_all/<id>/',views.admin_cluster_delete_all),
    path('admin_cluster_delete/<id>/',views.admin_cluster_delete),
    path('remote_sensing_data/',views.remote_sensing_data),
    path('livefeed/<usermob>/', views.live_feed_view, name='live_feed'),   
    path('delete_drawline/<id>/',views.delete_drawline),
    path('device_details/<device_type>/',views.device_details),     
    path('get_parameters/<pond_id>/',views.get_parameters),     

    ######################### checktray ################################

    path('checktray_generate/', checktray.views.checktrayGenerate),
    path('schedule/', checktray.views.scheduling),
    path('checktray_task/', checktray.views.checktrayTask),
    path('delete_task/', checktray.views.deleteTask),
    
]+ static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)


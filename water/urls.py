from django.contrib import admin
from django.urls import path,include
from myapp import views
from myapp.views import *
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
    path('automodeabort/<id>/',DeviceCommandAbortView.as_view()),
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
    path('manager_delete/',views.delete_manager),
    path('cluster_create/',views.cluster_create),
    path('viewuser/<id>/',views.viewuser),
    path('userponds/<registration_id>/',views.userponds),
    path('userpondsid/<id>/',views.userpondsid),
    path('deviceregistry_view/<customer_id>/',views.deviceregistry_view),     #
    # path('devicetype_create/<pond_id>/',views.devicetype_create),     #
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
    # path('devicetype_image/',views.devicetype_image),  #admin
    # path('weather/',views.weather,name='weather'),
    # path('user/<user_id>/',views.user,name='user'),
    path('master_signup/',views.master_registration),
    # path('login/',views.login),
    path('send_otp/',views.send_otp),
    # path('add_pond_number/',views.add_pond_number),
    # path('my/',views.my),
    # path('logout/',views.logout),
    path('changepassword/<mob>/',views.changepassword),
    # path('forgotpassword/',views.forgotpassword),
    path('pondcount/<registration_id>/',views.pondcount),
    # path('getmark/<id>/',views.getmark),
    # path('myhtml/<token>',views.myhtml),
    # path('gateway/<id>/',views.gateway,name='gateway'),
    #  path('gatewaysecond/<id>/',views.gatewaysecond,name='gatewaysecond'),
    path('success/',views.success, name='success'),
    path('gateway/success',views.success),
    path('create_order/',views.create_order),
    path('complete_order/',views.complete_order),
    path('photoupload/<Mob>/',views.photoupload),
    path('photosend/<id>/',views.photosend , name ="photosend"),
    path('adminpond/<Mob>/',views.adminpond),
    path('accounts/', include('django.contrib.auth.urls')),
    path('trail/',views.trail),
    # path('fetchlocation/<id>/',views.fetchlocation),
    path('pondanalytic/<mob>/',views.pondanalytic),  
    path('task_assign_pondlist/<id>/',views.task_assign_pondlist),
    # path('excel/',excel.as_view()), 
    path('fetch_cluster/<Mob>/', views.fetch_cluster),   
    path('admin_cluster_delete_all/<id>/',views.admin_cluster_delete_all),
    path('admin_cluster_delete/<id>/',views.admin_cluster_delete),
    path('remote_sensing_data/',views.remote_sensing_data),
    path('livefeed/<usermob>/', views.live_feed_view, name='live_feed'),   #
    path('delete_drawline/<id>/',views.delete_drawline),
    path('device_details/<device_type>/',views.device_details),     
    path('get_parameters/<pond_id>/',views.get_parameters),    #
    # path('telegram_bot_post/',views.telegram_bot_post),    #
    # re_path(r'^.*$', some_view, name='catch_all'),
    
    
    
    ################# manager #########################
    
   
 
]+ static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

from django.contrib import admin
from django.urls import path, include
from myapp import views
from myapp.views import *
import checktray.views
import checktray.view_images
from django.conf import settings

from django.conf.urls.static import static



urlpatterns = [
    path('api/', include('mobile_app.urls')),
    path('admin/', admin.site.urls),
    path('admin_cluster_view/<mob>/',views.admin_cluster_view),   #admin side
    path('adminpond_view/<id>/',views.adminpond_view),   #admin
    path('common_login/',views.common_login),
    path('workerview/<mob>/',views.workerview),      
    path('deviceid_view/<id>/',deviceid_view.as_view()),
    path('generate/',FeedingGenerateview.as_view()),
    path('automode/<id>/<tid>/',DeviceCommandStateView.as_view()),
    path('automodeabort/<id>/<tid>/',DeviceCommandAbortView.as_view()),
    path('tasksubmit/',TaskSubmitview.as_view()),
    path('feedtimepreview/',FeedTimePreview.as_view()),
    path('taskclear/',TaskclearView.as_view()),
    path("alertmessage/<device_id>/",AlertMessageView.as_view()),
    path("pond-task/", PondTaskView.as_view()),
    path("userponds/<registration_id>/", views.userponds),
    
    ######################### power monitoring #########################
    path("api/", include("power_monitoring.urls")),
    
    ######################### checktray ################################
    path("checktray_generate/", checktray.views.checktrayGenerate),
    path("schedule/", checktray.views.scheduling),
    path("checktray_task/", checktray.views.checktrayTask),
    path("delete_task/", checktray.views.deleteTask),
    path("confirm_image_upload/", checktray.view_images.confirm_image_upload),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

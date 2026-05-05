from django.contrib import admin
from django.urls import path, include
from django.http import HttpResponse
from myapp import views
from myapp.views import *
import checktray.views
import checktray.view_images
from django.conf import settings
# from checktray.test_call import test_call_now
from checktray.daily_call import call_manager_daily_reminder
from checktray.daily_call import call_manager_autofeeder_reminder
from checktray.daily_call import call_worker_for_task
from checktray.daily_call import call_worker_for_autofeeder_task

from django.conf.urls.static import static

def trigger_test_call(request):
    sid = call_manager_daily_reminder()
    if sid:
        return HttpResponse(f"✅ Call placed! SID: {sid}")
    return HttpResponse("❌ Call failed. Check console logs.")



def trigger_worker_test_call(request):
    task = (
        ChecktrayTask.objects
        .filter(status="Pending", worker_name__isnull=False)
        .select_related("device_id", "worker_name")
        .last()
    )
    if not task:
        return HttpResponse("❌ No pending task with worker found.")
    sid = call_worker_for_task(task)
    if sid:
        return HttpResponse(f"✅ Worker call placed to {task.worker_name.name} ({task.worker_name.mobno})! SID: {sid}")
    return HttpResponse("❌ Call failed. Check console logs.")


def trigger_autofeeder_worker_test_call(request):
    task = (
        Task.objects
        .filter(status="scheduled", worker_name__isnull=False)
        .select_related("device", "worker_name")
        .last()
    )
    if not task:
        return HttpResponse("❌ No scheduled autofeeder task with worker found.")
    sid = call_worker_for_autofeeder_task(task)
    if sid:
        return HttpResponse(f"✅ Autofeeder worker call placed to {task.worker_name.name} ({task.worker_name.mobno})! SID: {sid}")
    return HttpResponse("❌ Call failed. Check console logs.")



# ── add this new view ──
def trigger_autofeeder_manager_test_call(request):
    sid = call_manager_autofeeder_reminder()
    if sid:
        return HttpResponse(f"✅ Autofeeder manager call placed! SID: {sid}")
    return HttpResponse("❌ Call failed. Check console logs.")


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
    path("add-worker/", CreateWorkerAPIView.as_view()),
    
    ######################### power monitoring #########################
    path("api/", include("power_monitoring.urls")),
    
    ######################### checktray ################################
    path("checktray_generate/", checktray.views.checktrayGenerate),
    path("schedule/", checktray.views.scheduling),
    path("checktray_task/", checktray.views.checktrayTask),
    path("delete_task/", checktray.views.deleteTask),
    path("test-daily-call/", trigger_test_call),
    path("confirm_image_upload/", checktray.view_images.confirm_image_upload),
    path("test-worker-call/", trigger_worker_test_call),
    path("test-autofeeder-worker-call/", trigger_autofeeder_worker_test_call),
    path("test-autofeeder-manager-call/", trigger_autofeeder_manager_test_call),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

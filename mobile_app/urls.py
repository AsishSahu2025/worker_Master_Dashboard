from django.urls import path
from .views import *

urlpatterns = [
    path('allpond_cluster/<id>/',PondListView.as_view()),
    # path('ponds/<int:pk>/', PondDetailsView.as_view()),
    path('pond-devices/<device>/<taskcatagory>/<created_at>/',Task_Of_PondDeviceListView.as_view()),
]

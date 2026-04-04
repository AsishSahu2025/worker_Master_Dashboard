from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import (
    EmptySessionsDetailView,
    GenerateCyclesView,
    SensorDataViewSet,
    MonitoringSessionViewSet,
    EnergySummaryView,
    ActiveSessionView,
    AbortSessionView,
)

# DRF router for ViewSets
router = DefaultRouter()
router.register(r"sensor-data", SensorDataViewSet, basename="sensor-data")
router.register(r"sessions", MonitoringSessionViewSet, basename="sessions")

urlpatterns = router.urls + [
    path('generate-cycles/', GenerateCyclesView.as_view(), name='generate-cycles'),
    path('energy-summary/', EnergySummaryView.as_view(), name='energy-summary'),
    path('active-session/', ActiveSessionView.as_view(), name='active-session'),
    path('abort-session/', AbortSessionView.as_view(), name='abort-session'),
    path('empty-sessions-detail/', EmptySessionsDetailView.as_view(), name='empty-sessions-detail'),
]
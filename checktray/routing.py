from django.urls import path
from . import consumers

websocket_urlpatterns = [
    path('ws/thermal-images/', consumers.ThermalImageConsumer.as_asgi()),
]
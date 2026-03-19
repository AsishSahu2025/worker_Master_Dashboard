"""
ASGI config for pilot_feedtray project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/5.0/howto/deployment/asgi/
"""
import os
from django.core.asgi import get_asgi_application
from channels.auth import AuthMiddlewareStack
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.security.websocket import AllowedHostsOriginValidator
from django.urls import path


os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pilot_feedtray.settings')
django_asgi_app = get_asgi_application()

import app1.routing
application = ProtocolTypeRouter({
    "http": django_asgi_app,
    "websocket": AllowedHostsOriginValidator(
        AuthMiddlewareStack(
            URLRouter(app1.routing.websocket_urlpatterns)
        )
    )
})





# import os
# from django.core.asgi import get_asgi_application
# import django
# from channels.http import AsgiHandler
# from channels.routing import ProtocolTypeRouter, URLRouter
# from channels.security.websocket import AllowedHostsOriginValidator
# from app1 import consumers
# from channels.auth import AuthMiddlewareStack
# from django.urls import path
# os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pilot_feedtray.settings')

# application = get_asgi_application()

# ws_pattern = []

# application = ProtocolTypeRouter({
#     "http": get_asgi_application(),
#     "websocket": AllowedHostsOriginValidator(
#         AuthMiddlewareStack(
#             URLRouter([
#                 path("ws/thermal-images/", consumers.ThermalImageConsumer.as_asgi()),
#             ])
#         )
#     )
# })
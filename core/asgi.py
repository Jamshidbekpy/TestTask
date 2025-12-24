"""
ASGI config for core project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/5.2/howto/deployment/asgi/
"""
import os
import django
from dotenv import load_dotenv
from channels.routing import ProtocolTypeRouter, URLRouter
from django.core.asgi import get_asgi_application

# Middleware
from core.middleware import JWTAuthMiddleware
from core.routers import websocket_urlpatterns

# Environment
load_dotenv()

# Django setup
os.environ.setdefault("DJANGO_SETTINGS_MODULE", os.getenv("DJANGO_SETTINGS_MODULE"))
django.setup()

# Postman uchun - faqat JWT middleware
application = ProtocolTypeRouter({
    "http": get_asgi_application(),
    "websocket": JWTAuthMiddleware(  # ✅ Faqat JWT middleware
        URLRouter(websocket_urlpatterns)
    ),
})
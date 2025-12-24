# core/routers.py
from django.urls import path
from apps.calendarapp.consumers import CalendarConsumer

websocket_urlpatterns = [
    path('ws/calendar/', CalendarConsumer.as_asgi()),
]
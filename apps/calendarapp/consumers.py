# apps/calendar/consumers.py
import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.utils import timezone
from datetime import timedelta
import logging
from .models import (
    UserRequest, ParsedEventDraft, Event, 
    EventInvite, EventAlert
)
from .nlp_parser import CalendarNLPParser

logger = logging.getLogger(__name__)

class CalendarConsumer(AsyncWebsocketConsumer):
    """Calendar uchun WebSocket consumer"""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.parser = CalendarNLPParser()
        self.user = None
        self.room_group_name = None
    
    async def connect(self):
        """WebSocket ga ulanish"""
        self.user = self.scope["user"]
        
        if not self.user.is_authenticated:
            await self.close()
            return
        
        # User uchun group yaratish
        self.room_group_name = f"user_{self.user.id}"
        
        # Group ga qo'shilish
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        
        await self.accept()
        
        logger.info(f"✅ WebSocket connected: {self.user.email}")
        
        # Connection tasdiqlash xabari
        await self.send(json.dumps({
            "type": "connection_success",
            "message": "WebSocket ga muvaffaqiyatli ulandiz",
            "user": {
                "id": str(self.user.id),
                "email": self.user.email,
                "username": self.user.username
            }
        }))
    
    async def disconnect(self, close_code):
        """WebSocket dan uzilish"""
        if self.room_group_name:
            await self.channel_layer.group_discard(
                self.room_group_name,
                self.channel_name
            )
        
        logger.info(f"❌ WebSocket disconnected: {self.user.email if self.user else 'Anonymous'}")
    
    
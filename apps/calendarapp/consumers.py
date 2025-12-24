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
    
    async def receive(self, text_data):
        """Client dan xabar qabul qilish"""
        try:
            data = json.loads(text_data)
            action = data.get("action")
            
            if action == "parse_text":
                await self.handle_parse_text(data)
            elif action == "confirm_draft":
                await self.handle_confirm_draft(data)
            elif action == "get_events":
                await self.handle_get_events(data)
            elif action == "update_event":
                await self.handle_update_event(data)
            elif action == "delete_event":
                await self.handle_delete_event(data)
            elif action == "respond_invite":
                await self.handle_respond_invite(data)
            else:
                await self.send_error("Unknown action")
                
        except json.JSONDecodeError:
            await self.send_error("Invalid JSON format")
        except Exception as e:
            logger.error(f"❌ Error in receive: {e}")
            await self.send_error(str(e))
    
    async def handle_parse_text(self, data):
        """Textni parse qilish"""
        try:
            text = data.get("text", "").strip()
            
            if not text:
                await self.send_error("Text bo'sh bo'lishi mumkin emas")
                return
            
            # 1. UserRequest ga yozish
            user_request = await self.create_user_request(text)
            
            # 2. Parser ishlatish
            parse_result = self.parser.parse(
                prompt=text,
                user_timezone=self.user.timezone if hasattr(self.user, 'timezone') else 'Asia/Tashkent'
            )
            
            if parse_result.get('error'):
                await self.send_error(parse_result['error'])
                return
            
            # 3. Draft yaratish
            draft = await self.create_parsed_draft(
                original_text=text,
                parse_result=parse_result
            )
            
            # 4. Client ga preview yuborish
            await self.send(json.dumps({
                "type": "draft_preview",
                "draft_id": str(draft.id),
                "preview": {
                    "title": parse_result['extracted_data'].get('title', 'Event'),
                    "time": f"{parse_result['extracted_data'].get('time_start', '')} - {parse_result['extracted_data'].get('time_end', '')}",
                    "all_day": parse_result['extracted_data'].get('all_day', False),
                    "invites": parse_result['extracted_data'].get('invite', []),
                    "alerts": parse_result['extracted_data'].get('alert', []),
                    "repeat": parse_result['extracted_data'].get('repeat'),
                    "url": parse_result['extracted_data'].get('url'),
                    "note": parse_result['extracted_data'].get('note', '')[:100] + "..." if parse_result['extracted_data'].get('note') else None,
                },
                "confidence": parse_result['confidence'],
                "suggestions": parse_result['suggestions']
            }))
            
            logger.info(f"✅ Text parsed for {self.user.email}: {text[:50]}...")
            
        except Exception as e:
            logger.error(f"❌ Parse error: {e}")
            await self.send_error(f"Parse error: {str(e)}")
    
    async def handle_confirm_draft(self, data):
        """Draft ni tasdiqlash va event yaratish"""
        try:
            draft_id = data.get("draft_id")
            
            if not draft_id:
                await self.send_error("Draft ID berilmagan")
                return
            
            # Event yaratish
            event = await self.create_event_from_draft(draft_id)
            
            if not event:
                await self.send_error("Event yaratib bo'lmadi")
                return
            
            # Client ga xabar berish
            await self.send(json.dumps({
                "type": "event_created",
                "message": f"✅ '{event.title}' uchrashuvi yaratildi",
                "event": {
                    "id": str(event.id),
                    "title": event.title,
                    "time_start": event.time_start.isoformat(),
                    "time_end": event.time_end.isoformat(),
                    "all_day": event.all_day,
                    "invite_count": await self.get_invite_count(event.id),
                    "alert_count": await self.get_alert_count(event.id)
                }
            }))
            
            # Boshqa client larga ham xabar berish (agar real-time kerak bo'lsa)
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    "type": "event_notification",
                    "message": f"Yangi uchrashuv yaratildi: {event.title}",
                    "event_id": str(event.id)
                }
            )
            
            logger.info(f"✅ Event created for {self.user.email}: {event.title}")
            
        except Exception as e:
            logger.error(f"❌ Confirm draft error: {e}")
            await self.send_error(f"Event yaratishda xato: {str(e)}")
    
    async def handle_get_events(self, data):
        """Event larni olish"""
        try:
            start_date = data.get("start_date")
            end_date = data.get("end_date")
            
            events = await self.get_user_events(start_date, end_date)
            
            await self.send(json.dumps({
                "type": "events_list",
                "events": events,
                "count": len(events)
            }))
            
        except Exception as e:
            logger.error(f"❌ Get events error: {e}")
            await self.send_error(f"Eventlarni olishda xato: {str(e)}")
    
    async def handle_update_event(self, data):
        """Event ni yangilash"""
        try:
            event_id = data.get("event_id")
            updates = data.get("updates", {})
            
            if not event_id or not updates:
                await self.send_error("Event ID yoki updates berilmagan")
                return
            
            event = await self.update_event(event_id, updates)
            
            await self.send(json.dumps({
                "type": "event_updated",
                "message": f"✅ '{event.title}' uchrashuvi yangilandi",
                "event": {
                    "id": str(event.id),
                    "title": event.title,
                    "time_start": event.time_start.isoformat(),
                    "time_end": event.time_end.isoformat()
                }
            }))
            
        except Exception as e:
            logger.error(f"❌ Update event error: {e}")
            await self.send_error(f"Event yangilashda xato: {str(e)}")
    
    async def handle_delete_event(self, data):
        """Event ni o'chirish"""
        try:
            event_id = data.get("event_id")
            
            if not event_id:
                await self.send_error("Event ID berilmagan")
                return
            
            result = await self.delete_event(event_id)
            
            await self.send(json.dumps({
                "type": "event_deleted",
                "message": "✅ Uchrashuv o'chirildi",
                "event_id": event_id,
                "success": result
            }))
            
        except Exception as e:
            logger.error(f"❌ Delete event error: {e}")
            await self.send_error(f"Event o'chirishda xato: {str(e)}")
    
    async def handle_respond_invite(self, data):
        """Invite ga javob berish"""
        try:
            invite_id = data.get("invite_id")
            response = data.get("response")  # 'accept', 'decline', 'tentative'
            
            if not invite_id or not response:
                await self.send_error("Invite ID yoki response berilmagan")
                return
            
            invite = await self.respond_to_invite(invite_id, response)
            
            await self.send(json.dumps({
                "type": "invite_responded",
                "message": f"✅ Taklif {response} qilindi",
                "invite": {
                    "id": str(invite.id),
                    "event_title": invite.event.title,
                    "status": invite.status
                }
            }))
            
        except Exception as e:
            logger.error(f"❌ Respond invite error: {e}")
            await self.send_error(f"Taklifga javob berishda xato: {str(e)}")
    
    async def event_notification(self, event):
        """Event notification handler"""
        await self.send(text_data=json.dumps({
            "type": "notification",
            "message": event["message"],
            "event_id": event.get("event_id")
        }))
    
    async def send_error(self, message):
        """Error xabarini yuborish"""
        await self.send(json.dumps({
            "type": "error",
            "message": message
        }))
    
    # ============ DATABASE OPERATIONS ============
    
    @database_sync_to_async
    def create_user_request(self, text):
        """UserRequest yaratish"""
        return UserRequest.objects.create(
            user=self.user,
            text=text
        )
    
    @database_sync_to_async
    def create_parsed_draft(self, original_text, parse_result):
        """ParsedEventDraft yaratish"""
        return ParsedEventDraft.objects.create(
            user=self.user,
            original_text=original_text,
            language=parse_result['language'],
            intent=parse_result['intent'],
            extracted_data=parse_result['extracted_data'],
            expires_at=timezone.now() + timedelta(hours=24)
        )
    
    @database_sync_to_async
    def create_event_from_draft(self, draft_id):
        """Draft dan event yaratish"""
        try:
            draft = ParsedEventDraft.objects.get(
                id=draft_id,
                user=self.user,
                is_confirmed=False,
                expires_at__gt=timezone.now()
            )
            
            extracted = draft.extracted_data
            
            # Event yaratish
            event = Event.objects.create(
                user=self.user,
                title=extracted.get('title', 'Event'),
                all_day=extracted.get('all_day', False),
                time_start=extracted['time_start'],
                time_end=extracted['time_end'],
                repeat=extracted.get('repeat'),
                url=extracted.get('url'),
                note=extracted.get('note'),
                timezone=self.user.timezone if hasattr(self.user, 'timezone') else 'Asia/Tashkent'
            )
            
            # Invites qo'shish
            for email in extracted.get('invite', []):
                EventInvite.objects.create(
                    event=event,
                    email=email,
                    status='pending'
                )
            
            # Alerts qo'shish
            for alert_str in extracted.get('alert', []):
                import re
                match = re.match(r'(\d+)([mhdw])', alert_str)
                if match:
                    EventAlert.objects.create(
                        event=event,
                        value=int(match.group(1)),
                        unit=match.group(2)
                    )
            
            # Draft ni confirmed qilish
            draft.is_confirmed = True
            draft.confirmed_at = timezone.now()
            draft.save()
            
            return event
            
        except ParsedEventDraft.DoesNotExist:
            return None
    
    @database_sync_to_async
    def get_invite_count(self, event_id):
        """Eventdagi invite lar soni"""
        return EventInvite.objects.filter(event_id=event_id).count()
    
    @database_sync_to_async
    def get_alert_count(self, event_id):
        """Eventdagi alert lar soni"""
        return EventAlert.objects.filter(event_id=event_id).count()
    
    @database_sync_to_async
    def get_user_events(self, start_date=None, end_date=None):
        """User eventlarini olish"""
        from django.db.models import Q
        
        query = Q(user=self.user) | Q(invites__email=self.user.email, invites__status='accepted')
        events = Event.objects.filter(query, is_cancelled=False).distinct()
        
        if start_date:
            events = events.filter(time_start__gte=start_date)
        if end_date:
            events = events.filter(time_start__lte=end_date)
        
        return list(events.values(
            'id', 'title', 'time_start', 'time_end', 'all_day',
            'url', 'note', 'timezone'
        ))
    
    @database_sync_to_async
    def update_event(self, event_id, updates):
        """Event ni yangilash"""
        event = Event.objects.get(id=event_id, user=self.user)
        
        for key, value in updates.items():
            if hasattr(event, key):
                setattr(event, key, value)
        
        event.save()
        return event
    
    @database_sync_to_async
    def delete_event(self, event_id):
        """Event ni o'chirish"""
        try:
            event = Event.objects.get(id=event_id, user=self.user)
            event.delete()
            return True
        except Event.DoesNotExist:
            return False
    
    @database_sync_to_async
    def respond_to_invite(self, invite_id, response):
        """Invite ga javob berish"""
        invite = EventInvite.objects.get(
            id=invite_id,
            email=self.user.email
        )
        
        invite.status = response
        invite.save()
        return invite
from django.utils import timezone
from datetime import datetime, timedelta
import re
import pytz
from dateutil import parser as date_parser
import json

from .models import UserRequest, ParsedEventDraft, AuditLog, Event, EventInvite, EventAlert
from .nlp_parser import CalendarNLPParser, CalendarNLPHelper


class CalendarNLPService:
    """
    Real-time NLP processing service
    WebSocket dan kelgan text ni qabul qilib, parse qiladi va database ga yozadi
    """
    
    def __init__(self):
        self.parser = CalendarNLPParser()
        self.helper = CalendarNLPHelper()
    
    async def process_user_request(self, user, text: str, language: str = None):
        """
        User request ni process qilish
        1. UserRequest modelga saqlash
        2. NLP parse qilish
        3. ParsedEventDraft yaratish
        4. Response tayyorlash
        """
        try:
            print(f"🔍 Processing request from user {user.email}: {text[:50]}...")
            
            # 1. UserRequest saqlash
            user_request = await self._save_user_request(user, text)
            
            # 2. NLP parse qilish
            parse_result = self.parser.parse(text, language, user.timezone or 'Asia/Tashkent')
            
            # 3. ParsedEventDraft yaratish
            draft = await self._create_parsed_draft(user, user_request, parse_result)
            
            # 4. Audit log yozish
            await self._log_parsing(user, text, parse_result)
            
            # 5. Response tayyorlash
            response = self._prepare_response(user_request, draft, parse_result)
            
            print(f"✅ Request processed. Draft ID: {draft.id}, Intent: {parse_result['intent']}")
            
            return response
            
        except Exception as e:
            print(f"❌ NLP processing error: {str(e)}")
            raise
    
    async def _save_user_request(self, user, text: str):
        """UserRequest modelga saqlash"""
        try:
            user_request = UserRequest.objects.create(
                user=user,
                text=text
            )
            print(f"📝 UserRequest saved: {user_request.id}")
            return user_request
        except Exception as e:
            print(f"❌ UserRequest save error: {str(e)}")
            raise
    
    async def _create_parsed_draft(self, user, user_request, parse_result):
        """ParsedEventDraft yaratish"""
        try:
            # 24 soatdan keyin o'chirish
            expires_at = timezone.now() + timedelta(hours=24)
            
            draft = ParsedEventDraft.objects.create(
                user=user,
                original_text=parse_result['original_prompt'],
                language=parse_result['language'],
                intent=parse_result['intent'],
                extracted_data=parse_result['extracted_data'],
                expires_at=expires_at
            )
            
            print(f"📄 ParsedEventDraft created: {draft.id}")
            return draft
            
        except Exception as e:
            print(f"❌ ParsedEventDraft create error: {str(e)}")
            raise
    
    async def _log_parsing(self, user, text, parse_result):
        """Audit log yozish"""
        try:
            AuditLog.objects.create(
                user=user,
                action='parse',
                model_name='UserRequest',
                object_id=None,  # UserRequest ID bo'lishi mumkin
                changes={
                    'original_text': text[:100],
                    'parse_result': {
                        'intent': parse_result['intent'],
                        'language': parse_result['language'],
                        'confidence': parse_result['confidence']
                    }
                }
            )
            print(f"📊 Audit log created for parsing")
        except Exception as e:
            print(f"⚠️ Audit log error: {str(e)}")
    
    def _prepare_response(self, user_request, draft, parse_result):
        """WebSocket response tayyorlash"""
        return {
            'type': 'parsed_response',
            'status': 'success',
            'timestamp': timezone.now().isoformat(),
            'request_id': str(user_request.id),
            'draft_id': str(draft.id),
            'parse_result': {
                'intent': parse_result['intent'],
                'language': parse_result['language'],
                'confidence': parse_result['confidence'],
                'suggestions': parse_result.get('suggestions', [])
            },
            'extracted_data': parse_result['extracted_data'],
            'next_actions': [
                {
                    'action': 'confirm_draft',
                    'label': 'Tasdiqlash',
                    'data': {'draft_id': str(draft.id)}
                },
                {
                    'action': 'edit_draft',
                    'label': 'Tahrirlash',
                    'data': {'draft_id': str(draft.id)}
                },
                {
                    'action': 'cancel_draft',
                    'label': 'Bekor qilish',
                    'data': {'draft_id': str(draft.id)}
                }
            ]
        }
    
    async def confirm_draft(self, user, draft_id):
        """
        Draft ni tasdiqlash va Event yaratish
        """
        try:
            print(f"✅ Confirming draft: {draft_id}")
            
            # 1. Draft ni olish
            draft = await self._get_draft(user, draft_id)
            
            # 2. Event yaratish
            event = await self._create_event_from_draft(draft)
            
            # 3. Draft ni confirmed qilish
            await self._mark_draft_confirmed(draft, event)
            
            # 4. Audit log yozish
            await self._log_event_creation(user, event, draft)
            
            # 5. Response tayyorlash
            response = self._prepare_confirmation_response(event, draft)
            
            print(f"🎉 Event created: {event.title} ({event.id})")
            
            return response
            
        except Exception as e:
            print(f"❌ Draft confirmation error: {str(e)}")
            raise
    
    async def _get_draft(self, user, draft_id):
        """Draft ni olish va tekshirish"""
        try:
            draft = ParsedEventDraft.objects.get(
                id=draft_id,
                user=user,
                is_confirmed=False
            )
            return draft
        except ParsedEventDraft.DoesNotExist:
            raise Exception("Draft topilmadi yoki allaqachon tasdiqlangan")
    
    async def _create_event_from_draft(self, draft):
        """Draft dan Event yaratish"""
        extracted = draft.extracted_data
        
        # Timezone ni olish
        tz = pytz.timezone(draft.user.timezone or 'Asia/Tashkent')
        
        # Vaqtlarni convert qilish
        time_start = datetime.fromisoformat(extracted['time_start'].replace('Z', '+00:00'))
        time_end = datetime.fromisoformat(extracted['time_end'].replace('Z', '+00:00'))
        
        if time_start.tzinfo is None:
            time_start = tz.localize(time_start)
        if time_end.tzinfo is None:
            time_end = tz.localize(time_end)
        
        # Event yaratish
        event = Event.objects.create(
            user=draft.user,
            title=extracted.get('title', 'Uchrashuv'),
            all_day=extracted.get('all_day', False),
            time_start=time_start,
            time_end=time_end,
            repeat=extracted.get('repeat'),
            url=extracted.get('url'),
            note=extracted.get('note'),
            timezone=str(tz)
        )
        
        # Invites yaratish
        invites = extracted.get('invite', [])
        for email in invites:
            EventInvite.objects.create(
                event=event,
                email=email,
                status='pending'
            )
        
        # Alerts yaratish
        alerts = extracted.get('alert', [])
        for alert_str in alerts:
            match = re.match(r'(\d+)([mhdw])', alert_str)
            if match:
                EventAlert.objects.create(
                    event=event,
                    value=int(match.group(1)),
                    unit=match.group(2)
                )
        
        return event
    
    async def _mark_draft_confirmed(self, draft, event):
        """Draft ni confirmed qilish"""
        draft.is_confirmed = True
        draft.confirmed_at = timezone.now()
        draft.save()
    
    async def _log_event_creation(self, user, event, draft):
        """Event yaratilganligi haqida audit log"""
        AuditLog.objects.create(
            user=user,
            event=event,
            action='create',
            model_name='Event',
            object_id=event.id,
            changes={
                'from_draft': str(draft.id),
                'title': event.title,
                'time_start': event.time_start.isoformat(),
                'time_end': event.time_end.isoformat()
            }
        )
    
    def _prepare_confirmation_response(self, event, draft):
        """Confirmation response tayyorlash"""
        return {
            'type': 'event_created',
            'status': 'success',
            'timestamp': timezone.now().isoformat(),
            'message': f"✅ '{event.title}' uchrashuvi yaratildi",
            'event': {
                'id': str(event.id),
                'title': event.title,
                'time_start': event.time_start.isoformat(),
                'time_end': event.time_end.isoformat(),
                'all_day': event.all_day,
                'timezone': event.timezone
            },
            'draft': {
                'id': str(draft.id),
                'confirmed_at': draft.confirmed_at.isoformat()
            },
            'statistics': {
                'invites_count': event.invites.count(),
                'alerts_count': event.alerts.count()
            }
        }
    
    async def edit_draft(self, user, draft_id, edits: dict):
        """
        Draft ni tahrirlash
        """
        try:
            print(f"✏️ Editing draft: {draft_id}")
            
            # Draft ni olish
            draft = await self._get_draft(user, draft_id)
            
            # Extracted data ni yangilash
            current_data = draft.extracted_data.copy()
            current_data.update(edits)
            
            draft.extracted_data = current_data
            draft.save()
            
            # Audit log
            AuditLog.objects.create(
                user=user,
                action='update',
                model_name='ParsedEventDraft',
                object_id=draft.id,
                changes={'edits': edits}
            )
            
            response = {
                'type': 'draft_updated',
                'status': 'success',
                'timestamp': timezone.now().isoformat(),
                'message': 'Draft muvaffaqiyatli yangilandi',
                'draft_id': str(draft.id),
                'updated_fields': list(edits.keys())
            }
            
            print(f"📝 Draft updated: {draft.id}")
            
            return response
            
        except Exception as e:
            print(f"❌ Draft edit error: {str(e)}")
            raise
    
    async def cancel_draft(self, user, draft_id):
        """
        Draft ni bekor qilish
        """
        try:
            print(f"❌ Canceling draft: {draft_id}")
            
            # Draft ni olish
            draft = ParsedEventDraft.objects.get(
                id=draft_id,
                user=user,
                is_confirmed=False
            )
            
            # Audit log
            AuditLog.objects.create(
                user=user,
                action='delete',
                model_name='ParsedEventDraft',
                object_id=draft.id,
                changes={'original_text': draft.original_text[:100]}
            )
            
            # Draft ni o'chirish
            draft.delete()
            
            response = {
                'type': 'draft_cancelled',
                'status': 'success',
                'timestamp': timezone.now().isoformat(),
                'message': 'Draft bekor qilindi'
            }
            
            print(f"🗑️ Draft cancelled: {draft_id}")
            
            return response
            
        except Exception as e:
            print(f"❌ Draft cancellation error: {str(e)}")
            raise
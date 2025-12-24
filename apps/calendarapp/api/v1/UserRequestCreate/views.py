import logging
from rest_framework.generics import CreateAPIView
from .serializers import UserRequestCreateSerializer
from apps.calendarapp.models import UserRequest, Event, EventAlert, EventInvite, AuditLog
from apps.calendarapp.nlp_parser import CalendarNLPParser, CalendarNLPHelper

class UserRequestCreateView(CreateAPIView):
    """
    Yangi user so'rovi yaratish uchun API view
    """
    serializer_class = UserRequestCreateSerializer
    
    
    def create(self, request, *args, **kwargs):
        serislizer = self.get_serializer(data=request.data)
        serislizer.is_valid(raise_exception=True)
        
        parser = CalendarNLPParser()
        helper = CalendarNLPHelper()
        
        parsed_data = parser.parse(request.data.get('text', ''))
        
        print(f"Parsed Data: {parsed_data}............................................")
        
        intent = parsed_data.get('intent', 'unknown')
        language = parsed_data.get('language', 'unknown')
        confidence = parsed_data.get('confidence', 0.0)
        extracted_data = parsed_data.get('extracted_data', {})
        suggestions = parsed_data.get('suggestions', [])
        
    #    {'intent': 'CREATE', 'language': 'uz', 'confidence': 0.95, 'extracted_data': {'title': 'uchrashuvim bor', 'all_day': False, 'time_start': '2025-12-24T05:00:31.107968+05:00', 'time_end': '2025-12-24T06:00:31.107968+05:00', 'repeat': None, 'invite': [], 'alert': [], 'url': None, 'note': 'Bugun 5:00 da u
    #    rashuvim bor'}, 'suggestions': []}
    
        if intent == 'CREATE' and confidence >= 0.7:
            # Yangi event yaratish
            Event.objects.create(
                user=request.user,
                title=extracted_data.get('title', 'No Title'),
                all_day=extracted_data.get('all_day', False),
                time_start=helper.parse_datetime(extracted_data.get('time_start')),
                time_end=helper.parse_datetime(extracted_data.get('time_end')),
                repeat=extracted_data.get('repeat'),
                url=extracted_data.get('url'),
                note=extracted_data.get('note', ''),
            )
        
            AuditLog.objects.create(
                user=request.user,
                action='create',
                model_name='Event',
                object_id=Event.objects.last().id,
                changes=extracted_data,
            )
        
        elif intent == 'CANCEL' and confidence >= 0.7:
            # Event bekor qilish logikasi
            title = extracted_data.get('title')
            event = Event.objects.filter(user=request.user, title__icontains=title).last()
            if event:
                event.delete()
                
                AuditLog.objects.create(
                    user=request.user,
                    action='delete',
                    model_name='Event',
                    object_id=event.id,
                    changes={'title': title},
                )
        elif intent == 'UPDATE' and confidence >= 0.7:
            # Event yangilash logikasi
            title = extracted_data.get('title')
            event = Event.objects.filter(user=request.user, title__icontains=title).last()
            if event:
                old_data = {
                    'title': event.title,
                    'time_start': event.time_start.isoformat(),
                    'time_end': event.time_end.isoformat(),
                }
                event.time_start = helper.parse_datetime(extracted_data.get('time_start', event.time_start.isoformat()))
                event.time_end = helper.parse_datetime(extracted_data.get('time_end', event.time_end.isoformat()))
                event.save()
                
                new_data = {
                    'title': event.title,
                    'time_start': event.time_start.isoformat(),
                    'time_end': event.time_end.isoformat(),
                }
                
                AuditLog.objects.create(
                    user=request.user,
                    action='update',
                    model_name='Event',
                    object_id=event.id,
                    changes={'old': old_data, 'new': new_data},
                )
                
        
        elif intent == 'DELETE' and confidence >= 0.7:
            # Event o'chirish logikasi
            title = extracted_data.get('title')
            event = Event.objects.filter(user=request.user, title__icontains=title).last()
            if event:
                event.delete()
                
                AuditLog.objects.create(
                    user=request.user,
                    action='delete',
                    model_name='Event',
                    object_id=event.id,
                    changes={'title': title},
                )
                
        else:
            logging.info(f"Unknown intent or low confidence: {intent} ({confidence})")
            

        # Yangi so'rov yaratildi uchun audit log yaratish
        AuditLog.objects.create(
            user=request.user,
            action='create',
            model_name='UserRequest',
            object_id=response.data['id'],
            changes={'text': request.data.get('text', '')},
        )   
        response = super().create(request, *args, **kwargs)
        return response

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)
        
        


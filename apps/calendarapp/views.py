from rest_framework import generics, status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import  PermissionDenied
from django.utils import timezone
from django.db import transaction
from django.shortcuts import get_object_or_404
from django.db.models import Q
from datetime import datetime, timedelta
import logging

from .models import (
    Event, EventInvite, EventAlert,
    ParsedEventDraft, UserRequest, AuditLog
)
from .serializers import (
    EventSerializer, CreateEventSerializer, EventInviteSerializer,
    InviteResponseSerializer, ParseTextSerializer, ParseResponseSerializer,
    ConfirmDraftSerializer, UserRequestSerializer, AuditLogSerializer
)
from .nlp_parser import CalendarNLPParser

logger = logging.getLogger(__name__)

# ============ EVENT VIEWS ============

class EventListCreateAPIView(generics.ListCreateAPIView):
    """Event lar ro'yxati va yaratish"""
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        # Userning eventlari yoki user qabul qilgan eventlar
        return Event.objects.filter(
            Q(user=self.request.user) | 
            Q(invites__email=self.request.user.email, invites__status='accepted')
        ).filter(is_cancelled=False).distinct().order_by('time_start')
    
    def get_serializer_class(self):
        if self.request.method == 'POST':
            return CreateEventSerializer
        return EventSerializer
    
    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['request'] = self.request
        return context
    
    def perform_create(self, serializer):
        serializer.save()

class EventDetailAPIView(generics.RetrieveUpdateDestroyAPIView):
    """Event detail, yangilash, o'chirish"""
    permission_classes = [IsAuthenticated]
    serializer_class = EventSerializer
    lookup_field = 'id'
    
    def get_queryset(self):
        return Event.objects.filter(user=self.request.user)
    
    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['request'] = self.request
        return context
    
    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        self.perform_destroy(instance)
        return Response({
            'message': f"'{instance.title}' uchrashuvi o'chirildi"
        }, status=status.HTTP_200_OK)

class CancelEventAPIView(generics.UpdateAPIView):
    """Event ni bekor qilish"""
    permission_classes = [IsAuthenticated]
    serializer_class = EventSerializer
    http_method_names = ['patch']
    
    def get_queryset(self):
        return Event.objects.filter(user=self.request.user)
    
    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.is_cancelled = True
        instance.save()
        
        serializer = self.get_serializer(instance)
        return Response({
            'message': f"'{instance.title}' uchrashuvi bekor qilindi",
            'event': serializer.data
        })

class TodayEventsAPIView(generics.ListAPIView):
    """Bugungi eventlar"""
    permission_classes = [IsAuthenticated]
    serializer_class = EventSerializer
    
    def get_queryset(self):
        today = timezone.now().date()
        return Event.objects.filter(
            user=self.request.user,
            time_start__date=today,
            is_cancelled=False
        ).order_by('time_start')
    
    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['request'] = self.request
        return context

class UpcomingEventsAPIView(generics.ListAPIView):
    """Kelgusi eventlar"""
    permission_classes = [IsAuthenticated]
    serializer_class = EventSerializer
    
    def get_queryset(self):
        return Event.objects.filter(
            user=self.request.user,
            time_start__gte=timezone.now(),
            is_cancelled=False
        ).order_by('time_start')[:10]
    
    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['request'] = self.request
        return context

# ============ INVITE VIEWS ============

class MyInvitesAPIView(generics.ListAPIView):
    """User ga jo'natilgan invites"""
    permission_classes = [IsAuthenticated]
    serializer_class = EventInviteSerializer
    
    def get_queryset(self):
        return EventInvite.objects.filter(
            email=self.request.user.email,
            status='pending'
        ).select_related('event').order_by('-created_at')
    
    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['request'] = self.request
        return context

class RespondToInviteAPIView(generics.UpdateAPIView):
    """Invite ga javob berish"""
    permission_classes = [IsAuthenticated]
    serializer_class = InviteResponseSerializer
    http_method_names = ['patch']
    
    def get_object(self):
        invite_id = self.kwargs.get('invite_id')
        return get_object_or_404(
            EventInvite,
            id=invite_id,
            email=self.request.user.email
        )
    
    def update(self, request, *args, **kwargs):
        invite = self.get_object()
        serializer = self.get_serializer(data=request.data)
        
        if serializer.is_valid():
            invite.status = serializer.validated_data['response']
            invite.save()
            
            return Response({
                'message': f"Taklif {invite.status} qilindi",
                'invite': EventInviteSerializer(invite, context={'request': request}).data
            })
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

# ============ NLP PARSER VIEWS ============

class ParseTextView(APIView):
    """Textni parse qilish"""
    permission_classes = [IsAuthenticated]
    parser = CalendarNLPParser()
    
    def post(self, request):
        serializer = ParseTextSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        text = serializer.validated_data['text']
        language = serializer.validated_data.get('language')
        
        # 1. UserRequest ga yozish
        UserRequest.objects.create(
            user=request.user,
            text=text
        )
        
        # 2. Parse qilish
        parse_result = self.parser.parse(
            prompt=text,
            language=language,
            user_timezone=request.user.timezone if hasattr(request.user, 'timezone') else 'Asia/Tashkent'
        )
        
        if parse_result.get('error'):
            return Response(
                {'error': parse_result['error']},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # 3. Draft yaratish
        draft = ParsedEventDraft.objects.create(
            user=request.user,
            original_text=text,
            language=parse_result['language'],
            intent=parse_result['intent'],
            extracted_data=parse_result['extracted_data'],
            expires_at=timezone.now() + timedelta(hours=24)
        )
        
        # Response tayyorlash
        extracted = parse_result['extracted_data']
        response_serializer = ParseResponseSerializer(data={
            'draft_id': draft.id,
            'title': extracted.get('title', 'Event'),
            'time_start': extracted.get('time_start'),
            'time_end': extracted.get('time_end'),
            'all_day': extracted.get('all_day', False),
            'invites': extracted.get('invite', []),
            'alerts': extracted.get('alert', []),
            'repeat': extracted.get('repeat'),
            'url': extracted.get('url'),
            'note': extracted.get('note'),
            'confidence': parse_result['confidence'],
            'suggestions': parse_result['suggestions']
        })
        
        if response_serializer.is_valid():
            return Response(response_serializer.validated_data)
        
        return Response(response_serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class ConfirmDraftView(APIView):
    """Draft ni tasdiqlash va event yaratish"""
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        serializer = ConfirmDraftSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        draft_id = serializer.validated_data['draft_id']
        
        try:
            draft = ParsedEventDraft.objects.get(
                id=draft_id,
                user=request.user,
                is_confirmed=False,
                expires_at__gt=timezone.now()
            )
        except ParsedEventDraft.DoesNotExist:
            return Response(
                {'error': 'Draft topilmadi yoki muddati o\'tgan'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        extracted = draft.extracted_data
        
        with transaction.atomic():
            # Event yaratish
            event = Event.objects.create(
                user=request.user,
                title=extracted.get('title', 'Event'),
                all_day=extracted.get('all_day', False),
                time_start=extracted['time_start'],
                time_end=extracted['time_end'],
                repeat=extracted.get('repeat'),
                url=extracted.get('url'),
                note=extracted.get('note'),
                timezone=request.user.timezone if hasattr(request.user, 'timezone') else 'Asia/Tashkent'
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
        
        return Response({
            'message': f"✅ '{event.title}' uchrashuvi yaratildi",
            'event_id': str(event.id),
            'title': event.title,
            'time_start': event.time_start,
            'time_end': event.time_end,
            'invite_count': event.invites.count(),
            'alert_count': event.alerts.count()
        }, status=status.HTTP_201_CREATED)

# ============ OTHER VIEWS ============

class UserRequestListAPIView(generics.ListAPIView):
    """User requestlari ro'yxati"""
    permission_classes = [IsAuthenticated]
    serializer_class = UserRequestSerializer
    
    def get_queryset(self):
        return UserRequest.objects.filter(
            user=self.request.user
        ).order_by('-created_at')[:50]

class AuditLogListAPIView(generics.ListAPIView):
    """Audit log lar ro'yxati"""
    permission_classes = [IsAuthenticated]
    serializer_class = AuditLogSerializer
    
    def get_queryset(self):
        return AuditLog.objects.filter(
            user=self.request.user
        ).order_by('-created_at')[:100]
    
    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['request'] = self.request
        return context

# ============ ADMIN VIEWS ============

class EventInviteListAPIView(generics.ListAPIView):
    """Event uchun barcha invites"""
    permission_classes = [IsAuthenticated]
    serializer_class = EventInviteSerializer
    
    def get_queryset(self):
        event_id = self.kwargs.get('event_id')
        event = get_object_or_404(Event, id=event_id)
        
        # Faqat event owner ko'ra oladi
        if event.user != self.request.user:
            raise PermissionDenied("Bu uchrashuvga kirish huquqingiz yo'q")
        
        return event.invites.all().order_by('-created_at')
    
    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['request'] = self.request
        return context

class EventAlertListAPIView(generics.ListAPIView):
    """Event uchun barcha alerts"""
    permission_classes = [IsAuthenticated]
    serializer_class = EventInviteSerializer
    
    def get_queryset(self):
        event_id = self.kwargs.get('event_id')
        event = get_object_or_404(Event, id=event_id)
        
        # Faqat event owner ko'ra oladi
        if event.user != self.request.user:
            raise PermissionDenied("Bu uchrashuvga kirish huquqingiz yo'q")
        
        return event.alerts.all().order_by('-created_at')
    
    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['request'] = self.request
        return context

# ============ FILTERED EVENTS VIEWS ============

class EventsByDateRangeAPIView(generics.ListAPIView):
    """Date range bo'yicha eventlar"""
    permission_classes = [IsAuthenticated]
    serializer_class = EventSerializer
    
    def get_queryset(self):
        start_date = self.request.query_params.get('start_date')
        end_date = self.request.query_params.get('end_date')
        
        queryset = Event.objects.filter(
            Q(user=self.request.user) | 
            Q(invites__email=self.request.user.email, invites__status='accepted')
        ).filter(is_cancelled=False).distinct()
        
        if start_date:
            try:
                start_date = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
                queryset = queryset.filter(time_start__gte=start_date)
            except ValueError:
                pass
        
        if end_date:
            try:
                end_date = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
                queryset = queryset.filter(time_end__lte=end_date)
            except ValueError:
                pass
        
        return queryset.order_by('time_start')
    
    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['request'] = self.request
        return context
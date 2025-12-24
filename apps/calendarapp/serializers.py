# apps/calendar/serializers.py
from rest_framework import serializers
from django.utils import timezone
from .models import (
    Event, EventInvite, EventAlert,
    ParsedEventDraft, UserRequest, AuditLog
)

# ============ EVENT SERIALIZERS ============

class EventSerializer(serializers.ModelSerializer):
    invites = serializers.SerializerMethodField()
    alerts = serializers.SerializerMethodField()
    is_owner = serializers.SerializerMethodField()
    
    class Meta:
        model = Event
        fields = [
            'id', 'title', 'all_day', 'time_start', 'time_end',
            'repeat', 'url', 'note', 'is_cancelled', 'timezone',
            'invites', 'alerts', 'is_owner', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def get_invites(self, obj):
        return list(obj.invites.values('id', 'email', 'status'))
    
    def get_alerts(self, obj):
        return list(obj.alerts.values('id', 'value', 'unit', 'is_sent', 'sent_at'))
    
    def get_is_owner(self, obj):
        request = self.context.get('request')
        if request and request.user:
            return obj.user == request.user
        return False
    
    def validate(self, data):
        if data.get('time_start') and data.get('time_end'):
            if data['time_start'] >= data['time_end']:
                raise serializers.ValidationError({
                    'time_end': "Tugash vaqti boshlanish vaqtidan keyin bo'lishi kerak"
                })
        return data

class CreateEventSerializer(serializers.ModelSerializer):
    invites = serializers.ListField(
        child=serializers.EmailField(),
        write_only=True,
        required=False,
        default=[]
    )
    alerts = serializers.ListField(
        child=serializers.CharField(max_length=10),
        write_only=True,
        required=False,
        default=[]
    )
    
    class Meta:
        model = Event
        fields = [
            'title', 'all_day', 'time_start', 'time_end',
            'repeat', 'url', 'note', 'invites', 'alerts'
        ]
    
    def create(self, validated_data):
        invites = validated_data.pop('invites', [])
        alerts = validated_data.pop('alerts', [])
        
        request = self.context.get('request')
        validated_data['user'] = request.user
        validated_data['timezone'] = request.user.timezone if hasattr(request.user, 'timezone') else 'Asia/Tashkent'
        
        event = Event.objects.create(**validated_data)
        
        # Invites yaratish
        for email in invites:
            EventInvite.objects.create(
                event=event,
                email=email,
                status='pending'
            )
        
        # Alerts yaratish
        for alert_str in alerts:
            import re
            match = re.match(r'(\d+)([mhdw])', alert_str)
            if match:
                EventAlert.objects.create(
                    event=event,
                    value=int(match.group(1)),
                    unit=match.group(2)
                )
        
        return event

# ============ INVITE SERIALIZERS ============

class EventInviteSerializer(serializers.ModelSerializer):
    event_title = serializers.CharField(source='event.title', read_only=True)
    event_time = serializers.DateTimeField(source='event.time_start', read_only=True)
    is_owner = serializers.SerializerMethodField()
    
    class Meta:
        model = EventInvite
        fields = [
            'id', 'event', 'event_title', 'event_time',
            'email', 'status', 'is_owner', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']
    
    def get_is_owner(self, obj):
        request = self.context.get('request')
        if request and request.user:
            return obj.event.user == request.user
        return False

class InviteResponseSerializer(serializers.Serializer):
    response = serializers.ChoiceField(
        choices=['accepted', 'declined', 'tentative']
    )

# ============ NLP PARSER SERIALIZERS ============

class ParseTextSerializer(serializers.Serializer):
    text = serializers.CharField(max_length=1000)
    language = serializers.ChoiceField(
        choices=[('uz', 'Uzbek'), ('ru', 'Russian'), ('en', 'English')],
        required=False,
        allow_null=True
    )

class ParseResponseSerializer(serializers.Serializer):
    draft_id = serializers.UUIDField()
    title = serializers.CharField()
    time_start = serializers.DateTimeField()
    time_end = serializers.DateTimeField()
    all_day = serializers.BooleanField()
    invites = serializers.ListField(child=serializers.EmailField())
    alerts = serializers.ListField(child=serializers.CharField())
    repeat = serializers.CharField(allow_null=True)
    url = serializers.URLField(allow_null=True)
    note = serializers.CharField(allow_null=True)
    confidence = serializers.FloatField()
    suggestions = serializers.ListField(child=serializers.CharField())

class ConfirmDraftSerializer(serializers.Serializer):
    draft_id = serializers.UUIDField()

# ============ OTHER SERIALIZERS ============

class UserRequestSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserRequest
        fields = ['id', 'text', 'created_at']
        read_only_fields = ['id', 'created_at']

class AuditLogSerializer(serializers.ModelSerializer):
    user_email = serializers.EmailField(source='user.email', read_only=True)
    
    class Meta:
        model = AuditLog
        fields = [
            'id', 'user', 'user_email', 'event', 'action',
            'model_name', 'object_id', 'changes', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']
from rest_framework import serializers
from apps.calendarapp.models import Event

class EventCreateSerializer(serializers.ModelSerializer):
    """
    Yangi event yaratish uchun serializer
    """
    class Meta:
        model = Event
        fields = [
            'id',
            'title',
            'all_day',
            'time_start',
            'time_end',
            'repeat',
            'url',
            'note',
            'timezone',
        ]
        read_only_fields = ['id']
        

class EventRetrieveDestroySerializer(serializers.ModelSerializer):
    """
    Eventni olish yoki o'chirish uchun serializer
    """
    class Meta:
        model = Event
        fields = [
            'id',
            'title',
            'all_day',
            'time_start',
            'time_end',
            'repeat',
            'url',
            'note',
            'timezone',
        ]
        read_only_fields = ['id']
        
    def to_representation(self, instance):
        representation = super().to_representation(instance)
        # Qo'shimcha formatlash yoki maydonlarni o'zgartirish kerak bo'lsa, shu yerda amalga oshiring
        return representation


class EventListSerializer(serializers.ModelSerializer):
    """
    Eventni listini olish uchun serializer
    """
    class Meta:
        model = Event
        fields = [
            'id',
            'title',
            'all_day',
            'time_start',
            'time_end',
            'repeat',
            'url',
            'note',
            'timezone',
        ]
        read_only_fields = ['id']
        
        
    def to_representation(self, instance):
        representation = super().to_representation(instance)
        # Qo'shimcha formatlash yoki maydonlarni o'zgartirish kerak bo'lsa, shu yerda amalga oshiring
        return representation
    
class EventUpdateSerializer(serializers.ModelSerializer):
    """
    Eventni yangilash uchun serializer
    """
    class Meta:
        model = Event
        fields = [
            'title',
            'all_day',
            'time_start',
            'time_end',
            'repeat',
            'url',
            'note',
            'timezone',
        ]
from rest_framework import serializers
from apps.calendarapp.models import UserRequest, Event, EventInvite, EventAlert


class UserRequestCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserRequest
        fields = ['text']
        
    def to_representation(self, instance):
        representation = super().to_representation(instance)
        representation['id'] = str(instance.id)
        representation['user'] = instance.user.username
        representation['created_at'] = instance.created_at.isoformat()
        return representation

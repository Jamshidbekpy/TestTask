from django.contrib.auth import get_user_model
from rest_framework.generics import CreateAPIView, RetrieveDestroyAPIView, ListAPIView, UpdateAPIView
from apps.calendarapp.models import AuditLog, Event
from .serializer import EventCreateSerializer, EventRetrieveDestroySerializer, EventListSerializer, EventUpdateSerializer

User = get_user_model()

# ==================== Create Event API View =====================
class EventCreateAPIView(CreateAPIView):
    """
    Yangi event yaratish uchun API view
    """
    serializer_class = EventCreateSerializer

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)
        
        AuditLog.objects.create(
        user=self.request.user,
        event=serializer.instance,  # ← EVENT QO'SHILDI
        action="create",  # 'create'
        model_name='Event',
        object_id=serializer.instance.id,
        changes={'created': True}  # Yaratilganligini ko'rsatish uchun oddiy misol
        )
        

# ==================== Retrieve Event API View or delete Event API View {id} =====================

class EventRetrieveDestroyAPIView(RetrieveDestroyAPIView):
    """
    Eventni olish yoki o'chirish uchun API view
    """
    serializer_class = EventRetrieveDestroySerializer
    queryset = Event.objects.all()

    def perform_destroy(self, instance):
        # O'chirishdan oldin audit log yaratish
        AuditLog.objects.create(
            user=self.request.user,
            event=instance,
            action="delete",
            model_name='Event',
            object_id=instance.id,
            changes={'deleted': True}  # O'chirilganligini ko'rsatish uchun oddiy misol
        )
        instance.delete()
    
# ==================== Retrieve EventList API View  =====================

class EventListAPIView(ListAPIView):
    """
    Eventni listini olish uchun API view
    """
    serializer_class = EventListSerializer
    queryset = Event.objects.all()
    
    

# ==================== Update Event API View  =====================
      
class EventUpdateAPIView(UpdateAPIView):
    """
    Eventni yangilash uchun API view
    """
    serializer_class = EventUpdateSerializer
    queryset = Event.objects.all()
    
    def perform_update(self, serializer):
        old_instance = self.get_object()
        old_data = EventRetrieveDestroySerializer(old_instance).data
        
        updated_instance = serializer.save()
        new_data = EventRetrieveDestroySerializer(updated_instance).data
        
        # O'zgarishlarni aniqlash
        changes = {}
        for field in new_data:
            if old_data[field] != new_data[field]:
                changes[field] = {
                    'old': old_data[field],
                    'new': new_data[field]
                }
        
        # Audit log yaratish
        if changes:
            AuditLog.objects.create(
                user=self.request.user,
                event=updated_instance,
                action="update",
                model_name='Event',
                object_id=updated_instance.id,
                changes=changes
            )

__all__ = ["EventCreateAPIView", "EventRetrieveDestroyAPIView", "EventListAPIView", "EventUpdateAPIView"]
import uuid
from django.db import models
from django.contrib.auth import get_user_model
from django.utils.translation import gettext_lazy as _
from apps.base.models import BaseModel

User = get_user_model()

class UserRequest(BaseModel):
    """User so'rovlari uchun model"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='requests', verbose_name=_('User'))
    text = models.TextField(verbose_name=_('Request text'))
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = _('User request')
        verbose_name_plural = _('User requests')
        
    def __str__(self):
        return f"Request by {self.user.username} at {self.text[:20]}..."
    
class Event(BaseModel):
    """
    Event model - faqat talab qilingan fieldlar
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='events', verbose_name=_('User'))
    
    # REQUIRED FIELDS (specga asosan)
    title = models.CharField(max_length=255, verbose_name=_('Title'))
    all_day = models.BooleanField(default=False, verbose_name=_('All day'))  # all_day (boolean)
    time_start = models.DateTimeField(verbose_name=_('Start time'))  # time_start (datetime)
    time_end = models.DateTimeField(verbose_name=_('End time'))  # time_end (datetime)
    
    # REPEAT (RRULE yoki preset)
    repeat = models.TextField(null=True, blank=True, verbose_name=_('Repeat'))  # RRULE string yoki preset
    
    # URL (ixtiyoriy)
    url = models.URLField(blank=True, null=True, verbose_name=_('URL'))
    
    # NOTE (text)
    note = models.TextField(blank=True, null=True, verbose_name=_('Note'))
    
    # ADDITIONAL STATUS FIELDS
    is_cancelled = models.BooleanField(default=False, verbose_name=_('Is cancelled'))
    timezone = models.CharField(max_length=50, default='Asia/Tashkent', verbose_name=_('Timezone'))
    
    
    class Meta:
        ordering = ['time_start']
        indexes = [
            models.Index(fields=['user', 'time_start']),
            models.Index(fields=['time_start', 'time_end']),
        ]
        verbose_name = _('Event')
        verbose_name_plural = _('Events')
    
    def __str__(self):
        return f"{self.title} - {self.time_start.date()}"
    
    @property
    def duration(self):
        """Event davomiyligi"""
        if self.all_day:
            return _("All day")
        return self.time_end - self.time_start
    
    def save(self, *args, **kwargs):
        # All-day event uchun vaqtni sozlash
        if self.all_day:
            self.time_start = self.time_start.replace(hour=0, minute=0, second=0, microsecond=0)
            self.time_end = self.time_end.replace(hour=23, minute=59, second=59, microsecond=999999)
        
        super().save(*args, **kwargs)


class EventInvite(BaseModel):
    """
    Eventga taklif qilingan odamlar
    invite (email ro'yxati)
    """
    STATUS_CHOICES = [
        ('pending', _('Pending')),
        ('accepted', _('Accepted')),
        ('declined', _('Declined')),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name='invites', verbose_name=_('Event'))
    email = models.EmailField(verbose_name=_('Email'))
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending', verbose_name=_('Status'))
    
    class Meta:
        unique_together = ['event', 'email']
        verbose_name = _('Event invite')
        verbose_name_plural = _('Event invites')
    
    def __str__(self):
        return f"{self.email} - {self.event.title}"


class EventAlert(BaseModel):
    """
    Eventdan oldin ogohlantirish
    alert (masalan: 10m, 1h, 1d oldin — bir nechta bo'lishi mumkin)
    """
    class AlertUnit(models.TextChoices):
        MINUTES = 'm', _('Minutes')
        HOURS = 'h', _('Hours')
        DAYS = 'd', _('Days')
        WEEKS = 'w', _('Weeks')
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name='alerts', verbose_name=_('Event'))
    value = models.IntegerField(verbose_name=_('Value'))  # 10, 1, 30
    unit = models.CharField(max_length=1, choices=AlertUnit.choices, default=AlertUnit.MINUTES, verbose_name=_('Unit'))
    
    # Status
    is_sent = models.BooleanField(default=False, verbose_name=_('Is sent'))
    sent_at = models.DateTimeField(null=True, blank=True, verbose_name=_('Sent at'))
    
    class Meta:
        verbose_name = _('Event alert')
        verbose_name_plural = _('Event alerts')
    
    def __str__(self):
        return f"{self.value}{self.unit} before - {self.event.title}"
    
    @property
    def offset_seconds(self):
        """Offset soniyalarda"""
        if self.unit == self.AlertUnit.MINUTES:
            return self.value * 60
        elif self.unit == self.AlertUnit.HOURS:
            return self.value * 3600
        elif self.unit == self.AlertUnit.DAYS:
            return self.value * 86400
        elif self.unit == self.AlertUnit.WEEKS:
            return self.value * 604800
        return 0
    
    @property
    def display_text(self):
        """Ko'rinadigan matn: '10m', '1h', '1d'"""
        return f"{self.value}{self.unit}"


class ParsedEventDraft(BaseModel):
    """
    NLP parser natijalarini vaqtincha saqlash
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='drafts', verbose_name=_('User'))
    
    # Parser natijalari
    original_text = models.TextField(verbose_name=_('Original text'))
    language = models.CharField(max_length=10, default='uz', verbose_name=_('Language'))
    intent = models.CharField(max_length=50, verbose_name=_('Intent'))
    
    # Extracted slots (faqat required fields)
    extracted_data = models.JSONField(default=dict, verbose_name=_('Extracted data'))  # {
        # 'title': '...',
        # 'all_day': False,
        # 'time_start': '...',
        # 'time_end': '...',
        # 'repeat': '...',
        # 'invite': ['email1', 'email2'],
        # 'alert': ['10m', '1h'],
        # 'url': '...',
        # 'note': '...'
    # }
    
    # Confirmation
    is_confirmed = models.BooleanField(default=False, verbose_name=_('Is confirmed'))
    confirmed_at = models.DateTimeField(null=True, blank=True, verbose_name=_('Confirmed at'))
    
    # Timestamps
    expires_at = models.DateTimeField(verbose_name=_('Expires at'))
    
    class Meta:
        verbose_name = _('Parsed event draft')
        verbose_name_plural = _('Parsed event drafts')
    
    def __str__(self):
        return f"Draft: {self.intent} - {self.created_at}"


class AuditLog(BaseModel):
    """
    Audit log
    """
    ACTIONS = [
        ('create', _('Create')),
        ('update', _('Update')),
        ('delete', _('Delete')),
        ('view', _('View')),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, verbose_name=_('User'))
    event = models.ForeignKey(Event, on_delete=models.SET_NULL, null=True, blank=True, verbose_name=_('Event'))
    
    action = models.CharField(max_length=20, choices=ACTIONS, verbose_name=_('Action'))
    model_name = models.CharField(max_length=100, verbose_name=_('Model name'))
    object_id = models.UUIDField(verbose_name=_('Object ID'))
    changes = models.JSONField(default=dict, verbose_name=_('Changes'))
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = _('Audit log')
        verbose_name_plural = _('Audit logs')
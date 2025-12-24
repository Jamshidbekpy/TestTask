from django.contrib import admin
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _
from django.urls import reverse
from .models import UserRequest,Event, EventInvite, EventAlert, ParsedEventDraft, AuditLog
from .filters import FutureEventsFilter


@admin.register(UserRequest)
class UserRequestAdmin(admin.ModelAdmin):
    list_display = ('user', 'text', 'created_at')
    search_fields = ('user__username', 'text')
    readonly_fields = ('created_at', 'updated_at')
    
@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    list_display = (
        'title', 
        'user_link', 
        'time_start', 
        'time_end', 
        'all_day_display',
        'is_cancelled_display',
        'invites_count',
        'alerts_count',
        'duration_display',
    )
    list_filter = (
        FutureEventsFilter,
        'all_day', 
        'is_cancelled', 
        'timezone', 
        'created_at',
        'time_start',
    )
    search_fields = (
        'title', 
        'note', 
        'user__username', 
        'user__email',
        'timezone',
    )
    readonly_fields = (
        'created_at', 
        'updated_at', 
        'duration_display',
        'invites_list',
        'alerts_list',
    )
    fieldsets = (
        (_('Basic Information'), {
            'fields': ('user', 'title', 'timezone')
        }),
        (_('Time Information'), {
            'fields': ('all_day', 'time_start', 'time_end', 'duration_display')
        }),
        (_('Additional Information'), {
            'fields': ('repeat', 'url', 'note')
        }),
        (_('Status'), {
            'fields': ('is_cancelled',)
        }),
        (_('Related Objects'), {
            'fields': ('invites_list', 'alerts_list'),
            'classes': ('collapse',)
        }),
        (_('Timestamps'), {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    date_hierarchy = 'time_start'
    ordering = ('-time_start',)
    list_per_page = 25
    actions = ['mark_as_cancelled', 'mark_as_active']
    
    def user_link(self, obj):
        url = reverse("admin:auth_user_change", args=[obj.user.id])
        return format_html('<a href="{}">{}</a>', url, obj.user.username)
    user_link.short_description = _('User')
    user_link.admin_order_field = 'user__username'
    
    def all_day_display(self, obj):
        if obj.all_day:
            return format_html('<span style="color: green;">✓</span>')
        return format_html('<span style="color: gray;">✗</span>')
    all_day_display.short_description = _('All Day')
    
    def is_cancelled_display(self, obj):
        if obj.is_cancelled:
            return format_html(
                '<span style="color: red; font-weight: bold;">{}</span>', 
                _('Cancelled')
            )
        return format_html(
            '<span style="color: green;">{}</span>', 
            _('Active')
        )
    is_cancelled_display.short_description = _('Status')
    
    def duration_display(self, obj):
        return obj.duration
    duration_display.short_description = _('Duration')
    
    def invites_count(self, obj):
        count = obj.invites.count()
        url = reverse("admin:events_eventinvite_changelist") + f"?event__id__exact={obj.id}"
        return format_html('<a href="{}">{}</a>', url, count)
    invites_count.short_description = _('Invites')
    
    def alerts_count(self, obj):
        count = obj.alerts.count()
        url = reverse("admin:events_eventalert_changelist") + f"?event__id__exact={obj.id}"
        return format_html('<a href="{}">{}</a>', url, count)
    alerts_count.short_description = _('Alerts')
    
    def invites_list(self, obj):
        invites = obj.invites.all()
        if not invites:
            return _("No invites")
        
        html = '<ul>'
        for invite in invites:
            status_color = {
                'pending': 'orange',
                'accepted': 'green',
                'declined': 'red'
            }.get(invite.status, 'gray')
            
            html += f'<li>{invite.email} - <span style="color: {status_color};">{invite.get_status_display()}</span></li>'
        html += '</ul>'
        return format_html(html)
    invites_list.short_description = _('Invitation List')
    
    def alerts_list(self, obj):
        alerts = obj.alerts.all()
        if not alerts:
            return _("No alerts")
        
        html = '<ul>'
        for alert in alerts:
            sent_icon = '✓' if alert.is_sent else '✗'
            color = 'green' if alert.is_sent else 'orange'
            html += f'<li>{alert.display_text} - <span style="color: {color};">{sent_icon}</span></li>'
        html += '</ul>'
        return format_html(html)
    alerts_list.short_description = _('Alert List')
    
    def mark_as_cancelled(self, request, queryset):
        updated = queryset.update(is_cancelled=True)
        self.message_user(request, _('%(count)d events marked as cancelled') % {'count': updated})
    mark_as_cancelled.short_description = _('Mark selected events as cancelled')
    
    def mark_as_active(self, request, queryset):
        updated = queryset.update(is_cancelled=False)
        self.message_user(request, _('%(count)d events marked as active') % {'count': updated})
    mark_as_active.short_description = _('Mark selected events as active')


@admin.register(EventInvite)
class EventInviteAdmin(admin.ModelAdmin):
    list_display = (
        'email', 
        'event_link', 
        'status_display', 
        'created_at',
    )
    list_filter = (
        'status', 
        'created_at',
        'event__user',
    )
    search_fields = (
        'email', 
        'event__title',
        'event__user__username',
    )
    readonly_fields = ('created_at', 'updated_at')
    autocomplete_fields = ('event',)
    list_per_page = 50
    actions = ['mark_as_accepted', 'mark_as_declined', 'mark_as_pending']
    
    def event_link(self, obj):
        url = reverse("admin:events_event_change", args=[obj.event.id])
        return format_html('<a href="{}">{}</a>', url, obj.event.title)
    event_link.short_description = _('Event')
    event_link.admin_order_field = 'event__title'
    
    def status_display(self, obj):
        colors = {
            'pending': 'orange',
            'accepted': 'green',
            'declined': 'red'
        }
        color = colors.get(obj.status, 'gray')
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color, obj.get_status_display()
        )
    status_display.short_description = _('Status')
    
    def mark_as_accepted(self, request, queryset):
        updated = queryset.update(status='accepted')
        self.message_user(request, _('%(count)d invites marked as accepted') % {'count': updated})
    mark_as_accepted.short_description = _('Mark selected as accepted')
    
    def mark_as_declined(self, request, queryset):
        updated = queryset.update(status='declined')
        self.message_user(request, _('%(count)d invites marked as declined') % {'count': updated})
    mark_as_declined.short_description = _('Mark selected as declined')
    
    def mark_as_pending(self, request, queryset):
        updated = queryset.update(status='pending')
        self.message_user(request, _('%(count)d invites marked as pending') % {'count': updated})
    mark_as_pending.short_description = _('Mark selected as pending')


@admin.register(EventAlert)
class EventAlertAdmin(admin.ModelAdmin):
    list_display = (
        'display_text', 
        'event_link', 
        'is_sent_display',
        'sent_at',
        'offset_display',
    )
    list_filter = (
        'is_sent', 
        'unit',
        'sent_at',
        'event__user',
    )
    search_fields = (
        'event__title',
        'event__user__username',
    )
    readonly_fields = (
        'created_at', 
        'updated_at', 
        'offset_display',
        'display_text',
    )
    autocomplete_fields = ('event',)
    list_per_page = 50
    actions = ['mark_as_sent', 'mark_as_unsent']
    
    def event_link(self, obj):
        url = reverse("admin:events_event_change", args=[obj.event.id])
        return format_html('<a href="{}">{}</a>', url, obj.event.title)
    event_link.short_description = _('Event')
    event_link.admin_order_field = 'event__title'
    
    def is_sent_display(self, obj):
        if obj.is_sent:
            return format_html('<span style="color: green;">✓ {}</span>', _('Sent'))
        return format_html('<span style="color: orange;">✗ {}</span>', _('Not sent'))
    is_sent_display.short_description = _('Status')
    
    def offset_display(self, obj):
        return f"{obj.offset_seconds} {_('seconds')}"
    offset_display.short_description = _('Offset in seconds')
    
    def mark_as_sent(self, request, queryset):
        import datetime
        from django.utils import timezone
        updated = queryset.update(is_sent=True, sent_at=timezone.now())
        self.message_user(request, _('%(count)d alerts marked as sent') % {'count': updated})
    mark_as_sent.short_description = _('Mark selected as sent')
    
    def mark_as_unsent(self, request, queryset):
        updated = queryset.update(is_sent=False, sent_at=None)
        self.message_user(request, _('%(count)d alerts marked as unsent') % {'count': updated})
    mark_as_unsent.short_description = _('Mark selected as unsent')


@admin.register(ParsedEventDraft)
class ParsedEventDraftAdmin(admin.ModelAdmin):
    list_display = (
        'truncated_intent', 
        'user_link', 
        'language_display',
        'is_confirmed_display',
        'created_at',
        'expires_at',
    )
    list_filter = (
        'is_confirmed', 
        'language', 
        'intent',
        'created_at',
        'expires_at',
    )
    search_fields = (
        'original_text', 
        'intent',
        'user__username',
        'extracted_data',
    )
    readonly_fields = (
        'created_at', 
        'updated_at', 
        'confirmed_at',
        'extracted_data_prettified',
    )
    fieldsets = (
        (_('Basic Information'), {
            'fields': ('user', 'original_text', 'language', 'intent')
        }),
        (_('Extracted Data'), {
            'fields': ('extracted_data_prettified',),
            'classes': ('collapse', 'wide')
        }),
        (_('Confirmation'), {
            'fields': ('is_confirmed', 'confirmed_at')
        }),
        (_('Timestamps'), {
            'fields': ('created_at', 'updated_at', 'expires_at'),
            'classes': ('collapse',)
        }),
    )
    list_per_page = 25
    actions = ['mark_as_confirmed', 'mark_as_unconfirmed']
    
    def user_link(self, obj):
        if obj.user:
            url = reverse("admin:auth_user_change", args=[obj.user.id])
            return format_html('<a href="{}">{}</a>', url, obj.user.username)
        return '-'
    user_link.short_description = _('User')
    
    def truncated_intent(self, obj):
        if len(obj.intent) > 30:
            return f"{obj.intent[:30]}..."
        return obj.intent
    truncated_intent.short_description = _('Intent')
    
    def language_display(self, obj):
        flags = {
            'uz': '🇺🇿',
            'en': '🇺🇸',
            'ru': '🇷🇺',
        }
        flag = flags.get(obj.language, '🌐')
        return f"{flag} {obj.language.upper()}"
    language_display.short_description = _('Language')
    
    def is_confirmed_display(self, obj):
        if obj.is_confirmed:
            return format_html('<span style="color: green;">✓ {}</span>', _('Confirmed'))
        return format_html('<span style="color: orange;">✗ {}</span>', _('Not confirmed'))
    is_confirmed_display.short_description = _('Confirmed')
    
    def extracted_data_prettified(self, obj):
        import json
        try:
            data = json.dumps(obj.extracted_data, indent=2, ensure_ascii=False)
            return format_html('<pre style="background: #f5f5f5; padding: 10px; border-radius: 5px;">{}</pre>', data)
        except:
            return str(obj.extracted_data)
    extracted_data_prettified.short_description = _('Extracted Data (Pretty)')
    
    def mark_as_confirmed(self, request, queryset):
        import datetime
        from django.utils import timezone
        updated = queryset.update(is_confirmed=True, confirmed_at=timezone.now())
        self.message_user(request, _('%(count)d drafts marked as confirmed') % {'count': updated})
    mark_as_confirmed.short_description = _('Mark selected as confirmed')
    
    def mark_as_unconfirmed(self, request, queryset):
        updated = queryset.update(is_confirmed=False, confirmed_at=None)
        self.message_user(request, _('%(count)d drafts marked as unconfirmed') % {'count': updated})
    mark_as_unconfirmed.short_description = _('Mark selected as unconfirmed')


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = (
        'action_display', 
        'model_name', 
        'user_link',
        'event_link',
        'created_at',
    )
    list_filter = (
        'action', 
        'model_name',
        'created_at',
    )
    search_fields = (
        'user__username',
        'event__title',
        'model_name',
        'object_id',
    )
    readonly_fields = (
        'created_at', 
        'updated_at',
        'changes_prettified',
        'object_link',
    )
    fieldsets = (
        (_('Basic Information'), {
            'fields': ('user', 'event', 'action', 'model_name', 'object_id', 'object_link')
        }),
        (_('Changes'), {
            'fields': ('changes_prettified',),
            'classes': ('collapse', 'wide')
        }),
        (_('Timestamps'), {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    date_hierarchy = 'created_at'
    list_per_page = 50
    
    def user_link(self, obj):
        if obj.user:
            url = reverse("admin:auth_user_change", args=[obj.user.id])
            return format_html('<a href="{}">{}</a>', url, obj.user.username)
        return '-'
    user_link.short_description = _('User')
    
    def event_link(self, obj):
        if obj.event:
            url = reverse("admin:events_event_change", args=[obj.event.id])
            return format_html('<a href="{}">{}</a>', url, obj.event.title)
        return '-'
    event_link.short_description = _('Event')
    
    def action_display(self, obj):
        colors = {
            'create': 'green',
            'update': 'blue',
            'delete': 'red',
            'view': 'gray'
        }
        color = colors.get(obj.action, 'black')
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color, obj.get_action_display()
        )
    action_display.short_description = _('Action')
    
    def changes_prettified(self, obj):
        import json
        try:
            data = json.dumps(obj.changes, indent=2, ensure_ascii=False)
            return format_html('<pre style="background: #f5f5f5; padding: 10px; border-radius: 5px;">{}</pre>', data)
        except:
            return str(obj.changes)
    changes_prettified.short_description = _('Changes (Pretty)')
    
    def object_link(self, obj):
        """Dynamically create link to the changed object"""
        try:
            # Import all models from your app
            from django.apps import apps
            model_class = apps.get_model('events', obj.model_name.lower())
            
            # Try to get the object
            model_obj = model_class.objects.filter(pk=obj.object_id).first()
            if model_obj:
                app_label = model_obj._meta.app_label
                model_name = model_obj._meta.model_name
                url = reverse(f"admin:{app_label}_{model_name}_change", args=[obj.object_id])
                return format_html('<a href="{}">{}</a>', url, str(model_obj))
        except:
            pass
        return format_html('<code>{}</code>', obj.object_id)
    object_link.short_description = _('Object Link')
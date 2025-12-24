from django.contrib import admin
from django.utils.translation import gettext_lazy as _

class FutureEventsFilter(admin.SimpleListFilter):
    title = _('Time period')
    parameter_name = 'time_period'
    
    def lookups(self, request, model_admin):
        return (
            ('future', _('Future events')),
            ('past', _('Past events')),
            ('today', _('Today')),
        )
    
    def queryset(self, request, queryset):
        from django.utils import timezone
        now = timezone.now()
        
        if self.value() == 'future':
            return queryset.filter(time_start__gt=now)
        if self.value() == 'past':
            return queryset.filter(time_end__lt=now)
        if self.value() == 'today':
            return queryset.filter(
                time_start__date=now.date(),
                time_end__date=now.date()
            )
        return queryset
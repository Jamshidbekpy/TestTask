from django.apps import AppConfig


class CalendarappConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.calendarapp'
    
    def ready(self):
        import apps.calendarapp.signals # noqa

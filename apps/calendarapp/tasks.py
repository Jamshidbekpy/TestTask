# apps/calendar/tasks.py
from celery import shared_task
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.conf import settings
from django.utils import timezone
from datetime import datetime
import logging
from .models import EventAlert, EventInvite, Event

logger = logging.getLogger(__name__)

@shared_task
def send_event_alert(alert_id):
    """Alert vaqtida email yuborish"""
    try:
        alert = EventAlert.objects.get(id=alert_id, is_sent=False)
        
        # Alert yuborilganini belgilash
        alert.is_sent = True
        alert.sent_at = timezone.now()
        alert.save()
        
        # Barcha participantlarga email
        recipients = [alert.event.user.email]  # Event owner
        
        # Accepted invite lar
        accepted_emails = alert.event.invites.filter(
            status='accepted'
        ).values_list('email', flat=True)
        recipients.extend(accepted_emails)
        
        subject = f"⏰ Esdalik: {alert.event.title} {alert.value}{alert.unit} dan keyin boshlanadi"
        
        context = {
            'event': alert.event,
            'alert': alert,
            'time_left': f"{alert.value}{alert.unit}",
        }
        
        html_message = render_to_string('emails/event_reminder.html', context)
        plain_message = render_to_string('emails/event_reminder.txt', context)
        
        for recipient in set(recipients):
            send_mail(
                subject=subject,
                message=plain_message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[recipient],
                html_message=html_message,
                fail_silently=False,
            )
        
        logger.info(f"✅ Alert sent for event {alert.event.title} to {len(recipients)} recipients")
        
        return True
        
    except EventAlert.DoesNotExist:
        logger.error(f"❌ Alert not found: {alert_id}")
        return False
    except Exception as e:
        logger.error(f"❌ Failed to send alert: {e}")
        return False

@shared_task
def clean_expired_drafts():
    """Muddati o'tgan draft larni tozalash"""
    try:
        from .models import ParsedEventDraft
        
        expired_count = ParsedEventDraft.objects.filter(
            expires_at__lt=timezone.now(),
            is_confirmed=False
        ).delete()[0]
        
        logger.info(f"✅ Cleaned {expired_count} expired drafts")
        return expired_count
        
    except Exception as e:
        logger.error(f"❌ Failed to clean drafts: {e}")
        return 0

@shared_task
def send_daily_summary():
    """Har kuni userlarga kunlik summary yuborish"""
    try:
        from django.contrib.auth import get_user_model
        User = get_user_model()
        
        today = timezone.now().date()
        tomorrow = today + timezone.timedelta(days=1)
        
        for user in User.objects.filter(is_active=True):
            # Bugungi eventlar
            today_events = Event.objects.filter(
                user=user,
                time_start__date=today,
                is_cancelled=False
            ).order_by('time_start')
            
            # Ertangi eventlar
            tomorrow_events = Event.objects.filter(
                user=user,
                time_start__date=tomorrow,
                is_cancelled=False
            ).order_by('time_start')
            
            if today_events.exists() or tomorrow_events.exists():
                subject = f"📅 Kunlik uchrashuvlar xulosasi - {today}"
                
                context = {
                    'user': user,
                    'today': today,
                    'tomorrow': tomorrow,
                    'today_events': today_events,
                    'tomorrow_events': tomorrow_events,
                }
                
                html_message = render_to_string('emails/daily_summary.html', context)
                plain_message = render_to_string('emails/daily_summary.txt', context)
                
                send_mail(
                    subject=subject,
                    message=plain_message,
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[user.email],
                    html_message=html_message,
                    fail_silently=False,
                )
        
        logger.info("✅ Daily summaries sent")
        return True
        
    except Exception as e:
        logger.error(f"❌ Failed to send daily summaries: {e}")
        return False
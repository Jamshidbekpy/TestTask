# apps/calendar/signals.py
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.conf import settings
from django.utils import timezone
from datetime import timedelta
import logging
from .models import Event, EventInvite, EventAlert, AuditLog, UserRequest, ParsedEventDraft

logger = logging.getLogger(__name__)

# ==================== AUDIT LOG SIGNALS ====================

@receiver(post_save, sender=UserRequest)
def log_user_request_created(sender, instance, created, **kwargs):
    """UserRequest yaratilganda audit log"""
    if created:
        AuditLog.objects.create(
            user=instance.user,
            action='create',
            model_name='UserRequest',
            object_id=instance.id,
            changes={'text': [None, instance.text]}
        )

@receiver(post_save, sender=ParsedEventDraft)
def log_draft_created(sender, instance, created, **kwargs):
    """Draft yaratilganda audit log"""
    if created:
        AuditLog.objects.create(
            user=instance.user,
            action='create',
            model_name='ParsedEventDraft',
            object_id=instance.id,
            changes={'intent': [None, instance.intent]}
        )

@receiver(post_save, sender=Event)
def log_event_created(sender, instance, created, **kwargs):
    """Event yaratilganda audit log"""
    if created:
        AuditLog.objects.create(
            user=instance.user,
            event=instance,
            action='create',
            model_name='Event',
            object_id=instance.id,
            changes={
                'title': [None, instance.title],
                'time_start': [None, instance.time_start.isoformat()],
                'time_end': [None, instance.time_end.isoformat()]
            }
        )

# ==================== INVITE SIGNALS ====================

@receiver(post_save, sender=EventInvite)
def send_invite_email(sender, instance, created, **kwargs):
    """Yangi invite yaratilganda email yuborish"""
    if created and instance.status == 'pending':
        try:
            # Email content
            subject = f"📅 {instance.event.user.username} sizni '{instance.event.title}' ga taklif qildi"
            
            context = {
                'event': instance.event,
                'invite': instance,
                'inviter': instance.event.user,
                'accept_url': f"{settings.FRONTEND_URL}/invites/{instance.id}/accept",
                'decline_url': f"{settings.FRONTEND_URL}/invites/{instance.id}/decline",
                'tentative_url': f"{settings.FRONTEND_URL}/invites/{instance.id}/tentative",
            }
            
            html_message = render_to_string('emails/event_invite.html', context)
            plain_message = render_to_string('emails/event_invite.txt', context)
            
            send_mail(
                subject=subject,
                message=plain_message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[instance.email],
                html_message=html_message,
                fail_silently=False,
            )
            
            logger.info(f"✅ Invite email sent to {instance.email} for event {instance.event.title}")
            
            # Audit log
            AuditLog.objects.create(
                user=instance.event.user,
                event=instance.event,
                action='invite',
                model_name='EventInvite',
                object_id=instance.id,
                changes={'email_sent': [False, True]}
            )
            
        except Exception as e:
            logger.error(f"❌ Failed to send invite email: {e}")

@receiver(post_save, sender=EventInvite)
def notify_invite_status_change(sender, instance, **kwargs):
    """Invite statusi o'zgarganda event owner ga xabar berish"""
    if instance.pk:  # Faqat update holatida
        try:
            old_instance = EventInvite.objects.get(pk=instance.pk)
            if old_instance.status != instance.status and instance.status != 'pending':
                # Event owner ga email
                subject = f"✅ {instance.email} sizning taklifingizni {instance.status} qildi"
                
                context = {
                    'event': instance.event,
                    'invite': instance,
                    'invitee_email': instance.email,
                    'status': instance.status,
                }
                
                html_message = render_to_string('emails/invite_response.html', context)
                plain_message = render_to_string('emails/invite_response.txt', context)
                
                send_mail(
                    subject=subject,
                    message=plain_message,
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[instance.event.user.email],
                    html_message=html_message,
                    fail_silently=False,
                )
                
                logger.info(f"✅ Status change email sent to {instance.event.user.email}")
                
        except EventInvite.DoesNotExist:
            pass
        except Exception as e:
            logger.error(f"❌ Failed to send status email: {e}")

# ==================== ALERT SIGNALS ====================

@receiver(post_save, sender=EventAlert)
def schedule_alert_task(sender, instance, created, **kwargs):
    """Alert yaratilganda task schedule qilish"""
    if created:
        from .tasks import send_event_alert
        
        try:
            # Alert vaqtini hisoblash
            alert_time = instance.event.time_start - timedelta(seconds=instance.offset_seconds)
            
            # Celery ga schedule qilish
            send_event_alert.apply_async(
                args=[str(instance.id)],
                eta=alert_time
            )
            
            logger.info(f"✅ Alert scheduled for {alert_time}")
            
            # Audit log
            AuditLog.objects.create(
                user=instance.event.user,
                event=instance.event,
                action='alert_scheduled',
                model_name='EventAlert',
                object_id=instance.id,
                changes={'scheduled_for': [None, alert_time.isoformat()]}
            )
            
        except Exception as e:
            logger.error(f"❌ Failed to schedule alert: {e}")

# ==================== EVENT UPDATE SIGNALS ====================

@receiver(post_save, sender=Event)
def notify_event_update(sender, instance, created, **kwargs):
    """Event o'zgarganda barcha participantlarga xabar berish"""
    if not created and instance.pk:
        try:
            old_instance = Event.objects.get(pk=instance.pk)
            
            # Qaysi fieldlar o'zgarganligini tekshirish
            changed_fields = []
            for field in ['title', 'time_start', 'time_end', 'url']:
                old_value = getattr(old_instance, field)
                new_value = getattr(instance, field)
                if old_value != new_value:
                    changed_fields.append(field)
            
            if changed_fields:
                # Barcha participantlarga email (owner va invited users)
                recipients = [instance.user.email]
                recipients.extend(instance.invites.filter(status='accepted').values_list('email', flat=True))
                
                subject = f"📝 '{instance.title}' uchrashuvi o'zgartirildi"
                
                context = {
                    'event': instance,
                    'old_event': old_instance,
                    'changed_fields': changed_fields,
                    'user': instance.user,
                }
                
                html_message = render_to_string('emails/event_updated.html', context)
                plain_message = render_to_string('emails/event_updated.txt', context)
                
                for recipient in set(recipients):
                    send_mail(
                        subject=subject,
                        message=plain_message,
                        from_email=settings.DEFAULT_FROM_EMAIL,
                        recipient_list=[recipient],
                        html_message=html_message,
                        fail_silently=False,
                    )
                
                logger.info(f"✅ Event update emails sent to {len(recipients)} recipients")
                
                # Audit log
                AuditLog.objects.create(
                    user=instance.user,
                    event=instance,
                    action='update',
                    model_name='Event',
                    object_id=instance.id,
                    changes={'fields_updated': changed_fields}
                )
                
        except Event.DoesNotExist:
            pass
        except Exception as e:
            logger.error(f"❌ Failed to send update emails: {e}")



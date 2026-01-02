from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.conf import settings
import logging
from .whatsapp_utils import send_whatsapp_notification, format_message_for_whatsapp
from django.contrib.auth.models import User

logger = logging.getLogger(__name__)

def send_booking_notification(booking, action_type, extra_context=None):
    """
    Send email notification for booking actions that require approval.
    
    Args:
        booking: Booking instance
        action_type: Type of action ('created', 'approved', 'rejected', 'deroga_requested', 'modified')
        extra_context: Additional context for email template
    """
    # Determine recipient based on action type
    if action_type == 'approved':
        # Send to the booking owner (requester) to confirm approval
        recipient_family = booking.family_group
    elif booking.pending_with:
        # Send to whoever needs to act next
        recipient_family = booking.pending_with
    else:
        return  # No action needed if nobody is pending
    
    recipient_email = settings.FAMILY_EMAILS.get(recipient_family)
    
    if not recipient_email:
        logger.warning(f"No email configured for family: {recipient_family}")
        return
    
    # Prepare context for email template
    context = {
        'booking': booking,
        'action_type': action_type,
        'app_url': settings.PRENOPINZO_BASE_URL,
        'dashboard_url': f"{settings.PRENOPINZO_BASE_URL}/",
    }
    
    if extra_context:
        context.update(extra_context)
    
    # Determine subject based on action type
    subject_map = {
        'created': f'Nuova Richiesta Prenotazione: {booking.title}',
        'approved': f'✅ Prenotazione Approvata: {booking.title}',
        'rejected': f'Richiesta Rifiutata - Correzione Necessaria: {booking.title}',
        'deroga_requested': f'URGENTE - Richiesta Modifica Prenotazione: {booking.title}',
        'modified': f'Prenotazione Modificata - Nuova Approvazione Necessaria: {booking.title}',
        'period_reduced': f'Periodo Ridotto - Notifica: {booking.title}',
    }
    
    subject = subject_map.get(action_type, f'Notifica Prenotazione: {booking.title}')
    
    # Render HTML email
    html_message = render_to_string('bookings/emails/booking_notification.html', context)
    
    try:
        send_mail(
            subject=subject,
            message='',  # Plain text version (empty for HTML-only)
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[recipient_email],
            html_message=html_message,
            fail_silently=False,
        )
        logger.info(f"Email sent to {recipient_email} for booking {booking.id} - {action_type}")
        
        # --- WhatsApp Integration ---
        try:
            # Find users in the recipient family who have WhatsApp enabled
            # Note: We import User inside function or at top. Added at top.
            recipients = User.objects.filter(
                profile__family_group=recipient_family,
                profile__whatsapp_enabled=True
            )
            
            if recipients.exists():
                # Prepare WhatsApp message
                # We need a summary text. The 'extra_context' might have it, or we deduce it.
                # Actually, subject is a good summary header.
                wa_context = context.copy()
                wa_context['summary'] = subject # Use subject as summary for now
                wa_message = format_message_for_whatsapp(subject, wa_context)
                
                for user in recipients:
                    profile = user.profile
                    if profile.phone and profile.callmebot_apikey:
                        success = send_whatsapp_notification(profile.phone, wa_message, profile.callmebot_apikey)
                        if success:
                            logger.info(f"WhatsApp sent to {user.username} ({profile.phone})")
                        else:
                            logger.warning(f"Failed to send WhatsApp to {user.username}")
        except Exception as e:
            logger.error(f"Error in WhatsApp dispatch: {str(e)}")
            
    except Exception as e:
        logger.error(f"Failed to send email to {recipient_email}: {str(e)}")

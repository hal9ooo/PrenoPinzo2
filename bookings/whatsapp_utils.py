import requests
import urllib.parse
from django.conf import settings
import logging

logger = logging.getLogger(__name__)

def send_whatsapp_notification(phone_number, message_text, api_key=None):
    """
    Invia una notifica WhatsApp tramite CallMeBot.
    
    Args:
        phone_number (str): Numero formato internazionale (es. +393331234567)
        message_text (str): Il testo del messaggio (NO HTML).
        api_key (str): La chiave API personale dell'utente per CallMeBot.
    """
    
    if not api_key:
        return False

    # 1. Pulizia e Encoding del messaggio
    encoded_message = urllib.parse.quote(message_text)
    
    # 2. Costruzione URL
    url = f"https://api.callmebot.com/whatsapp.php?phone={phone_number}&text={encoded_message}&apikey={api_key}"
    
    try:
        # Timeout breve per non bloccare il thread Django se CallMeBot è lento
        response = requests.get(url, timeout=10)
        
        if response.status_code == 200:
            logger.info(f"WhatsApp inviato a {phone_number}")
            return True
        else:
            logger.error(f"Errore CallMeBot: {response.status_code} - {response.text}")
            return False
            
    except requests.exceptions.RequestException as e:
        logger.error(f"Eccezione invio WhatsApp: {str(e)}")
        return False

def format_message_for_whatsapp(subject, context_data):
    """
    Format generic notification data into WhatsApp text.
    """
    summary = context_data.get('summary', 'Aggiornamento prenotazione')
    booking_title = context_data.get('booking', {}).title if hasattr(context_data.get('booking'), 'title') else 'Prenotazione'
    action_url = context_data.get('action_url', settings.PRENOPINZO_BASE_URL)
    
    # Simple mapping
    # bold -> *text*
    # italic -> _text_
    # newline -> handled by encoded_message implicitly? No, need actual newlines which quoted handle.
    
    message = (
        f"🔔 *{subject}*\n\n"
        f"Oggetto: {booking_title}\n"
        f"👉 {summary}\n\n"
        f"🔗 Dettagli: {action_url}"
    )
    return message

from django.core.management.base import BaseCommand
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.conf import settings
from bookings.models import Booking

class Command(BaseCommand):
    help = 'Check for pending bookings and notify families via email (weekly)'

    def handle(self, *args, **kwargs):
        # Find all bookings that are pending
        pending_bookings = Booking.objects.exclude(pending_with__isnull=True).exclude(pending_with='')
        
        if not pending_bookings.exists():
            self.stdout.write(self.style.SUCCESS('No pending bookings found'))
            return

        # Group by family who needs to Act
        pending_map = {
            'Andrea': [],
            'Fabrizio': []
        }

        for booking in pending_bookings:
            if booking.pending_with in pending_map:
                pending_map[booking.pending_with].append(booking)

        # Send notifications
        for family, bookings in pending_map.items():
            if not bookings:
                continue
                
            count = len(bookings)
            recipient_email = settings.FAMILY_EMAILS.get(family)
            if not recipient_email:
                self.stdout.write(self.style.WARNING(f'No email for family {family}'))
                continue
                
            subject = f"Promemoria Settimanale: {count} Prenotazioni in Attesa - PrenoPinzo"
            
            html_message = render_to_string('emails/pending_bookings_email.html', {
                'family_name': family,
                'count': count,
                'bookings': bookings,
                'app_url': settings.PRENOPINZO_BASE_URL,
            })
            
            try:
                send_mail(
                    subject,
                    "", 
                    settings.DEFAULT_FROM_EMAIL,
                    [recipient_email],
                    html_message=html_message,
                    fail_silently=False,
                )
                self.stdout.write(self.style.SUCCESS(f'Sent weekly reminder to {family} with {count} pending bookings'))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'Failed to send email to {recipient_email}: {str(e)}'))

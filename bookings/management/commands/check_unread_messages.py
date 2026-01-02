from django.core.management.base import BaseCommand
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.conf import settings
from bookings.models import ChatMessage, UserProfile
from django.contrib.auth.models import User
from collections import defaultdict

import json
import os

class Command(BaseCommand):
    help = 'Check for unread chat messages and notify recipients via email'

    def handle(self, *args, **kwargs):
        # Path to persistent state file
        state_file = settings.BASE_DIR / 'data' / 'notification_state.json'
        
        # Load previous state
        previous_state = {}
        if state_file.exists():
            try:
                with open(state_file, 'r') as f:
                    previous_state = json.load(f)
            except Exception as e:
                self.stdout.write(self.style.WARNING(f'Failed to load state file: {e}'))

        unread_messages = ChatMessage.objects.filter(is_read=False)
        
        if not unread_messages.exists():
            self.stdout.write(self.style.SUCCESS('No unread messages found'))
            # Clear state if no messages exist
            if previous_state:
                try:
                    with open(state_file, 'w') as f:
                        json.dump({}, f)
                except:
                    pass
            return

        # Group unread messages by sender family
        messages_by_family = defaultdict(list)
        current_state = {}

        for msg in unread_messages:
            sender_family = msg.sender.profile.family_group
            messages_by_family[sender_family].append(msg)
            
            # Update current state
            if sender_family not in current_state:
                current_state[sender_family] = []
            current_state[sender_family].append(msg.id)

        # Send notifications
        messages_sent = False
        for family, messages in messages_by_family.items():
            current_ids = set(m.id for m in messages)
            previous_ids = set(previous_state.get(family, []))
            
            # Only notify if there are NEW unread messages since last check
            new_ids = current_ids - previous_ids
            
            if not new_ids:
                self.stdout.write(f'Skipping notification for {family}: No new unread messages (Existing: {len(current_ids)})')
                continue

            count = len(messages) # Total unread count (we report total, but trigger only on new)
            
            # If sender is Andrea -> Notify Fabrizio
            if family == 'Andrea':
                recipient_email = settings.FAMILY_EMAILS.get('Fabrizio')
                recipient_name = "Famiglia Fabrizio"
                sender_name = "Famiglia Andrea"
            # If sender is Fabrizio -> Notify Andrea
            elif family == 'Fabrizio':
                recipient_email = settings.FAMILY_EMAILS.get('Andrea')
                recipient_name = "Famiglia Andrea"
                sender_name = "Famiglia Fabrizio"
            else:
                self.stdout.write(self.style.WARNING(f"Unknown family group: {family}"))
                continue

            subject = render_to_string('emails/chat_notification_subject.txt', {'sender_name': sender_name})
            # Remove newlines from subject
            subject = ''.join(subject.splitlines())
            
            html_message = render_to_string('emails/chat_notification_email.html', {
                'recipient_name': recipient_name,
                'sender_name': sender_name,
                'count': count,
                'app_url': settings.PRENOPINZO_BASE_URL,
            })
            
            try:
                send_mail(
                    subject,
                    "", # Plain text message is empty as we use html_message
                    settings.DEFAULT_FROM_EMAIL,
                    [recipient_email],
                    html_message=html_message,
                    fail_silently=False,
                )
                self.stdout.write(self.style.SUCCESS(f'Sent notification to {recipient_name} regarding {count} unread messages from {sender_name}'))
                messages_sent = True
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'Failed to send email to {recipient_email}: {str(e)}'))

        # Save new state
        try:
            with open(state_file, 'w') as f:
                json.dump(current_state, f)
            self.stdout.write(self.style.SUCCESS('Successfully updated notification state'))
        except Exception as e:
             self.stdout.write(self.style.ERROR(f'Failed to save state file: {e}'))

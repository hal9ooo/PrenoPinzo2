from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.conf import settings
import os
import logging

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Syncs user email addresses from environment variables to the database'

    def handle(self, *args, **options):
        # Map usernames to environment variable keys
        user_mapping = {
            'andrea': 'EMAIL_ANDREA',
            'fabrizio': 'EMAIL_FABRIZIO'
        }

        updated_count = 0
        
        for username, env_key in user_mapping.items():
            email = os.environ.get(env_key)
            
            if not email:
                self.stdout.write(self.style.WARNING(f"Environment variable {env_key} not set. Skipping user {username}."))
                continue

            try:
                user = User.objects.get(username=username)
                
                if user.email != email:
                    old_email = user.email
                    user.email = email
                    user.save()
                    updated_count += 1
                    msg = f"Updated email for user '{username}': {old_email} -> {email}"
                    self.stdout.write(self.style.SUCCESS(msg))
                    logger.info(msg)
                else:
                    self.stdout.write(f"Email for user '{username}' is already up to date ({email})")
                    
            except User.DoesNotExist:
                self.stdout.write(self.style.ERROR(f"User '{username}' does not exist in database"))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"Error updating user '{username}': {str(e)}"))

        if updated_count > 0:
            self.stdout.write(self.style.SUCCESS(f"Successfully updated {updated_count} user emails."))
        else:
            self.stdout.write("No changes needed.")

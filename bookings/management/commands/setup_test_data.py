from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from bookings.models import UserProfile
import secrets

class Command(BaseCommand):
    help = 'Creates test users and profiles'

    def handle(self, *args, **kwargs):
        # Create Andrea
        if not User.objects.filter(username='andrea').exists():
            password = secrets.token_urlsafe(8)
            u1 = User.objects.create_user('andrea', 'andrea@example.com', password)
            UserProfile.objects.create(user=u1, family_group='Andrea')
            self.stdout.write(self.style.SUCCESS(f'User "andrea" created with password: {password}'))
        else:
            self.stdout.write('User "andrea" already exists')

        # Create Fabrizio
        if not User.objects.filter(username='fabrizio').exists():
            password = secrets.token_urlsafe(8)
            u2 = User.objects.create_user('fabrizio', 'fabrizio@example.com', password)
            UserProfile.objects.create(user=u2, family_group='Fabrizio')
            self.stdout.write(self.style.SUCCESS(f'User "fabrizio" created with password: {password}'))
        else:
            self.stdout.write('User "fabrizio" already exists')


"""
Management command to reset the database for testing.
Deletes all bookings, messages, and audit logs, then recreates test users.
"""
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from bookings.models import Booking, BookingAudit, ChatMessage, UserProfile
import secrets


class Command(BaseCommand):
    help = 'Reset database: delete all data and recreate test users'

    def add_arguments(self, parser):
        parser.add_argument(
            '--yes',
            action='store_true',
            help='Skip confirmation prompt',
        )

    def handle(self, *args, **options):
        if not options['yes']:
            confirm = input(
                '\n⚠️  ATTENZIONE: Questo cancellerà TUTTI i dati!\n'
                '   - Prenotazioni\n'
                '   - Messaggi chat\n'
                '   - Storico audit\n'
                '   - Utenti\n\n'
                'Sei sicuro? (scrivi "si" per confermare): '
            )
            if confirm.lower() not in ['si', 'sì', 'yes']:
                self.stdout.write(self.style.WARNING('Operazione annullata.'))
                return

        self.stdout.write('\n🗑️  Cancellazione dati in corso...')
        
        # Delete all data
        ChatMessage.objects.all().delete()
        self.stdout.write('   ✓ Messaggi chat cancellati')
        
        BookingAudit.objects.all().delete()
        self.stdout.write('   ✓ Audit log cancellato')
        
        Booking.objects.all().delete()
        self.stdout.write('   ✓ Prenotazioni cancellate')
        
        UserProfile.objects.all().delete()
        self.stdout.write('   ✓ Profili utente cancellati')
        
        User.objects.all().delete()
        self.stdout.write('   ✓ Utenti cancellati')

        self.stdout.write('\n👤 Creazione utenti di test...')
        
        # Generate random passwords for test users
        andrea_pass = secrets.token_urlsafe(8)
        fabrizio_pass = secrets.token_urlsafe(8)
        admin_pass = secrets.token_urlsafe(8)
        
        # Create test users
        andrea = User.objects.create_user(
            username='andrea',
            email='andrea@example.com',
            password=andrea_pass,
            first_name='Andrea',
            last_name='Famiglia'
        )
        UserProfile.objects.create(user=andrea, family_group='Andrea')
        self.stdout.write(f'   ✓ Utente andrea creato (password: {andrea_pass})')
        
        fabrizio = User.objects.create_user(
            username='fabrizio',
            email='fabrizio@example.com',
            password=fabrizio_pass,
            first_name='Fabrizio',
            last_name='Famiglia'
        )
        UserProfile.objects.create(user=fabrizio, family_group='Fabrizio')
        self.stdout.write(f'   ✓ Utente fabrizio creato (password: {fabrizio_pass})')
        
        # Create admin user
        admin = User.objects.create_superuser(
            username='admin',
            email='admin@example.com',
            password=admin_pass
        )
        UserProfile.objects.create(user=admin, family_group='Andrea')
        self.stdout.write(f'   ✓ Admin admin creato (password: {admin_pass})')

        self.stdout.write(self.style.SUCCESS('\n✅ Database resettato con successo!'))
        self.stdout.write('\n📋 Utenti disponibili:')
        self.stdout.write(f'   • andrea / {andrea_pass} (Famiglia Andrea)')
        self.stdout.write(f'   • fabrizio / {fabrizio_pass} (Famiglia Fabrizio)')
        self.stdout.write(f'   • admin / {admin_pass} (Superuser)\n')


from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from bookings.models import Booking, UserProfile, OwnershipPeriod
from django.utils import timezone
from datetime import datetime, timedelta, date

class Command(BaseCommand):
    help = 'Creates realistic seed data for screenshots'

    def handle(self, *args, **options):
        self.stdout.write('Cleaning database...')
        Booking.objects.all().delete()
        OwnershipPeriod.objects.all().delete()
        User.objects.exclude(is_superuser=True).delete()
        
        self.stdout.write('Creating users...')
        andrea = User.objects.create_user('andrea', 'andrea@example.com', '_TW1fIV0tw0')
        UserProfile.objects.create(user=andrea, family_group='Andrea', phone='+393331234567')
        
        fabrizio = User.objects.create_user('fabrizio', 'fabrizio@example.com', 'e71BNqNw0T4')
        UserProfile.objects.create(user=fabrizio, family_group='Fabrizio', phone='+393339876543')

        today = date.today()
        current_year = today.year
        
        self.stdout.write('Creating Ownership Periods...')
        # Andrea: Febbraio (Inverno), Luglio (Estate)
        OwnershipPeriod.objects.create(
            family_group='Andrea',
            start_date=date(current_year, 2, 1),
            end_date=date(current_year, 2, 15),
            created_by=andrea,
            note="Settimana Bianca"
        )
        OwnershipPeriod.objects.create(
            family_group='Andrea',
            start_date=date(current_year, 7, 1),
            end_date=date(current_year, 7, 31),
            created_by=andrea,
            note="Estate 2026 - Andrea"
        )
        
        # Fabrizio: Gennaio (Capodanno/Befana), Agosto (Ferragosto)
        OwnershipPeriod.objects.create(
            family_group='Fabrizio',
            start_date=date(current_year, 1, 1),
            end_date=date(current_year, 1, 10),
            created_by=fabrizio,
            note="Vacanze Invernali"
        )
        OwnershipPeriod.objects.create(
            family_group='Fabrizio',
            start_date=date(current_year, 8, 1),
            end_date=date(current_year, 8, 31),
            created_by=fabrizio,
            note="Agosto in Montagna"
        )

        self.stdout.write('Creating Bookings...')
        
        # 1. Past Booking (Andrea)
        Booking.objects.create(
            user=andrea,
            title="Weekend Scorso",
            start_date=today - timedelta(days=10),
            end_date=today - timedelta(days=8),
            status='APPROVED',
            created_at=timezone.now() - timedelta(days=20),
            family_group='Andrea'
        )

        # 2. Upcoming Booking (Andrea) - Approved
        Booking.objects.create(
            user=andrea,
            title="Ponte Carnevale",
            start_date=date(current_year, 2, 12), # Inside ownership period
            end_date=date(current_year, 2, 14),
            status='APPROVED',
            created_at=timezone.now() - timedelta(days=2),
            family_group='Andrea'
        )

        # 3. Upcoming Booking (Fabrizio) - Approved
        Booking.objects.create(
            user=fabrizio,
            title="Pasqua 2026",
            start_date=date(current_year, 4, 3), # Easter roughly
            end_date=date(current_year, 4, 7),
            status='APPROVED',
            created_at=timezone.now() - timedelta(days=5),
            family_group='Fabrizio'
        )

        # 4. Pending Booking (Andrea asks Fabrizio)
        Booking.objects.create(
            user=andrea,
            title="Weekend Maggio",
            start_date=date(current_year, 5, 15),
            end_date=date(current_year, 5, 17),
            status='NEGOTIATION',
            pending_with='Fabrizio',
            created_at=timezone.now() - timedelta(hours=2),
            family_group='Andrea'
        )

        # 5. Deroga Request (Fabrizio asks on Andrea's ownership)
        # Booking created by Andrea first
        b_luglio = Booking.objects.create(
            user=andrea,
            title="Settimana Luglio",
            start_date=date(current_year, 7, 10),
            end_date=date(current_year, 7, 17),
            status='APPROVED',
            created_at=timezone.now() - timedelta(days=10),
            family_group='Andrea'
        )
        
        self.stdout.write('Done! Database populated with realistic data.')

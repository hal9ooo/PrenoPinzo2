from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from bookings.models import Booking
import datetime
from django.utils import timezone

class Command(BaseCommand):
    help = 'Runs a verification scenario'

    def handle(self, *args, **kwargs):
        try:
            andrea = User.objects.get(username='andrea')
            fabrizio = User.objects.get(username='fabrizio')
        except User.DoesNotExist:
            self.stdout.write(self.style.ERROR('Users not found. Run setup_test_data first.'))
            return

        # Clean up
        Booking.objects.all().delete()
        self.stdout.write('Cleaned existing bookings.')

        # 1. Andrea Create Booking
        start = timezone.now().date() + datetime.timedelta(days=10)
        end = start + datetime.timedelta(days=7)
        booking = Booking.objects.create(
            user=andrea,
            family_group='Andrea',
            title='Vacanze Test',
            start_date=start,
            end_date=end,
            status='NEGOTIATION',
            pending_with='Fabrizio' # Logic handled in view usually, manually setting here to simulate
        )
        self.stdout.write(f'1. Booking Created: {booking.status}, Pending: {booking.pending_with}')
        assert booking.status == 'NEGOTIATION'
        assert booking.pending_with == 'Fabrizio'

        # 2. Fabrizio Approve
        booking.approve(fabrizio)
        booking.refresh_from_db()
        self.stdout.write(f'2. Booking Approved: {booking.status}, Pending: {booking.pending_with}')
        assert booking.status == 'APPROVED'
        assert booking.pending_with is None

        # 3. Request Deroga (Fabrizio asks Andrea to move)
        new_start = start + datetime.timedelta(days=1)
        new_end = end + datetime.timedelta(days=1)
        booking.request_deroga(fabrizio, new_start, new_end, "Please move")
        booking.refresh_from_db()
        self.stdout.write(f'3. Deroga Requested: {booking.status}, Pending: {booking.pending_with}')
        assert booking.status == 'DEROGA'
        assert booking.pending_with == 'Andrea'
        assert booking.start_date == new_start
        assert booking.original_start_date == start

        # 4. Andrea Accept Deroga
        booking.approve(andrea)
        booking.refresh_from_db()
        self.stdout.write(f'4. Deroga Accepted: {booking.status}, Start: {booking.start_date}')
        assert booking.status == 'APPROVED'
        assert booking.start_date == new_start
        assert booking.original_start_date is None

        self.stdout.write(self.style.SUCCESS('ALL SCENARIO TESTS PASSED'))

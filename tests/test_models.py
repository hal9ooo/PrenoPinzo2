"""Test isolati del dominio prenotazioni (issue onboarding).

Nessun accesso a rete/SMTP/HA/account reali: gira sulla test DB di Django
(sqlite in-memory) con utenti creati sul momento.
"""

from datetime import date

from django.contrib.auth.models import User
from django.test import TestCase

from bookings.models import Booking, OwnershipPeriod, UserProfile


class BookingWorkflowTests(TestCase):
    def setUp(self):
        self.andrea = User.objects.create_user("andrea", password="pw")
        self.fabrizio = User.objects.create_user("fabrizio", password="pw")
        self.booking = Booking.objects.create(
            user=self.andrea,
            family_group="Andrea",
            start_date=date(2026, 8, 1),
            end_date=date(2026, 8, 10),
            title="Estate",
        )

    def test_get_other_group(self):
        self.assertEqual(self.booking.get_other_group(), "Fabrizio")
        self.booking.family_group = "Fabrizio"
        self.assertEqual(self.booking.get_other_group(), "Andrea")

    def test_approve_from_negotiation_clears_pending_and_audits(self):
        self.booking.approve(self.fabrizio)
        self.booking.refresh_from_db()
        self.assertEqual(self.booking.status, "APPROVED")
        self.assertIsNone(self.booking.pending_with)
        self.assertTrue(
            self.booking.audits.filter(action="APPROVED", performed_by=self.fabrizio).exists()
        )

    def test_reject_from_negotiation_returns_to_owner_with_note(self):
        self.booking.reject(self.fabrizio, "date occupate")
        self.booking.refresh_from_db()
        self.assertEqual(self.booking.status, "NEGOTIATION")
        self.assertEqual(self.booking.pending_with, "Andrea")
        self.assertEqual(self.booking.rejection_note, "date occupate")

    def test_request_deroga_stores_original_dates(self):
        self.booking.status = "APPROVED"
        self.booking.save()
        self.booking.request_deroga(self.andrea, date(2026, 8, 5), date(2026, 8, 15), "cambio")
        self.booking.refresh_from_db()
        self.assertEqual(self.booking.status, "DEROGA")
        self.assertEqual(self.booking.original_start_date, date(2026, 8, 1))
        self.assertEqual(self.booking.original_end_date, date(2026, 8, 10))
        self.assertEqual(self.booking.deroga_requested_by, self.andrea)
        self.assertEqual(self.booking.pending_with, "Andrea")

    def test_approve_deroga_accepts_new_dates_and_clears_original(self):
        self.booking.status = "APPROVED"
        self.booking.save()
        self.booking.request_deroga(self.andrea, date(2026, 8, 5), date(2026, 8, 15), "cambio")
        self.booking.approve(self.fabrizio)
        self.booking.refresh_from_db()
        self.assertEqual(self.booking.status, "APPROVED")
        self.assertEqual(self.booking.start_date, date(2026, 8, 5))
        self.assertIsNone(self.booking.original_start_date)
        self.assertIsNone(self.booking.deroga_requested_by)

    def test_reject_deroga_reverts_new_dates(self):
        self.booking.status = "APPROVED"
        self.booking.save()
        self.booking.request_deroga(self.andrea, date(2026, 8, 5), date(2026, 8, 15), "cambio")
        self.booking.reject(self.fabrizio, "no")
        self.booking.refresh_from_db()
        self.assertEqual(self.booking.status, "APPROVED")
        self.assertEqual(self.booking.start_date, date(2026, 8, 1))
        self.assertEqual(self.booking.end_date, date(2026, 8, 10))
        self.assertIsNone(self.booking.original_start_date)

    def test_modify_sets_negotiation_pending_other_and_clears_note(self):
        self.booking.status = "APPROVED"
        self.booking.rejection_note = "vecchia nota"
        self.booking.save()
        self.booking.modify(self.andrea, date(2026, 9, 1), date(2026, 9, 5))
        self.booking.refresh_from_db()
        self.assertEqual(self.booking.status, "NEGOTIATION")
        self.assertEqual(self.booking.pending_with, "Fabrizio")
        self.assertIsNone(self.booking.rejection_note)

    def test_cancel(self):
        self.booking.cancel(self.andrea)
        self.booking.refresh_from_db()
        self.assertEqual(self.booking.status, "CANCELLED")
        self.assertIsNone(self.booking.pending_with)
        self.assertTrue(self.booking.audits.filter(action="CANCELLED").exists())


class BookingOverlapTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user("u", password="pw")

    def _booking(self, start, end, status="APPROVED"):
        return Booking.objects.create(
            user=self.user,
            family_group="Andrea",
            start_date=start,
            end_date=end,
            title="t",
            status=status,
        )

    def test_overlap_detected(self):
        self._booking(date(2026, 8, 1), date(2026, 8, 10))
        self.assertTrue(Booking.check_overlap(date(2026, 8, 5), date(2026, 8, 15)))

    def test_touching_dates_do_not_overlap(self):
        self._booking(date(2026, 8, 1), date(2026, 8, 10))
        self.assertFalse(Booking.check_overlap(date(2026, 8, 10), date(2026, 8, 15)))

    def test_only_approved_or_deroga_count(self):
        self._booking(date(2026, 8, 1), date(2026, 8, 10), status="NEGOTIATION")
        self.assertFalse(Booking.check_overlap(date(2026, 8, 5), date(2026, 8, 15)))

    def test_exclude_id_ignores_the_same_booking(self):
        booking = self._booking(date(2026, 8, 1), date(2026, 8, 10))
        self.assertFalse(
            Booking.check_overlap(date(2026, 8, 1), date(2026, 8, 10), exclude_id=booking.id)
        )


class OwnershipPeriodTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user("u", password="pw")
        self.period = OwnershipPeriod.objects.create(
            family_group="Andrea",
            start_date=date(2026, 7, 1),
            end_date=date(2026, 9, 1),
            created_by=self.user,
        )

    def test_display(self):
        self.assertEqual(self.period.get_family_group_display(), "Famiglia Andrea")

    def test_is_within_ownership(self):
        self.assertTrue(
            OwnershipPeriod.is_within_ownership("Andrea", date(2026, 7, 10), date(2026, 8, 10))
        )
        self.assertFalse(
            OwnershipPeriod.is_within_ownership("Andrea", date(2026, 6, 10), date(2026, 8, 10))
        )

    def test_overlap_with_other_family(self):
        self.assertTrue(
            OwnershipPeriod.check_overlap_with_other_family(
                "Fabrizio", date(2026, 7, 10), date(2026, 7, 20)
            )
        )
        self.assertFalse(
            OwnershipPeriod.check_overlap_with_other_family(
                "Andrea", date(2026, 7, 10), date(2026, 7, 20)
            )
        )


class UserProfileTests(TestCase):
    def test_str_includes_username_and_family(self):
        user = User.objects.create_user("mario", password="pw")
        profile = UserProfile.objects.create(user=user, family_group="Andrea")
        self.assertIn("mario", str(profile))
        self.assertIn("Andrea", str(profile))

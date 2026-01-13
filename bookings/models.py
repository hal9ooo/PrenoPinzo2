from django.db import models
from django.contrib.auth.models import User

class UserProfile(models.Model):
    FAMILY_CHOICES = [
        ('Andrea', 'Famiglia Andrea'),
        ('Fabrizio', 'Famiglia Fabrizio'),
    ]
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    family_group = models.CharField(max_length=20, choices=FAMILY_CHOICES)
    
    # WhatsApp Notification fields
    phone = models.CharField(max_length=20, blank=True, help_text="International format (e.g. +39333...)")
    callmebot_apikey = models.CharField(max_length=50, blank=True, help_text="Get it from CallMeBot")
    whatsapp_enabled = models.BooleanField(default=False, help_text="Enable WhatsApp notifications")
    avatar = models.ImageField(upload_to='avatars/', blank=True, null=True, help_text="Immagine del profilo")

    def __str__(self):
        return f"{self.user.username} ({self.family_group})"

class Booking(models.Model):
    STATUS_CHOICES = [
        ('NEGOTIATION', 'In Negoziazione'),
        ('APPROVED', 'Approvata'),
        ('REJECTED', 'Rifiutata'),
        ('CANCELLED', 'Cancellata'),
        ('DEROGA', 'Richiesta Revisione'),
    ]
    FAMILY_CHOICES = [
        ('Andrea', 'Famiglia Andrea'),
        ('Fabrizio', 'Famiglia Fabrizio'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='bookings')
    family_group = models.CharField(max_length=20, choices=FAMILY_CHOICES)
    start_date = models.DateField()
    end_date = models.DateField()
    title = models.CharField(max_length=200)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='NEGOTIATION')
    
    # Who needs to act next?
    pending_with = models.CharField(max_length=20, choices=FAMILY_CHOICES, null=True, blank=True)
    
    rejection_note = models.TextField(blank=True, null=True)

    # Deroga (Revision) fields
    original_start_date = models.DateField(null=True, blank=True)
    original_end_date = models.DateField(null=True, blank=True)
    deroga_requested_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='deroga_requests')
    deroga_note = models.TextField(blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.title} ({self.start_date} - {self.end_date})"

    def get_other_group(self):
        if self.family_group == 'Andrea':
            return 'Fabrizio'
        return 'Andrea'

    def log_action(self, action, user, details=None):
        BookingAudit.objects.create(
            booking=self,
            action=action,
            performed_by=user,
            details=details
        )

    def approve(self, user):
        if self.status == 'NEGOTIATION':
            self.status = 'APPROVED'
            self.pending_with = None
            self.log_action('APPROVED', user)
        elif self.status == 'DEROGA':
            # Accept Deroga
            self.status = 'APPROVED'
            self.pending_with = None
            self.original_start_date = None
            self.original_end_date = None
            self.deroga_requested_by = None
            self.deroga_note = None
            self.log_action('DEROGA_ACCEPTED', user)
        self.save()

    def reject(self, user, note):
        if self.status == 'NEGOTIATION':
            # Reject negotiation -> back to owner to fix
            self.status = 'NEGOTIATION'
            self.pending_with = self.family_group # Owner
            self.rejection_note = note
            self.log_action('REJECTED', user, details=f"Note: {note}")
        elif self.status == 'DEROGA':
            # Reject Deroga -> Revert to original dates
            self.status = 'APPROVED'
            self.start_date = self.original_start_date
            self.end_date = self.original_end_date
            self.original_start_date = None
            self.original_end_date = None
            self.deroga_requested_by = None
            self.deroga_note = None
            self.pending_with = None
            self.log_action('DEROGA_REJECTED', user)
        self.save()

    def request_deroga(self, user, new_start, new_end, note):
        if self.status == 'APPROVED':
            self.original_start_date = self.start_date
            self.original_end_date = self.end_date
            self.start_date = new_start
            self.end_date = new_end
            self.status = 'DEROGA'
            self.deroga_requested_by = user
            self.deroga_note = note
            # Pending with the owner of the booking
            self.pending_with = self.family_group
            self.log_action('DEROGA_REQUESTED', user, details=f"New dates: {new_start}-{new_end}. Note: {note}")
            self.save()

    def modify(self, user, new_start, new_end):
        # Owner modifies dates
        self.start_date = new_start
        self.end_date = new_end
        self.status = 'NEGOTIATION'
        self.pending_with = self.get_other_group()
        self.rejection_note = None # Clear previous rejection
        self.log_action('MODIFIED', user, details=f"New dates: {new_start}-{new_end}")
        self.save()

    def cancel(self, user):
        # Owner cancels their booking
        self.status = 'CANCELLED'
        self.pending_with = None
        self.log_action('CANCELLED', user, details=f"Booking cancelled: {self.title}")
        self.save()

    @classmethod
    def check_overlap(cls, start_date, end_date, exclude_id=None):
        """
        Check if the given date range overlaps with any APPROVED or DEROGA booking.
        Logic: Overlap if (StartA < EndB) and (EndA > StartB).
        This allows touching dates (e.g. A ends 30th, B starts 30th) assuming
        check-out in morning and check-in in afternoon.
        """
        query = cls.objects.filter(
            status__in=['APPROVED', 'DEROGA'],
            start_date__lt=end_date,
            end_date__gt=start_date
        )
        if exclude_id:
            query = query.exclude(id=exclude_id)
        
        return query.exists()

class BookingAudit(models.Model):
    booking = models.ForeignKey(Booking, on_delete=models.CASCADE, related_name='audits')
    action = models.CharField(max_length=100)
    performed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    timestamp = models.DateTimeField(auto_now_add=True)
    details = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"{self.action} on {self.booking} by {self.performed_by}"


class OwnershipPeriod(models.Model):
    """Periodi di pertinenza: prenotazioni in questi range sono auto-approvate"""
    FAMILY_CHOICES = [
        ('Andrea', 'Famiglia Andrea'),
        ('Fabrizio', 'Famiglia Fabrizio'),
    ]
    
    family_group = models.CharField(max_length=20, choices=FAMILY_CHOICES)
    start_date = models.DateField()
    end_date = models.DateField()
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='ownership_periods')
    created_at = models.DateTimeField(auto_now_add=True)
    note = models.CharField(max_length=200, blank=True, help_text="Es. Estate 2026")

    class Meta:
        ordering = ['start_date']

    def __str__(self):
        return f"{self.family_group}: {self.start_date} - {self.end_date}"

    def get_family_group_display(self):
        return dict(self.FAMILY_CHOICES).get(self.family_group, self.family_group)

    @classmethod
    def check_overlap_with_other_family(cls, family_group, start_date, end_date, exclude_id=None):
        """
        Check if overlaps with OTHER family's periods.
        Same-day touching is allowed (start_date < end_date, not <=).
        """
        other_family = 'Fabrizio' if family_group == 'Andrea' else 'Andrea'
        query = cls.objects.filter(
            family_group=other_family,
            start_date__lt=end_date,
            end_date__gt=start_date
        )
        if exclude_id:
            query = query.exclude(id=exclude_id)
        return query.exists()
    
    @classmethod
    def is_within_ownership(cls, family_group, start_date, end_date):
        """Check if a booking period is FULLY within an ownership period of the same family"""
        return cls.objects.filter(
            family_group=family_group,
            start_date__lte=start_date,
            end_date__gte=end_date
        ).exists()


class ChatMessage(models.Model):
    """Real-time chat messages between family groups"""
    sender = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sent_messages')
    content = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)
    is_read = models.BooleanField(default=False)

    class Meta:
        ordering = ['timestamp']

    def __str__(self):
        return f"{self.sender.username}: {self.content[:50]}"

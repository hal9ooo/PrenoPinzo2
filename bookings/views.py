from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, HttpResponseForbidden
from django.views.decorators.http import require_POST
from .models import Booking, UserProfile, BookingAudit
from .forms import BookingForm, DerogaForm, RejectForm, UserProfileForm
from .email_utils import send_booking_notification
from datetime import timedelta, date
import json
import holidays

@login_required
def dashboard(request):
    try:
        user_group = request.user.profile.family_group
    except UserProfile.DoesNotExist:
        # Handle case where user has no profile (shouldn't happen in prod but useful for debug)
        return render(request, 'bookings/no_profile.html')

    # Subquery to get the approval date for each booking
    from django.db.models import Subquery, OuterRef
    approval_date_subquery = BookingAudit.objects.filter(
        booking=OuterRef('pk'),
        action='APPROVED'
    ).order_by('-timestamp').values('timestamp')[:1]

    # 1. Deroga Requests received (status=DEROGA, pending_with=ME)
    deroga_requests = Booking.objects.filter(status='DEROGA', pending_with=user_group)

    # 2. Approved Bookings (Visible: Future + Past 30 Days)
    cutoff_date = date.today() - timedelta(days=30)
    approved_bookings = Booking.objects.filter(
        status__in=['APPROVED', 'DEROGA'], 
        end_date__gte=cutoff_date
    ).annotate(
        approved_at=Subquery(approval_date_subquery)
    ).order_by('start_date')
    
    # All history for modal
    all_history_bookings = Booking.objects.filter(status__in=['APPROVED', 'DEROGA']).annotate(
        approved_at=Subquery(approval_date_subquery)
    ).order_by('-start_date')

    # 3. Requires Attention (pending with ME, status=NEGOTIATION, but NOT created by MY family)
    # This shows requests from the OTHER family that need MY approval
    requires_attention = Booking.objects.filter(
        status='NEGOTIATION', 
        pending_with=user_group
    ).exclude(family_group=user_group)

    # 4. My Requests (status=NEGOTIATION, user=ME/MyGroup) - actually spec says "Le Tue Richieste (In attesa)"
    # Usually pending with OTHER, but could be pending with ME if rejected.
    # We want requests created by create_user's group that are not finalized.
    my_requests = Booking.objects.filter(status='NEGOTIATION', family_group=user_group)

    # 5. History (Audit logs) - Last 30 entries (Card)
    audit_history = BookingAudit.objects.select_related('booking', 'performed_by').order_by('-timestamp')[:30]
    
    # 6. All Audit Logs (Modal)
    all_audit_history = BookingAudit.objects.select_related('booking', 'performed_by').order_by('-timestamp')

    # 7. Ownership Periods (±3 months for card, all for modal)
    from .models import OwnershipPeriod
    from dateutil.relativedelta import relativedelta
    
    today = date.today()
    period_start_cutoff = today - relativedelta(months=3)
    period_end_cutoff = today + relativedelta(months=3)
    
    # Recent periods (within ±3 months)
    recent_ownership_periods = OwnershipPeriod.objects.filter(
        end_date__gte=period_start_cutoff,
        start_date__lte=period_end_cutoff
    ).order_by('start_date')
    
    # All periods for modal
    all_ownership_periods = OwnershipPeriod.objects.all().order_by('start_date')

    context = {
        'deroga_requests': deroga_requests,
        'approved_bookings': approved_bookings,
        'all_history_bookings': all_history_bookings,
        'requires_attention': requires_attention,
        'my_requests': my_requests,
        'user_group': user_group,
        'audit_history': audit_history,
        'all_audit_history': all_audit_history,
        'recent_ownership_periods': recent_ownership_periods,
        'all_ownership_periods': all_ownership_periods,
    }
    return render(request, 'bookings/dashboard.html', context)

@login_required
def calendar_view(request):
    return render(request, 'bookings/calendar.html')

@login_required
def help_view(request):
    return render(request, 'bookings/help.html')


@login_required
def chat_view(request):
    """Real-time chat page"""
    return render(request, 'bookings/chat.html')


@login_required
def unread_chat_count(request):
    """API endpoint to get unread chat message count"""
    from .models import ChatMessage
    count = ChatMessage.objects.filter(is_read=False).exclude(sender=request.user).count()
    return JsonResponse({'count': count})

@login_required
def booking_events(request):
    # Returns JSON for FullCalendar
    bookings = Booking.objects.exclude(status='CANCELLED').exclude(status='REJECTED')
    events = []
    
    user_group = request.user.profile.family_group

    for b in bookings:
        color = 'gray'
        if b.status == 'APPROVED':
            if b.family_group == 'Andrea':
                color = 'green'
            else:
                color = 'blue'
        elif b.status == 'NEGOTIATION':
            # Yellow: My pending requests
            # Orange: Other pending requests
            if b.family_group == user_group:
                color = 'gold' # My requests
            else:
                color = 'orange' # Others requests
        
        events.append({
            'id': b.id,
            'title': f"{b.title} ({b.family_group})",
            'start': b.start_date.isoformat(),
            'end': (b.end_date + timedelta(days=1)).isoformat(),  # FullCalendar end is EXCLUSIVE (next day)
            'color': color,
            'extendedProps': {
                'status': b.status,
                'pending_with': b.pending_with,
                'family_group': b.family_group  # CRITICAL: needed for drag & drop permission checks
            }
        })
    return JsonResponse(events, safe=False)

@login_required
@require_POST
def create_booking(request):
    from .models import OwnershipPeriod
    
    form = BookingForm(request.POST)
    if form.is_valid():
        booking = form.save(commit=False)
        booking.user = request.user
        booking.family_group = request.user.profile.family_group
        
        # Check constraints (Server side overlap check)
        # Smart overlap check allowing touching dates
        if Booking.check_overlap(booking.start_date, booking.end_date):
             return JsonResponse({'status': 'error', 'message': 'Date sovrapposte a una prenotazione approvata!'}, status=400)

        # Check if booking is within an ownership period (auto-approve)
        if OwnershipPeriod.is_within_ownership(booking.family_group, booking.start_date, booking.end_date):
            booking.status = 'APPROVED'
            booking.pending_with = None
            booking.save()
            booking.log_action('AUTO_APPROVED', request.user, details='Periodo di pertinenza')
            return JsonResponse({'status': 'ok', 'message': 'Prenotazione auto-approvata (periodo di pertinenza).'})
        else:
            # Standard negotiation flow
            booking.pending_with = booking.get_other_group()
            booking.save()
            booking.log_action('CREATED', request.user)
            # Send email notification to the other family
            send_booking_notification(booking, 'created')
            return JsonResponse({'status': 'ok'})
    else:
        return JsonResponse({'status': 'error', 'errors': form.errors}, status=400)

@login_required
@require_POST
def approve_booking(request, booking_id):
    booking = get_object_or_404(Booking, id=booking_id)
    if booking.pending_with != request.user.profile.family_group:
        return HttpResponseForbidden("Non tocca a te approvare.")
    
    booking.approve(request.user)
    # Send confirmation email to the booking owner
    send_booking_notification(booking, 'approved')
    return JsonResponse({'status': 'ok'})


@login_required
@require_POST
def reject_booking(request, booking_id):
    booking = get_object_or_404(Booking, id=booking_id)
    if booking.pending_with != request.user.profile.family_group:
        return HttpResponseForbidden("Non tocca a te rifiutare.")
    
    note = request.POST.get('note', '')
    booking.reject(request.user, note)
    # Send email notification if pending back with owner
    if booking.pending_with == booking.family_group:
        send_booking_notification(booking, 'rejected', {'rejection_note': note})
    return JsonResponse({'status': 'ok'})

@login_required
@require_POST
def request_deroga_view(request, booking_id):
    booking = get_object_or_404(Booking, id=booking_id)
    # Only if approved
    if booking.status != 'APPROVED':
        return JsonResponse({'status': 'error', 'message': 'Booking not approved'}, status=400)
    
    form = DerogaForm(request.POST)
    if form.is_valid():
        new_start = form.cleaned_data['new_start_date']
        new_end = form.cleaned_data['new_end_date']
        note = form.cleaned_data['note']
        booking.request_deroga(request.user, new_start, new_end, note)
        # Send urgent email notification to the owner
        send_booking_notification(booking, 'deroga_requested', {'deroga_note': note})
        return JsonResponse({'status': 'ok'})
    else:
        return JsonResponse({'status': 'error', 'errors': form.errors}, status=400)

@login_required
@require_POST
def modify_booking(request, booking_id):
    booking = get_object_or_404(Booking, id=booking_id)
    if booking.user != request.user:
         return HttpResponseForbidden("Non sei il proprietario.")
    
    form = BookingForm(request.POST, instance=booking)
    if form.is_valid():
        start = form.cleaned_data['start_date']
        end = form.cleaned_data['end_date']
        
        # Check overlaps (excluding self)
        if Booking.check_overlap(start, end, exclude_id=booking.id):
             return JsonResponse({'status': 'error', 'message': 'Date sovrapposte a una prenotazione approvata!'}, status=400)

        booking.modify(request.user, start, end)
        # Send email notification to the other family for re-approval
        send_booking_notification(booking, 'modified')
        return JsonResponse({'status': 'ok'})
    return JsonResponse({'status': 'error', 'errors': form.errors}, status=400)

@login_required
@require_POST
def delete_booking(request, booking_id):
    booking = get_object_or_404(Booking, id=booking_id)
    # Only owner can delete
    if booking.user != request.user:
        return HttpResponseForbidden("Non sei il proprietario.")
    
    booking.cancel(request.user)
    return JsonResponse({'status': 'ok'})

@login_required
@require_POST
def update_booking_dates(request, booking_id):
    """Handle drag & drop updates from calendar with smart approval logic"""
    from datetime import datetime
    
    booking = get_object_or_404(Booking, id=booking_id)
    
    # Verify ownership
    if booking.user != request.user:
        return JsonResponse({'status': 'error', 'message': 'Non autorizzato'}, status=403)
    
    # Get new dates
    new_start_str = request.POST.get('start_date')
    new_end_str = request.POST.get('end_date')
    
    try:
        new_start = datetime.strptime(new_start_str, '%Y-%m-%d').date()
        new_end = datetime.strptime(new_end_str, '%Y-%m-%d').date()
    except (ValueError, TypeError):
        return JsonResponse({'status': 'error', 'message': 'Formato date non valido'}, status=400)
    
    # Store original dates for comparison
    original_start = booking.start_date
    original_end = booking.end_date
    original_status = booking.status
    
    # Check for overlaps with other approved bookings (excluding this one)
    if Booking.check_overlap(new_start, new_end, exclude_id=booking_id):
        return JsonResponse({'status': 'error', 'message': 'Sovrapposizione con altra prenotazione approvata'}, status=400)
    
    # Apply smart approval logic for APPROVED bookings
    if original_status == 'APPROVED':
        # Check if period is reduced (no re-approval needed)
        is_reduction = (new_start >= original_start and new_end <= original_end)
        
        if is_reduction:
            # Keep approved, just update dates and notify
            booking.start_date = new_start
            booking.end_date = new_end
            booking.log_action('PERIOD_REDUCED', request.user, 
                             f"Periodo ridotto da {original_start} - {original_end} a {new_start} - {new_end}")
            booking.save()
            send_booking_notification(booking, 'period_reduced', {
                'original_start': original_start,
                'original_end': original_end
            })
            return JsonResponse({'status': 'ok', 'message': 'Periodo ridotto. L\'altra famiglia è stata notificata.'})
        else:
            # Period extended - require re-approval
            booking.start_date = new_start
            booking.end_date = new_end
            booking.status = 'NEGOTIATION'
            booking.pending_with = booking.get_other_group()
            booking.log_action('PERIOD_EXTENDED', request.user,
                             f"Periodo modificato da {original_start} - {original_end} a {new_start} - {new_end}, richiede nuova approvazione")
            booking.save()
            send_booking_notification(booking, 'modified')
            return JsonResponse({'status': 'ok', 'message': 'Periodo esteso. Richiesta nuova approvazione dall\'altra famiglia.'})
    
    # For NEGOTIATION status, just update dates
    elif original_status == 'NEGOTIATION':
        booking.start_date = new_start
        booking.end_date = new_end
        booking.log_action('DATES_UPDATED', request.user,
                         f"Date aggiornate da {original_start} - {original_end} a {new_start} - {new_end}")
        booking.save()
        send_booking_notification(booking, 'modified')
        return JsonResponse({'status': 'ok', 'message': 'Date aggiornate. L\'altra famiglia è stata notificata.'})
    
    return JsonResponse({'status': 'error', 'message': 'Stato non valido per modifica drag & drop'}, status=400)


def holiday_events(request):
    """Return Italian holidays for the calendar as background events"""
    # Get year range from request params (FullCalendar sends start/end)
    start_str = request.GET.get('start', '')
    end_str = request.GET.get('end', '')
    
    try:
        # Parse years from the date range
        if start_str:
            start_year = int(start_str[:4])
        else:
            start_year = date.today().year
        
        if end_str:
            end_year = int(end_str[:4])
        else:
            end_year = start_year
    except (ValueError, IndexError):
        start_year = end_year = date.today().year
    
    # Get Italian holidays for the year range
    it_holidays = holidays.Italy(years=range(start_year, end_year + 1))
    
    events = []
    for holiday_date, holiday_name in sorted(it_holidays.items()):
        events.append({
            'title': holiday_name,
            'start': holiday_date.isoformat(),
            'end': holiday_date.isoformat(),
            'display': 'background',  # Show as background event
            'color': '#ffcccc',  # Light red background
            'textColor': '#990000',
            'allDay': True,
            'extendedProps': {
                'is_holiday': True
            }
        })
    
    return JsonResponse(events, safe=False)


def get_bridge_days_in_booking(start_date, end_date, it_holidays):
    """
    Identify bridge days (ponti) within a booking period.
    A "ponte" is a holiday that falls on:
    - Monday (ponte with preceding weekend)
    - Tuesday (super-ponte if Monday is taken off)
    - Thursday (ponte if Friday is taken off)  
    - Friday (ponte with following weekend)
    Returns a list of (holiday_date, holiday_name, bridge_type)
    """
    bridge_days = []
    current = start_date
    while current <= end_date:
        if current in it_holidays:
            weekday = current.weekday()  # 0=Monday, 6=Sunday
            bridge_type = None
            
            if weekday == 0:  # Monday - ponte with weekend before
                bridge_type = "Ponte Lunedì"
            elif weekday == 1:  # Tuesday - super-ponte
                bridge_type = "Super-Ponte Martedì"
            elif weekday == 3:  # Thursday - ponte with potential Friday off
                bridge_type = "Ponte Giovedì"
            elif weekday == 4:  # Friday - ponte with weekend after
                bridge_type = "Ponte Venerdì"
            
            if bridge_type:
                bridge_days.append({
                    'date': current,
                    'name': it_holidays[current],
                    'type': bridge_type
                })
        
        current += timedelta(days=1)
    
    return bridge_days


@login_required
def statistics_view(request):
    """Comprehensive statistics page for bookings"""
    from django.db.models import Count, Sum, Avg, Max, Min, Q
    from django.db.models.functions import ExtractYear
    from collections import defaultdict
    
    user = request.user
    user_group = user.profile.family_group
    family_groups = [choice[0] for choice in Booking.FAMILY_CHOICES]
    other_group = next((group for group in family_groups if group != user_group), None)
    current_year = date.today().year
    year_start = date(current_year, 1, 1)
    year_end = date(current_year, 12, 31)

    def iter_date_range(start, end):
        current = start
        while current <= end:
            yield current
            current += timedelta(days=1)

    def overlap_days(start, end, range_start, range_end):
        overlap_start = max(start, range_start)
        overlap_end = min(end, range_end)
        if overlap_start > overlap_end:
            return 0
        return (overlap_end - overlap_start).days + 1
    
    # Get all years with bookings for bridge calculation
    all_approved = Booking.objects.filter(status='APPROVED')
    years_with_bookings = set()
    for b in all_approved:
        years_with_bookings.add(b.start_date.year)
        years_with_bookings.add(b.end_date.year)
    years_with_bookings.add(current_year)
    
    # Load Italian holidays for all relevant years
    it_holidays = holidays.Italy(years=list(years_with_bookings) if years_with_bookings else [current_year])
    
    # ========== MY BOOKINGS STATS ==========
    my_bookings = Booking.objects.filter(family_group=user_group).exclude(status='CANCELLED')
    my_approved = my_bookings.filter(status='APPROVED')
    
    # Calculate days per booking and bridge days
    my_total_days = 0
    my_max_period = 0
    my_periods_by_year = defaultdict(lambda: {'count': 0, 'days': 0})
    
    # Bridge (Ponte) statistics
    my_total_bridges = 0
    my_bridge_details = []  # List of all bridge days in my bookings
    my_bridges_by_year = defaultdict(lambda: {'count': 0, 'bridges': []})
    my_bridges_by_type = defaultdict(int)  # Count by bridge type
    
    for b in my_approved:
        days = (b.end_date - b.start_date).days + 1
        my_total_days += days
        my_max_period = max(my_max_period, days)
        booking_start_year = b.start_date.year
        booking_end_year = b.end_date.year
        for year in range(booking_start_year, booking_end_year + 1):
            year_range_start = date(year, 1, 1)
            year_range_end = date(year, 12, 31)
            year_days = overlap_days(b.start_date, b.end_date, year_range_start, year_range_end)
            if year_days > 0:
                my_periods_by_year[year]['count'] += 1
                my_periods_by_year[year]['days'] += year_days
        
        # Calculate bridges in this booking
        bridges = get_bridge_days_in_booking(b.start_date, b.end_date, it_holidays)
        my_total_bridges += len(bridges)
        for bridge in bridges:
            bridge['booking_title'] = b.title
            my_bridge_details.append(bridge)
            bridge_year = bridge['date'].year  # Use the bridge's actual year, not booking start year
            my_bridges_by_year[bridge_year]['count'] += 1
            my_bridges_by_year[bridge_year]['bridges'].append(bridge)
            my_bridges_by_type[bridge['type']] += 1
    
    my_avg_period = my_total_days / my_approved.count() if my_approved.count() > 0 else 0
    
    # ========== OTHER FAMILY STATS ==========
    other_bookings = Booking.objects.filter(family_group=other_group).exclude(status='CANCELLED')
    other_approved = other_bookings.filter(status='APPROVED')
    
    other_total_days = 0
    other_max_period = 0
    other_total_bridges = 0
    other_bridge_details = []
    other_bridges_by_year = defaultdict(lambda: {'count': 0, 'bridges': []})
    other_bridges_by_type = defaultdict(int)
    
    for b in other_approved:
        days = (b.end_date - b.start_date).days + 1
        other_total_days += days
        other_max_period = max(other_max_period, days)
        
        # Calculate bridges in this booking
        bridges = get_bridge_days_in_booking(b.start_date, b.end_date, it_holidays)
        other_total_bridges += len(bridges)
        for bridge in bridges:
            bridge['booking_title'] = b.title
            other_bridge_details.append(bridge)
            bridge_year = bridge['date'].year  # Use the bridge's actual year, not booking start year
            other_bridges_by_year[bridge_year]['count'] += 1
            other_bridges_by_year[bridge_year]['bridges'].append(bridge)
            other_bridges_by_type[bridge['type']] += 1
    
    # ========== BRIDGE COMPARISON ==========
    total_bridges = my_total_bridges + other_total_bridges
    my_bridge_percentage = round((my_total_bridges / total_bridges * 100), 1) if total_bridges > 0 else 0
    other_bridge_percentage = round(100 - my_bridge_percentage, 1) if total_bridges > 0 else 0
    
    # Current year bridges
    my_current_year_bridges = my_bridges_by_year.get(current_year, {'count': 0})['count']
    other_current_year_bridges = other_bridges_by_year.get(current_year, {'count': 0})['count']
    
    # ========== ACTION STATS FROM AUDIT ==========
    my_audits = BookingAudit.objects.filter(performed_by=user)
    
    # Actions I performed
    my_approvals = my_audits.filter(action='APPROVED').count()
    my_rejections = my_audits.filter(action='REJECTED').count()
    my_deroga_requests = my_audits.filter(action='DEROGA_REQUESTED').count()
    my_creations = my_audits.filter(action='CREATED').count()
    my_modifications = my_audits.filter(action__in=['MODIFIED', 'DATES_UPDATED', 'PERIOD_REDUCED', 'PERIOD_EXTENDED']).count()
    my_cancellations = my_audits.filter(action='CANCELLED').count()
    
    # Deroga stats
    deroga_accepted = my_audits.filter(action='DEROGA_ACCEPTED').count()
    deroga_rejected = my_audits.filter(action='DEROGA_REJECTED').count()
    
    # ========== CURRENT YEAR STATS ==========
    my_current_year = my_approved.filter(end_date__gte=year_start, start_date__lte=year_end)
    my_current_year_days = sum(overlap_days(b.start_date, b.end_date, year_start, year_end) for b in my_current_year)
    
    other_current_year = other_approved.filter(end_date__gte=year_start, start_date__lte=year_end)
    other_current_year_days = sum(overlap_days(b.start_date, b.end_date, year_start, year_end) for b in other_current_year)
    
    # ========== UPCOMING BOOKINGS ==========
    today = date.today()
    my_upcoming = my_approved.filter(start_date__gte=today).order_by('start_date')[:5]
    next_booking = my_upcoming.first()
    days_to_next = (next_booking.start_date - today).days if next_booking else None
    
    # ========== MONTHLY DISTRIBUTION ==========
    monthly_distribution = defaultdict(int)
    for b in my_approved:
        for day in iter_date_range(b.start_date, b.end_date):
            monthly_distribution[day.month] += 1
    
    month_names = ['Gen', 'Feb', 'Mar', 'Apr', 'Mag', 'Giu', 'Lug', 'Ago', 'Set', 'Ott', 'Nov', 'Dic']
    monthly_data = [monthly_distribution.get(i, 0) for i in range(1, 13)]
    
    # ========== COMPARISON ==========
    total_all_days = my_total_days + other_total_days
    if total_all_days > 0:
        my_percentage = round((my_total_days / total_all_days * 100), 1)
        other_percentage = round(100 - my_percentage, 1)
    else:
        my_percentage = 0
        other_percentage = 0
    
    context = {
        'user_group': user_group,
        'other_group': other_group,
        'current_year': current_year,
        
        # My stats
        'my_total_periods': my_approved.count(),
        'my_total_days': my_total_days,
        'my_max_period': my_max_period,
        'my_avg_period': round(my_avg_period, 1),
        'my_pending': my_bookings.filter(status='NEGOTIATION').count(),
        
        # Other family stats
        'other_total_periods': other_approved.count(),
        'other_total_days': other_total_days,
        'other_max_period': other_max_period,
        
        # Action stats
        'my_approvals': my_approvals,
        'my_rejections': my_rejections,
        'my_deroga_requests': my_deroga_requests,
        'my_creations': my_creations,
        'my_modifications': my_modifications,
        'my_cancellations': my_cancellations,
        'deroga_accepted': deroga_accepted,
        'deroga_rejected': deroga_rejected,
        
        # Current year
        'my_current_year_days': my_current_year_days,
        'my_current_year_periods': my_current_year.count(),
        'other_current_year_days': other_current_year_days,
        'other_current_year_periods': other_current_year.count(),
        
        # Upcoming
        'next_booking': next_booking,
        'days_to_next': days_to_next,
        'my_upcoming': my_upcoming,
        
        # Comparison
        'my_percentage': my_percentage,
        'other_percentage': other_percentage,
        
        # Monthly chart data
        'month_names': month_names,
        'monthly_data': monthly_data,
        
    # Yearly breakdown
    'my_periods_by_year': dict(sorted(my_periods_by_year.items(), reverse=True)),
        
        # Bridge (Ponte) statistics
        'my_total_bridges': my_total_bridges,
        'other_total_bridges': other_total_bridges,
        'my_bridge_percentage': my_bridge_percentage,
        'other_bridge_percentage': other_bridge_percentage,
        'my_current_year_bridges': my_current_year_bridges,
        'other_current_year_bridges': other_current_year_bridges,
        'my_bridges_by_type': dict(my_bridges_by_type),
        'other_bridges_by_type': dict(other_bridges_by_type),
        'my_bridge_details': sorted(my_bridge_details, key=lambda x: x['date'], reverse=True)[:10],  # Last 10
        'other_bridge_details': sorted(other_bridge_details, key=lambda x: x['date'], reverse=True)[:10],
    }
    
    return render(request, 'bookings/statistics.html', context)


@login_required
def export_ical(request):
    """Export bookings as iCal file"""
    from icalendar import Calendar, Event
    from django.http import HttpResponse
    
    user_group = request.user.profile.family_group
    
    # Get filter from query params
    filter_type = request.GET.get('filter', 'all')  # all, mine, approved
    
    cal = Calendar()
    cal.add('prodid', '-//PrenoPinzo//prenopinzo.local//')
    cal.add('version', '2.0')
    cal.add('calscale', 'GREGORIAN')
    cal.add('method', 'PUBLISH')
    cal.add('x-wr-calname', f'PrenoPinzo - {user_group}')
    
    # Build query
    bookings = Booking.objects.exclude(status='CANCELLED')
    
    if filter_type == 'mine':
        bookings = bookings.filter(family_group=user_group)
    elif filter_type == 'approved':
        bookings = bookings.filter(status='APPROVED')
    
    
    for booking in bookings:
        event = Event()
        event.add('summary', f"{booking.title} ({booking.family_group})")
        event.add('dtstart', booking.start_date)
        # End date is inclusive, iCal expects exclusive
        event.add('dtend', booking.end_date + timedelta(days=1))
        event.add('dtstamp', booking.created_at)
        event['uid'] = f'booking-{booking.id}@prenopinzo.local'
        
        # Add status as description
        status_map = {
            'APPROVED': '✅ Approvata',
            'NEGOTIATION': '⏳ In attesa',
            'DEROGA': '🔄 Richiesta revisione',
        }
        event.add('description', f"Stato: {status_map.get(booking.status, booking.status)}\nFamiglia: {booking.family_group}")
        
        # Color hint
        if booking.family_group == 'Andrea':
            event.add('categories', ['Andrea', 'Verde'])
        else:
            event.add('categories', ['Fabrizio', 'Blu'])
        
        cal.add_component(event)
    
    response = HttpResponse(cal.to_ical(), content_type='text/calendar')
    response['Content-Disposition'] = f'attachment; filename="prenopinzo_{filter_type}.ics"'
    return response


@login_required
def utilities_view(request):
    """Utilities page with weather and webcam"""
    return render(request, 'bookings/utilities.html')


# ============================================================
# Home Assistant Integration
# ============================================================
import requests
from django.conf import settings

@login_required
def get_thermostat_status(request):
    """Get current thermostat status from Home Assistant"""
    ha_url = getattr(settings, 'HA_URL', '')
    ha_token = getattr(settings, 'HA_TOKEN', '')
    entity_id = getattr(settings, 'HA_CLIMATE_ENTITY', 'climate.salotto')
    
    if not ha_url or not ha_token:
        return JsonResponse({'error': 'Home Assistant non configurato'}, status=500)
    
    try:
        headers = {
            'Authorization': f'Bearer {ha_token}',
            'Content-Type': 'application/json',
        }
        response = requests.get(
            f'{ha_url}/api/states/{entity_id}',
            headers=headers,
            timeout=10
        )
        response.raise_for_status()
        data = response.json()
        
        return JsonResponse({
            'state': data.get('state'),
            'current_temperature': data.get('attributes', {}).get('current_temperature'),
            'target_temperature': data.get('attributes', {}).get('temperature'),
            'hvac_action': data.get('attributes', {}).get('hvac_action'),
            'preset_mode': data.get('attributes', {}).get('preset_mode'),
            'min_temp': data.get('attributes', {}).get('min_temp', 7),
            'max_temp': data.get('attributes', {}).get('max_temp', 30),
        })
    except requests.exceptions.RequestException as e:
        return JsonResponse({'error': f'Errore connessione HA: {str(e)}'}, status=500)


@login_required
@require_POST
def set_thermostat_temp(request):
    """Set thermostat target temperature via Home Assistant"""
    ha_url = getattr(settings, 'HA_URL', '')
    ha_token = getattr(settings, 'HA_TOKEN', '')
    entity_id = getattr(settings, 'HA_CLIMATE_ENTITY', 'climate.salotto')
    
    if not ha_url or not ha_token:
        return JsonResponse({'error': 'Home Assistant non configurato'}, status=500)
    
    try:
        data = json.loads(request.body)
        temperature = float(data.get('temperature'))
        
        if temperature < 5 or temperature > 35:
            return JsonResponse({'error': 'Temperatura fuori range (5-35°C)'}, status=400)
        
        headers = {
            'Authorization': f'Bearer {ha_token}',
            'Content-Type': 'application/json',
        }
        
        response = requests.post(
            f'{ha_url}/api/services/climate/set_temperature',
            headers=headers,
            json={
                'entity_id': entity_id,
                'temperature': temperature
            },
            timeout=10
        )
        response.raise_for_status()
        
        return JsonResponse({'success': True, 'temperature': temperature})
    except (json.JSONDecodeError, ValueError, TypeError) as e:
        return JsonResponse({'error': f'Dati non validi: {str(e)}'}, status=400)
    except requests.exceptions.RequestException as e:
        return JsonResponse({'error': f'Errore connessione HA: {str(e)}'}, status=500)


@login_required
@require_POST
def set_thermostat_preset(request):
    """Set thermostat preset mode (away, home, etc.)"""
    ha_url = getattr(settings, 'HA_URL', '')
    ha_token = getattr(settings, 'HA_TOKEN', '')
    entity_id = getattr(settings, 'HA_CLIMATE_ENTITY', 'climate.salotto')
    
    if not ha_url or not ha_token:
        return JsonResponse({'error': 'Home Assistant non configurato'}, status=500)
    
    try:
        data = json.loads(request.body)
        preset = data.get('preset')
        
        headers = {
            'Authorization': f'Bearer {ha_token}',
            'Content-Type': 'application/json',
        }
        
        response = requests.post(
            f'{ha_url}/api/services/climate/set_preset_mode',
            headers=headers,
            json={
                'entity_id': entity_id,
                'preset_mode': preset
            },
            timeout=10
        )
        response.raise_for_status()
        
        return JsonResponse({'success': True, 'preset': preset})
    except (json.JSONDecodeError, ValueError, TypeError) as e:
        return JsonResponse({'error': f'Dati non validi: {str(e)}'}, status=400)
    except requests.exceptions.RequestException as e:
        return JsonResponse({'error': f'Errore connessione HA: {str(e)}'}, status=500)


@login_required
def get_schedule_options(request):
    """Get available schedule options from select entity"""
    ha_url = getattr(settings, 'HA_URL', '')
    ha_token = getattr(settings, 'HA_TOKEN', '')
    select_entity = getattr(settings, 'HA_SELECT_ENTITY', 'select.pinzolo')
    
    if not ha_url or not ha_token:
        return JsonResponse({'error': 'Home Assistant non configurato'}, status=500)
    
    try:
        headers = {
            'Authorization': f'Bearer {ha_token}',
            'Content-Type': 'application/json',
        }
        response = requests.get(
            f'{ha_url}/api/states/{select_entity}',
            headers=headers,
            timeout=10
        )
        response.raise_for_status()
        data = response.json()
        
        return JsonResponse({
            'current': data.get('state'),
            'options': data.get('attributes', {}).get('options', []),
        })
    except requests.exceptions.RequestException as e:
        return JsonResponse({'error': f'Errore connessione HA: {str(e)}'}, status=500)


@login_required
@require_POST
def set_schedule(request):
    """Set schedule via select entity"""
    ha_url = getattr(settings, 'HA_URL', '')
    ha_token = getattr(settings, 'HA_TOKEN', '')
    select_entity = getattr(settings, 'HA_SELECT_ENTITY', 'select.pinzolo')
    
    if not ha_url or not ha_token:
        return JsonResponse({'error': 'Home Assistant non configurato'}, status=500)
    
    try:
        data = json.loads(request.body)
        schedule = data.get('schedule')
        
        headers = {
            'Authorization': f'Bearer {ha_token}',
            'Content-Type': 'application/json',
        }
        
        response = requests.post(
            f'{ha_url}/api/services/select/select_option',
            headers=headers,
            json={
                'entity_id': select_entity,
                'option': schedule
            },
            timeout=10
        )
        response.raise_for_status()
        
        return JsonResponse({'success': True, 'schedule': schedule})
    except (json.JSONDecodeError, ValueError, TypeError) as e:
        return JsonResponse({'error': f'Dati non validi: {str(e)}'}, status=400)
    except requests.exceptions.RequestException as e:
        return JsonResponse({'error': f'Errore connessione HA: {str(e)}'}, status=500)


@login_required
def profile_view(request):
    """User profile and configuration view"""
    user_profile = get_object_or_404(UserProfile, user=request.user)
    
    if request.method == 'POST':
        form = UserProfileForm(request.POST, request.FILES, instance=user_profile)
        if form.is_valid():
            form.save()
            from django.contrib import messages
            messages.success(request, 'Profilo aggiornato con successo!')
            return redirect('profile')
    else:
        form = UserProfileForm(instance=user_profile)
    
    return render(request, 'bookings/profile.html', {
        'form': form,
        'user_profile': user_profile
    })


# ============================================================
# Ownership Periods (Periodi di Pertinenza)
# ============================================================
from .models import OwnershipPeriod

@login_required
def ownership_periods_view(request):
    """Page to manage ownership periods"""
    user_group = request.user.profile.family_group
    
    # My periods
    my_periods = OwnershipPeriod.objects.filter(family_group=user_group)
    # Other family's periods  
    family_groups = [choice[0] for choice in OwnershipPeriod.FAMILY_CHOICES]
    other_group = next((group for group in family_groups if group != user_group), None)
    other_periods = OwnershipPeriod.objects.filter(family_group=other_group)

    # Timeline data for the current year (split in two halves)
    timeline_year = date.today().year
    all_periods = list(my_periods) + list(other_periods)

    def period_to_segment_in_range(period, range_start, range_end):
        range_days = (range_end - range_start).days + 1
        overlap_start = max(period.start_date, range_start)
        overlap_end = min(period.end_date, range_end)
        if overlap_start > overlap_end:
            return None
        left = (overlap_start - range_start).days / range_days * 100
        width = ((overlap_end - overlap_start).days + 1) / range_days * 100
        return {
            'left': f"{left:.3f}",
            'width': f"{width:.3f}",
            'start': overlap_start,
            'end': overlap_end,
            'label': period.note or f"{period.start_date:%d %b} - {period.end_date:%d %b}",
            'family_group': period.family_group,
        }

    timeline_halves = [
        {
            'label': 'Gen–Giu',
            'start': date(timeline_year, 1, 1),
            'end': date(timeline_year, 6, 30),
            'months': list(range(1, 7)),
        },
        {
            'label': 'Lug–Dic',
            'start': date(timeline_year, 7, 1),
            'end': date(timeline_year, 12, 31),
            'months': list(range(7, 13)),
        },
    ]

    for half in timeline_halves:
        range_start = half['start']
        range_end = half['end']
        range_days = (range_end - range_start).days + 1
        segments = []
        for p in all_periods:
            seg = period_to_segment_in_range(p, range_start, range_end)
            if seg:
                segments.append(seg)
        segments.sort(key=lambda x: float(x['left']))
        half['segments'] = segments

        months = []
        for month in half['months']:
            month_start = date(timeline_year, month, 1)
            left = (month_start - range_start).days / range_days * 100
            months.append({
                'label': month_start.strftime('%b'),
                'left': f"{left:.3f}",
            })
        half['months'] = months
    
    return render(request, 'bookings/ownership_periods.html', {
        'my_periods': my_periods,
        'other_periods': other_periods,
        'user_group': user_group,
        'other_group': other_group,
        'timeline_year': timeline_year,
        'timeline_halves': timeline_halves,
    })


@login_required
def ownership_periods_api(request):
    """API endpoint returning ownership periods as calendar background events"""
    periods = OwnershipPeriod.objects.all()
    events = []
    
    for p in periods:
        # Pastel colors for background
        if p.family_group == 'Andrea':
            color = '#c8e6c9'  # Green pastel
        else:
            color = '#bbdefb'  # Blue pastel
        
        events.append({
            'id': f'ownership-{p.id}',
            'title': p.note or f'Pertinenza {p.family_group}',
            'start': p.start_date.isoformat(),
            'end': (p.end_date + timedelta(days=1)).isoformat(),  # FullCalendar end is exclusive
            'display': 'background',
            'color': color,
            'extendedProps': {
                'is_ownership_period': True,
                'family_group': p.family_group,
                'period_id': p.id,
            }
        })
    
    return JsonResponse(events, safe=False)


@login_required
@require_POST
def create_ownership_period(request):
    """Create a new ownership period"""
    from datetime import datetime
    
    user_group = request.user.profile.family_group
    
    start_str = request.POST.get('start_date')
    end_str = request.POST.get('end_date')
    note = request.POST.get('note', '')
    
    try:
        start_date = datetime.strptime(start_str, '%Y-%m-%d').date()
        end_date = datetime.strptime(end_str, '%Y-%m-%d').date()
    except (ValueError, TypeError):
        return JsonResponse({'status': 'error', 'message': 'Formato date non valido'}, status=400)
    
    if start_date >= end_date:
        return JsonResponse({'status': 'error', 'message': 'La data di fine deve essere successiva alla data di inizio'}, status=400)
    
    # Check overlap with other family's periods
    if OwnershipPeriod.check_overlap_with_other_family(user_group, start_date, end_date):
        return JsonResponse({'status': 'error', 'message': 'Sovrapposizione con un periodo di pertinenza dell\'altra famiglia!'}, status=400)
    
    period = OwnershipPeriod.objects.create(
        family_group=user_group,
        start_date=start_date,
        end_date=end_date,
        note=note,
        created_by=request.user
    )
    
    return JsonResponse({'status': 'ok', 'id': period.id})


@login_required
@require_POST
def delete_ownership_period(request, period_id):
    """Delete an ownership period"""
    period = get_object_or_404(OwnershipPeriod, id=period_id)
    
    # Only owner's family can delete
    if period.family_group != request.user.profile.family_group:
        return HttpResponseForbidden("Non puoi eliminare i periodi dell'altra famiglia.")
    
    period.delete()
    return JsonResponse({'status': 'ok'})

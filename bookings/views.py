from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, HttpResponseForbidden
from django.views.decorators.http import require_POST
from .models import Booking, UserProfile
from .forms import BookingForm, DerogaForm, RejectForm
import json

@login_required
def dashboard(request):
    try:
        user_group = request.user.profile.family_group
    except UserProfile.DoesNotExist:
        # Handle case where user has no profile (shouldn't happen in prod but useful for debug)
        return render(request, 'bookings/no_profile.html')

    # 1. Deroga Requests received (status=DEROGA, pending_with=ME)
    deroga_requests = Booking.objects.filter(status='DEROGA', pending_with=user_group)

    # 2. Approved Bookings (all)
    approved_bookings = Booking.objects.filter(status='APPROVED').order_by('start_date')

    # 3. Requires Attention (pending with ME, status=NEGOTIATION)
    requires_attention = Booking.objects.filter(status='NEGOTIATION', pending_with=user_group)

    # 4. My Requests (status=NEGOTIATION, user=ME/MyGroup) - actually spec says "Le Tue Richieste (In attesa)"
    # Usually pending with OTHER, but could be pending with ME if rejected.
    # We want requests created by create_user's group that are not finalized.
    my_requests = Booking.objects.filter(status='NEGOTIATION', family_group=user_group)

    # 5. History (Audit logs)
    # We'll fetch this in template via custom tag or just pass latest audits of all bookings
    # For now, let's keep it simple or add a separate query if needed.

    context = {
        'deroga_requests': deroga_requests,
        'approved_bookings': approved_bookings,
        'requires_attention': requires_attention,
        'my_requests': my_requests,
        'user_group': user_group,
    }
    return render(request, 'bookings/dashboard.html', context)

@login_required
def calendar_view(request):
    return render(request, 'bookings/calendar.html')

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
            'end': b.end_date.isoformat(), # FullCalendar end is exclusive? Check docs. Usually yes.
            'color': color,
            'extendedProps': {
                'status': b.status,
                'pending_with': b.pending_with
            }
        })
    return JsonResponse(events, safe=False)

@login_required
@require_POST
def create_booking(request):
    form = BookingForm(request.POST)
    if form.is_valid():
        booking = form.save(commit=False)
        booking.user = request.user
        booking.family_group = request.user.profile.family_group
        # Pending with OTHER group
        booking.pending_with = booking.get_other_group()
        # Check constraints? (Server side overlap check)
        # Simple overlap check:
        overlap = Booking.objects.filter(
            status='APPROVED',
            start_date__lt=booking.end_date,
            end_date__gt=booking.start_date
        ).exists()
        
        if overlap:
             return JsonResponse({'status': 'error', 'message': 'Date sovrapposte a una prenotazione approvata!'}, status=400)

        booking.save()
        booking.log_action('CREATED', request.user)
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
    return JsonResponse({'status': 'ok'})

@login_required
@require_POST
def reject_booking(request, booking_id):
    booking = get_object_or_404(Booking, id=booking_id)
    if booking.pending_with != request.user.profile.family_group:
        return HttpResponseForbidden("Non tocca a te rifiutare.")
    
    note = request.POST.get('note', '')
    booking.reject(request.user, note)
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
        # Check overlaps again?
        booking.modify(request.user, form.cleaned_data['start_date'], form.cleaned_data['end_date'])
        return JsonResponse({'status': 'ok'})
    return JsonResponse({'status': 'error', 'errors': form.errors}, status=400)

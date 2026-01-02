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
    overlap = Booking.objects.filter(
        status='APPROVED',
        start_date__lt=new_end,
        end_date__gt=new_start
    ).exclude(id=booking_id).exists()
    
    if overlap:
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

# Email Notification Configuration

## Overview
The email notification system sends HTML emails to the relevant family when booking actions require their approval.

## Configuration Files

### 1. Settings Configuration (`PrenoPinzo/settings.py`)

**SMTP Server Configuration:**
```python
EMAIL_HOST = '127.0.0.1'  # Your SMTP server
EMAIL_PORT = 25           # SMTP port
```

**App Base URL:**
```python
PRENOPINZO_BASE_URL = 'http://127.0.0.1:8000'  # Change to your production URL
```

**Family Email Addresses:**
```python
FAMILY_EMAILS = {
    'Andrea': 'andrea@example.com',     # Replace with actual email
    'Fabrizio': 'fabrizio@example.com', # Replace with actual email
}
```

## Email Triggers

Emails are automatically sent in the following cases:

1. **New Booking Created** (`action_type='created'`)
   - Sent to: Other family (who needs to approve)
   - When: A new booking request is created

2. **Booking Rejected** (`action_type='rejected'`)
   - Sent to: Original requester
   - When: A booking is rejected and needs corrections

3. **Deroga Requested** (`action_type='deroga_requested'`)
   - Sent to: Owner of the booking
   - When: Someone requests to change an already approved booking
   - Priority: URGENT

4. **Booking Modified** (`action_type='modified'`)
   - Sent to: Other family (for re-approval)
   - When: Owner modifies dates of their booking

## Email Content

Each email includes:
- 📌 Booking Title
- 👨‍👩‍👧‍👦 Family Name
- 📅 Period (start - end dates)
- 🔔 Current Status
- 👤 Created By
- 📝 Rejection/Deroga Notes (if applicable)
- 🔗 Direct link to Dashboard

## Testing Email Configuration

To test if email is working:

1. Create a test booking as one user
2. Check the console/logs for email sending status
3. For local testing without SMTP server, set:
   ```python
   EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
   ```
   This will print emails to the console instead of sending them.

## Production Deployment

Before deployment, update:
1. `PRENOPINZO_BASE_URL` to your production domain
2. `FAMILY_EMAILS` with real email addresses
3. `EMAIL_HOST` and `EMAIL_PORT` to your production SMTP server
4. Consider adding `EMAIL_HOST_USER` and `EMAIL_HOST_PASSWORD` if your SMTP requires authentication

## Troubleshooting

Check logs for email errors:
- Email sending is logged in `bookings/email_utils.py`
- Errors are logged with `logger.error()`
- Success is logged with `logger.info()`

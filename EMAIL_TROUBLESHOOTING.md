# Email Troubleshooting Guide for PrenoPinzo

This guide provides comprehensive instructions for diagnosing and resolving email sending issues.

---

## Table of Contents

1. [Manual Verification Checklist](#manual-verification-checklist)
2. [Running the Test Script](#running-the-test-script)
3. [SMTP Error Code Interpretation](#smtp-error-code-interpretation)
4. [Provider-Specific Configuration](#provider-specific-configuration)
5. [Firewall and Network Troubleshooting](#firewall-and-network-troubleshooting)
6. [Docker Container Issues](#docker-container-issues)

---

## Manual Verification Checklist

### 1. Host Configuration

**Check:** `EMAIL_HOST` in `.env`

```bash
# Verify the hostname resolves correctly
nslookup mail.tophost.it
# or
dig mail.tophost.it
```

**Common hosts:**
| Provider | Host |
|----------|------|
| Gmail | smtp.gmail.com |
| SendGrid | smtp.sendgrid.net |
| TopHost | mail.tophost.it |
| Outlook | smtp.office365.com |
| Yahoo | smtp.mail.yahoo.com |

**Verify:**

- [ ] Hostname is spelled correctly (no typos)
- [ ] No extra spaces before or after
- [ ] DNS resolves the hostname to an IP address

---

### 2. Port Configuration

**Check:** `EMAIL_PORT` in `.env`

| Port | Security     | EMAIL_USE_TLS | EMAIL_USE_SSL |
| ---- | ------------ | ------------- | ------------- |
| 587  | STARTTLS     | `True`        | `False`       |
| 465  | SSL/TLS      | `False`       | `True`        |
| 25   | None (plain) | `False`       | `False`       |

**Verify:**

- [ ] Port matches the security type you want
- [ ] Port is not blocked by firewall (see [Firewall Testing](#firewall-testing))

**Test port connectivity:**

```bash
# Test if port is reachable
telnet mail.tophost.it 587
# or
nc -vz mail.tophost.it 587
```

---

### 3. TLS/SSL Configuration

**Check:** `EMAIL_USE_TLS` and `EMAIL_USE_SSL` in `.env`

**Correct combinations:**

```ini
# Option 1: STARTTLS (recommended for port 587)
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_USE_SSL=False

# Option 2: SSL/TLS (for port 465)
EMAIL_PORT=465
EMAIL_USE_TLS=False
EMAIL_USE_SSL=True
```

**Verify:**

- [ ] TLS and SSL are not both `True` (invalid combination)
- [ ] Port matches the security type

---

### 4. Credentials

**Check:** `EMAIL_HOST_USER` and `EMAIL_HOST_PASSWORD` in `.env`

**Verify:**

- [ ] Username is correct (may be full email address or just username)
- [ ] Password has no leading/trailing spaces
- [ ] Special characters in password are preserved (no shell escaping issues)
- [ ] For SendGrid: username is `apikey` and password is the API key

**Common issues:**

```ini
# WRONG - spaces around password
EMAIL_HOST_PASSWORD= mypassword

# CORRECT
EMAIL_HOST_PASSWORD=mypassword

# WRONG - quotes may be included in value
EMAIL_HOST_PASSWORD="mypassword"

# CORRECT - quotes only if part of password
EMAIL_HOST_PASSWORD=mypassword
```

---

### 5. From Email Configuration

**Check:** `FROM_EMAIL` in `.env`

**Verify:**

- [ ] From email domain matches or is authorized by SMTP server
- [ ] Format is valid: `Name <email@domain.com>` or just `email@domain.com`
- [ ] Domain has proper SPF/DKIM records (for deliverability)

---

### 6. Firewall Testing

**Test outbound SMTP connectivity:**

```bash
# Test with telnet
telnet mail.tophost.it 587

# Test with netcat
nc -vz mail.tophost.it 587

# Test with curl (for HTTP-based services)
curl -v smtp://mail.tophost.it:587
```

**Expected output (successful):**

```
Trying 1.2.3.4...
Connected to mail.tophost.it.
Escape character is '^]'.
220 mail.tophost.it ESMTP ...
```

**Common firewall issues:**

- [ ] Corporate firewall blocks port 587/465
- [ ] Cloud provider (AWS, GCP) requires egress rules
- [ ] Docker container network isolation
- [ ] SELinux/AppArmor restrictions

---

## Running the Test Script

### Prerequisites

Python 3.6+ is required. No additional dependencies needed (uses standard library).

### Basic Usage

```bash
# Run with auto-detection of .env file
python scripts/test_email_configuration.py

# Specify .env file path
python scripts/test_email_configuration.py --env-file /path/to/.env

# Send actual test email
python scripts/test_email_configuration.py --test-recipient your-email@example.com
```

### Expected Output

```
======================================================================
PRENOPINZO EMAIL CONFIGURATION TEST
======================================================================
Test started at: 2026-03-28 14:30:00

CONFIGURATION LOADED:
----------------------------------------
  EMAIL_HOST:        mail.tophost.it
  EMAIL_PORT:        587
  EMAIL_USE_TLS:     True
  EMAIL_USE_SSL:     False
  EMAIL_HOST_USER:   gangini.net
  EMAIL_HOST_PASSWORD: Poke*********$t
  FROM_EMAIL:        PrenoPinzo <prenopinzo@gangini.net>

TEST 1: DNS Resolution
----------------------------------------
  [PASS] Resolved to: 1.2.3.4

TEST 2: Port Connectivity
----------------------------------------
  [PASS] Port 587 is OPEN and reachable

TEST 3: SMTP Connection
----------------------------------------
  [PASS] SMTP connection successful.
Server capabilities:
250-mail.tophost.it
...

TEST 4: SMTP Authentication
----------------------------------------
  [PASS] Authentication SUCCESSFUL

TEST 5: Send Test Email
----------------------------------------
  [PASS] Test email sent successfully to your-email@example.com

======================================================================
TEST SUMMARY
======================================================================
  [PASS] DNS Resolution
  [PASS] Port Connectivity
  [PASS] SMTP Connection
  [PASS] SMTP Authentication
  [PASS] Send Test Email

Results: 5/5 tests passed

SUCCESS: Email configuration is working correctly!
```

---

## SMTP Error Code Interpretation

### 2xx Codes (Success)

| Code | Meaning                               |
| ---- | ------------------------------------- |
| 220  | Service ready                         |
| 221  | Service closing transmission channel  |
| 235  | Authentication successful             |
| 250  | Requested mail action okay, completed |
| 251  | User not local; will forward          |

---

### 4xx Codes (Temporary Failures)

| Code | Meaning                                             | Action                   |
| ---- | --------------------------------------------------- | ------------------------ |
| 421  | Service not available, closing transmission channel | Retry later              |
| 450  | Mailbox unavailable (busy, greylisting)             | Retry later              |
| 451  | Local error, action aborted                         | Check server status      |
| 452  | Insufficient system storage                         | Retry later              |
| 454  | Temporary authentication failure                    | Check rate limits, retry |

---

### 5xx Codes (Permanent Failures)

| Code | Meaning                             | Action                           |
| ---- | ----------------------------------- | -------------------------------- |
| 500  | Syntax error, command unrecognized  | Check command format             |
| 501  | Syntax error in parameters          | Check email format               |
| 502  | Command not implemented             | Server limitation                |
| 503  | Bad sequence of commands            | Check TLS before auth            |
| 504  | Command parameter not implemented   | Server limitation                |
| 530  | Authentication required             | Enable TLS first                 |
| 534  | Authentication credentials invalid  | Reset password                   |
| 535  | Authentication failed               | **See detailed breakdown below** |
| 538  | Authentication mechanism too weak   | Use stronger auth                |
| 550  | Mailbox unavailable, user not found | Check recipient                  |
| 551  | User not local, try relay           | Check routing                    |
| 552  | Message exceeds fixed maximum size  | Reduce email size                |
| 553  | Mailbox name invalid                | Check sender address             |
| 554  | Transaction failed                  | Check SPF/DKIM                   |

---

### Detailed 535 Authentication Error Breakdown

**Error:** `535 5.7.8 Authentication failed`

**Possible causes:**

1. **Wrong credentials**

    ```
    Solution: Verify EMAIL_HOST_USER and EMAIL_HOST_PASSWORD in .env
    ```

2. **App password required (Gmail with 2FA)**

    ```
    Solution: Generate App Password at myaccount.google.com/apppasswords
    Use the 16-character app password, not your regular password
    ```

3. **Less secure apps blocked (Gmail)**

    ```
    Solution: Enable "Less secure app access" OR use OAuth2
    Note: Google is phasing out less secure app access
    ```

4. **Account locked or suspended**

    ```
    Solution: Log into webmail to verify account status
    Check for security alerts
    ```

5. **IP address blocked**

    ```
    Solution: Check if server IP is blacklisted
    Try from different network
    ```

6. **Wrong authentication method**
    ```
    Solution: Some providers require OAuth2 or specific auth methods
    Check provider documentation
    ```

---

## Provider-Specific Configuration

### Gmail

```ini
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_USE_SSL=False
EMAIL_HOST_USER=your-email@gmail.com
EMAIL_HOST_PASSWORD=your-app-password  # NOT regular password if 2FA enabled
FROM_EMAIL=Your Name <your-email@gmail.com>
```

**Requirements:**

- Enable 2-Factor Authentication
- Generate App Password (16 characters, no spaces)
- Or enable "Less secure app access" (not recommended)

---

### SendGrid

```ini
SENDGRID_API_KEY=SG.xxxxxxxxxxxxxxxxxxxxx
EMAIL_HOST=smtp.sendgrid.net
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_USE_SSL=False
EMAIL_HOST_USER=apikey  # LITERAL string "apikey"
EMAIL_HOST_PASSWORD=SG.xxxxxxxxxxxxxxxxxxxxx  # Same as SENDGRID_API_KEY
FROM_EMAIL=Your Name <verified@yourdomain.com>
```

**Requirements:**

- Domain must be verified in SendGrid
- Use literal string `apikey` as username
- API key as password

---

### TopHost (mail.tophost.it)

```ini
EMAIL_HOST=mail.tophost.it
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_USE_SSL=False
EMAIL_HOST_USER=gangini.net  # or full email
EMAIL_HOST_PASSWORD=your-password
FROM_EMAIL=PrenoPinzo <prenopinzo@gangini.net>
```

**Note:** Verify with TopHost if username should be:

- Just the domain (`gangini.net`)
- Full email address (`prenopinzo@gangini.net`)
- Just the username part (`prenopinzo`)

---

### Outlook / Office 365

```ini
EMAIL_HOST=smtp.office365.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_USE_SSL=False
EMAIL_HOST_USER=your-email@domain.com
EMAIL_HOST_PASSWORD=your-password
FROM_EMAIL=Your Name <your-email@domain.com>
```

**Requirements:**

- May require Modern Authentication (OAuth2)
- Check if SMTP AUTH is enabled in admin center

---

## Troubleshooting Workflow

### Step-by-Step Diagnosis

```
1. Run test script
   └─→ DNS fails? → Check hostname, DNS settings

2. Port connectivity test
   └─→ Port closed? → Check firewall, try alternative port

3. SMTP connection test
   └─→ Connection fails? → Try SSL vs TLS, check port

4. Authentication test
   └─→ Auth fails? → Check credentials, 2FA, app passwords

5. Send test email
   └─→ Send fails? → Check FROM email, SPF/DKIM, recipient
```

### Quick Fixes

| Symptom             | Quick Fix                             |
| ------------------- | ------------------------------------- |
| Connection timeout  | Try port 465 with SSL instead of 587  |
| Auth failed         | Regenerate password, check for spaces |
| Must issue STARTTLS | Set `EMAIL_USE_TLS=True`              |
| Relay access denied | Check FROM email domain               |
| Rate limited        | Wait 15-60 minutes, reduce frequency  |

---

## Security Best Practices

### .env File Security

```bash
# Restrict .env file permissions
chmod 600 .env

# Never commit .env to git
echo ".env" >> .gitignore

# Use different credentials for dev/prod
# Never use production credentials in development
```

### Credential Rotation

- [ ] Rotate email passwords/API keys every 90 days
- [ ] Revoke unused app passwords
- [ ] Monitor email sending logs for anomalies

### SPF/DKIM Records

For better deliverability, add DNS records:

```dns
; SPF Record (allows SMTP server to send for your domain)
yourdomain.com. IN TXT "v=spf1 include:mail.tophost.it -all"

; DKIM Record (signs emails cryptographically)
; Get value from your email provider
default._domainkey.yourdomain.com. IN TXT "v=DKIM1; k=rsa; p=MIIBIjANBg..."
```

---

## Contact and Support

If issues persist after following this guide:

1. Check your email provider's documentation
2. Contact TopHost support for server-specific issues
3. Review application logs: `docker logs prenopinzo-app`
4. Check server logs: `/var/log/mail.log` (if accessible)

---

## Docker Container Issues

### Problem: Password with Special Characters Not Working in Container

If your email password contains special characters like `$`, they may be interpreted as shell variables and truncated or modified.

**Symptom:**

- Email works locally but not inside Docker container
- Password appears truncated when checking environment variables in container

**Solution:**

#### Option 1: Use the .env file (Recommended - Secure)

The `.env` file is already in `.gitignore` and is passed directly to the container by docker-compose. Special characters like `$` are preserved correctly.

```ini
# .env file (NEVER commit this to git!)
EMAIL_HOST_PASSWORD=your$password$with$special$chars
```

**Important:** Make sure `.env` is in your `.gitignore`:

```gitignore
# Docker
.env
```

#### Option 2: Change your email password

If you continue to have issues, change your email password to one without special characters (`$`, `{`, `}`, `!`, etc.).

### Testing Email from Inside Container

```bash
# Copy test script to container
docker cp scripts/test_email_configuration.py prenopinzo-web:/app/scripts/

# Run test
docker exec prenopinzo-web python scripts/test_email_configuration.py

# Verify environment variable is correct
docker exec prenopinzo-web python -c "import os; print(repr(os.environ.get('EMAIL_HOST_PASSWORD')))"
```

### Verifying the Fix

After applying the fix, verify the password is correct inside the container:

```bash
docker exec prenopinzo-web python -c "import os; pw = os.environ.get('EMAIL_HOST_PASSWORD', ''); print(f'Length: {len(pw)}, Value: {pw}')"
```

Expected output for password `Poke36879255$t`:

```
Length: 14, Value: Poke36879255$t
```

---

_Last updated: 2026-03-28_

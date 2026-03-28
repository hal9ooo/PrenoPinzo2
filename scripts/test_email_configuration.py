#!/usr/bin/env python3
"""
Email Configuration Test Script for PrenoPinzo

This script performs comprehensive testing of SMTP email configuration
with verbose error handling and security best practices.

Usage:
    python test_email_configuration.py [--env-file PATH]

Features:
    - Validates .env file parameters
    - Tests SMTP connectivity (with and without TLS/SSL)
    - Tests SMTP authentication
    - Sends a test email (optional)
    - Provides detailed error interpretation
    - NEVER logs sensitive credentials
"""

import os
import sys
import smtplib
import socket
import ssl
import argparse
from typing import Optional, Tuple, Dict, Any
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime


# =============================================================================
# Configuration Loading
# =============================================================================

def load_env_file(env_path: str) -> Dict[str, str]:
    """Load environment variables from a .env file."""
    env_vars = {}
    if os.path.exists(env_path):
        with open(env_path, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, _, value = line.partition('=')
                    env_vars[key.strip()] = value.strip()
    return env_vars


def get_email_config(env_path: Optional[str] = None) -> Dict[str, Any]:
    """
    Load email configuration from environment or .env file.
    
    Returns a dictionary with sanitized config (passwords masked for display).
    """
    # Load from .env file if provided
    env_vars = {}
    if env_path:
        env_vars = load_env_file(env_path)
    else:
        # Try default locations
        for default_path in ['.env', '../.env', '../../.env']:
            if os.path.exists(default_path):
                env_vars = load_env_file(default_path)
                break
    
    # Also merge from actual environment (takes precedence)
    for key in ['EMAIL_HOST', 'EMAIL_PORT', 'EMAIL_USE_TLS', 'EMAIL_USE_SSL',
                'EMAIL_HOST_USER', 'EMAIL_HOST_PASSWORD', 'FROM_EMAIL',
                'SENDGRID_API_KEY']:
        if os.environ.get(key):
            env_vars[key] = os.environ.get(key)
    
    # Parse configuration
    config = {
        'host': env_vars.get('EMAIL_HOST', 'smtp.sendgrid.net'),
        'port': int(env_vars.get('EMAIL_PORT', '587')),
        'use_tls': env_vars.get('EMAIL_USE_TLS', 'True').lower() == 'true',
        'use_ssl': env_vars.get('EMAIL_USE_SSL', 'False').lower() == 'true',
        'username': env_vars.get('EMAIL_HOST_USER', 'apikey'),
        'password': env_vars.get('EMAIL_HOST_PASSWORD', ''),
        'from_email': env_vars.get('FROM_EMAIL', 'PrenoPinzo <noreply@localhost>'),
        'sendgrid_api_key': env_vars.get('SENDGRID_API_KEY', ''),
    }
    
    return config


def mask_secret(secret: str, show_chars: int = 4) -> str:
    """Mask a secret string for safe logging."""
    if not secret:
        return '(empty)'
    if len(secret) <= show_chars:
        return '***'
    return f"{secret[:show_chars]}{'*' * (len(secret) - show_chars)}"


# =============================================================================
# Network Connectivity Tests
# =============================================================================

def test_dns_resolution(host: str) -> Tuple[bool, str]:
    """Test if the email host can be resolved via DNS."""
    try:
        ip_addresses = socket.gethostbyname_ex(host)
        return True, f"Resolved to: {ip_addresses[2][0]}"
    except socket.gaierror as e:
        return False, f"DNS resolution failed: {e}"
    except Exception as e:
        return False, f"Unexpected DNS error: {e}"


def test_port_connectivity(host: str, port: int, timeout: int = 10) -> Tuple[bool, str]:
    """Test if the SMTP port is reachable (without TLS/SSL)."""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        result = sock.connect_ex((host, port))
        sock.close()
        
        if result == 0:
            return True, f"Port {port} is OPEN and reachable"
        else:
            return False, f"Port {port} is CLOSED (error code: {result})"
    except socket.timeout:
        return False, f"Connection to {host}:{port} timed out"
    except socket.error as e:
        return False, f"Socket error: {e}"
    except Exception as e:
        return False, f"Unexpected error: {e}"


# =============================================================================
# SMTP Tests
# =============================================================================

def test_smtp_connection(config: Dict[str, Any], use_tls: bool = False, 
                         use_ssl: bool = False, timeout: int = 10) -> Tuple[bool, str, Optional[smtplib.SMTP]]:
    """
    Test SMTP connection with optional TLS/SSL.
    
    Returns: (success, message, smtp_connection_or_none)
    """
    smtp = None
    try:
        # Create appropriate connection based on SSL/TLS requirements
        if use_ssl:
            # SSL connection (typically port 465)
            context = ssl.create_default_context()
            smtp = smtplib.SMTP_SSL(config['host'], config['port'], timeout=timeout, context=context)
        else:
            # Plain connection (TLS upgraded via STARTTLS if needed)
            smtp = smtplib.SMTP(config['host'], config['port'], timeout=timeout)
        
        # Get server greeting
        greeting = smtp.ehlo()[1]
        
        # Upgrade to TLS if requested and not using SSL
        if use_tls and not use_ssl:
            if smtp.has_extn('STARTTLS'):
                context = ssl.create_default_context()
                smtp.starttls(context=context)
                smtp.ehlo()  # Re-identify after TLS upgrade
            else:
                return False, "Server does not support STARTTLS extension", None
        
        return True, f"SMTP connection successful.\nServer capabilities:\n{greeting}", smtp
        
    except smtplib.SMTPConnectError as e:
        return False, f"SMTP connection failed: {e}\n\nPossible causes:\n  - Wrong host/port combination\n  - Server requires SSL instead of TLS (try port 465)\n  - Server requires TLS/SSL but connection is plain\n  - Firewall blocking connection", None
    except smtplib.SMTPServerDisconnected as e:
        return False, f"Server disconnected unexpectedly: {e}", None
    except ssl.SSLError as e:
        return False, f"SSL/TLS error: {e}\n\nPossible causes:\n  - Certificate verification failed\n  - Wrong SSL/TLS configuration\n  - Server certificate is self-signed or expired", None
    except socket.timeout:
        return False, f"Connection timed out after {timeout} seconds", None
    except socket.gaierror as e:
        return False, f"Network error: {e}\n\nPossible causes:\n  - Invalid hostname\n  - DNS resolution failed\n  - Network connectivity issues", None
    except Exception as e:
        return False, f"Unexpected error: {type(e).__name__}: {e}", None
    finally:
        # Don't close here - caller manages the connection
        pass
    
    return False, "Unknown error", None


def test_smtp_authentication(smtp: smtplib.SMTP, username: str, 
                             password: str) -> Tuple[bool, str]:
    """
    Test SMTP authentication.
    
    Returns: (success, message)
    """
    try:
        smtp.login(username, password)
        return True, "Authentication SUCCESSFUL"
    except smtplib.SMTPAuthenticationError as e:
        error_code = e.smtp_code if hasattr(e, 'smtp_code') else 'unknown'
        error_msg = e.smtp_error.decode() if hasattr(e, 'smtp_error') else str(e)
        
        interpretation = f"""
Authentication FAILED (SMTP Code: {error_code})

Error details: {error_msg}

Common causes and solutions:
  • Code 535/534: Invalid credentials
    → Verify username and password in .env file
    → Check for extra spaces or special characters
    → Ensure password hasn't expired
    
  • Code 535: Authentication method not supported
    → Server may require OAuth2 or app-specific password
    → Check if 2FA is enabled (may need app password)
    
  • Code 530: Must issue STARTTLS before authentication
    → Enable EMAIL_USE_TLS=True in .env
    
  • Code 454: Temporary authentication failure
    → Server may be rate-limiting; wait and retry
    → Check if account is locked
    
  • Code 550/553: Mailbox not allowed
    → Username may not be a valid mailbox
    → For SendGrid, use 'apikey' as username
"""
        return False, interpretation
    except smtplib.SMTPNotSupportedError as e:
        return False, f"Authentication method not supported: {e}\n\nServer may require a different authentication mechanism."
    except Exception as e:
        return False, f"Unexpected authentication error: {type(e).__name__}: {e}"


def send_test_email(smtp: smtplib.SMTP, from_email: str, to_email: str, 
                    subject: str = "PrenoPinzo Email Test", 
                    body: str = None) -> Tuple[bool, str]:
    """
    Send a test email through the authenticated SMTP connection.
    
    Returns: (success, message)
    """
    if body is None:
        body = f"""
This is a test email from PrenoPinzo.

If you received this message, your email configuration is working correctly.

Test Details:
  • Sent at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
  • From: {from_email}
  • To: {to_email}

--
PrenoPinzo Email System
"""

    try:
        msg = MIMEMultipart()
        msg['From'] = from_email
        msg['To'] = to_email
        msg['Subject'] = subject
        msg.attach(MIMEText(body, 'plain'))
        
        smtp.send_message(msg)
        return True, f"Test email sent successfully to {to_email}"
    except smtplib.SMTPRecipientsRefused as e:
        return False, f"Recipient refused: {e}\n\nPossible causes:\n  - Invalid recipient email address\n  - Domain is blocked or doesn't exist\n  - Recipient server rejected the email"
    except smtplib.SMTPSenderRefused as e:
        return False, f"Sender refused: {e}\n\nPossible causes:\n  - From email is not authorized\n  - Domain lacks proper DNS records (SPF, DKIM)\n  - Server requires specific sender address"
    except smtplib.SMTPDataError as e:
        return False, f"Data error: {e}\n\nPossible causes:\n  - Email content rejected\n  - Message too large\n  - Content filtering triggered"
    except Exception as e:
        return False, f"Unexpected error sending email: {type(e).__name__}: {e}"


# =============================================================================
# Main Test Runner
# =============================================================================

def run_tests(config: Dict[str, Any], test_recipient: Optional[str] = None) -> None:
    """Run all email configuration tests."""
    
    print("=" * 70)
    print("PRENOPINZO EMAIL CONFIGURATION TEST")
    print("=" * 70)
    print(f"Test started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # Display configuration (with masked secrets)
    print("CONFIGURATION LOADED:")
    print("-" * 40)
    print(f"  EMAIL_HOST:        {config['host']}")
    print(f"  EMAIL_PORT:        {config['port']}")
    print(f"  EMAIL_USE_TLS:     {config['use_tls']}")
    print(f"  EMAIL_USE_SSL:     {config['use_ssl']}")
    print(f"  EMAIL_HOST_USER:   {config['username']}")
    print(f"  EMAIL_HOST_PASSWORD: {mask_secret(config['password'])}")
    print(f"  FROM_EMAIL:        {config['from_email']}")
    if config.get('sendgrid_api_key'):
        print(f"  SENDGRID_API_KEY:  {mask_secret(config['sendgrid_api_key'])}")
    print()
    
    results = []
    
    # Test 1: DNS Resolution
    print("TEST 1: DNS Resolution")
    print("-" * 40)
    success, message = test_dns_resolution(config['host'])
    results.append(('DNS Resolution', success))
    print(f"  [{'PASS' if success else 'FAIL'}] {message}")
    print()
    
    if not success:
        print("ERROR: Cannot proceed without DNS resolution.")
        print_results(results)
        return
    
    # Test 2: Port Connectivity
    print("TEST 2: Port Connectivity")
    print("-" * 40)
    success, message = test_port_connectivity(config['host'], config['port'])
    results.append(('Port Connectivity', success))
    print(f"  [{'PASS' if success else 'FAIL'}] {message}")
    print()
    
    if not success:
        print("WARNING: Port is not reachable. Trying SMTP test anyway...")
    
    # Test 3: SMTP Connection
    print("TEST 3: SMTP Connection")
    print("-" * 40)
    success, message, smtp = test_smtp_connection(
        config, 
        use_tls=config['use_tls'], 
        use_ssl=config['use_ssl']
    )
    results.append(('SMTP Connection', success))
    print(f"  [{'PASS' if success else 'FAIL'}] {message}")
    print()
    
    if not success:
        # Try alternative configurations
        print("Attempting alternative configurations...")
        print()
        
        # Try SSL if TLS failed
        if config['use_tls'] and not config['use_ssl']:
            print("Trying SSL on port 465...")
            alt_config = config.copy()
            alt_config['use_tls'] = False
            alt_config['use_ssl'] = True
            alt_config['port'] = 465
            success, message, smtp = test_smtp_connection(alt_config, use_ssl=True)
            if success:
                print(f"  [{'PASS'}] SSL on port 465 works! Consider updating .env")
                results.append(('SMTP (SSL port 465)', True))
            else:
                print(f"  [{'FAIL'}] {message}")
                results.append(('SMTP (SSL port 465)', False))
            print()
        
        if not smtp:
            print("ERROR: Cannot proceed without SMTP connection.")
            print_results(results)
            return
    
    # Test 4: SMTP Authentication
    print("TEST 4: SMTP Authentication")
    print("-" * 40)
    if smtp:
        success, message = test_smtp_authentication(
            smtp, 
            config['username'], 
            config['password']
        )
        results.append(('SMTP Authentication', success))
        print(f"  [{'PASS' if success else 'FAIL'}] {message}")
        print()
        
        if not success:
            print("ERROR: Authentication failed. Cannot send test email.")
            print_results(results)
            smtp.quit()
            return
        
        # Test 5: Send Test Email
        if test_recipient:
            print("TEST 5: Send Test Email")
            print("-" * 40)
            success, message = send_test_email(
                smtp, 
                config['from_email'], 
                test_recipient
            )
            results.append(('Send Test Email', success))
            print(f"  [{'PASS' if success else 'FAIL'}] {message}")
            print()
        
        # Close connection
        smtp.quit()
    
    # Print Summary
    print_results(results)


def print_results(results: list) -> None:
    """Print test results summary."""
    print("=" * 70)
    print("TEST SUMMARY")
    print("=" * 70)
    
    passed = sum(1 for _, success in results if success)
    total = len(results)
    
    for test_name, success in results:
        status = "PASS" if success else "FAIL"
        print(f"  [{status}] {test_name}")
    
    print()
    print(f"Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("\nSUCCESS: Email configuration is working correctly!")
    else:
        print("\nWARNING: Some tests failed. Review the error messages above.")
    
    print()
    print("MANUAL VERIFICATION CHECKLIST:")
    print("-" * 40)
    print("""
□ Verify EMAIL_HOST is correct (e.g., smtp.gmail.com, mail.tophost.it)
□ Verify EMAIL_PORT matches the security type:
    • Port 587 → TLS (EMAIL_USE_TLS=True, EMAIL_USE_SSL=False)
    • Port 465 → SSL (EMAIL_USE_TLS=False, EMAIL_USE_SSL=True)
    • Port 25 → Plain (both False) - rarely used now
□ Verify credentials:
    • Username should be the full email or 'apikey' for SendGrid
    • Password should not have extra spaces
    • For Gmail with 2FA, use App Password, not regular password
□ Check firewall rules allow outbound connections on the SMTP port
□ Verify FROM_EMAIL domain matches or is authorized by the SMTP server
□ For SendGrid: Use 'apikey' as username and API key as password
□ Check DNS records (SPF, DKIM) if emails are rejected by recipients
""")


def main():
    parser = argparse.ArgumentParser(
        description='Test PrenoPinzo email configuration',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python test_email_configuration.py
  python test_email_configuration.py --env-file /path/to/.env
  python test_email_configuration.py --test-recipient test@example.com
        """
    )
    parser.add_argument(
        '--env-file', 
        type=str, 
        default=None,
        help='Path to .env file (default: search common locations)'
    )
    parser.add_argument(
        '--test-recipient',
        type=str,
        default=None,
        help='Email address to send test email to (optional)'
    )
    
    args = parser.parse_args()
    
    # Load configuration
    config = get_email_config(args.env_file)
    
    # Run tests
    run_tests(config, args.test_recipient)


if __name__ == '__main__':
    main()

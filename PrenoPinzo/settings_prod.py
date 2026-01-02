"""
Django production settings for PrenoPinzo project.
Loads configuration from environment variables.
"""

import os
from pathlib import Path

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# SECURITY: Load from environment
SECRET_KEY = os.environ.get('SECRET_KEY', 'change-me-in-production')

# SECURITY: Never run with debug in production
DEBUG = os.environ.get('DEBUG', 'False').lower() == 'true'

# Allowed hosts from environment (comma-separated)
ALLOWED_HOSTS = os.environ.get('ALLOWED_HOSTS', 'localhost').split(',')

# CSRF trusted origins for reverse proxy
CSRF_TRUSTED_ORIGINS = [
    f"http://{host}" for host in ALLOWED_HOSTS
] + [
    f"https://{host}" for host in ALLOWED_HOSTS
]

# Application definition
INSTALLED_APPS = [
    'daphne',
    'bookings',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django_htmx',
    'channels',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    "whitenoise.middleware.WhiteNoiseMiddleware",
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'django_htmx.middleware.HtmxMiddleware',
]

ROOT_URLCONF = 'PrenoPinzo.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'PrenoPinzo.wsgi.application'
ASGI_APPLICATION = 'PrenoPinzo.asgi.application'

# Channel layers for WebSocket
CHANNEL_LAYERS = {
    'default': {
        'BACKEND': 'channels.layers.InMemoryChannelLayer'
    }
}

# Database - SQLite with persistent path
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': Path(os.environ.get('DATABASE_PATH', BASE_DIR / 'data' / 'db.sqlite3')),
    }
}


# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]


# Internationalization
LANGUAGE_CODE = 'it-IT'
TIME_ZONE = 'Europe/Rome'
USE_I18N = True
USE_TZ = True
USE_L10N = True

# Date and time formats for Italian locale
DATE_FORMAT = 'd/m/Y'
SHORT_DATE_FORMAT = 'd/m/Y'
DATETIME_FORMAT = 'd/m/Y H:i'
SHORT_DATETIME_FORMAT = 'd/m/Y H:i'


# Static files
STATIC_URL = 'static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"

# Media files
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# Login/Logout redirects
LOGIN_REDIRECT_URL = 'dashboard'
LOGOUT_REDIRECT_URL = 'login'

# Default primary key field type
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'


# ============================================================
# Email Configuration - SendGrid
# ============================================================
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = 'smtp.sendgrid.net'
EMAIL_PORT = 587
EMAIL_USE_TLS = True
EMAIL_HOST_USER = 'apikey'  # SendGrid requires 'apikey' as username
EMAIL_HOST_PASSWORD = os.environ.get('SENDGRID_API_KEY', '')
DEFAULT_FROM_EMAIL = os.environ.get('FROM_EMAIL', 'PrenoPinzo <noreply@prenopinzo.local>')


# PrenoPinzo Custom Settings
PRENOPINZO_BASE_URL = os.environ.get('APP_BASE_URL', 'http://localhost')

# Family Email Addresses
FAMILY_EMAILS = {
    'Andrea': os.environ.get('EMAIL_ANDREA'),
    'Fabrizio': os.environ.get('EMAIL_FABRIZIO'),
}

# Home Assistant Integration
HA_URL = os.environ.get('HA_URL', '')
HA_TOKEN = os.environ.get('HA_TOKEN', '')
HA_CLIMATE_ENTITY = os.environ.get('HA_CLIMATE_ENTITY', 'climate.salotto')
HA_SELECT_ENTITY = os.environ.get('HA_SELECT_ENTITY', 'select.pinzolo')


# ============================================================
# Security Settings for Production
# ============================================================
if not DEBUG:
    # HTTPS settings (enable when using HTTPS)
    # SECURE_SSL_REDIRECT = True
    # SESSION_COOKIE_SECURE = True
    # CSRF_COOKIE_SECURE = True
    
    # Additional security
    SECURE_BROWSER_XSS_FILTER = True
    SECURE_CONTENT_TYPE_NOSNIFF = True
    X_FRAME_OPTIONS = 'DENY'

"""Production settings for Exam Jingga DATH Stack project."""
import os
from .base import *  # noqa: F401, F403

DEBUG = False

# Allowed hosts configuration
ALLOWED_HOSTS = [
    host.strip()
    for host in os.environ.get(
        'ALLOWED_HOSTS',
        'exam.smkn1rongga.sch.id,145.241.157.243,localhost,127.0.0.1'
    ).split(',')
    if host.strip()
]

# Database (PostgreSQL for VPS production / Supavisor pooler)
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.environ.get('DB_NAME', 'exam_jingga'),
        'USER': os.environ.get('DB_USER', 'postgres'),
        'PASSWORD': os.environ.get('DB_PASSWORD', ''),
        'HOST': os.environ.get('DB_HOST', 'localhost'),
        'PORT': os.environ.get('DB_PORT', '5432'),  # Default 5432 or Supavisor pooler 6543
        'CONN_MAX_AGE': int(os.environ.get('DB_CONN_MAX_AGE', 600)),
        'OPTIONS': {
            'sslmode': os.environ.get('DB_SSLMODE', 'prefer'),
        },
    }
}

# Static files configuration for WhiteNoise (Compression & High Performance Caching)
STORAGES = {
    'default': {
        'BACKEND': 'django.core.files.storage.FileSystemStorage',
    },
    'staticfiles': {
        'BACKEND': 'whitenoise.storage.CompressedStaticFilesStorage',
    },
}

# Security & SSL Settings
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SESSION_COOKIE_HTTPONLY = True
CSRF_COOKIE_HTTPONLY = True

SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = 'DENY'

# HTTP Strict Transport Security (HSTS)
SECURE_HSTS_SECONDS = int(os.environ.get('SECURE_HSTS_SECONDS', 31536000))  # 1 year
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True

# CSRF Trusted Origins
CSRF_TRUSTED_ORIGINS = [
    origin.strip()
    for origin in os.environ.get(
        'CSRF_TRUSTED_ORIGINS',
        'https://exam.smkn1rongga.sch.id,http://145.241.157.243'
    ).split(',')
    if origin.strip()
]

# Keycloak SSO Production Configuration
KEYCLOAK_URL = os.environ.get('KEYCLOAK_URL', 'https://sso.smkn1rongga.sch.id').rstrip('/')
KEYCLOAK_REALM = os.environ.get('KEYCLOAK_REALM', 'sekolah')
KEYCLOAK_CLIENT_ID = os.environ.get('KEYCLOAK_CLIENT_ID', 'exam-jingga')
KEYCLOAK_CLIENT_SECRET = os.environ.get('KEYCLOAK_CLIENT_SECRET', '')
KEYCLOAK_REDIRECT_URI = os.environ.get(
    'KEYCLOAK_REDIRECT_URI',
    'https://exam.smkn1rongga.sch.id/auth/callback/'
)

# Central Data Master OpenAPI Base URL & Webhook
DATA_MASTER_BASE_URL = os.environ.get(
    'DATA_MASTER_BASE_URL',
    'https://data.smkn1rongga.sch.id'
).rstrip('/')
WEBHOOK_SECRET_KEY = os.environ.get(
    'WEBHOOK_SECRET_KEY',
    'exam-jingga-webhook-secret-key-2026'
)

# Production Logging Configuration
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {process:d} {thread:d} {message}',
            'style': '{',
        },
        'simple': {
            'format': '{levelname} {asctime} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
    },
    'root': {
        'handlers': ['console'],
        'level': 'WARNING',
    },
    'loggers': {
        'django': {
            'handlers': ['console'],
            'level': os.environ.get('DJANGO_LOG_LEVEL', 'INFO'),
            'propagate': False,
        },
        'apps': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': False,
        },
    },
}

"""Development settings for Exam Jingga DATH Stack project."""
import os
from .base import *  # noqa: F401, F403

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

ALLOWED_HOSTS = ['*']

# Database (SQLite for local development)
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',  # noqa: F405
    }
}

# In local development, stream media assets directly from production VPS to avoid local disk bloating
MEDIA_URL = os.getenv('MEDIA_URL', 'https://exam.smkn1rongga.sch.id/media/')

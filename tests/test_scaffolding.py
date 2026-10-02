"""Tests for Task 1: Django Scaffolding & Offline Vendor Assets."""
from pathlib import Path
import pytest
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management import call_command


@pytest.mark.django_db
def test_django_settings():
    """Verify core Django settings."""
    assert settings.AUTH_USER_MODEL == 'accounts.CustomUser'
    assert settings.TIME_ZONE == 'Asia/Jakarta'
    assert 'apps.core.apps.CoreConfig' in settings.INSTALLED_APPS
    assert 'apps.accounts.apps.AccountsConfig' in settings.INSTALLED_APPS
    assert 'whitenoise.middleware.WhiteNoiseMiddleware' in settings.MIDDLEWARE


def test_system_check():
    """Verify django manage.py check passes with 0 errors."""
    call_command('check')


def test_legacy_react_archived():
    """Verify legacy React frontend files are archived in _legacy_react/."""
    base_dir = settings.BASE_DIR
    legacy_dir = base_dir / '_legacy_react'
    assert legacy_dir.exists()
    assert (legacy_dir / 'src').exists()
    assert (legacy_dir / 'public').exists()
    assert (legacy_dir / 'vite.config.js').exists()


def test_vendor_static_assets_exist():
    """Verify offline-first vendor assets and logo exist in static/."""
    base_dir = settings.BASE_DIR
    vendor_dir = base_dir / 'static' / 'vendor'
    assert (vendor_dir / 'htmx.min.js').is_file()
    assert (vendor_dir / 'htmx.min.js').stat().st_size > 1000

    assert (vendor_dir / 'alpine.min.js').is_file()
    assert (vendor_dir / 'alpine.min.js').stat().st_size > 1000

    assert (vendor_dir / 'lucide.min.js').is_file()
    assert (vendor_dir / 'lucide.min.js').stat().st_size > 1000

    logo_path = base_dir / 'static' / 'img' / 'logo_sekolah.png'
    assert logo_path.is_file()
    assert logo_path.stat().st_size > 1000


@pytest.mark.django_db
def test_custom_user_creation():
    """Verify CustomUser creation with UUID and roles."""
    User = get_user_model()
    user = User.objects.create_user(
        username='admin_test',
        email='admin@smkn1rongga.sch.id',
        password='password123',
        role='admin'
    )
    assert str(user.id) != ''
    assert user.role == 'admin'
    assert user.username == 'admin_test'
    assert str(user) == 'admin_test (Admin)'
    assert user.is_admin is True
    assert user.is_student is False


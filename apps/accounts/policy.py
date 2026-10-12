"""Kebijakan peran terpusat. Dipakai view di server dan sidebar, supaya menu yang tampil
selalu sama dengan yang diizinkan server."""
from apps.accounts.models import Role

SCHOOL_ADMIN_ROLES = {Role.ADMIN, Role.KURIKULUM, Role.PLATFORM_ADMIN, Role.DATA_ADMIN}


def _role(user):
    return str(getattr(user, 'role', '') or '').lower()


def is_school_admin(user):
    """Admin, kurikulum, platform/data admin, atau superuser."""
    if not user or not user.is_authenticated:
        return False
    return bool(user.is_superuser) or _role(user) in SCHOOL_ADMIN_ROLES


def is_teacher(user):
    return bool(user and user.is_authenticated) and _role(user) == Role.GURU

"""Role-based access control decorators for Exam Jingga."""
from functools import wraps
from django.contrib import messages
from django.shortcuts import redirect
from django.urls import reverse
from apps.accounts.models import Role


def role_required(allowed_roles):
    """
    Decorator for views that checks whether the logged-in user has one of the allowed roles.
    
    Behavior:
    - If user is not authenticated: redirect to login page with `?next=<current_path>`.
    - If user is a superuser: always allow access.
    - If user role is in allowed_roles: allow access.
    - If unauthorized:
        * Siswa attempting to access staff/admin routes is redirected to `/student/dashboard/`.
        * Staff/Teacher attempting to access student-only routes is redirected to `/dashboard/`.
    """
    if isinstance(allowed_roles, str):
        allowed_roles = [allowed_roles]
    allowed_roles_normalized = [str(r).lower() for r in allowed_roles]

    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            if not request.user.is_authenticated:
                login_url = reverse('accounts:login')
                return redirect(f"{login_url}?next={request.get_full_path()}")

            # Superusers always have full access
            if request.user.is_superuser:
                return view_func(request, *args, **kwargs)

            user_role = str(getattr(request.user, 'role', '')).lower()

            if user_role in allowed_roles_normalized:
                return view_func(request, *args, **kwargs)

            # Unauthorized access redirection
            messages.warning(request, "Anda tidak memiliki izin untuk mengakses halaman tersebut.")
            if getattr(request.user, 'is_student', False):
                return redirect('/student/dashboard/')
            return redirect('/dashboard/')

        return _wrapped_view
    return decorator


def admin_required(view_func):
    """
    Decorator requiring Administrator, Platform Admin, Data Admin, or Kurikulum role.
    """
    return role_required([
        Role.ADMIN,
        Role.PLATFORM_ADMIN,
        Role.DATA_ADMIN,
        Role.KURIKULUM,
    ])(view_func)


def teacher_required(view_func):
    """
    Decorator requiring Teacher (Guru), Proctor (Pengawas), Kurikulum, or Admin role.
    """
    return role_required([
        Role.ADMIN,
        Role.PLATFORM_ADMIN,
        Role.DATA_ADMIN,
        Role.KURIKULUM,
        Role.GURU,
        Role.PENGAWAS,
    ])(view_func)


def student_required(view_func):
    """
    Decorator requiring Siswa role.
    """
    return role_required([Role.SISWA])(view_func)

"""Views for Accounts and Hybrid SSO Authentication."""
import logging
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.core.cache import cache
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils.http import url_has_allowed_host_and_scheme
from django.views import View
from django.views.decorators.http import require_http_methods


from apps.accounts.services.keycloak_auth import (
    exchange_code_for_tokens,
    generate_pkce_pair,
    generate_random_string,
    get_authorization_url,
    get_logout_url,
    parse_and_sync_user,
)

logger = logging.getLogger(__name__)


def login_view(request):
    """
    Renders login page if unauthenticated.
    If authenticated, redirects Siswa to `/student/dashboard/` and staff to `/dashboard/`.
    """
    if request.user.is_authenticated:
        if getattr(request.user, 'is_student', False):
            return redirect('/student/dashboard/')
        return redirect('/dashboard/')

    from django.template.response import TemplateResponse
    return TemplateResponse(request, 'accounts/login.html')



class LoginView(View):
    """Class-based wrapper for login_view."""
    def get(self, request, *args, **kwargs):
        return login_view(request)


def sso_login_redirect_view(request):
    """
    Initiates OIDC PKCE login flow.
    Stores state, code_verifier, and next target in session, then redirects to Keycloak.
    """
    state = generate_random_string(32)
    code_verifier, code_challenge = generate_pkce_pair()

    target_path = request.GET.get('next', '')

    request.session['kc_state'] = state
    request.session['kc_code_verifier'] = code_verifier
    request.session['kc_target_path'] = target_path

    redirect_uri = request.build_absolute_uri(reverse('accounts:sso_callback'))
    auth_url = get_authorization_url(redirect_uri, state, code_challenge)

    return redirect(auth_url)


def sso_callback_view(request):
    """
    Handles OIDC PKCE callback from Keycloak.
    Validates state and code verifier, exchanges code for tokens, synchronizes user profile,
    and logs the user into the Django session.
    """
    error = request.GET.get('error')
    error_description = request.GET.get('error_description')
    if error:
        logger.warning(f"SSO Callback returned error: {error} - {error_description}")
        messages.error(request, f"Otentikasi SSO dibatalkan atau gagal: {error_description or error}")
        return redirect('accounts:login')

    code = request.GET.get('code')
    state = request.GET.get('state')
    saved_state = request.session.get('kc_state')
    code_verifier = request.session.get('kc_code_verifier')
    target_path = request.session.get('kc_target_path')

    # Security verification: state and code_verifier
    if not state or state != saved_state:
        logger.error("State mismatch in SSO callback.")
        messages.error(request, "Validasi keamanan SSO gagal (State mismatch). Silakan coba login kembali.")
        return redirect('accounts:login')

    if not code or not code_verifier:
        logger.error("Missing authorization code or PKCE code verifier in session.")
        messages.error(request, "Kode otorisasi atau code verifier PKCE tidak ditemukan. Silakan coba login kembali.")
        return redirect('accounts:login')

    redirect_uri = request.build_absolute_uri(reverse('accounts:sso_callback'))

    try:
        tokens = exchange_code_for_tokens(code, code_verifier, redirect_uri)
        user = parse_and_sync_user(tokens)
    except Exception as exc:
        logger.exception("Error processing Keycloak tokens in sso_callback_view")
        messages.error(request, f"Gagal memproses otentikasi SSO: {exc}")
        return redirect('accounts:login')

    if not user.is_active:
        messages.error(request, "Akun ujian Anda dinonaktifkan oleh sekolah. Silakan hubungi bagian kurikulum.")
        return redirect('accounts:login')

    # Log user in
    login(request, user)

    # Store id_token for Single Logout
    request.session['kc_id_token'] = tokens.get('id_token')

    # Clean up temporary PKCE session data
    request.session.pop('kc_state', None)
    request.session.pop('kc_code_verifier', None)
    request.session.pop('kc_target_path', None)

    safe_target = _safe_next(request, target_path)
    if safe_target:
        return redirect(safe_target)

    if user.is_student:
        return redirect('/student/dashboard/')
    return redirect('/dashboard/')


EMERGENCY_MAX_FAILURES = 5
EMERGENCY_LOCK_SECONDS = 15 * 60


def _safe_next(request, target_path):
    if target_path and url_has_allowed_host_and_scheme(
        target_path, allowed_hosts={request.get_host()}, require_https=request.is_secure()
    ):
        return target_path
    return None


def _client_ip(request):
    forwarded = request.META.get('HTTP_X_FORWARDED_FOR', '')
    return forwarded.split(',')[0].strip() if forwarded else request.META.get('REMOTE_ADDR', '')


def _throttle_keys(request, username):
    return [f"emergency-login:ip:{_client_ip(request)}", f"emergency-login:user:{username.lower()}"]


@require_http_methods(['GET', 'POST'])
def emergency_login_view(request):
    """
    Jalur login darurat bila SSO Keycloak tidak bisa diakses. Hanya superuser yang bisa masuk;
    akun lain tidak punya kata sandi lokal karena semua peran login lewat SSO.
    """
    context = {'next': request.POST.get('next') or request.GET.get('next', '')}
    if request.method == 'GET':
        return render(request, 'accounts/emergency_login.html', context)

    username = request.POST.get('username', '').strip()
    password = request.POST.get('password', '')
    keys = _throttle_keys(request, username)

    if any(cache.get(key, 0) >= EMERGENCY_MAX_FAILURES for key in keys):
        context['error'] = "Terlalu banyak percobaan gagal. Coba lagi dalam 15 menit."
        return render(request, 'accounts/emergency_login.html', context, status=429)

    user = authenticate(request, username=username, password=password) if username and password else None
    if user is None or not user.is_superuser or not user.is_active:
        for key in keys:
            cache.set(key, cache.get(key, 0) + 1, EMERGENCY_LOCK_SECONDS)
        logger.warning("Login darurat gagal untuk username=%s ip=%s", username, _client_ip(request))
        context['error'] = "Username atau kata sandi salah, atau akun ini bukan superuser."
        return render(request, 'accounts/emergency_login.html', context)

    for key in keys:
        cache.delete(key)
    login(request, user)
    logger.warning("Login darurat superuser berhasil: %s ip=%s", user.username, _client_ip(request))
    return redirect(_safe_next(request, context['next']) or '/dashboard/')


def logout_view(request):
    """Keluar dari sesi Django dan sesi Keycloak, supaya siswa berikutnya di komputer lab tidak ikut masuk."""
    id_token = request.session.get('kc_id_token')
    logout(request)
    if not id_token:
        # Login darurat tidak punya sesi Keycloak; tetap bisa keluar walau SSO sedang mati
        return redirect('accounts:login')
    post_logout = request.build_absolute_uri(reverse('accounts:login'))
    return redirect(get_logout_url(redirect_uri=post_logout, id_token_hint=id_token))


# Backward compatibility alias
LogoutView = logout_view

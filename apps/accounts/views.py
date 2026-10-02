"""Views for Accounts and Hybrid SSO Authentication."""
import logging
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.shortcuts import redirect, render
from django.urls import reverse
from django.views import View
from django.views.decorators.http import require_http_methods, require_POST


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
    """Class-based view wrapper for login_view."""
    def get(self, request, *args, **kwargs):
        return login_view(request)

    def post(self, request, *args, **kwargs):
        return local_login_view(request)



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
        messages.error(request, "Akun ujian Anda dinonaktifkan oleh sekolah. Silakan hubungi proktor/administrator!")
        return redirect('accounts:login')

    # Log user in
    login(request, user)

    # Store id_token for Single Logout
    request.session['kc_id_token'] = tokens.get('id_token')

    # Clean up temporary PKCE session data
    request.session.pop('kc_state', None)
    request.session.pop('kc_code_verifier', None)
    request.session.pop('kc_target_path', None)

    # Redirect to target path or dashboard
    if target_path and target_path.startswith('/'):
        return redirect(target_path)

    if user.is_student:
        return redirect('/student/dashboard/')
    return redirect('/dashboard/')


@require_POST
def local_login_view(request):
    """
    Handles emergency local login for superusers and local administrators.
    """
    username = request.POST.get('username', '').strip()
    password = request.POST.get('password', '')
    target_path = request.POST.get('next') or request.GET.get('next')

    if not username or not password:
        messages.error(request, "Username dan kata sandi wajib diisi.")
        return redirect('accounts:login')

    user = authenticate(request, username=username, password=password)

    if user is not None:
        if not user.is_active:
            messages.error(request, "Akun lokal ini telah dinonaktifkan.")
            return redirect('accounts:login')

        login(request, user)

        if target_path and target_path.startswith('/'):
            return redirect(target_path)

        if user.is_student:
            return redirect('/student/dashboard/')
        return redirect('/dashboard/')

    messages.error(request, "Username atau kata sandi administrator lokal salah.")
    return redirect('accounts:login')


def logout_view(request):
    """
    Logs out of Django session and redirects directly to login page with flash message.
    """
    logout(request)
    messages.info(request, "Anda telah berhasil keluar dari sistem.")
    return redirect('accounts:login')


# Backward compatibility alias
LogoutView = logout_view

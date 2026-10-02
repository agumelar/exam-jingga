"""Keycloak OIDC PKCE and User Profile Synchronization Service for Exam Jingga."""
import base64
import hashlib
import json
import logging
import os
import re
import secrets
import uuid
from urllib.parse import urlencode
import requests
from django.conf import settings
from django.contrib.auth import get_user_model
from apps.accounts.models import Role

logger = logging.getLogger(__name__)

# Keycloak Configuration
KEYCLOAK_URL = getattr(
    settings,
    'KEYCLOAK_URL',
    os.environ.get('KEYCLOAK_URL', 'https://sso.smkn1rongga.sch.id')
).rstrip('/')
KEYCLOAK_REALM = getattr(
    settings,
    'KEYCLOAK_REALM',
    os.environ.get('KEYCLOAK_REALM', 'sekolah')
)
KEYCLOAK_CLIENT_ID = getattr(
    settings,
    'KEYCLOAK_CLIENT_ID',
    os.environ.get('KEYCLOAK_CLIENT_ID', 'exam-jingga')
)


def get_auth_endpoint() -> str:
    """Return Keycloak OIDC authorization endpoint URL."""
    return f"{KEYCLOAK_URL}/realms/{KEYCLOAK_REALM}/protocol/openid-connect/auth"


def get_token_endpoint() -> str:
    """Return Keycloak OIDC token endpoint URL."""
    return f"{KEYCLOAK_URL}/realms/{KEYCLOAK_REALM}/protocol/openid-connect/token"


def get_logout_endpoint() -> str:
    """Return Keycloak OIDC logout endpoint URL."""
    return f"{KEYCLOAK_URL}/realms/{KEYCLOAK_REALM}/protocol/openid-connect/logout"


def get_userinfo_endpoint() -> str:
    """Return Keycloak OIDC userinfo endpoint URL."""
    return f"{KEYCLOAK_URL}/realms/{KEYCLOAK_REALM}/protocol/openid-connect/userinfo"


# --- PKCE Helpers (RFC 7636) ---

def generate_random_string(length: int = 64) -> str:
    """
    Generate a cryptographically secure random string using RFC 7636 unreserved characters.
    Characters: [A-Z, a-z, 0-9, '-', '.', '_', '~']
    """
    charset = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-._~"
    return ''.join(secrets.choice(charset) for _ in range(length))


def generate_pkce_pair() -> tuple[str, str]:
    """
    Generate PKCE code_verifier and code_challenge (S256).
    Returns (code_verifier, code_challenge).
    """
    code_verifier = generate_random_string(64)
    # SHA-256 hash of verifier
    hashed = hashlib.sha256(code_verifier.encode('ascii')).digest()
    # Base64url encode without padding
    code_challenge = base64.urlsafe_b64encode(hashed).decode('ascii').rstrip('=')
    return code_verifier, code_challenge


def get_authorization_url(redirect_uri: str, state: str, code_challenge: str) -> str:
    """
    Construct the Keycloak OIDC authorization URL with PKCE and prompt=login.
    prompt=login is MANDATORY to force the credential prompt, preventing session
    collisions across shared student computer lab workstations.
    """
    params = {
        'client_id': KEYCLOAK_CLIENT_ID,
        'response_type': 'code',
        'scope': 'openid profile email roles',
        'redirect_uri': redirect_uri,
        'state': state,
        'code_challenge': code_challenge,
        'code_challenge_method': 'S256',
        'prompt': 'login',  # WAJIB: Anti-tabrak akun di lab komputer
    }
    return f"{get_auth_endpoint()}?{urlencode(params)}"


def exchange_code_for_tokens(code: str, code_verifier: str, redirect_uri: str) -> dict:
    """
    Exchange authorization code for tokens via Keycloak token endpoint.
    """
    payload = {
        'grant_type': 'authorization_code',
        'client_id': KEYCLOAK_CLIENT_ID,
        'code': code,
        'redirect_uri': redirect_uri,
        'code_verifier': code_verifier,
    }
    headers = {
        'Content-Type': 'application/x-www-form-urlencoded',
        'Accept': 'application/json',
    }

    try:
        response = requests.post(
            get_token_endpoint(),
            data=payload,
            headers=headers,
            timeout=10
        )
    except requests.RequestException as exc:
        logger.error(f"Gagal menghubungi server Keycloak SSO: {exc}")
        raise ValueError(f"Tidak dapat terhubung ke server SSO Keycloak: {exc}") from exc

    if not response.ok:
        error_description = "Gagal menukarkan token otentikasi dari Keycloak."
        try:
            err_json = response.json()
            error_description = err_json.get('error_description') or err_json.get('error') or error_description
        except Exception:
            pass
        logger.error(f"Keycloak token exchange error {response.status_code}: {error_description}")
        raise ValueError(error_description)

    return response.json()


def parse_jwt_payload(token: str) -> dict:
    """
    Decode JWT payload without cryptographic signature verification (already validated via TLS/token endpoint).
    """
    if not token or not isinstance(token, str):
        return {}
    parts = token.split('.')
    if len(parts) < 2:
        return {}
    payload_b64 = parts[1]
    # Add back base64 padding
    rem = len(payload_b64) % 4
    if rem > 0:
        payload_b64 += '=' * (4 - rem)
    try:
        decoded_bytes = base64.urlsafe_b64decode(payload_b64.encode('utf-8'))
        return json.loads(decoded_bytes.decode('utf-8'))
    except Exception as exc:
        logger.warning(f"Gagal mem-parsing payload JWT: {exc}")
        return {}


def determine_user_role(payload: dict, username: str, email: str) -> str:
    """
    Determine institutional role from Keycloak realm roles, client roles, username pattern, and email domain.
    """
    realm_roles = payload.get('realm_access', {}).get('roles', []) or []
    client_roles = payload.get('resource_access', {}).get(KEYCLOAK_CLIENT_ID, {}).get('roles', []) or []
    all_roles = [str(r).lower() for r in (realm_roles + client_roles)]
    uname_lower = username.lower()
    email_lower = email.lower()

    # 1. Platform Admin & Data Admin
    if 'platform_admin' in all_roles:
        return Role.PLATFORM_ADMIN
    if 'data_admin' in all_roles:
        return Role.DATA_ADMIN

    # 2. Kurikulum
    if 'kurikulum' in all_roles:
        return Role.KURIKULUM

    # 3. Admin / Superadmin
    has_admin_keyword = any(r in all_roles for r in ['admin', 'superadmin', 'administrator'])
    if has_admin_keyword or uname_lower == 'admin' or 'admin' in uname_lower:
        return Role.ADMIN

    # 4. Pengawas
    if 'pengawas' in all_roles:
        return Role.PENGAWAS

    # 5. Siswa (Explicit role 'student'/'siswa' or username is NIS digits 4-12)
    is_likely_nis = bool(re.match(r'^\d{4,12}$', username))
    has_student_role = any(r in all_roles for r in ['siswa', 'student', 'peserta'])
    if has_student_role or is_likely_nis or ('@student.smkn1rongga.sch.id' in email_lower):
        return Role.SISWA

    # 6. Guru / PTK / Staff (Role 'ptk'/'guru', 16-18 digits NIP, or teacher email domain)
    is_likely_nip = bool(re.match(r'^\d{16,18}$', username))
    has_teacher_role = any(r in all_roles for r in ['guru', 'teacher', 'ptk', 'staff'])
    if has_teacher_role or is_likely_nip or '@smkn1rongga.sch.id' in email_lower:
        return Role.GURU

    # Default fallback
    return Role.SISWA


def get_m2m_access_token(client_id: str = None, client_secret: str = None) -> str:
    """
    Obtain a Machine-to-Machine (M2M) bearer access token from Keycloak using Client Credentials Grant.
    Used by backend services to query Central Data Master API (https://data.smkn1rongga.sch.id/v1).
    """
    c_id = client_id or getattr(settings, 'KEYCLOAK_CLIENT_ID', 'exam-jingga')
    c_secret = client_secret or getattr(settings, 'KEYCLOAK_CLIENT_SECRET', '')

    payload = {
        'grant_type': 'client_credentials',
        'client_id': c_id,
    }
    if c_secret:
        payload['client_secret'] = c_secret

    headers = {
        'Content-Type': 'application/x-www-form-urlencoded',
        'Accept': 'application/json',
    }

    try:
        response = requests.post(
            get_token_endpoint(),
            data=payload,
            headers=headers,
            timeout=10
        )
    except requests.RequestException as exc:
        logger.error(f"Gagal meminta token M2M dari Keycloak: {exc}")
        raise ValueError(f"Tidak dapat terhubung ke server SSO Keycloak: {exc}") from exc

    if not response.ok:
        err_msg = f"Keycloak M2M token request failed ({response.status_code})"
        try:
            err_json = response.json()
            err_msg = err_json.get('error_description') or err_json.get('error') or err_msg
        except Exception:
            pass
        logger.warning(f"Keycloak M2M error: {err_msg}")
        raise ValueError(err_msg)

    data = response.json()
    return data.get('access_token')


def parse_and_sync_user(tokens: dict):
    """
    Parse ID token or access token from Keycloak, synchronize or create CustomUser in local database,
    and link with Student or Teacher profile.
    """
    id_token = tokens.get('id_token')
    access_token = tokens.get('access_token')

    payload = parse_jwt_payload(id_token) if id_token else {}
    if not payload and access_token:
        payload = parse_jwt_payload(access_token)

    if not payload:
        raise ValueError("Token otorisasi Keycloak tidak valid atau kosong.")

    sub_str = payload.get('sub')
    if not sub_str:
        raise ValueError("Identitas pengguna (sub) tidak ditemukan dalam token Keycloak.")

    # Convert sub to valid UUID if possible
    sso_uuid = None
    try:
        sso_uuid = uuid.UUID(str(sub_str))
    except (ValueError, AttributeError, TypeError):
        sso_uuid = uuid.uuid5(uuid.NAMESPACE_DNS, str(sub_str))

    username = str(payload.get('preferred_username') or payload.get('sub') or '').strip()
    email = str(payload.get('email') or '').strip().lower()
    full_name = (
        payload.get('name')
        or payload.get('given_name')
        or payload.get('preferred_username')
        or username
    )

    role = determine_user_role(payload, username, email)
    is_likely_nis = bool(re.match(r'^\d{4,12}$', username))

    User = get_user_model()
    user = None

    # 1. Lookup by sso_id
    if sso_uuid:
        user = User.objects.filter(sso_id=sso_uuid).first()

    # 2. Lookup by username
    if not user and username:
        user = User.objects.filter(username__iexact=username).first()

    # 3. Lookup by email
    if not user and email:
        user = User.objects.filter(email__iexact=email).first()

    is_staff_role = role in [Role.ADMIN, Role.PLATFORM_ADMIN, Role.DATA_ADMIN, Role.KURIKULUM]

    if user:
        # Update existing user profile
        user.sso_id = sso_uuid
        if full_name:
            user.full_name = full_name
            name_parts = full_name.split(' ', 1)
            user.first_name = name_parts[0]
            user.last_name = name_parts[1] if len(name_parts) > 1 else ''
        if email:
            user.email = email
        user.role = role
        if role == Role.SISWA and (is_likely_nis or not user.nis):
            user.nis = username
        if is_staff_role and not user.is_staff:
            user.is_staff = True
        user.save()
        logger.info(f"Updated user profile for {user.username} (role: {user.role})")
    else:
        # Auto-create new user
        name_parts = full_name.split(' ', 1) if full_name else ['', '']
        first_name = name_parts[0]
        last_name = name_parts[1] if len(name_parts) > 1 else ''

        user = User(
            username=username,
            email=email or f"{username}@smkn1rongga.sch.id",
            sso_id=sso_uuid,
            full_name=full_name,
            first_name=first_name,
            last_name=last_name,
            role=role,
            nis=username if (role == Role.SISWA and is_likely_nis) else None,
            is_staff=is_staff_role,
            is_active=True
        )
        user.set_unusable_password()
        user.save()
        logger.info(f"Created new SSO user {user.username} (role: {user.role})")

    # Link with Student or Teacher profile in master_data
    try:
        from apps.master_data.models import Student, Teacher
        if user.role == Role.SISWA and user.nis:
            student = Student.objects.filter(nis=user.nis).first() or (sso_uuid and Student.objects.filter(sso_id=sso_uuid).first())
            if student:
                student.user = user
                student.full_name = user.full_name or student.full_name
                if sso_uuid:
                    student.sso_id = sso_uuid
                student.save(update_fields=['user', 'full_name', 'sso_id'])
        elif user.is_teacher or user.is_admin or user.is_curriculum:
            teacher = (sso_uuid and Teacher.objects.filter(sso_id=sso_uuid).first()) or Teacher.objects.filter(email__iexact=user.email).first() or Teacher.objects.filter(nip=user.username).first()
            if teacher:
                teacher.user = user
                teacher.full_name = user.full_name or teacher.full_name
                if sso_uuid:
                    teacher.sso_id = sso_uuid
                teacher.save(update_fields=['user', 'full_name', 'sso_id'])
    except Exception as exc:
        logger.warning(f"Tidak dapat menautkan profil master data untuk {user.username}: {exc}")

    return user


def get_logout_url(redirect_uri: str = None, id_token_hint: str = None) -> str:
    """
    Construct Keycloak single logout URL.
    """
    params = {}
    if id_token_hint:
        params['id_token_hint'] = id_token_hint
    else:
        params['client_id'] = KEYCLOAK_CLIENT_ID

    if redirect_uri:
        params['post_logout_redirect_uri'] = redirect_uri

    return f"{get_logout_endpoint()}?{urlencode(params)}"


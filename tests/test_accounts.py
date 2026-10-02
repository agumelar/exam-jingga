"""Tests for Accounts Module & Hybrid SSO Authentication (Task 3)."""
import base64
import json
import uuid
from unittest.mock import MagicMock, patch
import pytest
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from django.contrib.messages.storage.fallback import FallbackStorage
from django.http import HttpResponse
from django.test import Client, RequestFactory
from django.urls import reverse

from apps.accounts.decorators import admin_required, role_required, student_required, teacher_required
from apps.accounts.models import Role
from apps.accounts.services import keycloak_auth


def make_mock_jwt(payload: dict) -> str:
    """Helper to create base64url encoded mock JWT string."""
    header = {"alg": "RS256", "typ": "JWT"}
    h_b64 = base64.urlsafe_b64encode(json.dumps(header).encode()).decode().rstrip('=')
    p_b64 = base64.urlsafe_b64encode(json.dumps(payload).encode()).decode().rstrip('=')
    return f"{h_b64}.{p_b64}.mock_signature"


def add_session_and_messages(request):
    """Helper to attach session and message storage to RequestFactory requests."""
    from django.contrib.sessions.middleware import SessionMiddleware
    middleware = SessionMiddleware(lambda r: None)
    middleware.process_request(request)
    request.session.save()
    setattr(request, '_messages', FallbackStorage(request))


# ==============================================================================
# 1. CustomUser Model & Roles Tests
# ==============================================================================

@pytest.mark.django_db
def test_custom_user_roles_and_properties():
    """Verify role helper properties on CustomUser."""
    User = get_user_model()

    # Siswa
    student = User.objects.create_user(
        username='1234567890',
        nis='1234567890',
        full_name='Ahmad Siswa',
        role=Role.SISWA
    )
    assert student.is_student is True
    assert student.is_teacher is False
    assert student.is_admin is False
    assert student.is_curriculum is False
    assert str(student) == 'Ahmad Siswa (Siswa)'
    assert student.get_full_name() == 'Ahmad Siswa'

    # Guru
    teacher = User.objects.create_user(
        username='guru_math',
        full_name='Budi Santoso, S.Pd',
        role=Role.GURU
    )
    assert teacher.is_student is False
    assert teacher.is_teacher is True
    assert teacher.is_admin is False
    assert teacher.is_curriculum is False
    assert str(teacher) == 'Budi Santoso, S.Pd (Guru)'

    # Pengawas
    proctor = User.objects.create_user(
        username='pengawas_lab',
        full_name='Cici Pengawas',
        role=Role.PENGAWAS
    )
    assert proctor.is_teacher is True
    assert proctor.is_student is False

    # Kurikulum
    curriculum = User.objects.create_user(
        username='waka_kurikulum',
        full_name='Dedi Kurikulum, M.Kom',
        role=Role.KURIKULUM
    )
    assert curriculum.is_curriculum is True
    assert curriculum.is_admin is True

    # Admin, Platform Admin, Data Admin
    admin_user = User.objects.create_user(
        username='admin_exam',
        role=Role.ADMIN
    )
    platform_admin = User.objects.create_user(
        username='platform_adm',
        role=Role.PLATFORM_ADMIN
    )
    data_admin = User.objects.create_user(
        username='data_adm',
        role=Role.DATA_ADMIN
    )

    assert admin_user.is_admin is True
    assert platform_admin.is_admin is True
    assert data_admin.is_admin is True

    # Superuser check
    superuser = User.objects.create_superuser(
        username='root',
        email='root@school.test',
        password='password123'
    )
    assert superuser.is_admin is True


# ==============================================================================
# 2. Decorators & RBAC Redirection Tests
# ==============================================================================

@pytest.mark.django_db
def test_role_required_unauthenticated_redirects_to_login():
    """Unauthenticated users must be redirected to login with next parameter."""
    factory = RequestFactory()

    @role_required([Role.ADMIN])
    def dummy_view(request):
        return HttpResponse("Allowed")

    request = factory.get('/dashboard/admin/?tab=stats')
    request.user = AnonymousUser()
    add_session_and_messages(request)

    response = dummy_view(request)
    assert response.status_code == 302
    assert response.url == f"/accounts/login/?next=/dashboard/admin/?tab=stats"


@pytest.mark.django_db
def test_role_required_authorized_access():
    """Users with permitted roles should access the view successfully."""
    factory = RequestFactory()
    User = get_user_model()

    @admin_required
    def admin_view(request):
        return HttpResponse("Admin Section")

    admin = User.objects.create_user(username='adm', role=Role.ADMIN)
    request = factory.get('/dashboard/admin/')
    request.user = admin
    add_session_and_messages(request)

    response = admin_view(request)
    assert response.status_code == 200
    assert response.content.decode() == "Admin Section"


@pytest.mark.django_db
def test_role_required_student_trying_admin_redirects_to_student_dashboard():
    """Siswa accessing admin route is redirected to /student/dashboard/."""
    factory = RequestFactory()
    User = get_user_model()

    @admin_required
    def protected_view(request):
        return HttpResponse("Protected")

    student = User.objects.create_user(username='student1', role=Role.SISWA)
    request = factory.get('/dashboard/schedules/')
    request.user = student
    add_session_and_messages(request)

    response = protected_view(request)
    assert response.status_code == 302
    assert response.url == '/student/dashboard/'


@pytest.mark.django_db
def test_role_required_teacher_trying_student_redirects_to_dashboard():
    """Staff/Teacher accessing student-only route is redirected to /dashboard/."""
    factory = RequestFactory()
    User = get_user_model()

    @student_required
    def exam_room_view(request):
        return HttpResponse("Exam Active")

    teacher = User.objects.create_user(username='teacher1', role=Role.GURU)
    request = factory.get('/student/exam/123/')
    request.user = teacher
    add_session_and_messages(request)

    response = exam_room_view(request)
    assert response.status_code == 302
    assert response.url == '/dashboard/'


# ==============================================================================
# 3. PKCE & Keycloak Helper Services Tests
# ==============================================================================

def test_pkce_generation_and_auth_url():
    """Verify PKCE parameters and Keycloak authorization URL construction."""
    verifier, challenge = keycloak_auth.generate_pkce_pair()

    assert len(verifier) >= 43
    assert len(challenge) > 10
    # No padding character '=' in base64url encoded challenge
    assert '=' not in challenge

    redirect_uri = 'http://localhost:8000/auth/callback/'
    state = 'test_state_123'
    auth_url = keycloak_auth.get_authorization_url(redirect_uri, state, challenge)

    assert 'prompt=login' in auth_url
    assert 'code_challenge_method=S256' in auth_url
    assert f'code_challenge={challenge}' in auth_url
    assert f'state={state}' in auth_url
    assert 'client_id=exam-jingga' in auth_url
    assert 'response_type=code' in auth_url
    assert 'scope=openid+profile+email+roles' in auth_url or 'scope=openid%20profile%20email%20roles' in auth_url


@patch('apps.accounts.services.keycloak_auth.requests.post')
def test_exchange_code_for_tokens_success(mock_post):
    """Verify token exchange POST request to Keycloak."""
    mock_response = MagicMock()
    mock_response.ok = True
    mock_response.json.return_value = {
        'access_token': 'test_access',
        'id_token': 'test_id',
        'refresh_token': 'test_refresh'
    }
    mock_post.return_value = mock_response

    tokens = keycloak_auth.exchange_code_for_tokens(
        code='auth_code_xyz',
        code_verifier='verifier_123',
        redirect_uri='http://localhost:8000/auth/callback/'
    )

    assert tokens['access_token'] == 'test_access'
    assert mock_post.call_count == 1


# ==============================================================================
# 4. User Synchronization Service Tests
# ==============================================================================

@pytest.mark.django_db
def test_parse_and_sync_new_student_user():
    """Verify student sync creates a new CustomUser with NIS and SISWA role."""
    sso_uuid = str(uuid.uuid4())
    payload = {
        'sub': sso_uuid,
        'preferred_username': '0067891234',
        'email': '0067891234@student.smkn1rongga.sch.id',
        'name': 'Fajar Nugraha',
        'realm_access': {'roles': ['siswa', 'default-roles-sekolah']}
    }
    mock_tokens = {'id_token': make_mock_jwt(payload)}

    user = keycloak_auth.parse_and_sync_user(mock_tokens)

    assert user.username == '0067891234'
    assert user.full_name == 'Fajar Nugraha'
    assert user.nis == '0067891234'
    assert user.role == Role.SISWA
    assert str(user.sso_id) == sso_uuid
    assert user.is_student is True
    assert user.has_usable_password() is False


@pytest.mark.django_db
def test_parse_and_sync_teacher_and_admin_roles():
    """Verify role determination for teacher, kurikulum, and platform admin."""
    # Teacher
    teacher_payload = {
        'sub': str(uuid.uuid4()),
        'preferred_username': '198501012010011005',
        'email': 'hendra@smkn1rongga.sch.id',
        'name': 'Hendra Gunawan, S.Pd',
        'realm_access': {'roles': ['guru']}
    }
    teacher = keycloak_auth.parse_and_sync_user({'id_token': make_mock_jwt(teacher_payload)})
    assert teacher.role == Role.GURU
    assert teacher.is_teacher is True

    # Kurikulum
    curriculum_payload = {
        'sub': str(uuid.uuid4()),
        'preferred_username': 'kurikulum_smk',
        'email': 'kurikulum@smkn1rongga.sch.id',
        'name': 'Drs. Supriyadi',
        'realm_access': {'roles': ['kurikulum', 'guru']}
    }
    curriculum = keycloak_auth.parse_and_sync_user({'id_token': make_mock_jwt(curriculum_payload)})
    assert curriculum.role == Role.KURIKULUM
    assert curriculum.is_curriculum is True
    assert curriculum.is_staff is True

    # Platform Admin
    admin_payload = {
        'sub': str(uuid.uuid4()),
        'preferred_username': 'sysadmin',
        'email': 'sysadmin@smkn1rongga.sch.id',
        'name': 'System Administrator',
        'realm_access': {'roles': ['platform_admin']}
    }
    platform_admin = keycloak_auth.parse_and_sync_user({'id_token': make_mock_jwt(admin_payload)})
    assert platform_admin.role == Role.PLATFORM_ADMIN
    assert platform_admin.is_admin is True


@pytest.mark.django_db
def test_parse_and_sync_updates_existing_user():
    """Verify existing user lookup and profile update."""
    User = get_user_model()
    sso_uuid = uuid.uuid4()
    existing = User.objects.create_user(
        username='00889900',
        nis='00889900',
        full_name='Old Name',
        email='old@school.test',
        role=Role.SISWA,
        sso_id=sso_uuid
    )

    payload = {
        'sub': str(sso_uuid),
        'preferred_username': '00889900',
        'email': 'new_email@student.smkn1rongga.sch.id',
        'name': 'Updated New Name',
        'realm_access': {'roles': ['siswa']}
    }

    synced = keycloak_auth.parse_and_sync_user({'id_token': make_mock_jwt(payload)})

    assert synced.id == existing.id
    assert synced.full_name == 'Updated New Name'
    assert synced.email == 'new_email@student.smkn1rongga.sch.id'


# ==============================================================================
# 5. Views End-to-End Tests
# ==============================================================================

@pytest.mark.django_db
def test_login_view_unauthenticated_renders_page(client: Client):
    """Login view renders the M3 login page with direct login form and SSO option."""
    response = client.get(reverse('accounts:login'))
    assert response.status_code == 200
    assert 'EXAM' in response.content.decode()
    assert 'JINGGA' in response.content.decode()
    assert 'Masuk dengan SSO SMKN 1 Rongga' in response.content.decode()
    assert 'Opsi Login Manual' in response.content.decode()



@pytest.mark.django_db
def test_login_view_authenticated_redirects(client: Client):
    """Authenticated users visiting /auth/login/ are redirected to their dashboard."""
    User = get_user_model()
    student = User.objects.create_user(username='student_login', role=Role.SISWA)
    client.force_login(student)

    response = client.get(reverse('accounts:login'))
    assert response.status_code == 302
    assert response.url == '/student/dashboard/'

    admin = User.objects.create_user(username='admin_login', role=Role.ADMIN)
    client.force_login(admin)
    response_admin = client.get(reverse('accounts:login'))
    assert response_admin.status_code == 302
    assert response_admin.url == '/dashboard/'


@pytest.mark.django_db
def test_sso_login_redirect_view_sets_session_and_redirects(client: Client):
    """SSO redirect view generates state and PKCE verifier in session and redirects."""
    response = client.get(reverse('accounts:sso_redirect') + '?next=/dashboard/schedules/')
    assert response.status_code == 302
    assert 'sso.smkn1rongga.sch.id' in response.url
    assert 'prompt=login' in response.url

    session = client.session
    assert 'kc_state' in session
    assert 'kc_code_verifier' in session
    assert session.get('kc_target_path') == '/dashboard/schedules/'


@pytest.mark.django_db
@patch('apps.accounts.views.exchange_code_for_tokens')
def test_sso_callback_view_successful_login(mock_exchange, client: Client):
    """Callback view validates state, synchronizes user, and logs in."""
    sso_uuid = str(uuid.uuid4())
    payload = {
        'sub': sso_uuid,
        'preferred_username': '00991122',
        'email': '00991122@student.smkn1rongga.sch.id',
        'name': 'Andi Pratama',
        'realm_access': {'roles': ['siswa']}
    }
    id_token = make_mock_jwt(payload)
    mock_exchange.return_value = {
        'access_token': 'mock_access',
        'id_token': id_token,
        'refresh_token': 'mock_refresh'
    }

    # Setup session with PKCE values
    session = client.session
    session['kc_state'] = 'test_valid_state'
    session['kc_code_verifier'] = 'test_valid_verifier'
    session['kc_target_path'] = '/student/dashboard/'
    session.save()

    callback_url = reverse('accounts:sso_callback') + '?code=auth_code_123&state=test_valid_state'
    response = client.get(callback_url)

    assert response.status_code == 302
    assert response.url == '/student/dashboard/'

    # Check user is logged into session
    assert int(client.session['_auth_user_id'] is not None)
    User = get_user_model()
    logged_user = User.objects.get(username='00991122')
    assert logged_user.full_name == 'Andi Pratama'


@pytest.mark.django_db
def test_sso_callback_view_state_mismatch_fails(client: Client):
    """Callback view rejects requests with invalid state."""
    session = client.session
    session['kc_state'] = 'expected_state'
    session['kc_code_verifier'] = 'verifier'
    session.save()

    callback_url = reverse('accounts:sso_callback') + '?code=auth_code_123&state=wrong_state'
    response = client.get(callback_url, follow=True)

    assert response.status_code == 200
    assert 'Validasi keamanan SSO gagal' in response.content.decode()


@pytest.mark.django_db
def test_local_login_view_success_and_failure(client: Client):
    """Verify emergency local admin login authentication."""
    User = get_user_model()
    admin = User.objects.create_user(
        username='local_admin',
        password='StrongPassword123!',
        role=Role.ADMIN,
        full_name='Local Administrator'
    )

    # Failed login (wrong password)
    fail_res = client.post(reverse('accounts:local_login'), {
        'username': 'local_admin',
        'password': 'WrongPassword'
    }, follow=True)
    assert fail_res.status_code == 200
    assert 'salah' in fail_res.content.decode().lower()

    # Successful login
    success_res = client.post(reverse('accounts:local_login'), {
        'username': 'local_admin',
        'password': 'StrongPassword123!',
        'next': '/dashboard/'
    })
    assert success_res.status_code == 302
    assert success_res.url == '/dashboard/'


@pytest.mark.django_db
def test_logout_view_clears_session_and_redirects(client: Client):
    """Logout view clears user session and redirects directly to login page."""
    User = get_user_model()
    user = User.objects.create_user(username='user_logout', role=Role.GURU)
    client.force_login(user)

    response = client.get(reverse('accounts:logout'))
    assert response.status_code == 302
    assert response.url == reverse('accounts:login')
    assert '_auth_user_id' not in client.session

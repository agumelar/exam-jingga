"""Fase 0 audit: login SSO-only, jalur darurat superuser, webhook, XSS, upload pengaturan."""
import base64
import io
import json
import uuid
from unittest.mock import patch

import pytest
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import RequestFactory
from django.urls import NoReverseMatch, reverse

from apps.accounts.models import Role
from apps.accounts.services import keycloak_auth
from apps.master_data.models import Student, Teacher
from apps.master_data.views import WebhookSyncView

User = get_user_model()


def _jwt(payload):
    body = base64.urlsafe_b64encode(json.dumps(payload).encode()).decode().rstrip('=')
    return f"eyJhbGciOiJub25lIn0.{body}.sig"


@pytest.fixture(autouse=True)
def _clear_cache():
    cache.clear()
    yield
    cache.clear()


# ==============================================================================
# Login
# ==============================================================================

@pytest.mark.django_db
def test_login_page_has_no_password_form(client):
    html = client.get(reverse('accounts:login')).content.decode()
    assert 'name="password"' not in html
    assert reverse('accounts:sso_redirect') in html


def test_old_local_login_route_is_gone():
    with pytest.raises(NoReverseMatch):
        reverse('accounts:local_login')


@pytest.mark.django_db
def test_emergency_login_rejects_non_superuser_with_correct_password(client):
    User.objects.create_user(username='guru_lama', password='Jingga123', role=Role.GURU)

    res = client.post(reverse('accounts:emergency_login'), {'username': 'guru_lama', 'password': 'Jingga123'})

    assert '_auth_user_id' not in client.session
    assert res.status_code == 200


@pytest.mark.django_db
def test_emergency_login_accepts_superuser(client):
    User.objects.create_superuser(username='root_darurat', email='r@test.com', password='S4ngat-Rahasia!')

    res = client.post(reverse('accounts:emergency_login'), {'username': 'root_darurat', 'password': 'S4ngat-Rahasia!'})

    assert res.status_code == 302
    assert res.url == '/dashboard/'
    assert '_auth_user_id' in client.session


@pytest.mark.django_db
def test_emergency_login_throttles_after_repeated_failures(client):
    User.objects.create_superuser(username='root_throttle', email='t@test.com', password='S4ngat-Rahasia!')
    for _ in range(5):
        client.post(reverse('accounts:emergency_login'), {'username': 'root_throttle', 'password': 'salah'})

    res = client.post(reverse('accounts:emergency_login'), {'username': 'root_throttle', 'password': 'S4ngat-Rahasia!'})

    assert '_auth_user_id' not in client.session
    assert 'Terlalu banyak percobaan' in res.content.decode()


@pytest.mark.django_db
@pytest.mark.parametrize('evil', ['//evil.example/x', '/\\evil.example', 'https://evil.example/'])
def test_emergency_login_ignores_external_next(client, evil):
    User.objects.create_superuser(username='root_next', email='n@test.com', password='S4ngat-Rahasia!')

    res = client.post(reverse('accounts:emergency_login'), {'username': 'root_next', 'password': 'S4ngat-Rahasia!', 'next': evil})

    assert res.url == '/dashboard/'


@pytest.mark.django_db
def test_sso_callback_ignores_external_next(client):
    session = client.session
    session['kc_state'] = 'st'
    session['kc_code_verifier'] = 'cv'
    session['kc_target_path'] = '//evil.example/steal'
    session.save()
    payload = {'sub': str(uuid.uuid4()), 'preferred_username': '0011223344', 'realm_access': {'roles': ['siswa']}}

    with patch('apps.accounts.views.exchange_code_for_tokens', return_value={'id_token': _jwt(payload)}):
        res = client.get(reverse('accounts:sso_callback'), {'code': 'c', 'state': 'st'})

    assert res.url == '/student/dashboard/'


@pytest.mark.django_db
def test_logout_ends_keycloak_session(client):
    user = User.objects.create_user(username='guru_logout2', role=Role.GURU)
    client.force_login(user)
    session = client.session
    session['kc_id_token'] = 'id-token-value'
    session.save()

    res = client.get(reverse('accounts:logout'))

    assert res.status_code == 302
    assert res.url.startswith(f"{settings.KEYCLOAK_URL}/realms/{settings.KEYCLOAK_REALM}/protocol/openid-connect/logout")
    assert 'id_token_hint=id-token-value' in res.url
    assert 'post_logout_redirect_uri=' in res.url
    assert '_auth_user_id' not in client.session


# ==============================================================================
# Pemetaan peran SSO
# ==============================================================================

@pytest.mark.django_db
def test_username_containing_admin_is_not_promoted():
    payload = {'sub': str(uuid.uuid4()), 'preferred_username': 'staff_admin_tu', 'email': 'tu@smkn1rongga.sch.id',
               'realm_access': {'roles': ['guru']}}
    user = keycloak_auth.parse_and_sync_user({'id_token': _jwt(payload)})
    assert user.role == Role.GURU


@pytest.mark.django_db
def test_pengawas_claim_maps_to_guru():
    payload = {'sub': str(uuid.uuid4()), 'preferred_username': 'pengawas01', 'email': 'p01@smkn1rongga.sch.id',
               'realm_access': {'roles': ['pengawas']}}
    user = keycloak_auth.parse_and_sync_user({'id_token': _jwt(payload)})
    assert user.role == Role.GURU


@pytest.mark.django_db
def test_sso_cannot_take_over_local_superuser():
    User.objects.create_superuser(username='root', email='root@smkn1rongga.sch.id', password='x-Strong-1')
    payload = {'sub': str(uuid.uuid4()), 'preferred_username': 'root', 'email': 'root@smkn1rongga.sch.id',
               'realm_access': {'roles': ['guru']}}
    with pytest.raises(ValueError):
        keycloak_auth.parse_and_sync_user({'id_token': _jwt(payload)})


# ==============================================================================
# Webhook
# ==============================================================================

def _webhook(payload, key=None):
    request = RequestFactory().post('/api/webhook/sync/', data=json.dumps(payload), content_type='application/json',
                                    HTTP_X_API_KEY=key if key is not None else settings.WEBHOOK_SECRET_KEY)
    return WebhookSyncView.as_view()(request)


@pytest.mark.django_db
def test_webhook_rejects_wrong_key():
    assert _webhook({'type': 'staff', 'data': {'email': 'x@y.z'}}, key='salah').status_code == 401


@pytest.mark.django_db
def test_webhook_staff_cannot_create_admin_or_password():
    res = _webhook({'type': 'staff', 'data': {'email': 'kepala@smkn1rongga.sch.id', 'fullName': 'Kepala', 'ptkType': 'Kepala Sekolah admin'}})

    assert res.status_code == 200
    user = User.objects.get(email='kepala@smkn1rongga.sch.id')
    assert user.role == Role.GURU
    assert user.has_usable_password() is False
    assert user.is_staff is False


@pytest.mark.django_db
def test_webhook_does_not_change_existing_role():
    existing = User.objects.create_user(username='kurikulum_a', email='kur@smkn1rongga.sch.id', role=Role.KURIKULUM)

    _webhook({'type': 'staff', 'data': {'email': 'kur@smkn1rongga.sch.id', 'fullName': 'Bu Kurikulum', 'ptkType': 'guru'}})

    existing.refresh_from_db()
    assert existing.role == Role.KURIKULUM


@pytest.mark.django_db
def test_webhook_staff_delete_deactivates_instead_of_deleting():
    user = User.objects.create_user(username='guru_pindah', email='pindah@smkn1rongga.sch.id', role=Role.GURU)
    teacher = Teacher.objects.create(user=user, full_name='Guru Pindah', email='pindah@smkn1rongga.sch.id')

    _webhook({'action': 'delete', 'type': 'staff', 'data': {'email': 'pindah@smkn1rongga.sch.id'}})

    user.refresh_from_db()
    assert Teacher.objects.filter(pk=teacher.pk).exists()
    assert user.is_active is False


@pytest.mark.django_db
def test_webhook_student_delete_deactivates_login():
    user = User.objects.create_user(username='2425001', nis='2425001', role=Role.SISWA)
    Student.objects.create(user=user, nis='2425001', full_name='Siswa Keluar')

    _webhook({'action': 'delete', 'type': 'student', 'data': {'nis': '2425001'}})

    user.refresh_from_db()
    assert user.is_active is False
    assert Student.objects.get(nis='2425001').status == 'keluar'


@pytest.mark.django_db
def test_webhook_student_status_is_normalized():
    _webhook({'type': 'student', 'data': {'nis': '2425002', 'nama_siswa': 'Siswa Baru', 'status': 'ACTIVE'}})
    assert Student.objects.get(nis='2425002').status == 'aktif'
    assert User.objects.get(username='2425002').has_usable_password() is False


# ==============================================================================
# XSS & upload
# ==============================================================================

def test_question_card_does_not_mark_option_text_safe():
    with open(settings.BASE_DIR / 'templates/exam_engine/partials/question_card.html', encoding='utf-8') as fh:
        assert '|safe' not in fh.read()


@pytest.mark.parametrize('path', [
    'templates/questions/bank_soal.html',
    'templates/questions/partials/question_form_modal.html',
    'templates/master_data/import_students.html',
])
def test_json_in_script_blocks_uses_json_script(path):
    with open(settings.BASE_DIR / path, encoding='utf-8') as fh:
        assert '|safe' not in fh.read()


def _png_bytes():
    from PIL import Image
    buf = io.BytesIO()
    Image.new('RGB', (4, 4), 'orange').save(buf, format='PNG')
    return buf.getvalue()


@pytest.mark.django_db
def test_settings_upload_rejects_html_disguised_as_image(client, tmp_path, settings):
    settings.MEDIA_ROOT = tmp_path
    admin = User.objects.create_user(username='admin_upload', role=Role.ADMIN)
    client.force_login(admin)
    evil = SimpleUploadedFile('logo.html', b'<script>alert(1)</script>', content_type='text/html')

    client.post(reverse('reports:settings'), {'file_logo_left': evil})

    assert not list(tmp_path.rglob('*.html'))


@pytest.mark.django_db
def test_settings_upload_accepts_png(client, tmp_path, settings):
    settings.MEDIA_ROOT = tmp_path
    admin = User.objects.create_user(username='admin_upload_ok', role=Role.ADMIN)
    client.force_login(admin)
    logo = SimpleUploadedFile('logo.png', _png_bytes(), content_type='image/png')

    client.post(reverse('reports:settings'), {'file_logo_left': logo})

    saved = list(tmp_path.rglob('*.png'))
    assert len(saved) == 1


@pytest.mark.django_db
def test_settings_post_forbidden_for_guru(client):
    guru = User.objects.create_user(username='guru_settings', role=Role.GURU)
    client.force_login(guru)
    from apps.core.models import SchoolSetting
    before = SchoolSetting.get_settings().school_name

    client.post(reverse('reports:settings'), {'school_name': 'Diretas Guru'})

    assert SchoolSetting.get_settings().school_name == before

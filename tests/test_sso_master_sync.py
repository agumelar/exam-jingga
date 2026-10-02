import json
import uuid
import pytest
from unittest.mock import patch, MagicMock
from django.urls import reverse
from django.test import RequestFactory
from django.contrib.auth import get_user_model
from apps.accounts.models import Role
from apps.accounts.services.keycloak_auth import (
    get_authorization_url,
    determine_user_role,
    parse_and_sync_user,
    get_m2m_access_token,
    generate_pkce_pair
)
from apps.master_data.models import Student, Teacher, Major, ClassRoom
from apps.master_data.services.openapi_sync import MasterDataSyncService
from apps.master_data.views import WebhookSyncView

User = get_user_model()


@pytest.mark.django_db
def test_sso_pkce_and_auth_url():
    verifier, challenge = generate_pkce_pair()
    assert len(verifier) == 64
    assert len(challenge) > 0

    auth_url = get_authorization_url(
        redirect_uri='https://exam.smkn1rongga.sch.id/auth/callback/',
        state='test_state_123',
        code_challenge=challenge
    )
    assert 'prompt=login' in auth_url
    assert 'code_challenge_method=S256' in auth_url
    assert 'client_id=exam-jingga' in auth_url
    assert 'scope=openid+profile+email+roles' in auth_url or 'scope=openid%20profile%20email%20roles' in auth_url


def test_determine_user_role_mappings():
    # 1. Student with student role
    role1 = determine_user_role({'realm_access': {'roles': ['student']}}, '242510001', '242510001@smkn1rongga.sch.id')
    assert role1 == Role.SISWA

    # 2. PTK / Teacher with ptk role
    role2 = determine_user_role({'realm_access': {'roles': ['ptk']}}, '199001012022011001', 'guru@smkn1rongga.sch.id')
    assert role2 == Role.GURU

    # 3. Kurikulum
    role3 = determine_user_role({'realm_access': {'roles': ['ptk', 'kurikulum']}}, 'kurikulum_user', 'kurikulum@smkn1rongga.sch.id')
    assert role3 == Role.KURIKULUM

    # 4. Admin
    role4 = determine_user_role({'realm_access': {'roles': ['admin']}}, 'admin_user', 'admin@smkn1rongga.sch.id')
    assert role4 == Role.ADMIN


@pytest.mark.django_db
def test_parse_and_sync_user_links_student():
    student_id = uuid.uuid4()
    major = Major.objects.create(code='RPL', name='Rekayasa Perangkat Lunak')
    classroom = ClassRoom.objects.create(name='XII RPL 1', level=12, major=major)
    student = Student.objects.create(
        id=student_id,
        nis='242519999',
        full_name='Budi Santoso',
        class_room=classroom,
        major=major,
        status='aktif'
    )

    import base64

    jwt_payload = {
        "sub": str(student_id),
        "preferred_username": "242519999",
        "name": "Budi Santoso Updated",
        "email": "242519999@student.smkn1rongga.sch.id",
        "realm_access": {"roles": ["student"]}
    }
    payload_b64 = base64.urlsafe_b64encode(json.dumps(jwt_payload).encode()).decode().rstrip('=')

    tokens = {
        'id_token': f"eyJhbGciOiJIUzI1NiJ9.{payload_b64}.signature"
    }

    user = parse_and_sync_user(tokens)
    assert user.username == '242519999'
    assert user.role == Role.SISWA
    assert user.full_name == 'Budi Santoso Updated'

    student.refresh_from_db()
    assert student.user == user
    assert student.sso_id == student_id


@pytest.mark.django_db
def test_m2m_token_and_paginated_students_sync():
    service = MasterDataSyncService(base_url='https://mock-data.smkn1rongga.sch.id')

    mock_student_payload = {
        'data': [
            {
                'id': str(uuid.uuid4()),
                'fullName': 'Dewi Sartika',
                'nis': '242510099',
                'status': 'ACTIVE',
                'currentClass': {
                    'id': str(uuid.uuid4()),
                    'code': 'XI-RPL-1',
                    'name': 'XI RPL 1',
                    'gradeLevel': 11
                }
            }
        ],
        'meta': {
            'total': 1,
            'page': 1,
            'pageSize': 50,
            'pageCount': 1
        }
    }

    with patch('requests.post') as mock_post, patch('requests.get') as mock_get:
        # Mock Keycloak M2M token request
        mock_token_resp = MagicMock()
        mock_token_resp.ok = True
        mock_token_resp.status_code = 200
        mock_token_resp.json.return_value = {'access_token': 'mock_bearer_token_xyz'}
        mock_post.return_value = mock_token_resp

        # Mock Data Hub API response
        mock_get_resp = MagicMock()
        mock_get_resp.ok = True
        mock_get_resp.status_code = 200
        mock_get_resp.json.return_value = mock_student_payload
        mock_get.return_value = mock_get_resp

        token = get_m2m_access_token()
        assert token == 'mock_bearer_token_xyz'

        res = service.sync_students(bearer_token=token)
        assert res['success'] is True
        assert res['count'] == 1

        synced_student = Student.objects.filter(nis='242510099').first()
        assert synced_student is not None
        assert synced_student.full_name == 'Dewi Sartika'
        assert synced_student.class_room.name == 'XI RPL 1'
        assert synced_student.class_room.level == 11


@pytest.mark.django_db
def test_webhook_sync_view_create_and_update():
    factory = RequestFactory()
    view = WebhookSyncView.as_view()

    # 1. Unauthorized request without key
    req_unauth = factory.post('/api/webhook/sync/', data={}, content_type='application/json')
    resp_unauth = view(req_unauth)
    assert resp_unauth.status_code == 401

    # 2. Valid Student Webhook Push
    major = Major.objects.create(code='TKRO', name='Teknik Kendaraan Ringan')
    classroom = ClassRoom.objects.create(name='X TKRO 2', level=10, major=major)

    student_data = {
        'action': 'create',
        'type': 'student',
        'data': {
            'id': str(uuid.uuid4()),
            'nis': '242510777',
            'nama_siswa': 'Rahmat Hidayat',
            'kelas_id': str(classroom.id),
            'status_siswa': 'aktif',
            'email': '242510777@student.smkn1rongga.sch.id'
        }
    }

    req_valid = factory.post(
        '/api/webhook/sync/',
        data=json.dumps(student_data),
        content_type='application/json',
        HTTP_X_API_KEY='exam-jingga-webhook-secret-key-2026'
    )
    resp_valid = view(req_valid)
    assert resp_valid.status_code == 200
    res_json = json.loads(resp_valid.content)
    assert res_json.get('status') == 'success'

    # Verify student was created
    created_student = Student.objects.filter(nis='242510777').first()
    assert created_student is not None
    assert created_student.full_name == 'Rahmat Hidayat'
    assert created_student.class_room == classroom

    # 3. Valid Staff Webhook Push
    staff_data = {
        'action': 'update',
        'type': 'staff',
        'data': {
            'id': str(uuid.uuid4()),
            'fullName': 'Siti Rohmah, S.Pd.',
            'nip': '199505052024012001',
            'email': 'siti.rohmah@smkn1rongga.sch.id',
            'ptkType': 'Guru Mapel'
        }
    }

    req_staff = factory.post(
        '/api/webhook/sync/',
        data=json.dumps(staff_data),
        content_type='application/json',
        HTTP_X_API_KEY='exam-jingga-webhook-secret-key-2026'
    )
    resp_staff = view(req_staff)
    assert resp_staff.status_code == 200

    created_teacher = Teacher.objects.filter(email='siti.rohmah@smkn1rongga.sch.id').first()
    assert created_teacher is not None
    assert created_teacher.full_name == 'Siti Rohmah, S.Pd.'
    assert created_teacher.user.is_teacher is True

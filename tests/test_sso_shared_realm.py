"""Realm Keycloak `sekolah` dipakai bersama ASIK: peran admin Exam hanya dari client role `exam-jingga`."""
import base64
import json
import uuid

import pytest

from apps.accounts.models import Role
from apps.accounts.services import keycloak_auth

ADMIN_ROLES = {Role.ADMIN, Role.KURIKULUM, Role.PLATFORM_ADMIN, Role.DATA_ADMIN}


def _jwt(payload):
    body = base64.urlsafe_b64encode(json.dumps(payload).encode()).decode().rstrip('=')
    return f"eyJhbGciOiJub25lIn0.{body}.sig"


def _identity(username='tu_asik', email='tu@smkn1rongga.sch.id'):
    return {'sub': str(uuid.uuid4()), 'preferred_username': username, 'email': email, 'name': 'Petugas TU'}


@pytest.mark.django_db
@pytest.mark.parametrize('realm_role', ['admin', 'administrator', 'superadmin', 'kurikulum', 'platform_admin', 'data_admin'])
def test_realm_role_from_other_app_does_not_grant_exam_admin(realm_role):
    payload = {**_identity(), 'realm_access': {'roles': [realm_role]}}
    user = keycloak_auth.parse_and_sync_user({'id_token': _jwt(payload)})
    assert user.role not in ADMIN_ROLES
    assert user.is_staff is False


@pytest.mark.django_db
def test_admin_role_of_another_client_is_ignored():
    payload = {**_identity(), 'resource_access': {'asik': {'roles': ['admin']}}}
    user = keycloak_auth.parse_and_sync_user({'id_token': _jwt(payload)})
    assert user.role not in ADMIN_ROLES


@pytest.mark.django_db
def test_exam_client_role_in_id_token_grants_kurikulum():
    payload = {**_identity('kurikulum_smk', 'kurikulum@smkn1rongga.sch.id'),
               'resource_access': {'exam-jingga': {'roles': ['kurikulum']}}}
    user = keycloak_auth.parse_and_sync_user({'id_token': _jwt(payload)})
    assert user.role == Role.KURIKULUM


@pytest.mark.django_db
def test_exam_client_role_read_from_access_token():
    # Mapper role bawaan Keycloak hanya mengisi access token, bukan ID token
    identity = _identity('admin_exam', 'admin.exam@smkn1rongga.sch.id')
    access = {'sub': identity['sub'], 'resource_access': {'exam-jingga': {'roles': ['admin']}}}
    user = keycloak_auth.parse_and_sync_user({'id_token': _jwt(identity), 'access_token': _jwt(access)})
    assert user.role == Role.ADMIN
    assert user.is_staff is True


@pytest.mark.django_db
def test_realm_student_role_read_from_access_token():
    # Tanpa role dari access token, domain email ini akan dipetakan ke guru
    identity = _identity('siswa_tanpa_nis', 'siswa@smkn1rongga.sch.id')
    access = {'sub': identity['sub'], 'realm_access': {'roles': ['siswa']}}
    user = keycloak_auth.parse_and_sync_user({'id_token': _jwt(identity), 'access_token': _jwt(access)})
    assert user.role == Role.SISWA


@pytest.mark.django_db
def test_realm_teacher_role_still_maps_to_guru():
    payload = {**_identity('guru_asik', 'guru.asik@contoh.test'), 'realm_access': {'roles': ['guru']}}
    user = keycloak_auth.parse_and_sync_user({'id_token': _jwt(payload)})
    assert user.role == Role.GURU

"""Sinkron data pusat: client Keycloak khusus sinkron, dan kegagalan tidak boleh dilaporkan sebagai berhasil."""
from unittest.mock import MagicMock, patch

import pytest
from django.contrib.auth import get_user_model
from django.test import override_settings
from django.urls import reverse

from apps.accounts.services import keycloak_auth
from apps.master_data.models import Student
from apps.master_data.services.openapi_sync import MasterDataSyncService, SyncSourceError

User = get_user_model()
SYNC_SETTINGS = {'DATA_MASTER_CLIENT_ID': 'exam-jingga-sync', 'DATA_MASTER_CLIENT_SECRET': 'rahasia-uji'}


def _response(status=200, payload=None):
    res = MagicMock()
    res.ok = status < 400
    res.status_code = status
    res.json.return_value = payload if payload is not None else {}
    if status >= 400:
        res.raise_for_status.side_effect = Exception(f'{status} Client Error')
    return res


@override_settings(**SYNC_SETTINGS)
def test_m2m_token_uses_dedicated_sync_client():
    with patch.object(keycloak_auth.requests, 'post', return_value=_response(200, {'access_token': 'tok'})) as post:
        assert keycloak_auth.get_m2m_access_token() == 'tok'
    sent = post.call_args.kwargs['data']
    assert (sent['grant_type'], sent['client_id'], sent['client_secret']) == \
        ('client_credentials', 'exam-jingga-sync', 'rahasia-uji')


@override_settings(DATA_MASTER_CLIENT_ID='exam-jingga-sync', DATA_MASTER_CLIENT_SECRET='')
def test_m2m_token_refuses_without_secret():
    with patch.object(keycloak_auth.requests, 'post') as post:
        with pytest.raises(ValueError, match='DATA_MASTER_CLIENT_SECRET'):
            keycloak_auth.get_m2m_access_token()
    post.assert_not_called()


@pytest.fixture
def active_students(db):
    return [Student.objects.create(nis=f'77{i}', full_name=f'Siswa {i}', status='aktif') for i in range(3)]


@pytest.mark.django_db
def test_token_failure_stops_sync(active_students):
    with patch('apps.master_data.services.openapi_sync.get_m2m_access_token', side_effect=ValueError('ditolak')), \
            patch('apps.master_data.services.openapi_sync.requests.get') as get:
        with pytest.raises(SyncSourceError, match='ditolak'):
            MasterDataSyncService().sync_students()
    get.assert_not_called()
    assert Student.objects.filter(status='aktif').count() == 3


@pytest.mark.django_db
def test_unauthorized_api_stops_sync(active_students):
    with patch('apps.master_data.services.openapi_sync.get_m2m_access_token', return_value='tok'), \
            patch('apps.master_data.services.openapi_sync.requests.get', return_value=_response(401)):
        with pytest.raises(SyncSourceError, match='401'):
            MasterDataSyncService().sync_students()
    assert Student.objects.filter(status='aktif').count() == 3


@pytest.mark.django_db
def test_empty_student_feed_stops_sync(active_students):
    empty = _response(200, {'data': [], 'meta': {'pageCount': 1}})
    with patch('apps.master_data.services.openapi_sync.get_m2m_access_token', return_value='tok'), \
            patch('apps.master_data.services.openapi_sync.requests.get', return_value=empty):
        with pytest.raises(SyncSourceError, match='0 siswa'):
            MasterDataSyncService().sync_students()


@pytest.mark.django_db
def test_staff_fetch_failure_stops_sync_without_legacy_fallback():
    service = MasterDataSyncService()
    with patch.object(service, 'fetch_master_api', side_effect=PermissionError('401')) as fetch:
        with pytest.raises(SyncSourceError):
            service.sync_teachers()
    assert [c.args[0] for c in fetch.call_args_list] == ['/v1/staff']


@pytest.mark.django_db
def test_sync_view_reports_failure(client):
    client.force_login(User.objects.create_user(username='admin_sync', role='admin', is_staff=True))
    with patch.object(MasterDataSyncService, 'sync_students', side_effect=SyncSourceError('Token ditolak Keycloak')):
        res = client.post(reverse('master_data:sync'), {'type': 'students'}, HTTP_HX_REQUEST='true')
    html = res.content.decode()
    assert 'Token ditolak Keycloak' in html
    assert 'Sinkronisasi Berhasil' not in html


# ==============================================================================
# Paginasi data pusat (meta.totalPages, baris ganda, kelengkapan)
# ==============================================================================

def _row(i):
    return {'id': f'id-{i}', 'nis': f'88{i}', 'fullName': f'Siswa {i}', 'status': 'ACTIVE'}


def _pages(pages, total, meta_key='totalPages'):
    """Tiruan requests.get yang mengembalikan halaman sesuai params['page']."""
    def fake_get(url, params=None, headers=None, timeout=None):
        page = params['page']
        return _response(200, {'data': pages[page - 1], 'meta': {'page': page, meta_key: len(pages), 'total': total}})
    return fake_get


def _fetch(fake_get):
    service = MasterDataSyncService()
    with patch.object(service, '_get_headers', return_value={}), \
            patch('apps.master_data.services.openapi_sync.requests.get', side_effect=fake_get) as get:
        return service.fetch_all_students_paginated(), get


def test_reads_every_page_from_total_pages():
    rows, get = _fetch(_pages([[_row(1)], [_row(2)], [_row(3)]], total=3))
    assert [r['nis'] for r in rows] == ['881', '882', '883']
    assert get.call_count == 3


def test_legacy_page_count_meta_still_supported():
    rows, _ = _fetch(_pages([[_row(1)], [_row(2)]], total=2, meta_key='pageCount'))
    assert len(rows) == 2


def test_duplicate_rows_across_pages_are_merged():
    rows, _ = _fetch(_pages([[_row(1), _row(2)], [_row(2), _row(3)]], total=3))
    assert sorted(r['id'] for r in rows) == ['id-1', 'id-2', 'id-3']


def test_unstable_pagination_aborts_when_rows_are_missing():
    # API melaporkan 4 siswa, tapi paginasi mengulang id-2 dan tidak pernah mengirim id-4
    with pytest.raises(SyncSourceError, match='3 siswa unik dari 4'):
        _fetch(_pages([[_row(1), _row(2)], [_row(2), _row(3)]], total=4))


def test_requests_large_pages():
    _, get = _fetch(_pages([[_row(1)]], total=1))
    assert get.call_args.kwargs['params']['pageSize'] == 1000


# ==============================================================================
# Sinkron guru dimatikan sampai ada kunci NIP yang tertaut ke akun SSO guru
# ==============================================================================

@pytest.mark.django_db
def test_teacher_sync_button_is_refused(client):
    client.force_login(User.objects.create_user(username='admin_sync2', role='admin', is_staff=True))
    with patch.object(MasterDataSyncService, 'sync_teachers') as sync_teachers:
        res = client.post(reverse('master_data:sync'), {'type': 'teachers'}, HTTP_HX_REQUEST='true')
    sync_teachers.assert_not_called()
    assert 'Sinkron guru dinonaktifkan' in res.content.decode()


@pytest.mark.django_db
def test_sync_all_skips_teachers():
    service = MasterDataSyncService()
    feed = [{'id': 'id-1', 'nis': '5501', 'fullName': 'Siswa', 'status': 'ACTIVE'}]
    with patch.object(MasterDataSyncService, 'fetch_all_students_paginated', return_value=feed), \
            patch.object(MasterDataSyncService, 'sync_teachers') as sync_teachers:
        res = service.sync_all()
    sync_teachers.assert_not_called()
    assert res['students_count'] == 1
    assert 'guru tidak disinkron' in res['message']

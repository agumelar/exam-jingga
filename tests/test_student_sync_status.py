"""Data Siswa: jumlah selalu dihitung dari data (aktif dan tidak aktif terpisah), dan sinkron data pusat
berjalan otomatis tiap malam dengan catatan sinkron terakhir yang terlihat di halaman."""
from pathlib import Path
from unittest.mock import patch

import pytest
from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.urls import reverse

from apps.master_data.models import ClassRoom, MasterSyncLog, Student
from apps.master_data.services.openapi_sync import MasterDataSyncService, SyncSourceError

User = get_user_model()
ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture
def admin_client(client, db):
    client.force_login(User.objects.create_superuser(username='admin_siswa', email='a@x.id', password='x-Strong-1'))
    return client


@pytest.fixture
def students(db):
    kelas = ClassRoom.objects.create(name='11 RPL-1', level=11)
    Student.objects.create(nis='1001', full_name='Siswa Aktif Satu', class_room=kelas)
    Student.objects.create(nis='1002', full_name='Siswa Aktif Dua', class_room=kelas)
    Student.objects.create(nis='1003', full_name='Siswa Sudah Keluar', class_room=kelas, status='keluar')
    return kelas


def _page(client, query=''):
    return client.get(reverse('master_data:students') + query).content.decode()


@pytest.mark.django_db
def test_header_counts_active_and_inactive_separately(admin_client, students):
    html = _page(admin_client)
    assert '2 siswa aktif' in html
    assert '1 tidak aktif' in html
    assert 'Total Terdaftar' not in html


@pytest.mark.django_db
def test_counts_follow_the_data(admin_client, students):
    Student.objects.create(nis='1004', full_name='Siswa Baru', class_room=students)
    Student.objects.filter(nis='1001').update(status='keluar')
    html = _page(admin_client)
    assert '2 siswa aktif' in html
    assert '2 tidak aktif' in html


@pytest.mark.django_db
def test_list_shows_active_students_by_default(admin_client, students):
    html = _page(admin_client)
    assert 'Siswa Aktif Satu' in html and 'Siswa Aktif Dua' in html
    assert 'Siswa Sudah Keluar' not in html


@pytest.mark.django_db
def test_status_filter_shows_inactive_or_all(admin_client, students):
    inactive = _page(admin_client, '?status=nonaktif')
    assert 'Siswa Sudah Keluar' in inactive and 'Siswa Aktif Satu' not in inactive
    everyone = _page(admin_client, '?status=semua')
    assert all(name in everyone for name in ('Siswa Aktif Satu', 'Siswa Aktif Dua', 'Siswa Sudah Keluar'))


@pytest.mark.django_db
def test_no_fixed_student_numbers_in_page(admin_client, students):
    html = _page(admin_client)
    assert '722' not in html
    assert 'Semua Kelas (' not in html


def _ok_result(**extra):
    return {'success': True, 'students_count': 2, 'students_deactivated': 1, 'message': 'ok', **extra}


@pytest.mark.django_db
def test_button_sync_is_logged_and_shown(admin_client, students):
    with patch.object(MasterDataSyncService, 'sync_students',
                      return_value={'success': True, 'count': 2, 'deactivated': 1, 'message': 'ok'}):
        admin_client.post(reverse('master_data:sync'), {'type': 'students'}, HTTP_HX_REQUEST='true')

    log = MasterSyncLog.objects.get()
    assert (log.source, log.success, log.students_active, log.deactivated) == ('tombol', True, 2, 1)
    html = _page(admin_client)
    assert 'Sinkron terakhir' in html
    assert 'lewat tombol' in html


@pytest.mark.django_db
def test_nightly_command_syncs_and_logs_as_automatic(students):
    with patch.object(MasterDataSyncService, 'sync_all', return_value=_ok_result()) as sync_all:
        call_command('sync_master_data', '--otomatis')
    sync_all.assert_called_once()
    log = MasterSyncLog.objects.get()
    assert (log.source, log.success, log.deactivated) == ('otomatis', True, 1)


@pytest.mark.django_db
def test_failed_nightly_sync_is_logged_and_visible(admin_client, students):
    with patch.object(MasterDataSyncService, 'sync_all', side_effect=SyncSourceError('Data pusat mengembalikan 0 siswa')):
        with pytest.raises(SystemExit):
            call_command('sync_master_data', '--otomatis')
    log = MasterSyncLog.objects.get()
    assert log.success is False and '0 siswa' in log.message
    html = _page(admin_client)
    assert 'gagal' in html and 'Data pusat mengembalikan 0 siswa' in html


def test_nightly_timer_runs_at_half_past_midnight_and_is_installed():
    timer = (ROOT / 'scripts/exam_jingga_sync.timer').read_text(encoding='utf-8')
    service = (ROOT / 'scripts/exam_jingga_sync.service').read_text(encoding='utf-8')
    deploy = (ROOT / 'scripts/deploy_vps_dath.sh').read_text(encoding='utf-8')
    assert 'OnCalendar=*-*-* 00:30:00 Asia/Jakarta' in timer
    assert 'Persistent=false' in timer, 'sinkron yang terlewat tidak boleh menyusul di jam sekolah'
    assert 'sync_master_data --otomatis' in service
    assert 'exam_jingga_sync.timer' in deploy and 'exam_jingga_sync.service' in deploy

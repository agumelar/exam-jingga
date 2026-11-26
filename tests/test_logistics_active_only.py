"""Logistik ruang: hanya siswa aktif yang dihitung, dicetak, dan diekspor. Pembagian ruang milik siswa
yang sudah keluar tidak boleh ikut ke kartu ujian, daftar hadir, atau Excel, dan dibersihkan saat kocok."""
import io

import pytest
from django.contrib.auth import get_user_model
from openpyxl import load_workbook

from apps.master_data.models import ClassRoom, Student
from apps.reports.models import StudentLogistic
from apps.reports.utils import auto_distribute_logistics

User = get_user_model()


@pytest.fixture
def admin_client(client, db):
    client.force_login(User.objects.create_superuser(username='admin_logistik', email='l@x.id', password='x-Strong-1'))
    return client


@pytest.fixture
def placed(db):
    kelas = ClassRoom.objects.create(name='11 RPL-1', level=11)
    aktif = Student.objects.create(nis='2001', full_name='Siswa Masih Aktif', class_room=kelas)
    keluar = Student.objects.create(nis='2002', full_name='Siswa Sudah Keluar', class_room=kelas, status='keluar')
    Student.objects.create(nis='2003', full_name='Siswa Belum Dapat Ruang', class_room=kelas)
    StudentLogistic.objects.create(student=aktif, room_name='RUANG 01', session_name='SESI 1')
    StudentLogistic.objects.create(student=keluar, room_name='RUANG 01', session_name='SESI 1')
    return kelas


@pytest.mark.django_db
def test_counts_use_active_students_only(admin_client, placed):
    context = admin_client.get('/logistics/').context
    assert context['total_active_students'] == 2
    assert context['allocated_count'] == 1
    assert context['unassigned_count'] == 1


@pytest.mark.django_db
@pytest.mark.parametrize('url', ['/logistics/', '/exam-cards/', '/attendance-list/', '/attendance-list/?type=door'])
def test_pages_list_only_active_students(admin_client, placed, url):
    html = admin_client.get(url).content.decode()
    assert 'Siswa Masih Aktif' in html
    assert 'Siswa Sudah Keluar' not in html


@pytest.mark.django_db
def test_attendance_count_excludes_students_who_left(admin_client, placed):
    assert admin_client.get('/attendance-list/').context['students_count'] == 1


@pytest.mark.django_db
def test_excel_export_lists_only_active_students(admin_client, placed):
    response = admin_client.get('/reports/logistics/export/')
    ws = load_workbook(io.BytesIO(response.content)).active
    names = {str(cell.value) for row in ws.iter_rows() for cell in row if cell.value}
    assert '2001' in names, 'NIS siswa aktif'
    assert '2002' not in names, 'NIS siswa yang sudah keluar'


@pytest.mark.django_db
def test_shuffle_removes_rooms_of_students_who_left(placed):
    auto_distribute_logistics(levels=[11], room_count=1, capacity=10, sessions_count=1)
    assert not StudentLogistic.objects.filter(student__status='keluar').exists()
    assert StudentLogistic.objects.count() == 2

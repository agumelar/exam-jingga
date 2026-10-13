"""Fase 5 audit: master data dan bank soal (sinkron utuh, proteksi riwayat, import aman, soal terkunci)."""
import io
import uuid
from datetime import timedelta
from unittest.mock import MagicMock, patch

import openpyxl
import pytest
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import IntegrityError
from django.db.models import ProtectedError
from django.urls import reverse
from django.utils import timezone

from apps.accounts.models import Role
from apps.exam_engine.models import ExamSession
from apps.master_data.models import ClassRoom, Student, Subject, Teacher, TeacherAssignment
from apps.master_data.services.openapi_sync import MasterDataSyncService, SyncIncompleteError
from apps.questions.models import Question
from apps.schedules.models import Exam, ExamQuestion, Schedule

User = get_user_model()


def _students(n, cls=None):
    out = []
    for i in range(n):
        u = User.objects.create_user(username=f'ms{i}', nis=f'ms{i}', role=Role.SISWA)
        out.append(Student.objects.create(user=u, nis=f'ms{i}', full_name=f'S{i}', class_room=cls))
    return out


# ==============================================================================
# Sinkron data pusat
# ==============================================================================

@pytest.mark.django_db
def test_sync_deactivates_students_missing_from_source():
    cls = ClassRoom.objects.create(name='X MS 1', level=10)
    students = _students(4, cls)
    feed = [{'nis': s.nis, 'full_name': s.full_name, 'class_name': 'X MS 1', 'status': 'ACTIVE'} for s in students[:3]]

    MasterDataSyncService().sync_students(raw_students=feed)

    assert Student.objects.get(nis='ms3').status == 'keluar'
    assert User.objects.get(username='ms3').is_active is False
    assert Student.objects.get(nis='ms0').status == 'aktif'


@pytest.mark.django_db
def test_sync_skips_deactivation_when_feed_suspiciously_small():
    _students(10)
    MasterDataSyncService().sync_students(raw_students=[{'nis': 'ms0', 'full_name': 'S0', 'status': 'ACTIVE'}])
    assert Student.objects.filter(status='aktif').count() == 10


def test_paginated_fetch_failure_midway_aborts():
    first = MagicMock()
    first.json.return_value = {'data': [{'nis': '1'}], 'meta': {'pageCount': 3}}

    def fake_get(url, params=None, headers=None, timeout=None):
        if params['page'] == 1:
            return first
        raise ConnectionError('putus')

    service = MasterDataSyncService()
    with patch.object(service, '_get_headers', return_value={}), \
            patch('apps.master_data.services.openapi_sync.requests.get', side_effect=fake_get):
        with pytest.raises(SyncIncompleteError):
            service.fetch_all_students_paginated()


@pytest.mark.django_db
def test_staff_without_email_or_nip_is_skipped():
    MasterDataSyncService().sync_teachers(raw_staff=[{'full_name': 'Tanpa Kunci'}, {'full_name': 'Juga Tanpa Kunci'}])
    assert not Teacher.objects.exists()




# ==============================================================================
# Proteksi riwayat
# ==============================================================================

@pytest.mark.django_db
def test_deleting_student_with_results_is_blocked():
    cls = ClassRoom.objects.create(name='X MS 2', level=10)
    stu = _students(1, cls)[0]
    subject = Subject.objects.create(name='Mapel MS')
    exam = Exam.objects.create(subject=subject, title='UH', exam_type='UH', level=10)
    now = timezone.now()
    sch = Schedule.objects.create(exam=exam, class_room=cls, start_time=now, end_time=now + timedelta(hours=1), token='T')
    ExamSession.objects.create(student=stu, schedule=sch)
    with pytest.raises(ProtectedError):
        stu.delete()


@pytest.mark.django_db
def test_deleting_user_keeps_teacher_and_bank():
    u = User.objects.create_user(username='guru_hapus', role=Role.GURU)
    t = Teacher.objects.create(user=u, full_name='Guru Hapus', email='gh@x.id')
    u.delete()
    t.refresh_from_db()
    assert t.user is None


@pytest.mark.django_db
def test_assignment_is_unique():
    t = Teacher.objects.create(full_name='G', email='g@x.id')
    s = Subject.objects.create(name='M')
    c = ClassRoom.objects.create(name='X U 1', level=10)
    TeacherAssignment.objects.create(teacher=t, subject=s, class_room=c)
    with pytest.raises(IntegrityError):
        TeacherAssignment.objects.create(teacher=t, subject=s, class_room=c)


# ==============================================================================
# Import Excel
# ==============================================================================

def _xlsx(rows):
    wb = openpyxl.Workbook()
    ws = wb.active
    for r in rows:
        ws.append(r)
    buf = io.BytesIO()
    wb.save(buf)
    return SimpleUploadedFile('siswa.xlsx', buf.getvalue(),
                              content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')


@pytest.mark.django_db
def test_import_rejects_non_xlsx(client):
    client.force_login(User.objects.create_user(username='adm_imp', role=Role.ADMIN))
    bad = SimpleUploadedFile('siswa.csv', b'nis,nama,kelas', content_type='text/csv')
    client.post(reverse('import_siswa'), {'excel_file': bad})
    assert not Student.objects.exists()


@pytest.mark.django_db
def test_import_creates_students_without_local_password(client):
    ClassRoom.objects.create(name='X IMP 1', level=10)
    client.force_login(User.objects.create_user(username='adm_imp2', role=Role.ADMIN))
    client.post(reverse('import_siswa'), {'excel_file': _xlsx([['nis', 'nama', 'kelas'], ['5501', 'Ani', 'X IMP 1']])})
    assert User.objects.get(username='5501').has_usable_password() is False


@pytest.mark.django_db
def test_import_ignores_external_next(client):
    client.force_login(User.objects.create_user(username='adm_imp3', role=Role.ADMIN))
    res = client.post(reverse('import_siswa'), {'next': 'https://evil.example/'})
    assert res.url == reverse('import_siswa')


# ==============================================================================
# Bank soal
# ==============================================================================

@pytest.fixture
def bank(db):
    user = User.objects.create_user(username='guru_bank', role=Role.GURU)
    teacher = Teacher.objects.create(user=user, full_name='Guru Bank', email='gb@x.id')
    subject = Subject.objects.create(name='Mapel Bank')
    q = Question.objects.create(subject=subject, level=10, created_by=teacher, question_text='Asli',
                                option_a='a', option_b='b', option_c='c', option_d='d', option_e='e', correct_answer='A')
    exam = Exam.objects.create(teacher=teacher, subject=subject, title='UH Bank', exam_type='UH', level=10,
                               status='validated', target_question_count=1)
    return {'user': user, 'teacher': teacher, 'q': q, 'exam': exam}


def _edit_payload(q):
    return {'subject': q.subject_id, 'level': q.level, 'question_text': 'Diubah', 'option_a': 'a', 'option_b': 'b',
            'option_c': 'c', 'option_d': 'd', 'option_e': 'e', 'correct_answer': 'B', 'cp_code': ''}


@pytest.mark.django_db
def test_question_in_validated_exam_cannot_be_edited(client, bank):
    ExamQuestion.objects.create(exam=bank['exam'], question=bank['q'], order_number=1)
    client.force_login(bank['user'])
    res = client.post(reverse('questions:edit', args=[bank['q'].id]), _edit_payload(bank['q']), HTTP_HX_REQUEST='true')
    bank['q'].refresh_from_db()
    assert res.status_code == 409
    assert bank['q'].question_text == 'Asli'


@pytest.mark.django_db
def test_question_in_pending_exam_can_be_edited(client, bank):
    Exam.objects.filter(pk=bank['exam'].pk).update(status='pending_selection')
    ExamQuestion.objects.create(exam=bank['exam'], question=bank['q'], order_number=1)
    client.force_login(bank['user'])
    client.post(reverse('questions:edit', args=[bank['q'].id]), _edit_payload(bank['q']), HTTP_HX_REQUEST='true')
    bank['q'].refresh_from_db()
    assert bank['q'].question_text == 'Diubah'


@pytest.mark.django_db
def test_question_in_exam_cannot_be_deleted(client, bank):
    ExamQuestion.objects.create(exam=bank['exam'], question=bank['q'], order_number=1)
    client.force_login(bank['user'])
    res = client.post(reverse('questions:delete', args=[bank['q'].id]), HTTP_HX_REQUEST='true')
    assert res.status_code == 409
    assert Question.objects.filter(pk=bank['q'].pk).exists()


@pytest.mark.django_db
def test_unused_question_can_be_deleted(client, bank):
    client.force_login(bank['user'])
    client.post(reverse('questions:delete', args=[bank['q'].id]), HTTP_HX_REQUEST='true')
    assert not Question.objects.filter(pk=bank['q'].pk).exists()


@pytest.mark.django_db
def test_per_page_is_clamped(client, bank):
    client.force_login(bank['user'])
    assert client.get(reverse('questions:bank_soal'), {'per_page': 'abc'}).status_code == 200
    assert client.get(reverse('questions:bank_soal'), {'per_page': '100000'}).status_code == 200

"""Arsip paket ujian (sehari-hari) dan hapus permanen (admin, dengan backup otomatis lebih dulu)."""
from datetime import timedelta
from unittest.mock import patch

import pytest
from django.contrib.auth import get_user_model
from django.test import override_settings
from django.urls import reverse
from django.utils import timezone

from apps.accounts.models import Role
from apps.exam_engine.models import ExamSession, StudentAnswer
from apps.master_data.models import ClassRoom, Student, Subject, Teacher, TeacherAssignment
from apps.questions.models import Question
from apps.schedules import archive
from apps.schedules.models import Exam, ExamPurgeLog, ExamQuestion, Schedule

User = get_user_model()
HX = {'HTTP_HX_REQUEST': 'true'}


@pytest.fixture
def world(db):
    cls = ClassRoom.objects.create(name='10 Uji', level=10)
    subject = Subject.objects.create(name='Mapel Arsip')
    gu = User.objects.create_user(username='guru_arsip', role=Role.GURU)
    teacher = Teacher.objects.create(user=gu, full_name='Guru Arsip', email='ga@x.id')
    other_u = User.objects.create_user(username='guru_lain', role=Role.GURU)
    other = Teacher.objects.create(user=other_u, full_name='Guru Lain', email='gl@x.id')
    TeacherAssignment.objects.create(teacher=teacher, subject=subject, class_room=cls)
    q = Question.objects.create(subject=subject, level=10, created_by=teacher, question_text='Soal', option_a='a',
                                option_b='b', option_c='c', option_d='d', option_e='e', correct_answer='A')
    su = User.objects.create_user(username='9999000001', nis='9999000001', role=Role.SISWA)
    student = Student.objects.create(user=su, nis='9999000001', full_name='Siswa Uji 1', class_room=cls, status='aktif')
    admin = User.objects.create_user(username='admin-exam', role=Role.ADMIN, is_staff=True)
    kurikulum = User.objects.create_user(username='kurikulum', role=Role.KURIKULUM, is_staff=True)

    def make(title, exam_type='UH', hours_ago=3, session_status='finished'):
        exam = Exam.objects.create(teacher=teacher, subject=subject, title=title, exam_type=exam_type, level=10,
                                   status='validated', duration=30, target_question_count=1, token='ARS001')
        ExamQuestion.objects.create(exam=exam, question=q, order_number=1)
        start = timezone.now() - timedelta(hours=hours_ago)
        sch = Schedule.objects.create(exam=exam, class_room=cls, teacher=teacher, start_time=start,
                                      end_time=start + timedelta(minutes=30), token='ARS001', teacher_quota=1)
        if session_status:
            sess = ExamSession.objects.create(student=student, schedule=sch, status=session_status, score=100,
                                              started_at=start, finished_at=start + timedelta(minutes=30))
            StudentAnswer.objects.create(session=sess, question=q, order_number=1, chosen_answer='A', is_correct=True)
        return exam, sch

    return locals()


def _action(client, schedule, action, data=None):
    return client.post(reverse('schedules:action', kwargs={'pk': schedule.id, 'action': action}), data or {}, **HX)


# ==============================================================================
# Arsip
# ==============================================================================

@pytest.mark.django_db
def test_teacher_archives_own_finished_uh(client, world):
    exam, sch = world['make']('UH Lama')
    client.force_login(world['gu'])

    _action(client, sch, 'archive')

    exam.refresh_from_db()
    assert exam.archived_at is not None and exam.archived_by == world['gu']
    default = client.get(reverse('schedules:list'), {'date_filter': 'Semua'}).content.decode()
    assert 'UH Lama' not in default
    archived = client.get(reverse('schedules:list'), {'date_filter': 'Semua', 'status': 'arsip'}).content.decode()
    assert 'UH Lama' in archived


@pytest.mark.django_db
def test_archive_refused_before_schedule_ends(client, world):
    exam, sch = world['make']('UH Berjalan', hours_ago=0, session_status=None)
    client.force_login(world['gu'])
    res = _action(client, sch, 'archive')
    exam.refresh_from_db()
    assert exam.archived_at is None
    assert res.status_code == 409


@pytest.mark.django_db
def test_archive_refused_while_student_in_progress(client, world):
    exam, sch = world['make']('UH Tertinggal', session_status='active')
    client.force_login(world['admin'])
    _action(client, sch, 'archive')
    exam.refresh_from_db()
    assert exam.archived_at is None


@pytest.mark.django_db
def test_teacher_cannot_archive_official_exam_but_kurikulum_can(client, world):
    exam, sch = world['make']('PTS Lama', exam_type='PTS')
    client.force_login(world['gu'])
    assert _action(client, sch, 'archive').status_code == 403
    client.force_login(world['kurikulum'])
    _action(client, sch, 'archive')
    exam.refresh_from_db()
    assert exam.archived_at is not None


@pytest.mark.django_db
def test_unarchive_restores_and_results_stay_available(client, world):
    exam, sch = world['make']('UH Kembali')
    client.force_login(world['gu'])
    _action(client, sch, 'archive')
    assert client.get(reverse('reports:exam_results_detail', args=[exam.id])).status_code == 200

    _action(client, sch, 'unarchive')

    exam.refresh_from_db()
    assert exam.archived_at is None


@pytest.mark.django_db
def test_plain_delete_refusal_points_to_archive(client, world):
    _, sch = world['make']('UH Terpakai')
    client.force_login(world['admin'])
    res = client.post(reverse('schedules:delete', args=[sch.id]), **HX)
    assert 'Arsipkan' in res.headers.get('HX-Trigger', '') + res.content.decode()


# ==============================================================================
# Hapus permanen
# ==============================================================================

@pytest.fixture
def archived(world, tmp_path):
    exam, sch = world['make']('UJI COBA UH')
    exam.archived_at = timezone.now()
    exam.save(update_fields=['archived_at'])
    return exam, sch


def _purge(client, sch, typed):
    return _action(client, sch, 'purge', {'confirm_title': typed})


@pytest.mark.django_db
def test_purge_backs_up_then_deletes_everything_of_the_exam(client, world, archived, tmp_path):
    exam, sch = archived
    client.force_login(world['admin'])
    with override_settings(PURGE_ARCHIVE_DIR=str(tmp_path)), \
            patch.object(archive, 'run_pre_delete_backup', return_value='/backup/db-hapus.dump') as backup:
        _purge(client, sch, 'UJI COBA UH')

    backup.assert_called_once()
    assert not Exam.objects.filter(pk=exam.pk).exists()
    assert not Schedule.objects.filter(pk=sch.pk).exists()
    assert not ExamSession.objects.filter(schedule_id=sch.pk).exists()
    assert StudentAnswer.objects.count() == 0
    assert Student.objects.filter(nis='9999000001').exists()
    log = ExamPurgeLog.objects.get()
    assert (log.title, log.sessions_count, log.answers_count, log.deleted_by) == ('UJI COBA UH', 1, 1, world['admin'])
    assert log.backup_file == '/backup/db-hapus.dump'
    exported = list(tmp_path.glob('*.xlsx'))
    assert len(exported) == 1 and log.export_file == str(exported[0])


@pytest.mark.django_db
def test_purge_aborts_when_backup_fails(client, world, archived, tmp_path):
    exam, sch = archived
    client.force_login(world['admin'])
    with override_settings(PURGE_ARCHIVE_DIR=str(tmp_path)), \
            patch.object(archive, 'run_pre_delete_backup', side_effect=archive.ArchiveError('backup gagal')):
        res = _purge(client, sch, 'UJI COBA UH')
    assert Exam.objects.filter(pk=exam.pk).exists()
    assert not ExamPurgeLog.objects.exists()
    assert 'backup gagal' in res.content.decode()


@pytest.mark.django_db
def test_purge_requires_exact_title(client, world, archived, tmp_path):
    exam, sch = archived
    client.force_login(world['admin'])
    with override_settings(PURGE_ARCHIVE_DIR=str(tmp_path)), \
            patch.object(archive, 'run_pre_delete_backup') as backup:
        _purge(client, sch, 'uji coba')
    backup.assert_not_called()
    assert Exam.objects.filter(pk=exam.pk).exists()


@pytest.mark.django_db
def test_purge_only_for_admin_and_only_archived(client, world, tmp_path):
    exam, sch = world['make']('PAS Aktif', exam_type='PAS')
    with override_settings(PURGE_ARCHIVE_DIR=str(tmp_path)), \
            patch.object(archive, 'run_pre_delete_backup') as backup:
        client.force_login(world['admin'])
        _purge(client, sch, 'PAS Aktif')
        assert Exam.objects.filter(pk=exam.pk).exists()

        exam.archived_at = timezone.now()
        exam.save(update_fields=['archived_at'])
        for user in (world['kurikulum'], world['gu']):
            client.force_login(user)
            assert _purge(client, sch, 'PAS Aktif').status_code == 403
    backup.assert_not_called()
    assert Exam.objects.filter(pk=exam.pk).exists()


@pytest.mark.django_db
def test_purge_modal_asks_to_type_the_title(client, world, archived):
    _, sch = archived
    client.force_login(world['admin'])
    html = client.get(reverse('schedules:action', kwargs={'pk': sch.id, 'action': 'purge'}), **HX).content.decode()
    assert 'name="confirm_title"' in html
    assert 'UJI COBA UH' in html


# ==============================================================================
# Tampilan kartu dan filter
# ==============================================================================

@pytest.mark.django_db
def test_card_buttons_follow_archive_state(client, world):
    exam, sch = world['make']('UH Kartu')
    client.force_login(world['admin'])
    page = client.get(reverse('schedules:list'), {'date_filter': 'Semua'}).content.decode()
    assert f'archive-btn-{sch.id}' in page and f'purge-btn-{sch.id}' not in page
    assert '<option value="arsip">' in page

    _action(client, sch, 'archive')
    archived = client.get(reverse('schedules:list'), {'date_filter': 'Semua', 'status': 'arsip'}).content.decode()
    assert f'unarchive-btn-{sch.id}' in archived and f'purge-btn-{sch.id}' in archived
    assert 'Diarsipkan' in archived


@pytest.mark.django_db
def test_kurikulum_sees_no_purge_button(client, world):
    exam, sch = world['make']('UH Kurikulum')
    exam.archived_at = timezone.now()
    exam.save(update_fields=['archived_at'])
    client.force_login(world['kurikulum'])
    page = client.get(reverse('schedules:list'), {'date_filter': 'Semua', 'status': 'arsip'}).content.decode()
    assert f'unarchive-btn-{sch.id}' in page and f'purge-btn-{sch.id}' not in page


@pytest.mark.django_db
def test_unarchive_from_archive_view_rerenders_archive_list(client, world):
    exam, sch = world['make']('UH Tetap Arsip')
    other, other_sch = world['make']('UH Arsip Lain')
    client.force_login(world['gu'])
    _action(client, sch, 'archive')
    _action(client, other_sch, 'archive')

    res = client.post(reverse('schedules:action', kwargs={'pk': sch.id, 'action': 'unarchive'}),
                      HTTP_HX_REQUEST='true', HTTP_HX_CURRENT_URL='https://exam.test/schedules/?date_filter=Semua&status=arsip')

    html = res.content.decode()
    assert 'UH Arsip Lain' in html and 'UH Tetap Arsip' not in html

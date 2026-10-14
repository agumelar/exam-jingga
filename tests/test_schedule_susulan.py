"""Susulan: waktu jadwal boleh digeser setelah ujian berjalan, selama tidak ada siswa yang sedang mengerjakan."""
from datetime import timedelta

import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone
from django.utils.formats import date_format

from apps.accounts.models import Role
from apps.exam_engine.models import ExamSession
from apps.master_data.models import ClassRoom, Student, Subject, Teacher, TeacherAssignment
from apps.questions.models import Question
from apps.schedules.models import Exam, ExamQuestion, Schedule, ScheduleTimeChange

User = get_user_model()
HX = {'HTTP_HX_REQUEST': 'true'}


def _local(minutes):
    return (timezone.localtime() + timedelta(minutes=minutes)).strftime('%Y-%m-%dT%H:%M')


@pytest.fixture
def uh(db):
    cls = ClassRoom.objects.create(name='10 Uji', level=10)
    subject = Subject.objects.create(name='Mapel Susulan')
    gu = User.objects.create_user(username='guru_susulan', role=Role.GURU)
    teacher = Teacher.objects.create(user=gu, full_name='Guru Susulan', email='gs@x.id')
    TeacherAssignment.objects.create(teacher=teacher, subject=subject, class_room=cls)
    exam = Exam.objects.create(teacher=teacher, subject=subject, title='UH Susulan', exam_type='UH', level=10,
                               status='validated', duration=30, target_question_count=1, token='SUS001')
    q = Question.objects.create(subject=subject, level=10, created_by=teacher, question_text='Soal', option_a='a',
                                option_b='b', option_c='c', option_d='d', option_e='e', correct_answer='A')
    ExamQuestion.objects.create(exam=exam, question=q, order_number=1)
    start = timezone.now() - timedelta(hours=2)
    schedule = Schedule.objects.create(exam=exam, class_room=cls, teacher=teacher, start_time=start,
                                       end_time=start + timedelta(minutes=30), token='SUS001', teacher_quota=1)
    students = []
    for nis in ('9999000001', '9999000002'):
        su = User.objects.create_user(username=nis, nis=nis, role=Role.SISWA)
        students.append(Student.objects.create(user=su, nis=nis, full_name=f'Siswa {nis}', class_room=cls, status='aktif'))
    return {'exam': exam, 'schedule': schedule, 'guru': gu, 'cls': cls, 'subject': subject, 'students': students}


def _edit(client, w, start):
    return client.post(reverse('schedules:edit', args=[w['schedule'].id]), {
        'exam_type': 'UH', 'title': 'UH Susulan', 'level': 10, 'subject': w['subject'].id, 'class_room': w['cls'].id,
        'duration': 30, 'target_question_count': 1, 'session_no': '0', 'token': 'SUS001', 'start_time': start}, **HX)


def _session(w, student, status):
    return ExamSession.objects.create(student=student, schedule=w['schedule'], status=status,
                                      started_at=w['schedule'].start_time, finished_at=timezone.now() if status == 'finished' else None)


@pytest.mark.django_db
def test_owner_moves_uh_time_after_first_wave_finished(client, uh):
    _session(uh, uh['students'][0], 'finished')
    old_start = uh['schedule'].start_time
    client.force_login(uh['guru'])

    _edit(client, uh, _local(30))

    uh['schedule'].refresh_from_db()
    assert uh['schedule'].start_time > timezone.now()
    change = ScheduleTimeChange.objects.get(exam=uh['exam'])
    assert (change.changed_by, change.old_start) == (uh['guru'], old_start)
    assert change.new_start == uh['schedule'].start_time


@pytest.mark.django_db
def test_finished_student_cannot_take_susulan_but_others_can(client, uh):
    done, susulan = uh['students']
    _session(uh, done, 'finished')
    client.force_login(uh['guru'])
    _edit(client, uh, _local(-1))

    for student, expected in ((done, 1), (susulan, 1)):
        client.force_login(student.user)
        client.post(reverse('exam_engine:confirm_token'), {'schedule_id': str(uh['schedule'].id), 'token': 'SUS001'}, **HX)
        assert ExamSession.objects.filter(student=student).count() == expected
    assert ExamSession.objects.get(student=done).status == 'finished'
    assert ExamSession.objects.get(student=susulan).status == 'active'


@pytest.mark.django_db
@pytest.mark.parametrize('status', ['active', 'locked'])
def test_time_change_refused_while_a_student_is_in_progress(client, uh, status):
    _session(uh, uh['students'][0], status)
    before = uh['schedule'].start_time
    client.force_login(uh['guru'])

    res = _edit(client, uh, _local(30))

    uh['schedule'].refresh_from_db()
    assert uh['schedule'].start_time == before
    assert 'sedang mengerjakan' in res.content.decode()
    assert not ScheduleTimeChange.objects.exists()


@pytest.mark.django_db
def test_edit_before_anyone_starts_is_not_logged_as_susulan(client, uh):
    client.force_login(uh['guru'])
    _edit(client, uh, _local(30))
    assert not ScheduleTimeChange.objects.exists()


@pytest.mark.django_db
def test_schedule_card_shows_original_time_after_susulan(client, uh):
    _session(uh, uh['students'][0], 'finished')
    original = date_format(timezone.localtime(uh['schedule'].start_time), 'd M Y, H:i')
    client.force_login(uh['guru'])
    _edit(client, uh, _local(30))

    page = client.get(reverse('schedules:list')).content.decode()

    assert 'Susulan' in page
    assert original in page

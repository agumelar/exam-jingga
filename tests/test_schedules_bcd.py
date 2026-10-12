"""Fase 3 audit: pembuatan/edit/hapus jadwal (B), kuota (C), pemilihan soal (D)."""
from datetime import timedelta

import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone

from apps.accounts.models import Role
from apps.exam_engine.models import ExamSession
from apps.master_data.models import ClassRoom, Student, Subject, Teacher, TeacherAssignment
from apps.questions.models import Question
from apps.schedules.models import Exam, ExamQuestion, Schedule

User = get_user_model()


def _guru(name):
    user = User.objects.create_user(username=name, email=f'{name}@x.id', role=Role.GURU)
    return user, Teacher.objects.create(user=user, full_name=f'Guru {name}', email=f'{name}@x.id')


def _admin(name='admin_bcd'):
    return User.objects.create_user(username=name, role=Role.ADMIN)


def _start(minutes=60):
    return (timezone.localtime() + timedelta(minutes=minutes)).strftime('%Y-%m-%dT%H:%M')


@pytest.fixture
def base(db):
    cls = ClassRoom.objects.create(name='X BCD 1', level=10)
    cls2 = ClassRoom.objects.create(name='X BCD 2', level=10)
    cls11 = ClassRoom.objects.create(name='XI BCD 1', level=11)
    subject = Subject.objects.create(name='Mapel BCD')
    ua, ta = _guru('bcd_a')
    ub, tb = _guru('bcd_b')
    TeacherAssignment.objects.create(teacher=ta, subject=subject, class_room=cls)
    TeacherAssignment.objects.create(teacher=ta, subject=subject, class_room=cls11)
    TeacherAssignment.objects.create(teacher=tb, subject=subject, class_room=cls2)
    return locals()


def _post_create(client, **data):
    payload = {'exam_type': 'UH', 'title': 'UH BCD', 'duration': 60, 'target_question_count': 2,
               'session_no': '0', 'token': 'BCD123', 'start_time': _start()}
    payload.update(data)
    return client.post(reverse('schedules:create'), payload, HTTP_HX_REQUEST='true')


# ==============================================================================
# B. Pembuatan jadwal
# ==============================================================================

@pytest.mark.django_db
def test_guru_cannot_schedule_uh_for_class_not_taught(client, base):
    client.force_login(base['ua'])
    res = _post_create(client, level=10, subject=base['subject'].id, class_room=base['cls2'].id)
    assert not Schedule.objects.exists()
    assert 'tidak mengajar' in res.content.decode()


@pytest.mark.django_db
def test_guru_uh_always_owned_by_creator(client, base):
    client.force_login(base['ua'])
    _post_create(client, level=10, subject=base['subject'].id, class_room=base['cls'].id, teacher=base['tb'].id)
    exam = Exam.objects.get()
    assert exam.teacher == base['ta']
    assert Schedule.objects.get().teacher == base['ta']


@pytest.mark.django_db
def test_class_level_must_match(client, base):
    client.force_login(base['ua'])
    res = _post_create(client, level=10, subject=base['subject'].id, class_room=base['cls11'].id)
    assert not Schedule.objects.exists()
    assert 'jenjang' in res.content.decode().lower()


@pytest.mark.django_db
def test_invalid_start_time_is_rejected(client, base):
    client.force_login(base['ua'])
    _post_create(client, level=10, subject=base['subject'].id, class_room=base['cls'].id, start_time='bukan-tanggal')
    assert not Schedule.objects.exists()


@pytest.mark.django_db
def test_form_error_rerenders_modal_with_values(client, base):
    client.force_login(base['ua'])
    res = _post_create(client, level=10, subject=base['subject'].id, class_room=base['cls2'].id, title='Judul Tetap')
    assert res.status_code == 200
    assert res.headers.get('HX-Retarget') == '#modal-container'
    assert 'Judul Tetap' in res.content.decode()


@pytest.mark.django_db
def test_overlapping_schedule_same_class_rejected(client, base):
    client.force_login(base['ua'])
    _post_create(client, level=10, subject=base['subject'].id, class_room=base['cls'].id, start_time=_start(60))
    res = _post_create(client, level=10, subject=base['subject'].id, class_room=base['cls'].id, start_time=_start(90), title='UH Kedua')
    assert Schedule.objects.count() == 1
    assert 'bentrok' in res.content.decode().lower()


@pytest.mark.django_db
def test_pts_requires_teacher_who_teaches_the_class(client, base):
    client.force_login(_admin())
    bad = _post_create(client, exam_type='PTS', sub_type='PTS Ganjil', level=10, subject=base['subject'].id,
                       class_room=base['cls2'].id, teacher=base['ta'].id)
    assert not Schedule.objects.exists()
    assert 'tidak mengajar' in bad.content.decode()

    _post_create(client, exam_type='PTS', sub_type='PTS Ganjil', level=10, subject=base['subject'].id,
                 class_room=base['cls2'].id, teacher=base['tb'].id)
    sch = Schedule.objects.get()
    assert sch.teacher == base['tb'] and sch.exam.teacher == base['tb'] and sch.class_room == base['cls2']


@pytest.mark.django_db
def test_collaborative_target_must_cover_every_teacher(client, base):
    TeacherAssignment.objects.create(teacher=base['tb'], subject=base['subject'], class_room=base['cls'])
    TeacherAssignment.objects.create(teacher=_guru('bcd_c')[1], subject=base['subject'], class_room=base['cls'])
    client.force_login(_admin())
    res = _post_create(client, exam_type='PAS', sub_type='Penilaian Akhir Semester', level=10,
                       subject=base['subject'].id, target_question_count=2)
    assert not Exam.objects.exists()
    assert 'minimal 3' in res.content.decode()


# ==============================================================================
# B. Edit & hapus
# ==============================================================================

def _collab(base, status='pending_selection', target=4):
    exam = Exam.objects.create(teacher=base['ta'], subject=base['subject'], title='PAS BCD', exam_type='PAS', level=10,
                               status=status, target_question_count=target, token='OLD001', duration=60)
    now = timezone.now() + timedelta(hours=1)
    s1 = Schedule.objects.create(exam=exam, teacher=base['ta'], start_time=now, end_time=now + timedelta(minutes=60),
                                 token='OLD001', teacher_quota=target // 2)
    s2 = Schedule.objects.create(exam=exam, teacher=base['tb'], start_time=now, end_time=now + timedelta(minutes=60),
                                 token='OLD001', teacher_quota=target // 2)
    return exam, s1, s2


def _post_edit(client, schedule, **data):
    exam = schedule.exam
    payload = {'exam_type': exam.exam_type, 'sub_type': 'Penilaian Akhir Semester', 'title': exam.title,
               'level': exam.level, 'subject': exam.subject_id, 'duration': exam.duration,
               'target_question_count': exam.target_question_count, 'session_no': '0',
               'token': schedule.token, 'start_time': timezone.localtime(schedule.start_time).strftime('%Y-%m-%dT%H:%M')}
    payload.update(data)
    return client.post(reverse('schedules:edit', args=[schedule.id]), payload, HTTP_HX_REQUEST='true')


@pytest.mark.django_db
def test_edit_time_applies_to_every_schedule_and_keeps_quotas(client, base):
    exam, s1, s2 = _collab(base)
    client.force_login(_admin())

    _post_edit(client, s1, start_time=_start(180), token='NEW999', duration=90)

    s1.refresh_from_db(); s2.refresh_from_db(); exam.refresh_from_db()
    assert s1.start_time == s2.start_time
    assert s1.token == s2.token == exam.token == 'NEW999'
    assert (s1.end_time - s1.start_time) == timedelta(minutes=90)
    assert s1.teacher_quota + s2.teacher_quota == exam.target_question_count


@pytest.mark.django_db
def test_edit_target_recomputes_quotas_when_pending(client, base):
    exam, s1, s2 = _collab(base, target=4)
    client.force_login(_admin())

    _post_edit(client, s1, target_question_count=10)

    s1.refresh_from_db(); s2.refresh_from_db()
    assert s1.teacher_quota + s2.teacher_quota == 10


@pytest.mark.django_db
def test_edit_content_refused_after_validation(client, base):
    exam, s1, _ = _collab(base, status='validated', target=4)
    client.force_login(_admin())

    res = _post_edit(client, s1, target_question_count=10)

    exam.refresh_from_db()
    assert exam.target_question_count == 4
    assert 'buka kunci' in res.content.decode().lower()


@pytest.mark.django_db
def test_edit_time_refused_after_student_started(client, base):
    exam, s1, _ = _collab(base, status='validated')
    stu_user = User.objects.create_user(username='88001', nis='88001', role=Role.SISWA)
    stu = Student.objects.create(user=stu_user, nis='88001', full_name='S', class_room=base['cls'])
    ExamSession.objects.create(student=stu, schedule=s1)
    client.force_login(_admin())
    before = s1.start_time

    _post_edit(client, s1, start_time=_start(300))

    s1.refresh_from_db()
    assert s1.start_time == before


def _uh(base, teacher_key='ta', cls_key='cls'):
    teacher = base[teacher_key]
    exam = Exam.objects.create(teacher=teacher, subject=base['subject'], title='UH Milik', exam_type='UH', level=10,
                               target_question_count=2)
    now = timezone.now() + timedelta(hours=2)
    sch = Schedule.objects.create(exam=exam, teacher=teacher, class_room=base[cls_key], start_time=now,
                                  end_time=now + timedelta(minutes=60), token='UH0001', teacher_quota=2)
    return exam, sch


@pytest.mark.django_db
def test_guru_cannot_edit_or_delete_other_teachers_uh(client, base):
    exam, sch = _uh(base, 'tb', 'cls2')
    client.force_login(base['ua'])

    assert client.get(reverse('schedules:edit', args=[sch.id]), HTTP_HX_REQUEST='true').status_code == 403
    assert client.post(reverse('schedules:delete', args=[sch.id]), HTTP_HX_REQUEST='true').status_code == 403
    assert Schedule.objects.filter(pk=sch.pk).exists()


@pytest.mark.django_db
def test_delete_refused_when_sessions_exist(client, base):
    exam, sch = _uh(base)
    stu_user = User.objects.create_user(username='88002', nis='88002', role=Role.SISWA)
    stu = Student.objects.create(user=stu_user, nis='88002', full_name='S2', class_room=base['cls'])
    ExamSession.objects.create(student=stu, schedule=sch)
    client.force_login(base['ua'])

    res = client.post(reverse('schedules:delete', args=[sch.id]), HTTP_HX_REQUEST='true')

    assert res.status_code == 409
    assert Schedule.objects.filter(pk=sch.pk).exists()


@pytest.mark.django_db
def test_owner_deletes_unused_uh(client, base):
    exam, sch = _uh(base)
    client.force_login(base['ua'])
    client.post(reverse('schedules:delete', args=[sch.id]), HTTP_HX_REQUEST='true')
    assert not Schedule.objects.filter(pk=sch.pk).exists()
    assert not Exam.objects.filter(pk=exam.pk).exists()


@pytest.mark.django_db
def test_bulk_delete_skips_schedules_with_sessions(client, base):
    exam, sch = _uh(base)
    exam2, sch2 = _uh(base, cls_key='cls11')
    stu_user = User.objects.create_user(username='88003', nis='88003', role=Role.SISWA)
    stu = Student.objects.create(user=stu_user, nis='88003', full_name='S3', class_room=base['cls'])
    ExamSession.objects.create(student=stu, schedule=sch)
    client.force_login(_admin())

    client.post(reverse('schedules:bulk_delete'), {'schedule_ids': [str(sch.id), str(sch2.id)]}, HTTP_HX_REQUEST='true')

    assert Schedule.objects.filter(pk=sch.pk).exists()
    assert not Schedule.objects.filter(pk=sch2.pk).exists()


# ==============================================================================
# C & D. Kuota dan pemilihan soal
# ==============================================================================

def _q(base, author, n=1, subject=None, level=10, option_e='e'):
    out = []
    for i in range(n):
        out.append(Question.objects.create(subject=subject or base['subject'], level=level, created_by=author,
                                           question_text=f'Soal {author.full_name} {i}', option_a='a', option_b='b',
                                           option_c='c', option_d='d', option_e=option_e, correct_answer='A'))
    return out


def _toggle(client, exam, q):
    return client.post(reverse('schedules:toggle_question', args=[exam.id, q.id]), {'idx': '1'}, HTTP_HX_REQUEST='true')


@pytest.mark.django_db
def test_toggle_refuses_beyond_own_quota(client, base):
    exam, s1, _ = _collab(base, target=4)
    mine = _q(base, base['ta'], 3)
    client.force_login(base['ua'])
    _toggle(client, exam, mine[0]); _toggle(client, exam, mine[1])

    res = _toggle(client, exam, mine[2])

    assert res.status_code == 409
    assert exam.exam_questions.count() == 2


@pytest.mark.django_db
def test_guru_bank_lists_only_own_questions(client, base):
    exam, s1, _ = _collab(base)
    _q(base, base['ta'], 2)
    _q(base, base['tb'], 3)
    client.force_login(base['ua'])

    res = client.get(reverse('schedules:select_questions', args=[exam.id]))

    assert {q.created_by_id for q in res.context['bank_questions']} == {base['ta'].id}


@pytest.mark.django_db
def test_non_member_cannot_open_selection_page(client, base):
    exam, sch = _uh(base, 'tb', 'cls2')
    client.force_login(base['ua'])
    assert client.get(reverse('schedules:select_questions', args=[exam.id])).status_code == 404


@pytest.mark.django_db
def test_toggle_refuses_colleague_question(client, base):
    exam, s1, _ = _collab(base)
    theirs = _q(base, base['tb'])[0]
    client.force_login(base['ua'])
    assert _toggle(client, exam, theirs).status_code == 403
    assert not exam.exam_questions.exists()


@pytest.mark.django_db
def test_toggle_refuses_other_subject_or_level(client, base):
    exam, sch = _uh(base)
    other_subject = Subject.objects.create(name='Mapel Lain')
    wrong = [_q(base, base['ta'], subject=other_subject)[0], _q(base, base['ta'], level=11)[0]]
    client.force_login(base['ua'])
    for q in wrong:
        assert _toggle(client, exam, q).status_code == 403
    assert not exam.exam_questions.exists()


@pytest.mark.django_db
def test_toggle_refuses_question_without_option_e(client, base):
    exam, sch = _uh(base)
    legacy = _q(base, base['ta'], option_e='')[0]
    client.force_login(base['ua'])
    res = _toggle(client, exam, legacy)
    assert res.status_code == 409
    assert 'opsi E' in res.content.decode()


@pytest.mark.django_db
def test_order_numbers_stay_unique_and_renumber_on_save(client, base):
    exam, sch = _uh(base)
    Exam.objects.filter(pk=exam.pk).update(target_question_count=3)
    q1, q2, q3, q4 = _q(base, base['ta'], 4)
    client.force_login(base['ua'])
    for q in (q1, q2, q3):
        _toggle(client, exam, q)
    _toggle(client, exam, q1)
    _toggle(client, exam, q4)
    numbers = list(exam.exam_questions.values_list('order_number', flat=True))
    assert len(numbers) == len(set(numbers))

    client.post(reverse('schedules:save_questions', args=[exam.id]))

    assert sorted(exam.exam_questions.values_list('order_number', flat=True)) == [1, 2, 3]


@pytest.mark.django_db
def test_selection_page_is_paginated(client, base):
    exam, sch = _uh(base)
    _q(base, base['ta'], 30)
    client.force_login(base['ua'])

    first = client.get(reverse('schedules:select_questions', args=[exam.id]))
    second = client.get(reverse('schedules:select_questions', args=[exam.id]), {'page': 2})

    assert len(first.context['bank_questions']) == 25
    assert len(second.context['bank_questions']) == 5


@pytest.mark.django_db
def test_official_exam_requires_semester_title(client, base):
    client.force_login(_admin('admin_semester'))
    res = _post_create(client, exam_type='PTS', level=10, subject=base['subject'].id,
                       class_room=base['cls2'].id, teacher=base['tb'].id, title='')
    assert not Exam.objects.exists()
    assert 'semester' in res.content.decode().lower()


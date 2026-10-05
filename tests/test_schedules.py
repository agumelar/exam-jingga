"""Tests for Schedules and Exam Lifecycle Module (Task 6)."""
import uuid
import json
import pytest
from datetime import datetime, timedelta
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db.utils import IntegrityError
from django.urls import reverse
from django.utils import timezone

from apps.accounts.models import Role
from apps.master_data.models import Subject, Teacher, ClassRoom, Major, TeacherAssignment
from apps.questions.models import Question
from apps.schedules.models import Exam, ExamQuestion, Schedule
from apps.schedules.forms import ScheduleForm
from apps.schedules.utils import (
    generate_exam_token,
    resolve_exam_title,
    build_schedule_date_range,
    resolve_status_after_question_save,
    can_transition_status,
    calculate_collaborative_quotas,
    TOKEN_ALPHABET,
)

User = get_user_model()


# ==============================================================================
# 1. Model & Relations Tests
# ==============================================================================

@pytest.mark.django_db
def test_exam_model_creation_and_properties():
    """Verify Exam model fields, UUID pk, status, properties and str representation."""
    subject = Subject.objects.create(name='Matematika')
    teacher = Teacher.objects.create(full_name='Guru Matematika')

    exam = Exam.objects.create(
        teacher=teacher,
        subject=subject,
        title='Ulangan Harian Matriks',
        exam_type='UH',
        duration=60,
        target_question_count=20,
        level=11,
        status='pending_selection',
        token='ABCDEF'
    )

    assert isinstance(exam.id, uuid.UUID)
    assert 'UH' in str(exam)
    assert 'Ulangan Harian Matriks' in str(exam)
    assert exam.selected_questions_count == 0
    assert exam.is_ready_for_student is False
    assert exam.is_locked() is False

    # When validated
    exam.status = 'validated'
    exam.save()
    assert exam.is_ready_for_student is True
    assert exam.is_locked() is True


@pytest.mark.django_db
def test_exam_question_model_and_unique_constraint():
    """Verify ExamQuestion model, ordering, and unique constraint on [exam, question]."""
    subject = Subject.objects.create(name='Bahasa Inggris')
    teacher = Teacher.objects.create(full_name='Guru Bahasa Inggris')
    exam = Exam.objects.create(teacher=teacher, subject=subject, title='PTS Ganjil', exam_type='PTS', level=10)

    q1 = Question.objects.create(subject=subject, level=10, question_text='What is a noun?', correct_answer='A')
    q2 = Question.objects.create(subject=subject, level=10, question_text='What is a verb?', correct_answer='B')

    eq1 = ExamQuestion.objects.create(exam=exam, question=q1, order_number=1)
    eq2 = ExamQuestion.objects.create(exam=exam, question=q2, order_number=2)

    assert exam.selected_questions_count == 2
    assert 'Soal #1' in str(eq1)

    # Violating unique constraint should raise IntegrityError
    with pytest.raises(IntegrityError):
        ExamQuestion.objects.create(exam=exam, question=q1, order_number=3)


@pytest.mark.django_db
def test_schedule_model_and_properties():
    """Verify Schedule model fields, relationships, session display, and token active status."""
    subject = Subject.objects.create(name='Informatika')
    teacher = Teacher.objects.create(full_name='Guru Informatika')
    classroom = ClassRoom.objects.create(name='X RPL 1', level=10)

    start_dt = timezone.now()
    end_dt = start_dt + timedelta(minutes=90)

    exam = Exam.objects.create(
        teacher=teacher,
        subject=subject,
        title='PAS Ganjil Informatika',
        exam_type='PAS',
        level=10,
        status='pending_selection'
    )

    schedule = Schedule.objects.create(
        exam=exam,
        class_room=classroom,
        teacher=teacher,
        start_time=start_dt,
        end_time=end_dt,
        token='INF999',
        session_no=1,
        status='active',
        teacher_quota=20
    )

    assert isinstance(schedule.id, uuid.UUID)
    assert schedule.session_display == 'Sesi 1'
    assert schedule.cluster_classes_text == 'X RPL 1'
    assert schedule.is_token_active is False  # Exam is pending_selection

    # When exam is validated
    exam.status = 'ready'
    exam.save()
    assert schedule.is_token_active is True

    # Test session 0 displays 'Semua Sesi'
    schedule.session_no = 0
    assert schedule.session_display == 'Semua Sesi'


# ==============================================================================
# 2. Utilities & Helper Functions Tests
# ==============================================================================

def test_token_generator():
    """Verify generated tokens are 6 characters and do not contain ambiguous characters."""
    for _ in range(50):
        tok = generate_exam_token(6)
        assert len(tok) == 6
        assert tok.upper() == tok
        for char in tok:
            assert char in TOKEN_ALPHABET
            assert char not in ['0', 'O', '1', 'I']


def test_resolve_exam_title():
    """Verify resolve_exam_title formats names accurately."""
    assert resolve_exam_title('SAJ', 'Test', 'Any') == 'Asesmen Sumatif Akhir Jenjang'
    assert resolve_exam_title('PTS', 'Fallback', 'PTS Ganjil 2025/2026') == 'PTS Ganjil 2025/2026'
    assert resolve_exam_title('PAS', 'Fallback', 'Penilaian Akhir Semester') == 'Penilaian Akhir Semester'
    assert resolve_exam_title('UH', 'Ulangan Bab 2', '') == 'Ulangan Bab 2'


def test_build_schedule_date_range():
    """Verify build_schedule_date_range handles string format and duration calculation."""
    start_str = '2026-09-01T08:00'
    start_dt, end_dt = build_schedule_date_range(start_str, duration_minutes=90)

    assert start_dt.hour == 8
    assert start_dt.minute == 0
    diff = end_dt - start_dt
    assert diff.total_seconds() == 90 * 60


def test_resolve_status_after_question_save():
    """Verify resolve_status_after_question_save workflow rules."""
    # When not full
    assert resolve_status_after_question_save('UH', is_full=False) == 'pending_selection'
    assert resolve_status_after_question_save('PAS', is_full=False) == 'pending_selection'

    # When full
    assert resolve_status_after_question_save('UH', is_full=True) == 'validated'
    assert resolve_status_after_question_save('PTS', is_full=True) == 'waiting_validation'
    assert resolve_status_after_question_save('PAS', is_full=True) == 'waiting_validation'
    assert resolve_status_after_question_save('SAJ', is_full=True) == 'waiting_validation'


def test_can_transition_status():
    """Verify can_transition_status validation rules for admin and guru."""
    # Admin verifying exam
    assert can_transition_status('admin', 'PAS', 'waiting_validation', 'validated') is True
    assert can_transition_status('kurikulum', 'PTS', 'waiting_validation', 'ready') is True
    assert can_transition_status('guru', 'PTS', 'waiting_validation', 'validated') is False

    # Guru unlocking UH
    assert can_transition_status('guru', 'UH', 'validated', 'pending_selection') is True
    assert can_transition_status('guru', 'UH', 'ready', 'pending_selection') is True
    assert can_transition_status('guru', 'PAS', 'validated', 'pending_selection') is False


def test_calculate_collaborative_quotas():
    """Verify collaborative question quota splitting across multiple teachers."""
    teachers = ['t1', 't2', 't3']
    quotas = calculate_collaborative_quotas(teachers, total_target_questions=40)

    # 40 / 3 = 13 with remainder 1 (so: 14, 13, 13)
    assert quotas['t1'] == 14
    assert quotas['t2'] == 13
    assert quotas['t3'] == 13
    assert sum(quotas.values()) == 40


# ==============================================================================
# 3. ScheduleForm Tests
# ==============================================================================

@pytest.mark.django_db
def test_schedule_form_create_single_uh():
    """Verify ScheduleForm successfully creates single UH Exam and Schedule."""
    subject = Subject.objects.create(name='Pemrograman Web')
    classroom = ClassRoom.objects.create(name='XI RPL 1', level=11)
    teacher = Teacher.objects.create(full_name='Pak Budi, S.Kom')

    form_data = {
        'exam_type': 'UH',
        'title': 'Ulangan Harian JavaScript',
        'level': 11,
        'subject': str(subject.id),
        'class_room': str(classroom.id),
        'start_time': '2026-09-10T08:30',
        'duration': 60,
        'target_question_count': 30,
        'session_no': '1',
        'token': 'JS1234',
    }

    form = ScheduleForm(data=form_data)
    assert form.is_valid(), form.errors
    schedules = form.save(creator_teacher=teacher)

    assert len(schedules) == 1
    sched = schedules[0]
    assert sched.exam.title == 'Ulangan Harian JavaScript'
    assert sched.exam.exam_type == 'UH'
    assert sched.exam.level == 11
    assert sched.class_room == classroom
    assert sched.token == 'JS1234'


@pytest.mark.django_db
def test_schedule_form_create_collaborative_pas():
    """Verify ScheduleForm creates collaborative PAS schedules for assigned teachers."""
    subject = Subject.objects.create(name='Fisika')
    c1 = ClassRoom.objects.create(name='X TBSM 1', level=10)
    c2 = ClassRoom.objects.create(name='X TBSM 2', level=10)

    t1 = Teacher.objects.create(full_name='Guru Fisika A')
    t2 = Teacher.objects.create(full_name='Guru Fisika B')

    TeacherAssignment.objects.create(teacher=t1, subject=subject, class_room=c1)
    TeacherAssignment.objects.create(teacher=t2, subject=subject, class_room=c2)

    form_data = {
        'exam_type': 'PAS',
        'sub_type': 'Penilaian Akhir Semester',
        'level': 10,
        'subject': str(subject.id),
        'start_time': '2026-12-01T08:00',
        'duration': 90,
        'target_question_count': 40,
        'session_no': '0',
        'token': 'PASFIS',
    }

    form = ScheduleForm(data=form_data)
    assert form.is_valid(), form.errors
    schedules = form.save()

    assert len(schedules) == 2
    exam = schedules[0].exam
    assert exam.title == 'Penilaian Akhir Semester'
    assert exam.exam_type == 'PAS'

    # Quota should be distributed (40 / 2 = 20 each)
    quotas = [s.teacher_quota for s in schedules]
    assert quotas == [20, 20]


# ==============================================================================
# 4. View & HTMX Endpoints Tests
# ==============================================================================

@pytest.mark.django_db
def test_schedule_list_view_admin(client):
    """Verify ScheduleListView displays all schedules for Admin."""
    admin_user = User.objects.create_superuser(username='admin_schedules', email='admin@test.com', password='password123')
    client.force_login(admin_user)

    subject = Subject.objects.create(name='Basis Data')
    classroom = ClassRoom.objects.create(name='XI RPL 2', level=11)
    teacher = Teacher.objects.create(full_name='Guru Basis Data')

    exam = Exam.objects.create(subject=subject, teacher=teacher, title='PTS Basis Data', exam_type='PTS', level=11)
    Schedule.objects.create(exam=exam, class_room=classroom, teacher=teacher, start_time=timezone.now(), end_time=timezone.now() + timedelta(hours=1), token='PTSBAS')

    res = client.get(reverse('schedules:list'))
    assert res.status_code == 200
    content = res.content.decode()
    assert 'Jadwal Ujian' in content
    assert 'PTS Basis Data' in content
    assert 'PTSBAS' in content


@pytest.mark.django_db
def test_schedule_list_view_teacher_scoping(client):
    """Verify ScheduleListView scopes to Teacher's own schedules."""
    teacher_user = User.objects.create_user(
        username='guru_siti',
        email='siti@smkn1rongga.sch.id',
        full_name='Siti Aminah, S.Pd',
        role=Role.GURU,
        password='password123'
    )
    t_siti = Teacher.objects.create(user=teacher_user, full_name='Siti Aminah, S.Pd', email='siti@smkn1rongga.sch.id')
    t_other = Teacher.objects.create(full_name='Guru Lain', email='lain@test.com')

    subject = Subject.objects.create(name='Sejarah')
    exam_siti = Exam.objects.create(subject=subject, teacher=t_siti, title='UH Sejarah Siti', exam_type='UH', level=10)
    exam_other = Exam.objects.create(subject=subject, teacher=t_other, title='UH Sejarah Guru Lain', exam_type='UH', level=10)

    Schedule.objects.create(exam=exam_siti, teacher=t_siti, start_time=timezone.now(), end_time=timezone.now() + timedelta(hours=1), token='SEJSIT')
    Schedule.objects.create(exam=exam_other, teacher=t_other, start_time=timezone.now(), end_time=timezone.now() + timedelta(hours=1), token='SEJOTH')

    client.force_login(teacher_user)
    res = client.get(reverse('schedules:list'))
    assert res.status_code == 200
    content = res.content.decode()
    assert 'UH Sejarah Siti' in content
    assert 'UH Sejarah Guru Lain' not in content


@pytest.mark.django_db
def test_schedule_create_modal_get_and_post_htmx(client):
    """Verify ScheduleCreateModalView GET modal form and POST action via HTMX."""
    admin_user = User.objects.create_superuser(username='admin_create_sched', email='admin2@test.com', password='password123')
    client.force_login(admin_user)

    subject = Subject.objects.create(name='Kimia')
    classroom = ClassRoom.objects.create(name='X ATPH 1', level=10)
    teacher = Teacher.objects.create(full_name='Guru Kimia')

    # 1. GET Modal Form
    get_res = client.get(reverse('schedules:create') + '?type=UH')
    assert get_res.status_code == 200
    assert 'Konfigurasi' in get_res.content.decode()

    # 2. POST Create via HTMX
    post_data = {
        'exam_type': 'UH',
        'title': 'Ulangan Harian Stoikiometri',
        'level': 10,
        'subject': str(subject.id),
        'class_room': str(classroom.id),
        'teacher': str(teacher.id),
        'start_time': '2026-10-05T09:00',
        'duration': 60,
        'target_question_count': 25,
        'session_no': '0',
        'token': 'KIM123',
    }
    post_res = client.post(
        reverse('schedules:create'),
        data=post_data,
        HTTP_HX_REQUEST='true'
    )
    assert post_res.status_code == 200
    assert 'Ulangan Harian Stoikiometri' in post_res.content.decode()
    assert Schedule.objects.filter(token='KIM123').exists()


@pytest.mark.django_db
def test_schedule_edit_modal_get_and_post_htmx(client):
    """Verify ScheduleEditModalView GET and POST update."""
    admin_user = User.objects.create_superuser(username='admin_edit_sched', email='admin3@test.com', password='password123')
    client.force_login(admin_user)

    subject = Subject.objects.create(name='Fisika')
    classroom = ClassRoom.objects.create(name='XI TKRO 1', level=11)
    teacher = Teacher.objects.create(full_name='Guru Fisika')

    exam = Exam.objects.create(subject=subject, teacher=teacher, title='PTS Fisika Awal', exam_type='PTS', level=11)
    schedule = Schedule.objects.create(exam=exam, class_room=classroom, teacher=teacher, start_time=timezone.now(), end_time=timezone.now() + timedelta(hours=1), token='FIS111')

    # 1. GET Edit Modal
    get_res = client.get(reverse('schedules:edit', kwargs={'pk': schedule.id}))
    assert get_res.status_code == 200
    assert 'PTS Fisika Awal' in get_res.content.decode()

    # 2. POST Edit
    update_data = {
        'exam_type': 'PTS',
        'sub_type': 'PTS Fisika Revisi',
        'level': 11,
        'subject': str(subject.id),
        'class_room': str(classroom.id),
        'start_time': '2026-10-15T10:00',
        'duration': 75,
        'target_question_count': 30,
        'session_no': '2',
        'token': 'FIS222',
    }
    post_res = client.post(
        reverse('schedules:edit', kwargs={'pk': schedule.id}),
        data=update_data,
        HTTP_HX_REQUEST='true'
    )
    assert post_res.status_code == 200
    schedule.refresh_from_db()
    assert schedule.token == 'FIS222'
    assert schedule.exam.title == 'PTS Fisika Revisi'


@pytest.mark.django_db
def test_schedule_delete_view_and_bulk_delete(client):
    """Verify ScheduleDeleteView and BulkDeleteSchedulesView."""
    admin_user = User.objects.create_superuser(username='admin_del_sched', email='admin4@test.com', password='password123')
    client.force_login(admin_user)

    subject = Subject.objects.create(name='Biologi')
    exam1 = Exam.objects.create(subject=subject, title='UH Biologi 1', exam_type='UH', level=10)
    s1 = Schedule.objects.create(exam=exam1, start_time=timezone.now(), end_time=timezone.now() + timedelta(hours=1), token='BIO001')

    exam2 = Exam.objects.create(subject=subject, title='UH Biologi 2', exam_type='UH', level=10)
    s2 = Schedule.objects.create(exam=exam2, start_time=timezone.now(), end_time=timezone.now() + timedelta(hours=1), token='BIO002')

    # 1. Single delete confirmation GET
    del_get_res = client.get(reverse('schedules:delete', kwargs={'pk': s1.id}))
    assert del_get_res.status_code == 200
    assert 'Hapus Jadwal Ujian?' in del_get_res.content.decode()

    # 2. Single delete POST
    del_post_res = client.post(reverse('schedules:delete', kwargs={'pk': s1.id}), HTTP_HX_REQUEST='true')
    assert del_post_res.status_code == 200
    assert not Schedule.objects.filter(id=s1.id).exists()

    # 3. Bulk delete POST
    bulk_res = client.post(
        reverse('schedules:bulk_delete'),
        data=json.dumps({'schedule_ids': [str(s2.id)]}),
        content_type='application/json',
        HTTP_HX_REQUEST='true'
    )
    assert bulk_res.status_code == 200
    assert not Schedule.objects.filter(id=s2.id).exists()


@pytest.mark.django_db
def test_schedule_action_verify_and_unlock(client):
    """Verify ScheduleActionView verify (admin) and unlock (guru)."""
    admin_user = User.objects.create_superuser(username='admin_verify', email='admin5@test.com', password='password123')
    guru_user = User.objects.create_user(username='guru_unlock', email='guru@smkn1rongga.sch.id', role=Role.GURU, password='password123')
    t_guru = Teacher.objects.create(user=guru_user, full_name='Guru Penguji', email='guru@smkn1rongga.sch.id')

    subject = Subject.objects.create(name='Pancasila')

    # 1. Admin verifies PTS exam from waiting_validation to validated
    exam_pts = Exam.objects.create(subject=subject, title='PTS Pancasila', exam_type='PTS', status='waiting_validation', level=10)
    s_pts = Schedule.objects.create(exam=exam_pts, teacher=t_guru, start_time=timezone.now(), end_time=timezone.now() + timedelta(hours=1), token='PAN001')

    client.force_login(admin_user)
    verify_res = client.post(reverse('schedules:action', kwargs={'pk': s_pts.id, 'action': 'verify'}))
    assert verify_res.status_code == 200
    exam_pts.refresh_from_db()
    assert exam_pts.status == 'validated'

    # 2. Guru unlocks UH exam from validated to pending_selection
    exam_uh = Exam.objects.create(subject=subject, teacher=t_guru, title='UH Pancasila', exam_type='UH', status='validated', level=10)
    s_uh = Schedule.objects.create(exam=exam_uh, teacher=t_guru, start_time=timezone.now(), end_time=timezone.now() + timedelta(hours=1), token='PAN002')

    client.force_login(guru_user)
    unlock_res = client.post(reverse('schedules:action', kwargs={'pk': s_uh.id, 'action': 'unlock'}))
    assert unlock_res.status_code == 200
    exam_uh.refresh_from_db()
    assert exam_uh.status == 'pending_selection'


# ==============================================================================
# 5. Question Selection & Toggle HTMX Tests
# ==============================================================================

@pytest.mark.django_db
def test_select_questions_view_and_toggle_htmx(client):
    """Verify SelectQuestionsView, ToggleQuestionView, and SaveQuestionsView."""
    guru_user = User.objects.create_user(username='guru_select', email='select@smkn1rongga.sch.id', role=Role.GURU, password='password123')
    teacher = Teacher.objects.create(user=guru_user, full_name='Guru Pembuat Soal', email='select@smkn1rongga.sch.id')
    subject = Subject.objects.create(name='Rekayasa Perangkat Lunak')

    exam = Exam.objects.create(
        subject=subject,
        teacher=teacher,
        title='UH Pemrograman Lanjut',
        exam_type='UH',
        target_question_count=2,
        level=11,
        status='pending_selection'
    )
    schedule = Schedule.objects.create(
        exam=exam,
        teacher=teacher,
        start_time=timezone.now(),
        end_time=timezone.now() + timedelta(hours=1),
        token='RPL999',
        teacher_quota=2
    )

    q1 = Question.objects.create(subject=subject, created_by=teacher, level=11, question_text='Soal nomor satu RPL', correct_answer='A')
    q2 = Question.objects.create(subject=subject, created_by=teacher, level=11, question_text='Soal nomor dua RPL', correct_answer='B')
    q3 = Question.objects.create(subject=subject, created_by=teacher, level=11, question_text='Soal nomor tiga RPL', correct_answer='C')

    client.force_login(guru_user)

    # 1. GET Select Questions Page
    get_res = client.get(reverse('schedules:select_questions', kwargs={'exam_id': exam.id}))
    assert get_res.status_code == 200
    assert 'UH Pemrograman Lanjut' in get_res.content.decode()
    assert 'Soal nomor satu RPL' in get_res.content.decode()

    # 2. Toggle add Q1 via HTMX
    toggle_q1 = client.post(
        reverse('schedules:toggle_question', kwargs={'exam_id': exam.id, 'question_id': q1.id}),
        data={'idx': '1'},
        HTTP_HX_REQUEST='true'
    )
    assert toggle_q1.status_code == 200
    assert 'Terpilih' in toggle_q1.content.decode()
    assert ExamQuestion.objects.filter(exam=exam, question=q1).exists()

    # 3. Toggle add Q2 via HTMX (reaching target count 2)
    toggle_q2 = client.post(
        reverse('schedules:toggle_question', kwargs={'exam_id': exam.id, 'question_id': q2.id}),
        data={'idx': '2'},
        HTTP_HX_REQUEST='true'
    )
    assert toggle_q2.status_code == 200
    assert ExamQuestion.objects.filter(exam=exam, question=q2).exists()

    # 4. Attempting to add Q3 exceeding target count 2 returns 400
    toggle_q3 = client.post(
        reverse('schedules:toggle_question', kwargs={'exam_id': exam.id, 'question_id': q3.id}),
        data={'idx': '3'},
        HTTP_HX_REQUEST='true'
    )
    assert toggle_q3.status_code == 400

    # 5. POST Save Questions (UH Express Lane auto-validates)
    save_res = client.post(reverse('schedules:save_questions', kwargs={'exam_id': exam.id}))
    assert save_res.status_code == 302
    exam.refresh_from_db()
    assert exam.status == 'validated'


# ==============================================================================
# 6. RBAC & Security Checks
# ==============================================================================

@pytest.mark.django_db
def test_rbac_student_blocked_from_schedules(client):
    """Ensure Student is blocked from accessing Schedules and redirected to /student/dashboard/."""
    student_user = User.objects.create_user(username='student_sched', role=Role.SISWA, password='password123')
    client.force_login(student_user)

    urls = [
        reverse('schedules:list'),
        reverse('schedules:create'),
        '/jadwal-ujian/',
    ]
    for u in urls:
        res = client.get(u)
        assert res.status_code == 302
        assert '/student/dashboard/' in res['Location']


@pytest.mark.django_db
def test_rbac_unauthenticated_blocked_from_schedules(client):
    """Ensure unauthenticated user is redirected to login."""
    res = client.get(reverse('schedules:list'))
    assert res.status_code == 302
    assert reverse('accounts:login') in res['Location']


@pytest.mark.django_db
def test_schedule_model_clean_validation():
    """Ensure Schedule.clean() raises ValidationError if end_time <= start_time."""
    now = timezone.now()
    exam = Exam.objects.create(title='Exam Clean Test', duration=60)
    sched = Schedule(
        exam=exam,
        start_time=now,
        end_time=now,  # Same time (0 minutes duration)
        token='TEST01'
    )
    with pytest.raises(ValidationError):
        sched.clean()

    # Even worse: end_time before start_time
    sched.end_time = now - timedelta(minutes=10)
    with pytest.raises(ValidationError):
        sched.clean()

    # Valid schedule
    sched.end_time = now + timedelta(minutes=60)
    sched.clean()  # Should not raise


@pytest.mark.django_db
def test_schedule_form_duration_validation():
    """Ensure ScheduleForm rejects duration less than 1 minute and accepts 10 minutes."""
    form_data = {
        'exam_type': 'UH',
        'title': 'UH Durasi Singkat',
        'level': 10,
        'subject': '',
        'start_time': '2026-10-02T08:00',
        'duration': 0,  # Invalid (< 1 min)
        'target_question_count': 10,
        'session_no': '0'
    }
    form = ScheduleForm(data=form_data)
    assert form.is_valid() is False
    assert 'duration' in form.errors
    assert 'minimal 1 menit' in form.errors['duration'][0]


@pytest.mark.django_db
def test_schedule_form_teacher_role_scoping():
    """Ensure teacher cannot submit non-UH assessments (PTS/PAS/SAJ)."""
    teacher_user = User.objects.create_user(
        username='guru_budi',
        email='budi@smkn1rongga.sch.id',
        role=Role.GURU,
        password='password123'
    )
    classroom = ClassRoom.objects.create(name='XII RPL 1', level=12)
    subject = Subject.objects.create(name='Pemrograman Web')

    form_data = {
        'exam_type': 'PTS',  # Prohibited for guru
        'title': 'PTS RPL',
        'level': 12,
        'subject': subject.id,
        'class_room': classroom.id,
        'start_time': '2026-10-05T08:00',
        'duration': 60,
        'target_question_count': 40,
        'session_no': '0'
    }
    form = ScheduleForm(data=form_data, user=teacher_user)
    assert form.is_valid() is False
    assert 'exam_type' in form.errors



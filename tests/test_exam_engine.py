"""Tests for Core CBT Exam Engine (Task 7)."""
import uuid
import pytest
from datetime import timedelta
from django.contrib.auth import get_user_model
from django.db.utils import IntegrityError
from django.urls import reverse
from django.utils import timezone

from apps.accounts.models import Role
from apps.master_data.models import Subject, Teacher, ClassRoom, Major, Student
from apps.questions.models import Question
from apps.schedules.models import Exam, ExamQuestion, Schedule
from apps.exam_engine.models import ExamSession, StudentAnswer
from apps.exam_engine.utils import (
    initialize_session_answers,
    get_session_questions_payload,
    grade_exam_session,
)

User = get_user_model()


# ==============================================================================
# 1. Model & Relations Tests
# ==============================================================================

@pytest.mark.django_db
def test_exam_session_model_creation_and_properties():
    """Verify ExamSession model fields, UUID pk, status, properties and str representation."""
    major = Major.objects.create(code='RPL', name='Rekayasa Perangkat Lunak')
    classroom = ClassRoom.objects.create(name='XII RPL 1', level=12, major=major)
    subject = Subject.objects.create(name='Pemrograman Web')
    teacher = Teacher.objects.create(full_name='Guru RPL')

    student_user = User.objects.create_user(
        username='siswa1',
        password='password123',
        role=Role.SISWA,
        full_name='Ahmad Siswa'
    )
    student = Student.objects.create(
        user=student_user,
        nis='1234567890',
        full_name='Ahmad Siswa',
        class_room=classroom,
        major=major
    )

    exam = Exam.objects.create(
        teacher=teacher,
        subject=subject,
        title='UAS Pemrograman Web',
        exam_type='PAS',
        duration=90,
        target_question_count=40,
        level=12,
        status='ready',
        token='PASRPL'
    )

    schedule = Schedule.objects.create(
        exam=exam,
        class_room=classroom,
        teacher=teacher,
        start_time=timezone.now(),
        end_time=timezone.now() + timedelta(hours=2),
        token='PASRPL',
        session_no=1,
        room_name='Lab Komputer 1',
        status='active'
    )

    session = ExamSession.objects.create(
        student=student,
        schedule=schedule,
        status='active',
        remaining_seconds=5400,
        violation_count=0,
        score=0.0
    )

    assert isinstance(session.id, uuid.UUID)
    assert session.is_active is True
    assert session.is_locked is False
    assert session.is_finished is False
    assert 'Ahmad Siswa' in str(session)
    assert 'UAS Pemrograman Web' in str(session)
    assert session.answered_count == 0
    assert session.doubt_count == 0

    # Unique constraint test: student + schedule
    with pytest.raises(IntegrityError):
        ExamSession.objects.create(
            student=student,
            schedule=schedule,
            status='active'
        )


@pytest.mark.django_db
def test_student_answer_model_and_grading():
    """Verify StudentAnswer creation, correctness evaluation and unique constraint."""
    subject = Subject.objects.create(name='Bahasa Indonesia')
    teacher = Teacher.objects.create(full_name='Guru Bahasa')
    student_user = User.objects.create_user(username='siswa2', role=Role.SISWA)
    student = Student.objects.create(user=student_user, nis='9876543210', full_name='Budi Siswa')

    exam = Exam.objects.create(teacher=teacher, subject=subject, title='UH Teks Anekdot', duration=60)
    schedule = Schedule.objects.create(
        exam=exam,
        teacher=teacher,
        start_time=timezone.now(),
        end_time=timezone.now() + timedelta(hours=1),
        token='ANEK01',
        status='active'
    )
    session = ExamSession.objects.create(student=student, schedule=schedule)

    q1 = Question.objects.create(
        subject=subject,
        question_text='Apa itu teks anekdot?',
        option_a='Cerita lucu yang mengandung kritik',
        option_b='Teks berita',
        correct_answer='A'
    )
    q2 = Question.objects.create(
        subject=subject,
        question_text='Struktur teks anekdot adalah...',
        option_a='Abstraksi, Orientasi, Krisis, Reaksi, Koda',
        option_b='Tesis, Argumen',
        correct_answer='A'
    )

    ans1 = StudentAnswer.objects.create(
        session=session,
        question=q1,
        chosen_answer='A',
        is_doubt=False
    )
    ans2 = StudentAnswer.objects.create(
        session=session,
        question=q2,
        chosen_answer='B',
        is_doubt=True
    )

    assert isinstance(ans1.id, uuid.UUID)
    assert ans1.evaluate_correctness() is True
    assert ans2.evaluate_correctness() is False

    ans1.save()
    ans2.save()

    assert session.answered_count == 2
    assert session.doubt_count == 1
    assert session.correct_count == 1

    # Unique constraint test: session + question
    with pytest.raises(IntegrityError):
        StudentAnswer.objects.create(session=session, question=q1)


# ==============================================================================
# 2. Token Confirmation & Session Initialization Tests
# ==============================================================================

@pytest.mark.django_db
def test_confirm_token_view_valid_and_invalid(client):
    """Test token verification, session creation and answer sheet initialization."""
    subject = Subject.objects.create(name='Matematika')
    teacher = Teacher.objects.create(full_name='Guru MTK')
    student_user = User.objects.create_user(username='siswa_mtk', password='password123', role=Role.SISWA)
    student = Student.objects.create(user=student_user, nis='111222333', full_name='Siswa MTK')

    exam = Exam.objects.create(
        teacher=teacher,
        subject=subject,
        title='UH Vektor',
        exam_type='UH',
        duration=60,
        status='ready',
        token='VEKTOR'
    )
    schedule = Schedule.objects.create(
        exam=exam,
        teacher=teacher,
        start_time=timezone.now(),
        end_time=timezone.now() + timedelta(hours=2),
        token='VEKTOR',
        status='active'
    )

    q1 = Question.objects.create(subject=subject, question_text='Soal 1', option_a='A', correct_answer='A')
    q2 = Question.objects.create(subject=subject, question_text='Soal 2', option_a='A', correct_answer='B')
    ExamQuestion.objects.create(exam=exam, question=q1, order_number=1)
    ExamQuestion.objects.create(exam=exam, question=q2, order_number=2)

    client.force_login(student_user)

    # 1. Invalid Token Test
    res_invalid = client.post(
        reverse('exam_engine:confirm_token'),
        {'schedule_id': str(schedule.id), 'token': 'WRONG9'},
        HTTP_HX_REQUEST='true'
    )
    assert res_invalid.status_code == 400
    assert 'Token ujian tidak valid' in res_invalid.content.decode('utf-8')

    # 2. Valid Token Test (case-insensitive & whitespace tolerant)
    res_valid = client.post(
        reverse('exam_engine:confirm_token'),
        {'schedule_id': str(schedule.id), 'token': ' vektor '},
        HTTP_HX_REQUEST='true'
    )
    assert res_valid.status_code == 200
    assert 'HX-Redirect' in res_valid.headers
    
    session = ExamSession.objects.filter(student=student, schedule=schedule).first()
    assert session is not None
    assert session.is_active is True
    assert session.remaining_seconds == 3600
    assert session.student_answers.count() == 2


# ==============================================================================
# 3. Exam Interface & Question Swapping Tests
# ==============================================================================

@pytest.mark.django_db
def test_exam_interface_view_and_question_swap(client):
    """Test sterile exam interface rendering and HTMX question viewport swapping."""
    subject = Subject.objects.create(name='Fisika')
    teacher = Teacher.objects.create(full_name='Guru Fisika')
    student_user = User.objects.create_user(username='siswa_fisika', role=Role.SISWA)
    student = Student.objects.create(user=student_user, nis='444555666', full_name='Siswa Fisika')

    exam = Exam.objects.create(teacher=teacher, subject=subject, title='PAT Fisika Terapan', duration=90, status='ready')
    schedule = Schedule.objects.create(
        exam=exam,
        teacher=teacher,
        start_time=timezone.now(),
        end_time=timezone.now() + timedelta(hours=2),
        token='FISIKA',
        status='active'
    )
    session = ExamSession.objects.create(student=student, schedule=schedule, remaining_seconds=5400)

    q1 = Question.objects.create(subject=subject, question_text='Hukum Newton 1', option_a='Inersia', correct_answer='A')
    q2 = Question.objects.create(subject=subject, question_text='Hukum Termodinamika', option_a='Entropi', correct_answer='A')
    ExamQuestion.objects.create(exam=exam, question=q1, order_number=1)
    ExamQuestion.objects.create(exam=exam, question=q2, order_number=2)
    initialize_session_answers(session)

    client.force_login(student_user)

    # 1. Load Main Interface
    res = client.get(reverse('exam_engine:exam_interface', kwargs={'session_id': session.id}))
    assert res.status_code == 200
    assert 'EXAM JINGGA LIVE' in res.content.decode('utf-8')
    assert 'PAT Fisika Terapan' in res.content.decode('utf-8')
    assert 'Hukum Newton 1' in res.content.decode('utf-8')

    # 2. HTMX Question Swap to Question #2
    res_swap = client.get(
        reverse('exam_engine:question_swap', kwargs={'session_id': session.id, 'order_num': 2}),
        HTTP_HX_REQUEST='true'
    )
    assert res_swap.status_code == 200
    assert 'Hukum Termodinamika' in res_swap.content.decode('utf-8')
    assert 'Soal 2 dari 2' in res_swap.content.decode('utf-8')


# ==============================================================================
# 4. Answer Auto-Save with Out-of-Band (OOB) Updates Tests
# ==============================================================================

@pytest.mark.django_db
def test_save_answer_view_with_oob_updates(client):
    """Test saving option selection and doubt toggling with OOB button/counter updates."""
    subject = Subject.objects.create(name='Kimia')
    teacher = Teacher.objects.create(full_name='Guru Kimia')
    student_user = User.objects.create_user(username='siswa_kimia', role=Role.SISWA)
    student = Student.objects.create(user=student_user, nis='777888999', full_name='Siswa Kimia')

    exam = Exam.objects.create(teacher=teacher, subject=subject, title='UH Larutan Asam Basa', duration=60, status='ready')
    schedule = Schedule.objects.create(
        exam=exam,
        teacher=teacher,
        start_time=timezone.now(),
        end_time=timezone.now() + timedelta(hours=1),
        token='KIMIA1',
        status='active'
    )
    session = ExamSession.objects.create(student=student, schedule=schedule)

    q1 = Question.objects.create(
        subject=subject,
        question_text='pH asam adalah...',
        option_a='Kurang dari 7',
        option_b='Lebih dari 7',
        correct_answer='A'
    )
    ExamQuestion.objects.create(exam=exam, question=q1, order_number=1)
    ans1 = StudentAnswer.objects.create(session=session, question=q1)

    client.force_login(student_user)

    # 1. Save Answer A
    res = client.post(
        reverse('exam_engine:save_answer', kwargs={'session_id': session.id}),
        {
            'question_id': str(q1.id),
            'chosen_answer': 'A',
            'order_num': 1,
            'is_doubt': 'false'
        },
        HTTP_HX_REQUEST='true'
    )
    assert res.status_code == 200
    content = res.content.decode('utf-8')
    assert 'hx-swap-oob="outerHTML"' in content
    assert 'nav-btn-1' in content
    assert 'bg-emerald-500' in content

    ans1.refresh_from_db()
    assert ans1.chosen_answer == 'A'
    assert ans1.is_correct is True
    assert ans1.is_doubt is False

    # 2. Toggle Doubt (Ragu-ragu)
    res_doubt = client.post(
        reverse('exam_engine:save_answer', kwargs={'session_id': session.id}),
        {
            'question_id': str(q1.id),
            'chosen_answer': 'A',
            'order_num': 1,
            'is_doubt': 'true'
        },
        HTTP_HX_REQUEST='true'
    )
    assert res_doubt.status_code == 200
    content_doubt = res_doubt.content.decode('utf-8')
    assert 'bg-amber-400' in content_doubt

    ans1.refresh_from_db()
    assert ans1.is_doubt is True


# ==============================================================================
# 5. Anti-Cheat Violation & Screen Lock Tests
# ==============================================================================

@pytest.mark.django_db
def test_violation_handler_and_status_check(client):
    """Test anti-cheat violation count increments, 2+ violations lock, and proctor unlock polling."""
    subject = Subject.objects.create(name='Biologi')
    teacher = Teacher.objects.create(full_name='Guru Biologi')
    student_user = User.objects.create_user(username='siswa_bio', role=Role.SISWA)
    student = Student.objects.create(user=student_user, nis='12121212', full_name='Siswa Biologi')

    exam = Exam.objects.create(teacher=teacher, subject=subject, title='UH Genetika', duration=60, status='ready')
    schedule = Schedule.objects.create(
        exam=exam,
        teacher=teacher,
        start_time=timezone.now(),
        end_time=timezone.now() + timedelta(hours=1),
        token='BIOLOGI',
        status='active'
    )
    session = ExamSession.objects.create(student=student, schedule=schedule, status='active', violation_count=0)

    client.force_login(student_user)

    # 1. First Violation (Warning Toast)
    res_v1 = client.post(reverse('exam_engine:violation_handler', kwargs={'session_id': session.id}))
    assert res_v1.status_code == 200
    assert 'Peringatan Anti-Cheat (1/2)' in res_v1.content.decode('utf-8')
    
    session.refresh_from_db()
    assert session.violation_count == 1
    assert session.status == 'active'

    # 2. Second Violation (Lock Triggered)
    res_v2 = client.post(reverse('exam_engine:violation_handler', kwargs={'session_id': session.id}))
    assert res_v2.status_code == 200
    assert 'Ujian Terkunci!' in res_v2.content.decode('utf-8')
    assert 'lock-screen-overlay' in res_v2.content.decode('utf-8')

    session.refresh_from_db()
    assert session.violation_count == 2
    assert session.status == 'locked'

    # 3. Status Polling while Locked
    res_check_locked = client.get(reverse('exam_engine:check_status', kwargs={'session_id': session.id}))
    assert res_check_locked.status_code == 200
    assert 'Ujian Terkunci!' in res_check_locked.content.decode('utf-8')

    # 4. Proctor unlocks the session
    session.status = 'active'
    session.save()

    res_check_unlocked = client.get(reverse('exam_engine:check_status', kwargs={'session_id': session.id}))
    assert res_check_unlocked.status_code == 200
    assert 'lock-container' in res_check_unlocked.content.decode('utf-8')
    assert 'window.location.reload()' in res_check_unlocked.content.decode('utf-8')


# ==============================================================================
# 6. Finish Exam & Auto-Grading Tests
# ==============================================================================

@pytest.mark.django_db
def test_finish_exam_view_and_score_calculation(client):
    """Test final exam submission, score calculation and finish modal rendering."""
    subject = Subject.objects.create(name='Sejarah')
    teacher = Teacher.objects.create(full_name='Guru Sejarah')
    student_user = User.objects.create_user(username='siswa_sejarah', role=Role.SISWA)
    student = Student.objects.create(user=student_user, nis='333222111', full_name='Siswa Sejarah')

    exam = Exam.objects.create(teacher=teacher, subject=subject, title='PAS Sejarah Indonesia', duration=60, status='ready')
    schedule = Schedule.objects.create(
        exam=exam,
        teacher=teacher,
        start_time=timezone.now(),
        end_time=timezone.now() + timedelta(hours=1),
        token='SEJ001',
        status='active'
    )
    session = ExamSession.objects.create(student=student, schedule=schedule, status='active')

    q1 = Question.objects.create(subject=subject, question_text='Proklamasi 1945', correct_answer='A')
    q2 = Question.objects.create(subject=subject, question_text='Sumpah Pemuda 1928', correct_answer='B')
    q3 = Question.objects.create(subject=subject, question_text='Budi Utomo 1908', correct_answer='C')
    q4 = Question.objects.create(subject=subject, question_text='Hari Pahlawan 10 Nov', correct_answer='D')

    # 3 out of 4 correct -> 75%
    StudentAnswer.objects.create(session=session, question=q1, chosen_answer='A')
    StudentAnswer.objects.create(session=session, question=q2, chosen_answer='B')
    StudentAnswer.objects.create(session=session, question=q3, chosen_answer='C')
    StudentAnswer.objects.create(session=session, question=q4, chosen_answer='A') # Wrong

    client.force_login(student_user)

    # Submit via HTMX
    res = client.post(
        reverse('exam_engine:finish_exam', kwargs={'session_id': session.id}),
        HTTP_HX_REQUEST='true'
    )
    assert res.status_code == 200
    assert 'Ujian Berhasil Dikirim!' in res.content.decode('utf-8')
    assert '75' in res.content.decode('utf-8')

    session.refresh_from_db()
    assert session.status == 'finished'
    assert session.score == 75.0
    assert session.finished_at is not None


# ==============================================================================
# 7. Student Dashboard View Tests
# ==============================================================================

@pytest.mark.django_db
def test_student_dashboard_view(client):
    """Test student dashboard view listing active schedules, logistics and history."""
    major = Major.objects.create(code='TKRO', name='Teknik Kendaraan Ringan Otomotif')
    classroom = ClassRoom.objects.create(name='XI TKRO 1', level=11, major=major)
    subject = Subject.objects.create(name='Kelistrikan Otomotif')
    teacher = Teacher.objects.create(full_name='Guru Otomotif')

    student_user = User.objects.create_user(username='siswa_tkro', role=Role.SISWA, full_name='Dedi Otomotif')
    student = Student.objects.create(
        user=student_user,
        nis='9988776655',
        full_name='Dedi Otomotif',
        class_room=classroom,
        major=major
    )

    exam1 = Exam.objects.create(teacher=teacher, subject=subject, title='UH Sistem Starter', exam_type='UH', duration=45, level=11, status='ready')
    schedule1 = Schedule.objects.create(
        exam=exam1,
        class_room=classroom,
        teacher=teacher,
        start_time=timezone.now(),
        end_time=timezone.now() + timedelta(hours=1),
        token='STR001',
        room_name='Bengkel Otomotif',
        session_no=1,
        status='active'
    )

    # Finished exam
    exam2 = Exam.objects.create(teacher=teacher, subject=subject, title='UH Pengisian', exam_type='UH', duration=45, level=11, status='ready')
    schedule2 = Schedule.objects.create(
        exam=exam2,
        class_room=classroom,
        teacher=teacher,
        start_time=timezone.now() - timedelta(days=1),
        end_time=timezone.now() - timedelta(days=1, hours=-1),
        token='CHG001',
        status='active'
    )
    ExamSession.objects.create(student=student, schedule=schedule2, status='finished', score=88.5, finished_at=timezone.now())

    client.force_login(student_user)

    res = client.get(reverse('exam_engine:student_dashboard'))
    assert res.status_code == 200
    content = res.content.decode('utf-8')
    assert 'Dedi Otomotif' in content
    assert 'XI TKRO 1' in content
    assert 'UH Sistem Starter' in content
    assert 'Bengkel Otomotif' in content
    assert ('88.5' in content or '88,5' in content)


@pytest.mark.django_db
def test_opsi_a_hard_stop_remaining_seconds():
    """Verify calculate_remaining_seconds caps remaining duration by schedule.end_time (Opsi A)."""
    now = timezone.now()
    subject = Subject.objects.create(name='Bahasa Indonesia')
    exam = Exam.objects.create(subject=subject, title='PTS B.Indo', duration=60, status='ready')
    # Schedule closes in 20 minutes
    schedule = Schedule.objects.create(
        exam=exam,
        start_time=now - timedelta(minutes=40),
        end_time=now + timedelta(minutes=20),
        token='INDO01',
        status='active'
    )
    student_user = User.objects.create_user(username='siswa_hardstop', role=Role.SISWA)
    student = Student.objects.create(user=student_user, nis='999111222', full_name='Siswa Hardstop')
    # Student starts now, personal 60m duration would end at now + 60m
    session = ExamSession.objects.create(
        student=student,
        schedule=schedule,
        started_at=now,
        status='active',
        remaining_seconds=3600
    )
    # Remaining seconds should be capped by schedule.end_time (approx 20 minutes = 1200 seconds), NOT 60m (3600s)
    rem = session.calculate_remaining_seconds()
    assert 1190 <= rem <= 1205


@pytest.mark.django_db
def test_confirm_token_time_gates(client):
    """Verify ConfirmTokenView rejects token submission if outside schedule start_time/end_time window."""
    now = timezone.now()
    subject = Subject.objects.create(name='IPAS')
    exam = Exam.objects.create(subject=subject, title='PTS IPAS', duration=60, status='ready')
    student_user = User.objects.create_user(username='siswa_gate', role=Role.SISWA)
    Student.objects.create(user=student_user, nis='999333444', full_name='Siswa Gate')
    client.force_login(student_user)

    # 1. Schedule already ended (e.g. 13:31 test)
    ended_schedule = Schedule.objects.create(
        exam=exam,
        start_time=now - timedelta(hours=2),
        end_time=now - timedelta(minutes=5),
        token='PASSED',
        status='active'
    )
    res_ended = client.post(
        reverse('exam_engine:confirm_token'),
        {'schedule_id': str(ended_schedule.id), 'token': 'PASSED'},
        HTTP_HX_REQUEST='true'
    )
    assert res_ended.status_code == 400
    assert 'telah berakhir' in res_ended.content.decode('utf-8')

    # 2. Schedule not started yet
    future_schedule = Schedule.objects.create(
        exam=exam,
        start_time=now + timedelta(hours=1),
        end_time=now + timedelta(hours=2),
        token='FUTURE',
        status='active'
    )
    res_future = client.post(
        reverse('exam_engine:confirm_token'),
        {'schedule_id': str(future_schedule.id), 'token': 'FUTURE'},
        HTTP_HX_REQUEST='true'
    )
    assert res_future.status_code == 400
    assert 'belum dibuka' in res_future.content.decode('utf-8')


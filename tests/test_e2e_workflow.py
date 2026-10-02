"""End-to-End Workflow Verification Test for Exam Jingga CBT DATH Stack.

Simulates the complete CBT examination lifecycle across 10 critical operational stages:
1. Setup Master Data (Majors, Classes, Teachers, Students, Subjects, Assignments).
2. Create Question Bank (Questions with choices A-E, answer key, points, explanation).
3. Create Exam & Schedule (Assign to Class, Select Questions, Verify Schedule & Generate Token).
4. Student Logs in & accesses Student Dashboard.
5. Student Inputs Token & starts Exam Session.
6. Student answers questions with instant HTMX auto-save.
7. Student tests anti-cheat warning & radar unlock.
8. Student finishes exam (Score calculation and grading).
9. Teacher/Admin opens Live Monitoring & Exam Results.
10. Admin downloads Excel Results report.
"""
from datetime import timedelta
import io
import openpyxl
import pytest
from django.contrib.auth import get_user_model
from django.test import Client
from django.utils import timezone

from apps.accounts.models import Role
from apps.master_data.models import (
    Major,
    ClassRoom,
    Subject,
    Teacher,
    Student,
    TeacherAssignment,
)
from apps.questions.models import Question
from apps.schedules.models import Exam, Schedule, ExamQuestion
from apps.exam_engine.models import ExamSession, StudentAnswer
from apps.reports.models import StudentLogistic

User = get_user_model()


@pytest.mark.django_db
def test_full_cbt_e2e_workflow_lifecycle():
    """
    Comprehensive End-to-End Test executing the complete 10-stage CBT lifecycle.
    """
    # =========================================================================
    # STAGE 1: Setup Master Data (Majors, Classes, Teachers, Students, Assignments)
    # =========================================================================
    # Create Admin User
    admin_user = User.objects.create_superuser(
        username='superadmin',
        email='admin@smkn1rongga.sch.id',
        password='AdminPassword123!',
        role=Role.ADMIN,
    )

    # Create Major & ClassRoom
    major = Major.objects.create(
        name='Teknik Komputer dan Jaringan',
        code='TKJ',
    )
    class_room = ClassRoom.objects.create(
        name='XII TKJ 1',
        level=12,
        major=major,
    )

    # Create Subject
    subject = Subject.objects.create(
        name='Teknologi Layanan Jaringan',
        code='TLJ-12',
    )

    # Create Teacher & User
    teacher_user = User.objects.create_user(
        username='198501012010011001',
        email='guru.tkj@smkn1rongga.sch.id',
        password='TeacherPassword123!',
        role=Role.GURU,
    )
    teacher = Teacher.objects.create(
        user=teacher_user,
        nip='198501012010011001',
        full_name='Budi Haryanto, S.Kom.',
        role_level='guru',
    )

    # Create Teacher Assignment
    assignment = TeacherAssignment.objects.create(
        teacher=teacher,
        subject=subject,
        class_room=class_room,
    )

    # Create Student & User
    student_user = User.objects.create_user(
        username='0061234567',
        email='siswa.ahmad@smkn1rongga.sch.id',
        password='StudentPassword123!',
        role=Role.SISWA,
    )
    student = Student.objects.create(
        user=student_user,
        nis='0061234567',
        full_name='Ahmad Dahlan',
        class_room=class_room,
        major=major,
        status='aktif',
    )

    assert major.pk is not None
    assert class_room.pk is not None
    assert teacher.user.role == 'guru'
    assert student.user.role == 'siswa'
    assert assignment.class_room == class_room

    # =========================================================================
    # STAGE 2: Create Question Bank (Questions with choices A-E)
    # =========================================================================
    q_data = [
        ('Apa fungsi utama protokol DHCP pada jaringan komputer?', 'A',
         'Memberikan konfigurasi IP address secara otomatis ke client',
         'Menerjemahkan nama domain menjadi IP address',
         'Mengenkripsi jalur komunikasi data',
         'Menyaring paket data yang masuk',
         'Membatasi bandwidth pengguna'),
        ('Protokol default yang digunakan untuk web aman terenkripsi adalah?', 'B',
         'HTTP port 80',
         'HTTPS port 443',
         'FTP port 21',
         'SSH port 22',
         'Telnet port 23'),
        ('Perangkat jaringan yang bekerja pada layer 3 OSI adalah?', 'C',
         'Hub',
         'Switch Unmanaged',
         'Router',
         'Repeater',
         'Network Card'),
        ('Perintah terminal Linux untuk memeriksa konektivitas jaringan adalah?', 'D',
         'ls -la',
         'chmod 755',
         'cat /etc/passwd',
         'ping 8.8.8.8',
         'mkdir backup'),
        ('Kabel UTP kategori 6 (Cat6) standar menggunakan konektor tipe?', 'E',
         'BNC',
         'SC Fiber',
         'RJ-11',
         'LC Duplex',
         'RJ-45'),
    ]

    questions = []
    for q_text, correct_opt, opt_a, opt_b, opt_c, opt_d, opt_e in q_data:
        q = Question.objects.create(
            subject=subject,
            created_by=teacher,
            level=12,
            question_text=q_text,
            option_a=opt_a,
            option_b=opt_b,
            option_c=opt_c,
            option_d=opt_d,
            option_e=opt_e,
            correct_answer=correct_opt,
        )
        questions.append(q)

    assert len(questions) == 5
    assert all(q.option_a for q in questions)

    # =========================================================================
    # STAGE 3: Create Exam & Schedule (Assign to Class, Select Questions, Verify)
    # =========================================================================
    exam = Exam.objects.create(
        title='Penilaian Akhir Semester TLJ XII',
        exam_type='PAS',
        subject=subject,
        teacher=teacher,
        level=12,
        duration=60,
        target_question_count=5,
        token='JNG888',
        status='draft',
    )

    # Attach questions to exam
    for idx, q in enumerate(questions, start=1):
        ExamQuestion.objects.create(
            exam=exam,
            question=q,
            order_number=idx,
        )

    assert exam.exam_questions.count() == 5

    # Create Schedule
    now = timezone.now()
    schedule = Schedule.objects.create(
        exam=exam,
        class_room=class_room,
        teacher=teacher,
        token='JNG888',
        start_time=now - timedelta(minutes=10),
        end_time=now + timedelta(hours=2),
        status='active',
        room_name='Lab Komputer 1',
        session_no=1,
    )

    # Validate Exam & Schedule state
    exam.status = 'validated'
    exam.save(update_fields=['status'])

    assert schedule.status == 'active'
    assert exam.status == 'validated'
    assert schedule.token == 'JNG888'

    # =========================================================================
    # STAGE 4: Student Logs In & Accesses Student Dashboard
    # =========================================================================
    student_client = Client()
    student_client.force_login(student_user)

    dashboard_resp = student_client.get('/student-dashboard/')
    assert dashboard_resp.status_code == 200
    assert 'student' in dashboard_resp.context
    assert 'available_exams' in dashboard_resp.context
    assert len(dashboard_resp.context['available_exams']) >= 1
    assert dashboard_resp.context['available_exams'][0]['schedule'].id == schedule.id

    # =========================================================================
    # STAGE 5: Student Inputs Token & Starts Exam Session
    # =========================================================================
    # Invalid token attempt
    invalid_token_resp = student_client.post(
        '/exam/confirm-token/',
        {'schedule_id': str(schedule.id), 'token': 'WRONG9'},
        HTTP_HX_REQUEST='true'
    )
    assert invalid_token_resp.status_code == 400

    # Valid token submission
    confirm_resp = student_client.post(
        '/exam/confirm-token/',
        {'schedule_id': str(schedule.id), 'token': 'JNG888'},
        HTTP_HX_REQUEST='true'
    )
    assert confirm_resp.status_code == 200
    assert 'HX-Redirect' in confirm_resp.headers

    # Verify ExamSession was initialized
    exam_session = ExamSession.objects.get(student=student, schedule=schedule)
    assert exam_session.status == 'active'
    assert exam_session.student_answers.count() == 5

    # =========================================================================
    # STAGE 6: Student Answers Questions with Instant HTMX Auto-Save
    # =========================================================================
    # Access exam interface
    interface_resp = student_client.get(f'/exam/session/{exam_session.id}/')
    assert interface_resp.status_code == 200
    assert interface_resp.context['total_count'] == 5

    # Student answers all 5 questions correctly (A, B, C, D, E)
    expected_answers = ['A', 'B', 'C', 'D', 'E']
    for idx, (q, ans_opt) in enumerate(zip(questions, expected_answers), start=1):
        save_resp = student_client.post(
            f'/exam/session/{exam_session.id}/save-answer/',
            {
                'question_id': str(q.id),
                'chosen_answer': ans_opt,
                'is_doubt': 'false',
                'order_num': str(idx),
            },
            HTTP_HX_REQUEST='true'
        )
        assert save_resp.status_code == 200
        assert f'nav-btn-{idx}' in save_resp.content.decode('utf-8')

        # Verify StudentAnswer updated in DB
        db_answer = StudentAnswer.objects.get(session=exam_session, question=q)
        assert db_answer.chosen_answer == ans_opt
        assert db_answer.is_correct is True

    # Test swap question viewport
    swap_resp = student_client.get(
        f'/exam/session/{exam_session.id}/question/3/',
        HTTP_HX_REQUEST='true'
    )
    assert swap_resp.status_code == 200
    assert 'Perangkat jaringan yang bekerja pada layer 3 OSI' in swap_resp.content.decode('utf-8')

    # =========================================================================
    # STAGE 7: Student Tests Anti-Cheat Warning & Radar Unlock
    # =========================================================================
    # Violation 1: Warning Toast
    v1_resp = student_client.post(
        f'/exam/session/{exam_session.id}/violation/',
        HTTP_HX_REQUEST='true'
    )
    assert v1_resp.status_code == 200
    assert 'Peringatan Anti-Cheat (1/2)' in v1_resp.content.decode('utf-8')
    exam_session.refresh_from_db()
    assert exam_session.violation_count == 1
    assert exam_session.status == 'active'

    # Violation 2: Locked Overlay
    v2_resp = student_client.post(
        f'/exam/session/{exam_session.id}/violation/',
        HTTP_HX_REQUEST='true'
    )
    assert v2_resp.status_code == 200
    assert 'Ujian Terkunci' in v2_resp.content.decode('utf-8')
    exam_session.refresh_from_db()
    assert exam_session.violation_count == 2
    assert exam_session.status == 'locked'

    # Teacher/Admin Unlocks Session
    admin_client = Client()
    admin_client.force_login(admin_user)

    unlock_resp = admin_client.post(
        f'/session-management/unlock/{exam_session.id}/',
        HTTP_HX_REQUEST='true'
    )
    assert unlock_resp.status_code == 200
    exam_session.refresh_from_db()
    assert exam_session.status == 'active'
    assert exam_session.violation_count == 0

    # Student Polls Status Check after unlock
    check_status_resp = student_client.get(
        f'/exam/session/{exam_session.id}/check-status/',
        HTTP_HX_REQUEST='true'
    )
    assert check_status_resp.status_code == 200
    assert 'window.location.reload()' in check_status_resp.content.decode('utf-8')

    # =========================================================================
    # STAGE 8: Student Finishes Exam (Score Calculation and Grading)
    # =========================================================================
    finish_resp = student_client.post(
        f'/exam/session/{exam_session.id}/finish/',
        HTTP_HX_REQUEST='true'
    )
    assert finish_resp.status_code == 200
    assert '100' in finish_resp.content.decode('utf-8')

    exam_session.refresh_from_db()
    assert exam_session.status == 'finished'
    assert exam_session.score == 100.0
    assert exam_session.finished_at is not None

    # Re-accessing interface redirects back to student dashboard
    finish_revisit = student_client.get(f'/exam/session/{exam_session.id}/')
    assert finish_revisit.status_code == 302
    assert finish_revisit.url == '/student/dashboard/'

    # =========================================================================
    # STAGE 9: Teacher/Admin Opens Live Monitoring & Exam Results
    # =========================================================================
    # Live Monitoring
    monitoring_resp = admin_client.get(
        f'/session-management/?schedule_id={schedule.id}'
    )
    assert monitoring_resp.status_code == 200
    assert monitoring_resp.context['finished_count'] >= 1

    # Live Monitoring Table Partial
    table_resp = admin_client.get(
        f'/session-management/table/?schedule_id={schedule.id}',
        HTTP_HX_REQUEST='true'
    )
    assert table_resp.status_code == 200
    assert 'Ahmad Dahlan' in table_resp.content.decode('utf-8')
    assert 'Selesai' in table_resp.content.decode('utf-8')

    # Exam Results View
    results_resp = admin_client.get(f'/exam-results/{exam.id}/')
    assert results_resp.status_code == 200
    assert results_resp.context['exam'].id == exam.id
    assert results_resp.context['stats']['avg'] == 100.0
    assert results_resp.context['stats']['passed_count'] == 1

    # Distractor Analysis View
    analysis_resp = admin_client.get(f'/exam-results/{exam.id}/analysis/')
    assert analysis_resp.status_code == 200
    assert 'analysis' in analysis_resp.context
    assert len(analysis_resp.context['analysis']) == 5
    # First item was answered A by 1 student
    assert analysis_resp.context['analysis'][0]['distro']['A'] == 1

    # =========================================================================
    # STAGE 10: Admin Downloads Excel Results Report
    # =========================================================================
    export_resp = admin_client.get(f'/exam-results/{exam.id}/export/')
    assert export_resp.status_code == 200
    assert (
        export_resp['Content-Type']
        == 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    assert 'attachment;' in export_resp['Content-Disposition']

    # Validate Excel File Integrity with openpyxl
    excel_stream = io.BytesIO(export_resp.content)
    wb = openpyxl.load_workbook(excel_stream)
    sheet = wb.active
    assert sheet is not None
    
    # Check that student name and score 100 exist in worksheet cells
    found_student = False
    found_score = False
    for row in sheet.iter_rows(values_only=True):
        row_str = " ".join([str(v) for v in row if v is not None]).upper()
        if 'AHMAD DAHLAN' in row_str:
            found_student = True
        if '100' in row_str:
            found_score = True

    assert found_student is True
    assert found_score is True


@pytest.mark.django_db
def test_production_settings_configuration_integrity():
    """Verify production settings properties and WhiteNoise storage configuration."""
    from config.settings import production as prod_settings
    
    assert prod_settings.DEBUG is False
    assert prod_settings.STORAGES['staticfiles']['BACKEND'] in [
        'whitenoise.storage.CompressedStaticFilesStorage',
        'whitenoise.storage.CompressedManifestStaticFilesStorage'
    ]
    assert prod_settings.SECURE_PROXY_SSL_HEADER == ('HTTP_X_FORWARDED_PROTO', 'https')
    assert prod_settings.SESSION_COOKIE_SECURE is True
    assert prod_settings.CSRF_COOKIE_SECURE is True
    assert prod_settings.X_FRAME_OPTIONS == 'DENY'
    assert len(prod_settings.ALLOWED_HOSTS) > 0
    assert 'exam.smkn1rongga.sch.id' in prod_settings.ALLOWED_HOSTS
    assert prod_settings.KEYCLOAK_CLIENT_ID == 'exam-jingga'

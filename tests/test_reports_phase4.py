"""Fase 4 audit: peserta yang diharapkan, rekap, analisis, Excel, logistik, cetak."""
import io
from datetime import timedelta

import openpyxl
import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone

from apps.accounts.models import Role
from apps.core.models import SchoolSetting
from apps.exam_engine.eligibility import expected_students_for_exam
from apps.exam_engine.models import ExamSession, StudentAnswer
from apps.master_data.models import ClassRoom, Student, Subject, Teacher, TeacherAssignment
from apps.questions.models import Question
from apps.reports.models import StudentLogistic
from apps.reports.utils import calculate_distractor_analysis, excel_safe
from apps.schedules.models import Exam, ExamQuestion, Schedule

User = get_user_model()


@pytest.fixture
def world(db):
    c1 = ClassRoom.objects.create(name='X R4 1', level=10)
    c2 = ClassRoom.objects.create(name='X R4 2', level=10)
    subject = Subject.objects.create(name='Mapel R4')
    tuser = User.objects.create_user(username='guru_r4', role=Role.GURU)
    teacher = Teacher.objects.create(user=tuser, full_name='Guru R4', email='r4@x.id')
    TeacherAssignment.objects.create(teacher=teacher, subject=subject, class_room=c1)
    exam = Exam.objects.create(teacher=teacher, subject=subject, title='UH R4', exam_type='UH', level=10,
                               status='validated', target_question_count=2)
    now = timezone.now()
    sch = Schedule.objects.create(exam=exam, class_room=c1, teacher=teacher, start_time=now - timedelta(hours=1),
                                  end_time=now + timedelta(hours=1), token='R4R4R4')
    qs = []
    for i, key in enumerate(['A', 'B']):
        q = Question.objects.create(subject=subject, level=10, created_by=teacher, question_text=f'Q{i}',
                                    option_a='a', option_b='b', option_c='c', option_d='d', option_e='e', correct_answer=key)
        ExamQuestion.objects.create(exam=exam, question=q, order_number=i + 1)
        qs.append(q)
    students = []
    for i in range(4):
        u = User.objects.create_user(username=f'r4s{i}', nis=f'r4s{i}', role=Role.SISWA)
        students.append(Student.objects.create(user=u, nis=f'r4s{i}', full_name=f'Siswa {i}', class_room=c1))
    outsider_user = User.objects.create_user(username='r4out', nis='r4out', role=Role.SISWA)
    outsider = Student.objects.create(user=outsider_user, nis='r4out', full_name='Kelas Lain', class_room=c2)
    admin = User.objects.create_user(username='admin_r4', role=Role.ADMIN)
    return locals()


def _finish(sch, student, answers, score):
    sess = ExamSession.objects.create(student=student, schedule=sch, status='finished', score=score,
                                      finished_at=timezone.now())
    for n, (q, choice) in enumerate(answers, start=1):
        a = StudentAnswer.objects.create(session=sess, question=q, chosen_answer=choice, order_number=n)
        a.evaluate_correctness()
        a.save()
    return sess


@pytest.mark.django_db
def test_expected_students_only_the_scheduled_class(world):
    ids = set(expected_students_for_exam(world['exam']).values_list('id', flat=True))
    assert ids == {s.id for s in world['students']}


@pytest.mark.django_db
def test_monitoring_count_matches_expected(client, world):
    client.force_login(world['admin'])
    res = client.get(reverse('reports:session_monitoring'), {'schedule_id': world['sch'].id})
    assert res.context['total_count'] == 4


@pytest.mark.django_db
def test_rekap_counts_blank_separately_and_uses_kkm(client, world):
    q1, q2 = world['qs']
    _finish(world['sch'], world['students'][0], [(q1, 'A'), (q2, None)], 50.0)
    settings = SchoolSetting.get_settings()
    settings.kkm = 50
    settings.save()
    client.force_login(world['admin'])

    res = client.get(reverse('reports:exam_results_detail', args=[world['exam'].id]))

    row = next(p for p in res.context['participants'] if p['nis'] == 'r4s0')
    assert (row['correct_count'], row['wrong_count'], row['blank_count']) == (1, 0, 1)
    assert row['is_passed'] is True
    assert res.context['stats']['kkm'] == 50


@pytest.mark.django_db
def test_discrimination_index(world):
    q1, q2 = world['qs']
    s = world['students']
    _finish(world['sch'], s[0], [(q1, 'A'), (q2, 'B')], 100)
    _finish(world['sch'], s[1], [(q1, 'A'), (q2, 'B')], 100)
    _finish(world['sch'], s[2], [(q1, 'C'), (q2, 'B')], 50)
    _finish(world['sch'], s[3], [(q1, 'C'), (q2, 'C')], 0)

    data = calculate_distractor_analysis(world['exam'])['analysis_data']

    first = data[0]
    assert first['discrimination'] == 1.0
    assert first['distro']['C'] == 2


def test_excel_safe_neutralises_formulas():
    assert excel_safe('=HYPERLINK("x")') == '\'=HYPERLINK("x")'
    assert excel_safe('Budi') == 'Budi'
    assert excel_safe(5) == 5


@pytest.mark.django_db
def test_export_escapes_student_name_formula(client, world):
    Student.objects.filter(pk=world['students'][0].pk).update(full_name='=1+1')
    client.force_login(world['admin'])
    res = client.get(reverse('reports:exam_results_export', args=[world['exam'].id]))
    wb = openpyxl.load_workbook(io.BytesIO(res.content))
    values = [c.value for row in wb['Rekap Nilai'].iter_rows() for c in row]
    assert "'=1+1" in values


@pytest.mark.django_db
def test_logistics_refuses_when_capacity_too_small(client, world):
    StudentLogistic.objects.create(student=world['students'][0], room_name='LAMA', session_name='SESI 9')
    client.force_login(world['admin'])

    client.post(reverse('reports:logistics_generate'), {'levels': '10', 'room_count': 1, 'capacity': 2, 'sessions_count': 1})

    assert StudentLogistic.objects.filter(room_name='LAMA').exists()
    assert StudentLogistic.objects.count() == 1


@pytest.mark.django_db
def test_logistics_allocates_everyone_when_capacity_fits(client, world):
    client.force_login(world['admin'])
    client.post(reverse('reports:logistics_generate'), {'levels': '10', 'room_count': 1, 'capacity': 3, 'sessions_count': 2})
    assert StudentLogistic.objects.count() == 5


@pytest.mark.django_db
def test_attendance_has_no_fake_rows_without_allocation(client, world):
    client.force_login(world['admin'])
    res = client.get(reverse('reports:attendance_list'))
    assert res.context['groups'] == []
    assert 'Belum ada alokasi' in res.content.decode()


@pytest.mark.django_db
def test_door_list_print_format(client, world):
    StudentLogistic.objects.create(student=world['students'][0], room_name='RUANG 01', session_name='SESI 1')
    client.force_login(world['admin'])
    res = client.get(reverse('reports:attendance_list'), {'type': 'door', 'print': 'true'})
    html = res.content.decode()
    assert 'DAFTAR PESERTA' in html
    assert 'Tanda Tangan' not in html


@pytest.mark.django_db
def test_schedule_card_links_to_results(client, world):
    client.force_login(world['admin'])
    html = client.get(reverse('schedules:list'), {'date_filter': 'Semua Ujian'}).content.decode()
    assert reverse('reports:exam_results_detail', args=[world['exam'].id]) in html


@pytest.mark.django_db
def test_student_dashboard_room_from_logistics(client, world):
    StudentLogistic.objects.create(student=world['students'][1], room_name='LAB 2', session_name='SESI 2')
    client.force_login(world['students'][1].user)
    res = client.get(reverse('exam_engine:student_dashboard'))
    assert res.context['logistics'] == {'room_name': 'LAB 2', 'session_name': 'SESI 2'}


@pytest.mark.django_db
def test_results_list_rejects_malformed_exam_id(client, world):
    client.force_login(world['admin'])
    assert client.get(reverse('reports:exam_results_list'), {'exam_id': 'bukan-uuid'}).status_code == 404

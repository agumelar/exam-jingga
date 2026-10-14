"""Tampilan ujian di HP: layar tetap menyala, zoom dan ukuran teks, jendela token, teks soal, label tombol."""
import re
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
QUESTION = 'Apa fungsi utama tag HTML form?'


@pytest.fixture
def pages(db, client):
    cls = ClassRoom.objects.create(name='10 Uji', level=10)
    subject = Subject.objects.create(name='Mapel HP')
    tu = User.objects.create_user(username='guru_hp', role=Role.GURU)
    teacher = Teacher.objects.create(user=tu, full_name='Guru HP', email='guru_hp@x.id')
    TeacherAssignment.objects.create(teacher=teacher, subject=subject, class_room=cls)
    exam = Exam.objects.create(teacher=teacher, subject=subject, title='UH HP', exam_type='UH', level=10,
                               status='validated', duration=30, target_question_count=2, token='HP0001',
                               shuffle_questions=False, shuffle_options=False)
    for i in range(2):
        q = Question.objects.create(subject=subject, level=10, created_by=teacher, question_text=QUESTION,
                                    option_a='a', option_b='b', option_c='c', option_d='d', option_e='e',
                                    correct_answer='A')
        ExamQuestion.objects.create(exam=exam, question=q, order_number=i + 1)
    now = timezone.now()
    sch = Schedule.objects.create(exam=exam, class_room=cls, teacher=teacher, start_time=now - timedelta(minutes=1),
                                  end_time=now + timedelta(hours=1), token='HP0001', teacher_quota=2)
    su = User.objects.create_user(username='9999000001', nis='9999000001', role=Role.SISWA)
    student = Student.objects.create(user=su, nis='9999000001', full_name='Siswa Uji 1', class_room=cls, status='aktif')
    client.force_login(su)
    dashboard = client.get(reverse('exam_engine:student_dashboard')).content.decode()
    client.post(reverse('exam_engine:confirm_token'), {'schedule_id': str(sch.id), 'token': 'HP0001'}, HTTP_HX_REQUEST='true')
    session = ExamSession.objects.get(student=student)
    exam_page = client.get(reverse('exam_engine:exam_interface', args=[session.id])).content.decode()
    return {'dashboard': dashboard, 'exam': exam_page}


def test_screen_stays_awake_during_exam(pages):
    # Layar HP yang padam sendiri memicu visibilitychange dan tercatat sebagai pelanggaran
    assert "navigator.wakeLock.request('screen')" in pages['exam']


def test_students_can_zoom(pages):
    viewport = re.search(r'<meta name="viewport" content="([^"]+)"', pages['exam']).group(1)
    assert 'user-scalable=no' not in viewport
    assert 'maximum-scale' not in viewport
    # Keyboard HP mengecilkan area tata letak, sehingga jendela di tengah layar tidak tertutup
    assert 'interactive-widget=resizes-content' in viewport


def test_text_size_controls_reachable_on_phone(pages):
    drawer = pages['exam'].split('Daftar Nomor Soal', 1)[1]
    assert "fontSize = 'large'" in drawer
    assert 'Ukuran teks' in drawer


def test_question_text_has_no_leading_whitespace(pages):
    assert re.search(r'whitespace-pre-wrap[^"]*"\s*>' + re.escape(QUESTION) + '<', pages['exam'])


def test_bottom_bar_labels_are_indonesian(pages):
    bar = pages['exam'].split('aria-label="Navigasi Ujian Jempol"', 1)[1].split('</nav>', 1)[0]
    assert '<span>Kembali</span>' in bar and '<span>Lanjut</span>' in bar
    assert '<span>Prev</span>' not in bar and '<span>Next</span>' not in bar


def test_token_modal_fits_small_phones_and_sits_above_keyboard(pages):
    modal = pages['dashboard'].split('x-show="showTokenModal"', 1)[1].split('</template>', 1)[0]
    container = re.search(r'class="([^"]+)"', modal).group(1)
    assert 'items-start' in container and 'sm:items-center' in container
    # Atribut class biasa, bukan :class milik Alpine
    box = re.search(r'maxlength="1".*?\s(?<!:)class="([^"]+)"', modal, re.S).group(1)
    assert 'flex-1' in box and 'min-w-0' in box

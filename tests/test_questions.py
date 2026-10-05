"""Tests for Question Bank Module (Task 5)."""
import io
import uuid
import pytest
from PIL import Image
from django.core.files.uploadedfile import SimpleUploadedFile
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.urls import reverse

from apps.accounts.models import Role
from apps.master_data.models import Subject, Teacher, ClassRoom, TeacherAssignment
from apps.questions.models import Question
from apps.questions.forms import QuestionForm

User = get_user_model()


def generate_dummy_image(name="test_image.png"):
    """Helper to generate a valid in-memory PNG image for testing file uploads."""
    file = io.BytesIO()
    image = Image.new('RGB', (100, 100), color=(234, 88, 12))
    image.save(file, 'PNG')
    file.seek(0)
    return SimpleUploadedFile(name, file.read(), content_type='image/png')


# ==============================================================================
# 1. Question Model & Form Tests
# ==============================================================================

@pytest.mark.django_db
def test_question_model_creation_and_options_helper():
    """Verify Question model fields, UUID pk, str representation, and get_options helper."""
    subject = Subject.objects.create(name='Pemrograman Web')
    teacher = Teacher.objects.create(full_name='Pak Ahmad, S.Kom')

    q = Question.objects.create(
        subject=subject,
        created_by=teacher,
        level=11,
        question_text='Apa kepanjangan dari HTML?',
        option_a='Hyper Text Markup Language',
        option_b='High Technical Modern Language',
        option_c='Home Tool Markup Language',
        option_d='Hyperlinks Text Module Language',
        option_e='None of the above',
        correct_answer='A'
    )

    assert isinstance(q.id, uuid.UUID)
    assert 'Pemrograman Web' in str(q)
    assert 'Kelas 11' in str(q)
    assert q.correct_answer == 'A'

    options = q.get_options()
    assert len(options) == 5
    assert options[0]['key'] == 'A'
    assert options[0]['text'] == 'Hyper Text Markup Language'
    assert options[0]['is_correct'] is True
    assert options[1]['key'] == 'B'
    assert options[1]['is_correct'] is False


@pytest.mark.django_db
def test_question_model_clean_validation():
    """Verify clean method validates correct_answer choices."""
    subject = Subject.objects.create(name='Matematika')
    q = Question(
        subject=subject,
        level=10,
        question_text='Berapakah 2 + 2?',
        option_a='4',
        option_b='3',
        option_c='5',
        option_d='6',
        option_e='7',
        correct_answer='Z'  # Invalid choice
    )
    with pytest.raises(ValidationError):
        q.clean()


@pytest.mark.django_db
def test_question_form_save_with_image_and_clear():
    """Verify QuestionForm processes image uploads and handles clearing images."""
    subject = Subject.objects.create(name='Basis Data')
    img = generate_dummy_image('soal.png')
    img_opt = generate_dummy_image('opsi_a.png')

    form_data = {
        'subject': str(subject.id),
        'level': 12,
        'question_text': 'Perhatikan diagram ERD berikut:',
        'option_a': 'Relasi 1 to Many',
        'option_b': 'Relasi Many to Many',
        'option_c': 'Relasi 1 to 1',
        'option_d': 'Tabel Master',
        'option_e': 'Primary Key',
        'correct_answer': 'B',
    }
    file_data = {
        'question_image': img,
        'image_a': img_opt,
    }

    form = QuestionForm(data=form_data, files=file_data)
    assert form.is_valid(), form.errors
    q = form.save()

    assert q.question_image.name is not None
    assert q.image_a.name is not None
    assert q.correct_answer == 'B'

    # Now clear the images using form clear flags
    clear_form_data = {
        'subject': str(subject.id),
        'level': 12,
        'question_text': 'Perhatikan diagram ERD berikut (update):',
        'option_a': 'Relasi 1 to Many',
        'option_b': 'Relasi Many to Many',
        'option_c': 'Relasi 1 to 1',
        'option_d': 'Tabel Master',
        'option_e': 'Primary Key',
        'correct_answer': 'B',
        'clear_question_image': True,
        'clear_image_a': True,
    }
    form2 = QuestionForm(data=clear_form_data, instance=q)
    assert form2.is_valid(), form2.errors
    updated_q = form2.save()
    assert not updated_q.question_image
    assert not updated_q.image_a


# ==============================================================================
# 2. Filtering & Search Logic Tests
# ==============================================================================

@pytest.mark.django_db
def test_question_filtering_queries():
    """Verify filtering questions by Subject, Level, Teacher, and Search keyword."""
    s1 = Subject.objects.create(name='Fisika')
    s2 = Subject.objects.create(name='Kimia')

    t1 = Teacher.objects.create(full_name='Guru Fisika')
    t2 = Teacher.objects.create(full_name='Guru Kimia')

    q1 = Question.objects.create(
        subject=s1,
        created_by=t1,
        level=10,
        question_text='Hukum Newton pertama tentang inersia',
        correct_answer='A'
    )
    q2 = Question.objects.create(
        subject=s1,
        created_by=t1,
        level=11,
        question_text='Persamaan gerak melingkar beraturan',
        correct_answer='B'
    )
    q3 = Question.objects.create(
        subject=s2,
        created_by=t2,
        level=10,
        question_text='Struktur atom hidrogen dan elektron',
        correct_answer='C'
    )

    # Filter by Subject
    assert Question.objects.filter(subject=s1).count() == 2
    assert Question.objects.filter(subject=s2).count() == 1

    # Filter by Level
    assert Question.objects.filter(level=10).count() == 2
    assert Question.objects.filter(level=11).count() == 1

    # Filter by Teacher
    assert Question.objects.filter(created_by=t1).count() == 2

    # Search keyword
    assert Question.objects.filter(question_text__icontains='newton').count() == 1
    assert Question.objects.filter(question_text__icontains='atom').count() == 1


# ==============================================================================
# 3. View & HTMX Endpoints Tests
# ==============================================================================

@pytest.mark.django_db
def test_bank_soal_view_admin(client):
    """Verify BankSoalView renders dashboard for Admin with all questions."""
    admin_user = User.objects.create_superuser(username='admin_test', email='admin@test.com', password='password123')
    client.force_login(admin_user)

    s = Subject.objects.create(name='Bahasa Indonesia')
    Question.objects.create(subject=s, level=10, question_text='Ide pokok paragraf di atas adalah...', correct_answer='A')

    response = client.get(reverse('questions:bank_soal'))
    assert response.status_code == 200
    content = response.content.decode()
    assert 'Bank Soal' in content
    assert 'Bahasa Indonesia' in content
    assert 'Ide pokok paragraf' in content


@pytest.mark.django_db
def test_bank_soal_view_teacher_scoping(client):
    """Verify Teacher sees questions created by them or their assigned subjects."""
    teacher_user = User.objects.create_user(
        username='guru_eko',
        email='eko@smkn1rongga.sch.id',
        full_name='Eko Prasetyo',
        role=Role.GURU,
        password='password123'
    )
    teacher = Teacher.objects.create(user=teacher_user, full_name='Eko Prasetyo', email='eko@smkn1rongga.sch.id')

    other_teacher = Teacher.objects.create(full_name='Guru Lain', email='lain@test.com')

    s_eko = Subject.objects.create(name='Algoritma')
    s_other = Subject.objects.create(name='Sejarah')

    q_eko = Question.objects.create(subject=s_eko, created_by=teacher, level=10, question_text='Pseudocode flowchart', correct_answer='A')
    q_other = Question.objects.create(subject=s_other, created_by=other_teacher, level=12, question_text='Perang Diponegoro', correct_answer='B')

    client.force_login(teacher_user)
    response = client.get(reverse('questions:bank_soal'))
    assert response.status_code == 200
    content = response.content.decode()
    assert 'Pseudocode flowchart' in content
    assert 'Perang Diponegoro' not in content


@pytest.mark.django_db
def test_question_filter_view_htmx(client):
    """Verify QuestionFilterView handles HTMX request with search and level filters."""
    admin_user = User.objects.create_superuser(username='admin2', email='admin2@test.com', password='password123')
    client.force_login(admin_user)

    s = Subject.objects.create(name='Matematika')
    q1 = Question.objects.create(subject=s, level=10, question_text='Integral tak tentu', correct_answer='A')
    q2 = Question.objects.create(subject=s, level=12, question_text='Matriks ordo 3x3', correct_answer='B')

    # Filter level 12 via HTMX
    response = client.get(
        reverse('questions:filter') + '?level=12',
        HTTP_HX_REQUEST='true'
    )
    assert response.status_code == 200
    content = response.content.decode()
    assert 'Matriks ordo 3x3' in content
    assert 'Integral tak tentu' not in content


@pytest.mark.django_db
def test_question_create_view_get_and_post_htmx(client):
    """Verify QuestionCreateView GET modal form and POST create action via HTMX."""
    admin_user = User.objects.create_superuser(username='admin3', email='admin3@test.com', password='password123')
    client.force_login(admin_user)

    subject = Subject.objects.create(name='Desain Grafis')

    # 1. GET Create Modal
    get_res = client.get(reverse('questions:create') + f'?subject_id={subject.id}&level=10')
    assert get_res.status_code == 200
    assert 'Tambah Butir Soal Baru' in get_res.content.decode()

    # 2. POST Create via HTMX
    post_data = {
        'subject': str(subject.id),
        'level': 10,
        'question_text': 'Warna primer dalam model warna subtractive adalah?',
        'option_a': 'Cyan, Magenta, Yellow',
        'option_b': 'Red, Green, Blue',
        'option_c': 'Black and White',
        'option_d': 'Monochrome',
        'option_e': 'Pastel',
        'correct_answer': 'A',
    }
    post_res = client.post(
        reverse('questions:create'),
        data=post_data,
        HTTP_HX_REQUEST='true'
    )
    assert post_res.status_code == 200
    assert 'Cyan, Magenta, Yellow' in post_res.content.decode()
    assert Question.objects.filter(question_text__icontains='Warna primer').exists()


@pytest.mark.django_db
def test_question_edit_view_get_and_post_htmx(client):
    """Verify QuestionEditView GET modal form and POST update action via HTMX."""
    admin_user = User.objects.create_superuser(username='admin4', email='admin4@test.com', password='password123')
    client.force_login(admin_user)

    subject = Subject.objects.create(name='Jaringan Komputer')
    q = Question.objects.create(
        subject=subject,
        level=11,
        question_text='Alamat default gateway?',
        option_a='192.168.1.1',
        option_b='127.0.0.1',
        correct_answer='A'
    )

    # 1. GET Edit Modal
    get_res = client.get(reverse('questions:edit', kwargs={'pk': q.id}))
    assert get_res.status_code == 200
    assert 'Update Butir Soal' in get_res.content.decode()

    # 2. POST Edit via HTMX
    update_data = {
        'subject': str(subject.id),
        'level': 11,
        'cp_code': 'CP 2',
        'cp_name': 'Konfigurasi Jaringan Dasar',
        'question_text': 'Alamat default gateway untuk jaringan lokal?',
        'option_a': '192.168.1.1',
        'option_b': '127.0.0.1 (Loopback)',
        'option_c': '255.255.255.0',
        'option_d': '0.0.0.0',
        'option_e': '169.254.0.1',
        'correct_answer': 'A',
    }
    post_res = client.post(
        reverse('questions:edit', kwargs={'pk': q.id}),
        data=update_data,
        HTTP_HX_REQUEST='true'
    )
    assert post_res.status_code == 200
    q.refresh_from_db()
    assert 'untuk jaringan lokal' in q.question_text
    assert q.option_b == '127.0.0.1 (Loopback)'
    assert q.cp_code == 'CP 2'
    assert q.cp_name == 'Konfigurasi Jaringan Dasar'


@pytest.mark.django_db
def test_question_delete_view_and_detail_view(client):
    """Verify QuestionDeleteView confirmation and action, and QuestionDetailView."""
    admin_user = User.objects.create_superuser(username='admin5', email='admin5@test.com', password='password123')
    client.force_login(admin_user)

    subject = Subject.objects.create(name='Sistem Operasi')
    q = Question.objects.create(
        subject=subject,
        level=10,
        question_text='Perintah Linux untuk melihat direktori aktif adalah?',
        option_a='pwd',
        option_b='ls',
        option_c='cd',
        option_d='mkdir',
        option_e='rm',
        correct_answer='A'
    )

    # 1. Detail View
    detail_res = client.get(reverse('questions:detail', kwargs={'pk': q.id}))
    assert detail_res.status_code == 200
    assert 'PREVIEW BUTIR SOAL' in detail_res.content.decode()
    assert 'pwd' in detail_res.content.decode()

    # 2. Delete Confirmation Modal (GET)
    delete_get_res = client.get(reverse('questions:delete', kwargs={'pk': q.id}))
    assert delete_get_res.status_code == 200
    assert 'Hapus Butir Soal?' in delete_get_res.content.decode()

    # 3. Delete Action (POST via HTMX)
    delete_post_res = client.post(
        reverse('questions:delete', kwargs={'pk': q.id}),
        HTTP_HX_REQUEST='true'
    )
    assert delete_post_res.status_code == 200
    assert not Question.objects.filter(id=q.id).exists()


# ==============================================================================
# 4. RBAC & Security Checks
# ==============================================================================

@pytest.mark.django_db
def test_rbac_student_blocked_from_questions(client):
    """Ensure Student cannot access Question Bank and is redirected to /student/dashboard/."""
    student_user = User.objects.create_user(
        username='student_test',
        role=Role.SISWA,
        password='password123'
    )
    client.force_login(student_user)

    urls = [
        reverse('questions:bank_soal'),
        reverse('questions:filter'),
        reverse('questions:create'),
    ]
    for url in urls:
        res = client.get(url)
        assert res.status_code == 302
        assert '/student/dashboard/' in res['Location']


@pytest.mark.django_db
def test_rbac_unauthenticated_blocked_from_questions(client):
    """Ensure unauthenticated user is redirected to login."""
    res = client.get(reverse('questions:bank_soal'))
    assert res.status_code == 302
    assert reverse('accounts:login') in res['Location']


@pytest.mark.django_db
def test_dynamic_teacher_filtering_by_subject(client):
    """Verify that selecting a subject filters the teachers list to only assigned teachers."""
    import json
    from apps.master_data.models import Subject, Teacher, ClassRoom, Major, TeacherAssignment

    admin_user = User.objects.create_superuser(
        username='admin_filter_test',
        email='admin_filter@test.com',
        password='password123',
        role=Role.ADMIN
    )
    client.force_login(admin_user)

    major = Major.objects.create(code='RPL', name='Rekayasa Perangkat Lunak')
    classroom = ClassRoom.objects.create(name='X RPL 1', level=10, major=major)

    subj_mtk = Subject.objects.create(name='Matematika Wajib')
    subj_fsk = Subject.objects.create(name='Fisika Dasar')

    teacher_mtk = Teacher.objects.create(full_name='Guru Matematika', email='mtk@test.com')
    teacher_fsk = Teacher.objects.create(full_name='Guru Fisika', email='fsk@test.com')

    TeacherAssignment.objects.create(teacher=teacher_mtk, subject=subj_mtk, class_room=classroom)
    TeacherAssignment.objects.create(teacher=teacher_fsk, subject=subj_fsk, class_room=classroom)

    # 1. BankSoalView without filter -> both teachers present
    res_all = client.get(reverse('questions:bank_soal'))
    assert res_all.status_code == 200
    teachers_all = list(res_all.context['teachers'])
    assert teacher_mtk in teachers_all
    assert teacher_fsk in teachers_all

    # Verify teachers_json mapping in context
    teachers_json = json.loads(res_all.context['teachers_json'])
    mtk_entry = next((t for t in teachers_json if t['id'] == str(teacher_mtk.id)), None)
    assert mtk_entry is not None
    assert str(subj_mtk.id) in mtk_entry['subject_ids']

    # 2. BankSoalView with subject_id filter -> only teacher_mtk in context['teachers']
    res_mtk = client.get(reverse('questions:bank_soal') + f"?subject_id={subj_mtk.id}")
    assert res_mtk.status_code == 200
    teachers_mtk = list(res_mtk.context['teachers'])
    assert teacher_mtk in teachers_mtk
    assert teacher_fsk not in teachers_mtk

    # 3. QuestionCreateView with subject_id filter -> only teacher_mtk in context['teachers']
    res_create = client.get(reverse('questions:create') + f"?subject_id={subj_mtk.id}")
    assert res_create.status_code == 200
    teachers_create = list(res_create.context['teachers'])
    assert teacher_mtk in teachers_create
    assert teacher_fsk not in teachers_create

    # 4. QuestionEditView for a Matematika question -> only teacher_mtk in context['teachers']
    q_mtk = Question.objects.create(
        subject=subj_mtk,
        created_by=teacher_mtk,
        level=10,
        question_text="Berapakah 2 + 2?",
        option_a="1", option_b="2", option_c="3", option_d="4", option_e="5",
        correct_answer="D"
    )
    res_edit = client.get(reverse('questions:edit', kwargs={'pk': q_mtk.id}))
    assert res_edit.status_code == 200
    teachers_edit = list(res_edit.context['teachers'])
    assert teacher_mtk in teachers_edit
    assert teacher_fsk not in teachers_edit


@pytest.mark.django_db
def test_restore_supabase_images_command(monkeypatch):
    """Verify restore_supabase_images command updates question image URLs accurately."""
    from django.core.management import call_command
    from unittest.mock import MagicMock
    import psycopg

    q = Question.objects.create(
        question_text="Sample question with image",
        correct_answer="A"
    )

    fake_cur = MagicMock()
    fake_cur.fetchall.return_value = [
        (
            str(q.id),
            "https://vlawnrlczxagcitlaokh.supabase.co/storage/v1/object/public/question-images/test/sample.png",
            "https://vlawnrlczxagcitlaokh.supabase.co/storage/v1/object/public/question-images/test/opt_a.png",
            "", "", "", ""
        )
    ]
    fake_cur.__enter__.return_value = fake_cur

    fake_conn = MagicMock()
    fake_conn.cursor.return_value = fake_cur

    monkeypatch.setattr(psycopg, 'connect', lambda *args, **kwargs: fake_conn)

    call_command('restore_supabase_images', '--no-download')

    q.refresh_from_db()
    assert "https://vlawnrlczxagcitlaokh.supabase.co" in q.question_image.name
    assert "opt_a.png" in q.image_a.name


@pytest.mark.django_db
def test_question_form_requires_five_options():
    """Verify QuestionForm strictly requires all 5 options (A-E) for SMK standard."""
    from apps.questions.forms import QuestionForm

    subject = Subject.objects.create(name='Pemrograman Web')

    # 1. Invalid when option_e is missing
    form_incomplete = QuestionForm(data={
        'subject': subject.id,
        'level': 11,
        'question_text': 'Apa fungsi tag div?',
        'option_a': 'Container',
        'option_b': 'Paragraf',
        'option_c': 'Judul',
        'option_d': 'Gambar',
        'correct_answer': 'A',
    })
    assert not form_incomplete.is_valid()
    assert 'option_e' in form_incomplete.errors

    # 2. Valid when all 5 options provided
    form_complete = QuestionForm(data={
        'subject': subject.id,
        'level': 11,
        'cp_code': 'CP 1',
        'cp_name': 'Elemen HTML Dasar',
        'question_text': 'Apa fungsi tag div?',
        'option_a': 'Container',
        'option_b': 'Paragraf',
        'option_c': 'Judul',
        'option_d': 'Gambar',
        'option_e': 'Tautan',
        'correct_answer': 'A',
    })
    assert form_complete.is_valid(), form_complete.errors
    saved = form_complete.save()
    assert saved.cp_code == 'CP 1'
    assert saved.cp_display == 'CP 1: Elemen HTML Dasar'


@pytest.mark.django_db
def test_question_cp_tagging_and_filtering(client):
    """Verify CP filter in Bank Soal view and Question Selection view."""
    admin_user = User.objects.create_superuser(username='admin_cp', email='admin_cp@test.com', password='password123')
    client.force_login(admin_user)

    subject = Subject.objects.create(name='Basis Data')
    q_cp1 = Question.objects.create(
        subject=subject,
        level=11,
        cp_code='CP 1',
        cp_name='DDL & DML',
        question_text='Perintah SQL untuk membuat tabel?',
        option_a='CREATE TABLE', option_b='ALTER TABLE', option_c='DROP TABLE', option_d='SELECT', option_e='UPDATE',
        correct_answer='A'
    )
    q_cp2 = Question.objects.create(
        subject=subject,
        level=11,
        cp_code='CP 2',
        cp_name='Normalisasi',
        question_text='Bentuk normal pertama disebut?',
        option_a='1NF', option_b='2NF', option_c='3NF', option_d='BCNF', option_e='4NF',
        correct_answer='A'
    )

    # Filter in Bank Soal
    res_cp1 = client.get(reverse('questions:filter') + f'?subject_id={subject.id}&cp_code=CP 1', HTTP_HX_REQUEST='true')
    assert res_cp1.status_code == 200
    content_cp1 = res_cp1.content.decode()
    assert 'CREATE TABLE' in content_cp1
    assert '1NF' not in content_cp1

    # Filter in Select Questions view
    from apps.schedules.models import Exam
    exam = Exam.objects.create(
        title='UH Basis Data',
        subject=subject,
        level=11,
        exam_type='UH',
        target_question_count=10,
    )
    res_select = client.get(reverse('schedules:select_questions', kwargs={'exam_id': exam.id}) + '?cp_code=CP 2')
    assert res_select.status_code == 200
    select_content = res_select.content.decode()
    assert '1NF' in select_content
    assert 'CREATE TABLE' not in select_content



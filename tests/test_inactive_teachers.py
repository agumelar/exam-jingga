"""Guru yang akunnya dinonaktifkan (pindah tugas, akun uji) hilang dari pilihan guru, tetapi data dan soalnya tetap ada."""
import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse

from apps.accounts.models import Role
from apps.master_data.models import ClassRoom, Subject, Teacher, TeacherAssignment
from apps.questions.models import Question
from apps.schedules.forms import ScheduleForm

User = get_user_model()


@pytest.fixture
def teachers(db):
    active_user = User.objects.create_user(username='guru_aktif', role=Role.GURU)
    moved_user = User.objects.create_user(username='dhavika', role=Role.GURU, is_active=False)
    active = Teacher.objects.create(user=active_user, full_name='Guru Aktif', email='aktif@x.id')
    moved = Teacher.objects.create(user=moved_user, full_name='Dhafika Mutiara', email='dhafika@x.id')
    # Guru baru dari data pusat belum punya akun sampai login pertama; tetap dianggap aktif
    fresh = Teacher.objects.create(full_name='Iwan Setiawan', nip='199001012020121001')
    subject = Subject.objects.create(name='Mapel Uji')
    Question.objects.create(subject=subject, level=10, created_by=moved, question_text='Soal lama', option_a='a',
                            option_b='b', option_c='c', option_d='d', option_e='e', correct_answer='A')
    admin = User.objects.create_user(username='admin_guru', role=Role.ADMIN, is_staff=True)
    return {'active': active, 'moved': moved, 'fresh': fresh, 'admin': admin}


@pytest.mark.django_db
def test_active_queryset_excludes_deactivated_accounts(teachers):
    names = set(Teacher.objects.active().values_list('full_name', flat=True))
    assert names == {'Guru Aktif', 'Iwan Setiawan'}


@pytest.mark.django_db
def test_assignment_page_offers_only_active_teachers(client, teachers):
    client.force_login(teachers['admin'])
    html = client.get(reverse('penugasan_guru')).content.decode()
    assert 'Guru Aktif' in html and 'Iwan Setiawan' in html
    assert 'Dhafika Mutiara' not in html


@pytest.mark.django_db
def test_schedule_form_rejects_deactivated_teacher(teachers):
    form = ScheduleForm(is_admin=True)
    choices = set(form.fields['teacher'].queryset.values_list('full_name', flat=True))
    assert 'Dhafika Mutiara' not in choices and 'Guru Aktif' in choices


@pytest.mark.django_db
def test_master_teacher_list_marks_deactivated_teacher(client, teachers):
    client.force_login(teachers['admin'])
    html = client.get('/master-guru/').content.decode()
    assert 'Dhafika Mutiara' in html
    assert 'Nonaktif' in html


@pytest.mark.django_db
def test_questions_of_deactivated_teacher_are_kept(teachers):
    assert Question.objects.filter(created_by=teachers['moved']).count() == 1


@pytest.mark.django_db
def test_editing_question_keeps_deactivated_author_selectable(client, teachers):
    question = Question.objects.get(created_by=teachers['moved'])
    client.force_login(teachers['admin'])
    res = client.get(reverse('questions:edit', args=[question.id]), HTTP_HX_REQUEST='true')
    assert 'Dhafika Mutiara' in res.content.decode()
    create = client.get(reverse('questions:create'), HTTP_HX_REQUEST='true').content.decode()
    assert 'Dhafika Mutiara' not in create

"""Fase 2 audit: hak akses per peran (tanpa pengawas; admin/kurikulum memegang logistik dan aksi sesi)."""
from datetime import timedelta
from importlib import import_module

import pytest
from django.apps import apps as django_apps
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone

from apps.accounts.models import Role
from apps.exam_engine.models import ExamSession
from apps.master_data.models import ClassRoom, Student, Subject, Teacher, TeacherAssignment
from apps.schedules.models import Exam, Schedule

User = get_user_model()


def _guru(name):
    user = User.objects.create_user(username=name, email=f'{name}@x.id', role=Role.GURU)
    return user, Teacher.objects.create(user=user, full_name=f'Guru {name}', email=f'{name}@x.id')


def _uh(teacher, title, cls):
    subject = Subject.objects.create(name=f'Mapel {title}')
    TeacherAssignment.objects.create(teacher=teacher, subject=subject, class_room=cls)
    exam = Exam.objects.create(teacher=teacher, subject=subject, title=title, exam_type='UH', level=10,
                               status='validated', target_question_count=1)
    now = timezone.now()
    sch = Schedule.objects.create(exam=exam, class_room=cls, teacher=teacher, start_time=now - timedelta(minutes=5),
                                  end_time=now + timedelta(hours=1), token='TOK001')
    return exam, sch


@pytest.fixture
def world(db):
    cls = ClassRoom.objects.create(name='X POL 1', level=10)
    ua, ta = _guru('pol_a')
    ub, tb = _guru('pol_b')
    exam_a, sch_a = _uh(ta, 'UH Milik A', cls)
    exam_b, sch_b = _uh(tb, 'UH Milik B', cls)
    suser = User.objects.create_user(username='77001', nis='77001', role=Role.SISWA)
    student = Student.objects.create(user=suser, nis='77001', full_name='Siswa Pol', class_room=cls)
    session_b = ExamSession.objects.create(student=student, schedule=sch_b, status='locked')
    admin = User.objects.create_user(username='kur_pol', role=Role.KURIKULUM)
    return locals()


ADMIN_ONLY_PAGES = ['reports:logistics', 'reports:exam_cards', 'reports:attendance_list',
                    'reports:logistics_export', 'reports:settings']


@pytest.mark.django_db
@pytest.mark.parametrize('name', ADMIN_ONLY_PAGES)
def test_guru_blocked_from_admin_only_pages(client, world, name):
    client.force_login(world['ua'])
    res = client.get(reverse(name))
    assert res.status_code in (302, 403)
    if res.status_code == 302:
        assert 'logistics' not in res.url and 'settings' not in res.url


@pytest.mark.django_db
@pytest.mark.parametrize('name', ADMIN_ONLY_PAGES)
def test_kurikulum_reaches_admin_only_pages(client, world, name):
    client.force_login(world['admin'])
    assert client.get(reverse(name)).status_code == 200


@pytest.mark.django_db
def test_platform_admin_reaches_reports(client, world):
    user = User.objects.create_user(username='plat_pol', role=Role.PLATFORM_ADMIN)
    client.force_login(user)
    assert client.get(reverse('reports:logistics')).status_code == 200


@pytest.mark.django_db
def test_guru_cannot_generate_logistics(client, world):
    client.force_login(world['ua'])
    res = client.post(reverse('reports:logistics_generate'), {'room_count': 1, 'capacity': 10})
    assert res.status_code in (302, 403)


@pytest.mark.django_db
@pytest.mark.parametrize('action', ['session_unlock', 'session_reset', 'session_force_submit'])
def test_guru_cannot_act_on_sessions_even_own_exam(client, world, action):
    client.force_login(world['ub'])
    res = client.post(reverse(f'reports:{action}', args=[world['session_b'].id]), {'reason': 'coba'})
    world['session_b'].refresh_from_db()
    assert res.status_code == 403
    assert world['session_b'].status == 'locked'


@pytest.mark.django_db
def test_kurikulum_unlocks_session(client, world):
    client.force_login(world['admin'])
    client.post(reverse('reports:session_unlock', args=[world['session_b'].id]),
                {'reason': 'Sudah dibina kurikulum'}, HTTP_HX_REQUEST='true')
    world['session_b'].refresh_from_db()
    assert world['session_b'].status == 'active'


@pytest.mark.django_db
def test_guru_monitoring_only_own_schedules(client, world):
    client.force_login(world['ua'])

    res = client.get(reverse('reports:session_monitoring'), {'schedule_id': world['sch_b'].id})

    assert res.status_code == 200
    assert {s.id for s in res.context['schedules']} == {world['sch_a'].id}
    assert res.context['selected_schedule'].id == world['sch_a'].id
    assert res.context['can_manage_sessions'] is False


@pytest.mark.django_db
def test_guru_monitoring_table_rejects_other_schedule(client, world):
    client.force_login(world['ua'])
    res = client.get(reverse('reports:session_monitoring_table'), {'schedule_id': world['sch_b'].id})
    assert res.status_code == 404


@pytest.mark.django_db
@pytest.mark.parametrize('name', ['reports:exam_results_detail', 'reports:exam_results_export', 'reports:distractor_analysis'])
def test_guru_cannot_open_other_teachers_results(client, world, name):
    client.force_login(world['ua'])
    assert client.get(reverse(name, args=[world['exam_b'].id])).status_code == 404
    assert client.get(reverse(name, args=[world['exam_a'].id])).status_code == 200


@pytest.mark.django_db
def test_results_dropdown_lists_only_own_exams(client, world):
    client.force_login(world['ua'])
    res = client.get(reverse('reports:exam_results_detail', args=[world['exam_a'].id]))
    assert {e.id for e in res.context['all_exams']} == {world['exam_a'].id}


@pytest.mark.django_db
def test_guru_without_teacher_profile_sees_nothing(client, world):
    orphan = User.objects.create_user(username='guru_tanpa_profil', role=Role.GURU)
    client.force_login(orphan)
    assert client.get(reverse('reports:exam_results_detail', args=[world['exam_a'].id])).status_code == 404


@pytest.mark.django_db
def test_core_dashboard_scoped_for_guru(client, world):
    from django.core.cache import cache
    cache.clear()
    client.force_login(world['ua'])
    res = client.get('/dashboard/')
    assert {s.exam_id for s in res.context['recent_schedules']} == {world['exam_a'].id}
    assert all(s.schedule.exam_id == world['exam_a'].id for s in res.context['recent_sessions'])


@pytest.mark.django_db
def test_pengawas_role_no_longer_grants_staff_access(client, world):
    user = User.objects.create_user(username='eks_pengawas', role='pengawas')
    client.force_login(user)
    assert client.get(reverse('schedules:list')).status_code == 302


@pytest.mark.django_db
def test_official_exam_token_only_for_admin(client, world):
    exam_a = world['exam_a']
    Exam.objects.filter(pk=exam_a.pk).update(exam_type='PAS')
    client.force_login(world['ua'])
    res = client.post(reverse('schedules:action', args=[world['sch_a'].id, 'regenerate-token']), HTTP_HX_REQUEST='true')
    assert res.status_code == 403


@pytest.mark.django_db
def test_migrate_pengawas_accounts():
    migration = import_module('apps.accounts.migrations.0004_remove_pengawas_role')
    with_profile = User.objects.create_user(username='pw_profil', role='pengawas')
    Teacher.objects.create(user=with_profile, full_name='Pengawas Guru', email='pw@x.id')
    without = User.objects.create_user(username='pw_tanpa', role='pengawas')

    migration.convert_pengawas_accounts(django_apps, None)

    with_profile.refresh_from_db()
    without.refresh_from_db()
    assert with_profile.role == Role.GURU and with_profile.is_active
    assert without.is_active is False

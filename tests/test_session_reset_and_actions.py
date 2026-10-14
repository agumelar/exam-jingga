"""Aksi sesi tanpa isian alasan, dan halaman ujian yang tertinggal setelah sesi direset."""
import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse

from apps.accounts.models import Role
from apps.exam_engine.models import ExamSession
from apps.reports.models import SessionActionLog

from .test_exam_engine_integrity import World

User = get_user_model()
HX = {'HTTP_HX_REQUEST': 'true'}


def _kurikulum():
    return User.objects.create_user(username='kurikulum_aksi', role=Role.KURIKULUM, is_staff=True)


@pytest.mark.django_db
@pytest.mark.parametrize('action,status,expected', [
    ('session_unlock', 'locked', 'active'),
    ('session_force_submit', 'locked', 'finished'),
])
def test_session_actions_work_without_reason(client, action, status, expected):
    w = World(f'noreason{status[:2]}{expected[:2]}', exam_type='PAS')
    _, session = w.start(client, w.student(f'55{len(action)}'))
    ExamSession.objects.filter(pk=session.pk).update(status=status, violation_count=2)
    client.force_login(_kurikulum())

    client.post(reverse(f'reports:{action}', args=[session.id]), **HX)

    session.refresh_from_db()
    assert session.status == expected
    log = SessionActionLog.objects.get(session_id_snapshot=session.id)
    assert log.previous_status == status and log.previous_violation_count == 2


@pytest.mark.django_db
def test_monitoring_buttons_do_not_ask_for_a_reason(client):
    w = World('noprompt', exam_type='PAS')
    _, session = w.start(client, w.student('5601'))
    ExamSession.objects.filter(pk=session.pk).update(status='locked', violation_count=2)
    client.force_login(_kurikulum())

    html = client.get(reverse('reports:session_monitoring_table'), {'schedule_id': w.schedule.id}).content.decode()

    assert 'hx-prompt' not in html
    # Reset dan paksa selesai tidak bisa dibatalkan, jadi tetap ada konfirmasi tanpa isian
    assert html.count('hx-confirm') == 2


@pytest.mark.django_db
def test_finish_on_reset_session_returns_to_dashboard(client):
    w = World('resetgone')
    student = w.student('5701')
    _, session = w.start(client, student)
    session_id = session.id
    session.delete()

    res = client.post(reverse('exam_engine:finish_exam', args=[session_id]))

    assert res.status_code == 302
    assert res.url == '/student/dashboard/?sesi=direset'


@pytest.mark.django_db
def test_dashboard_explains_reset(client):
    w = World('resetnote')
    student = w.student('5801')
    client.force_login(student.user)
    page = client.get(reverse('exam_engine:student_dashboard'), {'sesi': 'direset'}).content.decode()
    assert 'Sesi ujianmu direset oleh kurikulum' in page
    assert 'Masukkan token lagi' in page


@pytest.mark.django_db
def test_exam_page_leaves_when_session_is_gone(client):
    w = World('resetjs')
    _, session = w.start(client, w.student('5901'))
    page = client.get(reverse('exam_engine:exam_interface', args=[session.id])).content.decode()
    # Detak jantung atau permintaan HTMX yang mendapat 404 mengarahkan siswa ke dashboard
    assert '/student/dashboard/?sesi=direset' in page
    assert 'status === 404' in page

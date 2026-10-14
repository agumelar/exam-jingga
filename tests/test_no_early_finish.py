"""Aturan sekolah: siswa tidak bisa menyelesaikan ujian sendiri; ujian berakhir saat hitung mundur habis."""
from datetime import timedelta

import pytest
from django.urls import reverse
from django.utils import timezone

from apps.exam_engine.models import ExamSession

from .test_exam_engine_integrity import World


def _finish(client, session, htmx=True):
    extra = {'HTTP_HX_REQUEST': 'true'} if htmx else {}
    return client.post(reverse('exam_engine:finish_exam', args=[session.id]), **extra)


def _expire(session, seconds_left=0):
    duration = session.schedule.exam.duration
    started = timezone.now() - timedelta(minutes=duration) + timedelta(seconds=seconds_left)
    ExamSession.objects.filter(pk=session.pk).update(started_at=started)


@pytest.mark.django_db
@pytest.mark.parametrize('exam_type', ['UH', 'PTS', 'PAS'])
def test_student_cannot_finish_before_time_is_up(client, exam_type):
    w = World(f'early{exam_type.lower()}', exam_type=exam_type)
    _, session = w.start(client, w.student(f'71{len(exam_type)}1'))

    res = _finish(client, session)

    session.refresh_from_db()
    assert session.status == 'active'
    assert session.finished_at is None
    assert res.status_code == 403
    assert 'terkirim otomatis saat waktu habis' in res.content.decode()


@pytest.mark.django_db
def test_early_finish_without_htmx_returns_to_exam(client):
    w = World('earlyplain')
    _, session = w.start(client, w.student('7201'))
    res = _finish(client, session, htmx=False)
    session.refresh_from_db()
    assert session.status == 'active'
    assert res.url == f'/exam/session/{session.id}/'


@pytest.mark.django_db
def test_auto_submit_at_end_of_countdown_is_accepted(client):
    w = World('ontime')
    _, session = w.start(client, w.student('7301'))
    # Jam HP dan server bisa selisih beberapa detik saat hitung mundur mencapai nol
    _expire(session, seconds_left=5)

    _finish(client, session)

    session.refresh_from_db()
    assert session.status == 'finished'


@pytest.mark.django_db
def test_finish_after_deadline_is_accepted(client):
    w = World('late2')
    _, session = w.start(client, w.student('7401'))
    _expire(session)
    _finish(client, session, htmx=False)
    session.refresh_from_db()
    assert session.status == 'finished'


@pytest.mark.django_db
def test_exam_page_has_no_finish_controls(client):
    w = World('nobutton', n_questions=2)
    _, session = w.start(client, w.student('7501'))

    page = client.get(reverse('exam_engine:exam_interface', args=[session.id])).content.decode()
    last = client.get(reverse('exam_engine:question_swap', args=[session.id, 2])).content.decode()

    for html in (page, last):
        assert 'showFinishModal = true' not in html
        assert 'Selesai &amp; Kirim Jawaban' not in html and 'Selesai & Kirim Jawaban' not in html
    assert 'Kirim Jawaban' not in page
    # Formulir tersembunyi tetap ada untuk kiriman otomatis saat waktu habis
    assert 'id="finish-exam-form"' in page
    assert 'Jawaban terkirim otomatis saat waktu habis' in last

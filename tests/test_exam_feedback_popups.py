"""Peringatan pindah layar di tengah layar, dan pop up nilai di dashboard setelah waktu habis."""
from datetime import timedelta

import pytest
from django.urls import reverse
from django.utils import timezone

from apps.exam_engine.models import ExamSession, StudentAnswer

from .test_exam_engine_integrity import World


def _violation(client, session):
    return client.post(reverse('exam_engine:violation_handler', args=[session.id])).content.decode()


@pytest.mark.django_db
def test_violation_warning_is_a_centered_dialog_that_needs_acknowledgement(client):
    w = World('warnuh')
    _, session = w.start(client, w.student('6601'))

    html = _violation(client, session)

    assert 'role="alertdialog"' in html
    assert 'fixed inset-0' in html and 'items-center' in html
    assert 'Kamu berpindah layar' in html
    assert 'Saya mengerti' in html
    assert 'Pelanggaran ke-1' in html


@pytest.mark.django_db
def test_official_exam_warning_says_next_violation_locks(client):
    w = World('warnpas', exam_type='PAS')
    _, session = w.start(client, w.student('6602'))
    html = _violation(client, session)
    assert 'Satu kali lagi berpindah layar, ujianmu terkunci' in html


def _finish_at_time_up(client, w, nis, correct=3):
    _, session = w.start(client, w.student(nis))
    answers = StudentAnswer.objects.filter(session=session).select_related('question')
    for a in list(answers)[:correct]:
        client.post(reverse('exam_engine:save_answer', args=[session.id]),
                    {'question_id': a.question_id, 'chosen_answer': a.question.correct_answer}, HTTP_HX_REQUEST='true')
    ExamSession.objects.filter(pk=session.pk).update(started_at=timezone.now() - timedelta(minutes=w.exam.duration))
    res = client.post(reverse('exam_engine:finish_exam', args=[session.id]))
    return session, res


@pytest.mark.django_db
def test_dashboard_shows_score_popup_once_after_time_up(client):
    w = World('popup', n_questions=5)
    session, res = _finish_at_time_up(client, w, '6701', correct=3)
    assert res.url == '/student/dashboard/'

    first = client.get(reverse('exam_engine:student_dashboard')).content.decode()
    assert 'id="score-popup"' in first
    assert w.exam.title in first
    assert '>60<' in first.replace(' ', '') or '>60.0<' in first.replace(' ', '')
    assert '3 dari 5 soal benar' in first

    again = client.get(reverse('exam_engine:student_dashboard')).content.decode()
    assert 'id="score-popup"' not in again


@pytest.mark.django_db
def test_popup_also_shown_when_server_graded_the_session(client):
    # Jawaban yang masuk setelah waktu habis membuat server menilai sesi lalu mengarahkan ke dashboard
    w = World('popupserver')
    _, session = w.start(client, w.student('6801'))
    ExamSession.objects.filter(pk=session.pk).update(started_at=timezone.now() - timedelta(minutes=61))
    q = w.questions[0]
    client.post(reverse('exam_engine:save_answer', args=[session.id]), {'question_id': q.id, 'chosen_answer': 'C'},
                HTTP_HX_REQUEST='true')

    page = client.get(reverse('exam_engine:student_dashboard')).content.decode()
    assert 'id="score-popup"' in page


@pytest.mark.django_db
def test_no_popup_for_exams_finished_long_ago(client):
    w = World('popupold')
    session, _ = _finish_at_time_up(client, w, '6901')
    ExamSession.objects.filter(pk=session.pk).update(finished_at=timezone.now() - timedelta(hours=1))
    page = client.get(reverse('exam_engine:student_dashboard')).content.decode()
    assert 'id="score-popup"' not in page

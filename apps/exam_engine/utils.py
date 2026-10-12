"""Helper utilities for Core CBT Exam Engine."""
import random

from django.db import transaction
from django.db.models import Count, Q
from django.utils import timezone

from apps.exam_engine.models import ExamSession, StudentAnswer
from apps.schedules.models import ExamQuestion

DISPLAY_KEYS = 'ABCDE'


def _available_option_keys(question):
    """Huruf asli opsi yang punya isi (teks atau gambar); opsi kosong tidak ditampilkan."""
    return [opt['key'] for opt in question.get_options() if (opt['text'] or '').strip() or opt['image_url']]


def initialize_session_answers(session):
    """
    Membuat lembar jawaban sekali saja (aman dipanggil berulang dan bersamaan).
    Urutan soal dan urutan opsi diacak per siswa dengan seed dari id sesi, lalu disimpan,
    sehingga tampilan tetap sama saat siswa membuka ulang lembar kerjanya.
    """
    exam = session.schedule.exam
    exam_questions = list(
        ExamQuestion.objects.filter(exam=exam).select_related('question').order_by('order_number', 'created_at')
    )
    rng = random.Random(str(session.id))
    if exam.shuffle_questions:
        rng.shuffle(exam_questions)

    rows = []
    for position, eq in enumerate(exam_questions, start=1):
        keys = _available_option_keys(eq.question)
        if exam.shuffle_options and not eq.question.lock_option_order:
            rng.shuffle(keys)
        rows.append(StudentAnswer(
            session=session,
            question=eq.question,
            order_number=position,
            option_order=''.join(keys) or DISPLAY_KEYS,
        ))

    with transaction.atomic():
        ExamSession.objects.select_for_update().filter(pk=session.pk).first()
        if not StudentAnswer.objects.filter(session=session).exists():
            StudentAnswer.objects.bulk_create(rows, ignore_conflicts=True)


def session_counts(session):
    agg = StudentAnswer.objects.filter(session=session).aggregate(
        total=Count('id'),
        answered=Count('id', filter=Q(chosen_answer__isnull=False) & ~Q(chosen_answer='')),
        doubt=Count('id', filter=Q(is_doubt=True)),
    )
    total = agg['total'] or 0
    return {
        'total_count': total,
        'answered_count': agg['answered'] or 0,
        'doubt_count': agg['doubt'] or 0,
        'progress_percent': int(agg['answered'] / total * 100) if total else 0,
    }


def display_key_for(answer):
    """Huruf yang dilihat siswa untuk jawaban tersimpan (jawaban disimpan dalam huruf asli)."""
    if not answer.chosen_answer:
        return ''
    visible = [k for k in (answer.option_order or DISPLAY_KEYS)]
    try:
        return DISPLAY_KEYS[visible.index(answer.chosen_answer)]
    except ValueError:
        return answer.chosen_answer


def build_question_item(answer, with_options=True):
    q = answer.question
    item = {
        'order_num': answer.order_number,
        'student_answer': answer,
        'question': q,
        'chosen_answer': answer.chosen_answer,
        'chosen_display': display_key_for(answer),
        'is_answered': bool(answer.chosen_answer),
        'is_doubt': answer.is_doubt,
        'options': [],
    }
    if with_options:
        by_key = {opt['key']: opt for opt in q.get_options()}
        visible_index = 0
        for original in (answer.option_order or DISPLAY_KEYS):
            opt = by_key.get(original)
            if not opt or not ((opt['text'] or '').strip() or opt['image_url']):
                continue
            item['options'].append({
                'key': original,
                'display_key': DISPLAY_KEYS[visible_index],
                'text': opt['text'],
                'image_url': opt['image_url'],
                'is_selected': answer.chosen_answer == original,
            })
            visible_index += 1
    return item


def _navigation(current_order, total):
    return {
        'current_order': current_order,
        'has_prev': current_order > 1,
        'prev_order': current_order - 1 if current_order > 1 else None,
        'has_next': current_order < total,
        'next_order': current_order + 1 if current_order < total else None,
        'is_last': current_order == total,
    }


def get_question_payload(session, current_order=1):
    """Satu soal aktif + penghitung, untuk navigasi dan simpan jawaban (tanpa memuat semua soal)."""
    counts = session_counts(session)
    total = counts['total_count']
    current_order = min(max(int(current_order or 1), 1), max(total, 1))
    answer = (
        StudentAnswer.objects.filter(session=session, order_number=current_order)
        .select_related('question', 'question__subject').first()
    )
    return {
        **counts,
        **_navigation(current_order, total),
        'current_item': build_question_item(answer) if answer else None,
    }


def get_session_questions_payload(session, current_order=1):
    """Seluruh daftar soal (untuk grid navigasi) + soal aktif lengkap dengan opsinya."""
    answers = list(
        StudentAnswer.objects.filter(session=session)
        .select_related('question', 'question__subject')
        .order_by('order_number', 'id')
    )
    total = len(answers)
    current_order = min(max(int(current_order or 1), 1), max(total, 1))
    questions_list = []
    current_item = None
    for ans in answers:
        is_current = ans.order_number == current_order
        item = build_question_item(ans, with_options=is_current)
        item['is_current'] = is_current
        questions_list.append(item)
        if is_current:
            current_item = item
    answered = sum(1 for i in questions_list if i['is_answered'])
    return {
        'questions_list': questions_list,
        'current_item': current_item,
        'total_count': total,
        'answered_count': answered,
        'doubt_count': sum(1 for i in questions_list if i['is_doubt']),
        'progress_percent': int(answered / total * 100) if total else 0,
        **_navigation(current_order, total),
    }


def grade_exam_session(session):
    """
    Mengoreksi lembar jawaban dan menghitung nilai (0-100) sekali saja.
    Baris sesi dikunci supaya kirim otomatis dan klik Selesai yang bersamaan tidak menilai dua kali.
    """
    with transaction.atomic():
        locked = ExamSession.objects.select_for_update().get(pk=session.pk)
        if locked.status == 'finished':
            session.refresh_from_db()
            return locked.score

        answers = list(locked.student_answers.select_related('question'))
        for ans in answers:
            ans.evaluate_correctness()
        StudentAnswer.objects.bulk_update(answers, ['is_correct'])

        correct = sum(1 for a in answers if a.is_correct)
        locked.score = round(correct / len(answers) * 100, 2) if answers else 0.0
        locked.status = 'finished'
        locked.finished_at = timezone.now()
        locked.remaining_seconds = 0
        locked.save(update_fields=['score', 'status', 'finished_at', 'remaining_seconds'])

    session.refresh_from_db()
    return session.score


def finalize_if_time_up(session):
    """Nilai sesi yang waktunya habis. True bila sesi sudah selesai setelah pemanggilan ini."""
    if session.status == 'finished':
        return True
    if session.calculate_remaining_seconds() <= 0:
        grade_exam_session(session)
        return True
    return False

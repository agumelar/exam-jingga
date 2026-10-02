"""Helper utilities for Core CBT Exam Engine."""
from django.utils import timezone
from apps.exam_engine.models import ExamSession, StudentAnswer
from apps.schedules.models import ExamQuestion


def initialize_session_answers(session):
    """
    Menginisialisasi lembar StudentAnswer untuk semua butir soal pada naskah ujian.
    Jika naskah soal diacak, dapat disesuaikan urutannya.
    """
    exam = session.schedule.exam
    exam_questions = (
        ExamQuestion.objects.filter(exam=exam)
        .select_related('question')
        .order_by('order_number')
    )

    created_answers = []
    for eq in exam_questions:
        ans, created = StudentAnswer.objects.get_or_create(
            session=session,
            question=eq.question,
            defaults={
                'chosen_answer': None,
                'is_doubt': False,
                'is_correct': None,
            }
        )
        created_answers.append(ans)
    return created_answers


def get_session_questions_payload(session, current_order=1):
    """
    Mengambil seluruh daftar soal pada sesi ujian dengan urutan terindeks 1..N.
    Mengembalikan metadata lengkap untuk navigasi sidebar, drawer, dan viewport aktif.
    """
    answers = (
        StudentAnswer.objects.filter(session=session)
        .select_related('question', 'question__subject')
        .order_by('question__question_exams__order_number', 'id')
    )

    questions_list = []
    current_item = None
    answered_count = 0
    doubt_count = 0

    for idx, ans in enumerate(answers, start=1):
        q = ans.question
        is_answered = bool(ans.chosen_answer)
        is_doubt = ans.is_doubt
        if is_answered:
            answered_count += 1
        if is_doubt:
            doubt_count += 1

        raw_options = q.get_options() if hasattr(q, 'get_options') else []
        options = []
        for raw_opt in raw_options:
            opt_dict = dict(raw_opt)
            opt_dict['is_selected'] = bool(ans.chosen_answer and ans.chosen_answer.upper() == opt_dict['key'].upper())
            options.append(opt_dict)

        item = {
            'order_num': idx,
            'student_answer': ans,
            'question': q,
            'chosen_answer': ans.chosen_answer,
            'is_answered': is_answered,
            'is_doubt': is_doubt,
            'is_current': (idx == current_order),
            'options': options,
        }
        questions_list.append(item)

        if idx == current_order:
            current_item = item

    # Fallback jika current_order di luar jangkauan
    if not current_item and questions_list:
        current_item = questions_list[0]
        current_order = 1

    total_count = len(questions_list)
    progress_percent = int((answered_count / total_count * 100)) if total_count > 0 else 0

    return {
        'questions_list': questions_list,
        'current_item': current_item,
        'current_order': current_order,
        'total_count': total_count,
        'answered_count': answered_count,
        'doubt_count': doubt_count,
        'progress_percent': progress_percent,
        'has_prev': current_order > 1,
        'prev_order': current_order - 1 if current_order > 1 else None,
        'has_next': current_order < total_count,
        'next_order': current_order + 1 if current_order < total_count else None,
        'is_last': current_order == total_count,
    }


def grade_exam_session(session):
    """
    Mengoreksi semua jawaban siswa pada sesi ujian dan menghitung nilai akhir (0-100).
    """
    answers = session.student_answers.select_related('question').all()
    correct_count = 0
    total_count = answers.count()

    for ans in answers:
        ans.evaluate_correctness()
        ans.save(update_fields=['is_correct'])
        if ans.is_correct:
            correct_count += 1

    score = round((correct_count / total_count * 100), 2) if total_count > 0 else 0.0
    session.score = score
    session.status = 'finished'
    session.finished_at = timezone.now()
    session.remaining_seconds = 0
    session.save(update_fields=['score', 'status', 'finished_at', 'remaining_seconds'])
    return score

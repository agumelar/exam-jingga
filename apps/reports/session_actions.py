"""
Aksi admin/kurikulum terhadap sesi siswa. Setiap aksi wajib beralasan dan tercatat di SessionActionLog.

- Buka kunci: hanya sesi berstatus terkunci. Jumlah pelanggaran tidak dihapus (tetap jadi bukti pembinaan).
- Reset: hanya sesi aktif/terkunci; lembar jawaban disimpan di log lalu sesi dihapus agar siswa mulai ulang.
- Paksa selesai: hanya sesi aktif/terkunci; dinilai sekali.
"""
from django.db import transaction

from apps.exam_engine.models import ExamSession
from apps.exam_engine.utils import grade_exam_session
from apps.reports.models import SessionActionLog


class SessionActionError(Exception):
    def __init__(self, message, status=409):
        super().__init__(message)
        self.message = message
        self.status = status


ALLOWED_FROM = {
    'unlock': {'locked'},
    'reset': {'active', 'locked'},
    'force_submit': {'active', 'locked'},
}
REFUSED_MESSAGES = {
    'unlock': "Hanya sesi yang terkunci yang bisa dibuka kuncinya.",
    'reset': "Sesi yang sudah selesai tidak bisa di-reset; nilainya sudah tercatat.",
    'force_submit': "Sesi ini sudah selesai.",
}


def _log(session, action, actor, reason, with_answers=False):
    answers = []
    if with_answers:
        answers = [
            {
                'question_id': str(a.question_id),
                'order_number': a.order_number,
                'option_order': a.option_order,
                'chosen_answer': a.chosen_answer,
                'is_doubt': a.is_doubt,
            }
            for a in session.student_answers.all()
        ]
    return SessionActionLog.objects.create(
        action=action,
        reason=reason,
        actor=actor,
        student_id=session.student_id,
        schedule_id=session.schedule_id,
        session_id_snapshot=session.id,
        previous_status=session.status,
        previous_violation_count=session.violation_count,
        previous_score=session.score,
        answers_snapshot=answers,
    )


def perform_session_action(session_id, action, actor, reason):
    reason = (reason or '').strip()
    if action not in ALLOWED_FROM:
        raise SessionActionError("Aksi tidak dikenal.", status=404)

    with transaction.atomic():
        try:
            session = ExamSession.objects.select_for_update().select_related('student').get(pk=session_id)
        except ExamSession.DoesNotExist:
            raise SessionActionError("Sesi tidak ditemukan.", status=404)
        if session.status not in ALLOWED_FROM[action]:
            raise SessionActionError(REFUSED_MESSAGES[action])

        _log(session, action, actor, reason, with_answers=(action == 'reset'))
        if action == 'unlock':
            session.status = 'active'
            session.save(update_fields=['status'])
        elif action == 'reset':
            session.delete()
        else:
            grade_exam_session(session)
    return session

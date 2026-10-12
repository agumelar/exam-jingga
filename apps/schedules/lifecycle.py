"""
Aturan siklus hidup naskah ujian: pengajuan, tarik, verifikasi, kembalikan, buka kunci, token.

Semua aksi mengunci baris Exam (select_for_update) supaya pengecekan
"belum ada siswa yang mulai" tidak bentrok dengan siswa yang memasukkan
token pada saat yang sama.
"""
from dataclasses import dataclass

from django.db import transaction
from django.utils import timezone

from apps.schedules.models import Exam, Schedule
from apps.schedules.utils import (
    ADMIN_ROLES,
    can_transition_status,
    generate_exam_token,
    resolve_status_after_question_save,
)


class LifecycleError(Exception):
    """Aksi ditolak. `status` dipakai view sebagai kode HTTP."""

    def __init__(self, message, status=409):
        super().__init__(message)
        self.message = message
        self.status = status


@dataclass
class Actor:
    user: object
    teacher: object = None

    @property
    def role(self):
        return str(getattr(self.user, 'role', '') or '').lower()

    @property
    def is_admin(self):
        return bool(getattr(self.user, 'is_superuser', False)) or self.role in ADMIN_ROLES

    @property
    def transition_role(self):
        return 'admin' if self.is_admin else 'guru'


def is_exam_member(exam, teacher):
    """Guru anggota paket: pembuat paket atau guru yang punya jadwal di paket itu."""
    if not teacher:
        return False
    if exam.teacher_id == teacher.id:
        return True
    return Schedule.objects.filter(exam=exam, teacher=teacher).exists()


def teacher_quota_progress(exam):
    """Daftar progres kuota per guru di paket, berdasarkan soal yang dibuat guru tersebut."""
    selected = list(exam.exam_questions.values_list('question__created_by_id', flat=True))
    progress = []
    seen = set()
    for sch in Schedule.objects.filter(exam=exam).select_related('teacher'):
        if not sch.teacher or sch.teacher_id in seen:
            continue
        seen.add(sch.teacher_id)
        quota = sch.teacher_quota if sch.teacher_quota > 0 else exam.target_question_count
        filled = sum(1 for author_id in selected if author_id == sch.teacher_id)
        progress.append({'teacher': sch.teacher, 'filled': filled, 'quota': quota, 'done': filled >= quota})
    return progress


def is_question_set_complete(exam):
    """
    Naskah lengkap bila jumlah soal mencapai target. Untuk paket kolaboratif
    (lebih dari satu guru), kuota tiap guru juga harus terpenuhi.
    """
    if exam.exam_questions.count() < exam.target_question_count:
        return False
    progress = teacher_quota_progress(exam)
    if len(progress) > 1:
        return all(p['done'] for p in progress)
    return True


def _locked_exam(exam_id):
    return Exam.objects.select_for_update().get(pk=exam_id)


def _require_transition(actor, exam, to_status, message):
    if not can_transition_status(actor.transition_role, exam.exam_type, exam.status, to_status):
        raise LifecycleError(message, status=403)


def _require_member_or_admin(actor, exam):
    if not actor.is_admin and not is_exam_member(exam, actor.teacher):
        raise LifecycleError("Anda bukan guru pengampu paket ujian ini.", status=403)


def _require_note(note):
    note = (note or '').strip()
    if not note:
        raise LifecycleError("Alasan wajib diisi supaya guru tahu apa yang perlu diperbaiki.", status=422)
    return note


def _record_review(exam, actor, note):
    exam.review_note = note
    exam.reviewed_by = actor.user
    exam.reviewed_at = timezone.now()


def ensure_questions_editable(exam, actor):
    """Dipakai saat memilih atau melepas soal."""
    _require_member_or_admin(actor, exam)
    if exam.status != 'pending_selection':
        raise LifecycleError(
            "Naskah sudah terkunci. Buka kunci naskah dulu sebelum mengubah soal.", status=409
        )


def submit_questions(exam_id, actor):
    """Simpan pilihan soal. Kembalikan (exam, status_baru, lengkap)."""
    with transaction.atomic():
        exam = _locked_exam(exam_id)
        ensure_questions_editable(exam, actor)
        complete = is_question_set_complete(exam)
        next_status = resolve_status_after_question_save(exam.exam_type, complete)
        if next_status != exam.status:
            _require_transition(actor, exam, next_status, "Anda tidak berwenang mengajukan naskah ini.")
            exam.status = next_status
            exam.save(update_fields=['status', 'updated_at'])
        return exam, next_status, complete


def withdraw_submission(exam_id, actor):
    with transaction.atomic():
        exam = _locked_exam(exam_id)
        if exam.status != 'waiting_validation':
            raise LifecycleError("Naskah ini tidak sedang menunggu verifikasi.")
        if actor.is_admin or not is_exam_member(exam, actor.teacher):
            raise LifecycleError("Hanya guru pengampu yang bisa menarik pengajuan.", status=403)
        _require_transition(actor, exam, 'pending_selection', "Pengajuan ini tidak bisa ditarik.")
        exam.status = 'pending_selection'
        exam.save(update_fields=['status', 'updated_at'])
        return exam


def verify_exam(exam_id, actor):
    with transaction.atomic():
        exam = _locked_exam(exam_id)
        _require_transition(actor, exam, 'validated', "Hanya admin yang bisa memverifikasi naskah yang sedang diajukan.")
        if not is_question_set_complete(exam):
            raise LifecycleError(
                f"Naskah belum lengkap ({exam.exam_questions.count()} dari {exam.target_question_count} soal, "
                "atau ada guru yang belum memenuhi kuotanya)."
            )
        exam.status = 'validated'
        exam.save(update_fields=['status', 'updated_at'])
        return exam


def reject_exam(exam_id, actor, note):
    with transaction.atomic():
        exam = _locked_exam(exam_id)
        if not actor.is_admin:
            raise LifecycleError("Hanya admin yang bisa mengembalikan naskah ke guru.", status=403)
        _require_transition(actor, exam, 'pending_selection', "Naskah ini tidak sedang menunggu verifikasi.")
        note = _require_note(note)
        exam.status = 'pending_selection'
        _record_review(exam, actor, note)
        exam.save(update_fields=['status', 'review_note', 'reviewed_by', 'reviewed_at', 'updated_at'])
        return exam


def unlock_block_reason(exam, actor):
    """Alasan buka kunci ditolak, atau None bila boleh. Dipakai juga untuk menampilkan tombol."""
    if exam.status != 'validated':
        return "Naskah belum terverifikasi."
    if not can_transition_status(actor.transition_role, exam.exam_type, 'validated', 'pending_selection'):
        return "Naskah ujian resmi hanya bisa dibuka kuncinya oleh admin."
    if not actor.is_admin and not is_exam_member(exam, actor.teacher):
        return "Anda bukan guru pengampu paket ujian ini."
    started = exam.started_sessions_count()
    if started:
        return f"Tidak bisa dibuka: {started} siswa sudah mulai mengerjakan."
    return None


def unlock_exam(exam_id, actor, note):
    with transaction.atomic():
        exam = _locked_exam(exam_id)
        reason = unlock_block_reason(exam, actor)
        if reason:
            raise LifecycleError(reason, status=409)
        note = _require_note(note)
        exam.status = 'pending_selection'
        _record_review(exam, actor, note)
        exam.save(update_fields=['status', 'review_note', 'reviewed_by', 'reviewed_at', 'updated_at'])
        return exam


def can_regenerate_token(exam, actor):
    """UH: guru pemilik paket. Ujian resmi: hanya admin/kurikulum."""
    if actor.is_admin:
        return True
    return exam.exam_type == 'UH' and is_exam_member(exam, actor.teacher)


def regenerate_token(exam_id, actor):
    """Token baru diterapkan ke paket dan semua jadwalnya agar siswa di jadwal mana pun memakai token yang sama."""
    with transaction.atomic():
        exam = _locked_exam(exam_id)
        if not can_regenerate_token(exam, actor):
            raise LifecycleError("Anda tidak berwenang memperbarui token ujian ini.", status=403)
        new_token = generate_exam_token(6)
        exam.token = new_token
        exam.save(update_fields=['token', 'updated_at'])
        Schedule.objects.filter(exam=exam).update(token=new_token, updated_at=timezone.now())
        return exam

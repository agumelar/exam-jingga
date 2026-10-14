"""
Arsip dan hapus permanen paket ujian.

Arsip (sehari-hari): paket yang semua jadwalnya sudah lewat disembunyikan dari daftar jadwal; nilai dan
rekapnya tetap tersimpan dan bisa dikembalikan. Admin/kurikulum untuk semua jenis, guru untuk UH miliknya.

Hapus permanen (jarang, hanya admin): hanya untuk paket yang sudah diarsipkan, setelah nama paket diketik
ulang. Sebelum menghapus, rekap nilai disimpan sebagai Excel dan database dibackup ke folder arsip-hapus
(ikut tersalin ke Google Drive bila rclone aktif). Bila backup gagal, tidak ada yang dihapus.
"""
import re
import subprocess
from pathlib import Path

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from apps.accounts.models import Role
from apps.schedules.lifecycle import LifecycleError, is_exam_member
from apps.schedules.models import Exam, ExamPurgeLog

PURGE_ROLES = {Role.ADMIN, Role.PLATFORM_ADMIN}


class ArchiveError(LifecycleError):
    pass


def can_manage_archive(exam, actor):
    if actor.is_admin:
        return True
    return exam.exam_type == 'UH' and is_exam_member(exam, actor.teacher)


def can_purge(actor):
    return bool(getattr(actor.user, 'is_superuser', False)) or actor.role in PURGE_ROLES


def _sessions_in_progress(exam):
    from apps.exam_engine.models import ExamSession
    return ExamSession.objects.filter(schedule__exam=exam, status__in=['active', 'locked']).exists()


def archive_block_reason(exam):
    last_end = max((s.end_time for s in exam.schedules.all() if s.end_time), default=None)
    if last_end is None or last_end > timezone.now():
        return "Paket baru bisa diarsipkan setelah semua jadwalnya lewat."
    if _sessions_in_progress(exam):
        return "Masih ada siswa yang sedang mengerjakan atau terkunci. Selesaikan dulu lewat Monitoring."
    return ''


def _locked(exam_id):
    return Exam.objects.select_for_update().get(pk=exam_id)


def archive_exam(exam_id, actor):
    with transaction.atomic():
        exam = _locked(exam_id)
        if not can_manage_archive(exam, actor):
            raise ArchiveError("Anda tidak berwenang mengarsipkan paket ini.", status=403)
        if exam.archived_at:
            raise ArchiveError("Paket ini sudah diarsipkan.")
        reason = archive_block_reason(exam)
        if reason:
            raise ArchiveError(reason)
        exam.archived_at = timezone.now()
        exam.archived_by = actor.user
        exam.save(update_fields=['archived_at', 'archived_by', 'updated_at'])
        return exam


def unarchive_exam(exam_id, actor):
    with transaction.atomic():
        exam = _locked(exam_id)
        if not can_manage_archive(exam, actor):
            raise ArchiveError("Anda tidak berwenang mengembalikan paket ini.", status=403)
        exam.archived_at = None
        exam.archived_by = None
        exam.save(update_fields=['archived_at', 'archived_by', 'updated_at'])
        return exam


def _slug(text):
    return re.sub(r'[^a-z0-9]+', '-', text.lower()).strip('-')[:40] or 'paket'


def run_pre_delete_backup(label):
    """
    Backup database ke folder arsip-hapus lewat scripts/backup_db.sh (mode --arsip), yang juga menyalin
    folder itu ke Google Drive bila RCLONE_REMOTE diisi. Mengembalikan path file dump.
    """
    script = settings.BACKUP_SCRIPT
    try:
        result = subprocess.run(['bash', script, label, '--arsip'], capture_output=True, text=True, timeout=300)
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise ArchiveError(f"Backup database gagal dijalankan: {exc}. Tidak ada yang dihapus.")
    if result.returncode != 0:
        detail = (result.stderr or result.stdout).strip().splitlines()[-1:] or ['tanpa keterangan']
        raise ArchiveError(f"Backup database gagal ({detail[0]}). Tidak ada yang dihapus.")
    match = re.search(r'-> (\S+\.dump)', result.stdout)
    return match.group(1) if match else ''


def _export_results(exam, folder):
    from apps.reports.views import build_exam_results_export
    folder.mkdir(parents=True, exist_ok=True)
    stamp = timezone.localtime().strftime('%Y%m%d-%H%M')
    path = folder / f"exam-jingga-rekap-{_slug(exam.title)}-{stamp}.xlsx"
    path.write_bytes(build_exam_results_export(exam).content)
    return path


def purge_exam(exam_id, actor, confirm_title):
    from apps.exam_engine.models import ExamSession, StudentAnswer

    if not can_purge(actor):
        raise ArchiveError("Hapus permanen hanya bisa dilakukan admin.", status=403)
    exam = Exam.objects.select_related('subject', 'teacher').get(pk=exam_id)
    if not exam.archived_at:
        raise ArchiveError("Arsipkan paket ini dulu sebelum menghapus permanen.")
    if (confirm_title or '').strip() != exam.title.strip():
        raise ArchiveError("Nama paket yang diketik tidak sama. Tidak ada yang dihapus.", status=422)
    if _sessions_in_progress(exam):
        raise ArchiveError("Masih ada siswa yang sedang mengerjakan atau terkunci.")

    # Simpan rekap dan backup dulu; kegagalan di sini membatalkan penghapusan
    export_path = _export_results(exam, Path(settings.PURGE_ARCHIVE_DIR))
    backup_path = run_pre_delete_backup(f"hapus-{_slug(exam.title)}")

    schedules = list(exam.schedules.select_related('class_room'))
    sessions = ExamSession.objects.filter(schedule__exam=exam)
    with transaction.atomic():
        log = ExamPurgeLog.objects.create(
            exam_id_snapshot=exam.id, title=exam.title, exam_type=exam.exam_type,
            subject_name=exam.subject.name if exam.subject else '',
            teacher_name=exam.teacher.full_name if exam.teacher else '',
            classes=', '.join(sorted({s.class_room.name for s in schedules if s.class_room})),
            first_start=min((s.start_time for s in schedules), default=None),
            schedules_count=len(schedules), sessions_count=sessions.count(),
            answers_count=StudentAnswer.objects.filter(session__in=sessions).count(),
            backup_file=backup_path, export_file=str(export_path), deleted_by=actor.user,
        )
        StudentAnswer.objects.filter(session__in=sessions).delete()
        sessions.delete()
        exam.schedules.all().delete()
        exam.delete()
    return log

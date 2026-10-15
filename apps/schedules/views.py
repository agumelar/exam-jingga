import json
from urllib.parse import parse_qs, urlparse
from django.shortcuts import render, get_object_or_404, redirect
from django.views import View
from django.core.paginator import Paginator
from django.http import Http404, HttpResponse, JsonResponse
from django.contrib import messages
from django.urls import reverse
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.db import transaction
from django.db.models import Q, Count

from apps.accounts.decorators import teacher_required, admin_required
from apps.master_data.models import Subject, ClassRoom, Teacher, TeacherAssignment
from apps.questions.models import Question
from apps.schedules.models import Exam, ExamQuestion, Schedule
from apps.schedules.forms import ScheduleForm
from apps.exam_engine.models import ExamSession
from apps.schedules import archive, lifecycle
from apps.schedules.lifecycle import Actor, LifecycleError
from apps.schedules.utils import generate_exam_token


def _get_current_teacher(user):
    """Helper untuk mengambil objek Teacher dari user login."""
    if not user or not user.is_authenticated:
        return None
    if hasattr(user, 'teacher_profile'):
        return user.teacher_profile
    return Teacher.objects.filter(user=user).first() or Teacher.objects.filter(email=user.email).first()


def _is_staff_admin(user):
    """Cek apakah user memiliki hak akses administratif."""
    if not user or not user.is_authenticated:
        return False
    if user.is_superuser:
        return True
    user_role = str(getattr(user, 'role', '')).lower()
    return user_role in ['admin', 'kurikulum', 'platform_admin', 'data_admin']


def _actor(request):
    return Actor(user=request.user, teacher=_get_current_teacher(request.user))


def _enrich_schedule_data(schedules, actor):
    """Lampirkan progres soal dan hak aksi lifecycle ke setiap kartu jadwal."""
    current_teacher = actor.teacher
    exam_ids = {s.exam_id for s in schedules}
    started_by_exam = dict(
        ExamSession.objects.filter(schedule__exam_id__in=exam_ids)
        .values_list('schedule__exam_id')
        .annotate(n=Count('id'))
    )

    enriched = []
    for s in schedules:
        exam = s.exam
        if not exam:
            continue

        all_eq = exam.exam_questions.select_related('question__created_by').all()
        total_selected = len(all_eq)

        if current_teacher:
            my_count = sum(1 for eq in all_eq if eq.question.created_by_id == current_teacher.id)
        else:
            my_count = total_selected

        s.my_question_count = my_count
        s.total_question_count = total_selected

        s.final_quota = s.teacher_quota if s.teacher_quota > 0 else exam.target_question_count
        s.is_task_done = (exam.status != 'pending_selection') or (my_count >= s.final_quota)

        s.teacher_progress_list = [
            {
                'teacher_id': str(p['teacher'].id),
                'name': p['teacher'].full_name,
                'filled': p['filled'],
                'quota': p['quota'],
                'done': p['done'],
            }
            for p in lifecycle.teacher_quota_progress(exam)
        ]

        is_member = lifecycle.is_exam_member(exam, current_teacher)
        status = exam.status
        s.started_sessions = started_by_exam.get(exam.id, 0)
        s.can_select_questions = status == 'pending_selection' and (is_member or actor.is_admin)
        s.can_verify = actor.is_admin and status == 'waiting_validation'
        s.can_reject = s.can_verify
        s.can_withdraw = not actor.is_admin and is_member and status == 'waiting_validation'
        s.show_unlock = status == 'validated' and (actor.is_admin or (exam.exam_type == 'UH' and is_member))
        s.unlock_blocked_reason = (
            f"Tidak bisa dibuka: {s.started_sessions} siswa sudah mulai mengerjakan."
            if s.show_unlock and s.started_sessions else ''
        )
        s.can_regenerate_token = lifecycle.can_regenerate_token(exam, actor)
        s.is_archived = bool(exam.archived_at)
        if s.is_archived:
            s.can_select_questions = s.can_verify = s.can_reject = s.can_withdraw = False
            s.show_unlock = s.can_regenerate_token = False
        s.can_archive = not s.is_archived and archive.can_manage_archive(exam, actor) and not archive.archive_block_reason(exam)
        s.can_unarchive = s.is_archived and archive.can_manage_archive(exam, actor)
        s.can_purge = s.is_archived and archive.can_purge(actor)
        enriched.append(s)
    return enriched


def _scoped_schedules(actor):
    qs = Schedule.objects.select_related('exam__subject', 'exam__teacher', 'class_room', 'teacher').all()
    if actor.is_admin:
        return qs
    if actor.teacher:
        # Guru melihat jadwal miliknya atau paket yang ia buat
        return qs.filter(Q(teacher=actor.teacher) | Q(exam__teacher=actor.teacher))
    return qs.none()


def _toast(message, level='success'):
    return {'message': message, 'level': level}


def _archive_filter(qs, status_filter):
    """Paket arsip hanya tampil di filter Arsip; filter lain menyembunyikannya."""
    return qs.filter(exam__archived_at__isnull=(status_filter != 'arsip'))


def _current_status_filter(request):
    query = parse_qs(urlparse(request.headers.get('HX-Current-URL', '')).query)
    return (query.get('status') or ['all'])[0]


def _render_schedule_grid(request, toast=None, close_modal=False):
    actor = _actor(request)
    status_filter = _current_status_filter(request)
    qs = _archive_filter(_scoped_schedules(actor), status_filter)
    context = {
        'status_filter': status_filter,
        'can_bulk_purge': status_filter == 'arsip' and archive.can_purge(actor),
        'schedules': _enrich_schedule_data(list(qs.order_by('-start_time')), actor),
        'is_admin': actor.is_admin,
        'user_role': actor.transition_role,
        'current_teacher': actor.teacher,
    }
    res = render(request, 'schedules/partials/schedule_list_grid.html', context)
    if toast:
        res['HX-Trigger'] = json.dumps({'showToast': _toast(toast)})
    if close_modal:
        # Setelah settle: bila dikirim lebih awal, form di dalam modal sudah
        # terhapus sebelum htmx sempat men-swap grid.
        res['HX-Trigger-After-Settle'] = json.dumps({'closeModal': True})
    return res


def _error_toast_response(message, status):
    """Tolak aksi HTMX tanpa mengganti konten; pesan tampil lewat toast."""
    res = HttpResponse(message, status=status)
    res['HX-Reswap'] = 'none'
    res['HX-Trigger'] = json.dumps({'showToast': _toast(message, 'error')})
    return res


@method_decorator(teacher_required, name='dispatch')
class ScheduleListView(View):
    """
    Menampilkan daftar Jadwal Ujian CBT dengan kartu elevated M3.
    Mendukung pencarian nama ujian/mapel, filter tanggal 'Hari Ini', dan filter status.
    """
    def get(self, request):
        user = request.user
        current_teacher = _get_current_teacher(user)
        is_admin = _is_staff_admin(user)

        search_query = request.GET.get('q', '').strip()
        date_filter = request.GET.get('date_filter', 'Hari Ini')
        status_filter = request.GET.get('status', 'all')

        actor = _actor(request)
        qs = _archive_filter(_scoped_schedules(actor), status_filter)

        # Search filter
        if search_query:
            qs = qs.filter(
                Q(exam__title__icontains=search_query) |
                Q(exam__subject__name__icontains=search_query)
            )

        # Date filter
        if date_filter == 'Hari Ini':
            today = timezone.localdate()
            qs = qs.filter(start_time__date=today)

        # Filter fase: sama dengan Schedule.phase, dinyatakan sebagai query
        now = timezone.now()
        if status_filter == 'aktif':
            qs = qs.filter(exam__status='validated', start_time__lte=now, end_time__gte=now)
        elif status_filter == 'terjadwal':
            qs = qs.filter(exam__status='validated', start_time__gt=now)
        elif status_filter == 'selesai':
            qs = qs.filter(end_time__lt=now)
        elif status_filter == 'draft':
            qs = qs.filter(exam__status__in=['pending_selection', 'waiting_validation'], end_time__gte=now)

        schedules = list(qs.order_by('-start_time'))
        enriched_schedules = _enrich_schedule_data(schedules, actor)

        # Dropdown choices for modal
        available_levels = [10, 11, 12]
        available_classes = ClassRoom.objects.all().order_by('name')
        available_subjects = Subject.objects.all().order_by('name')
        available_teachers = Teacher.objects.all().order_by('full_name')

        context = {
            'schedules': enriched_schedules,
            'schedules_count': len(enriched_schedules),
            'search_query': search_query,
            'date_filter': date_filter,
            'status_filter': status_filter,
            'can_bulk_purge': status_filter == 'arsip' and archive.can_purge(actor),
            'is_admin': is_admin,
            'user_role': 'admin' if is_admin else 'guru',
            'current_teacher': current_teacher,
            'available_levels': available_levels,
            'available_classes': available_classes,
            'available_subjects': available_subjects,
            'available_teachers': available_teachers,
            'active_menu': 'jadwal',
            'page_title': 'Jadwal Ujian',
            'page_subtitle': 'Lifecycle Management Ujian CBT',
        }

        is_htmx = bool(request.headers.get('HX-Request'))
        is_full_page = request.GET.get('full_page', '').lower() in ['true', '1', 'yes']

        if is_htmx and not is_full_page:
            return render(request, 'schedules/partials/schedule_list_grid.html', context)

        return render(request, 'schedules/schedule_list.html', context)


def _assignment_options(actor):
    """Data penugasan untuk pilihan bertingkat jenjang, mapel, guru, kelas di form jadwal."""
    qs = TeacherAssignment.objects.select_related('teacher', 'subject', 'class_room')
    if not actor.is_admin:
        qs = qs.filter(teacher=actor.teacher) if actor.teacher else qs.none()
    return [
        {
            'teacher_id': str(a.teacher_id), 'teacher_name': a.teacher.full_name,
            'subject_id': str(a.subject_id), 'subject_name': a.subject.name,
            'class_id': str(a.class_room_id), 'class_name': a.class_room.name,
            'level': a.class_room.level,
        }
        for a in qs.order_by('subject__name', 'class_room__name') if a.teacher_id and a.subject_id and a.class_room_id
    ]


def _render_form_modal(request, form, actor, schedule=None):
    context = {
        'form': form,
        'values': form.form_values(),
        'editing': schedule is not None,
        'schedule': schedule,
        'is_admin': actor.is_admin,
        'content_locked': bool(schedule and schedule.exam.status != 'pending_selection'),
        'available_levels': [10, 11, 12],
        'assignment_options': _assignment_options(actor),
    }
    res = render(request, 'schedules/partials/schedule_form_modal.html', context)
    if form.is_bound:
        # Form gagal validasi: tampilkan ulang di modal (htmx tidak men-swap respons 4xx)
        res['HX-Retarget'] = '#modal-container'
        res['HX-Reswap'] = 'innerHTML'
    return res


def _can_edit_schedule(actor, schedule):
    """UH: guru pembuat paket atau admin. Ujian resmi: hanya admin/kurikulum."""
    if actor.is_admin:
        return True
    exam = schedule.exam
    return exam.exam_type == 'UH' and actor.teacher is not None and exam.teacher_id == actor.teacher.id


@method_decorator(teacher_required, name='dispatch')
class ScheduleCreateModalView(View):
    """Modal buat jadwal (GET) dan simpan (POST)."""

    def get(self, request):
        actor = _actor(request)
        exam_type = request.GET.get('type', 'PTS' if actor.is_admin else 'UH')
        form = ScheduleForm(is_admin=actor.is_admin, creator_teacher=actor.teacher, initial={
            'exam_type': exam_type if actor.is_admin else 'UH',
            'duration': 60, 'target_question_count': 40, 'session_no': 0,
        })
        return _render_form_modal(request, form, actor)

    def post(self, request):
        actor = _actor(request)
        form = ScheduleForm(request.POST, is_admin=actor.is_admin, creator_teacher=actor.teacher)
        if not form.is_valid():
            return _render_form_modal(request, form, actor)
        created = form.save()
        return _render_schedule_grid(request, toast=f"Jadwal ujian tersimpan ({len(created)} jadwal).", close_modal=True)


@method_decorator(teacher_required, name='dispatch')
class ScheduleEditModalView(View):
    """Modal edit jadwal (GET) dan simpan (POST)."""

    def _load(self, request, pk):
        schedule = get_object_or_404(Schedule.objects.select_related('exam', 'class_room', 'teacher'), pk=pk)
        actor = _actor(request)
        return schedule, actor

    def get(self, request, pk):
        schedule, actor = self._load(request, pk)
        if not _can_edit_schedule(actor, schedule):
            return _error_toast_response("Anda tidak berwenang mengubah jadwal ini.", 403)
        form = ScheduleForm(schedule_instance=schedule, is_admin=actor.is_admin, creator_teacher=actor.teacher)
        return _render_form_modal(request, form, actor, schedule)

    def post(self, request, pk):
        schedule, actor = self._load(request, pk)
        if not _can_edit_schedule(actor, schedule):
            return _error_toast_response("Anda tidak berwenang mengubah jadwal ini.", 403)
        form = ScheduleForm(request.POST, schedule_instance=schedule, is_admin=actor.is_admin, user=request.user,
                            creator_teacher=actor.teacher)
        if not form.is_valid():
            return _render_form_modal(request, form, actor, schedule)
        form.save()
        return _render_schedule_grid(request, toast="Jadwal ujian diperbarui.", close_modal=True)


def _delete_schedule(schedule):
    """Hapus jadwal (dan paketnya bila jadwal terakhir). Ditolak bila sudah ada sesi siswa."""
    if schedule.exam_sessions.exists():
        raise LifecycleError("Jadwal ini sudah dikerjakan siswa, jadi tidak bisa dihapus langsung. Arsipkan paketnya "
                             "agar hilang dari daftar; hapus permanen oleh admin tersedia dari filter Arsip.")
    exam = schedule.exam
    with transaction.atomic():
        schedule.delete()
        if exam and not exam.schedules.exists():
            exam.delete()


@method_decorator(teacher_required, name='dispatch')
class ScheduleDeleteView(View):
    """Konfirmasi hapus jadwal (GET) dan hapus (POST)."""

    def get(self, request, pk):
        schedule = get_object_or_404(Schedule.objects.select_related('exam', 'class_room'), pk=pk)
        if not _can_edit_schedule(_actor(request), schedule):
            return _error_toast_response("Anda tidak berwenang menghapus jadwal ini.", 403)
        return render(request, 'schedules/partials/schedule_delete_modal.html', {'schedule': schedule})

    def post(self, request, pk):
        schedule = get_object_or_404(Schedule.objects.select_related('exam'), pk=pk)
        if not _can_edit_schedule(_actor(request), schedule):
            return _error_toast_response("Anda tidak berwenang menghapus jadwal ini.", 403)
        try:
            _delete_schedule(schedule)
        except LifecycleError as exc:
            return _error_toast_response(exc.message, exc.status)
        return _render_schedule_grid(request, toast="Jadwal ujian dihapus.", close_modal=True)


@method_decorator(admin_required, name='dispatch')
class BulkDeleteSchedulesView(View):
    """Hapus beberapa jadwal sekaligus (admin). Jadwal yang sudah dikerjakan siswa dilewati."""

    def post(self, request):
        try:
            schedule_ids = json.loads(request.body).get('schedule_ids', [])
        except (ValueError, AttributeError):
            schedule_ids = request.POST.getlist('schedule_ids')

        deleted, skipped = 0, 0
        for schedule in Schedule.objects.filter(id__in=schedule_ids).select_related('exam'):
            try:
                _delete_schedule(schedule)
                deleted += 1
            except LifecycleError:
                skipped += 1
        toast = f"{deleted} jadwal dihapus."
        if skipped:
            toast += (f" {skipped} jadwal dilewati karena sudah dikerjakan siswa. "
                      "Arsipkan paketnya agar hilang dari daftar.")
        return _render_schedule_grid(request, toast=toast)


def _posted_schedule_ids(request):
    try:
        return json.loads(request.body).get('schedule_ids', [])
    except (ValueError, AttributeError):
        return request.POST.getlist('schedule_ids')


@method_decorator(admin_required, name='dispatch')
class BulkPurgeSchedulesView(View):
    """Hapus permanen beberapa paket arsip (admin): satu kalimat konfirmasi, satu backup untuk semuanya."""

    def _exam_ids(self, schedule_ids):
        return list(Schedule.objects.filter(id__in=schedule_ids).values_list('exam_id', flat=True).distinct())

    def _modal(self, request, schedule_ids, error=''):
        return render(request, 'schedules/partials/schedule_bulk_purge_modal.html', {
            'rows': archive.purge_preview(self._exam_ids(schedule_ids)),
            'schedule_ids': schedule_ids,
            'phrase': archive.PURGE_PHRASE,
            'error': error,
        })

    def get(self, request):
        if not archive.can_purge(_actor(request)):
            return _error_toast_response("Hapus permanen hanya bisa dilakukan admin.", 403)
        return self._modal(request, request.GET.getlist('schedule_ids'))

    def post(self, request):
        schedule_ids = _posted_schedule_ids(request)
        try:
            logs, skipped = archive.purge_exams(self._exam_ids(schedule_ids), _actor(request),
                                                request.POST.get('confirm_phrase', ''))
        except archive.ArchiveError as exc:
            if exc.status == 403:
                return _error_toast_response(exc.message, 403)
            return self._modal(request, schedule_ids, error=exc.message)
        toast = (f"{len(logs)} paket dihapus permanen. Rekap nilai dan backup database tersimpan "
                 "di folder arsip-hapus.")
        if skipped:
            toast += f" {len(skipped)} paket dilewati: " + '; '.join(f"{t} ({r})" for t, r in skipped) + '.'
        res = _render_schedule_grid(request, toast=toast, close_modal=True)
        res['HX-Retarget'] = '#schedule-list-grid-container'
        res['HX-Reswap'] = 'outerHTML'
        return res


@method_decorator(admin_required, name='dispatch')
class BulkArchiveSchedulesView(View):
    """Arsipkan paket dari beberapa jadwal terpilih (admin). Paket yang belum lewat atau masih berjalan dilewati."""

    def post(self, request):
        actor = _actor(request)
        exam_ids = set(Schedule.objects.filter(id__in=_posted_schedule_ids(request)).values_list('exam_id', flat=True))
        archived, skipped = 0, 0
        for exam_id in exam_ids:
            try:
                archive.archive_exam(exam_id, actor)
                archived += 1
            except archive.ArchiveError:
                skipped += 1
        toast = f"{archived} paket diarsipkan."
        if skipped:
            toast += f" {skipped} paket dilewati karena jadwalnya belum lewat, masih berjalan, atau sudah diarsipkan."
        return _render_schedule_grid(request, toast=toast)


REASON_MODAL_ACTIONS = {
    'reject': {
        'title': 'Kembalikan Naskah ke Guru',
        'description': 'Naskah kembali ke status Tunggu Soal. Tulis bagian yang perlu diperbaiki supaya guru tahu apa yang harus diubah.',
        'submit_label': 'Kembalikan ke Guru',
        'placeholder': 'Contoh: Soal nomor 12 belum punya opsi E.',
    },
    'unlock': {
        'title': 'Buka Kunci Naskah',
        'description': 'Naskah kembali ke status Tunggu Soal dan hilang dari layar siswa sampai disimpan ulang. Tulis alasan revisinya.',
        'submit_label': 'Buka Kunci Naskah',
        'placeholder': 'Contoh: Kunci jawaban soal nomor 17 salah.',
    },
}


@method_decorator(teacher_required, name='dispatch')
class ScheduleActionView(View):
    """
    Aksi lifecycle naskah dari kartu jadwal: verify, withdraw, regenerate-token,
    serta reject dan unlock yang memakai modal alasan (GET menampilkan modal).
    """
    def _render_reason_modal(self, request, schedule, action, error='', note=''):
        actor = _actor(request)
        block_reason = lifecycle.unlock_block_reason(schedule.exam, actor) if action == 'unlock' else ''
        context = {
            'schedule': schedule,
            'action': action,
            'copy': REASON_MODAL_ACTIONS[action],
            'error': error,
            'note': note,
            'block_reason': block_reason,
        }
        return render(request, 'schedules/partials/schedule_reason_modal.html', context)

    def _render_purge_modal(self, request, schedule, error='', typed=''):
        return render(request, 'schedules/partials/schedule_purge_modal.html',
                      {'schedule': schedule, 'error': error, 'typed': typed})

    def get(self, request, pk, action):
        schedule = get_object_or_404(Schedule.objects.select_related('exam'), pk=pk)
        if action == 'purge':
            if not archive.can_purge(_actor(request)):
                return _error_toast_response("Hapus permanen hanya bisa dilakukan admin.", 403)
            return self._render_purge_modal(request, schedule)
        if action not in REASON_MODAL_ACTIONS:
            return HttpResponse(status=404)
        return self._render_reason_modal(request, schedule, action)

    def _purge(self, request, schedule, actor):
        typed = request.POST.get('confirm_title', '')
        try:
            log = archive.purge_exam(schedule.exam_id, actor, typed)
        except archive.ArchiveError as exc:
            if exc.status == 403:
                return _error_toast_response(exc.message, 403)
            return self._render_purge_modal(request, schedule, error=exc.message, typed=typed)
        res = _render_schedule_grid(
            request, close_modal=True,
            toast=f"Paket '{log.title}' dihapus permanen. Rekap nilai dan backup database tersimpan di folder arsip-hapus.")
        res['HX-Retarget'] = '#schedule-list-grid-container'
        res['HX-Reswap'] = 'outerHTML'
        return res

    def post(self, request, pk, action):
        schedule = get_object_or_404(Schedule.objects.select_related('exam'), pk=pk)
        actor = _actor(request)
        exam_id = schedule.exam_id

        if action == 'purge':
            return self._purge(request, schedule, actor)

        if action in REASON_MODAL_ACTIONS:
            note = request.POST.get('note', '')
            try:
                if action == 'reject':
                    exam = lifecycle.reject_exam(exam_id, actor, note)
                    toast = f"Naskah '{exam.title}' dikembalikan ke guru."
                else:
                    exam = lifecycle.unlock_exam(exam_id, actor, note)
                    toast = f"Kunci naskah '{exam.title}' dibuka. Soal bisa direvisi."
            except LifecycleError as exc:
                schedule.exam.refresh_from_db()
                return self._render_reason_modal(request, schedule, action, error=exc.message, note=note)
            res = _render_schedule_grid(request, toast=toast, close_modal=True)
            res['HX-Retarget'] = '#schedule-list-grid-container'
            res['HX-Reswap'] = 'outerHTML'
            return res

        handlers = {
            'verify': (lifecycle.verify_exam, "Naskah '{title}' terverifikasi. Ujian terbuka sesuai jam jadwal."),
            'withdraw': (lifecycle.withdraw_submission, "Pengajuan naskah '{title}' ditarik. Soal bisa diubah lagi."),
            'regenerate-token': (lifecycle.regenerate_token, "Token baru: {token}. Berlaku di semua jadwal paket ini."),
            'archive': (archive.archive_exam, "Paket '{title}' diarsipkan. Nilainya tetap bisa dibuka di Hasil Ujian."),
            'unarchive': (archive.unarchive_exam, "Paket '{title}' dikembalikan ke daftar jadwal."),
        }
        if action not in handlers:
            return HttpResponse(status=404)

        handler, message = handlers[action]
        try:
            exam = handler(exam_id, actor)
        except LifecycleError as exc:
            return _error_toast_response(exc.message, exc.status)
        return _render_schedule_grid(request, toast=message.format(title=exam.title, token=exam.token))


QUESTIONS_PER_PAGE = 25


def _resolve_exam(exam_id):
    """exam_id bisa id paket atau id jadwal (tautan lama dari kartu jadwal)."""
    exam = Exam.objects.filter(id=exam_id).select_related('subject', 'teacher').first()
    if exam:
        return exam
    schedule = Schedule.objects.filter(id=exam_id).select_related('exam__subject', 'exam__teacher').first()
    return schedule.exam if schedule else None


def _require_member_exam(request, exam_id):
    exam = _resolve_exam(exam_id)
    actor = _actor(request)
    if exam is None or not (actor.is_admin or lifecycle.is_exam_member(exam, actor.teacher)):
        raise Http404
    return exam, actor


def _collab_info(exam, actor):
    selected_authors = list(exam.exam_questions.values_list('question__created_by_id', flat=True))
    total = len(selected_authors)
    teacher = actor.teacher
    mine = sum(1 for a in selected_authors if teacher and a == teacher.id) if teacher else total
    return {
        'is_collab': lifecycle.is_multi_teacher(exam),
        'quota': lifecycle.teacher_quota_for(exam, teacher),
        'my_count': mine,
        'total_selected': total,
        'target_count': exam.target_question_count,
        'is_full': total >= exam.target_question_count,
    }


@method_decorator(teacher_required, name='dispatch')
class SelectQuestionsView(View):
    """
    Pilih butir soal untuk paket ujian. Guru hanya melihat dan memilih soal buatannya sendiri
    (bank soal milik guru); admin melihat semua soal pada mapel dan jenjang paket.
    """

    def get(self, request, exam_id):
        exam, actor = _require_member_exam(request, exam_id)

        q_filter = Q(subject=exam.subject)
        if exam.level:
            q_filter &= Q(level=exam.level)
        if not actor.is_admin:
            q_filter &= Q(created_by=actor.teacher)
        selected_cp = request.GET.get('cp_code', '').strip()
        if selected_cp:
            q_filter &= Q(cp_code=selected_cp)
        search_query = request.GET.get('q', '').strip()
        if search_query:
            q_filter &= (Q(question_text__icontains=search_query) | Q(cp_name__icontains=search_query))

        bank_qs = Question.objects.filter(q_filter).select_related('created_by', 'subject').order_by('created_at', 'id')
        page = Paginator(bank_qs, QUESTIONS_PER_PAGE).get_page(request.GET.get('page'))

        selected_ids = {str(qid) for qid in exam.exam_questions.values_list('question_id', flat=True)}
        info = _collab_info(exam, actor)
        context = {
            'exam': exam,
            'bank_questions': page.object_list,
            'page_obj': page,
            'selected_ids': selected_ids,
            'others_selected_count': info['total_selected'] - info['my_count'],
            'cp_choices': Question.CP_CHOICES,
            'selected_cp': selected_cp,
            'search_query': search_query,
            'collab_info': info,
            'current_teacher': actor.teacher,
            'is_admin': actor.is_admin,
            'is_locked': exam.is_locked(),
            'page_title': f'Pilih Soal: {exam.title}',
        }
        return render(request, 'schedules/select_questions.html', context)


@method_decorator(teacher_required, name='dispatch')
class ToggleQuestionView(View):
    """Pilih atau lepas satu soal. Semua aturan (kunci, pemilik, mapel, kuota, opsi E) dicek di lifecycle."""

    def post(self, request, exam_id, question_id):
        exam, actor = _require_member_exam(request, exam_id)
        question = get_object_or_404(Question.objects.select_related('created_by'), id=question_id)

        try:
            is_selected = lifecycle.toggle_question(exam.id, question, actor)
        except LifecycleError as exc:
            return _error_toast_response(exc.message, exc.status)

        exam.refresh_from_db()
        try:
            idx = int(request.POST.get('idx', 0))
        except ValueError:
            idx = 0
        context = {
            'q': question,
            'idx': idx,
            'is_selected': is_selected,
            'exam': exam,
            'is_locked': exam.is_locked(),
            'collab_info': _collab_info(exam, actor),
        }
        return render(request, 'schedules/partials/question_selection_row.html', context)


@method_decorator(teacher_required, name='dispatch')
class SaveQuestionsView(View):
    """Simpan pilihan soal; bila lengkap, naskah diajukan (resmi) atau langsung terverifikasi (UH)."""

    def post(self, request, exam_id):
        exam = _resolve_exam(exam_id)
        if not exam:
            messages.error(request, "Paket ujian tidak ditemukan.")
            return redirect('schedules:list')

        try:
            exam, next_status, complete = lifecycle.submit_questions(exam.id, _actor(request))
        except LifecycleError as exc:
            messages.error(request, exc.message)
            return redirect('schedules:list')

        total_selected = exam.exam_questions.count()
        progress = f"{total_selected}/{exam.target_question_count}"
        if next_status == 'validated':
            messages.success(request, f"Soal lengkap ({progress}). Ulangan Harian siap dikerjakan sesuai jam jadwal.")
        elif next_status == 'waiting_validation':
            messages.success(request, f"Soal lengkap ({progress}) dan diajukan ke admin untuk verifikasi.")
        elif total_selected >= exam.target_question_count:
            messages.info(request, f"Pilihan soal tersimpan ({progress}). Masih ada guru yang belum memenuhi kuotanya; naskah diajukan ke admin saat guru terakhir menyimpan kuotanya.")
        else:
            messages.info(request, f"Pilihan soal tersimpan sementara ({progress} soal).")
        return redirect('schedules:list')

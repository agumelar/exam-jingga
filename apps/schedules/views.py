import json
from django.shortcuts import render, get_object_or_404, redirect
from django.views import View
from django.http import HttpResponse, JsonResponse
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
from apps.schedules import lifecycle
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


def _render_schedule_grid(request, toast=None, close_modal=False):
    actor = _actor(request)
    context = {
        'schedules': _enrich_schedule_data(list(_scoped_schedules(actor).order_by('-start_time')), actor),
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
        qs = _scoped_schedules(actor)

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


@method_decorator(teacher_required, name='dispatch')
class ScheduleCreateModalView(View):
    """
    Renders HTMX modal form for creating a new Schedule/Exam and processes POST submission.
    """
    def get(self, request):
        user = request.user
        current_teacher = _get_current_teacher(user)
        is_admin = _is_staff_admin(user)

        exam_type = request.GET.get('type', 'PTS' if is_admin else 'UH')
        token = generate_exam_token(6)

        form = ScheduleForm(
            user=user,
            initial={
                'exam_type': exam_type,
                'token': token,
                'duration': 60,
                'target_question_count': 40,
                'session_no': '0',
            }
        )

        context = {
            'form': form,
            'editing': False,
            'is_admin': is_admin,
            'user_role': 'admin' if is_admin else 'guru',
            'current_teacher': current_teacher,
            'available_levels': [10, 11, 12],
            'available_classes': ClassRoom.objects.all().order_by('name'),
            'available_subjects': Subject.objects.all().order_by('name'),
            'available_teachers': Teacher.objects.all().order_by('full_name'),
            'generated_token': token,
        }
        return render(request, 'schedules/partials/schedule_form_modal.html', context)

    def post(self, request):
        user = request.user
        current_teacher = _get_current_teacher(user)
        is_admin = _is_staff_admin(user)

        if not is_admin and request.POST.get('exam_type', '') != 'UH':
            return HttpResponse("Guru hanya memiliki wewenang untuk menjadwalkan Ulangan Harian (UH).", status=403)

        form = ScheduleForm(request.POST, user=user)
        if form.is_valid():
            created_schedules = form.save(creator_teacher=current_teacher)
            return _render_schedule_grid(
                request,
                toast=f"Jadwal ujian tersimpan ({len(created_schedules)} jadwal).",
                close_modal=True,
            )

        context = {
            'form': form,
            'editing': False,
            'is_admin': is_admin,
            'user_role': 'admin' if is_admin else 'guru',
            'current_teacher': current_teacher,
            'available_levels': [10, 11, 12],
            'available_classes': ClassRoom.objects.all().order_by('name'),
            'available_subjects': Subject.objects.all().order_by('name'),
            'available_teachers': Teacher.objects.all().order_by('full_name'),
            'generated_token': request.POST.get('token', generate_exam_token(6)),
        }
        return render(request, 'schedules/partials/schedule_form_modal.html', context, status=422)


@method_decorator(teacher_required, name='dispatch')
class ScheduleEditModalView(View):
    """
    Renders HTMX modal form for editing an existing Schedule and processes POST update.
    """
    def get(self, request, pk):
        schedule = get_object_or_404(Schedule.objects.select_related('exam', 'class_room', 'teacher'), pk=pk)
        user = request.user
        current_teacher = _get_current_teacher(user)
        is_admin = _is_staff_admin(user)

        # Check edit permission
        if not is_admin and schedule.exam.exam_type != 'UH':
            return HttpResponse("<script>alert('Anda tidak memiliki izin mengedit jadwal ini');</script>", status=403)

        form = ScheduleForm(user=user, schedule_instance=schedule)
        context = {
            'form': form,
            'editing': True,
            'schedule': schedule,
            'is_admin': is_admin,
            'user_role': 'admin' if is_admin else 'guru',
            'current_teacher': current_teacher,
            'available_levels': [10, 11, 12],
            'available_classes': ClassRoom.objects.all().order_by('name'),
            'available_subjects': Subject.objects.all().order_by('name'),
            'available_teachers': Teacher.objects.all().order_by('full_name'),
            'generated_token': schedule.token,
        }
        return render(request, 'schedules/partials/schedule_form_modal.html', context)

    def post(self, request, pk):
        schedule = get_object_or_404(Schedule.objects.select_related('exam'), pk=pk)
        user = request.user
        current_teacher = _get_current_teacher(user)
        is_admin = _is_staff_admin(user)

        if not is_admin and schedule.exam.exam_type != 'UH':
            return HttpResponse("Unauthorized", status=403)

        form = ScheduleForm(request.POST, user=user, schedule_instance=schedule)
        if form.is_valid():
            form.save(creator_teacher=current_teacher)
            return _render_schedule_grid(request, toast="Jadwal ujian diperbarui.", close_modal=True)

        context = {
            'form': form,
            'editing': True,
            'schedule': schedule,
            'is_admin': is_admin,
            'user_role': 'admin' if is_admin else 'guru',
            'current_teacher': current_teacher,
            'available_levels': [10, 11, 12],
            'available_classes': ClassRoom.objects.all().order_by('name'),
            'available_subjects': Subject.objects.all().order_by('name'),
            'available_teachers': Teacher.objects.all().order_by('full_name'),
            'generated_token': request.POST.get('token', schedule.token),
        }
        return render(request, 'schedules/partials/schedule_form_modal.html', context, status=422)


@method_decorator(teacher_required, name='dispatch')
class ScheduleDeleteView(View):
    """
    Menampilkan konfirmasi hapus jadwal (GET) dan mengeksekusi penghapusan (POST).
    """
    def get(self, request, pk):
        schedule = get_object_or_404(Schedule.objects.select_related('exam', 'class_room'), pk=pk)
        return render(request, 'schedules/partials/schedule_delete_modal.html', {'schedule': schedule})

    def post(self, request, pk):
        schedule = get_object_or_404(Schedule.objects.select_related('exam'), pk=pk)
        user = request.user
        current_teacher = _get_current_teacher(user)
        is_admin = _is_staff_admin(user)

        if not is_admin and schedule.exam.exam_type != 'UH':
            return HttpResponse("Unauthorized", status=403)

        exam = schedule.exam
        schedule.delete()

        # If exam has no more schedules left, clean up exam as well
        if exam and exam.schedules.count() == 0:
            exam.delete()

        return _render_schedule_grid(request, toast="Jadwal ujian dihapus.", close_modal=True)


@method_decorator(admin_required, name='dispatch')
class BulkDeleteSchedulesView(View):
    """
    Menghapus beberapa jadwal terpilih sekaligus (Admin only).
    """
    def post(self, request):
        try:
            body = json.loads(request.body)
            schedule_ids = body.get('schedule_ids', [])
        except (ValueError, json.JSONDecodeError):
            schedule_ids = request.POST.getlist('schedule_ids')

        if schedule_ids:
            schedules = Schedule.objects.filter(id__in=schedule_ids).select_related('exam')
            exam_ids = [s.exam_id for s in schedules if s.exam_id]
            schedules.delete()

            # Clean up orphaned exams
            for eid in set(exam_ids):
                if not Schedule.objects.filter(exam_id=eid).exists():
                    Exam.objects.filter(id=eid).delete()

        return _render_schedule_grid(request, toast=f"{len(schedule_ids)} jadwal dihapus.")


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

    def get(self, request, pk, action):
        schedule = get_object_or_404(Schedule.objects.select_related('exam'), pk=pk)
        if action not in REASON_MODAL_ACTIONS:
            return HttpResponse(status=404)
        return self._render_reason_modal(request, schedule, action)

    def post(self, request, pk, action):
        schedule = get_object_or_404(Schedule.objects.select_related('exam'), pk=pk)
        actor = _actor(request)
        exam_id = schedule.exam_id

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
        }
        if action not in handlers:
            return HttpResponse(status=404)

        handler, message = handlers[action]
        try:
            exam = handler(exam_id, actor)
        except LifecycleError as exc:
            return _error_toast_response(exc.message, exc.status)
        return _render_schedule_grid(request, toast=message.format(title=exam.title, token=exam.token))


@method_decorator(teacher_required, name='dispatch')
class SelectQuestionsView(View):
    """
    Antarmuka pemilihan butir naskah soal dari Bank Soal (SelectQuestions.jsx).
    Mendukung seleksi soal real-time dengan HTMX, kuota per-guru, dan indikator kolaborasi.
    """
    def get(self, request, exam_id):
        # Resolve exam: exam_id can be Exam UUID or Schedule UUID
        exam = Exam.objects.filter(id=exam_id).select_related('subject', 'teacher').first()
        schedule = None
        if not exam:
            schedule = Schedule.objects.filter(id=exam_id).select_related('exam__subject', 'exam__teacher').first()
            if schedule:
                exam = schedule.exam

        if not exam:
            messages.error(request, "Paket ujian tidak ditemukan.")
            return redirect('schedules:list')

        user = request.user
        current_teacher = _get_current_teacher(user)
        is_admin = _is_staff_admin(user)

        # Questions from Question Bank matching subject and level
        q_filter = Q(subject=exam.subject)
        if exam.level:
            q_filter &= Q(level=exam.level)
        
        selected_cp = request.GET.get('cp_code', '').strip()
        if selected_cp:
            q_filter &= Q(cp_code=selected_cp)

        search_query = request.GET.get('q', '').strip()
        if search_query:
            q_filter &= (Q(question_text__icontains=search_query) | Q(cp_name__icontains=search_query))

        # If teacher, show questions created by teacher or available in subject
        bank_questions = Question.objects.filter(q_filter).select_related('created_by', 'subject').order_by('created_at')

        # Selected questions
        selected_links = list(exam.exam_questions.select_related('question__created_by').all())
        all_selected_ids = [eq.question_id for eq in selected_links]

        if current_teacher:
            my_selected_ids = [eq.question_id for eq in selected_links if eq.question.created_by_id == current_teacher.id]
            others_selected_ids = [eq.question_id for eq in selected_links if eq.question.created_by_id != current_teacher.id]
        else:
            my_selected_ids = all_selected_ids
            others_selected_ids = []

        is_collab = exam.exam_type in ['PAS', 'PAT', 'PAS/PAT', 'SAJ']
        
        # Determine quota
        if schedule and schedule.teacher_quota > 0:
            quota = schedule.teacher_quota
        elif current_teacher and is_collab:
            teacher_sched = Schedule.objects.filter(exam=exam, teacher=current_teacher).first()
            quota = teacher_sched.teacher_quota if teacher_sched and teacher_sched.teacher_quota > 0 else exam.target_question_count
        else:
            quota = exam.target_question_count

        total_selected = len(all_selected_ids)
        my_count = len(my_selected_ids)

        context = {
            'exam': exam,
            'schedule': schedule,
            'bank_questions': bank_questions,
            'selected_ids': [str(qid) for qid in my_selected_ids],
            'all_selected_ids': [str(qid) for qid in all_selected_ids],
            'others_selected_count': len(others_selected_ids),
            'cp_choices': Question.CP_CHOICES,
            'selected_cp': selected_cp,
            'search_query': search_query,
            'collab_info': {
                'is_collab': is_collab,
                'quota': quota,
                'my_count': my_count,
                'total_selected': total_selected,
                'target_count': exam.target_question_count,
                'is_full': total_selected >= exam.target_question_count,
            },
            'current_teacher': current_teacher,
            'is_admin': is_admin,
            'is_locked': exam.is_locked(),
            'page_title': f'Pilih Soal: {exam.title}',
        }
        return render(request, 'schedules/select_questions.html', context)


@method_decorator(teacher_required, name='dispatch')
class ToggleQuestionView(View):
    """
    HTMX Endpoint untuk toggle seleksi 1 butir soal.
    URL: POST /schedules/exam/<uuid:exam_id>/toggle-question/<uuid:question_id>/
    """
    def post(self, request, exam_id, question_id):
        exam = Exam.objects.filter(id=exam_id).first()
        if not exam:
            schedule = Schedule.objects.filter(id=exam_id).select_related('exam').first()
            if schedule:
                exam = schedule.exam

        if not exam:
            return HttpResponse("Paket ujian tidak ditemukan", status=404)

        question = get_object_or_404(Question, id=question_id)
        actor = _actor(request)
        current_teacher = actor.teacher

        with transaction.atomic():
            exam = Exam.objects.select_for_update().get(pk=exam.pk)
            try:
                lifecycle.ensure_questions_editable(exam, actor)
            except LifecycleError as exc:
                return _error_toast_response(exc.message, exc.status)

            existing_eq = ExamQuestion.objects.filter(exam=exam, question=question).first()
            if existing_eq:
                existing_eq.delete()
                is_selected = False
            else:
                current_count = exam.exam_questions.count()
                if current_count >= exam.target_question_count:
                    return _error_toast_response(
                        f"Target {exam.target_question_count} soal sudah terpenuhi. Lepas satu soal dulu untuk menggantinya.",
                        400,
                    )
                ExamQuestion.objects.create(exam=exam, question=question, order_number=current_count + 1)
                is_selected = True

        # Recalculate counts
        all_eq = list(exam.exam_questions.select_related('question').all())
        total_selected = len(all_eq)
        if current_teacher:
            my_count = sum(1 for eq in all_eq if eq.question.created_by_id == current_teacher.id)
        else:
            my_count = total_selected

        is_collab = exam.exam_type in ['PAS', 'PAT', 'PAS/PAT', 'SAJ']
        quota = exam.target_question_count

        context = {
            'q': question,
            'idx': int(request.POST.get('idx', 0)),
            'is_selected': is_selected,
            'exam': exam,
            'collab_info': {
                'is_collab': is_collab,
                'quota': quota,
                'my_count': my_count,
                'total_selected': total_selected,
                'target_count': exam.target_question_count,
                'is_full': total_selected >= exam.target_question_count,
            }
        }
        return render(request, 'schedules/partials/question_selection_row.html', context)


@method_decorator(teacher_required, name='dispatch')
class SaveQuestionsView(View):
    """
    Menyimpan & mengunci pilihan butir soal ujian.
    Jika soal sudah lengkap -> update status paket ujian (validated untuk UH, waiting_validation untuk PTS/PAS/PAT/SAJ).
    """
    def post(self, request, exam_id):
        exam = Exam.objects.filter(id=exam_id).first()
        if not exam:
            schedule = Schedule.objects.filter(id=exam_id).select_related('exam').first()
            if schedule:
                exam = schedule.exam

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

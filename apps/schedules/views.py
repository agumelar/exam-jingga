import json
from django.shortcuts import render, get_object_or_404, redirect
from django.views import View
from django.http import HttpResponse, JsonResponse
from django.contrib import messages
from django.urls import reverse
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.db.models import Q, Count

from apps.accounts.decorators import teacher_required, admin_required
from apps.master_data.models import Subject, ClassRoom, Teacher, TeacherAssignment
from apps.questions.models import Question
from apps.schedules.models import Exam, ExamQuestion, Schedule
from apps.schedules.forms import ScheduleForm
from apps.schedules.utils import (
    generate_exam_token,
    resolve_status_after_question_save,
    can_transition_status,
)


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


def _enrich_schedule_data(schedules, current_teacher=None):
    """Helper to attach question counts, collaborator progress, etc. to schedule objects."""
    enriched = []
    for s in schedules:
        exam = s.exam
        if not exam:
            continue
        
        # Calculate selected question counts
        all_eq = exam.exam_questions.select_related('question__created_by').all()
        total_selected = len(all_eq)
        
        if current_teacher:
            my_count = sum(1 for eq in all_eq if eq.question.created_by_id == current_teacher.id)
        else:
            my_count = total_selected
            
        s.my_question_count = my_count
        s.total_question_count = total_selected
        
        # Final quota
        s.final_quota = s.teacher_quota if s.teacher_quota > 0 else exam.target_question_count
        s.is_task_done = (exam.status != 'pending_selection') or (my_count >= s.final_quota)
        
        # Build progress list for multi-teacher exams
        other_schedules = Schedule.objects.filter(exam=exam).select_related('teacher')
        progress_list = []
        for os in other_schedules:
            if os.teacher:
                t_count = sum(1 for eq in all_eq if eq.question.created_by_id == os.teacher.id)
                t_quota = os.teacher_quota if os.teacher_quota > 0 else exam.target_question_count
                progress_list.append({
                    'teacher_id': str(os.teacher.id),
                    'name': os.teacher.full_name,
                    'filled': t_count,
                    'quota': t_quota,
                    'done': t_count >= t_quota
                })
        s.teacher_progress_list = progress_list
        enriched.append(s)
    return enriched


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

        qs = Schedule.objects.select_related('exam__subject', 'exam__teacher', 'class_room', 'teacher').all()

        if not is_admin:
            # Teachers only see their own schedules or exams they created
            if current_teacher:
                qs = qs.filter(Q(teacher=current_teacher) | Q(exam__teacher=current_teacher))
            else:
                qs = qs.none()

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

        # Status filter
        if status_filter == 'aktif':
            qs = qs.filter(status='active')
        elif status_filter == 'selesai':
            qs = qs.filter(status='closed')
        elif status_filter == 'draft':
            qs = qs.filter(status='draft')

        schedules = list(qs.order_by('-start_time'))
        enriched_schedules = _enrich_schedule_data(schedules, current_teacher)

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

        form = ScheduleForm(request.POST, user=user)
        if form.is_valid():
            created_schedules = form.save(creator_teacher=current_teacher)
            messages.success(request, f"Jadwal ujian berhasil dibuat ({len(created_schedules)} sesi/jadwal tersimpan).")
            
            # Return updated schedule list partial via HTMX
            qs = Schedule.objects.select_related('exam__subject', 'exam__teacher', 'class_room', 'teacher').all()
            if not is_admin:
                qs = qs.filter(Q(teacher=current_teacher) | Q(exam__teacher=current_teacher))
            
            enriched_schedules = _enrich_schedule_data(list(qs.order_by('-start_time')), current_teacher)
            context = {
                'schedules': enriched_schedules,
                'is_admin': is_admin,
                'user_role': 'admin' if is_admin else 'guru',
                'current_teacher': current_teacher,
            }
            res = render(request, 'schedules/partials/schedule_list_grid.html', context)
            res['HX-Trigger'] = json.dumps({'closeModal': True, 'showToast': 'Jadwal ujian berhasil disimpan!'})
            return res

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
            messages.success(request, "Jadwal ujian berhasil diperbarui.")

            qs = Schedule.objects.select_related('exam__subject', 'exam__teacher', 'class_room', 'teacher').all()
            if not is_admin:
                qs = qs.filter(Q(teacher=current_teacher) | Q(exam__teacher=current_teacher))

            enriched_schedules = _enrich_schedule_data(list(qs.order_by('-start_time')), current_teacher)
            context = {
                'schedules': enriched_schedules,
                'is_admin': is_admin,
                'user_role': 'admin' if is_admin else 'guru',
                'current_teacher': current_teacher,
            }
            res = render(request, 'schedules/partials/schedule_list_grid.html', context)
            res['HX-Trigger'] = json.dumps({'closeModal': True, 'showToast': 'Jadwal berhasil diperbarui!'})
            return res

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

        # Return updated grid
        qs = Schedule.objects.select_related('exam__subject', 'exam__teacher', 'class_room', 'teacher').all()
        if not is_admin:
            qs = qs.filter(Q(teacher=current_teacher) | Q(exam__teacher=current_teacher))

        enriched_schedules = _enrich_schedule_data(list(qs.order_by('-start_time')), current_teacher)
        context = {
            'schedules': enriched_schedules,
            'is_admin': is_admin,
            'user_role': 'admin' if is_admin else 'guru',
            'current_teacher': current_teacher,
        }
        res = render(request, 'schedules/partials/schedule_list_grid.html', context)
        res['HX-Trigger'] = json.dumps({'closeModal': True, 'showToast': 'Jadwal berhasil dihapus.'})
        return res


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

        user = request.user
        current_teacher = _get_current_teacher(user)
        is_admin = _is_staff_admin(user)

        qs = Schedule.objects.select_related('exam__subject', 'exam__teacher', 'class_room', 'teacher').all()
        enriched_schedules = _enrich_schedule_data(list(qs.order_by('-start_time')), current_teacher)
        context = {
            'schedules': enriched_schedules,
            'is_admin': is_admin,
            'user_role': 'admin' if is_admin else 'guru',
            'current_teacher': current_teacher,
        }
        res = render(request, 'schedules/partials/schedule_list_grid.html', context)
        res['HX-Trigger'] = json.dumps({'showToast': f'{len(schedule_ids)} jadwal berhasil dihapus.'})
        return res


@method_decorator(teacher_required, name='dispatch')
class ScheduleActionView(View):
    """
    Handles exam lifecycle actions: verify, unlock, regenerate-token.
    """
    def post(self, request, pk, action):
        schedule = get_object_or_404(Schedule.objects.select_related('exam'), pk=pk)
        exam = schedule.exam
        user = request.user
        user_role = 'admin' if _is_staff_admin(user) else 'guru'

        if action == 'verify':
            if not can_transition_status(user_role, exam.exam_type, exam.status, 'validated'):
                return HttpResponse("Transisi status verifikasi tidak diizinkan.", status=403)
            exam.status = 'validated'
            exam.save()
            messages.success(request, f"Paket ujian '{exam.title}' berhasil diverifikasi!")

        elif action == 'unlock':
            if not can_transition_status(user_role, exam.exam_type, exam.status, 'pending_selection'):
                return HttpResponse("Transisi buka kunci tidak diizinkan.", status=403)
            exam.status = 'pending_selection'
            exam.save()
            messages.success(request, f"Kunci naskah '{exam.title}' telah dibuka. Silakan revisi butir soal.")

        elif action == 'regenerate-token':
            new_token = generate_exam_token(6)
            schedule.token = new_token
            schedule.save()
            if exam:
                exam.token = new_token
                exam.save()
            messages.success(request, f"Token berhasil diperbarui: {new_token}")

        # Return updated grid
        current_teacher = _get_current_teacher(user)
        is_admin = _is_staff_admin(user)
        qs = Schedule.objects.select_related('exam__subject', 'exam__teacher', 'class_room', 'teacher').all()
        if not is_admin:
            qs = qs.filter(Q(teacher=current_teacher) | Q(exam__teacher=current_teacher))

        enriched_schedules = _enrich_schedule_data(list(qs.order_by('-start_time')), current_teacher)
        context = {
            'schedules': enriched_schedules,
            'is_admin': is_admin,
            'user_role': user_role,
            'current_teacher': current_teacher,
        }
        res = render(request, 'schedules/partials/schedule_list_grid.html', context)
        res['HX-Trigger'] = json.dumps({'showToast': 'Status berhasil diperbarui.'})
        return res


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
        user = request.user
        current_teacher = _get_current_teacher(user)

        existing_eq = ExamQuestion.objects.filter(exam=exam, question=question).first()
        is_selected = False

        if existing_eq:
            # Remove selection
            existing_eq.delete()
            is_selected = False
        else:
            # Check limit
            current_count = exam.exam_questions.count()
            if current_count >= exam.target_question_count:
                return HttpResponse(
                    f"<script>alert('Target {exam.target_question_count} butir soal sudah terpenuhi!');</script>",
                    status=400
                )
            
            # Add selection
            ExamQuestion.objects.create(
                exam=exam,
                question=question,
                order_number=current_count + 1
            )
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

        total_selected = exam.exam_questions.count()
        is_full = total_selected >= exam.target_question_count

        next_status = resolve_status_after_question_save(exam.exam_type, is_full)
        if next_status:
            exam.status = next_status
            exam.save()

        if is_full:
            if exam.exam_type == 'UH':
                messages.success(request, f"Soal lengkap ({total_selected}/{exam.target_question_count})! Ulangan Harian siap dilaksanakan.")
            else:
                messages.success(request, f"Soal lengkap ({total_selected}/{exam.target_question_count}) & diajukan ke Admin untuk verifikasi.")
        else:
            messages.info(request, f"Pilihan soal berhasil disimpan sementara ({total_selected}/{exam.target_question_count} butir soal).")

        return redirect('schedules:list')

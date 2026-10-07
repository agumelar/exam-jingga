import json
from django.shortcuts import render, get_object_or_404, redirect
from django.views.generic import View
from django.utils.decorators import method_decorator
from django.contrib import messages
from django.http import HttpResponse, JsonResponse
from django.db.models import Q, Count
from apps.accounts.decorators import teacher_required
from apps.accounts.models import Role
from apps.master_data.models import Subject, Teacher, ClassRoom, TeacherAssignment
from .models import Question
from .forms import QuestionForm


def get_current_teacher(user):
    """Helper to retrieve Teacher profile for the authenticated user."""
    if not user.is_authenticated:
        return None
    if hasattr(user, 'teacher_profile') and user.teacher_profile:
        return user.teacher_profile
    teacher = Teacher.objects.filter(user=user).first()
    if teacher:
        return teacher
    if user.email:
        teacher = Teacher.objects.filter(email__iexact=user.email).first()
        if teacher:
            return teacher
    return None


def get_scoped_questions_queryset(request):
    """Filter questions queryset based on user role, assigned subjects, and query parameters."""
    user = request.user
    qs = Question.objects.select_related('subject', 'created_by').all().order_by('-created_at')

    # RBAC Scoping
    is_staff_admin = (
        user.is_superuser or
        getattr(user, 'is_admin', False) or
        user.role in [Role.ADMIN, Role.PLATFORM_ADMIN, Role.DATA_ADMIN, Role.KURIKULUM]
    )

    if not is_staff_admin:
        # User is Guru / Pengawas
        teacher = get_current_teacher(user)
        if teacher:
            assigned_subject_ids = TeacherAssignment.objects.filter(
                teacher=teacher
            ).values_list('subject_id', flat=True)
            qs = qs.filter(
                Q(created_by=teacher) | Q(subject_id__in=assigned_subject_ids)
            )
        else:
            qs = qs.filter(created_by__user=user)

    # Apply query parameter filters
    subject_id = request.GET.get('subject_id', '').strip() or request.POST.get('filter_subject_id', '').strip()
    level = request.GET.get('level', '').strip() or request.POST.get('filter_level', '').strip()
    teacher_id = request.GET.get('teacher_id', '').strip() or request.POST.get('filter_teacher_id', '').strip()
    cp_code = request.GET.get('cp_code', '').strip() or request.POST.get('filter_cp_code', '').strip()
    q = request.GET.get('q', '').strip() or request.POST.get('filter_q', '').strip()

    if subject_id:
        qs = qs.filter(subject_id=subject_id)
    if level and level.isdigit():
        qs = qs.filter(level=int(level))
    if teacher_id and is_staff_admin:
        qs = qs.filter(created_by_id=teacher_id)
    if cp_code:
        qs = qs.filter(cp_code=cp_code)
    if q:
        qs = qs.filter(
            Q(question_text__icontains=q) |
            Q(cp_name__icontains=q) |
            Q(option_a__icontains=q) |
            Q(option_b__icontains=q) |
            Q(option_c__icontains=q) |
            Q(option_d__icontains=q) |
            Q(option_e__icontains=q) |
            Q(subject__name__icontains=q)
        )

    return qs


from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger


def get_teachers_subject_mapping(teachers_qs=None):
    """Returns a list of dicts with teacher id, name, assigned subject_ids, and subject_levels mapping."""
    if teachers_qs is None:
        teachers_qs = Teacher.objects.prefetch_related(
            'assignments__subject',
            'assignments__class_room'
        ).all().order_by('full_name')
    else:
        teachers_qs = teachers_qs.prefetch_related(
            'assignments__subject',
            'assignments__class_room'
        )

    teachers_data = []
    for t in teachers_qs:
        subj_ids = set()
        subject_levels = {}
        all_levels = set()
        for a in t.assignments.all():
            if a.subject_id:
                s_id = str(a.subject_id)
                subj_ids.add(s_id)
                if s_id not in subject_levels:
                    subject_levels[s_id] = set()
                if a.class_room and a.class_room.level:
                    lvl = int(a.class_room.level)
                    subject_levels[s_id].add(lvl)
                    all_levels.add(lvl)

        subj_levels_serialized = {k: sorted(list(v)) for k, v in subject_levels.items()}
        teachers_data.append({
            'id': str(t.id),
            'name': t.full_name,
            'subject_ids': sorted(list(subj_ids)),
            'subject_levels': subj_levels_serialized,
            'levels': sorted(list(all_levels)),
        })
    return teachers_data


def get_subjects_level_mapping(subjects_qs=None, teacher=None):
    """
    Returns a list of dicts with subject id, name, code, and list of levels
    where this subject is taught (from TeacherAssignment / ClassRoom.level).
    If teacher is provided, only levels assigned to that teacher are included.
    """
    if subjects_qs is None:
        subjects_qs = Subject.objects.all().order_by('name')

    assign_qs = TeacherAssignment.objects.filter(
        subject__isnull=False,
        class_room__isnull=False
    )
    if teacher:
        assign_qs = assign_qs.filter(teacher=teacher)

    assignments = assign_qs.values('subject_id', 'class_room__level').distinct()

    subject_levels_map = {}
    for a in assignments:
        s_id = str(a['subject_id'])
        lvl = a['class_room__level']
        if lvl:
            subject_levels_map.setdefault(s_id, set()).add(int(lvl))

    # Also inspect Question table if subject has questions with levels
    q_qs = Question.objects.filter(subject__isnull=False)
    if teacher:
        q_qs = q_qs.filter(created_by=teacher)
    q_levels = q_qs.values('subject_id', 'level').distinct()
    for q in q_levels:
        s_id = str(q['subject_id'])
        lvl = q['level']
        if lvl:
            subject_levels_map.setdefault(s_id, set()).add(int(lvl))

    subjects_data = []
    for s in subjects_qs:
        s_id = str(s.id)
        lvls = sorted(list(subject_levels_map.get(s_id, [])))
        # Fallback: if subject has NO assignments and NO questions yet, allow all levels [10, 11, 12]
        if not lvls:
            lvls = [10, 11, 12]
        subjects_data.append({
            'id': s_id,
            'name': s.name,
            'code': s.code or '',
            'levels': lvls,
        })
    return subjects_data


def _render_question_list_partial(request, toast_message=None, status_code=200):
    """Shared helper to render question_list.html partial with full pagination and filter context."""
    user = request.user
    teacher = get_current_teacher(user)
    is_staff_admin = (
        user.is_superuser or
        getattr(user, 'is_admin', False) or
        user.role in [Role.ADMIN, Role.PLATFORM_ADMIN, Role.DATA_ADMIN, Role.KURIKULUM]
    )
    questions_qs = get_scoped_questions_queryset(request)
    filtered_count = questions_qs.count()

    per_page = int(request.GET.get('per_page') or request.POST.get('per_page') or 20)
    paginator = Paginator(questions_qs, per_page)
    page_number = request.GET.get('page') or request.POST.get('page', 1)
    try:
        page_obj = paginator.page(page_number)
    except (PageNotAnInteger, ValueError):
        page_obj = paginator.page(1)
    except EmptyPage:
        page_obj = paginator.page(paginator.num_pages)

    context = {
        'page_obj': page_obj,
        'questions': page_obj.object_list,
        'questions_count': filtered_count,
        'selected_subject': request.GET.get('subject_id', '').strip() or request.POST.get('filter_subject_id', '').strip(),
        'selected_level': request.GET.get('level', '').strip() or request.POST.get('filter_level', '').strip(),
        'selected_teacher': request.GET.get('teacher_id', '').strip() or request.POST.get('filter_teacher_id', '').strip(),
        'selected_cp': request.GET.get('cp_code', '').strip() or request.POST.get('filter_cp_code', '').strip(),
        'search_query': request.GET.get('q', '').strip() or request.POST.get('filter_q', '').strip(),
        'is_staff_admin': is_staff_admin,
        'current_teacher': teacher,
        'toast_message': toast_message,
    }
    return render(request, 'questions/partials/question_list.html', context, status=status_code)


@method_decorator(teacher_required, name='dispatch')
class BankSoalView(View):
    """
    Main Question Bank Dashboard View.
    Renders bank_soal.html with level tabs, subject filter, search bar, and paginated question list.
    """
    template_name = 'questions/bank_soal.html'

    def get(self, request, *args, **kwargs):
        user = request.user
        teacher = get_current_teacher(user)
        is_staff_admin = (
            user.is_superuser or
            getattr(user, 'is_admin', False) or
            user.role in [Role.ADMIN, Role.PLATFORM_ADMIN, Role.DATA_ADMIN, Role.KURIKULUM]
        )

        selected_subject = request.GET.get('subject_id', '').strip()
        selected_level = request.GET.get('level', '').strip()
        selected_teacher = request.GET.get('teacher_id', '').strip() if is_staff_admin else (str(teacher.id) if teacher else '')
        selected_cp = request.GET.get('cp_code', '').strip()

        # Build list of available subjects and teachers mapping
        teachers_data = []
        if is_staff_admin:
            subjects = Subject.objects.all().order_by('name')
            all_teachers = Teacher.objects.prefetch_related('assignments__class_room', 'assignments__subject').all().order_by('full_name')
            teachers_data = get_teachers_subject_mapping(all_teachers)
            subjects_data = get_subjects_level_mapping(subjects)
            if selected_subject:
                teachers = [
                    t for t in all_teachers 
                    if any(str(s) == selected_subject for s in t.assignments.filter(subject__isnull=False).values_list('subject_id', flat=True))
                ]
            else:
                teachers = all_teachers
        else:
            # For teacher, prioritize their assigned subjects
            if teacher:
                assigned_subj_ids = TeacherAssignment.objects.filter(
                    teacher=teacher
                ).values_list('subject_id', flat=True)
                subjects = Subject.objects.filter(
                    Q(id__in=assigned_subj_ids) | Q(questions__created_by=teacher)
                ).distinct().order_by('name')
                if not subjects.exists():
                    subjects = Subject.objects.all().order_by('name')
                teachers_data = get_teachers_subject_mapping(Teacher.objects.filter(id=teacher.id))
                subjects_data = get_subjects_level_mapping(subjects, teacher=teacher)
            else:
                subjects = Subject.objects.all().order_by('name')
                teachers_data = []
                subjects_data = get_subjects_level_mapping(subjects)
            teachers = Teacher.objects.filter(id=teacher.id) if teacher else Teacher.objects.none()

        questions_qs = get_scoped_questions_queryset(request)
        total_questions_count = Question.objects.count() if is_staff_admin else (
            Question.objects.filter(created_by=teacher).count() if teacher else 0
        )
        subjects_count = subjects.count()
        filtered_count = questions_qs.count()

        # Pagination: 20 per page
        per_page = int(request.GET.get('per_page', 20))
        paginator = Paginator(questions_qs, per_page)
        page_number = request.GET.get('page', 1)
        try:
            page_obj = paginator.page(page_number)
        except (PageNotAnInteger, ValueError):
            page_obj = paginator.page(1)
        except EmptyPage:
            page_obj = paginator.page(paginator.num_pages)

        context = {
            'page_title': 'Bank Soal CBT',
            'page_subtitle': 'Kelola & susun butir soal ujian per Mata Pelajaran dan Jenjang Kelas',
            'active_menu': 'bank_soal',
            'page_obj': page_obj,
            'questions': page_obj.object_list,
            'questions_count': filtered_count,
            'total_questions_count': total_questions_count,
            'subjects_count': subjects_count,
            'subjects': subjects,
            'subjects_json': json.dumps(subjects_data),
            'teachers': teachers,
            'teachers_json': json.dumps(teachers_data),
            'levels': [10, 11, 12],
            'cp_choices': Question.CP_CHOICES,
            'selected_subject': selected_subject,
            'selected_level': selected_level,
            'selected_teacher': selected_teacher,
            'selected_cp': selected_cp,
            'search_query': request.GET.get('q', '').strip(),
            'is_staff_admin': is_staff_admin,
            'current_teacher': teacher,
        }
        return render(request, self.template_name, context)


@method_decorator(teacher_required, name='dispatch')
class QuestionFilterView(View):
    """
    HTMX Endpoint returning partial question_list.html.
    Filters questions dynamically as user types or selects filters with pagination support.
    """
    partial_template_name = 'questions/partials/question_list.html'

    def get(self, request, *args, **kwargs):
        return _render_question_list_partial(request)


@method_decorator(teacher_required, name='dispatch')
class QuestionCreateView(View):
    """
    View for creating a new question with HTMX modal form support.
    """
    modal_template_name = 'questions/partials/question_form_modal.html'
    list_template_name = 'questions/partials/question_list.html'

    def get(self, request, *args, **kwargs):
        user = request.user
        teacher = get_current_teacher(user)
        is_staff_admin = (
            user.is_superuser or
            getattr(user, 'is_admin', False) or
            user.role in [Role.ADMIN, Role.PLATFORM_ADMIN, Role.DATA_ADMIN, Role.KURIKULUM]
        )

        if is_staff_admin:
            subjects = Subject.objects.all().order_by('name')
            all_teachers = Teacher.objects.prefetch_related('assignments__class_room', 'assignments__subject').all().order_by('full_name')
            teachers_data = get_teachers_subject_mapping(all_teachers)
            subjects_data = get_subjects_level_mapping(subjects)
        else:
            if teacher:
                assigned_subj_ids = TeacherAssignment.objects.filter(
                    teacher=teacher
                ).values_list('subject_id', flat=True)
                subjects = Subject.objects.filter(
                    Q(id__in=assigned_subj_ids) | Q(questions__created_by=teacher)
                ).distinct().order_by('name')
                if not subjects.exists():
                    subjects = Subject.objects.all().order_by('name')
                all_teachers = Teacher.objects.filter(id=teacher.id)
                teachers_data = get_teachers_subject_mapping(all_teachers)
                subjects_data = get_subjects_level_mapping(subjects, teacher=teacher)
            else:
                subjects = Subject.objects.all().order_by('name')
                all_teachers = Teacher.objects.none()
                teachers_data = []
                subjects_data = get_subjects_level_mapping(subjects)

        preselected_subject = request.GET.get('subject_id', '').strip()
        preselected_level = request.GET.get('level', '').strip()
        preselected_teacher = request.GET.get('teacher_id', '').strip() or (str(teacher.id) if teacher else '')

        if preselected_subject and is_staff_admin:
            filtered_teachers = []
            for t in all_teachers:
                t_assignments = t.assignments.filter(subject_id=preselected_subject)
                if preselected_level and preselected_level.isdigit():
                    t_assignments = t_assignments.filter(class_room__level=int(preselected_level))
                if t_assignments.exists():
                    filtered_teachers.append(t)
            teachers = filtered_teachers if filtered_teachers else all_teachers
        else:
            teachers = all_teachers if is_staff_admin else (Teacher.objects.filter(id=teacher.id) if teacher else Teacher.objects.none())

        if not is_staff_admin and teacher:
            teacher_levels = sorted(list(TeacherAssignment.objects.filter(
                teacher=teacher, class_room__isnull=False
            ).values_list('class_room__level', flat=True).distinct()))
            levels = teacher_levels if teacher_levels else [10, 11, 12]
        else:
            levels = [10, 11, 12]

        context = {
            'question': None,
            'subjects': subjects,
            'subjects_json': json.dumps(subjects_data),
            'teachers': teachers,
            'teachers_json': json.dumps(teachers_data),
            'levels': levels,
            'cp_choices': Question.CP_CHOICES,
            'preselected_subject': preselected_subject,
            'preselected_level': preselected_level,
            'preselected_teacher': preselected_teacher,
            'is_staff_admin': is_staff_admin,
            'current_teacher': teacher,
            'is_edit': False,
        }
        return render(request, self.modal_template_name, context)

    def post(self, request, *args, **kwargs):
        user = request.user
        teacher = get_current_teacher(user)
        is_staff_admin = (
            user.is_superuser or
            getattr(user, 'is_admin', False) or
            user.role in [Role.ADMIN, Role.PLATFORM_ADMIN, Role.DATA_ADMIN, Role.KURIKULUM]
        )

        form = QuestionForm(request.POST, request.FILES)
        if form.is_valid():
            question = form.save(commit=False)
            if not is_staff_admin and teacher:
                question.created_by = teacher
            elif not question.created_by and teacher:
                question.created_by = teacher
            question.save()

            if request.headers.get('HX-Request') or request.POST.get('is_htmx'):
                response = _render_question_list_partial(request, toast_message='Butir soal berhasil ditambahkan ke bank soal.')
                response['HX-Trigger'] = json.dumps({'questionSaved': True, 'closeModal': True})
                return response

            messages.success(request, "Butir soal berhasil ditambahkan ke bank soal.")
            return redirect('questions:bank_soal')

        # Form errors handling
        subjects = Subject.objects.all().order_by('name')
        all_teachers = Teacher.objects.prefetch_related('assignments__class_room', 'assignments__subject').all().order_by('full_name')
        teachers_data = get_teachers_subject_mapping(all_teachers) if is_staff_admin else []
        teachers = all_teachers if is_staff_admin else (Teacher.objects.filter(id=teacher.id) if teacher else Teacher.objects.none())
        subjects_data = get_subjects_level_mapping(subjects, teacher=teacher if not is_staff_admin else None)

        if not is_staff_admin and teacher:
            teacher_levels = sorted(list(TeacherAssignment.objects.filter(
                teacher=teacher, class_room__isnull=False
            ).values_list('class_room__level', flat=True).distinct()))
            levels = teacher_levels if teacher_levels else [10, 11, 12]
        else:
            levels = [10, 11, 12]

        context = {
            'question': None,
            'form': form,
            'errors': form.errors,
            'subjects': subjects,
            'subjects_json': json.dumps(subjects_data),
            'teachers': teachers,
            'teachers_json': json.dumps(teachers_data),
            'levels': levels,
            'cp_choices': Question.CP_CHOICES,
            'is_staff_admin': is_staff_admin,
            'current_teacher': teacher,
            'is_edit': False,
        }
        return render(request, self.modal_template_name, context, status=400)


@method_decorator(teacher_required, name='dispatch')
class QuestionEditView(View):
    """
    View for editing an existing question via HTMX modal form.
    """
    modal_template_name = 'questions/partials/question_form_modal.html'
    list_template_name = 'questions/partials/question_list.html'

    def get_question(self, request, pk):
        user = request.user
        is_staff_admin = (
            user.is_superuser or
            getattr(user, 'is_admin', False) or
            user.role in [Role.ADMIN, Role.PLATFORM_ADMIN, Role.DATA_ADMIN, Role.KURIKULUM]
        )
        if is_staff_admin:
            return get_object_or_404(Question, pk=pk)
        
        teacher = get_current_teacher(user)
        if teacher:
            assigned_subject_ids = TeacherAssignment.objects.filter(teacher=teacher).values_list('subject_id', flat=True)
            return get_object_or_404(
                Question.objects.filter(
                    Q(created_by=teacher) | Q(subject_id__in=assigned_subject_ids)
                ),
                pk=pk
            )
        return get_object_or_404(Question, pk=pk, created_by__user=user)

    def get(self, request, pk, *args, **kwargs):
        question = self.get_question(request, pk)
        user = request.user
        teacher = get_current_teacher(user)
        is_staff_admin = (
            user.is_superuser or
            getattr(user, 'is_admin', False) or
            user.role in [Role.ADMIN, Role.PLATFORM_ADMIN, Role.DATA_ADMIN, Role.KURIKULUM]
        )

        if is_staff_admin:
            subjects = Subject.objects.all().order_by('name')
            all_teachers = Teacher.objects.prefetch_related('assignments__class_room', 'assignments__subject').all().order_by('full_name')
            teachers_data = get_teachers_subject_mapping(all_teachers)
            subjects_data = get_subjects_level_mapping(subjects)
        else:
            if teacher:
                assigned_subj_ids = TeacherAssignment.objects.filter(
                    teacher=teacher
                ).values_list('subject_id', flat=True)
                subjects = Subject.objects.filter(
                    Q(id__in=assigned_subj_ids) | Q(questions__created_by=teacher)
                ).distinct().order_by('name')
                if not subjects.exists():
                    subjects = Subject.objects.all().order_by('name')
                all_teachers = Teacher.objects.filter(id=teacher.id)
                teachers_data = get_teachers_subject_mapping(all_teachers)
                subjects_data = get_subjects_level_mapping(subjects, teacher=teacher)
            else:
                subjects = Subject.objects.all().order_by('name')
                all_teachers = Teacher.objects.none()
                teachers_data = []
                subjects_data = get_subjects_level_mapping(subjects)

        curr_subject = str(question.subject_id) if question.subject_id else ''
        curr_level = question.level

        if curr_subject and is_staff_admin:
            filtered_teachers = []
            for t in all_teachers:
                t_assignments = t.assignments.filter(subject_id=curr_subject)
                if curr_level:
                    t_assignments = t_assignments.filter(class_room__level=curr_level)
                if t_assignments.exists():
                    filtered_teachers.append(t)
            teachers = filtered_teachers if filtered_teachers else all_teachers
            if question.created_by and question.created_by not in teachers:
                teachers.insert(0, question.created_by)
        else:
            teachers = all_teachers if is_staff_admin else (Teacher.objects.filter(id=teacher.id) if teacher else Teacher.objects.none())

        if not is_staff_admin and teacher:
            teacher_levels = sorted(list(TeacherAssignment.objects.filter(
                teacher=teacher, class_room__isnull=False
            ).values_list('class_room__level', flat=True).distinct()))
            levels = teacher_levels if teacher_levels else [10, 11, 12]
        else:
            levels = [10, 11, 12]

        context = {
            'question': question,
            'subjects': subjects,
            'subjects_json': json.dumps(subjects_data),
            'teachers': teachers,
            'teachers_json': json.dumps(teachers_data),
            'levels': levels,
            'cp_choices': Question.CP_CHOICES,
            'preselected_subject': curr_subject,
            'preselected_level': str(question.level) if question.level else '',
            'preselected_teacher': str(question.created_by.id) if question.created_by else '',
            'is_staff_admin': is_staff_admin,
            'current_teacher': teacher,
            'is_edit': True,
        }
        return render(request, self.modal_template_name, context)

    def post(self, request, pk, *args, **kwargs):
        question = self.get_question(request, pk)
        user = request.user
        teacher = get_current_teacher(user)
        is_staff_admin = (
            user.is_superuser or
            getattr(user, 'is_admin', False) or
            user.role in [Role.ADMIN, Role.PLATFORM_ADMIN, Role.DATA_ADMIN, Role.KURIKULUM]
        )

        form = QuestionForm(request.POST, request.FILES, instance=question)
        if form.is_valid():
            updated_question = form.save(commit=False)
            if not is_staff_admin and teacher:
                updated_question.created_by = teacher
            updated_question.save()

            if request.headers.get('HX-Request') or request.POST.get('is_htmx'):
                response = _render_question_list_partial(request, toast_message='Butir soal berhasil diperbarui.')
                response['HX-Trigger'] = json.dumps({'questionSaved': True, 'closeModal': True})
                return response

            messages.success(request, "Butir soal berhasil diperbarui.")
            return redirect('questions:bank_soal')

        subjects = Subject.objects.all().order_by('name')
        all_teachers = Teacher.objects.prefetch_related('assignments__class_room', 'assignments__subject').all().order_by('full_name')
        teachers_data = get_teachers_subject_mapping(all_teachers) if is_staff_admin else []
        teachers = all_teachers if is_staff_admin else (Teacher.objects.filter(id=teacher.id) if teacher else Teacher.objects.none())
        subjects_data = get_subjects_level_mapping(subjects, teacher=teacher if not is_staff_admin else None)

        if not is_staff_admin and teacher:
            teacher_levels = sorted(list(TeacherAssignment.objects.filter(
                teacher=teacher, class_room__isnull=False
            ).values_list('class_room__level', flat=True).distinct()))
            levels = teacher_levels if teacher_levels else [10, 11, 12]
        else:
            levels = [10, 11, 12]

        context = {
            'question': question,
            'form': form,
            'errors': form.errors,
            'subjects': subjects,
            'subjects_json': json.dumps(subjects_data),
            'teachers': teachers,
            'teachers_json': json.dumps(teachers_data),
            'levels': levels,
            'cp_choices': Question.CP_CHOICES,
            'is_staff_admin': is_staff_admin,
            'current_teacher': teacher,
            'is_edit': True,
        }
        return render(request, self.modal_template_name, context, status=400)


@method_decorator(teacher_required, name='dispatch')
class QuestionDeleteView(View):
    """
    View for deleting a question via HTMX confirmation modal or action.
    """
    modal_template_name = 'questions/partials/question_delete_modal.html'
    list_template_name = 'questions/partials/question_list.html'

    def get_question(self, request, pk):
        user = request.user
        is_staff_admin = (
            user.is_superuser or
            getattr(user, 'is_admin', False) or
            user.role in [Role.ADMIN, Role.PLATFORM_ADMIN, Role.DATA_ADMIN, Role.KURIKULUM]
        )
        if is_staff_admin:
            return get_object_or_404(Question, pk=pk)
        
        teacher = get_current_teacher(user)
        if teacher:
            assigned_subject_ids = TeacherAssignment.objects.filter(teacher=teacher).values_list('subject_id', flat=True)
            return get_object_or_404(
                Question.objects.filter(
                    Q(created_by=teacher) | Q(subject_id__in=assigned_subject_ids)
                ),
                pk=pk
            )
        return get_object_or_404(Question, pk=pk, created_by__user=user)

    def get(self, request, pk, *args, **kwargs):
        question = self.get_question(request, pk)
        return render(request, self.modal_template_name, {'question': question})

    def post(self, request, pk, *args, **kwargs):
        question = self.get_question(request, pk)
        user = request.user
        teacher = get_current_teacher(user)
        is_staff_admin = (
            user.is_superuser or
            getattr(user, 'is_admin', False) or
            user.role in [Role.ADMIN, Role.PLATFORM_ADMIN, Role.DATA_ADMIN, Role.KURIKULUM]
        )

        # Cleanup image files from disk
        images = [
            question.question_image,
            question.image_a,
            question.image_b,
            question.image_c,
            question.image_d,
            question.image_e,
        ]
        for img in images:
            if img:
                try:
                    img.delete(save=False)
                except Exception:
                    pass

        question.delete()

        if request.headers.get('HX-Request') or request.POST.get('is_htmx'):
            response = _render_question_list_partial(request, toast_message='Butir soal berhasil dihapus.')
            response['HX-Trigger'] = json.dumps({'questionDeleted': True, 'closeModal': True})
            return response

        messages.success(request, "Butir soal berhasil dihapus.")
        return redirect('questions:bank_soal')

    def delete(self, request, pk, *args, **kwargs):
        return self.post(request, pk, *args, **kwargs)


@method_decorator(teacher_required, name='dispatch')
class QuestionDetailView(View):
    """
    View to preview question details and full options A-E with correct answer highlighted.
    """
    template_name = 'questions/partials/question_detail_modal.html'

    def get(self, request, pk, *args, **kwargs):
        user = request.user
        is_staff_admin = (
            user.is_superuser or
            getattr(user, 'is_admin', False) or
            user.role in [Role.ADMIN, Role.PLATFORM_ADMIN, Role.DATA_ADMIN, Role.KURIKULUM]
        )
        if is_staff_admin:
            question = get_object_or_404(Question, pk=pk)
        else:
            teacher = get_current_teacher(user)
            if teacher:
                assigned_subject_ids = TeacherAssignment.objects.filter(teacher=teacher).values_list('subject_id', flat=True)
                question = get_object_or_404(
                    Question.objects.filter(
                        Q(created_by=teacher) | Q(subject_id__in=assigned_subject_ids)
                    ),
                    pk=pk
                )
            else:
                question = get_object_or_404(Question, pk=pk, created_by__user=user)

        context = {
            'question': question,
            'options': question.get_options(),
            'is_staff_admin': is_staff_admin,
        }
        return render(request, self.template_name, context)

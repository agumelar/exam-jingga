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
    q = request.GET.get('q', '').strip() or request.POST.get('filter_q', '').strip()

    if subject_id:
        qs = qs.filter(subject_id=subject_id)
    if level and level.isdigit():
        qs = qs.filter(level=int(level))
    if teacher_id and is_staff_admin:
        qs = qs.filter(created_by_id=teacher_id)
    if q:
        qs = qs.filter(
            Q(question_text__icontains=q) |
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
    """Returns a list of dicts with teacher id, name, and assigned subject_ids."""
    if teachers_qs is None:
        teachers_qs = Teacher.objects.prefetch_related('assignments').all().order_by('full_name')
    else:
        teachers_qs = teachers_qs.prefetch_related('assignments')

    teachers_data = []
    for t in teachers_qs:
        subj_ids = list(
            t.assignments.filter(subject__isnull=False).values_list('subject_id', flat=True).distinct()
        )
        teachers_data.append({
            'id': str(t.id),
            'name': t.full_name,
            'subject_ids': [str(s) for s in subj_ids],
        })
    return teachers_data


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

        # Build list of available subjects and teachers mapping
        teachers_data = []
        if is_staff_admin:
            subjects = Subject.objects.all().order_by('name')
            all_teachers = Teacher.objects.prefetch_related('assignments').all().order_by('full_name')
            teachers_data = get_teachers_subject_mapping(all_teachers)
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
                teachers_data = [{
                    'id': str(teacher.id),
                    'name': teacher.full_name,
                    'subject_ids': [str(s) for s in assigned_subj_ids]
                }]
            else:
                subjects = Subject.objects.all().order_by('name')
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
            'teachers': teachers,
            'teachers_json': json.dumps(teachers_data),
            'levels': [10, 11, 12],
            'selected_subject': selected_subject,
            'selected_level': selected_level,
            'selected_teacher': selected_teacher,
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
        user = request.user
        teacher = get_current_teacher(user)
        is_staff_admin = (
            user.is_superuser or
            getattr(user, 'is_admin', False) or
            user.role in [Role.ADMIN, Role.PLATFORM_ADMIN, Role.DATA_ADMIN, Role.KURIKULUM]
        )
        questions_qs = get_scoped_questions_queryset(request)
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
            'page_obj': page_obj,
            'questions': page_obj.object_list,
            'questions_count': filtered_count,
            'selected_subject': request.GET.get('subject_id', '').strip(),
            'selected_level': request.GET.get('level', '').strip(),
            'selected_teacher': request.GET.get('teacher_id', '').strip(),
            'search_query': request.GET.get('q', '').strip(),
            'is_staff_admin': is_staff_admin,
            'current_teacher': teacher,
        }
        return render(request, self.partial_template_name, context)


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

        subjects = Subject.objects.all().order_by('name')
        all_teachers = Teacher.objects.prefetch_related('assignments').all().order_by('full_name')
        teachers_data = get_teachers_subject_mapping(all_teachers) if is_staff_admin else []

        preselected_subject = request.GET.get('subject_id', '').strip()
        preselected_level = request.GET.get('level', '').strip()
        preselected_teacher = request.GET.get('teacher_id', '').strip() or (str(teacher.id) if teacher else '')

        if preselected_subject and is_staff_admin:
            teachers = [
                t for t in all_teachers 
                if any(str(s) == preselected_subject for s in t.assignments.filter(subject__isnull=False).values_list('subject_id', flat=True))
            ]
        else:
            teachers = all_teachers if is_staff_admin else (Teacher.objects.filter(id=teacher.id) if teacher else Teacher.objects.none())

        context = {
            'question': None,
            'subjects': subjects,
            'teachers': teachers,
            'teachers_json': json.dumps(teachers_data),
            'levels': [10, 11, 12],
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
                questions_qs = get_scoped_questions_queryset(request)
                context = {
                    'questions': questions_qs,
                    'questions_count': questions_qs.count(),
                    'is_staff_admin': is_staff_admin,
                    'current_teacher': teacher,
                    'toast_message': 'Butir soal berhasil ditambahkan ke bank soal.',
                }
                response = render(request, self.list_template_name, context)
                response['HX-Trigger'] = json.dumps({'questionSaved': True, 'closeModal': True})
                return response

            messages.success(request, "Butir soal berhasil ditambahkan ke bank soal.")
            return redirect('questions:bank_soal')

        # Form errors handling
        subjects = Subject.objects.all().order_by('name')
        all_teachers = Teacher.objects.prefetch_related('assignments').all().order_by('full_name')
        teachers_data = get_teachers_subject_mapping(all_teachers) if is_staff_admin else []
        teachers = all_teachers if is_staff_admin else (Teacher.objects.filter(id=teacher.id) if teacher else Teacher.objects.none())

        context = {
            'question': None,
            'form': form,
            'errors': form.errors,
            'subjects': subjects,
            'teachers': teachers,
            'teachers_json': json.dumps(teachers_data),
            'levels': [10, 11, 12],
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

        subjects = Subject.objects.all().order_by('name')
        all_teachers = Teacher.objects.prefetch_related('assignments').all().order_by('full_name')
        teachers_data = get_teachers_subject_mapping(all_teachers) if is_staff_admin else []

        curr_subject = str(question.subject_id) if question.subject_id else ''
        if curr_subject and is_staff_admin:
            teachers = [
                t for t in all_teachers 
                if any(str(s) == curr_subject for s in t.assignments.filter(subject__isnull=False).values_list('subject_id', flat=True))
            ]
            if question.created_by and question.created_by not in teachers:
                teachers.insert(0, question.created_by)
        else:
            teachers = all_teachers if is_staff_admin else (Teacher.objects.filter(id=teacher.id) if teacher else Teacher.objects.none())

        context = {
            'question': question,
            'subjects': subjects,
            'teachers': teachers,
            'teachers_json': json.dumps(teachers_data),
            'levels': [10, 11, 12],
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
                questions_qs = get_scoped_questions_queryset(request)
                context = {
                    'questions': questions_qs,
                    'questions_count': questions_qs.count(),
                    'is_staff_admin': is_staff_admin,
                    'current_teacher': teacher,
                    'toast_message': 'Butir soal berhasil diperbarui.',
                }
                response = render(request, self.list_template_name, context)
                response['HX-Trigger'] = json.dumps({'questionSaved': True, 'closeModal': True})
                return response

            messages.success(request, "Butir soal berhasil diperbarui.")
            return redirect('questions:bank_soal')

        subjects = Subject.objects.all().order_by('name')
        all_teachers = Teacher.objects.prefetch_related('assignments').all().order_by('full_name')
        teachers_data = get_teachers_subject_mapping(all_teachers) if is_staff_admin else []
        teachers = all_teachers if is_staff_admin else (Teacher.objects.filter(id=teacher.id) if teacher else Teacher.objects.none())

        context = {
            'question': question,
            'form': form,
            'errors': form.errors,
            'subjects': subjects,
            'teachers': teachers,
            'teachers_json': json.dumps(teachers_data),
            'levels': [10, 11, 12],
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
            questions_qs = get_scoped_questions_queryset(request)
            context = {
                'questions': questions_qs,
                'questions_count': questions_qs.count(),
                'is_staff_admin': is_staff_admin,
                'current_teacher': teacher,
                'toast_message': 'Butir soal berhasil dihapus.',
            }
            response = render(request, self.list_template_name, context)
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

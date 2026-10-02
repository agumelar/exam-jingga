from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import render, redirect
from django.views.generic import TemplateView
from django.utils import timezone
from .models import SchoolSetting

from apps.master_data.models import Student, Teacher, ClassRoom, Major
from apps.questions.models import Question
from apps.schedules.models import Schedule, Exam
from apps.exam_engine.models import ExamSession


class DashboardView(LoginRequiredMixin, TemplateView):
    template_name = 'core/dashboard.html'
    login_url = '/accounts/login/'

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()
        if getattr(request.user, 'is_student', False) or getattr(request.user, 'role', '') == 'siswa':
            return redirect('/student/dashboard/')
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user

        # Page metadata
        context['page_title'] = 'Dashboard'
        context['page_subtitle'] = 'Pusat Kontrol & Ringkasan Aktivitas Ujian'
        context['active_menu'] = 'dashboard'
        context['heading'] = 'Dashboard CBT'
        context['subheading'] = 'Selamat datang di Panel Kontrol Exam Jingga'
        context['settings'] = SchoolSetting.get_settings()

        # 1. Master Data Stats
        total_students = Student.objects.count()
        total_teachers = Teacher.objects.count()
        total_classes = ClassRoom.objects.count()
        total_majors = Major.objects.count()

        # 2. Question Bank Stats
        total_questions = Question.objects.count()
        total_exams = Exam.objects.count()

        # 3. Schedule & Session Stats
        active_schedules_qs = Schedule.objects.filter(status='active').select_related('exam', 'class_room', 'teacher')
        active_schedules_count = active_schedules_qs.count()
        total_schedules_count = Schedule.objects.count()

        active_sessions_count = ExamSession.objects.filter(status='active').count()
        finished_sessions_count = ExamSession.objects.filter(status='finished').count()
        locked_sessions_count = ExamSession.objects.filter(status='locked').count()
        total_sessions_count = ExamSession.objects.count()

        # 4. Recent Active Schedules List
        recent_schedules = Schedule.objects.select_related('exam', 'class_room', 'teacher').order_by('-start_time')[:5]

        # 5. Recent Student Activity
        recent_sessions = ExamSession.objects.select_related('student', 'schedule__exam', 'student__class_room').order_by('-started_at')[:6]

        context.update({
            'total_students': total_students,
            'total_teachers': total_teachers,
            'total_classes': total_classes,
            'total_majors': total_majors,
            'total_questions': total_questions,
            'total_exams': total_exams,
            'active_schedules_count': active_schedules_count,
            'total_schedules_count': total_schedules_count,
            'active_sessions_count': active_sessions_count,
            'finished_sessions_count': finished_sessions_count,
            'locked_sessions_count': locked_sessions_count,
            'total_sessions_count': total_sessions_count,
            'recent_schedules': recent_schedules,
            'recent_sessions': recent_sessions,
        })

        return context


def custom_404_view(request, exception=None):
    """Custom Material Design 3 404 Not Found error handler."""
    return render(request, '404.html', status=404)


def custom_500_view(request):
    """Custom Material Design 3 500 Internal Server Error handler."""
    return render(request, '500.html', status=500)


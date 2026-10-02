import json
import uuid
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
from django.db.models import Q, Avg, Max, Min, Count
from django.http import HttpResponse, JsonResponse, HttpResponseForbidden
from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone
from django.views import View
from django.views.decorators.http import require_POST

from apps.accounts.models import Role
from apps.core.models import SchoolSetting
from apps.master_data.models import Student, ClassRoom, Major, Subject, Teacher, TeacherAssignment
from apps.schedules.models import Exam, Schedule, ExamQuestion
from apps.exam_engine.models import ExamSession, StudentAnswer
from apps.exam_engine.utils import grade_exam_session
from apps.reports.models import StudentLogistic
from apps.reports.utils import (
    get_exam_related_schedules,
    get_student_best_session_map,
    calculate_distractor_analysis,
    auto_distribute_logistics,
    generate_exam_results_excel,
    generate_logistics_excel
)


def get_user_role(user):
    """Helper to resolve user role safely."""
    if not user.is_authenticated:
        return ''
    if hasattr(user, 'role') and user.role:
        return str(user.role).lower()
    if user.is_superuser:
        return 'admin'
    return ''


def is_staff_or_admin(user):
    """Check if user has administrative or teaching privileges."""
    if not user.is_authenticated:
        return False
    if user.is_superuser:
        return True
    role = get_user_role(user)
    return role in ['admin', 'kurikulum', 'guru', 'pengawas']


# ==============================================================================
# 1. LIVE MONITORING & SESSION MANAGEMENT
# ==============================================================================

class SessionMonitoringView(View):
    """
    Pusat Kendali Monitoring Ujian Real-Time.
    Memantau kehadiran dan status siswa yang sedang mengerjakan ujian.
    """
    def get(self, request, *args, **kwargs):
        if not is_staff_or_admin(request.user):
            return redirect('accounts:login')

        user_role = get_user_role(request.user)
        schedules = Schedule.objects.select_related('exam', 'class_room', 'teacher', 'exam__subject').order_by('-start_time')
        
        # Scoping jika guru
        if user_role == 'guru' and hasattr(request.user, 'teacher_profile') and request.user.teacher_profile:
            teacher = request.user.teacher_profile
            schedules = schedules.filter(Q(teacher=teacher) | Q(exam__teacher=teacher))

        selected_schedule_id = kwargs.get('schedule_id') or request.GET.get('schedule_id', '') or request.GET.get('schedule', '')
        selected_schedule = None
        if selected_schedule_id:
            selected_schedule_id = str(selected_schedule_id).strip()
            try:
                selected_schedule = schedules.filter(id=selected_schedule_id).first()
            except Exception:
                selected_schedule = None
        if not selected_schedule and schedules.exists():
            selected_schedule = schedules.first()
            selected_schedule_id = str(selected_schedule.id)

        # Filters
        class_id = request.GET.get('class_id', '')
        room_name = request.GET.get('room_name', '')
        status_filter = request.GET.get('status', 'all')
        search_query = request.GET.get('q', '').strip()

        # Ambil data siswa & sesi
        data = self._get_monitoring_data(
            selected_schedule=selected_schedule,
            class_id=class_id,
            room_name=room_name,
            status_filter=status_filter,
            search_query=search_query,
            user=request.user
        )

        all_classes = ClassRoom.objects.all().order_by('name')
        all_rooms = list(StudentLogistic.objects.values_list('room_name', flat=True).distinct().order_by('room_name'))
        if not all_rooms:
            all_rooms = list(Schedule.objects.exclude(room_name__isnull=True).exclude(room_name='').values_list('room_name', flat=True).distinct().order_by('room_name'))

        context = {
            'active_menu': 'sesi',
            'page_title': 'Session Monitoring',
            'page_subtitle': 'Real-time CBT Exam Control Center',
            'schedules': schedules,
            'selected_schedule': selected_schedule,
            'selected_schedule_id': selected_schedule_id,
            'classes': all_classes,
            'rooms': all_rooms,
            'filter_class_id': class_id,
            'filter_room_name': room_name,
            'filter_status': status_filter,
            'search_query': search_query,
            'user_role': user_role,
            **data
        }

        # If HTMX request, render only table partial
        if request.headers.get('HX-Request') and not request.headers.get('HX-Boosted'):
            return render(request, 'reports/partials/monitoring_table.html', context)

        return render(request, 'reports/session_management.html', context)

    def _get_monitoring_data(self, selected_schedule, class_id, room_name, status_filter, search_query, user):
        if not selected_schedule:
            return {
                'participants': [],
                'total_count': 0,
                'active_count': 0,
                'locked_count': 0,
                'finished_count': 0,
                'not_started_count': 0,
            }

        exam = selected_schedule.exam
        related_sch_ids = list(exam.schedules.values_list('id', flat=True)) if exam else [selected_schedule.id]

        # Scope siswa target
        students_qs = Student.objects.filter(status='aktif').select_related('class_room', 'major')
        if exam and exam.exam_type in ['UH', 'PTS'] and selected_schedule.class_room:
            students_qs = students_qs.filter(class_room=selected_schedule.class_room)
        elif exam and exam.level:
            students_qs = students_qs.filter(class_room__level=exam.level)

        if class_id:
            students_qs = students_qs.filter(class_room_id=class_id)

        if search_query:
            students_qs = students_qs.filter(
                Q(full_name__icontains=search_query) | Q(nis__icontains=search_query)
            )

        students = list(students_qs.order_by('full_name'))
        student_ids = [s.id for s in students]

        # Ambil logistik ruangan
        logistics_map = {
            str(l.student_id): l for l in StudentLogistic.objects.filter(student_id__in=student_ids)
        }

        # Filter by room
        if room_name and room_name != 'all':
            students = [s for s in students if logistics_map.get(str(s.id)) and logistics_map[str(s.id)].room_name == room_name]

        # Tarik sesi ujian terkait
        sessions_qs = ExamSession.objects.filter(
            schedule_id__in=related_sch_ids,
            student_id__in=student_ids
        ).select_related('student', 'schedule').order_by('-started_at')

        session_map = {}
        for s in sessions_qs:
            sid = str(s.student_id)
            if sid not in session_map:
                session_map[sid] = s
            else:
                curr = session_map[sid]
                if s.status == 'finished' and curr.status != 'finished':
                    session_map[sid] = s
                elif s.status == 'locked' and curr.status == 'active':
                    session_map[sid] = s

        # Build participant list with live stats
        participants = []
        active_cnt = 0
        locked_cnt = 0
        finished_cnt = 0
        not_started_cnt = 0

        for s in students:
            sid = str(s.id)
            session = session_map.get(sid)
            logistic = logistics_map.get(sid)

            if not session:
                status = 'not_started'
                status_label = 'Belum Mulai'
                status_badge = 'bg-stone-100 text-stone-600 dark:bg-stone-800 dark:text-stone-400'
                not_started_cnt += 1
            elif session.status == 'active':
                status = 'active'
                status_label = 'Mengerjakan'
                status_badge = 'bg-blue-100 text-blue-700 dark:bg-blue-950/40 dark:text-blue-400 font-bold'
                active_cnt += 1
            elif session.status == 'locked':
                status = 'locked'
                status_label = 'Terkunci'
                status_badge = 'bg-red-100 text-red-700 dark:bg-red-950/40 dark:text-red-400 font-bold'
                locked_cnt += 1
            elif session.status == 'finished':
                status = 'finished'
                status_label = 'Selesai'
                status_badge = 'bg-emerald-100 text-emerald-700 dark:bg-emerald-950/40 dark:text-emerald-400 font-bold'
                finished_cnt += 1
            else:
                status = session.status
                status_label = session.status
                status_badge = 'bg-stone-100 text-stone-600'

            item = {
                'student': s,
                'session': session,
                'logistic': logistic,
                'status': status,
                'status_label': status_label,
                'status_badge': status_badge,
                'room_name': logistic.room_name if logistic else (selected_schedule.room_name or '-'),
                'session_name': logistic.session_name if logistic else f"Sesi {selected_schedule.session_no}",
            }

            if status_filter == 'all' or status_filter == status:
                participants.append(item)

        return {
            'participants': participants,
            'total_count': len(students),
            'active_count': active_cnt,
            'locked_count': locked_cnt,
            'finished_count': finished_cnt,
            'not_started_count': not_started_cnt,
        }


class SessionMonitoringTableView(SessionMonitoringView):
    """HTMX Polling endpoint for the live table."""
    def get(self, request, *args, **kwargs):
        if not is_staff_or_admin(request.user):
            return HttpResponseForbidden("Unauthorized")

        user_role = get_user_role(request.user)
        selected_schedule_id = kwargs.get('schedule_id') or request.GET.get('schedule_id', '') or request.GET.get('schedule', '')
        selected_schedule = None
        if selected_schedule_id:
            try:
                selected_schedule = Schedule.objects.select_related('exam', 'class_room').get(id=selected_schedule_id)
            except (Schedule.DoesNotExist, ValueError):
                selected_schedule = None

        class_id = request.GET.get('class_id', '')
        room_name = request.GET.get('room_name', '')
        status_filter = request.GET.get('status', 'all')
        search_query = request.GET.get('q', '').strip()

        data = self._get_monitoring_data(
            selected_schedule=selected_schedule,
            class_id=class_id,
            room_name=room_name,
            status_filter=status_filter,
            search_query=search_query,
            user=request.user
        )

        context = {
            'selected_schedule': selected_schedule,
            'selected_schedule_id': selected_schedule_id,
            'filter_class_id': class_id,
            'filter_room_name': room_name,
            'filter_status': status_filter,
            'search_query': search_query,
            'user_role': user_role,
            **data
        }
        return render(request, 'reports/partials/monitoring_table.html', context)


@require_POST
def session_unlock_action(request, session_id):
    """Buka Kunci Sesi Siswa (Set status active & violation_count 0)."""
    if not is_staff_or_admin(request.user):
        return JsonResponse({'success': False, 'message': 'Akses ditolak'}, status=403)

    session = get_object_or_404(ExamSession, id=session_id)
    session.status = 'active'
    session.violation_count = 0
    session.save(update_fields=['status', 'violation_count'])

    if request.headers.get('HX-Request'):
        response = HttpResponse("OK")
        response['HX-Trigger'] = json.dumps({
            'sessionUpdated': {'sessionId': str(session_id), 'status': 'active'},
            'showToast': {'type': 'success', 'message': f'Sesi {session.student.full_name} berhasil dibuka.'}
        })
        return response

    messages.success(request, f"Sesi {session.student.full_name} berhasil dibuka kembali.")
    return redirect(request.META.get('HTTP_REFERER', '/session-management/'))


@require_POST
def session_reset_action(request, session_id):
    """Reset sesi siswa agar dapat login ulang dari awal."""
    if not is_staff_or_admin(request.user):
        return JsonResponse({'success': False, 'message': 'Akses ditolak'}, status=403)

    session = get_object_or_404(ExamSession, id=session_id)
    student_name = session.student.full_name
    # Delete answers and session to allow fresh start
    session.student_answers.all().delete()
    session.delete()

    if request.headers.get('HX-Request'):
        response = HttpResponse("OK")
        response['HX-Trigger'] = json.dumps({
            'sessionUpdated': {'sessionId': str(session_id), 'status': 'reset'},
            'showToast': {'type': 'success', 'message': f'Sesi {student_name} berhasil di-reset.'}
        })
        return response

    messages.success(request, f"Sesi {student_name} berhasil di-reset.")
    return redirect(request.META.get('HTTP_REFERER', '/session-management/'))


@require_POST
def session_force_submit_action(request, session_id):
    """Paksa selesai sesi siswa & kalkulasi nilai akhir."""
    if not is_staff_or_admin(request.user):
        return JsonResponse({'success': False, 'message': 'Akses ditolak'}, status=403)

    session = get_object_or_404(ExamSession, id=session_id)
    score = grade_exam_session(session)
    session.status = 'finished'
    session.finished_at = timezone.now()
    session.save(update_fields=['status', 'score', 'finished_at'])

    if request.headers.get('HX-Request'):
        response = HttpResponse("OK")
        response['HX-Trigger'] = json.dumps({
            'sessionUpdated': {'sessionId': str(session_id), 'status': 'finished', 'score': score},
            'showToast': {'type': 'success', 'message': f'Sesi {session.student.full_name} dipaksa selesai. Skor: {score}'}
        })
        return response

    messages.success(request, f"Sesi {session.student.full_name} dipaksa selesai dengan nilai {score}.")
    return redirect(request.META.get('HTTP_REFERER', '/session-management/'))


# ==============================================================================
# 2. EXAM RESULTS & RECAPITULATION
# ==============================================================================

class ExamResultsListView(View):
    """Halaman daftar ujian untuk memilih hasil rekapitulasi nilai."""
    def get(self, request):
        if not is_staff_or_admin(request.user):
            return redirect('accounts:login')

        exams = Exam.objects.select_related('subject', 'teacher').prefetch_related('schedules').order_by('-created_at')
        user_role = get_user_role(request.user)

        if user_role == 'guru' and hasattr(request.user, 'teacher_profile') and request.user.teacher_profile:
            teacher = request.user.teacher_profile
            exams = exams.filter(Q(teacher=teacher) | Q(schedules__teacher=teacher)).distinct()

        # If there are exams, redirect to the first one or display selector
        selected_exam_id = request.GET.get('exam_id')
        if selected_exam_id:
            return redirect('reports:exam_results_detail', exam_id=selected_exam_id)

        if exams.exists():
            first_exam = exams.first()
            return redirect('reports:exam_results_detail', exam_id=first_exam.id)

        context = {
            'active_menu': 'hasil_ujian',
            'page_title': 'Hasil Ujian',
            'page_subtitle': 'Rekapitulasi Nilai & Analisis Butir Soal',
            'exams': exams,
        }
        return render(request, 'reports/exam_results.html', context)


class ExamResultsView(View):
    """
    Tampilan Detail Hasil Ujian & Rekapitulasi Nilai per Siswa & Kelas.
    """
    def get(self, request, exam_id):
        if not is_staff_or_admin(request.user):
            return redirect('accounts:login')

        exam = get_object_or_404(Exam.objects.select_related('subject', 'teacher'), id=exam_id)
        user_role = get_user_role(request.user)

        # Scoping kelas
        allowed_class_ids = None
        if user_role == 'guru' and hasattr(request.user, 'teacher_profile') and request.user.teacher_profile:
            teacher = request.user.teacher_profile
            assignments = TeacherAssignment.objects.filter(teacher=teacher, subject=exam.subject)
            allowed_class_ids = list(assignments.values_list('class_room_id', flat=True))

        # Tarik semua jadwal terkait
        related_schedules = exam.schedules.all()
        related_sch_ids = list(related_schedules.values_list('id', flat=True))

        # Tarik siswa
        students_qs = Student.objects.filter(status='aktif').select_related('class_room', 'major')
        if exam.exam_type in ['UH', 'PTS']:
            sch_classes = [s.class_room_id for s in related_schedules if s.class_room_id]
            if sch_classes:
                students_qs = students_qs.filter(class_room_id__in=sch_classes)
        elif exam.level:
            students_qs = students_qs.filter(class_room__level=exam.level)

        if allowed_class_ids is not None:
            students_qs = students_qs.filter(class_room_id__in=allowed_class_ids)

        # Filters
        class_filter = request.GET.get('class_name', 'Semua Kelas')
        search_query = request.GET.get('q', '').strip()

        if class_filter and class_filter != 'Semua Kelas':
            students_qs = students_qs.filter(class_room__name=class_filter)

        if search_query:
            students_qs = students_qs.filter(
                Q(full_name__icontains=search_query) | Q(nis__icontains=search_query)
            )

        students = list(students_qs.order_by('class_room__name', 'full_name'))
        available_classes = list(
            ClassRoom.objects.filter(
                id__in=Student.objects.filter(status='aktif', class_room__level=exam.level if exam.level else None).values_list('class_room_id', flat=True)
            ).values_list('name', flat=True).distinct().order_by('name')
        ) if exam.level else list(ClassRoom.objects.values_list('name', flat=True).distinct().order_by('name'))

        # Map sesi terbaik per siswa
        session_map = get_student_best_session_map(exam, related_sch_ids)

        # Hitung statistik
        participants_data = []
        scores_list = []
        completed_count = 0

        for s in students:
            sid = str(s.id)
            session = session_map.get(sid)
            is_finished = session and session.status == 'finished'
            score = round(session.score, 1) if is_finished else 0.0

            if is_finished:
                completed_count += 1
                scores_list.append(score)

            correct_cnt = session.correct_count if session else 0
            total_ans = session.total_questions_count if session else 0
            wrong_cnt = max(0, total_ans - correct_cnt) if session else 0

            status_label = 'Belum Mulai'
            status_badge = 'bg-stone-100 text-stone-600 dark:bg-stone-800 dark:text-stone-400'
            if session:
                if session.status == 'finished':
                    status_label = 'Selesai'
                    status_badge = 'bg-emerald-100 text-emerald-700 dark:bg-emerald-950/40 dark:text-emerald-400'
                elif session.status == 'locked':
                    status_label = 'Terkunci'
                    status_badge = 'bg-red-100 text-red-700 dark:bg-red-950/40 dark:text-red-400'
                elif session.status == 'active':
                    status_label = 'Mengerjakan'
                    status_badge = 'bg-blue-100 text-blue-700 dark:bg-blue-950/40 dark:text-blue-400'

            participants_data.append({
                'student': s,
                'nis': s.nis,
                'full_name': s.full_name,
                'class_name': s.class_room.name if s.class_room else '-',
                'session': session,
                'is_finished': is_finished,
                'score': score,
                'correct_count': correct_cnt,
                'wrong_count': wrong_cnt,
                'status_label': status_label,
                'status_badge': status_badge,
                'is_passed': score >= 75.0 and is_finished,
            })

        total_students = len(students)
        avg_score = round(sum(scores_list) / len(scores_list), 1) if scores_list else 0.0
        highest_score = max(scores_list) if scores_list else 0.0
        lowest_score = min(scores_list) if scores_list else 0.0
        passed_count = sum(1 for p in participants_data if p['is_passed'])
        pass_rate = round((passed_count / completed_count) * 100, 1) if completed_count > 0 else 0.0

        stats = {
            'avg': avg_score,
            'highest': highest_score,
            'lowest': lowest_score,
            'completed': completed_count,
            'total': total_students,
            'pass_rate': pass_rate,
            'passed_count': passed_count,
        }

        # Analisis butir soal
        analysis = calculate_distractor_analysis(exam, related_sch_ids)

        context = {
            'active_menu': 'hasil_ujian',
            'page_title': f"Hasil Ujian: {exam.title}",
            'page_subtitle': f"{exam.subject.name if exam.subject else 'Umum'} | {exam.exam_type}",
            'exam': exam,
            'participants': participants_data,
            'stats': stats,
            'analysis': analysis['analysis_data'],
            'total_finished': analysis['total_finished'],
            'available_classes': available_classes,
            'selected_class': class_filter,
            'search_query': search_query,
            'active_tab': request.GET.get('tab', 'rekap'),
            'all_exams': Exam.objects.select_related('subject').order_by('-created_at')[:20],
        }
        return render(request, 'reports/exam_results.html', context)


class ExamResultsExportView(View):
    """Download Rekap Hasil Ujian (.xlsx) via openpyxl."""
    def get(self, request, exam_id):
        if not is_staff_or_admin(request.user):
            return HttpResponseForbidden("Unauthorized")

        exam = get_object_or_404(Exam.objects.select_related('subject', 'teacher'), id=exam_id)
        related_sch_ids = list(exam.schedules.values_list('id', flat=True))

        students_qs = Student.objects.filter(status='aktif').select_related('class_room', 'major')
        if exam.exam_type in ['UH', 'PTS']:
            sch_classes = [s.class_room_id for s in exam.schedules.all() if s.class_room_id]
            if sch_classes:
                students_qs = students_qs.filter(class_room_id__in=sch_classes)
        elif exam.level:
            students_qs = students_qs.filter(class_room__level=exam.level)

        students = list(students_qs.order_by('class_room__name', 'full_name'))
        session_map = get_student_best_session_map(exam, related_sch_ids)

        participants_data = []
        for s in students:
            session = session_map.get(str(s.id))
            is_fin = session and session.status == 'finished'
            participants_data.append({
                'nis': s.nis,
                'full_name': s.full_name,
                'class_name': s.class_room.name if s.class_room else '-',
                'status_label': 'Selesai' if is_fin else (session.get_status_display() if session else 'Belum Mulai'),
                'correct_count': session.correct_count if session else 0,
                'wrong_count': max(0, (session.total_questions_count or 0) - (session.correct_count or 0)) if session else 0,
                'score': round(session.score, 1) if is_fin else 0.0,
                'is_finished': is_fin,
            })

        analysis_dict = calculate_distractor_analysis(exam, related_sch_ids)
        return generate_exam_results_excel(exam, participants_data, analysis_dict['analysis_data'])


class DistractorAnalysisView(View):
    """Standalone page / view for Analisis Butir Soal & Sebaran Pengecoh."""
    def get(self, request, exam_id):
        if not is_staff_or_admin(request.user):
            return redirect('accounts:login')

        exam = get_object_or_404(Exam.objects.select_related('subject', 'teacher'), id=exam_id)
        analysis = calculate_distractor_analysis(exam)

        context = {
            'active_menu': 'hasil_ujian',
            'page_title': f"Analisis Butir Soal: {exam.title}",
            'page_subtitle': f"Sebaran Pengecoh & Daya Pembeda Soal CBT",
            'exam': exam,
            'analysis': analysis['analysis_data'],
            'total_finished': analysis['total_finished'],
            'questions_count': analysis['questions_count'],
        }
        return render(request, 'reports/distractor_analysis.html', context)


# ==============================================================================
# 3. PRINTABLE EXAM CARDS & ATTENDANCE LISTS
# ==============================================================================

class ExamCardsView(View):
    """
    Cetak Kartu Peserta Ujian Siswa (Exam Cards).
    Mendukung filter Ruang, Sesi, dan Kelas dengan tata letak cetak A4.
    """
    def get(self, request):
        if not is_staff_or_admin(request.user):
            return redirect('accounts:login')

        settings = SchoolSetting.get_settings()
        filter_room = request.GET.get('room', 'all')
        filter_session = request.GET.get('session', 'all')
        filter_class = request.GET.get('class_id', 'all')

        logistics_qs = StudentLogistic.objects.select_related('student', 'student__class_room', 'student__major').order_by('room_name', 'session_name', 'student__full_name')

        if filter_room != 'all' and filter_room:
            logistics_qs = logistics_qs.filter(room_name=filter_room)
        if filter_session != 'all' and filter_session:
            logistics_qs = logistics_qs.filter(session_name=filter_session)
        if filter_class != 'all' and filter_class:
            logistics_qs = logistics_qs.filter(student__class_room_id=filter_class)

        logistics = list(logistics_qs)
        
        # Fallback jika belum ada student_logistics: buat kartu dari data Student langsung
        if not logistics:
            students_qs = Student.objects.filter(status='aktif').select_related('class_room', 'major').order_by('class_room__name', 'full_name')
            if filter_class != 'all' and filter_class:
                students_qs = students_qs.filter(class_room_id=filter_class)
            
            logistics = [
                StudentLogistic(
                    student=s,
                    room_name="RUANG 01",
                    session_name="SESI 1",
                    exam_period=f"{settings.exam_name} {settings.academic_year}"
                )
                for s in students_qs
            ]

        all_rooms = list(StudentLogistic.objects.values_list('room_name', flat=True).distinct().order_by('room_name'))
        all_sessions = list(StudentLogistic.objects.values_list('session_name', flat=True).distinct().order_by('session_name'))
        all_classes = ClassRoom.objects.all().order_by('name')

        context = {
            'active_menu': 'kartu_peserta',
            'page_title': 'Kartu Peserta Ujian',
            'page_subtitle': f'Tahun Pelajaran {settings.academic_year}',
            'settings': settings,
            'students': logistics,
            'rooms': all_rooms,
            'sessions': all_sessions,
            'classes': all_classes,
            'filter_room': filter_room,
            'filter_session': filter_session,
            'filter_class': filter_class,
            'is_print_mode': request.GET.get('print', 'false') == 'true',
        }
        return render(request, 'reports/exam_cards.html', context)


class AttendanceListView(View):
    """
    Cetak Daftar Hadir Ujian & Berita Acara Pelaksanaan (Attendance List).
    Format 1: Daftar Hadir Pengawas (Tanda Tangan Zig-zag).
    Format 2: Daftar Peserta Ruangan (Tempelan Pintu).
    """
    def get(self, request):
        if not is_staff_or_admin(request.user):
            return redirect('accounts:login')

        settings = SchoolSetting.get_settings()
        filter_room = request.GET.get('room', 'all')
        filter_session = request.GET.get('session', 'all')
        print_type = request.GET.get('type', 'attendance')  # 'attendance' or 'door'

        logistics_qs = StudentLogistic.objects.select_related('student', 'student__class_room', 'student__major').order_by('room_name', 'session_name', 'student__full_name')

        if filter_room != 'all' and filter_room:
            logistics_qs = logistics_qs.filter(room_name=filter_room)
        if filter_session != 'all' and filter_session:
            logistics_qs = logistics_qs.filter(session_name=filter_session)

        logistics = list(logistics_qs)

        # Fallback jika belum ada logistics
        if not logistics:
            students_qs = Student.objects.filter(status='aktif').select_related('class_room', 'major').order_by('full_name')
            logistics = [
                StudentLogistic(
                    student=s,
                    room_name="RUANG 01",
                    session_name="SESI 1",
                    exam_period=f"{settings.exam_name} {settings.academic_year}"
                )
                for s in students_qs[:36]
            ]

        # Grouping by (room_name, session_name)
        groups = {}
        for item in logistics:
            key = f"{item.room_name}_{item.session_name}"
            if key not in groups:
                groups[key] = {
                    'room_name': item.room_name,
                    'session_name': item.session_name,
                    'students': []
                }
            groups[key]['students'].append(item)

        all_rooms = list(StudentLogistic.objects.values_list('room_name', flat=True).distinct().order_by('room_name'))
        all_sessions = list(StudentLogistic.objects.values_list('session_name', flat=True).distinct().order_by('session_name'))

        context = {
            'active_menu': 'daftar_hadir',
            'page_title': 'Daftar Hadir Ujian',
            'page_subtitle': 'Cetak Berita Acara & Daftar Hadir Pengawas Ruang',
            'settings': settings,
            'groups': list(groups.values()),
            'students_count': len(logistics),
            'rooms': all_rooms,
            'sessions': all_sessions,
            'filter_room': filter_room,
            'filter_session': filter_session,
            'print_type': print_type,
            'is_print_mode': request.GET.get('print', 'false') == 'true',
        }
        return render(request, 'reports/attendance_list.html', context)


# ==============================================================================
# 4. LOGISTICS ALLOCATION & MANAGEMENT
# ==============================================================================

class LogisticsView(View):
    """
    Manajemen Penempatan & Alokasi Ruang serta Sesi Siswa.
    Mendukung pengocokan otomatis (auto-shuffle) dan export Excel.
    """
    def get(self, request):
        if not is_staff_or_admin(request.user):
            return redirect('accounts:login')

        total_active_students = Student.objects.filter(status='aktif').count()
        logistics_count = StudentLogistic.objects.count()
        unassigned_count = max(0, total_active_students - logistics_count)

        filter_room = request.GET.get('room', 'all')
        filter_session = request.GET.get('session', 'all')
        search_query = request.GET.get('q', '').strip()

        logistics_qs = StudentLogistic.objects.select_related('student', 'student__class_room', 'student__major').order_by('room_name', 'session_name', 'student__full_name')

        if filter_room != 'all' and filter_room:
            logistics_qs = logistics_qs.filter(room_name=filter_room)
        if filter_session != 'all' and filter_session:
            logistics_qs = logistics_qs.filter(session_name=filter_session)
        if search_query:
            logistics_qs = logistics_qs.filter(
                Q(student__full_name__icontains=search_query) | Q(student__nis__icontains=search_query)
            )

        all_rooms = list(StudentLogistic.objects.values_list('room_name', flat=True).distinct().order_by('room_name'))
        all_sessions = list(StudentLogistic.objects.values_list('session_name', flat=True).distinct().order_by('session_name'))
        classes = ClassRoom.objects.all().order_by('name')

        context = {
            'active_menu': 'sesi',
            'page_title': 'Logistik & Sesi Ruangan',
            'page_subtitle': 'Otomatisasi Penempatan Ruang & Sesi Ujian Siswa',
            'total_active_students': total_active_students,
            'allocated_count': logistics_count,
            'unassigned_count': unassigned_count,
            'logistics': logistics_qs,
            'rooms': all_rooms,
            'sessions': all_sessions,
            'classes': classes,
            'filter_room': filter_room,
            'filter_session': filter_session,
            'search_query': search_query,
        }
        return render(request, 'reports/logistics.html', context)


@require_POST
def logistics_generate_action(request):
    """Endpoint untuk generate dan kocok alokasi ruang & sesi siswa."""
    if not is_staff_or_admin(request.user):
        return JsonResponse({'success': False, 'message': 'Akses ditolak'}, status=403)

    try:
        levels_raw = request.POST.getlist('levels')
        if not levels_raw:
            # Check comma separated or single field
            levels_str = request.POST.get('levels', '')
            levels = [int(x.strip()) for x in levels_str.split(',') if x.strip().isdigit()]
        else:
            levels = [int(x) for x in levels_raw if str(x).isdigit()]

        if not levels:
            levels = [10, 11, 12]

        room_count = int(request.POST.get('room_count', 1))
        capacity = int(request.POST.get('capacity', 36))
        sessions_count = int(request.POST.get('sessions_count', 2))

        settings = SchoolSetting.get_settings()
        exam_period = f"{settings.exam_name} {settings.academic_year}"

        allocated = auto_distribute_logistics(
            levels=levels,
            room_count=room_count,
            capacity=capacity,
            sessions_count=sessions_count,
            exam_period=exam_period
        )

        messages.success(request, f"Berhasil mengalokasikan {allocated} siswa ke dalam {room_count} ruangan dan {sessions_count} sesi.")
        if request.headers.get('HX-Request'):
            response = HttpResponse("OK")
            response['HX-Redirect'] = '/logistics/'
            return response

        return redirect('reports:logistics')
    except Exception as e:
        messages.error(request, f"Gagal mengocok logistik: {str(e)}")
        return redirect('reports:logistics')


class LogisticsExportView(View):
    """Export Excel data alokasi logistik ruangan siswa."""
    def get(self, request):
        if not is_staff_or_admin(request.user):
            return HttpResponseForbidden("Unauthorized")

        filter_room = request.GET.get('room', 'all')
        filter_session = request.GET.get('session', 'all')

        logistics_qs = StudentLogistic.objects.select_related('student', 'student__class_room').order_by('room_name', 'session_name', 'student__full_name')

        if filter_room != 'all' and filter_room:
            logistics_qs = logistics_qs.filter(room_name=filter_room)
        if filter_session != 'all' and filter_session:
            logistics_qs = logistics_qs.filter(session_name=filter_session)

        return generate_logistics_excel(logistics_qs)


# ==============================================================================
# 5. INSTITUTIONAL SETTINGS MANAGEMENT
# ==============================================================================

class SettingsView(View):
    """
    Pengaturan Lembaga, Identitas Sekolah, Pejabat TTD, dan Kop Surat.
    Sesuai 100% dengan Settings.jsx.
    """
    def get(self, request):
        if not is_staff_or_admin(request.user):
            return redirect('accounts:login')

        settings = SchoolSetting.get_settings()
        context = {
            'active_menu': 'pengaturan',
            'page_title': 'Pengaturan Sistem',
            'page_subtitle': 'Konfigurasi Identitas Sekolah & Kop Surat Titimangsa',
            'settings': settings,
        }
        return render(request, 'reports/settings.html', context)

    def post(self, request):
        if not is_staff_or_admin(request.user):
            return HttpResponseForbidden("Unauthorized")

        settings = SchoolSetting.get_settings()

        # Kop Surat
        settings.header_1 = request.POST.get('header_1', settings.header_1).strip()
        settings.header_2 = request.POST.get('header_2', settings.header_2).strip()
        settings.header_3 = request.POST.get('header_3', settings.header_3).strip()

        # Identitas Dasar
        settings.school_name = request.POST.get('school_name', settings.school_name).strip()
        settings.school_majors_list = request.POST.get('school_majors_list', settings.school_majors_list).strip()
        settings.school_address = request.POST.get('school_address', settings.school_address).strip()
        settings.school_phone = request.POST.get('school_phone', settings.school_phone).strip()
        settings.school_postal_code = request.POST.get('school_postal_code', settings.school_postal_code).strip()
        settings.school_website = request.POST.get('school_website', settings.school_website).strip()
        settings.school_email = request.POST.get('school_email', settings.school_email).strip()

        # Pejabat TTD
        settings.headmaster_name = request.POST.get('headmaster_name', settings.headmaster_name).strip()
        settings.headmaster_nip = request.POST.get('headmaster_nip', settings.headmaster_nip).strip()
        settings.curriculum_vicedir_name = request.POST.get('curriculum_vicedir_name', settings.curriculum_vicedir_name).strip()
        settings.curriculum_vicedir_nip = request.POST.get('curriculum_vicedir_nip', settings.curriculum_vicedir_nip).strip()
        settings.committee_chairman = request.POST.get('committee_chairman', settings.committee_chairman).strip()

        # Titimangsa & Pelaksanaan
        settings.exam_city = request.POST.get('exam_city', settings.exam_city).strip()
        settings.exam_date = request.POST.get('exam_date', settings.exam_date).strip()
        settings.academic_year = request.POST.get('academic_year', settings.academic_year).strip()
        settings.semester = request.POST.get('semester', settings.semester).strip()
        settings.exam_name = request.POST.get('exam_name', settings.exam_name).strip()

        # Direct URL Fields
        for url_field in ['logo_left_url', 'logo_right_url', 'watermark_url', 'school_seal_url', 'headmaster_signature_url', 'curriculum_signature_url']:
            val = request.POST.get(url_field)
            if val is not None:
                setattr(settings, url_field, val.strip())

        # Handle File Uploads (Assets)
        for file_field in ['file_logo_left', 'file_logo_right', 'file_watermark', 'file_seal', 'file_sig_headmaster', 'file_sig_curriculum']:
            if file_field in request.FILES:
                uploaded_file = request.FILES[file_field]
                filename = f"settings/{file_field}_{uuid.uuid4().hex[:8]}_{uploaded_file.name}"
                saved_path = default_storage.save(filename, ContentFile(uploaded_file.read()))
                media_url = default_storage.url(saved_path)

                target_field_map = {
                    'file_logo_left': 'logo_left_url',
                    'file_logo_right': 'logo_right_url',
                    'file_watermark': 'watermark_url',
                    'file_seal': 'school_seal_url',
                    'file_sig_headmaster': 'headmaster_signature_url',
                    'file_sig_curriculum': 'curriculum_signature_url'
                }
                setattr(settings, target_field_map[file_field], media_url)

        settings.save()
        messages.success(request, "Semua pengaturan identitas sekolah & titimangsa berhasil disimpan!")

        if request.headers.get('HX-Request'):
            response = HttpResponse("OK")
            response['HX-Trigger'] = json.dumps({
                'showToast': {'type': 'success', 'message': 'Semua pengaturan berhasil disimpan!'}
            })
            return response

        return redirect('reports:settings')

"""Views and HTMX Endpoints for Core CBT Exam Engine."""
import logging
import uuid

from django.contrib import messages
from django.db import transaction
from django.db.models import F
from django.http import Http404, HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.template.loader import render_to_string
from django.template.response import TemplateResponse
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.cache import never_cache

from apps.accounts.models import Role
from apps.master_data.models import Student
from apps.schedules.models import Schedule
from apps.exam_engine.eligibility import COLLABORATIVE_TYPES, eligible_schedules_for, student_block_reason
from apps.exam_engine.models import ExamSession, StudentAnswer
from apps.exam_engine.utils import (
    finalize_if_time_up,
    get_question_payload,
    get_session_questions_payload,
    grade_exam_session,
    initialize_session_answers,
)

logger = logging.getLogger(__name__)

DASHBOARD_URL = '/student/dashboard/'
FINISH_GRACE_SECONDS = 10


def get_current_student(request):
    """Profil Student milik akun siswa yang sedang login, atau None untuk akun non-siswa."""
    user = request.user
    if not user.is_authenticated or getattr(user, 'role', '') != Role.SISWA:
        return None
    student = getattr(user, 'student_profile', None)
    if not student:
        student = Student.objects.filter(user=user).first()
    if not student and getattr(user, 'nis', None):
        student = Student.objects.filter(nis=user.nis).first()
    return student


def get_owned_session(request, session_id, for_update=False):
    """Sesi ujian milik siswa yang login. Sesi siswa lain (atau akun non-siswa) dianggap tidak ada."""
    student = get_current_student(request)
    if student is None:
        raise Http404
    qs = ExamSession.objects.select_related(
        'student', 'schedule', 'schedule__exam', 'schedule__exam__subject', 'schedule__teacher'
    )
    if for_update:
        qs = qs.select_for_update()
    return get_object_or_404(qs, id=session_id, student=student)


def _hx_redirect(url):
    response = HttpResponse(status=200)
    response['HX-Redirect'] = url
    return response


def _gate_message(text, tone='error'):
    palette = (
        'bg-red-50 dark:bg-red-950/40 text-red-800 dark:text-red-200 border-red-300 dark:border-red-800'
        if tone == 'error' else
        'bg-amber-50 dark:bg-amber-950/40 text-amber-900 dark:text-amber-100 border-amber-300 dark:border-amber-800'
    )
    return HttpResponse(f'<div class="p-3 rounded-xl text-sm font-semibold border {palette}" role="alert">{text}</div>')


@method_decorator(never_cache, name='dispatch')
class StudentDashboardView(View):
    """Dashboard siswa: jadwal yang boleh dikerjakan, status sesi, dan riwayat nilai."""

    def get(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect(f"/auth/login/?next={request.get_full_path()}")

        student = get_current_student(request)
        block_reason = student_block_reason(student)
        eligible = eligible_schedules_for(student) if not block_reason else []

        sessions_by_schedule = {}
        if student:
            for sess in ExamSession.objects.filter(student=student):
                sessions_by_schedule[sess.schedule_id] = sess

        now = timezone.now()
        available_exams = []
        for sch in eligible:
            sess = sessions_by_schedule.get(sch.id)
            if sess and sess.status == 'finished':
                continue
            available_exams.append({
                'schedule': sch,
                'student_status': sess.status if sess else 'not_started',
                'score': sess.score if sess else None,
                'session_id': sess.id if sess else None,
                'is_time_ended': bool(sch.end_time and now > sch.end_time),
                'is_not_started': bool(sch.start_time and now < sch.start_time),
            })

        exam_history = []
        if student:
            for fs in (
                ExamSession.objects.filter(student=student, status='finished')
                .select_related('schedule', 'schedule__exam', 'schedule__exam__subject')
                .order_by('-finished_at', '-started_at')
            ):
                exam_history.append({
                    'schedule': fs.schedule,
                    'student_status': 'finished',
                    'score': fs.score,
                    'session_id': fs.id,
                    'finished_at': fs.finished_at,
                })

        # Ruang dan sesi siswa berasal dari alokasi logistik (yang juga tercetak di kartu)
        from apps.reports.models import StudentLogistic
        logistic = StudentLogistic.objects.filter(student=student).order_by('-updated_at').first() if student else None
        context = {
            'student': student,
            'student_block_reason': block_reason,
            'student_full_name': student.full_name if student else (request.user.get_full_name() or request.user.username),
            'student_nis': student.nis if student else '',
            'student_class_name': student.class_room.name if student and student.class_room else '-',
            'available_exams': available_exams,
            'exam_history': exam_history,
            'logistics': {
                'room_name': logistic.room_name if logistic else '-',
                'session_name': logistic.session_name if logistic else '-',
            },
            'now': now,
        }
        return TemplateResponse(request, 'exam_engine/student_dashboard.html', context)


@method_decorator(never_cache, name='dispatch')
class ConfirmTokenView(View):
    """Validasi token 6 karakter lalu memulai atau melanjutkan sesi ujian siswa."""

    def post(self, request, *args, **kwargs):
        is_htmx = bool(request.headers.get('HX-Request'))

        def reject(text, tone='error'):
            if is_htmx:
                return _gate_message(text, tone)
            (messages.error if tone == 'error' else messages.warning)(request, text)
            return redirect(DASHBOARD_URL)

        if not request.user.is_authenticated:
            return redirect('accounts:login')

        student = get_current_student(request)
        block_reason = student_block_reason(student)
        if block_reason:
            return reject(block_reason)

        schedule_id = request.POST.get('schedule_id', '').strip()
        entered_token = request.POST.get('token', '').strip().upper()
        if not schedule_id or not entered_token:
            return reject("Jadwal dan 6 karakter token wajib diisi.")
        try:
            posted = Schedule.objects.select_related('exam').get(id=uuid.UUID(schedule_id))
        except (ValueError, Schedule.DoesNotExist):
            return reject("Jadwal ujian tidak ditemukan.")

        if not posted.exam.is_ready_for_student:
            return reject("Naskah ujian ini belum diverifikasi, jadi belum bisa dikerjakan.")

        # Jadwal yang dipakai selalu jadwal hasil eligibility, bukan id kiriman browser,
        # supaya siswa tidak bisa membuka paket lewat jadwal kelas lain atau membuat sesi ganda.
        schedule = next((s for s in eligible_schedules_for(student) if s.exam_id == posted.exam_id), None)
        if schedule is None:
            return reject("Ujian ini bukan untuk kelas Anda.")

        now = timezone.now()
        existing = ExamSession.objects.filter(student=student, schedule__exam_id=schedule.exam_id).first()
        if existing and existing.status == 'finished':
            return _hx_redirect(DASHBOARD_URL) if is_htmx else redirect(DASHBOARD_URL)

        if not existing:
            if schedule.end_time and now > schedule.end_time:
                end_str = timezone.localtime(schedule.end_time).strftime('%H:%M')
                return reject(f"Waktu ujian ini sudah berakhir pukul {end_str} WIB.")
            if schedule.start_time and now < schedule.start_time:
                start_str = timezone.localtime(schedule.start_time).strftime('%H:%M')
                return reject(f"Ujian belum dibuka. Akses dibuka pukul {start_str} WIB.", tone='warning')

        if schedule.token.strip().upper() != entered_token:
            return reject("Token ujian tidak valid. Minta token dari guru di ruang ujian.")

        if existing:
            session = existing
        else:
            session, _ = ExamSession.objects.get_or_create(
                student=student,
                schedule=schedule,
                defaults={'status': 'active', 'remaining_seconds': (schedule.exam.duration or 60) * 60},
            )
        initialize_session_answers(session)

        target_url = f"/exam/session/{session.id}/"
        return _hx_redirect(target_url) if is_htmx else redirect(target_url)


@method_decorator(never_cache, name='dispatch')
class ExamInterfaceView(View):
    """Lembar kerja ujian siswa."""

    def get(self, request, session_id, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect(f"/auth/login/?next={request.get_full_path()}")
        session = get_owned_session(request, session_id)

        if finalize_if_time_up(session):
            session.refresh_from_db()
            messages.info(request, f"Ujian sudah selesai. Nilai Anda: {session.score}")
            return redirect(DASHBOARD_URL)

        initialize_session_answers(session)
        remaining = session.calculate_remaining_seconds()
        ExamSession.objects.filter(pk=session.pk).update(remaining_seconds=remaining, last_seen_at=timezone.now())

        payload = get_session_questions_payload(session, current_order=1)
        exam = session.schedule.exam
        context = {
            'session': session,
            'schedule': session.schedule,
            'exam': exam,
            'questions': payload['questions_list'],
            'current_item': payload['current_item'],
            'current_order': payload['current_order'],
            'total_count': payload['total_count'],
            'answered_count': payload['answered_count'],
            'doubt_count': payload['doubt_count'],
            'progress_percent': payload['progress_percent'],
            'has_prev': payload['has_prev'],
            'prev_order': payload['prev_order'],
            'has_next': payload['has_next'],
            'next_order': payload['next_order'],
            'is_last': payload['is_last'],
            'remaining_seconds': remaining,
            'is_locked': session.is_locked,
            'is_official_exam': (exam.exam_type or '').upper() in COLLABORATIVE_TYPES,
            'violation_count': session.violation_count,
            'exam_title': exam.title,
        }
        return TemplateResponse(request, 'exam_engine/exam_interface.html', context)


def _card_context(session, payload):
    return {
        'session': session,
        'schedule': session.schedule,
        'exam': session.schedule.exam,
        'current_item': payload['current_item'],
        'current_order': payload['current_order'],
        'total_count': payload['total_count'],
        'has_prev': payload['has_prev'],
        'prev_order': payload['prev_order'],
        'has_next': payload['has_next'],
        'next_order': payload['next_order'],
        'is_last': payload['is_last'],
    }


@method_decorator(never_cache, name='dispatch')
class QuestionSwapView(View):
    """Ganti soal di viewport (#question-viewport)."""

    def get(self, request, session_id, order_num, *args, **kwargs):
        session = get_owned_session(request, session_id)
        if finalize_if_time_up(session):
            return _hx_redirect(DASHBOARD_URL)
        payload = get_question_payload(session, current_order=order_num)
        return TemplateResponse(request, 'exam_engine/partials/question_card.html', _card_context(session, payload))


@method_decorator(never_cache, name='dispatch')
class SaveAnswerView(View):
    """
    Simpan pilihan jawaban atau toggle Ragu. Hanya field yang dikirim yang berubah,
    lalu kartu soal dirender ulang beserta OOB update tombol navigasi dan penghitung.
    """

    def post(self, request, session_id, *args, **kwargs):
        session = get_owned_session(request, session_id)
        if finalize_if_time_up(session):
            return _hx_redirect(DASHBOARD_URL)
        if session.status == 'locked':
            response = HttpResponse("Sesi ujian terkunci.", status=409)
            response['HX-Reswap'] = 'none'
            return response

        try:
            question_id = uuid.UUID(request.POST.get('question_id', ''))
        except ValueError:
            raise Http404
        answer = get_object_or_404(StudentAnswer.objects.select_related('question'), session=session, question_id=question_id)

        if 'chosen_answer' in request.POST:
            choice = request.POST.get('chosen_answer', '').strip().upper()
            if choice in (answer.option_order or 'ABCDE'):
                answer.chosen_answer = choice or None
        if 'toggle_doubt' in request.POST:
            answer.is_doubt = not answer.is_doubt

        answer.evaluate_correctness()
        answer.save(update_fields=['chosen_answer', 'is_doubt', 'is_correct', 'updated_at'])

        payload = get_question_payload(session, current_order=answer.order_number)
        context = _card_context(session, payload)
        card_html = render_to_string('exam_engine/partials/question_card.html', context, request=request)
        oob_html = render_to_string('exam_engine/partials/answer_oob.html', {
            'session': session,
            'item': payload['current_item'],
            'answered_count': payload['answered_count'],
            'total_count': payload['total_count'],
            'progress_percent': payload['progress_percent'],
        }, request=request)
        return HttpResponse(card_html + oob_html)


@method_decorator(never_cache, name='dispatch')
class ViolationHandlerView(View):
    """
    Catat pelanggaran pindah layar. UH dan PTS hanya peringatan; PAS/PAT/SAJ terkunci pada pelanggaran ke-2
    dan dibuka hanya oleh admin/kurikulum (SOP pembinaan siswa).
    """

    def post(self, request, session_id, *args, **kwargs):
        with transaction.atomic():
            session = get_owned_session(request, session_id, for_update=True)
            if session.status == 'finished':
                return _hx_redirect(DASHBOARD_URL)
            if session.status == 'locked':
                return render(request, 'exam_engine/partials/lock_overlay.html', {'session': session})

            ExamSession.objects.filter(pk=session.pk).update(violation_count=F('violation_count') + 1)
            session.refresh_from_db(fields=['violation_count'])
            is_official = (session.schedule.exam.exam_type or 'UH').upper() in COLLABORATIVE_TYPES
            if is_official and session.violation_count >= 2:
                session.status = 'locked'
                session.save(update_fields=['status'])
                return render(request, 'exam_engine/partials/lock_overlay.html', {'session': session})

        return render(request, 'exam_engine/partials/violation_toast.html', {
            'count': session.violation_count,
            'is_official': is_official,
        })


@method_decorator(never_cache, name='dispatch')
class StatusCheckView(View):
    """Polling layar terkunci: buka kembali bila admin membuka kunci, ke dashboard bila sesi selesai."""

    def get(self, request, session_id, *args, **kwargs):
        session = get_owned_session(request, session_id)
        if finalize_if_time_up(session):
            return _hx_redirect(DASHBOARD_URL)
        if session.status == 'active':
            response = HttpResponse('')
            response['HX-Refresh'] = 'true'
            return response
        return render(request, 'exam_engine/partials/lock_overlay.html', {'session': session})


@method_decorator(never_cache, name='dispatch')
class HeartbeatView(View):
    """Detak berkala dari browser siswa: mencatat kapan terakhir terlihat dan mengembalikan status sesi."""

    def post(self, request, session_id, *args, **kwargs):
        session = get_owned_session(request, session_id)
        finalize_if_time_up(session)
        ExamSession.objects.filter(pk=session.pk).update(last_seen_at=timezone.now())
        session.refresh_from_db(fields=['status'])
        return JsonResponse({'status': session.status, 'remaining_seconds': session.calculate_remaining_seconds()})


@method_decorator(never_cache, name='dispatch')
class FinishExamView(View):
    """Kirim lembar ujian dan hitung nilai."""

    def post(self, request, session_id, *args, **kwargs):
        session = get_owned_session(request, session_id)
        if session.status == 'locked':
            # Sesi terkunci karena pelanggaran diselesaikan oleh admin/kurikulum, bukan oleh siswa
            messages.error(request, "Ujian Anda terkunci. Temui bagian kurikulum.")
            return redirect(f"/exam/session/{session.id}/")
        # Aturan sekolah: siswa tidak menyelesaikan ujian sendiri; formulir ini dikirim otomatis saat
        # hitung mundur habis. Selisih beberapa detik jam HP dan server tetap diterima.
        if session.status != 'finished' and session.calculate_remaining_seconds() > FINISH_GRACE_SECONDS:
            message = "Ujian belum bisa diselesaikan. Jawaban terkirim otomatis saat waktu habis."
            if request.headers.get('HX-Request'):
                return HttpResponse(message, status=403)
            messages.info(request, message)
            return redirect(f"/exam/session/{session.id}/")
        score = grade_exam_session(session)
        if request.headers.get('HX-Request'):
            return render(request, 'exam_engine/partials/finish_modal.html', {'session': session, 'score': score})
        messages.success(request, f"Ujian berhasil diselesaikan. Nilai Anda: {score}")
        return redirect(DASHBOARD_URL)

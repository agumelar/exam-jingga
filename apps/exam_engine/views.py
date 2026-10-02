"""Views and HTMX Endpoints for Core CBT Exam Engine (Task 7)."""
import logging
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.http import HttpResponse, HttpResponseForbidden, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.template.response import TemplateResponse
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.http import require_POST, require_GET

from apps.accounts.decorators import student_required
from apps.master_data.models import Student
from apps.schedules.models import Schedule, ExamQuestion
from apps.exam_engine.models import ExamSession, StudentAnswer
from apps.exam_engine.utils import (
    initialize_session_answers,
    get_session_questions_payload,
    grade_exam_session,
)

logger = logging.getLogger(__name__)
User = get_user_model()


def get_current_student(request):
    """Mencari objek Student yang terkait dengan pengguna yang sedang login."""
    if not request.user.is_authenticated:
        return None
    student = getattr(request.user, 'student_profile', None)
    if not student:
        student = Student.objects.filter(user=request.user).first()
    if not student and getattr(request.user, 'nis', None):
        student = Student.objects.filter(nis=request.user.nis).first()
    return student


class StudentDashboardView(View):
    """
    Dashboard Siswa Peserta Ujian CBT.
    Menampilkan profil siswa, jadwal ujian aktif/tersedia, alokasi ruang/sesi, dan riwayat nilai ujian selesai.
    """
    def get(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect(f"/auth/login/?next={request.get_full_path()}")

        student = get_current_student(request)
        
        # Fallback profile untuk staff/admin yang menguji dashboard siswa
        if not student:
            full_name = request.user.get_full_name() or request.user.username
            nis = getattr(request.user, 'nis', None) or '0000000000'
            student_class_name = 'Peserta Ujian'
            student_level = 10
        else:
            full_name = student.full_name
            nis = student.nis
            student_class_name = student.class_room.name if student.class_room else 'Kelas Terdaftar'
            student_level = student.class_room.level if student.class_room else 10

        # Ambil jadwal ujian yang aktif dan siap diujikan
        schedules_qs = (
            Schedule.objects.filter(
                status='active',
                exam__status__in=['validated', 'ready', 'active']
            )
            .select_related('exam', 'exam__subject', 'exam__teacher', 'class_room', 'teacher')
            .order_by('start_time')
        )

        # Filter jadwal sesuai kelas / jenjang siswa
        eligible_schedules = []
        for sch in schedules_qs:
            if sch.exam.exam_type in ['UH', 'PTS']:
                # Non-collaborative: harus spesifik kelas siswa jika student punya kelas
                if student and student.class_room:
                    if sch.class_room_id == student.class_room_id:
                        eligible_schedules.append(sch)
                else:
                    eligible_schedules.append(sch)
            else:
                # Collaborative (PAS, PAT, SAJ): cocok jenjang tingkat atau kelas
                if sch.exam.level and sch.exam.level == student_level:
                    eligible_schedules.append(sch)
                elif sch.class_room_id and student and student.class_room_id == sch.class_room_id:
                    eligible_schedules.append(sch)
                elif not sch.class_room_id and not sch.exam.level:
                    eligible_schedules.append(sch)

        # Ambil sesi siswa yang sudah ada
        my_sessions_map = {}
        if student:
            for sess in ExamSession.objects.filter(student=student):
                my_sessions_map[str(sess.schedule_id)] = sess

        available_exams = []
        for sch in eligible_schedules:
            sess = my_sessions_map.get(str(sch.id))
            student_status = sess.status if sess else 'not_started'
            score = sess.score if sess else None
            session_id = sess.id if sess else None

            if student_status != 'finished':
                available_exams.append({
                    'schedule': sch,
                    'student_status': student_status,
                    'score': score,
                    'session_id': session_id,
                })

        # Ambil seluruh riwayat ujian selesai milik siswa
        exam_history = []
        if student:
            finished_sessions = (
                ExamSession.objects.filter(student=student, status='finished')
                .select_related('schedule', 'schedule__exam', 'schedule__exam__subject')
                .order_by('-finished_at', '-started_at')
            )
            for fs in finished_sessions:
                exam_history.append({
                    'schedule': fs.schedule,
                    'student_status': 'finished',
                    'score': fs.score,
                    'session_id': fs.id,
                    'finished_at': fs.finished_at,
                })

        # Ruangan & Sesi logistik
        logistics = {
            'room_name': eligible_schedules[0].room_name if eligible_schedules and eligible_schedules[0].room_name else 'Lab CBT 1',
            'session_name': eligible_schedules[0].session_display if eligible_schedules else 'Sesi 1',
        }

        context = {
            'student': student,
            'student_full_name': full_name,
            'student_nis': nis,
            'student_class_name': student_class_name,
            'available_exams': available_exams,
            'exam_history': exam_history,
            'logistics': logistics,
            'now': timezone.now(),
        }
        return TemplateResponse(request, 'exam_engine/student_dashboard.html', context)


class ConfirmTokenView(View):
    """
    Validasi Token Ujian 6 Digit (Huruf & Angka) dan Memulai / Melanjutkan Sesi Ujian Siswa.
    Endpoint: POST /exam/confirm-token/
    """
    def post(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return HttpResponseForbidden("Silakan login terlebih dahulu.")

        student = get_current_student(request)
        if not student:
            # Buat student profile otomatis jika admin / tester
            student, _ = Student.objects.get_or_create(
                user=request.user,
                defaults={
                    'nis': getattr(request.user, 'nis', None) or '0000000000',
                    'full_name': request.user.get_full_name() or request.user.username,
                    'status': 'aktif'
                }
            )

        schedule_id = request.POST.get('schedule_id', '').strip()
        entered_token = request.POST.get('token', '').strip().upper()

        if not schedule_id or not entered_token:
            if request.headers.get('HX-Request'):
                return HttpResponse('<div class="p-3 bg-red-100 dark:bg-red-950/40 text-red-600 rounded-xl text-xs font-bold border border-red-200 dark:border-red-900">Jadwal dan 6 digit token wajib diisi.</div>', status=400)
            messages.error(request, "Jadwal dan token wajib diisi.")
            return redirect('/student/dashboard/')

        schedule = get_object_or_404(Schedule.objects.select_related('exam'), id=schedule_id)

        # Validasi Token
        if schedule.token.strip().upper() != entered_token:
            if request.headers.get('HX-Request'):
                return HttpResponse('<div class="p-3 bg-red-100 dark:bg-red-950/40 text-red-600 rounded-xl text-xs font-bold border border-red-200 dark:border-red-900">Token ujian tidak valid. Pastikan meminta token dari pengawas!</div>', status=400)
            messages.error(request, "Token ujian tidak valid. Silakan periksa kembali token dari pengawas ruangan.")
            return redirect('/student/dashboard/')

        # Dapatkan atau buat ExamSession secara atomik
        session, created = ExamSession.objects.get_or_create(
            student=student,
            schedule=schedule,
            defaults={
                'status': 'active',
                'remaining_seconds': (schedule.exam.duration or 60) * 60,
                'violation_count': 0,
                'score': 0.0,
            }
        )

        if created:
            initialize_session_answers(session)
        elif session.status == 'finished':
            if request.headers.get('HX-Request'):
                response = HttpResponse(status=200)
                response['HX-Redirect'] = '/student/dashboard/'
                return response
            messages.info(request, "Ujian ini telah selesai dikerjakan.")
            return redirect('/student/dashboard/')

        target_url = f"/exam/session/{session.id}/"
        if request.headers.get('HX-Request'):
            response = HttpResponse(status=200)
            response['HX-Redirect'] = target_url
            return response

        return redirect(target_url)


class ExamInterfaceView(View):
    """
    Lembar Kerja CBT Siswa (Sterile Exam Interface).
    Menampilkan Top Bar (Timer, Font Size Toggle, Tombol Selesai), Viewport Soal #1, dan Drawer Navigasi.
    Endpoint: GET /exam/session/<uuid:session_id>/
    """
    def get(self, request, session_id, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect(f"/auth/login/?next={request.get_full_path()}")

        session = get_object_or_404(
            ExamSession.objects.select_related(
                'student', 'student__user', 'schedule', 'schedule__exam',
                'schedule__exam__subject', 'schedule__teacher'
            ),
            id=session_id
        )

        # Validasi kepemilikan sesi ujian
        student = get_current_student(request)
        if not request.user.is_superuser:
            if student and session.student_id != student.id:
                messages.error(request, "Anda tidak memiliki akses ke lembar kerja ujian ini.")
                return redirect('/student/dashboard/')

        # Jika sudah selesai, alihkan ke dashboard
        if session.status == 'finished':
            messages.info(request, f"Ujian telah diselesaikan dengan nilai {session.score}.")
            return redirect('/student/dashboard/')

        # Hitung sisa waktu dinamis
        remaining = session.calculate_remaining_seconds()
        if remaining <= 0 and session.status == 'active':
            grade_exam_session(session)
            messages.warning(request, "Waktu ujian telah habis. Jawaban Anda telah otomatis dikirim ke server.")
            return redirect('/student/dashboard/')

        session.remaining_seconds = remaining
        session.save(update_fields=['remaining_seconds'])

        # Inisialisasi lembar jawaban jika belum ada
        if session.student_answers.count() == 0:
            initialize_session_answers(session)

        # Muat data butir soal dan navigasi
        payload = get_session_questions_payload(session, current_order=1)

        context = {
            'session': session,
            'schedule': session.schedule,
            'exam': session.schedule.exam,
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
            'violation_count': session.violation_count,
            'exam_title': session.schedule.exam.title,
            'exam_subtitle': f"{session.schedule.exam.subject.name if session.schedule.exam.subject else 'CBT'} • {session.student.full_name}",
        }
        return TemplateResponse(request, 'exam_engine/exam_interface.html', context)


class QuestionSwapView(View):
    """
    HTMX Endpoint untuk Mengganti Butir Soal pada Viewport (#question-viewport).
    Endpoint: GET /exam/session/<uuid:session_id>/question/<int:order_num>/
    """
    def get(self, request, session_id, order_num, *args, **kwargs):
        if not request.user.is_authenticated:
            return HttpResponseForbidden("Unauthenticated")

        session = get_object_or_404(
            ExamSession.objects.select_related('schedule', 'schedule__exam'),
            id=session_id
        )

        payload = get_session_questions_payload(session, current_order=order_num)

        context = {
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
        return TemplateResponse(request, 'exam_engine/partials/question_card.html', context)


class SaveAnswerView(View):
    """
    HTMX Endpoint untuk Menyimpan Pilihan Jawaban dan Status Ragu-Ragu secara Real-Time.
    Mengembalikan Out-of-Band (OOB) swap untuk mengupdate warna tombol navigasi di drawer dan sidebar.
    Endpoint: POST /exam/session/<uuid:session_id>/save-answer/
    """
    def post(self, request, session_id, *args, **kwargs):
        if not request.user.is_authenticated:
            return HttpResponseForbidden("Unauthenticated")

        session = get_object_or_404(ExamSession, id=session_id)
        if session.status in ['locked', 'finished']:
            return HttpResponseForbidden("Sesi ujian terkunci atau telah selesai.")

        question_id = request.POST.get('question_id')
        chosen_answer = request.POST.get('chosen_answer')
        is_doubt_raw = request.POST.get('is_doubt')
        order_num = int(request.POST.get('order_num', 1))

        ans = get_object_or_404(
            StudentAnswer.objects.select_related('question'),
            session=session,
            question_id=question_id
        )

        if chosen_answer is not None:
            clean_ans = chosen_answer.strip().upper()
            ans.chosen_answer = clean_ans if clean_ans in ['A', 'B', 'C', 'D', 'E'] else None

        if is_doubt_raw is not None:
            ans.is_doubt = is_doubt_raw in ['true', 'True', '1', 1, True, 'on']

        ans.evaluate_correctness()
        ans.save()

        # Update totals & generate Out-of-Band (OOB) Swaps
        payload = get_session_questions_payload(session, current_order=order_num)
        curr = payload['current_item']

        # Determine Button Color State
        # Green/Emerald = Answered, Amber/Yellow = Doubt, Stone = Empty
        is_answered = bool(ans.chosen_answer)
        is_doubt = ans.is_doubt

        btn_classes = "bg-slate-100 dark:bg-zinc-800 text-slate-600 dark:text-zinc-400"
        if is_doubt:
            btn_classes = "bg-amber-400 text-slate-950 font-black shadow-md shadow-amber-400/20"
        elif is_answered:
            btn_classes = "bg-emerald-500 text-white font-black shadow-md shadow-emerald-500/20"

        active_ring = "ring-2 ring-orange-600 ring-offset-2 dark:ring-offset-zinc-950 scale-105 shadow-md z-10"

        ans_badge = f'<span class="text-[7px] leading-none uppercase">{ans.chosen_answer}</span>' if is_answered else ''
        drawer_ans_badge = f'<span class="text-[8px] opacity-80 uppercase leading-none font-bold">{ans.chosen_answer}</span>' if is_answered else ''

        # Render OOB snippets
        oob_response = f"""
        <!-- OOB Update for Desktop Sidebar Button -->
        <button 
          id="nav-btn-{order_num}" 
          hx-swap-oob="outerHTML"
          hx-get="/exam/session/{session.id}/question/{order_num}/" 
          hx-target="#question-viewport"
          hx-swap="innerHTML"
          @click="activeOrder = {order_num}"
          :class="activeOrder === {order_num} ? '{active_ring}' : ''"
          class="h-11 rounded-xl text-xs font-black transition-all cursor-pointer flex flex-col items-center justify-center {btn_classes}"
        >
          <span>{order_num}</span>
          {ans_badge}
        </button>

        <!-- OOB Update for Mobile Drawer Button -->
        <button 
          id="drawer-nav-btn-{order_num}" 
          hx-swap-oob="outerHTML"
          hx-get="/exam/session/{session.id}/question/{order_num}/" 
          hx-target="#question-viewport"
          hx-swap="innerHTML"
          @click="activeOrder = {order_num}; isDrawerOpen = false"
          :class="activeOrder === {order_num} ? 'ring-3 ring-orange-600 ring-offset-2 dark:ring-offset-zinc-900 scale-105 shadow-xl z-10' : ''"
          class="h-12 rounded-2xl text-xs font-black transition-all flex flex-col items-center justify-center relative cursor-pointer active:scale-95 {btn_classes}"
        >
          <span>{order_num}</span>
          {drawer_ans_badge}
        </button>

        <!-- OOB Update for Answered Counter -->
        <span id="answered-counter" hx-swap-oob="outerHTML" class="text-[10px] font-black text-orange-600">
          {payload['answered_count']}/{payload['total_count']}
        </span>
        <span id="drawer-answered-counter" hx-swap-oob="outerHTML" class="text-[10px] font-bold text-slate-400 dark:text-zinc-500 uppercase tracking-widest">
          Terjawab: {payload['answered_count']} dari {payload['total_count']} ({payload['progress_percent']}%)
        </span>

        <!-- OOB Update for Progress Bars -->
        <div id="progress-bar-fill" hx-swap-oob="outerHTML" class="bg-gradient-to-r from-orange-500 to-orange-600 h-full transition-all duration-500" style="width: {payload['progress_percent']}%;"></div>
        <div id="drawer-progress-bar-fill" hx-swap-oob="outerHTML" class="bg-gradient-to-r from-orange-500 to-orange-600 h-full transition-all duration-500" style="width: {payload['progress_percent']}%;"></div>
        """
        return HttpResponse(oob_response.strip(), content_type="text/html")


class ViolationHandlerView(View):
    """
    HTMX Endpoint untuk Mencatat Pelanggaran Pindah Layar / Tab Blur.
    Jika violation_count >= 2, kunci sesi ujian dan tampilkan Red Screen Lock Overlay.
    Endpoint: POST /exam/session/<uuid:session_id>/violation/
    """
    def post(self, request, session_id, *args, **kwargs):
        session = get_object_or_404(ExamSession, id=session_id)
        if session.status == 'finished':
            return HttpResponseForbidden("Sesi selesai.")

        session.violation_count += 1
        if session.violation_count >= 2:
            session.status = 'locked'
            session.save(update_fields=['violation_count', 'status'])
            # Render red lock overlay
            return render(request, 'exam_engine/partials/lock_overlay.html', {'session': session})

        session.save(update_fields=['violation_count'])
        return HttpResponse(
            f"""
            <div id="toast-warning" class="fixed top-20 right-6 z-50 p-4 rounded-2xl bg-amber-500 text-slate-950 font-black shadow-2xl flex items-center gap-3 animate-in slide-in-from-top duration-300">
              <i data-lucide="alert-triangle" class="w-5 h-5"></i>
              <div>
                <p class="text-xs uppercase">Peringatan Anti-Cheat ({session.violation_count}/2)</p>
                <p class="text-[10px] font-bold">Dilarang berpindah aplikasi atau tab selama ujian!</p>
              </div>
            </div>
            <script>
              setTimeout(() => {{
                const t = document.getElementById('toast-warning');
                if (t) t.remove();
              }}, 3500);
              if (window.lucide) lucide.createIcons();
            </script>
            """,
            content_type="text/html"
        )


class StatusCheckView(View):
    """
    HTMX Polling Endpoint untuk Memeriksa Status Kunci Sesi Ujian (Dipanggil tiap 3 detik).
    Jika status kembali 'active' (dibuka oleh proktor), refresh atau hilangkan lock overlay.
    Endpoint: GET /exam/session/<uuid:session_id>/check-status/
    """
    def get(self, request, session_id, *args, **kwargs):
        session = get_object_or_404(ExamSession, id=session_id)
        if session.status == 'active':
            # Session telah dibuka kuncinya oleh pengawas
            return HttpResponse(
                """
                <div id="lock-container" hx-swap-oob="innerHTML"></div>
                <script>
                  window.location.reload();
                </script>
                """,
                content_type="text/html"
            )
        # Tetap terkunci
        return render(request, 'exam_engine/partials/lock_overlay.html', {'session': session})


class FinishExamView(View):
    """
    Penyelesaian dan Pengumpulan Ujian Siswa (Kalkulasi Nilai Otomatis).
    Endpoint: POST /exam/session/<uuid:session_id>/finish/
    """
    def post(self, request, session_id, *args, **kwargs):
        session = get_object_or_404(ExamSession, id=session_id)
        if session.status != 'finished':
            score = grade_exam_session(session)
        else:
            score = session.score

        if request.headers.get('HX-Request'):
            return render(request, 'exam_engine/partials/finish_modal.html', {
                'session': session,
                'score': score,
            })

        messages.success(request, f"Ujian berhasil diselesaikan! Nilai Anda: {score}")
        return redirect('/student/dashboard/')

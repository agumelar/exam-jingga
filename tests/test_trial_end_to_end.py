"""Uji coba alur lengkap seperti rencana uji di produksi.

Data meniru produksi: kelas 10 Uji (jurusan Ujicoba), guru gumelar, akun admin-exam dan kurikulum,
dua siswa uji (NIS 9999000001 dan 9999000002), plus satu kelas lain beserta gurunya sebagai pembanding.
Setiap peran disimulasikan lewat request HTTP. Login SSO, timer, deteksi pindah tab, dan tampilan
browser tidak tercakup di sini; bagian itu diuji lewat uji asap di produksi.
"""
import io
from datetime import timedelta
from types import SimpleNamespace

import openpyxl
import pytest
from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.urls import reverse
from django.utils import timezone

from apps.accounts.models import Role
from apps.exam_engine.models import ExamSession, StudentAnswer
from apps.master_data.models import ClassRoom, Major, Student, Subject, Teacher, TeacherAssignment
from apps.questions.models import Question
from apps.reports.models import SessionActionLog
from apps.schedules.models import Exam, ExamQuestion, Schedule

User = get_user_model()
HX = {'HTTP_HX_REQUEST': 'true'}


def _start_in(minutes):
    return (timezone.localtime() + timedelta(minutes=minutes)).strftime('%Y-%m-%dT%H:%M')


def _student(nis, name, class_room):
    user = User.objects.create_user(username=nis, nis=nis, role=Role.SISWA, full_name=name)
    return Student.objects.create(user=user, nis=nis, full_name=name, class_room=class_room, status='aktif')


def _question(author, subject, tag, correct):
    return Question.objects.create(subject=subject, level=10, created_by=author, question_text=f'Soal lama {tag}',
                                   option_a=f'{tag}-a', option_b=f'{tag}-b', option_c=f'{tag}-c',
                                   option_d=f'{tag}-d', option_e=f'{tag}-e', correct_answer=correct)


@pytest.fixture
def school(db):
    major = Major.objects.create(name='Ujicoba', code='UJI')
    uji = ClassRoom.objects.create(name='10 Uji', level=10, major=major)
    rpl = ClassRoom.objects.create(name='10 RPL 1', level=10, major=major)
    subject = Subject.objects.create(name='Konsentrasi Keahlian RPL')

    guru_user = User.objects.create_user(username='gumelar', role=Role.GURU, email='gumelar@smkn1rongga.sch.id')
    guru = Teacher.objects.create(user=guru_user, full_name='Agung Gumelar Saputra', email=guru_user.email)
    rekan_user = User.objects.create_user(username='rekan', role=Role.GURU, email='rekan@smkn1rongga.sch.id')
    rekan = Teacher.objects.create(user=rekan_user, full_name='Guru Rekan', email=rekan_user.email)
    TeacherAssignment.objects.create(teacher=guru, subject=subject, class_room=uji)
    TeacherAssignment.objects.create(teacher=rekan, subject=subject, class_room=rpl)

    admin = User.objects.create_user(username='admin-exam', role=Role.ADMIN, is_staff=True)
    kurikulum = User.objects.create_user(username='kurikulum', role=Role.KURIKULUM, is_staff=True)

    siswa1 = _student('9999000001', 'Siswa Uji 1', uji)
    siswa2 = _student('9999000002', 'Siswa Uji 2', uji)
    luar = _student('9999000009', 'Siswa Kelas Lain', rpl)

    # Di produksi gumelar sudah punya 2 soal level 10; soal rekan tidak boleh bisa dipilih gumelar
    lama = [_question(guru, subject, 'lama1', 'B'), _question(guru, subject, 'lama2', 'D')]
    soal_rekan = _question(rekan, subject, 'rekan', 'A')
    return SimpleNamespace(**locals())


def _create_questions(client, s, n=3):
    letters = ['A', 'C', 'E']
    for i in range(n):
        res = client.post(reverse('questions:create'), {
            'subject': s.subject.id, 'level': 10, 'question_text': f'Soal uji coba {i + 1}',
            'option_a': f'baru{i}-a', 'option_b': f'baru{i}-b', 'option_c': f'baru{i}-c',
            'option_d': f'baru{i}-d', 'option_e': f'baru{i}-e', 'correct_answer': letters[i],
        }, **HX)
        assert res.status_code == 200, res.content.decode()[:500]
    return list(Question.objects.filter(created_by=s.guru, question_text__startswith='Soal uji coba'))


def _create_schedule(client, s, **data):
    payload = {'exam_type': 'UH', 'title': 'UJI COBA UH', 'level': 10, 'subject': s.subject.id,
               'class_room': s.uji.id, 'duration': 20, 'target_question_count': 5, 'session_no': '0',
               'token': 'UJI001', 'start_time': _start_in(60)}
    payload.update(data)
    return client.post(reverse('schedules:create'), payload, **HX)


def _pick_questions(client, exam, questions):
    for q in questions:
        res = client.post(reverse('schedules:toggle_question', args=[exam.id, q.id]), {'idx': '1'}, **HX)
        assert res.status_code == 200, res.content.decode()[:500]
    return client.post(reverse('schedules:save_questions', args=[exam.id]), **HX)


def _open_now(schedule):
    now = timezone.now()
    Schedule.objects.filter(pk=schedule.pk).update(start_time=now - timedelta(minutes=1),
                                                   end_time=now + timedelta(minutes=schedule.exam.duration + 30))


def _start_exam(client, student, schedule, token):
    client.force_login(student.user)
    res = client.post(reverse('exam_engine:confirm_token'), {'schedule_id': str(schedule.id), 'token': token}, **HX)
    return res, ExamSession.objects.filter(student=student, schedule=schedule).first()


def _answer(client, session, question, letter):
    return client.post(reverse('exam_engine:save_answer', args=[session.id]),
                       {'question_id': question.id, 'chosen_answer': letter}, **HX)


def _wrong_letter(question):
    return next(x for x in 'ABCDE' if x != question.correct_answer)


def _layout(session):
    return [(a.question_id, a.option_order) for a in StudentAnswer.objects.filter(session=session).order_by('order_number')]


# ==============================================================================
# Ulangan Harian: guru sendiri dari soal sampai rekap
# ==============================================================================

@pytest.mark.django_db
def test_uh_trial_from_question_bank_to_results(client, school):
    s = school

    # 1. Guru menulis 3 soal level 10 lewat Bank Soal
    client.force_login(s.guru_user)
    baru = _create_questions(client, s)
    assert len(baru) == 3
    assert all(q.created_by == s.guru and q.level == 10 for q in baru)
    soal = s.lama + baru

    # 2. Guru tidak bisa membuat UH untuk kelas yang tidak diajar
    ditolak = _create_schedule(client, s, class_room=s.rpl.id)
    assert 'tidak mengajar' in ditolak.content.decode()
    assert not Schedule.objects.exists()

    # 3. Guru membuat UH untuk 10 Uji
    _create_schedule(client, s)
    exam = Exam.objects.get()
    schedule = Schedule.objects.get()
    assert (exam.exam_type, exam.status, exam.teacher, schedule.class_room) == ('UH', 'pending_selection', s.guru, s.uji)

    # 4. Halaman pilih soal hanya memuat soal milik guru, soal rekan tidak bisa dipilih
    page = client.get(reverse('schedules:select_questions', args=[exam.id]))
    assert page.status_code == 200
    html = page.content.decode()
    assert 'Soal uji coba 1' in html and 'Soal lama rekan' not in html
    client.post(reverse('schedules:toggle_question', args=[exam.id, s.soal_rekan.id]), {'idx': '1'}, **HX)
    assert not ExamQuestion.objects.filter(exam=exam, question=s.soal_rekan).exists()

    # 5. Simpan 5 soal: UH langsung tervalidasi tanpa verifikasi admin
    _pick_questions(client, exam, soal)
    exam.refresh_from_db()
    assert exam.status == 'validated'
    assert list(ExamQuestion.objects.filter(exam=exam).order_by('order_number').values_list('order_number', flat=True)) == [1, 2, 3, 4, 5]

    # 6. Isi naskah terkunci setelah tervalidasi
    edit = client.post(reverse('schedules:edit', args=[schedule.id]), {
        'exam_type': 'UH', 'title': 'UJI COBA UH', 'level': 10, 'subject': s.subject.id, 'class_room': s.uji.id,
        'duration': 20, 'target_question_count': 6, 'session_no': '0', 'token': 'UJI001',
        'start_time': timezone.localtime(schedule.start_time).strftime('%Y-%m-%dT%H:%M')}, **HX)
    exam.refresh_from_db()
    assert exam.target_question_count == 5
    assert 'tidak bisa diubah setelah diajukan' in edit.content.decode()

    # 7. Sebelum jam mulai, token belum bisa dipakai
    early, early_session = _start_exam(client, s.siswa1, schedule, 'UJI001')
    assert early_session is None

    _open_now(schedule)
    schedule.refresh_from_db()

    # 8. Dashboard siswa uji menampilkan UH; siswa kelas lain tidak melihat dan tidak bisa masuk
    client.force_login(s.siswa1.user)
    dash = client.get(reverse('exam_engine:student_dashboard'))
    assert [e['schedule'].id for e in dash.context['available_exams']] == [schedule.id]
    client.force_login(s.luar.user)
    assert client.get(reverse('exam_engine:student_dashboard')).context['available_exams'] == []
    _, luar_session = _start_exam(client, s.luar, schedule, 'UJI001')
    assert luar_session is None

    # 9. Token salah menampilkan pesan, token benar membuka ujian
    salah, sesi_salah = _start_exam(client, s.siswa1, schedule, 'SALAH1')
    assert sesi_salah is None
    assert 'Token ujian tidak valid' in salah.content.decode()
    ok, sesi1 = _start_exam(client, s.siswa1, schedule, 'UJI001')
    assert sesi1 is not None and sesi1.status == 'active'
    assert ok.headers.get('HX-Redirect', '').endswith(f'/exam/session/{sesi1.id}/')
    assert client.get(reverse('exam_engine:exam_interface', args=[sesi1.id])).status_code == 200

    _, sesi2 = _start_exam(client, s.siswa2, schedule, 'UJI001')
    assert sesi2 is not None

    # 10. Urutan soal dan opsi diacak per siswa, setiap soal muncul sekali
    for sesi in (sesi1, sesi2):
        layout = _layout(sesi)
        assert sorted(q for q, _ in layout) == sorted(q.id for q in soal)
        assert all(sorted(order) == list('ABCDE') for _, order in layout)
    assert _layout(sesi1) != _layout(sesi2)

    # 11. Siswa 1 menjawab semua benar lalu selesai
    client.force_login(s.siswa1.user)
    for q in soal:
        assert _answer(client, sesi1, q, q.correct_answer).status_code == 200
    client.post(reverse('exam_engine:finish_exam', args=[sesi1.id]), **HX)
    sesi1.refresh_from_db()
    assert (sesi1.status, sesi1.score) == ('finished', 100)

    # 12. Siswa 2: 2 benar, 2 salah, 1 kosong, satu ditandai ragu; pindah tab di UH tidak mengunci
    client.force_login(s.siswa2.user)
    _answer(client, sesi2, soal[0], soal[0].correct_answer)
    _answer(client, sesi2, soal[1], soal[1].correct_answer)
    _answer(client, sesi2, soal[2], _wrong_letter(soal[2]))
    _answer(client, sesi2, soal[3], _wrong_letter(soal[3]))
    client.post(reverse('exam_engine:save_answer', args=[sesi2.id]), {'question_id': soal[3].id, 'toggle_doubt': '1'}, **HX)
    for _ in range(3):
        client.post(reverse('exam_engine:violation_handler', args=[sesi2.id]), **HX)
    sesi2.refresh_from_db()
    assert (sesi2.status, sesi2.violation_count) == ('active', 3)

    # 13. Browser ditutup lalu dibuka lagi: jawaban dan tanda ragu tetap ada
    client.logout()
    client.force_login(s.siswa2.user)
    assert client.get(reverse('exam_engine:exam_interface', args=[sesi2.id])).status_code == 200
    ragu = StudentAnswer.objects.get(session=sesi2, question=soal[3])
    assert (ragu.chosen_answer, ragu.is_doubt) == (_wrong_letter(soal[3]), True)

    # 14. Waktu habis: jawaban baru ditolak, penilai otomatis menutup sesi
    ExamSession.objects.filter(pk=sesi2.pk).update(started_at=timezone.now() - timedelta(minutes=25))
    call_command('grade_expired_sessions')
    sesi2.refresh_from_db()
    assert (sesi2.status, sesi2.score) == ('finished', 40)
    _answer(client, sesi2, soal[4], soal[4].correct_answer)
    assert StudentAnswer.objects.get(session=sesi2, question=soal[4]).chosen_answer is None

    # 15. Rekap guru: dua peserta, nilai, benar/salah/kosong
    client.force_login(s.guru_user)
    hasil = client.get(reverse('reports:exam_results_detail', args=[exam.id]))
    assert hasil.status_code == 200
    rows = {p['nis']: p for p in hasil.context['participants']}
    assert set(rows) == {'9999000001', '9999000002'}
    assert (rows['9999000002']['score'], rows['9999000002']['correct_count'],
            rows['9999000002']['wrong_count'], rows['9999000002']['blank_count']) == (40, 2, 2, 1)
    assert hasil.context['stats']['completed'] == 2

    # 16. Analisis pengecoh memakai huruf asli soal walau opsi diacak
    analisis = client.get(reverse('reports:distractor_analysis', args=[exam.id]))
    assert analisis.status_code == 200
    from apps.reports.utils import calculate_distractor_analysis
    data = {row['question_id']: row for row in calculate_distractor_analysis(exam)['analysis_data']}
    assert data[str(soal[2].id)]['correct_answer'] == soal[2].correct_answer
    pengecoh = data[str(soal[2].id)]['distro']
    assert pengecoh[_wrong_letter(soal[2])] == 1
    assert pengecoh[soal[2].correct_answer] == 1

    # 17. Export Excel bisa dibuka dan memuat kedua siswa
    xlsx = client.get(reverse('reports:exam_results_export', args=[exam.id]))
    assert xlsx.status_code == 200
    wb = openpyxl.load_workbook(io.BytesIO(xlsx.content))
    isi = ' '.join(str(c.value) for ws in wb.worksheets for row in ws.iter_rows() for c in row if c.value is not None)
    assert 'SISWA UJI 1' in isi and 'SISWA UJI 2' in isi
    assert 'BELUM TUNTAS' in isi and 'ANALISIS BUTIR SOAL' in isi

    # 18. Guru lain tidak bisa membuka rekap paket ini
    client.force_login(s.rekan_user)
    assert client.get(reverse('reports:exam_results_detail', args=[exam.id])).status_code == 404

    # 19. Jadwal yang sudah dikerjakan tidak bisa dihapus
    client.force_login(s.guru_user)
    client.post(reverse('schedules:delete', args=[schedule.id]), **HX)
    assert Schedule.objects.filter(pk=schedule.pk).exists()


# ==============================================================================
# PTS: dibuat admin untuk satu guru, dikembalikan, diverifikasi, dihentikan kurikulum
# ==============================================================================

@pytest.mark.django_db
def test_pts_trial_review_and_session_actions(client, school):
    s = school
    client.force_login(s.guru_user)
    soal = s.lama + _create_questions(client, s)

    # 1. Admin membuat PTS untuk gumelar di 10 Uji
    client.force_login(s.admin)
    _create_schedule(client, s, exam_type='PTS', sub_type='PTS Ganjil', teacher=s.guru.id, title='UJI COBA PTS',
                     token='PTS001', start_time=_start_in(180))
    exam = Exam.objects.get()
    schedule = Schedule.objects.get()
    assert (exam.exam_type, exam.teacher, schedule.teacher, exam.status) == ('PTS', s.guru, s.guru, 'pending_selection')

    # 2. Guru memilih soal: PTS menunggu verifikasi admin
    client.force_login(s.guru_user)
    _pick_questions(client, exam, soal)
    exam.refresh_from_db()
    assert exam.status == 'waiting_validation'

    def action(user, name, data=None):
        client.force_login(user)
        res = client.post(reverse('schedules:action', kwargs={'pk': schedule.id, 'action': name}), data or {}, **HX)
        exam.refresh_from_db()
        return res

    # 3. Guru tidak bisa memverifikasi naskahnya sendiri
    action(s.guru_user, 'verify')
    assert exam.status == 'waiting_validation'

    # 4. Admin mengembalikan naskah: alasan wajib
    action(s.admin, 'reject', {'note': '  '})
    assert exam.status == 'waiting_validation'
    action(s.admin, 'reject', {'note': 'Soal nomor 2 kunci jawabannya perlu dicek.'})
    assert exam.status == 'pending_selection'
    assert exam.review_note == 'Soal nomor 2 kunci jawabannya perlu dicek.'

    # 5. Guru mengajukan ulang, admin memverifikasi
    client.force_login(s.guru_user)
    client.post(reverse('schedules:save_questions', args=[exam.id]), **HX)
    exam.refresh_from_db()
    assert exam.status == 'waiting_validation'
    action(s.admin, 'verify')
    assert exam.status == 'validated'

    _open_now(schedule)
    schedule.refresh_from_db()

    # 6. Pindah tab di PTS hanya peringatan, tidak mengunci (ketentuan.md: kunci hanya PAS/PAT/SAJ)
    _, sesi1 = _start_exam(client, s.siswa1, schedule, 'PTS001')
    for _ in range(2):
        client.post(reverse('exam_engine:violation_handler', args=[sesi1.id]), **HX)
    sesi1.refresh_from_db()
    assert (sesi1.status, sesi1.violation_count) == ('active', 2)

    # 7. Siswa 1 selesai normal
    for q in soal:
        _answer(client, sesi1, q, q.correct_answer)
    client.post(reverse('exam_engine:finish_exam', args=[sesi1.id]), **HX)
    sesi1.refresh_from_db()
    assert (sesi1.status, sesi1.score) == ('finished', 100)

    # 8. Guru tidak bisa menghentikan sesi; kurikulum bisa, alasan wajib, tercatat di log
    _, sesi2 = _start_exam(client, s.siswa2, schedule, 'PTS001')
    _answer(client, sesi2, soal[0], soal[0].correct_answer)
    client.force_login(s.guru_user)
    assert client.post(reverse('reports:session_force_submit', args=[sesi2.id]), {'reason': 'coba'}, **HX).status_code == 403
    client.force_login(s.kurikulum)
    client.post(reverse('reports:session_force_submit', args=[sesi2.id]), {'reason': ' '}, **HX)
    sesi2.refresh_from_db()
    assert sesi2.status == 'active'
    client.post(reverse('reports:session_force_submit', args=[sesi2.id]), {'reason': 'Waktu sesi ruangan habis'}, **HX)
    sesi2.refresh_from_db()
    assert (sesi2.status, sesi2.score) == ('finished', 20)
    log = SessionActionLog.objects.get(session_id_snapshot=sesi2.id)
    assert (log.action, log.reason, log.previous_status) == ('force_submit', 'Waktu sesi ruangan habis', 'active')

    # 9. Monitoring kurikulum hanya memuat siswa kelas 10 Uji
    mon = client.get(reverse('reports:session_monitoring'), {'schedule_id': schedule.id})
    assert mon.status_code == 200
    assert '9999000001' in mon.content.decode() and '9999000009' not in mon.content.decode()

    # 10. Naskah tidak bisa dibuka kuncinya setelah siswa mulai
    action(s.admin, 'unlock', {'note': 'Mau revisi soal'})
    assert exam.status == 'validated'


# ==============================================================================
# PAS kolaboratif: dua guru mengisi kuota, siswa terkunci lalu dibina kurikulum
# ==============================================================================

@pytest.mark.django_db
def test_pas_trial_collaboration_lock_and_unlock(client, school):
    s = school
    rekan_baru = _question(s.rekan, s.subject, 'rekan2', 'C')
    # Mapel produktif diampu dua guru di 10 Uji (ketentuan.md: soal dibagi antar guru di kelas yang sama)
    TeacherAssignment.objects.create(teacher=s.rekan, subject=s.subject, class_room=s.uji)

    # 1. Admin membuat PAS jenjang 10. Kelas dikelompokkan per himpunan guru:
    #    10 Uji {gumelar, rekan} dan 10 RPL 1 {rekan} menjadi dua paket terpisah
    client.force_login(s.admin)
    _create_schedule(client, s, exam_type='PAS', sub_type='PAS Ganjil', title='UJI COBA PAS', class_room='',
                     target_question_count=4, token='PAS001', start_time=_start_in(300))
    assert Exam.objects.count() == 2
    exam = Exam.objects.filter(schedules__class_room=s.uji).distinct().get()
    quota = dict(Schedule.objects.filter(exam=exam).values_list('teacher__user__username', 'teacher_quota'))
    assert quota == {'gumelar': 2, 'rekan': 2}

    # 2. Paket baru diajukan setelah kedua guru memenuhi kuota
    client.force_login(s.guru_user)
    _pick_questions(client, exam, s.lama)
    exam.refresh_from_db()
    assert exam.status == 'pending_selection'
    client.force_login(s.rekan_user)
    _pick_questions(client, exam, [s.soal_rekan, rekan_baru])
    exam.refresh_from_db()
    assert exam.status == 'waiting_validation'

    client.force_login(s.admin)
    client.post(reverse('schedules:action', kwargs={'pk': exam.schedules.first().id, 'action': 'verify'}), **HX)
    exam.refresh_from_db()
    assert exam.status == 'validated'
    for sch in exam.schedules.all():
        _open_now(sch)
    schedule = exam.schedules.get(teacher=s.guru)

    # 3. Siswa 10 Uji mengerjakan; pindah tab dua kali mengunci sesi
    client.force_login(s.siswa1.user)
    available = client.get(reverse('exam_engine:student_dashboard')).context['available_exams']
    assert len(available) == 1
    target = available[0]['schedule']
    _, sesi = _start_exam(client, s.siswa1, target, 'PAS001')
    assert sesi is not None
    soal = [eq.question for eq in ExamQuestion.objects.filter(exam=exam).select_related('question')]
    assert len(soal) == 4
    _answer(client, sesi, soal[0], soal[0].correct_answer)
    for _ in range(2):
        client.post(reverse('exam_engine:violation_handler', args=[sesi.id]), **HX)
    sesi.refresh_from_db()
    assert sesi.status == 'locked'

    # 4. Selama terkunci jawaban tidak tersimpan
    _answer(client, sesi, soal[1], soal[1].correct_answer)
    assert StudentAnswer.objects.get(session=sesi, question=soal[1]).chosen_answer is None

    # 5. Guru tidak bisa membuka kunci; kurikulum bisa dengan alasan wajib, dan tercatat
    client.force_login(s.guru_user)
    assert client.post(reverse('reports:session_unlock', args=[sesi.id]), {'reason': 'coba'}, **HX).status_code == 403
    client.force_login(s.kurikulum)
    client.post(reverse('reports:session_unlock', args=[sesi.id]), {'reason': ' '}, **HX)
    sesi.refresh_from_db()
    assert sesi.status == 'locked'
    client.post(reverse('reports:session_unlock', args=[sesi.id]), {'reason': 'Sudah dibina kurikulum'}, **HX)
    sesi.refresh_from_db()
    assert (sesi.status, sesi.violation_count) == ('active', 2)
    log = SessionActionLog.objects.get(session_id_snapshot=sesi.id)
    assert (log.action, log.reason, log.previous_status) == ('unlock', 'Sudah dibina kurikulum', 'locked')

    # 6. Jawaban sebelum terkunci tetap ada; siswa melanjutkan dan selesai
    client.force_login(s.siswa1.user)
    assert StudentAnswer.objects.get(session=sesi, question=soal[0]).chosen_answer == soal[0].correct_answer
    for q in soal[1:]:
        _answer(client, sesi, q, q.correct_answer)
    client.post(reverse('exam_engine:finish_exam', args=[sesi.id]), **HX)
    sesi.refresh_from_db()
    assert (sesi.status, sesi.score) == ('finished', 100)

    # 7. Rekap gumelar hanya memuat kelas yang ia ampu
    client.force_login(s.guru_user)
    nis = {p['nis'] for p in client.get(reverse('reports:exam_results_detail', args=[exam.id])).context['participants']}
    assert nis == {'9999000001', '9999000002'}


@pytest.mark.django_db
def test_logout_without_sso_token_returns_to_login(client, school):
    client.force_login(school.siswa1.user)
    res = client.get(reverse('accounts:logout'))
    assert res.status_code == 302
    assert '_auth_user_id' not in client.session

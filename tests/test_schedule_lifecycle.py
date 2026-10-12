"""Alur status paket ujian (Bagian A audit Jadwal Ujian).

Aturan bisnis dari ketentuan.md dan keputusan audit 2026-10-12:
- UH: guru simpan soal lengkap -> langsung validated, tanpa verifikasi admin.
- PTS/PAS/PAT/SAJ: simpan lengkap -> waiting_validation -> admin verifikasi.
- Admin boleh mengembalikan naskah ke guru dengan alasan wajib.
- Guru boleh menarik pengajuan selama belum diverifikasi.
- Buka kunci naskah tervalidasi: admin (semua jenis) atau guru pemilik (UH),
  alasan wajib, dan hanya selama belum ada siswa yang mulai mengerjakan.
- Paket kolaboratif baru diajukan setelah kuota semua guru terpenuhi.
- Token diperbarui serentak di semua jadwal dalam satu paket.
"""
import json
from datetime import timedelta

import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone

from apps.accounts.models import Role
from apps.exam_engine.models import ExamSession
from apps.master_data.models import Student, Subject, Teacher
from apps.questions.models import Question
from apps.schedules.models import Exam, ExamQuestion, Schedule
from apps.schedules.utils import can_transition_status

User = get_user_model()


def _guru(username):
    user = User.objects.create_user(username=username, email=f'{username}@smkn1rongga.sch.id', role=Role.GURU, password='pw')
    teacher = Teacher.objects.create(user=user, full_name=f'Guru {username}', email=user.email)
    return user, teacher


def _admin(username='admin_lc'):
    return User.objects.create_user(username=username, email=f'{username}@test.com', role=Role.ADMIN, password='pw')


def _exam(teacher, exam_type='UH', status='pending_selection', target=2, subject=None):
    subject = subject or Subject.objects.create(name=f'Mapel {exam_type} {status}')
    return Exam.objects.create(
        teacher=teacher, subject=subject, title=f'{exam_type} Uji', exam_type=exam_type,
        target_question_count=target, level=10, status=status, token='TKN001',
    )


def _schedule(exam, teacher, quota=0, start_offset=-5, end_offset=60):
    now = timezone.now()
    return Schedule.objects.create(
        exam=exam, teacher=teacher,
        start_time=now + timedelta(minutes=start_offset),
        end_time=now + timedelta(minutes=end_offset),
        token=exam.token or 'TKN001', teacher_quota=quota,
    )


def _add_questions(exam, author, n):
    for i in range(n):
        q = Question.objects.create(subject=exam.subject, level=exam.level, created_by=author,
                                    question_text=f'Soal {author.full_name} {i}', correct_answer='A')
        ExamQuestion.objects.create(exam=exam, question=q, order_number=exam.exam_questions.count() + 1)


def _start_session(schedule):
    user = User.objects.create_user(username=f'siswa_{schedule.id.hex[:6]}', role=Role.SISWA)
    student = Student.objects.create(user=user, nis=schedule.id.hex[:10], full_name='Siswa Uji')
    return ExamSession.objects.create(student=student, schedule=schedule)


def _action(client, schedule, action, data=None):
    return client.post(
        reverse('schedules:action', kwargs={'pk': schedule.id, 'action': action}),
        data or {}, HTTP_HX_REQUEST='true',
    )


# ==============================================================================
# Model & aturan transisi murni
# ==============================================================================

def test_exam_status_choices_only_three_lifecycle_states():
    assert [c[0] for c in Exam.STATUS_CHOICES] == ['pending_selection', 'waiting_validation', 'validated']


def test_can_transition_status_table():
    # Admin
    assert can_transition_status('admin', 'PAS', 'waiting_validation', 'validated')
    assert can_transition_status('kurikulum', 'PTS', 'waiting_validation', 'pending_selection')
    assert can_transition_status('admin', 'SAJ', 'validated', 'pending_selection')
    assert can_transition_status('admin', 'UH', 'validated', 'pending_selection')
    # Guru
    assert can_transition_status('guru', 'UH', 'pending_selection', 'validated')
    assert can_transition_status('guru', 'PTS', 'pending_selection', 'waiting_validation')
    assert can_transition_status('guru', 'PAS', 'waiting_validation', 'pending_selection')
    assert can_transition_status('guru', 'UH', 'validated', 'pending_selection')
    # Ditolak
    assert not can_transition_status('guru', 'PTS', 'waiting_validation', 'validated')
    assert not can_transition_status('guru', 'PAS', 'validated', 'pending_selection')
    assert not can_transition_status('guru', 'UH', 'pending_selection', 'waiting_validation')
    assert not can_transition_status('guru', 'PTS', 'pending_selection', 'validated')
    assert not can_transition_status('admin', 'PAS', 'pending_selection', 'validated')


@pytest.mark.django_db
def test_schedule_phase_follows_exam_status_and_time():
    _, t = _guru('phase')
    exam = _exam(t, status='pending_selection')
    s = _schedule(exam, t, start_offset=30, end_offset=90)
    assert s.phase == 'pending_selection'

    exam.status = 'waiting_validation'
    exam.save()
    s.refresh_from_db()
    assert s.phase == 'waiting_validation'

    exam.status = 'validated'
    exam.save()
    s.refresh_from_db()
    assert s.phase == 'scheduled'

    s.start_time = timezone.now() - timedelta(minutes=5)
    s.save()
    assert s.phase == 'running'

    s.end_time = timezone.now() - timedelta(minutes=1)
    s.save()
    assert s.phase == 'finished'

    exam.status = 'pending_selection'
    exam.save()
    s.refresh_from_db()
    assert s.phase == 'missed'


# ==============================================================================
# Pengajuan naskah
# ==============================================================================

@pytest.mark.django_db
def test_save_questions_on_locked_exam_does_not_downgrade_status(client):
    user, t = _guru('locked_save')
    exam = _exam(t, exam_type='PTS', status='validated', target=2)
    _schedule(exam, t, quota=2)
    _add_questions(exam, t, 2)
    client.force_login(user)

    client.post(reverse('schedules:save_questions', kwargs={'exam_id': exam.id}))

    exam.refresh_from_db()
    assert exam.status == 'validated'


@pytest.mark.django_db
def test_collaborative_exam_waits_until_every_teacher_quota_met(client):
    user_a, t_a = _guru('collab_a')
    _, t_b = _guru('collab_b')
    exam = _exam(t_a, exam_type='PAS', target=4)
    _schedule(exam, t_a, quota=2)
    _schedule(exam, t_b, quota=2)
    # Guru A mengisi 4 soal sendirian: total penuh, kuota guru B belum terpenuhi
    _add_questions(exam, t_a, 4)
    client.force_login(user_a)

    client.post(reverse('schedules:save_questions', kwargs={'exam_id': exam.id}))
    exam.refresh_from_db()
    assert exam.status == 'pending_selection'


@pytest.mark.django_db
def test_collaborative_exam_submits_when_all_quotas_met(client):
    user_a, t_a = _guru('collab_ok_a')
    _, t_b = _guru('collab_ok_b')
    exam = _exam(t_a, exam_type='PAS', target=4)
    _schedule(exam, t_a, quota=2)
    _schedule(exam, t_b, quota=2)
    _add_questions(exam, t_a, 2)
    _add_questions(exam, t_b, 2)
    client.force_login(user_a)

    client.post(reverse('schedules:save_questions', kwargs={'exam_id': exam.id}))
    exam.refresh_from_db()
    assert exam.status == 'waiting_validation'


@pytest.mark.django_db
def test_toggle_question_blocked_when_exam_locked(client):
    user, t = _guru('toggle_lock')
    exam = _exam(t, status='validated', target=3)
    _schedule(exam, t)
    q = Question.objects.create(subject=exam.subject, level=10, created_by=t, question_text='Soal baru', correct_answer='A')
    client.force_login(user)

    res = client.post(reverse('schedules:toggle_question', kwargs={'exam_id': exam.id, 'question_id': q.id}),
                      {'idx': '1'}, HTTP_HX_REQUEST='true')

    assert res.status_code == 409
    assert not ExamQuestion.objects.filter(exam=exam, question=q).exists()


@pytest.mark.django_db
def test_toggle_question_blocked_for_non_member_teacher(client):
    _, owner = _guru('toggle_owner')
    outsider_user, outsider = _guru('toggle_outsider')
    exam = _exam(owner, target=3)
    _schedule(exam, owner)
    q = Question.objects.create(subject=exam.subject, level=10, created_by=outsider, question_text='Soal luar', correct_answer='A')
    client.force_login(outsider_user)

    res = client.post(reverse('schedules:toggle_question', kwargs={'exam_id': exam.id, 'question_id': q.id}),
                      {'idx': '1'}, HTTP_HX_REQUEST='true')

    assert res.status_code == 403
    assert not ExamQuestion.objects.filter(exam=exam).exists()


# ==============================================================================
# Tarik pengajuan, verifikasi, kembalikan
# ==============================================================================

@pytest.mark.django_db
def test_teacher_withdraws_waiting_submission(client):
    user, t = _guru('withdraw')
    exam = _exam(t, exam_type='PTS', status='waiting_validation')
    s = _schedule(exam, t)
    client.force_login(user)

    res = _action(client, s, 'withdraw')

    assert res.status_code == 200
    exam.refresh_from_db()
    assert exam.status == 'pending_selection'


@pytest.mark.django_db
def test_admin_verify_requires_complete_questions(client):
    _, t = _guru('verify_incomplete')
    exam = _exam(t, exam_type='PTS', status='waiting_validation', target=3)
    s = _schedule(exam, t, quota=3)
    _add_questions(exam, t, 1)
    client.force_login(_admin())

    res = _action(client, s, 'verify')

    assert res.status_code == 409
    exam.refresh_from_db()
    assert exam.status == 'waiting_validation'


@pytest.mark.django_db
def test_admin_reject_requires_reason_and_stores_note(client):
    _, t = _guru('reject')
    exam = _exam(t, exam_type='PAS', status='waiting_validation')
    s = _schedule(exam, t)
    admin = _admin()
    client.force_login(admin)

    empty = _action(client, s, 'reject', {'note': '   '})
    exam.refresh_from_db()
    assert empty.status_code == 200
    assert 'Alasan wajib diisi' in empty.content.decode()
    assert exam.status == 'waiting_validation'

    ok = _action(client, s, 'reject', {'note': 'Soal nomor 3 kunci jawabannya salah.'})
    exam.refresh_from_db()
    assert ok.status_code == 200
    assert ok.headers.get('HX-Retarget') == '#schedule-list-grid-container'
    assert exam.status == 'pending_selection'
    assert exam.review_note == 'Soal nomor 3 kunci jawabannya salah.'
    assert exam.reviewed_by == admin
    assert exam.reviewed_at is not None


@pytest.mark.django_db
def test_teacher_cannot_reject(client):
    user, t = _guru('reject_guru')
    exam = _exam(t, exam_type='PAS', status='waiting_validation')
    s = _schedule(exam, t)
    client.force_login(user)

    _action(client, s, 'reject', {'note': 'Coba tolak'})

    exam.refresh_from_db()
    assert exam.status == 'waiting_validation'


# ==============================================================================
# Buka kunci naskah
# ==============================================================================

@pytest.mark.django_db
def test_admin_unlocks_official_exam_with_reason(client):
    _, t = _guru('unlock_admin')
    exam = _exam(t, exam_type='PAS', status='validated')
    s = _schedule(exam, t)
    client.force_login(_admin())

    res = _action(client, s, 'unlock', {'note': 'Gambar soal nomor 5 tidak tampil.'})

    assert res.status_code == 200
    exam.refresh_from_db()
    assert exam.status == 'pending_selection'
    assert exam.review_note == 'Gambar soal nomor 5 tidak tampil.'


@pytest.mark.django_db
def test_teacher_cannot_unlock_official_exam(client):
    user, t = _guru('unlock_guru_pas')
    exam = _exam(t, exam_type='PAS', status='validated')
    s = _schedule(exam, t)
    client.force_login(user)

    _action(client, s, 'unlock', {'note': 'Revisi'})

    exam.refresh_from_db()
    assert exam.status == 'validated'


@pytest.mark.django_db
def test_teacher_unlocks_own_uh_with_reason(client):
    user, t = _guru('unlock_uh')
    exam = _exam(t, exam_type='UH', status='validated')
    s = _schedule(exam, t)
    client.force_login(user)

    res = _action(client, s, 'unlock', {'note': 'Tambah soal bab 2.'})

    assert res.status_code == 200
    exam.refresh_from_db()
    assert exam.status == 'pending_selection'


@pytest.mark.django_db
def test_teacher_cannot_unlock_other_teachers_uh(client):
    _, owner = _guru('unlock_owner')
    other_user, _ = _guru('unlock_other')
    exam = _exam(owner, exam_type='UH', status='validated')
    s = _schedule(exam, owner)
    client.force_login(other_user)

    _action(client, s, 'unlock', {'note': 'Bukan milik saya'})

    exam.refresh_from_db()
    assert exam.status == 'validated'


@pytest.mark.django_db
@pytest.mark.parametrize('exam_type', ['UH', 'PAS'])
def test_unlock_refused_after_student_started(client, exam_type):
    user, t = _guru(f'unlock_started_{exam_type.lower()}')
    exam = _exam(t, exam_type=exam_type, status='validated')
    s = _schedule(exam, t)
    _start_session(s)
    client.force_login(_admin(f'admin_started_{exam_type.lower()}') if exam_type == 'PAS' else user)

    res = _action(client, s, 'unlock', {'note': 'Revisi soal'})

    exam.refresh_from_db()
    assert exam.status == 'validated'
    assert '1 siswa sudah mulai mengerjakan' in res.content.decode()


@pytest.mark.django_db
def test_unlock_requires_reason(client):
    user, t = _guru('unlock_noreason')
    exam = _exam(t, exam_type='UH', status='validated')
    s = _schedule(exam, t)
    client.force_login(user)

    res = _action(client, s, 'unlock', {'note': ''})

    exam.refresh_from_db()
    assert exam.status == 'validated'
    assert 'Alasan wajib diisi' in res.content.decode()


@pytest.mark.django_db
def test_unlock_modal_renders_for_allowed_user(client):
    user, t = _guru('unlock_modal')
    exam = _exam(t, exam_type='UH', status='validated')
    s = _schedule(exam, t)
    client.force_login(user)

    res = client.get(reverse('schedules:action', kwargs={'pk': s.id, 'action': 'unlock'}), HTTP_HX_REQUEST='true')

    assert res.status_code == 200
    body = res.content.decode()
    assert 'Buka Kunci Naskah' in body
    assert 'name="note"' in body


# ==============================================================================
# Token
# ==============================================================================

@pytest.mark.django_db
def test_regenerate_token_updates_every_schedule_in_exam(client):
    _, t_a = _guru('token_a')
    _, t_b = _guru('token_b')
    exam = _exam(t_a, exam_type='PAS', status='validated')
    s_a = _schedule(exam, t_a)
    s_b = _schedule(exam, t_b)
    client.force_login(_admin())

    res = _action(client, s_a, 'regenerate-token')

    assert res.status_code == 200
    exam.refresh_from_db()
    s_a.refresh_from_db()
    s_b.refresh_from_db()
    assert exam.token != 'TKN001'
    assert s_a.token == s_b.token == exam.token


@pytest.mark.django_db
def test_teacher_cannot_regenerate_official_exam_token(client):
    user, t = _guru('token_guru_pas')
    exam = _exam(t, exam_type='PAS', status='validated')
    s = _schedule(exam, t)
    client.force_login(user)

    res = _action(client, s, 'regenerate-token')

    s.refresh_from_db()
    assert res.status_code == 403
    assert s.token == 'TKN001'


@pytest.mark.django_db
def test_teacher_regenerates_own_uh_token(client):
    user, t = _guru('token_guru_uh')
    exam = _exam(t, exam_type='UH', status='validated')
    s = _schedule(exam, t)
    client.force_login(user)

    res = _action(client, s, 'regenerate-token')

    s.refresh_from_db()
    assert res.status_code == 200
    assert s.token != 'TKN001'


@pytest.mark.django_db
def test_pengawas_regenerates_official_exam_token(client):
    _, t = _guru('token_pengawas_owner')
    pengawas = User.objects.create_user(username='pengawas_lc', role=Role.PENGAWAS, password='pw')
    exam = _exam(t, exam_type='PAS', status='validated')
    s = _schedule(exam, t)
    client.force_login(pengawas)

    res = _action(client, s, 'regenerate-token')

    s.refresh_from_db()
    assert res.status_code == 200
    assert s.token != 'TKN001'


@pytest.mark.django_db
def test_action_error_sends_toast_trigger(client):
    user, t = _guru('toast_err')
    exam = _exam(t, exam_type='PAS', status='validated')
    s = _schedule(exam, t)
    client.force_login(user)

    res = _action(client, s, 'regenerate-token')

    trigger = json.loads(res.headers['HX-Trigger'])
    assert trigger['showToast']['level'] == 'error'
    assert res.headers.get('HX-Reswap') == 'none'


# ==============================================================================
# Gerbang token siswa
# ==============================================================================

@pytest.mark.django_db
@pytest.mark.parametrize('status', ['pending_selection', 'waiting_validation'])
def test_confirm_token_rejects_unvalidated_exam(client, status):
    _, t = _guru(f'gate_{status}')
    exam = _exam(t, status=status)
    s = _schedule(exam, t)
    from apps.master_data.models import ClassRoom
    gate_class = ClassRoom.objects.create(name=f'X GATE {status}', level=10)
    Schedule.objects.filter(pk=s.pk).update(class_room=gate_class)
    student_user = User.objects.create_user(username=f'siswa_gate_{status}', role=Role.SISWA)
    Student.objects.create(user=student_user, nis=f'99{len(status)}', full_name='Siswa Gerbang', class_room=gate_class)
    client.force_login(student_user)

    res = client.post(reverse('exam_engine:confirm_token'),
                      {'schedule_id': str(s.id), 'token': 'TKN001'}, HTTP_HX_REQUEST='true')

    assert res.status_code == 200
    assert 'belum diverifikasi' in res.content.decode()
    assert not ExamSession.objects.filter(schedule=s).exists()


# ==============================================================================
# Filter fase daftar jadwal & dashboard
# ==============================================================================

@pytest.mark.django_db
def test_schedule_list_status_filter_uses_phase(client):
    _, t = _guru('filter_phase')
    running = _schedule(_exam(t, status='validated'), t)
    finished = _schedule(_exam(t, exam_type='PTS', status='validated'), t, start_offset=-120, end_offset=-60)
    draft = _schedule(_exam(t, exam_type='PAS', status='pending_selection'), t, start_offset=60, end_offset=120)
    client.force_login(_admin())

    def ids(status):
        res = client.get(reverse('schedules:list'), {'status': status, 'date_filter': 'Semua Ujian'}, HTTP_HX_REQUEST='true')
        return {s.id for s in res.context['schedules']}

    assert ids('aktif') == {running.id}
    assert ids('selesai') == {finished.id}
    assert ids('draft') == {draft.id}


# ==============================================================================
# Render kartu jadwal & dashboard
# ==============================================================================

def _list_html(client):
    res = client.get(reverse('schedules:list'), {'date_filter': 'Semua Ujian'})
    assert res.status_code == 200
    return res.content.decode()


@pytest.mark.django_db
def test_card_shows_verify_and_reject_for_admin_on_waiting_exam(client):
    _, t = _guru('card_admin')
    _schedule(_exam(t, exam_type='PAS', status='waiting_validation'), t)
    client.force_login(_admin())

    html = _list_html(client)

    assert 'Verifikasi Naskah' in html
    assert 'Kembalikan ke Guru' in html
    assert 'Tarik Pengajuan' not in html


@pytest.mark.django_db
def test_card_shows_withdraw_and_review_note_for_teacher(client):
    user, t = _guru('card_teacher')
    exam = _exam(t, exam_type='PTS', status='waiting_validation')
    _schedule(exam, t)
    client.force_login(user)

    assert 'Tarik Pengajuan' in _list_html(client)

    exam.status = 'pending_selection'
    exam.review_note = 'Opsi E soal nomor 4 kosong.'
    exam.save()
    html = _list_html(client)
    assert 'Opsi E soal nomor 4 kosong.' in html
    assert 'Pilih Soal' in html


@pytest.mark.django_db
def test_card_unlock_button_explains_block_when_students_started(client):
    user, t = _guru('card_unlock_block')
    exam = _exam(t, exam_type='UH', status='validated')
    s = _schedule(exam, t)
    _start_session(s)
    client.force_login(user)

    html = _list_html(client)

    assert 'aria-disabled="true"' in html
    assert 'Tidak bisa dibuka: 1 siswa sudah mulai mengerjakan.' in html


@pytest.mark.django_db
def test_dashboard_active_count_uses_running_phase(client):
    from django.core.cache import cache
    cache.clear()
    _, t = _guru('dash_count')
    _schedule(_exam(t, status='validated'), t)
    _schedule(_exam(t, exam_type='PTS', status='pending_selection'), t)
    _schedule(_exam(t, exam_type='PAS', status='validated'), t, start_offset=60, end_offset=120)
    client.force_login(_admin('admin_dash'))

    res = client.get('/dashboard/')

    assert res.context['active_schedules_count'] == 1


@pytest.mark.django_db
def test_modal_success_closes_modal_after_settle_not_before_swap(client):
    # closeModal yang dikirim di HX-Trigger menghapus form sebelum htmx sempat
    # men-swap grid, sehingga grid dan toast tidak pernah tampil.
    _, t = _guru('modal_settle')
    exam = _exam(t, exam_type='PAS', status='waiting_validation')
    s = _schedule(exam, t)
    client.force_login(_admin('admin_settle'))

    res = _action(client, s, 'reject', {'note': 'Perbaiki soal nomor 1.'})

    assert 'closeModal' not in json.loads(res.headers.get('HX-Trigger', '{}'))
    assert json.loads(res.headers['HX-Trigger-After-Settle'])['closeModal'] is True
    assert json.loads(res.headers['HX-Trigger'])['showToast']['level'] == 'success'

import secrets
from datetime import datetime, timedelta
from django.utils import timezone


TOKEN_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"


def generate_exam_token(length=6):
    """
    Menghasilkan token alfanumerik acak sepanjang `length` karakter (default 6),
    tanpa karakter ambigu (mengecualikan 0, O, 1, I).
    """
    return "".join(secrets.choice(TOKEN_ALPHABET) for _ in range(length))


def resolve_exam_title(exam_type, title='', sub_type=''):
    """
    Menentukan judul resmi paket ujian berdasarkan tipe dan sub-tipe asesmen.
    """
    norm_type = str(exam_type or '').strip().upper()
    if norm_type == 'SAJ':
        return 'Asesmen Sumatif Akhir Jenjang'
    if norm_type in ['PTS', 'PAS', 'PAT', 'PAS/PAT']:
        return sub_type if sub_type else title
    return title


def build_schedule_date_range(start_time_val, duration_minutes=60):
    """
    Membuat range waktu start_time dan end_time berbasis timezone Jakarta.
    Mendukung datetime object atau string format ISO / 'YYYY-MM-DDTHH:MM'.
    """
    if not start_time_val:
        start_dt = timezone.now()
    elif isinstance(start_time_val, datetime):
        if timezone.is_naive(start_time_val):
            start_dt = timezone.make_aware(start_time_val, timezone.get_current_timezone())
        else:
            start_dt = start_time_val
    else:
        # String parsing
        cleaned_str = str(start_time_val).replace(' ', 'T')[:16]
        try:
            naive_dt = datetime.strptime(cleaned_str, '%Y-%m-%dT%H:%M')
            start_dt = timezone.make_aware(naive_dt, timezone.get_current_timezone())
        except ValueError:
            start_dt = timezone.now()

    duration = int(duration_minutes) if duration_minutes else 60
    end_dt = start_dt + timedelta(minutes=duration)
    return start_dt, end_dt


def resolve_status_after_question_save(exam_type, is_full):
    """
    Menentukan status paket ujian setelah aksi simpan butir soal:
    - UH Express: jika butir soal sudah genap target -> langsung 'validated'.
    - PTS/PAS/PAT/SAJ: jika butir soal lengkap -> 'waiting_validation' (menunggu approval admin).
    - Jika belum lengkap -> tetap 'pending_selection'.
    """
    if not is_full:
        return 'pending_selection'
    norm_type = str(exam_type or '').strip().upper()
    if norm_type == 'UH':
        return 'validated'
    return 'waiting_validation'


def can_transition_status(role, exam_type, from_status, to_status):
    """
    Validasi izin transisi status ujian:
    - Admin dapat memverifikasi dari 'waiting_validation' -> 'validated' / 'ready'.
    - Guru dapat membuka kunci ujian UH dari 'validated'/'ready' -> 'pending_selection'.
    """
    norm_role = str(role or '').lower()
    norm_type = str(exam_type or '').upper()
    norm_from = str(from_status or '').lower()
    norm_to = str(to_status or '').lower()

    if norm_role in ['admin', 'kurikulum', 'platform_admin', 'data_admin']:
        if norm_from == 'waiting_validation' and norm_to in ['validated', 'ready']:
            return True

    if norm_role == 'guru' and norm_type == 'UH':
        if norm_from in ['validated', 'ready'] and norm_to == 'pending_selection':
            return True

    return False


def calculate_collaborative_quotas(teachers_list, total_target_questions):
    """
    Membagi kuota target butir soal secara merata ke daftar guru kolaborator.
    Mengembalikan dict mapping: {teacher_id: quota_count}.
    """
    if not teachers_list:
        return {}
    num_teachers = len(teachers_list)
    total_target = int(total_target_questions) if total_target_questions else 40
    base_quota = total_target // num_teachers
    remainder = total_target % num_teachers

    quotas = {}
    for idx, t in enumerate(teachers_list):
        t_id = getattr(t, 'id', t) if not isinstance(t, (str, int)) else t
        quotas[str(t_id)] = base_quota + (1 if idx < remainder else 0)

    return quotas

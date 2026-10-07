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


def build_teacher_set_key(teacher_ids):
    """
    Membuat string kunci unik deterministik dari daftar guru (misal: 'id1|id2').
    Source of truth: ketentuan.md & legacy teacherSetKey.js
    """
    if not teacher_ids:
        return ""
    cleaned = sorted([str(getattr(t, 'id', t)) for t in teacher_ids if t])
    return "|".join(cleaned)


def build_teacher_set_groups(assignments):
    """
    Mengelompokkan kelas-kelas berdasarkan kesamaan himpunan guru pengampu
    pada mata pelajaran dan jenjang yang bersangkutan.
    Source of truth: ketentuan.md & legacy scheduleGrouping.js
    
    Output list of dict:
    [
        {
            'teacher_ids': [sorted_teacher_ids],
            'teachers': [Teacher objects],
            'class_ids': [class_ids],
            'classes': [ClassRoom objects],
        },
        ...
    ]
    """
    if not assignments:
        return []

    teachers_by_class = {}  # class_id -> set of teacher_id
    teachers_map = {}       # teacher_id -> Teacher object
    classes_map = {}        # class_id -> ClassRoom object

    for a in assignments:
        c_id = str(getattr(a, 'class_room_id', None) or getattr(getattr(a, 'class_room', None), 'id', ''))
        t_id = str(getattr(a, 'teacher_id', None) or getattr(getattr(a, 'teacher', None), 'id', ''))
        if not c_id or not t_id:
            continue

        if c_id not in teachers_by_class:
            teachers_by_class[c_id] = set()
        teachers_by_class[c_id].add(t_id)

        teacher_obj = getattr(a, 'teacher', None)
        if teacher_obj and t_id not in teachers_map:
            teachers_map[t_id] = teacher_obj
            
        class_obj = getattr(a, 'class_room', None)
        if class_obj and c_id not in classes_map:
            classes_map[c_id] = class_obj

    group_map = {}
    for c_id, teacher_set in teachers_by_class.items():
        sorted_t_ids = sorted(list(teacher_set))
        key = "|".join(sorted_t_ids)
        if key not in group_map:
            group_map[key] = {
                'teacher_ids': sorted_t_ids,
                'teachers': [teachers_map[tid] for tid in sorted_t_ids if tid in teachers_map],
                'class_ids': [],
                'classes': []
            }
        group_map[key]['class_ids'].append(c_id)
        if c_id in classes_map and classes_map[c_id] not in group_map[key]['classes']:
            group_map[key]['classes'].append(classes_map[c_id])

    return list(group_map.values())


def build_teacher_quota_map(assignments, total_target=40):
    """
    Menghitung kuota soal per guru berdasarkan jumlah guru maksimum per kelas
    (untuk mapel produktif/team teaching di rombel yang sama).
    Source of truth: ketentuan.md & legacy scheduleQuota.js
    """
    if not assignments:
        return {}

    total_target = int(total_target) if total_target else 40
    class_teachers = {}   # class_id -> set of teacher_id
    teacher_classes = {}  # teacher_id -> set of class_id

    for a in assignments:
        c_id = str(getattr(a, 'class_room_id', None) or getattr(getattr(a, 'class_room', None), 'id', ''))
        t_id = str(getattr(a, 'teacher_id', None) or getattr(getattr(a, 'teacher', None), 'id', ''))
        if not c_id or not t_id:
            continue

        if c_id not in class_teachers:
            class_teachers[c_id] = set()
        class_teachers[c_id].add(t_id)

        if t_id not in teacher_classes:
            teacher_classes[t_id] = set()
        teacher_classes[t_id].add(c_id)

    teacher_max_count = {}
    for t_id, class_set in teacher_classes.items():
        max_count = 1
        for c_id in class_set:
            count = len(class_teachers.get(c_id, set())) or 1
            if count > max_count:
                max_count = count
        teacher_max_count[t_id] = max_count

    quota_map = {}
    grouped = {}  # max_count -> list of teacher_id
    for t_id, max_count in teacher_max_count.items():
        if max_count not in grouped:
            grouped[max_count] = []
        grouped[max_count].append(t_id)

    for max_count, teacher_ids in grouped.items():
        base_quota = total_target // max_count
        remainder = total_target % max_count
        for index, t_id in enumerate(sorted(teacher_ids)):
            quota_map[t_id] = base_quota + (1 if index < remainder else 0)

    return quota_map

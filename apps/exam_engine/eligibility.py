"""
Siapa boleh mengerjakan jadwal apa. Satu sumber aturan untuk dashboard siswa dan gerbang token,
supaya jadwal yang tidak tampil di dashboard juga tidak bisa dimasuki lewat token.

Aturan (ketentuan.md): siswa hanya mengerjakan ujian kelasnya dan dari guru yang mengajar kelasnya.
"""
from apps.master_data.models import TeacherAssignment
from apps.schedules.models import Schedule

COLLABORATIVE_TYPES = {'PAS', 'PAT', 'SAJ', 'PAS/PAT'}


def student_block_reason(student):
    """Alasan siswa tidak bisa ujian sama sekali, atau None."""
    if student is None:
        return "Akun ini bukan akun siswa, jadi tidak bisa mengerjakan ujian."
    if (student.status or '').lower() != 'aktif':
        return "Status siswa Anda tidak aktif. Hubungi bagian kurikulum."
    if not student.class_room_id:
        return "Anda belum terdaftar di kelas mana pun. Hubungi bagian kurikulum."
    return None


def _teachers_of_class(student):
    """{subject_id: {teacher_id}} untuk kelas siswa."""
    mapping = {}
    for subject_id, teacher_id in TeacherAssignment.objects.filter(
        class_room_id=student.class_room_id
    ).values_list('subject_id', 'teacher_id'):
        if teacher_id:
            mapping.setdefault(subject_id, set()).add(teacher_id)
    return mapping


def eligible_schedules_for(student):
    """
    Jadwal terverifikasi yang boleh dikerjakan siswa, satu per paket ujian.
    Bila siswa sudah punya sesi di salah satu jadwal paket, jadwal itulah yang dipakai.
    """
    if student_block_reason(student):
        return []

    candidates = list(
        Schedule.objects.filter(status='active', exam__status='validated')
        .select_related('exam', 'exam__subject', 'exam__teacher', 'class_room', 'teacher')
        .order_by('start_time')
    )
    level = student.class_room.level
    class_teachers = _teachers_of_class(student)

    teachers_by_exam = {}
    for sch in candidates:
        if sch.teacher_id:
            teachers_by_exam.setdefault(sch.exam_id, set()).add(sch.teacher_id)

    eligible_by_exam = {}
    for sch in candidates:
        if sch.class_room_id:
            # Jadwal untuk satu rombel: hanya rombel itu
            ok = sch.class_room_id == student.class_room_id
        else:
            # Jadwal gabungan lama tanpa rombel: jenjang sama dan guru paket persis guru mapel kelas ini
            subject_teachers = class_teachers.get(sch.exam.subject_id, set())
            if sch.exam.level != level or not subject_teachers:
                ok = False
            elif sch.exam.exam_type in COLLABORATIVE_TYPES:
                ok = teachers_by_exam.get(sch.exam_id, set()) == subject_teachers
            else:
                ok = sch.teacher_id in subject_teachers
        if ok:
            eligible_by_exam.setdefault(sch.exam_id, []).append(sch)

    from apps.exam_engine.models import ExamSession
    started = set(
        ExamSession.objects.filter(student=student, schedule__exam_id__in=eligible_by_exam.keys())
        .values_list('schedule_id', flat=True)
    )
    result = []
    for schedules in eligible_by_exam.values():
        chosen = next((s for s in schedules if s.id in started), schedules[0])
        result.append(chosen)
    result.sort(key=lambda s: s.start_time)
    return result

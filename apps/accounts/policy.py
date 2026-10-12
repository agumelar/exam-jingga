"""
Kebijakan peran terpusat. Dipakai view di server dan sidebar, supaya menu yang tampil
selalu sama dengan yang diizinkan server.

Peran: admin/kurikulum (dan platform/data admin) mengelola semua; guru hanya paket ujian
yang ia buat atau ikut ampu; siswa hanya lewat mesin ujian. Sekolah tidak memakai peran pengawas.
"""
from django.db.models import Q

from apps.accounts.models import Role

SCHOOL_ADMIN_ROLES = {Role.ADMIN, Role.KURIKULUM, Role.PLATFORM_ADMIN, Role.DATA_ADMIN}


def _role(user):
    return str(getattr(user, 'role', '') or '').lower()


def is_school_admin(user):
    """Admin, kurikulum, platform/data admin, atau superuser."""
    if not user or not user.is_authenticated:
        return False
    return bool(user.is_superuser) or _role(user) in SCHOOL_ADMIN_ROLES


def is_teacher(user):
    return bool(user and user.is_authenticated) and _role(user) == Role.GURU


def is_staff_area_user(user):
    """Boleh membuka area staf (dashboard, bank soal, jadwal, laporan miliknya)."""
    return is_school_admin(user) or is_teacher(user)


def can_manage_sessions(user):
    """Buka kunci, reset, dan paksa selesai sesi siswa: hanya admin/kurikulum (SOP pembinaan)."""
    return is_school_admin(user)


def teacher_of(user):
    """Profil Teacher milik akun, atau None."""
    if not user or not user.is_authenticated:
        return None
    from apps.master_data.models import Teacher
    teacher = getattr(user, 'teacher_profile', None)
    return teacher or Teacher.objects.filter(user=user).first()


def exams_visible_to(user):
    """Paket ujian yang boleh dilihat hasil dan monitoringnya. Guru tanpa profil tidak melihat apa pun."""
    from apps.schedules.models import Exam
    qs = Exam.objects.all()
    if is_school_admin(user):
        return qs
    teacher = teacher_of(user) if is_teacher(user) else None
    if teacher is None:
        return qs.none()
    return qs.filter(Q(teacher=teacher) | Q(schedules__teacher=teacher)).distinct()


def schedules_visible_to(user):
    from apps.schedules.models import Schedule
    qs = Schedule.objects.all()
    if is_school_admin(user):
        return qs
    teacher = teacher_of(user) if is_teacher(user) else None
    if teacher is None:
        return qs.none()
    return qs.filter(Q(teacher=teacher) | Q(exam__teacher=teacher))


def nav_permissions(request):
    """Context processor: flag menu sidebar dari kebijakan yang sama dengan server."""
    user = getattr(request, 'user', None)
    return {
        'nav': {
            'is_school_admin': is_school_admin(user),
            'is_staff_area': is_staff_area_user(user),
            'can_manage_sessions': can_manage_sessions(user),
        }
    }

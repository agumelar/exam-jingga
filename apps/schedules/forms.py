from datetime import timedelta

from django import forms
from django.db import transaction
from django.utils import timezone

from apps.master_data.models import ClassRoom, Subject, Teacher, TeacherAssignment
from apps.schedules.models import Exam, Schedule, ScheduleTimeChange
from apps.schedules.utils import (
    build_teacher_quota_map,
    build_teacher_set_groups,
    calculate_collaborative_quotas,
    generate_exam_token,
    resolve_exam_title,
)

COLLABORATIVE_TYPES = {'PAS', 'PAT', 'SAJ'}
SESSION_CHOICES = [(0, 'Semua Sesi'), (1, 'Sesi 1'), (2, 'Sesi 2'), (3, 'Sesi 3')]


class ScheduleForm(forms.Form):
    """
    Membuat atau mengedit paket ujian beserta jadwalnya.

    - UH: dibuat guru untuk kelas yang ia ajar (atau admin atas nama guru pengampu kelas itu).
    - PTS: admin memilih mapel, guru pengampu, lalu kelas yang diajar guru tersebut. Satu guru, satu kelas.
    - PAS/PAT/SAJ: kolaboratif; kelas dikelompokkan menurut himpunan guru pengampu, kuota dibagi per guru.
    """
    exam_type = forms.ChoiceField(choices=Exam.EXAM_TYPE_CHOICES, initial='UH')
    title = forms.CharField(max_length=255, required=False)
    sub_type = forms.CharField(max_length=100, required=False)
    level = forms.TypedChoiceField(choices=Exam.LEVEL_CHOICES, coerce=int)
    subject = forms.ModelChoiceField(queryset=Subject.objects.all())
    class_room = forms.ModelChoiceField(queryset=ClassRoom.objects.all(), required=False)
    teacher = forms.ModelChoiceField(queryset=Teacher.objects.active(), required=False)
    start_time = forms.DateTimeField(input_formats=['%Y-%m-%dT%H:%M'])
    token = forms.CharField(max_length=10, required=False)
    duration = forms.IntegerField(initial=60, min_value=1, max_value=600)
    target_question_count = forms.IntegerField(initial=40, min_value=1, max_value=200)
    session_no = forms.TypedChoiceField(choices=SESSION_CHOICES, coerce=int, initial=0)

    def __init__(self, *args, user=None, schedule_instance=None, creator_teacher=None, is_admin=False, **kwargs):
        self.user = user
        self.schedule_instance = schedule_instance
        self.creator_teacher = creator_teacher
        self.is_admin = is_admin
        super().__init__(*args, **kwargs)
        if not is_admin:
            self.fields['exam_type'].choices = [('UH', 'Ulangan Harian')]
        if schedule_instance:
            exam = schedule_instance.exam
            self.initial.update({
                'exam_type': exam.exam_type,
                'title': exam.title,
                'level': exam.level,
                'subject': exam.subject_id,
                'class_room': schedule_instance.class_room_id,
                'teacher': schedule_instance.teacher_id,
                'duration': exam.duration,
                'target_question_count': exam.target_question_count,
                'token': schedule_instance.token,
                'session_no': schedule_instance.session_no,
                'start_time': timezone.localtime(schedule_instance.start_time).strftime('%Y-%m-%dT%H:%M'),
            })
        if not self.initial.get('token'):
            self.initial['token'] = generate_exam_token(6)

    # ------------------------------------------------------------------ helpers

    def form_values(self):
        """Nilai untuk template: data yang dikirim (saat error) atau nilai awal."""
        names = ['exam_type', 'title', 'sub_type', 'level', 'subject', 'class_room', 'teacher',
                 'start_time', 'token', 'duration', 'target_question_count', 'session_no']
        if self.is_bound:
            return {n: self.data.get(n, '') for n in names}
        return {n: ('' if self.initial.get(n) is None else self.initial.get(n)) for n in names}

    def _exam_teacher(self, cleaned):
        """Guru pemilik paket: guru yang login, atau pilihan admin (saat edit tanpa pilihan: guru jadwal ini)."""
        if not self.is_admin:
            return self.creator_teacher or (self.schedule_instance.teacher if self.schedule_instance else None)
        return cleaned.get('teacher') or (self.schedule_instance.teacher if self.schedule_instance else None)

    def _check_assignment(self, teacher, subject, class_room):
        if not TeacherAssignment.objects.filter(teacher=teacher, subject=subject, class_room=class_room).exists():
            self.add_error('class_room', f"{teacher.full_name} tidak mengajar {subject.name} di {class_room.name}.")

    def _collab_assignments(self, cleaned):
        return list(TeacherAssignment.objects.filter(
            subject=cleaned['subject'], class_room__level=cleaned['level']
        ).select_related('teacher', 'class_room'))

    # ------------------------------------------------------------------ validation

    def clean(self):
        cleaned = super().clean()
        exam_type = cleaned.get('exam_type')
        subject = cleaned.get('subject')
        level = cleaned.get('level')
        class_room = cleaned.get('class_room')
        if not exam_type or not subject or not level:
            return cleaned

        if not self.is_admin and exam_type != 'UH':
            self.add_error('exam_type', 'Guru hanya bisa menjadwalkan Ulangan Harian (UH).')
        if exam_type == 'UH' and not cleaned.get('title'):
            self.add_error('title', 'Nama ujian wajib diisi untuk Ulangan Harian.')
        if exam_type in ('PTS', 'PAS', 'PAT') and not cleaned.get('sub_type') and not self.schedule_instance:
            self.add_error('sub_type', 'Pilih semester ujian (menjadi judul paket).')

        if exam_type in ('UH', 'PTS'):
            if self.schedule_instance and not class_room:
                class_room = cleaned['class_room'] = self.schedule_instance.class_room
            if not class_room:
                self.add_error('class_room', 'Kelas wajib dipilih untuk UH dan PTS.')
            else:
                if class_room.level != level:
                    self.add_error('class_room', f"{class_room.name} bukan kelas jenjang {level}.")
                teacher = self._exam_teacher(cleaned)
                if teacher is None:
                    self.add_error('teacher', 'Guru pengampu wajib dipilih.' if self.is_admin else
                                   'Akun Anda belum terhubung ke data guru. Hubungi bagian kurikulum.')
                elif class_room.level == level:
                    self._check_assignment(teacher, subject, class_room)
        elif exam_type in COLLABORATIVE_TYPES:
            assignments = self._collab_assignments(cleaned)
            if not assignments:
                self.add_error('subject', f"Belum ada guru yang mengajar {subject.name} di jenjang {level}.")
            else:
                widest = max(len(g['teacher_ids']) for g in build_teacher_set_groups(assignments))
                target = cleaned.get('target_question_count') or 0
                if target < widest:
                    self.add_error('target_question_count',
                                   f"Target soal minimal {widest} agar setiap guru pengampu mendapat kuota.")

        start = cleaned.get('start_time')
        duration = cleaned.get('duration')
        if start and duration and class_room and exam_type in ('UH', 'PTS') and not self.errors:
            end = start + timedelta(minutes=duration)
            clash = Schedule.objects.filter(class_room=class_room, start_time__lt=end, end_time__gt=start)
            if self.schedule_instance:
                clash = clash.exclude(exam_id=self.schedule_instance.exam_id)
            other = clash.select_related('exam').first()
            if other:
                self.add_error('start_time', f"Jadwal bentrok dengan '{other.exam.title}' di {class_room.name} "
                                             f"({timezone.localtime(other.start_time):%d %b %H:%M} WIB).")

        if self.schedule_instance:
            self._clean_edit(cleaned)
        return cleaned

    def _clean_edit(self, cleaned):
        exam = self.schedule_instance.exam
        content_changed = (
            cleaned.get('exam_type') != exam.exam_type
            or cleaned.get('subject') and cleaned['subject'].id != exam.subject_id
            or cleaned.get('level') != exam.level
            or cleaned.get('target_question_count') != exam.target_question_count
        )
        if content_changed and exam.status != 'pending_selection':
            self.add_error(None, "Isi naskah (jenis, mapel, jenjang, target soal) tidak bisa diubah setelah diajukan "
                                 "atau diverifikasi. Buka kunci naskah dulu.")
        start = cleaned.get('start_time')
        time_changed = (
            start and start != self.schedule_instance.start_time.replace(second=0, microsecond=0)
            or cleaned.get('duration') != exam.duration
            or cleaned.get('session_no') != self.schedule_instance.session_no
        )
        # Susulan: waktu boleh digeser setelah ujian berjalan, asal tidak ada siswa yang sedang mengerjakan.
        # Siswa yang sudah selesai tetap ditolak gerbang token; sisa waktu siswa aktif bisa terpotong bila digeser.
        if time_changed and self._sessions_in_progress(exam):
            self.add_error('start_time', "Waktu tidak bisa diubah karena masih ada siswa yang sedang mengerjakan "
                                         "atau terkunci. Tunggu sampai mereka selesai, atau selesaikan sesi yang "
                                         "terkunci lewat Monitoring.")

    @staticmethod
    def _sessions_in_progress(exam):
        from apps.exam_engine.models import ExamSession
        return ExamSession.objects.filter(schedule__exam=exam, status__in=['active', 'locked']).exists()

    # ------------------------------------------------------------------ save

    def save(self):
        with transaction.atomic():
            if self.schedule_instance:
                return self._save_edit()
            return self._save_create()

    def _save_create(self):
        c = self.cleaned_data
        start = c['start_time']
        end = start + timedelta(minutes=c['duration'])
        token = (c.get('token') or generate_exam_token(6)).upper()
        title = resolve_exam_title(c['exam_type'], c.get('title', ''), c.get('sub_type', ''))
        common_exam = dict(subject=c['subject'], title=title, exam_type=c['exam_type'], duration=c['duration'],
                           target_question_count=c['target_question_count'], level=c['level'],
                           status='pending_selection', token=token, start_time=start)
        common_schedule = dict(start_time=start, end_time=end, token=token, session_no=c['session_no'], status='active')

        if c['exam_type'] in ('UH', 'PTS'):
            teacher = self._exam_teacher(c)
            exam = Exam.objects.create(teacher=teacher, **common_exam)
            return [Schedule.objects.create(exam=exam, class_room=c['class_room'], teacher=teacher,
                                            teacher_quota=c['target_question_count'], **common_schedule)]

        schedules = []
        assignments = self._collab_assignments(c)
        for group in build_teacher_set_groups(assignments):
            group_assignments = [a for a in assignments if str(a.class_room_id) in group['class_ids']]
            quota_map = build_teacher_quota_map(group_assignments, c['target_question_count'])
            exam = Exam.objects.create(teacher=self.creator_teacher or group['teachers'][0], **common_exam)
            single_class = group['classes'][0] if len(group['classes']) == 1 else None
            for teacher in group['teachers']:
                schedules.append(Schedule.objects.create(
                    exam=exam, class_room=single_class, teacher=teacher,
                    teacher_quota=quota_map.get(str(teacher.id), c['target_question_count']), **common_schedule,
                ))
        return schedules

    def _save_edit(self):
        c = self.cleaned_data
        schedule = self.schedule_instance
        exam = schedule.exam
        start = c['start_time']
        end = start + timedelta(minutes=c['duration'])
        token = (c.get('token') or schedule.token).upper()

        old_start, old_end = schedule.start_time, schedule.end_time
        finished = exam.started_sessions_count()
        if finished and (start != old_start or end != old_end):
            ScheduleTimeChange.objects.create(exam=exam, changed_by=self.user, old_start=old_start, old_end=old_end,
                                              new_start=start, new_end=end, finished_sessions=finished)

        exam.title = resolve_exam_title(c['exam_type'], c.get('title', ''), c.get('sub_type', '')) or exam.title
        exam.duration = c['duration']
        exam.token = token
        exam.start_time = start
        target_changed = c['target_question_count'] != exam.target_question_count
        if exam.status == 'pending_selection':
            exam.exam_type = c['exam_type']
            exam.subject = c['subject']
            exam.level = c['level']
            exam.target_question_count = c['target_question_count']
        exam.save()

        # Waktu, durasi, sesi, dan token berlaku untuk semua jadwal dalam paket ini
        Schedule.objects.filter(exam=exam).update(start_time=start, end_time=end, token=token,
                                                  session_no=c['session_no'], updated_at=timezone.now())

        if exam.status == 'pending_selection' and c['exam_type'] in ('UH', 'PTS'):
            teacher = self._exam_teacher(c) or schedule.teacher
            Schedule.objects.filter(pk=schedule.pk).update(class_room=c['class_room'], teacher=teacher)
            if teacher and exam.teacher_id != teacher.id:
                Exam.objects.filter(pk=exam.pk).update(teacher=teacher)

        if target_changed and exam.status == 'pending_selection':
            schedules = list(Schedule.objects.filter(exam=exam).exclude(teacher=None).order_by('teacher_id'))
            teachers = sorted({s.teacher_id for s in schedules}, key=str)
            quotas = calculate_collaborative_quotas(teachers, exam.target_question_count)
            for s in schedules:
                Schedule.objects.filter(pk=s.pk).update(teacher_quota=quotas[str(s.teacher_id)])
        return list(Schedule.objects.filter(exam=exam))

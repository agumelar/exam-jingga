from django import forms
from django.utils import timezone
from apps.master_data.models import Subject, ClassRoom, Teacher, TeacherAssignment
from apps.schedules.models import Exam, Schedule
from apps.schedules.utils import (
    generate_exam_token,
    resolve_exam_title,
    build_schedule_date_range,
    calculate_collaborative_quotas,
    build_teacher_set_groups,
    build_teacher_quota_map,
    build_teacher_set_key,
)


class ScheduleForm(forms.Form):
    """
    Form untuk membuat atau mengedit Jadwal dan Paket Ujian CBT.
    Mendukung Ulangan Harian (UH), PTS, PAS, PAT, dan SAJ.
    """
    exam_type = forms.ChoiceField(
        choices=Exam.EXAM_TYPE_CHOICES,
        initial='UH',
        widget=forms.Select(attrs={'class': 'w-full bg-slate-50 dark:bg-stone-800 p-4 rounded-2xl border-none outline-none font-bold'})
    )
    title = forms.CharField(
        max_length=255,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'w-full bg-slate-50 dark:bg-stone-800 p-4 rounded-2xl border-none font-bold outline-none focus:ring-2 focus:ring-orange-500',
            'placeholder': 'Cth: Ulangan Harian Bab 1'
        })
    )
    sub_type = forms.CharField(
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={'class': 'w-full bg-slate-50 dark:bg-stone-800 p-4 rounded-2xl border-none outline-none'})
    )
    level = forms.IntegerField(
        required=True,
        widget=forms.Select(
            choices=[('', '-- Pilih Jenjang --'), (10, 'Kelas 10'), (11, 'Kelas 11'), (12, 'Kelas 12')],
            attrs={'class': 'w-full bg-slate-50 dark:bg-stone-800 p-4 rounded-2xl border-none outline-none focus:ring-2 focus:ring-orange-500'}
        )
    )
    subject = forms.ModelChoiceField(
        queryset=Subject.objects.all(),
        required=True,
        empty_label="-- Pilih Mapel --",
        widget=forms.Select(attrs={'class': 'w-full bg-slate-50 dark:bg-stone-800 p-4 rounded-2xl border-none outline-none focus:ring-2 focus:ring-orange-500'})
    )
    class_room = forms.ModelChoiceField(
        queryset=ClassRoom.objects.all(),
        required=False,
        empty_label="-- Pilih Kelas --",
        widget=forms.Select(attrs={'class': 'w-full bg-orange-50 dark:bg-orange-950/30 p-4 rounded-2xl border-none outline-none focus:ring-2 focus:ring-orange-500'})
    )
    teacher = forms.ModelChoiceField(
        queryset=Teacher.objects.all(),
        required=False,
        empty_label="-- Pilih Guru Penanggung Jawab --",
        widget=forms.Select(attrs={'class': 'w-full bg-slate-50 dark:bg-stone-800 p-4 rounded-2xl border-none outline-none focus:ring-2 focus:ring-orange-500'})
    )
    start_time = forms.CharField(
        required=True,
        widget=forms.TextInput(attrs={
            'type': 'datetime-local',
            'class': 'w-full bg-slate-50 dark:bg-stone-800 p-4 rounded-2xl border-none outline-none focus:ring-2 focus:ring-orange-500'
        })
    )
    token = forms.CharField(
        max_length=10,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'w-full bg-slate-50 dark:bg-stone-800 p-4 rounded-2xl border-none font-black tracking-widest text-orange-600 outline-none',
            'readonly': 'readonly'
        })
    )
    duration = forms.IntegerField(
        initial=60,
        min_value=1,
        widget=forms.NumberInput(attrs={
            'class': 'w-full bg-slate-50 dark:bg-stone-800 p-4 rounded-2xl border-none shadow-inner outline-none focus:ring-2 focus:ring-orange-500'
        })
    )
    target_question_count = forms.IntegerField(
        initial=40,
        min_value=1,
        widget=forms.NumberInput(attrs={
            'class': 'w-full bg-slate-50 dark:bg-stone-800 p-4 rounded-2xl border-none shadow-inner outline-none focus:ring-2 focus:ring-orange-500'
        })
    )
    session_no = forms.CharField(
        initial='0',
        widget=forms.Select(
            choices=[('0', 'Semua Sesi'), ('1', 'Sesi 1'), ('2', 'Sesi 2'), ('3', 'Sesi 3')],
            attrs={'class': 'w-full bg-slate-50 dark:bg-stone-800 p-4 rounded-2xl border-none outline-none focus:ring-2 focus:ring-orange-500'}
        )
    )

    def __init__(self, *args, user=None, schedule_instance=None, **kwargs):
        self.user = user
        self.schedule_instance = schedule_instance
        super().__init__(*args, **kwargs)

        if not self.initial.get('token'):
            self.initial['token'] = generate_exam_token(6)

        # Scoping based on user role
        if user and getattr(user, 'role', '') == 'guru':
            # Teachers can only create UH
            self.fields['exam_type'].choices = [('UH', 'Ulangan Harian')]

        # Populate initial if editing
        if schedule_instance:
            exam = schedule_instance.exam
            self.initial['exam_type'] = exam.exam_type
            self.initial['title'] = exam.title
            self.initial['level'] = exam.level
            self.initial['subject'] = exam.subject
            self.initial['class_room'] = schedule_instance.class_room
            self.initial['teacher'] = schedule_instance.teacher
            self.initial['duration'] = exam.duration
            self.initial['target_question_count'] = exam.target_question_count
            self.initial['token'] = schedule_instance.token
            self.initial['session_no'] = str(schedule_instance.session_no)
            if schedule_instance.start_time:
                local_dt = timezone.localtime(schedule_instance.start_time)
                self.initial['start_time'] = local_dt.strftime('%Y-%m-%dT%H:%M')

    def clean(self):
        cleaned_data = super().clean()
        exam_type = cleaned_data.get('exam_type')
        title = cleaned_data.get('title')
        sub_type = cleaned_data.get('sub_type')
        class_room = cleaned_data.get('class_room')

        if exam_type == 'UH' and not title:
            self.add_error('title', 'Nama ujian wajib diisi untuk Ulangan Harian.')

        if exam_type in ['UH', 'PTS'] and not class_room and not self.schedule_instance:
            self.add_error('class_room', 'Kelas wajib dipilih untuk UH dan PTS.')

        if self.user and getattr(self.user, 'role', '') == 'guru':
            if exam_type != 'UH':
                self.add_error('exam_type', 'Guru hanya memiliki wewenang untuk menjadwalkan Ulangan Harian (UH).')

        duration = cleaned_data.get('duration')
        if duration is not None and duration < 1:
            self.add_error('duration', 'Durasi pelaksanaan ujian minimal 1 menit.')

        return cleaned_data

    def save(self, creator_teacher=None):
        cleaned_data = self.cleaned_data
        exam_type = cleaned_data.get('exam_type')
        raw_title = cleaned_data.get('title', '')
        sub_type = cleaned_data.get('sub_type', '')
        level = cleaned_data.get('level')
        subject = cleaned_data.get('subject')
        class_room = cleaned_data.get('class_room')
        teacher = cleaned_data.get('teacher') or creator_teacher
        duration = cleaned_data.get('duration') or 60
        target_count = cleaned_data.get('target_question_count') or 40
        token_val = cleaned_data.get('token') or generate_exam_token(6)
        start_time_val = cleaned_data.get('start_time')
        session_str = cleaned_data.get('session_no', '0')
        session_no = 0 if session_str == 'Semua Sesi' else int(session_str)

        start_dt, end_dt = build_schedule_date_range(start_time_val, duration)
        final_title = resolve_exam_title(exam_type, raw_title, sub_type)

        if self.schedule_instance:
            # Updating existing schedule
            schedule = self.schedule_instance
            exam = schedule.exam
            exam.title = final_title
            exam.duration = duration
            exam.target_question_count = target_count
            exam.exam_type = exam_type
            exam.save()

            schedule.start_time = start_dt
            schedule.end_time = end_dt
            schedule.token = token_val
            schedule.session_no = session_no
            schedule.teacher_quota = target_count
            if class_room:
                schedule.class_room = class_room
            schedule.save()
            return [schedule]

        # Creating new exam & schedule(s)
        if exam_type in ['UH', 'PTS']:
            # Single teacher & class schedule
            exam = Exam.objects.create(
                teacher=teacher,
                subject=subject,
                title=final_title,
                exam_type=exam_type,
                duration=duration,
                target_question_count=target_count,
                level=level,
                status='pending_selection',
                token=token_val,
                start_time=start_dt
            )
            schedule = Schedule.objects.create(
                exam=exam,
                class_room=class_room,
                teacher=teacher,
                start_time=start_dt,
                end_time=end_dt,
                token=token_val,
                session_no=session_no,
                status='active',
                teacher_quota=target_count
            )
            return [schedule]

        # Collaborative Exam (PAS / PAT / SAJ)
        # Sesuai ketentuan.md:
        # - Pengisian soal dan jadwal berdasarkan masing-masing guru
        # - Untuk 1 mapel dengan beda guru di kelas yang sama (mapel produktif/team teaching), soal dibagi rata
        assignments = list(TeacherAssignment.objects.filter(
            subject=subject,
            class_room__level=level
        ).select_related('teacher', 'class_room'))

        if not assignments:
            # Fallback jika belum ada penugasan guru di master data
            exam = Exam.objects.create(
                teacher=creator_teacher or teacher,
                subject=subject,
                title=final_title,
                exam_type=exam_type,
                duration=duration,
                target_question_count=target_count,
                level=level,
                status='pending_selection',
                token=token_val,
                start_time=start_dt
            )
            sch = Schedule.objects.create(
                exam=exam,
                class_room=None,
                teacher=creator_teacher or teacher,
                start_time=start_dt,
                end_time=end_dt,
                token=token_val,
                session_no=session_no,
                status='active',
                teacher_quota=target_count
            )
            return [sch]

        # Kelompokkan kelas berdasarkan himpunan guru pengampu
        teacher_set_groups = build_teacher_set_groups(assignments)
        schedules = []

        for group in teacher_set_groups:
            group_teachers = group.get('teachers', [])
            if not group_teachers:
                continue

            group_assignments = [
                a for a in assignments
                if str(getattr(a, 'class_room_id', '')) in group['class_ids']
            ]
            quota_map = build_teacher_quota_map(group_assignments, target_count)

            exam = Exam.objects.create(
                teacher=creator_teacher or group_teachers[0],
                subject=subject,
                title=final_title,
                exam_type=exam_type,
                duration=duration,
                target_question_count=target_count,
                level=level,
                status='pending_selection',
                token=token_val,
                start_time=start_dt
            )

            # Jika grup hanya mencakup 1 rombel kelas, tautkan langsung ke class_room tersebut
            group_class_obj = group['classes'][0] if len(group.get('classes', [])) == 1 else None

            for t in group_teachers:
                quota = quota_map.get(str(t.id), target_count)
                sch = Schedule.objects.create(
                    exam=exam,
                    class_room=group_class_obj,
                    teacher=t,
                    start_time=start_dt,
                    end_time=end_dt,
                    token=token_val,
                    session_no=session_no,
                    status='active',
                    teacher_quota=quota
                )
                schedules.append(sch)

        return schedules

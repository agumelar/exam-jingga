import uuid
from datetime import timedelta
from django.db import models
from django.utils import timezone


class ExamSession(models.Model):
    """
    Sesi Pengerjaan Ujian Siswa.
    Menyimpan status pengerjaan siswa, waktu mulai/selesai, sisa waktu, jumlah pelanggaran, dan skor akhir.
    """
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('locked', 'Locked'),
        ('finished', 'Finished'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    student = models.ForeignKey(
        'master_data.Student',
        on_delete=models.CASCADE,
        related_name='exam_sessions',
        db_column='student_id',
        help_text="Siswa Peserta Ujian"
    )
    schedule = models.ForeignKey(
        'schedules.Schedule',
        on_delete=models.CASCADE,
        related_name='exam_sessions',
        db_column='schedule_id',
        help_text="Jadwal Ujian Terkait"
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='active',
        help_text="Status Sesi Ujian (active, locked, finished)"
    )
    violation_count = models.IntegerField(
        default=0,
        help_text="Jumlah Pelanggaran / Pindah Layar Terdeteksi"
    )
    score = models.FloatField(
        default=0.0,
        help_text="Nilai / Skor Akhir Ujian (0 - 100)"
    )
    started_at = models.DateTimeField(
        auto_now_add=True,
        help_text="Waktu Mulai Pengerjaan"
    )
    finished_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Waktu Selesai Pengerjaan"
    )
    remaining_seconds = models.IntegerField(
        default=3600,
        help_text="Sisa Waktu Pengerjaan dalam Detik"
    )

    class Meta:
        db_table = 'exam_sessions'
        ordering = ['-started_at']
        verbose_name = 'Sesi Ujian'
        verbose_name_plural = 'Daftar Sesi Ujian'
        constraints = [
            models.UniqueConstraint(
                fields=['student', 'schedule'],
                name='uq_student_schedule_session'
            )
        ]

    def __str__(self):
        sch_title = self.schedule.exam.title if self.schedule and self.schedule.exam else "Ujian"
        stu_name = self.student.full_name if self.student else "Siswa"
        return f"[{self.get_status_display()}] {stu_name} - {sch_title}"

    @property
    def is_active(self):
        return self.status == 'active'

    @property
    def is_locked(self):
        return self.status == 'locked'

    @property
    def is_finished(self):
        return self.status == 'finished'

    @property
    def total_questions_count(self):
        return self.student_answers.count()

    @property
    def answered_count(self):
        return self.student_answers.exclude(chosen_answer__isnull=True).exclude(chosen_answer='').count()

    @property
    def doubt_count(self):
        return self.student_answers.filter(is_doubt=True).count()

    @property
    def correct_count(self):
        return self.student_answers.filter(is_correct=True).count()

    def calculate_remaining_seconds(self):
        """Menghitung sisa detik pengerjaan berdasarkan started_at dan durasi jadwal."""
        if self.status == 'finished':
            return 0
        if not self.started_at or not self.schedule or not self.schedule.exam:
            return self.remaining_seconds

        duration_minutes = self.schedule.exam.duration or 60
        end_time = self.started_at + timedelta(minutes=duration_minutes)
        now = timezone.now()
        rem = int((end_time - now).total_seconds())
        return max(0, rem)


class StudentAnswer(models.Model):
    """
    Lembar Jawaban Butir Soal oleh Siswa pada suatu Sesi Ujian.
    Mencatat opsi yang dipilih (A-E), status ragu-ragu, dan kebenaran jawaban.
    """
    ANSWER_CHOICES = [
        ('A', 'A'),
        ('B', 'B'),
        ('C', 'C'),
        ('D', 'D'),
        ('E', 'E'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    session = models.ForeignKey(
        ExamSession,
        on_delete=models.CASCADE,
        related_name='student_answers',
        db_column='session_id',
        help_text="Sesi Ujian Siswa"
    )
    question = models.ForeignKey(
        'questions.Question',
        on_delete=models.CASCADE,
        related_name='student_answers',
        db_column='question_id',
        help_text="Butir Soal Terkait"
    )
    chosen_answer = models.CharField(
        max_length=1,
        choices=ANSWER_CHOICES,
        null=True,
        blank=True,
        help_text="Pilihan Jawaban Siswa (A, B, C, D, E)"
    )
    is_doubt = models.BooleanField(
        default=False,
        help_text="Status Ragu-ragu Jawaban"
    )
    is_correct = models.BooleanField(
        null=True,
        blank=True,
        help_text="Hasil Koreksi Jawaban (True jika Benar)"
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        help_text="Waktu Terakhir Jawaban Diperbarui"
    )

    class Meta:
        db_table = 'student_answers'
        ordering = ['session', 'question']
        verbose_name = 'Jawaban Siswa'
        verbose_name_plural = 'Daftar Jawaban Siswa'
        constraints = [
            models.UniqueConstraint(
                fields=['session', 'question'],
                name='uq_session_question_answer'
            )
        ]

    def __str__(self):
        ans = self.chosen_answer or '-'
        doubt_str = ' [Ragu]' if self.is_doubt else ''
        return f"Sesi {self.session_id} - Q:{self.question_id} -> {ans}{doubt_str}"

    def evaluate_correctness(self):
        """Memeriksa apakah jawaban yang dipilih cocok dengan kunci jawaban soal."""
        if not self.chosen_answer:
            self.is_correct = None
        elif self.question and self.question.correct_answer:
            self.is_correct = (self.chosen_answer.upper() == self.question.correct_answer.upper())
        else:
            self.is_correct = False
        return self.is_correct

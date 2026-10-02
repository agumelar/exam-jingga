import uuid
from django.db import models
from django.utils import timezone


class Exam(models.Model):
    """
    Paket Naskah Ujian CBT.
    Menyimpan konfigurasi utama paket soal, durasi, target butir soal, dan status lifecycle.
    """
    EXAM_TYPE_CHOICES = [
        ('UH', 'Ulangan Harian'),
        ('PTS', 'Penilaian Tengah Semester'),
        ('PAS', 'Penilaian Akhir Semester'),
        ('PAT', 'Penilaian Akhir Tahun'),
        ('SAJ', 'Sumatif Akhir Jenjang'),
    ]

    STATUS_CHOICES = [
        ('pending_selection', 'Tunggu Soal'),
        ('waiting_validation', 'Tunggu Verifikasi'),
        ('validated', 'Tervalidasi'),
        ('ready', 'Siap Ujian'),
        ('active', 'Sedang Berlangsung'),
        ('closed', 'Selesai'),
    ]

    LEVEL_CHOICES = [
        (10, 'Kelas 10'),
        (11, 'Kelas 11'),
        (12, 'Kelas 12'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    teacher = models.ForeignKey(
        'master_data.Teacher',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='exams',
        db_column='teacher_id',
        help_text="Guru Pembuat / Penanggung Jawab Paket Ujian"
    )
    subject = models.ForeignKey(
        'master_data.Subject',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='exams',
        db_column='subject_id',
        help_text="Mata Pelajaran Ujian"
    )
    title = models.CharField(max_length=255, help_text="Judul / Nama Ujian")
    exam_type = models.CharField(
        max_length=20,
        choices=EXAM_TYPE_CHOICES,
        default='UH',
        help_text="Jenis Asesmen Ujian"
    )
    duration = models.IntegerField(default=60, help_text="Durasi Ujian dalam Menit")
    target_question_count = models.IntegerField(default=40, help_text="Target Jumlah Butir Soal")
    level = models.IntegerField(
        choices=LEVEL_CHOICES,
        null=True,
        blank=True,
        help_text="Tingkat / Jenjang Kelas (10, 11, 12)"
    )
    status = models.CharField(
        max_length=50,
        choices=STATUS_CHOICES,
        default='pending_selection',
        help_text="Status Siklus Hidup Ujian"
    )
    shuffle_questions = models.BooleanField(
        default=True,
        help_text="Acak Urutan Soal untuk Setiap Siswa"
    )
    token = models.CharField(
        max_length=10,
        null=True,
        blank=True,
        help_text="Token Akses Ujian (6 Karakter)"
    )
    start_time = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Waktu Mulai Pelaksanaan Ujian"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'exams'
        ordering = ['-created_at']
        verbose_name = 'Paket Ujian'
        verbose_name_plural = 'Daftar Paket Ujian'

    def __str__(self):
        subj = self.subject.name if self.subject else "Umum"
        return f"[{self.exam_type}] {self.title} - {subj}"

    @property
    def selected_questions_count(self):
        return self.exam_questions.count()

    @property
    def is_ready_for_student(self):
        return self.status in ['validated', 'ready', 'active']

    def is_locked(self):
        """Memeriksa apakah naskah soal sudah dikunci (validated/ready/active)."""
        return self.status in ['validated', 'ready', 'active']


class ExamQuestion(models.Model):
    """
    Relasi Butir Soal terpilih pada Paket Ujian CBT.
    Menjamin integritas paket soal dan urutan naskah.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    exam = models.ForeignKey(
        Exam,
        on_delete=models.CASCADE,
        related_name='exam_questions',
        db_column='exam_id',
        help_text="Paket Ujian Terkait"
    )
    question = models.ForeignKey(
        'questions.Question',
        on_delete=models.CASCADE,
        related_name='question_exams',
        db_column='question_id',
        help_text="Butir Soal Terpilih dari Bank Soal"
    )
    order_number = models.IntegerField(default=1, help_text="Nomor Urut Soal")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'exam_questions'
        ordering = ['order_number', 'created_at']
        verbose_name = 'Soal Paket Ujian'
        verbose_name_plural = 'Daftar Soal Paket Ujian'
        constraints = [
            models.UniqueConstraint(
                fields=['exam', 'question'],
                name='uq_exam_question'
            )
        ]

    def __str__(self):
        return f"{self.exam.title} - Soal #{self.order_number}"


class Schedule(models.Model):
    """
    Jadwal Pelaksanaan Sesi Ujian CBT.
    Menghubungkan Paket Ujian ke Rombel Kelas, Pengawas, Sesi, Ruang, dan Token.
    """
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('verified', 'Terverifikasi'),
        ('active', 'Aktif'),
        ('closed', 'Selesai'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    exam = models.ForeignKey(
        Exam,
        on_delete=models.CASCADE,
        related_name='schedules',
        db_column='exam_id',
        help_text="Paket Ujian"
    )
    class_room = models.ForeignKey(
        'master_data.ClassRoom',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='schedules',
        db_column='class_id',
        help_text="Rombongan Belajar / Kelas"
    )
    teacher = models.ForeignKey(
        'master_data.Teacher',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='schedules',
        db_column='teacher_id',
        help_text="Guru Pengawas / Pengampu"
    )
    start_time = models.DateTimeField(help_text="Waktu Mulai Jadwal Ujian")
    end_time = models.DateTimeField(help_text="Waktu Berakhir Jadwal Ujian")
    token = models.CharField(max_length=10, help_text="Token Akses Ujian")
    session_no = models.IntegerField(default=1, help_text="Nomor Sesi Ujian (0 = Semua Sesi)")
    room_name = models.CharField(max_length=100, null=True, blank=True, help_text="Nama Ruang Ujian")
    status = models.CharField(
        max_length=50,
        choices=STATUS_CHOICES,
        default='active',
        help_text="Status Jadwal Ujian"
    )
    teacher_quota = models.IntegerField(
        default=0,
        help_text="Target Kuota Butir Soal Kontribusi Guru ini"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'schedules'
        ordering = ['-start_time']
        verbose_name = 'Jadwal Ujian'
        verbose_name_plural = 'Daftar Jadwal Ujian'

    def __str__(self):
        cls_name = self.class_room.name if self.class_room else "Semua Kelas"
        return f"{self.exam.title} ({cls_name}) - {self.token}"

    def clean(self):
        super().clean()
        if self.start_time and self.end_time and self.end_time <= self.start_time:
            from django.core.exceptions import ValidationError
            raise ValidationError({'end_time': 'Waktu berakhir ujian harus setelah waktu mulai.'})

    @property
    def is_token_active(self):
        """Token aktif jika paket ujian berstatus validated, ready, atau active."""
        if not self.exam:
            return False
        return self.exam.is_ready_for_student

    @property
    def session_display(self):
        if self.session_no == 0:
            return 'Semua Sesi'
        return f'Sesi {self.session_no}'

    @property
    def cluster_classes_text(self):
        """Menampilkan teks gabungan kelas jika jadwal berupa kluster kolaboratif."""
        if self.class_room:
            return self.class_room.name
        if self.exam and self.exam.level:
            return f"Semua Kelas {self.exam.level}"
        return "Semua Kelas"

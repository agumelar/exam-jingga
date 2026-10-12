import uuid
from django.db import models


class StudentLogistic(models.Model):
    """
    Data Alokasi Logistik Ruang dan Sesi Ujian Siswa.
    Digunakan untuk pencetakan Kartu Ujian, Daftar Hadir, dan Penempatan Ruang CBT.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    student = models.ForeignKey(
        'master_data.Student',
        on_delete=models.CASCADE,
        related_name='logistics',
        db_column='student_id',
        help_text="Siswa Peserta Ujian"
    )
    room_name = models.CharField(
        max_length=100,
        default='RUANG 01',
        help_text="Nama / Nomor Ruangan Ujian (e.g. RUANG 01, Lab Komputer 1)"
    )
    session_name = models.CharField(
        max_length=100,
        default='SESI 1',
        help_text="Nama Sesi Ujian (e.g. SESI 1, SESI 2)"
    )
    exam_period = models.CharField(
        max_length=100,
        blank=True,
        default='',
        help_text="Periode Ujian (e.g. PAS Ganjil 2025/2026)"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'student_logistics'
        ordering = ['room_name', 'session_name', 'student__full_name']
        verbose_name = 'Logistik Siswa'
        verbose_name_plural = 'Daftar Logistik Siswa'

    def __str__(self):
        std_name = self.student.full_name if self.student else "Siswa"
        return f"{std_name} - {self.room_name} ({self.session_name})"


class SessionActionLog(models.Model):
    """
    Jejak buka kunci, reset, dan paksa selesai sesi siswa oleh admin/kurikulum.
    Reset menghapus sesi agar siswa bisa mulai ulang, jadi isi lembar jawabannya disimpan di sini dulu.
    """
    ACTION_CHOICES = [
        ('unlock', 'Buka Kunci'),
        ('reset', 'Reset Sesi'),
        ('force_submit', 'Paksa Selesai'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    action = models.CharField(max_length=20, choices=ACTION_CHOICES)
    reason = models.TextField()
    actor = models.ForeignKey('accounts.CustomUser', on_delete=models.SET_NULL, null=True, related_name='session_actions')
    student = models.ForeignKey('master_data.Student', on_delete=models.SET_NULL, null=True, related_name='session_actions')
    schedule = models.ForeignKey('schedules.Schedule', on_delete=models.SET_NULL, null=True, related_name='session_actions')
    session_id_snapshot = models.UUIDField(help_text="Id sesi saat aksi dilakukan (sesi bisa sudah dihapus oleh reset)")
    previous_status = models.CharField(max_length=20)
    previous_violation_count = models.IntegerField(default=0)
    previous_score = models.FloatField(default=0.0)
    answers_snapshot = models.JSONField(default=list, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'session_action_logs'
        ordering = ['-created_at']
        verbose_name = 'Log Aksi Sesi'
        verbose_name_plural = 'Log Aksi Sesi'

    def __str__(self):
        return f"{self.get_action_display()} oleh {self.actor_id} ({self.created_at:%Y-%m-%d %H:%M})"

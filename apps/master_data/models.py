import uuid
from django.db import models
from django.conf import settings


class Major(models.Model):
    """Konsentrasi Keahlian / Jurusan SMK."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    code = models.CharField(max_length=50, unique=True, help_text="Kode Jurusan (e.g. RPL, TBSM, TKRO, ATPH)")
    name = models.CharField(max_length=255, help_text="Nama Jurusan (e.g. Rekayasa Perangkat Lunak)")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'majors'
        ordering = ['name']
        verbose_name = 'Jurusan'
        verbose_name_plural = 'Daftar Jurusan'

    def __str__(self):
        return f"{self.code} - {self.name}"


class ClassRoom(models.Model):
    """Rombongan Belajar / Kelas."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    major = models.ForeignKey(
        Major,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        db_column='major_id',
        related_name='classes',
        help_text="Jurusan / Konsentrasi Keahlian"
    )
    name = models.CharField(max_length=100, unique=True, help_text="Nama Kelas (e.g. X RPL 1, XI TBSM 2)")
    level = models.IntegerField(default=10, help_text="Tingkat Kelas (10, 11, 12)")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'classes'
        ordering = ['name']
        verbose_name = 'Kelas / Rombel'
        verbose_name_plural = 'Daftar Kelas / Rombel'

    def save(self, *args, **kwargs):
        if self.name:
            upper = self.name.strip().upper()
            if upper.startswith(('XII ', '12 ', 'XII-', 'XII_')) or upper.startswith('12') or upper.startswith('XII'):
                self.level = 12
            elif upper.startswith(('XI ', '11 ', 'XI-', 'XI_')) or upper.startswith('11') or upper.startswith('XI'):
                self.level = 11
            elif upper.startswith(('X ', '10 ', 'X-', 'X_')) or upper.startswith('10') or upper.startswith('X'):
                self.level = 10
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class Teacher(models.Model):
    """Data Guru & Tenaga Pendidik / Pembuat Soal."""
    ROLE_CHOICES = [
        ('admin', 'Admin'),
        ('kurikulum', 'Kurikulum'),
        ('guru', 'Guru'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        db_column='user_id',
        related_name='teacher_profile'
    )
    sso_id = models.UUIDField(null=True, blank=True, unique=True, help_text="SSO Keycloak UUID")
    nip = models.CharField(max_length=50, null=True, blank=True, help_text="Nomor Induk Pegawai")
    full_name = models.CharField(max_length=255, help_text="Nama Lengkap Guru")
    email = models.CharField(max_length=255, null=True, blank=True, unique=True, help_text="Email SSO / Sekolah")
    role_level = models.CharField(max_length=20, choices=ROLE_CHOICES, default='guru')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'teachers'
        ordering = ['full_name']
        verbose_name = 'Guru / GTK'
        verbose_name_plural = 'Daftar Guru / GTK'

    def __str__(self):
        return f"{self.full_name} ({self.get_role_level_display()})"


class Student(models.Model):
    """Data Siswa Peserta Ujian CBT."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        db_column='user_id',
        related_name='student_profile'
    )
    sso_id = models.UUIDField(null=True, blank=True, unique=True, help_text="SSO Keycloak UUID")
    nis = models.CharField(max_length=50, unique=True, help_text="Nomor Induk Siswa")
    full_name = models.CharField(max_length=255, help_text="Nama Lengkap Siswa")
    major = models.ForeignKey(
        Major,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        db_column='major_id',
        related_name='students'
    )
    class_room = models.ForeignKey(
        ClassRoom,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        db_column='class_id',
        related_name='students'
    )
    status = models.CharField(max_length=50, default='aktif', help_text="Status Siswa (aktif, mutasi, lulus, dll)")
    email = models.CharField(max_length=255, null=True, blank=True)
    password_plain = models.CharField(max_length=100, blank=True, default='', help_text="Password default / kartu peserta")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'students'
        ordering = ['full_name']
        verbose_name = 'Siswa'
        verbose_name_plural = 'Daftar Siswa'

    def __str__(self):
        return f"{self.nis} - {self.full_name}"


class Subject(models.Model):
    """Mata Pelajaran Ujian."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    code = models.CharField(max_length=50, blank=True, default='')
    name = models.CharField(max_length=255, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'subjects'
        ordering = ['name']
        verbose_name = 'Mata Pelajaran'
        verbose_name_plural = 'Daftar Mata Pelajaran'

    def __str__(self):
        return self.name


class TeacherAssignment(models.Model):
    """Penugasan Guru Pengampu Mata Pelajaran di Kelas."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    teacher = models.ForeignKey(
        Teacher,
        on_delete=models.CASCADE,
        db_column='teacher_id',
        related_name='assignments'
    )
    subject = models.ForeignKey(
        Subject,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        db_column='subject_id',
        related_name='assignments'
    )
    subject_name = models.CharField(max_length=255, blank=True, default='')
    class_room = models.ForeignKey(
        ClassRoom,
        on_delete=models.CASCADE,
        db_column='class_id',
        related_name='teacher_assignments'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'teacher_assignments'
        verbose_name = 'Penugasan Guru'
        verbose_name_plural = 'Daftar Penugasan Guru'

    def save(self, *args, **kwargs):
        if self.subject and not self.subject_name:
            self.subject_name = self.subject.name
        elif self.subject_name and not self.subject:
            subj, _ = Subject.objects.get_or_create(name=self.subject_name.strip())
            self.subject = subj
        super().save(*args, **kwargs)

    def __str__(self):
        subj = self.subject.name if self.subject else self.subject_name
        return f"{self.teacher.full_name} - {subj} ({self.class_room.name})"

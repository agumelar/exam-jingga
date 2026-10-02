import uuid
from django.contrib.auth.models import AbstractUser
from django.db import models


class Role(models.TextChoices):
    ADMIN = 'admin', 'Admin'
    KURIKULUM = 'kurikulum', 'Kurikulum'
    GURU = 'guru', 'Guru'
    PENGAWAS = 'pengawas', 'Pengawas'
    SISWA = 'siswa', 'Siswa'
    PLATFORM_ADMIN = 'platform_admin', 'Platform Admin'
    DATA_ADMIN = 'data_admin', 'Data Admin'


class CustomUser(AbstractUser):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    sso_id = models.UUIDField(null=True, blank=True, unique=True, help_text="Keycloak User UUID")
    role = models.CharField(
        max_length=20,
        choices=Role.choices,
        default=Role.SISWA,
        help_text="Peran pengguna dalam sistem CBT"
    )
    nis = models.CharField(
        max_length=50,
        null=True,
        blank=True,
        help_text="Nomor Induk Siswa (untuk role Siswa)"
    )
    full_name = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        help_text="Nama Lengkap Pengguna"
    )

    class Meta:
        db_table = 'users'
        verbose_name = 'User'
        verbose_name_plural = 'Users'

    def __str__(self):
        name = self.full_name or self.username
        return f"{name} ({self.get_role_display()})"

    @property
    def is_student(self):
        return self.role == Role.SISWA

    @property
    def is_teacher(self):
        return self.role in [Role.GURU, Role.PENGAWAS]

    @property
    def is_admin(self):
        return self.is_superuser or self.role in [
            Role.ADMIN,
            Role.PLATFORM_ADMIN,
            Role.DATA_ADMIN,
            Role.KURIKULUM,
        ]

    @property
    def is_curriculum(self):
        return self.role == Role.KURIKULUM

    def get_full_name(self):
        if self.full_name:
            return self.full_name
        full = super().get_full_name()
        return full if full else self.username


from django.db import models


class SchoolSetting(models.Model):
    """Singleton-style model storing school identity, letterhead, and exam execution settings."""
    school_name = models.CharField(max_length=255, default='SMK NEGERI 1 RONGGA')
    school_address = models.TextField(blank=True, default='')
    school_website = models.CharField(max_length=255, blank=True, default='')
    school_email = models.EmailField(max_length=255, blank=True, default='')
    school_phone = models.CharField(max_length=50, blank=True, default='')
    school_postal_code = models.CharField(max_length=50, blank=True, default='')
    school_majors_list = models.CharField(max_length=255, blank=True, default='', help_text="Daftar Jurusan")

    academic_year = models.CharField(max_length=50, default='2025/2026')
    semester = models.CharField(max_length=50, default='Ganjil')
    exam_name = models.CharField(max_length=255, default='Penilaian Akhir Semester (PAS)')
    exam_city = models.CharField(max_length=100, default='Rongga')
    exam_date = models.CharField(max_length=100, blank=True, default='')

    headmaster_name = models.CharField(max_length=255, blank=True, default='')
    headmaster_nip = models.CharField(max_length=50, blank=True, default='')
    curriculum_vicedir_name = models.CharField(max_length=255, blank=True, default='')
    curriculum_vicedir_nip = models.CharField(max_length=50, blank=True, default='')
    committee_chairman = models.CharField(max_length=255, blank=True, default='')

    logo_left_url = models.TextField(blank=True, default='', help_text="URL / Base64 logo kiri (cth: Pemda)")
    logo_right_url = models.TextField(blank=True, default='', help_text="URL / Base64 logo kanan (cth: Sekolah)")
    watermark_url = models.TextField(blank=True, default='', help_text="URL / Base64 watermark latar")
    school_seal_url = models.TextField(blank=True, default='', help_text="URL / Base64 cap stempel sekolah")
    headmaster_signature_url = models.TextField(blank=True, default='', help_text="URL / Base64 TTD Kepala Sekolah")
    curriculum_signature_url = models.TextField(blank=True, default='', help_text="URL / Base64 TTD Wakasek Kurikulum")

    header_1 = models.CharField(max_length=255, blank=True, default='', help_text="Kop Surat Baris 1")
    header_2 = models.CharField(max_length=255, blank=True, default='', help_text="Kop Surat Baris 2")
    header_3 = models.CharField(max_length=255, blank=True, default='', help_text="Kop Surat Baris 3")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'school_settings'
        verbose_name = 'School Setting'
        verbose_name_plural = 'School Settings'

    def __str__(self):
        return f"{self.school_name} ({self.academic_year} - {self.semester})"

    @classmethod
    def get_settings(cls):
        """Helper to get or create the single school setting instance."""
        obj, _ = cls.objects.get_or_create(id=1)
        return obj

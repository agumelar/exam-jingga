import re
import uuid
from django.db import models
from django.core.exceptions import ValidationError
from apps.master_data.models import Subject, Teacher


_CROSS_REFERENCE_PATTERNS = [
    re.compile(r'\b(semua|keduanya|seluruh)\b.*\b(benar|salah|jawaban|pilihan|opsi)\b', re.IGNORECASE),
    re.compile(r'\b(benar|salah)\s+semua\b', re.IGNORECASE),
    re.compile(r'\btidak\s+ada\b.*\b(benar|salah|jawaban)\b', re.IGNORECASE),
    re.compile(r'\b[a-e]\s*(,|dan|&|serta|atau)\s*[a-e]\b', re.IGNORECASE),
    re.compile(r'\b(jawaban|opsi|pilihan)\s+[a-e]\b', re.IGNORECASE),
]


def detect_cross_referencing_options(option_texts):
    """
    True bila ada opsi yang maknanya bergantung pada posisi opsi lain ("Semua benar",
    "A dan B benar"). Opsi seperti itu rusak bila urutannya diacak.
    """
    return any(p.search(text or '') for text in option_texts for p in _CROSS_REFERENCE_PATTERNS)


class Question(models.Model):
    """
    Butir Soal CBT (Bank Soal) untuk Mata Pelajaran & Tingkat Kelas.
    Mendukung opsi A-E, upload gambar pertanyaan dan opsi, serta penandaan kunci jawaban.
    """
    ANSWER_CHOICES = [
        ('A', 'A'),
        ('B', 'B'),
        ('C', 'C'),
        ('D', 'D'),
        ('E', 'E'),
    ]

    LEVEL_CHOICES = [
        (10, 'Kelas 10'),
        (11, 'Kelas 11'),
        (12, 'Kelas 12'),
    ]

    CP_CHOICES = [
        ('CP 1', 'CP 1'),
        ('CP 2', 'CP 2'),
        ('CP 3', 'CP 3'),
        ('CP 4', 'CP 4'),
        ('CP 5', 'CP 5'),
        ('CP 6', 'CP 6'),
        ('CP 7', 'CP 7'),
        ('CP 8', 'CP 8'),
        ('CP 9', 'CP 9'),
        ('CP 10', 'CP 10'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    subject = models.ForeignKey(
        Subject,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        db_column='subject_id',
        related_name='questions',
        help_text="Mata Pelajaran Ujian"
    )
    created_by = models.ForeignKey(
        Teacher,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        db_column='created_by',
        related_name='created_questions',
        help_text="Guru Pembuat Soal"
    )
    level = models.IntegerField(
        choices=LEVEL_CHOICES,
        null=True,
        blank=True,
        help_text="Tingkat / Jenjang Kelas (10, 11, 12)"
    )
    cp_code = models.CharField(
        max_length=10,
        choices=CP_CHOICES,
        blank=True,
        default='',
        db_index=True,
        help_text="Capaian Pembelajaran (CP 1 - CP 10)"
    )
    cp_name = models.CharField(
        max_length=255,
        blank=True,
        default='',
        help_text="Keterangan Topik/Materi Capaian Pembelajaran"
    )
    question_text = models.TextField(help_text="Isi Teks Pertanyaan Soal")
    question_image = models.ImageField(
        upload_to='questions/',
        null=True,
        blank=True,
        help_text="Gambar Ilustrasi Soal"
    )

    option_a = models.TextField(blank=True, default='', help_text="Pilihan Jawaban A")
    image_a = models.ImageField(upload_to='questions/options/', null=True, blank=True, help_text="Gambar Opsi A")

    option_b = models.TextField(blank=True, default='', help_text="Pilihan Jawaban B")
    image_b = models.ImageField(upload_to='questions/options/', null=True, blank=True, help_text="Gambar Opsi B")

    option_c = models.TextField(blank=True, default='', help_text="Pilihan Jawaban C")
    image_c = models.ImageField(upload_to='questions/options/', null=True, blank=True, help_text="Gambar Opsi C")

    option_d = models.TextField(blank=True, default='', help_text="Pilihan Jawaban D")
    image_d = models.ImageField(upload_to='questions/options/', null=True, blank=True, help_text="Gambar Opsi D")

    option_e = models.TextField(blank=True, default='', help_text="Pilihan Jawaban E")
    image_e = models.ImageField(upload_to='questions/options/', null=True, blank=True, help_text="Gambar Opsi E")

    correct_answer = models.CharField(
        max_length=1,
        choices=ANSWER_CHOICES,
        default='A',
        help_text="Kunci Jawaban Benar (A/B/C/D/E)"
    )
    lock_option_order = models.BooleanField(
        default=False,
        help_text="Jangan acak urutan opsi (untuk opsi seperti 'Semua benar' atau 'A dan B benar')"
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'questions'
        ordering = ['-created_at']
        verbose_name = 'Butir Soal'
        verbose_name_plural = 'Bank Soal'
        indexes = [
            models.Index(fields=['subject', 'level', 'cp_code']),
            models.Index(fields=['-created_at']),
        ]

    @property
    def cp_display(self):
        if self.cp_code and self.cp_name:
            return f"{self.cp_code}: {self.cp_name}"
        return self.cp_code or self.cp_name or ""

    def edit_lock_reason(self):
        """Alasan soal tidak boleh diubah: sudah masuk naskah yang diajukan/terverifikasi atau sudah dijawab siswa."""
        if self.student_answers.exists():
            return "Soal ini sudah dijawab siswa, jadi isinya tidak bisa diubah agar nilai tetap sah."
        locked = self.question_exams.exclude(exam__status='pending_selection').select_related('exam').first()
        if locked:
            return f"Soal ini dipakai naskah '{locked.exam.title}' yang sudah diajukan atau terverifikasi. Buka kunci naskah dulu."
        return None

    def delete_block_reason(self):
        """Alasan soal tidak boleh dihapus dari bank soal."""
        if self.student_answers.exists():
            return "Soal ini sudah dijawab siswa dan menjadi bagian dari riwayat nilai, jadi tidak bisa dihapus."
        used = self.question_exams.count()
        if used:
            return f"Soal ini masih dipilih di {used} paket ujian. Lepas dari paket tersebut dulu."
        return None

    @property
    def has_empty_option_e(self):
        return not bool(str(self.option_e).strip() or self.image_e)

    def clean(self):
        super().clean()
        if self.correct_answer:
            self.correct_answer = self.correct_answer.upper()
            if self.correct_answer not in ['A', 'B', 'C', 'D', 'E']:
                raise ValidationError({'correct_answer': 'Kunci jawaban harus berupa salah satu dari A, B, C, D, atau E.'})

    def save(self, *args, **kwargs):
        if self.correct_answer:
            self.correct_answer = self.correct_answer.upper()
        super().save(*args, **kwargs)

    def get_image_url(self, field_name='question_image'):
        """Smart URL resolver handling remote URLs (Supabase), base64, and local/VPS media storage."""
        val = getattr(self, field_name, None)
        if not val:
            return None
        s = str(val).strip()
        if not s or s.lower() == 'none' or s == '':
            return None
        if s.startswith('http://') or s.startswith('https://') or s.startswith('data:') or s.startswith('//'):
            return s
        try:
            return val.url
        except Exception:
            from django.conf import settings
            media_url = getattr(settings, 'MEDIA_URL', '/media/')
            if not media_url.endswith('/'):
                media_url += '/'
            return f"{media_url}{s.lstrip('/')}"

    @property
    def image_url(self):
        """Returns the resolved URL for question_image."""
        return self.get_image_url('question_image')

    @property
    def image_a_url(self):
        """Returns the resolved URL for image_a."""
        return self.get_image_url('image_a')

    @property
    def image_b_url(self):
        """Returns the resolved URL for image_b."""
        return self.get_image_url('image_b')

    @property
    def image_c_url(self):
        """Returns the resolved URL for image_c."""
        return self.get_image_url('image_c')

    @property
    def image_d_url(self):
        """Returns the resolved URL for image_d."""
        return self.get_image_url('image_d')

    @property
    def image_e_url(self):
        """Returns the resolved URL for image_e."""
        return self.get_image_url('image_e')

    def __str__(self):
        subj = self.subject.name if self.subject else "Umum"
        lvl = f"Kelas {self.level}" if self.level else "Semua Tingkat"
        preview = self.question_text[:60] + ('...' if len(self.question_text) > 60 else '')
        return f"[{subj} - {lvl}] {preview}"

    def get_options(self):
        """Helper to return options structure with smart image_url resolution for templates."""
        opts = [
            ('A', self.option_a, self.image_a, 'image_a'),
            ('B', self.option_b, self.image_b, 'image_b'),
            ('C', self.option_c, self.image_c, 'image_c'),
            ('D', self.option_d, self.image_d, 'image_d'),
            ('E', self.option_e, self.image_e, 'image_e'),
        ]
        return [
            {
                'key': key,
                'label': key,
                'text': text,
                'image': img,
                'image_url': self.get_image_url(field_key),
                'is_correct': self.correct_answer == key
            }
            for key, text, img, field_key in opts
        ]


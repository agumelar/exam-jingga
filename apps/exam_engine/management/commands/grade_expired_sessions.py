"""
Menilai sesi aktif atau terkunci yang waktunya sudah habis.

Tanpa ini, siswa yang browsernya mati menjelang akhir ujian tertinggal berstatus aktif
dengan nilai 0 dan tidak masuk rekap. Dijalankan tiap 2 menit oleh scripts/exam_jingga_grader.timer.
"""
from django.core.management.base import BaseCommand

from apps.exam_engine.models import ExamSession
from apps.exam_engine.utils import grade_exam_session


class Command(BaseCommand):
    help = "Nilai otomatis sesi ujian yang sisa waktunya sudah habis."

    def handle(self, *args, **options):
        graded = 0
        sessions = ExamSession.objects.filter(status__in=['active', 'locked']).select_related('schedule', 'schedule__exam')
        for session in sessions.iterator():
            if session.calculate_remaining_seconds() <= 0:
                grade_exam_session(session)
                graded += 1
        if graded:
            self.stdout.write(f"{graded} sesi kedaluwarsa dinilai.")

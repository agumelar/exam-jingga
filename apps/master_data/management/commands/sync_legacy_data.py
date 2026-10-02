import sys
from django.core.management.base import BaseCommand
from apps.master_data.services.legacy_db_sync import legacy_db_sync_service


class Command(BaseCommand):
    help = 'Menyinkronkan seluruh data dari database Exam Jingga awal (Bank Soal, Siswa, Guru, Kelas, Jurusan)'

    def handle(self, *args, **options):
        self.stdout.write(self.style.MIGRATE_HEADING("=================================================="))
        self.stdout.write(self.style.MIGRATE_HEADING("  SINKRONISASI LENGKAP DATABASE EXAM JINGGA AWAL  "))
        self.stdout.write(self.style.MIGRATE_HEADING("=================================================="))
        self.stdout.write(f"Endpoint: {legacy_db_sync_service.api_url}\n")

        def on_progress(msg):
            self.stdout.write(self.style.WARNING(f"[*] {msg}"))

        try:
            res = legacy_db_sync_service.sync_all(on_progress=on_progress)

            if res.get('success'):
                self.stdout.write("\n" + self.style.SUCCESS("=================================================="))
                self.stdout.write(self.style.SUCCESS("           SINKRONISASI SUKSES 100%               "))
                self.stdout.write(self.style.SUCCESS("=================================================="))
                self.stdout.write(self.style.SUCCESS(res.get('summary', '')))
            else:
                self.stdout.write(self.style.ERROR(f"\n[!] Gagal: {res.get('error')}"))
                sys.exit(1)
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"\n[!] Kesalahan: {str(e)}"))
            sys.exit(1)

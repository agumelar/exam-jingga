import sys
from django.core.management.base import BaseCommand
from apps.master_data.models import MasterSyncLog
from apps.master_data.services.openapi_sync import MasterDataSyncService


class Command(BaseCommand):
    help = 'Sinkronisasi seluruh Data Master (Jurusan, Kelas, Guru, Siswa) dari data.smkn1rongga.sch.id'

    def add_arguments(self, parser):
        parser.add_argument(
            '--url',
            type=str,
            help='Base URL server master data pusat (default: https://data.smkn1rongga.sch.id)'
        )
        parser.add_argument(
            '--otomatis',
            action='store_true',
            help='Dipakai timer systemd tiap malam; dicatat sebagai sinkron otomatis'
        )
        parser.add_argument(
            '--token',
            type=str,
            help='Bearer Access Token Keycloak jika diperlukan'
        )

    def handle(self, *args, **options):
        base_url = options.get('url')
        token = options.get('token')
        source = 'otomatis' if options.get('otomatis') else 'perintah'

        self.stdout.write(self.style.MIGRATE_HEADING("=================================================="))
        self.stdout.write(self.style.MIGRATE_HEADING("   EXAM JINGGA - SINKRONISASI DATA MASTER PUSAT   "))
        self.stdout.write(self.style.MIGRATE_HEADING("=================================================="))

        service = MasterDataSyncService(base_url=base_url)
        self.stdout.write(f"Target Server: {service.base_url}\n")

        def on_progress(msg):
            self.stdout.write(self.style.WARNING(f"[*] {msg}"))

        try:
            result = service.sync_all(bearer_token=token, on_progress=on_progress)
        except Exception as e:
            MasterSyncLog.record(source, 'all', error=e)
            self.stdout.write(self.style.ERROR(f"\n[!] Terjadi kesalahan saat sinkronisasi: {str(e)}"))
            sys.exit(1)

        if not result.get('success'):
            MasterSyncLog.record(source, 'all', error=result.get('error') or 'Sinkron gagal tanpa keterangan')
            self.stdout.write(self.style.ERROR(f"\n[!] Gagal: {result.get('error')}"))
            sys.exit(1)

        MasterSyncLog.record(source, 'all', result)
        self.stdout.write("\n" + self.style.SUCCESS("=================================================="))
        self.stdout.write(self.style.SUCCESS("           SINKRONISASI BERHASIL 100%             "))
        self.stdout.write(self.style.SUCCESS("=================================================="))
        self.stdout.write(f"- Jurusan / Keahlian: {result.get('majors_count', 0)}")
        self.stdout.write(f"- Kelas / Rombel    : {result.get('classes_count', 0)}")
        self.stdout.write(f"- Guru & GTK        : {result.get('teachers_count', 0)}")
        self.stdout.write(f"- Siswa Terdaftar   : {result.get('students_count', 0)}")
        self.stdout.write(f"- Siswa dinonaktifkan: {result.get('students_deactivated', 0)}")
        self.stdout.write(self.style.SUCCESS(f"\n{result.get('message')}\n"))

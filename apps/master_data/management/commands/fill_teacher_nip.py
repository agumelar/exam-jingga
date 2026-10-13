"""
Mengisi NIP guru Exam dari data staf pusat lewat pencocokan nama.

Bawaannya uji kering (tidak menulis apa pun); tambahkan --apply untuk menyimpan. Guru yang sudah
punya NIP dan NIP yang sudah dipakai guru lain tidak disentuh. Setelah ini, NIP dari username
Keycloak saat guru login menjadi konfirmasi akhir.
"""
from django.core.management.base import BaseCommand
from django.db import transaction
from django.db.models import Q

from apps.master_data.models import Teacher
from apps.master_data.services.openapi_sync import MasterDataSyncService
from apps.master_data.services.teacher_identity import match_staff_to_teachers


class Command(BaseCommand):
    help = "Isi NIP guru dari data staf pusat berdasarkan nama (uji kering kecuali --apply)."

    def add_arguments(self, parser):
        parser.add_argument('--apply', action='store_true', help='Simpan NIP hasil pencocokan.')

    def handle(self, *args, **options):
        staff = MasterDataSyncService().fetch_master_api('/v1/staff', params={'pageSize': 1000})
        used_nips = set(Teacher.objects.exclude(Q(nip=None) | Q(nip='')).values_list('nip', flat=True))
        open_staff = [s for s in staff if s.get('nip') and str(s['nip']).strip() not in used_nips]
        teachers = Teacher.objects.filter(Q(nip=None) | Q(nip=''))

        result = match_staff_to_teachers(open_staff, teachers)
        mode = "Disimpan" if options['apply'] else "Uji kering, tidak ada yang disimpan"
        self.stdout.write(f"{mode}. Cocok: {len(result['matches'])}, ganda: {len(result['ambiguous'])}, "
                          f"tidak ditemukan di Exam: {len(result['unmatched_staff'])}.")
        for teacher, nip in result['matches']:
            self.stdout.write(f"  {teacher.full_name} -> NIP ...{nip[-4:]}")
        if result['ambiguous']:
            self.stdout.write(f"Nama ganda, isi manual: {', '.join(result['ambiguous'])}")
        if result['unmatched_staff']:
            self.stdout.write(f"Staf pusat tanpa pasangan di Exam: {', '.join(result['unmatched_staff'])}")

        if options['apply']:
            with transaction.atomic():
                for teacher, nip in result['matches']:
                    Teacher.objects.filter(pk=teacher.pk).update(nip=nip)

import logging
import uuid
import requests
from django.conf import settings
from django.db import transaction
from django.contrib.auth import get_user_model
from apps.accounts.models import Role
from apps.accounts.services.keycloak_auth import get_m2m_access_token
from apps.master_data.models import Major, ClassRoom, Teacher, Student
from apps.master_data.services.teacher_identity import real_nip

logger = logging.getLogger(__name__)
User = get_user_model()


class SyncSourceError(RuntimeError):
    """Data pusat tidak bisa dibaca (token, izin, jaringan, atau isi kosong); sinkron dibatalkan."""


class SyncIncompleteError(SyncSourceError):
    """Tarikan data pusat terputus di tengah; hasilnya tidak boleh diperlakukan sebagai data lengkap."""


class MasterDataSyncService:
    """
    Service untuk sinkronisasi data master dari data.smkn1rongga.sch.id / SDP OpenAPI.
    Mendukung Machine-to-Machine (M2M) Keycloak token, paginasi otomatis, dan ekstraksi
    Jurusan, Rombel, Guru, dan Siswa secara konsisten dengan single source of truth.
    """

    def __init__(self, base_url=None):
        self.base_url = (base_url or getattr(settings, 'DATA_MASTER_BASE_URL', 'https://data.smkn1rongga.sch.id')).rstrip('/')

    def _resolve_token(self, bearer_token=None):
        if bearer_token:
            return bearer_token
        try:
            return get_m2m_access_token()
        except Exception as e:
            logger.warning(f"Token data pusat gagal: {e}")
            raise SyncSourceError(f"Token akses data pusat gagal diambil dari Keycloak: {e}") from e

    def _get_headers(self, bearer_token=None):
        headers = {
            'Accept': 'application/json',
            'Content-Type': 'application/json',
            'User-Agent': 'ExamJingga-DATH-Sync/2026.1'
        }
        token = self._resolve_token(bearer_token)
        if token:
            headers['Authorization'] = f"Bearer {token}"
        return headers

    def fetch_master_api(self, endpoint, params=None, bearer_token=None, timeout=25):
        """
        Helper fetch data master API dengan response parser fleksibel.
        """
        clean_endpoint = endpoint if endpoint.startswith('/') else f"/{endpoint}"
        url = f"{self.base_url}{clean_endpoint}"
        headers = self._get_headers(bearer_token=bearer_token)

        try:
            response = requests.get(url, params=params or {}, headers=headers, timeout=timeout)
        except requests.RequestException as e:
            logger.warning(f"Error fetching from {url}: {e}")
            raise RuntimeError(f"Gagal terhubung ke {url}: {str(e)}")

        if response.status_code == 401:
            raise PermissionError("Sesi otorisasi SSO / Bearer Token Anda tidak valid atau kedaluwarsa.")

        if not response.ok:
            try:
                err_body = response.json()
                msg = err_body.get('message') or f"Status code: {response.status_code}"
            except Exception:
                msg = f"HTTP {response.status_code} ({response.reason})"
            raise RuntimeError(f"Gagal mengambil data dari {endpoint}: {msg}")

        try:
            json_data = response.json()
        except Exception:
            return []

        if isinstance(json_data, list):
            return json_data
        if isinstance(json_data, dict):
            for key in ['data', 'items', 'students', 'staff', 'users', 'results']:
                if isinstance(json_data.get(key), list):
                    return json_data[key]
        return []

    def fetch_all_students_paginated(self, bearer_token=None, on_progress=None):
        """
        Mengambil seluruh data siswa aktif dari GET /v1/students dengan paginasi otomatis.
        Bila satu halaman gagal, sinkron dihentikan (SyncIncompleteError) agar data parsial
        tidak dianggap lengkap dan tidak memicu penonaktifan siswa.

        Paginasi API pusat pernah tidak stabil (baris yang sama muncul di dua halaman, baris lain
        tidak pernah muncul), jadi halaman diambil besar, baris digabung per id, dan jumlah siswa
        unik harus sama dengan meta.total.
        """
        unique = {}
        page = 1
        page_size = 1000
        page_count = 1
        expected_total = None

        headers = self._get_headers(bearer_token=bearer_token)
        url = f"{self.base_url}/v1/students"

        while page <= page_count:
            if on_progress:
                on_progress(f"Mengambil halaman siswa {page} dari {page_count}...")

            params = {
                'page': page,
                'pageSize': page_size,
                'status': 'ACTIVE'
            }

            try:
                response = requests.get(url, params=params, headers=headers, timeout=25)
                response.raise_for_status()
                res_json = response.json()
            except Exception as e:
                if page == 1:
                    logger.warning(f"Paginated fetch failed on first page: {e}")
                    raise SyncSourceError(f"Data siswa pusat tidak bisa diambil: {e}") from e
                raise SyncIncompleteError(f"Halaman siswa {page} dari {page_count} gagal diambil: {e}") from e

            items = res_json.get('data', []) if isinstance(res_json, dict) else res_json
            if isinstance(items, list):
                for item in items:
                    key = (item.get('id') or item.get('nis')) if isinstance(item, dict) else None
                    unique[key or f'tanpa-kunci-{len(unique)}'] = item

            meta = res_json.get('meta', {}) if isinstance(res_json, dict) else {}
            page_count = meta.get('totalPages') or meta.get('pageCount') or 1
            if meta.get('total') is not None:
                expected_total = int(meta['total'])
            page += 1

        all_students = list(unique.values())
        if not all_students:
            raise SyncSourceError("Data pusat mengembalikan 0 siswa; sinkron dibatalkan agar data Exam tidak berubah.")
        if expected_total is not None and len(all_students) != expected_total:
            raise SyncIncompleteError(
                f"Data pusat tidak konsisten: diterima {len(all_students)} siswa unik dari {expected_total} "
                "yang dilaporkan. Sinkron dibatalkan agar data Exam tidak berubah."
            )

        return all_students

    def sync_majors(self, raw_students=None, bearer_token=None, on_progress=None):
        """
        1. Tarik Data Jurusan dari Pusat / Ekstrak dari data siswa
        """
        if on_progress:
            on_progress("Menghubungkan ke data.smkn1rongga.sch.id...")

        if raw_students is None:
            raw_students = self.fetch_all_students_paginated(bearer_token=bearer_token, on_progress=on_progress)

        if on_progress:
            on_progress("Mengekstrak daftar Konsentrasi Keahlian / Jurusan...")

        major_names = set()
        for s in (raw_students or []):
            curr_class = s.get('currentClass') or {}
            class_code = curr_class.get('code') or curr_class.get('name') if isinstance(curr_class, dict) else None
            m_name = (
                s.get('major')
                or s.get('jurusan')
                or s.get('competency')
                or s.get('konsentrasi_keahlian')
                or class_code
            )
            if m_name and str(m_name).strip():
                major_names.add(str(m_name).strip())

        # Standar Jurusan Default SMKN 1 Rongga
        default_majors = [
            ('RPL', 'Rekayasa Perangkat Lunak'),
            ('TBSM', 'Teknik Sepeda Motor'),
            ('ATPH', 'Agribisnis Tanaman Pangan dan Hortikultura'),
            ('TKRO', 'Teknik Kendaraan Ringan Otomotif')
        ]

        synced_majors = []
        with transaction.atomic():
            for code, name in default_majors:
                m, _ = Major.objects.update_or_create(code=code, defaults={'name': name})
                synced_majors.append(m)

            for name in major_names:
                upper = name.upper()
                code = None
                if 'PERANGKAT LUNAK' in upper or 'PPLG' in upper or 'RPL' in upper:
                    code = 'RPL'
                elif 'SEPEDA MOTOR' in upper or 'TBSM' in upper or 'TSM' in upper:
                    code = 'TBSM'
                elif 'TANAMAN' in upper or 'PANGAN' in upper or 'ATPH' in upper or 'AT' in upper.replace('-', ' ').split():
                    code = 'ATPH'
                elif 'KENDARAAN' in upper or 'TKRO' in upper or 'TO' in upper.replace('-', ' ').split():
                    code = 'TKRO'

                if code:
                    major, _ = Major.objects.update_or_create(
                        code=code,
                        defaults={'name': name if len(name) > 4 else dict(default_majors).get(code, name)}
                    )
                    if major not in synced_majors:
                        synced_majors.append(major)

        return {
            'success': True,
            'count': len(synced_majors),
            'majors': synced_majors,
            'message': f"Berhasil menyinkronkan {len(synced_majors)} Jurusan."
        }

    def sync_classes(self, raw_students=None, bearer_token=None, on_progress=None):
        """
        2. Tarik Data Kelas / Rombel dari Pusat
        """
        if on_progress:
            on_progress("Menghubungkan ke data.smkn1rongga.sch.id...")

        self.sync_majors(raw_students=raw_students, bearer_token=bearer_token, on_progress=on_progress)
        major_map = {m.code.upper(): m for m in Major.objects.all()}

        if raw_students is None:
            raw_students = self.fetch_all_students_paginated(bearer_token=bearer_token, on_progress=on_progress)

        if on_progress:
            on_progress("Mengekstrak Rombel Kelas Tahun Ajaran Terbaru...")

        class_entries = {}
        for s in (raw_students or []):
            curr_class = s.get('currentClass')
            if isinstance(curr_class, dict):
                c_name = curr_class.get('name') or curr_class.get('code')
                c_level = curr_class.get('gradeLevel')
                if not c_level:
                    upper = str(c_name or '').upper().strip()
                    if upper.startswith(('XII ', '12 ', 'XII-', 'XII_')) or upper.startswith('12') or upper.startswith('XII'):
                        c_level = 12
                    elif upper.startswith(('XI ', '11 ', 'XI-', 'XI_')) or upper.startswith('11') or upper.startswith('XI'):
                        c_level = 11
                    else:
                        c_level = 10
                c_id = curr_class.get('id')
                if c_name:
                    class_entries[str(c_name).strip()] = {
                        'name': str(c_name).strip(),
                        'level': int(c_level),
                        'id': c_id
                    }
            else:
                cls = s.get('class_name') or s.get('kelas') or s.get('rombel') or s.get('class')
                if cls and str(cls).strip():
                    name_clean = str(cls).strip()
                    upper = name_clean.upper()
                    lvl = 10
                    if upper.startswith(('XI ', '11 ', 'XI-', 'XI_')):
                        lvl = 11
                    elif upper.startswith(('XII ', '12 ', 'XII-', 'XII_')):
                        lvl = 12
                    class_entries[name_clean] = {'name': name_clean, 'level': lvl, 'id': None}

        synced_classes = []
        with transaction.atomic():
            for name, meta in class_entries.items():
                upper = name.upper()
                level = meta['level']

                matched_major = None
                if 'RPL' in upper or 'PPLG' in upper:
                    matched_major = major_map.get('RPL')
                elif 'TBSM' in upper or 'TSM' in upper:
                    matched_major = major_map.get('TBSM')
                elif 'ATPH' in upper or 'AT' in upper.replace('-', ' ').split():
                    matched_major = major_map.get('ATPH')
                elif 'TKRO' in upper or 'TO' in upper.replace('-', ' ').split():
                    matched_major = major_map.get('TKRO')

                classroom, _ = ClassRoom.objects.update_or_create(
                    name=name,
                    defaults={
                        'level': level,
                        'major': matched_major
                    }
                )
                synced_classes.append(classroom)

        return {
            'success': True,
            'count': len(synced_classes),
            'classes': synced_classes,
            'message': f"Berhasil menyinkronkan {len(synced_classes)} Kelas / Rombel."
        }

    def sync_teachers(self, raw_staff=None, bearer_token=None, on_progress=None):
        """
        3. Cocokkan Data Guru Pusat (GET /v1/staff) dengan guru Exam lewat NIP.

        NIP adalah kunci identitas guru (username Keycloak guru juga NIP). Sinkron ini tidak membuat
        guru atau akun: guru pusat yang belum ada di Exam dilaporkan agar admin menambahkannya
        lewat Master Guru, karena guru lama di Exam baru ber-NIP setelah login SSO atau fill_teacher_nip.
        """
        if on_progress:
            on_progress("Menghubungkan ke data.smkn1rongga.sch.id/v1/staff...")

        if raw_staff is None:
            try:
                raw_staff = self.fetch_master_api('/v1/staff', params={'pageSize': 1000}, bearer_token=bearer_token)
            except SyncSourceError:
                raise
            except Exception as e:
                raise SyncSourceError(f"Data guru pusat tidak bisa diambil: {e}") from e
            if not raw_staff:
                raise SyncSourceError("Data pusat mengembalikan 0 guru; sinkron dibatalkan agar data Exam tidak berubah.")

        exam_nips = set(Teacher.objects.exclude(nip=None).exclude(nip='').values_list('nip', flat=True))
        matched, unmatched = [], []
        for t in raw_staff:
            nip = real_nip(t.get('nip'))
            name = t.get('fullName') or t.get('full_name') or t.get('name') or '-'
            if not nip:
                continue
            if nip in exam_nips:
                matched.append(name)
            elif str(t.get('ptkType') or '').strip().lower() == 'guru':
                unmatched.append(name)

        message = f"{len(matched)} guru pusat cocok dengan guru Exam lewat NIP."
        if unmatched:
            message += (f" {len(unmatched)} guru pusat belum tertaut di Exam (tambahkan lewat Master Guru, "
                        f"atau tunggu guru tersebut login SSO): {', '.join(sorted(unmatched))}.")
        return {
            'success': True,
            'count': len(matched),
            'unmatched': sorted(unmatched),
            'message': message,
        }

    def sync_students(self, raw_students=None, bearer_token=None, on_progress=None):
        """
        4. Tarik Data Siswa dari Pusat (GET /v1/students)
        """
        if on_progress:
            on_progress("1/3 Menghubungkan ke server data master pusat...")

        if raw_students is None:
            raw_students = self.fetch_all_students_paginated(bearer_token=bearer_token, on_progress=on_progress)

        if on_progress:
            on_progress(f"2/3 Memperbarui Rombel & Memetakan {len(raw_students)} Siswa...")

        self.sync_classes(raw_students=raw_students, bearer_token=bearer_token, on_progress=on_progress)

        class_map = {c.name.strip().upper(): c for c in ClassRoom.objects.all()}
        major_code_map = {m.code.upper(): m for m in Major.objects.all()}

        if on_progress:
            on_progress("3/3 Menyimpan siswa ke database CBT...")

        synced_students = []
        with transaction.atomic():
            for s in (raw_students or []):
                nis = str(s.get('nis') or s.get('nisn') or '').strip()
                if not nis:
                    continue

                full_name = s.get('fullName') or s.get('full_name') or s.get('name') or 'Siswa'
                
                # Extract class name from currentClass dict or plain field
                curr_class = s.get('currentClass')
                class_name = ''
                if isinstance(curr_class, dict):
                    class_name = str(curr_class.get('name') or curr_class.get('code') or '').strip().upper()
                else:
                    class_name = str(s.get('class_name') or s.get('kelas') or s.get('rombel') or s.get('class') or '').strip().upper()

                matched_class = class_map.get(class_name)
                matched_major = None

                if matched_class and matched_class.major:
                    matched_major = matched_class.major
                elif class_name:
                    if 'RPL' in class_name or 'PPLG' in class_name:
                        matched_major = major_code_map.get('RPL')
                    elif 'TBSM' in class_name or 'TSM' in class_name:
                        matched_major = major_code_map.get('TBSM')
                    elif 'ATPH' in class_name or 'AT' in class_name.replace('-', ' ').split():
                        matched_major = major_code_map.get('ATPH')
                    elif 'TKRO' in class_name or 'TO' in class_name.replace('-', ' ').split():
                        matched_major = major_code_map.get('TKRO')

                raw_status = str(s.get('status') or 'aktif').lower()
                status = 'aktif' if raw_status in ['active', 'aktif'] else raw_status
                email = s.get('email') or f"{nis}@student.smkn1rongga.sch.id"

                sso_id_str = s.get('id') or s.get('sso_id')
                sso_id = None
                if sso_id_str:
                    try:
                        sso_id = uuid.UUID(str(sso_id_str))
                    except (ValueError, TypeError):
                        sso_id = None

                user = User.objects.filter(nis=nis).first()
                if not user and sso_id:
                    user = User.objects.filter(sso_id=sso_id).first()
                if not user:
                    user = User.objects.filter(username=nis).first()

                if user:
                    if not user.is_superuser:
                        user.full_name = full_name
                        user.nis = nis
                        user.email = email
                        user.role = Role.SISWA
                        user.is_active = status == 'aktif'
                        if sso_id and not user.sso_id:
                            user.sso_id = sso_id
                        user.save()
                else:
                    user = User(
                        username=nis,
                        nis=nis,
                        full_name=full_name,
                        email=email,
                        role=Role.SISWA,
                        sso_id=sso_id
                    )
                    user.set_unusable_password()
                    user.save()

                student, _ = Student.objects.update_or_create(
                    nis=nis,
                    defaults={
                        'user': user,
                        'full_name': full_name,
                        'class_room': matched_class,
                        'major': matched_major,
                        'status': status,
                        'email': email,
                        'sso_id': sso_id
                    }
                )
                synced_students.append(student)

        deactivated = self._deactivate_missing_students({s.nis for s in synced_students})

        return {
            'success': True,
            'count': len(synced_students),
            'deactivated': deactivated,
            'students': synced_students,
            'message': f"Sinkronisasi berhasil: {len(synced_students)} siswa tersinkron, {deactivated} siswa yang tidak ada lagi di data pusat dinonaktifkan."
        }

    def _deactivate_missing_students(self, fetched_nis):
        """
        Siswa aktif yang tidak ada lagi di data pusat dinonaktifkan (status dan login).
        Rem pengaman: bila data pusat yang diterima kurang dari separuh siswa aktif, penonaktifan
        dibatalkan karena lebih mungkin data pusat bermasalah daripada separuh siswa keluar.
        """
        active = Student.objects.filter(status='aktif')
        if not fetched_nis or len(fetched_nis) < active.count() * 0.5:
            logger.warning("Penonaktifan siswa dilewati: data pusat hanya %s siswa", len(fetched_nis))
            return 0
        missing = active.exclude(nis__in=fetched_nis)
        user_ids = list(missing.exclude(user=None).values_list('user_id', flat=True))
        count = missing.update(status='keluar')
        User.objects.filter(id__in=user_ids, is_superuser=False).update(is_active=False)
        return count

    def sync_all(self, bearer_token=None, on_progress=None):
        """
        Tarik seluruh data master. Data siswa diambil sekali lalu dipakai untuk jurusan, kelas, dan siswa.
        """
        raw_students = self.fetch_all_students_paginated(bearer_token=bearer_token, on_progress=on_progress)
        majors_res = self.sync_majors(raw_students=raw_students, bearer_token=bearer_token, on_progress=on_progress)
        classes_res = self.sync_classes(raw_students=raw_students, bearer_token=bearer_token, on_progress=on_progress)
        students_res = self.sync_students(raw_students=raw_students, bearer_token=bearer_token, on_progress=on_progress)
        teachers_res = self.sync_teachers(bearer_token=bearer_token, on_progress=on_progress)

        return {
            'success': True,
            'majors_count': majors_res.get('count', 0),
            'classes_count': classes_res.get('count', 0),
            'teachers_count': teachers_res.get('count', 0),
            'students_count': students_res.get('count', 0),
            'message': (
                f"Data Master diperbarui dari {self.base_url}. "
                f"{students_res.get('count', 0)} Siswa Terdaftar, "
                f"{classes_res.get('count', 0)} Rombel Kelas. {teachers_res.get('message', '')}"
            )
        }


master_data_sync_service = MasterDataSyncService()

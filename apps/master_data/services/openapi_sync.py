import logging
import uuid
import requests
from django.conf import settings
from django.db import transaction
from django.contrib.auth import get_user_model
from apps.accounts.models import Role
from apps.accounts.services.keycloak_auth import get_m2m_access_token
from apps.master_data.models import Major, ClassRoom, Teacher, Student

logger = logging.getLogger(__name__)
User = get_user_model()


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
            logger.info(f"M2M Keycloak token fallback: {e}")
            return None

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
        """
        all_students = []
        page = 1
        page_size = 100
        page_count = 1

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
            except Exception as e:
                logger.warning(f"Paginated fetch failed on page {page}: {e}")
                break

            if not response.ok:
                break

            try:
                res_json = response.json()
            except Exception:
                break

            items = res_json.get('data', []) if isinstance(res_json, dict) else res_json
            if isinstance(items, list):
                all_students.extend(items)

            meta = res_json.get('meta', {}) if isinstance(res_json, dict) else {}
            page_count = meta.get('pageCount', 1)
            page += 1

        # Fallback if paginated endpoint returned nothing
        if not all_students:
            try:
                all_students = self.fetch_master_api('/v1/students', bearer_token=bearer_token)
            except Exception:
                try:
                    all_students = self.fetch_master_api('/students', bearer_token=bearer_token)
                except Exception as e:
                    logger.warning(f"Fallback student fetch failed: {e}")
                    all_students = []

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
                elif 'TANAMAN' in upper or 'PANGAN' in upper or 'ATPH' in upper or 'AT' in upper:
                    code = 'ATPH'
                elif 'KENDARAAN' in upper or 'TKRO' in upper or 'TO' in upper:
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
                elif 'ATPH' in upper or 'AT' in upper:
                    matched_major = major_map.get('ATPH')
                elif 'TKRO' in upper or 'TO' in upper:
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
        3. Tarik Data Guru & GTK dari Pusat (GET /v1/staff)
        """
        if on_progress:
            on_progress("Menghubungkan ke data.smkn1rongga.sch.id/v1/staff...")

        if raw_staff is None:
            try:
                raw_staff = self.fetch_master_api('/v1/staff', bearer_token=bearer_token)
            except Exception:
                try:
                    raw_staff = self.fetch_master_api('/staff', bearer_token=bearer_token)
                except Exception as e:
                    logger.warning(f"Gagal fetch staff: {e}")
                    raw_staff = []

        if on_progress:
            on_progress(f"Memproses {len(raw_staff)} Guru & Tenaga Pendidik...")

        synced_teachers = []
        with transaction.atomic():
            for t in (raw_staff or []):
                full_name = t.get('fullName') or t.get('full_name') or t.get('name') or 'Guru'
                nip = str(t.get('nip') or '').strip() or None
                email = (t.get('email') or f"{nip or 'guru'}@smkn1rongga.sch.id").lower().strip()
                raw_role = (t.get('ptkType') or t.get('role_level') or t.get('role') or 'guru').lower()
                
                role_level = 'admin' if any(k in raw_role for k in ['admin', 'kepala']) else ('kurikulum' if 'kurikulum' in raw_role else 'guru')

                sso_id_str = t.get('id') or t.get('sso_id')
                sso_id = None
                if sso_id_str:
                    try:
                        sso_id = uuid.UUID(str(sso_id_str))
                    except (ValueError, TypeError):
                        sso_id = None

                username = (email.split('@')[0] if email else nip or f"guru_{uuid.uuid4().hex[:6]}").replace('.', '_')
                user = None
                if sso_id:
                    user = User.objects.filter(sso_id=sso_id).first()
                if not user and email:
                    user = User.objects.filter(email__iexact=email).first()
                if not user:
                    user = User.objects.filter(username=username).first()

                user_role = Role.ADMIN if role_level == 'admin' else (Role.KURIKULUM if role_level == 'kurikulum' else Role.GURU)

                if user:
                    user.full_name = full_name
                    user.email = email
                    user.role = user_role
                    user.is_staff = True
                    if sso_id and not user.sso_id:
                        user.sso_id = sso_id
                    user.save()
                else:
                    user = User.objects.create(
                        username=username,
                        email=email,
                        full_name=full_name,
                        role=user_role,
                        sso_id=sso_id,
                        is_staff=True
                    )
                    user.set_password("Jingga123")
                    user.save()

                teacher, _ = Teacher.objects.update_or_create(
                    email=email,
                    defaults={
                        'user': user,
                        'full_name': full_name,
                        'nip': nip,
                        'role_level': role_level,
                        'sso_id': sso_id
                    }
                )
                synced_teachers.append(teacher)

        return {
            'success': True,
            'count': len(synced_teachers),
            'teachers': synced_teachers,
            'message': f"Berhasil menyinkronkan {len(synced_teachers)} Data Guru & GTK."
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
                    elif 'ATPH' in class_name or 'AT' in class_name:
                        matched_major = major_code_map.get('ATPH')
                    elif 'TKRO' in class_name or 'TO' in class_name:
                        matched_major = major_code_map.get('TKRO')

                raw_status = str(s.get('status') or 'aktif').lower()
                status = 'aktif' if raw_status in ['active', 'aktif'] else raw_status
                email = s.get('email') or f"{nis}@student.smkn1rongga.sch.id"
                password_plain = s.get('password_plain') or f"jingga{nis}"

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
                    user.full_name = full_name
                    user.nis = nis
                    user.email = email
                    user.role = Role.SISWA
                    if sso_id and not user.sso_id:
                        user.sso_id = sso_id
                    user.save()
                else:
                    user = User.objects.create(
                        username=nis,
                        nis=nis,
                        full_name=full_name,
                        email=email,
                        role=Role.SISWA,
                        sso_id=sso_id
                    )
                    user.set_password(password_plain)
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
                        'password_plain': password_plain,
                        'sso_id': sso_id
                    }
                )
                synced_students.append(student)

        return {
            'success': True,
            'count': len(synced_students),
            'students': synced_students,
            'message': f"Sinkronisasi berhasil! Total {len(synced_students)} siswa tersinkronisasi lengkap dari SDP."
        }

    def sync_all(self, bearer_token=None, on_progress=None):
        """
        Tarik Seluruh Data Master Sekaligus Secara Berurutan
        """
        majors_res = self.sync_majors(bearer_token=bearer_token, on_progress=on_progress)
        classes_res = self.sync_classes(bearer_token=bearer_token, on_progress=on_progress)
        teachers_res = self.sync_teachers(bearer_token=bearer_token, on_progress=on_progress)
        students_res = self.sync_students(bearer_token=bearer_token, on_progress=on_progress)

        return {
            'success': True,
            'majors_count': majors_res.get('count', 0),
            'classes_count': classes_res.get('count', 0),
            'teachers_count': teachers_res.get('count', 0),
            'students_count': students_res.get('count', 0),
            'message': (
                f"Seluruh Data Master telah diperbarui dari {self.base_url}. "
                f"{students_res.get('count', 0)} Siswa Terdaftar, "
                f"{classes_res.get('count', 0)} Rombel Kelas, "
                f"{teachers_res.get('count', 0)} Guru & GTK."
            )
        }


master_data_sync_service = MasterDataSyncService()

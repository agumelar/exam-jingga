import logging
import uuid
import requests
from django.conf import settings
from django.db import transaction
from django.contrib.auth import get_user_model
from apps.accounts.models import Role
from apps.master_data.models import Major, ClassRoom, Teacher, Student, Subject, TeacherAssignment
from apps.questions.models import Question

logger = logging.getLogger(__name__)
User = get_user_model()


class LegacyDatabaseSyncService:
    """
    Service untuk menyinkronkan seluruh data historis dan bank soal dari
    database Exam Jingga awal (Supabase Engine / Kong REST API) ke model Django.
    """

    def __init__(self, base_url=None, anon_key=None):
        self.base_url = (base_url or getattr(settings, 'VITE_SUPABASE_URL', 'https://dbexam.smkn1rongga.sch.id/api/kong')).rstrip('/')
        if not self.base_url.endswith('/rest/v1'):
            self.api_url = f"{self.base_url}/rest/v1"
        else:
            self.api_url = self.base_url

        self.anon_key = anon_key or getattr(
            settings,
            'VITE_SUPABASE_ANON_KEY',
            'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJyb2xlIjoiYW5vbiIsImlzcyI6InN1cGFiYXNlIiwiaWF0IjoxNzg2ODE0MzE2LCJleHAiOjE5NDQ0OTQzMTZ9.YJWx2qWGTJGdHfYkoFXBMq8hwh2Vin3pX-Wyr-Wk-y0'
        )

    def _get_headers(self):
        return {
            'apikey': self.anon_key,
            'Authorization': f'Bearer {self.anon_key}',
            'Accept': 'application/json',
            'Content-Type': 'application/json',
            'User-Agent': 'ExamJingga-DATH-LegacyMigrator/2026.1'
        }

    def fetch_all(self, table_name, select='*', batch_size=1000):
        """Fetch all records with automatic pagination support."""
        url = f"{self.api_url}/{table_name}"
        headers = self._get_headers()
        records = []
        offset = 0

        while True:
            params = {
                'select': select,
                'limit': batch_size,
                'offset': offset
            }
            try:
                response = requests.get(url, headers=headers, params=params, timeout=30)
                if not response.ok:
                    logger.error(f"Gagal mengambil data dari {table_name}: {response.status_code} - {response.text[:200]}")
                    break
                data = response.json()
                if not data:
                    break
                records.extend(data)
                if len(data) < batch_size:
                    break
                offset += batch_size
            except Exception as e:
                logger.error(f"Exception fetching {table_name}: {e}")
                break

        return records

    def sync_all(self, on_progress=None):
        """
        Jalankan sinkronisasi seluruh tabel secara berurutan sesuai relasi Foreign Key.
        """
        results = {}

        # 1. MAJORS
        if on_progress:
            on_progress("1/7 Menyinkronkan Jurusan (Majors)...")
        results['majors'] = self.sync_majors()

        # 2. CLASSES
        if on_progress:
            on_progress("2/7 Menyinkronkan Rombel Kelas (Classes)...")
        results['classes'] = self.sync_classes()

        # 3. SUBJECTS
        if on_progress:
            on_progress("3/7 Menyinkronkan Mata Pelajaran (Subjects)...")
        results['subjects'] = self.sync_subjects()

        # 4. TEACHERS & USERS
        if on_progress:
            on_progress("4/7 Menyinkronkan Guru & Akun PTK...")
        results['teachers'] = self.sync_teachers()

        # 5. STUDENTS & ACCOUNTS
        if on_progress:
            on_progress("5/7 Menyinkronkan 441+ Siswa & Akun Login Siswa...")
        results['students'] = self.sync_students()

        # 6. TEACHER ASSIGNMENTS
        if on_progress:
            on_progress("6/7 Menyinkronkan Penugasan Guru (Teacher Assignments)...")
        results['assignments'] = self.sync_teacher_assignments()

        # 7. QUESTIONS (BANK SOAL - 2,801+ BUTIR SOAL)
        if on_progress:
            on_progress("7/7 Menyinkronkan 2,801+ Butir Soal Bank Soal...")
        results['questions'] = self.sync_questions(on_progress=on_progress)

        return {
            'success': True,
            'results': results,
            'summary': (
                f"Sinkronisasi Data Selesai:\n"
                f"- {results['majors']} Jurusan\n"
                f"- {results['classes']} Rombel Kelas\n"
                f"- {results['subjects']} Mata Pelajaran\n"
                f"- {results['teachers']} Guru & GTK\n"
                f"- {results['students']} Siswa Terdaftar\n"
                f"- {results['assignments']} Penugasan Mengajar\n"
                f"- {results['questions']} Butir Soal Bank Soal"
            )
        }

    def sync_majors(self):
        raw = self.fetch_all('majors')
        count = 0
        with transaction.atomic():
            for item in raw:
                major_id = uuid.UUID(item['id'])
                name = item.get('name', 'Jurusan')
                upper = name.upper()

                if 'PERANGKAT LUNAK' in upper or 'RPL' in upper:
                    code = 'RPL'
                elif 'SEPEDA MOTOR' in upper or 'TBSM' in upper or 'TSM' in upper:
                    code = 'TBSM'
                elif 'TANAMAN' in upper or 'PANGAN' in upper or 'ATPH' in upper or 'AT' in upper:
                    code = 'ATPH'
                elif 'KENDARAAN' in upper or 'TKRO' in upper or 'TO' in upper:
                    code = 'TKRO'
                else:
                    code = name[:4].upper().strip()

                # Upsert safely by ID or Code
                existing = Major.objects.filter(id=major_id).first()
                if not existing:
                    existing = Major.objects.filter(code=code).first()

                if existing:
                    existing.code = code
                    existing.name = name
                    existing.save()
                else:
                    Major.objects.create(
                        id=major_id,
                        code=code,
                        name=name
                    )
                count += 1
        return count

    def sync_classes(self):
        raw = self.fetch_all('classes')
        count = 0
        with transaction.atomic():
            for item in raw:
                class_id = uuid.UUID(item['id'])
                name = item.get('name', 'Kelas')
                upper = name.upper()

                level = 10
                if upper.startswith(('XI ', '11 ', 'XI-', 'XI_')):
                    level = 11
                elif upper.startswith(('XII ', '12 ', 'XII-', 'XII_')):
                    level = 12

                major = None
                if item.get('major_id'):
                    major = Major.objects.filter(id=uuid.UUID(item['major_id'])).first()
                if not major:
                    if 'RPL' in upper:
                        major = Major.objects.filter(code='RPL').first()
                    elif 'TBSM' in upper or 'TSM' in upper:
                        major = Major.objects.filter(code='TBSM').first()
                    elif 'ATPH' in upper or 'AT' in upper:
                        major = Major.objects.filter(code='ATPH').first()
                    elif 'TKRO' in upper or 'TO' in upper:
                        major = Major.objects.filter(code='TKRO').first()

                existing = ClassRoom.objects.filter(id=class_id).first()
                if not existing:
                    existing = ClassRoom.objects.filter(name=name).first()

                if existing:
                    existing.name = name
                    existing.level = level
                    existing.major = major
                    existing.save()
                else:
                    ClassRoom.objects.create(
                        id=class_id,
                        name=name,
                        level=level,
                        major=major
                    )
                count += 1
        return count

    def sync_subjects(self):
        raw = self.fetch_all('subjects')
        count = 0
        with transaction.atomic():
            for item in raw:
                subj_id = uuid.UUID(item['id'])
                name = item.get('name', 'Mata Pelajaran')

                existing = Subject.objects.filter(id=subj_id).first()
                if not existing:
                    existing = Subject.objects.filter(name=name).first()

                if existing:
                    existing.name = name
                    existing.save()
                else:
                    Subject.objects.create(
                        id=subj_id,
                        name=name
                    )
                count += 1
        return count

    def sync_teachers(self):
        raw = self.fetch_all('teachers')
        count = 0
        with transaction.atomic():
            for item in raw:
                teacher_id = uuid.UUID(item['id'])
                full_name = item.get('full_name') or 'Guru'
                raw_role = (item.get('role_level') or 'guru').lower()
                role_level = 'admin' if raw_role in ['admin', 'platform_admin'] else ('kurikulum' if raw_role == 'kurikulum' else 'guru')
                user_role = Role.ADMIN if role_level == 'admin' else (Role.KURIKULUM if role_level == 'kurikulum' else Role.GURU)

                nip = str(item.get('nip')).strip() if item.get('nip') else None
                email = (item.get('email') or f"guru_{teacher_id.hex[:6]}@smkn1rongga.sch.id").lower().strip()
                sso_id = uuid.UUID(item['sso_id']) if item.get('sso_id') else None

                # Find or create User
                username = (email.split('@')[0] if email else f"guru_{teacher_id.hex[:6]}").replace('.', '_')
                user = User.objects.filter(email__iexact=email).first()
                if not user and sso_id:
                    user = User.objects.filter(sso_id=sso_id).first()
                if not user:
                    user = User.objects.filter(username=username).first()

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
                    user.set_password(item.get('password') or 'Jingga123')
                    user.save()

                existing = Teacher.objects.filter(id=teacher_id).first()
                if not existing:
                    existing = Teacher.objects.filter(email=email).first()

                if existing:
                    existing.user = user
                    existing.full_name = full_name
                    existing.nip = nip
                    existing.email = email
                    existing.role_level = role_level
                    existing.sso_id = sso_id
                    existing.save()
                else:
                    Teacher.objects.create(
                        id=teacher_id,
                        user=user,
                        full_name=full_name,
                        nip=nip,
                        email=email,
                        role_level=role_level,
                        sso_id=sso_id
                    )
                count += 1
        return count

    def sync_students(self):
        raw = self.fetch_all('students')
        count = 0
        with transaction.atomic():
            for item in raw:
                student_id = uuid.UUID(item['id'])
                nis = str(item.get('nis') or '').strip()
                if not nis:
                    continue

                full_name = item.get('full_name') or 'Siswa'
                status = item.get('status') or 'aktif'
                email = item.get('email') or f"{nis}@student.smkn1rongga.sch.id"
                password_plain = item.get('password_plain') or f"jingga{nis}"
                sso_id = uuid.UUID(item['sso_id']) if item.get('sso_id') else None

                major = None
                if item.get('major_id'):
                    major = Major.objects.filter(id=uuid.UUID(item['major_id'])).first()

                classroom = None
                if item.get('class_id'):
                    classroom = ClassRoom.objects.filter(id=uuid.UUID(item['class_id'])).first()

                # User Account
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

                existing = Student.objects.filter(id=student_id).first()
                if not existing:
                    existing = Student.objects.filter(nis=nis).first()

                if existing:
                    existing.user = user
                    existing.nis = nis
                    existing.full_name = full_name
                    existing.major = major
                    existing.class_room = classroom
                    existing.status = status
                    existing.email = email
                    existing.password_plain = password_plain
                    existing.sso_id = sso_id
                    existing.save()
                else:
                    Student.objects.create(
                        id=student_id,
                        user=user,
                        nis=nis,
                        full_name=full_name,
                        major=major,
                        class_room=classroom,
                        status=status,
                        email=email,
                        password_plain=password_plain,
                        sso_id=sso_id
                    )
                count += 1
        return count

    def sync_teacher_assignments(self):
        raw = self.fetch_all('teacher_assignments')
        count = 0
        with transaction.atomic():
            for item in raw:
                assign_id = uuid.UUID(item['id'])
                teacher = Teacher.objects.filter(id=uuid.UUID(item['teacher_id'])).first() if item.get('teacher_id') else None
                classroom = ClassRoom.objects.filter(id=uuid.UUID(item['class_id'])).first() if item.get('class_id') else None
                subject_name = ''

                if item.get('subject_id'):
                    subj = Subject.objects.filter(id=uuid.UUID(item['subject_id'])).first()
                    if subj:
                        subject_name = subj.name

                if teacher and classroom:
                    TeacherAssignment.objects.update_or_create(
                        id=assign_id,
                        defaults={
                            'teacher': teacher,
                            'class_room': classroom,
                            'subject_name': subject_name or 'Umum'
                        }
                    )
                    count += 1
        return count

    def sync_questions(self, on_progress=None):
        raw = self.fetch_all('questions')
        count = 0
        total_raw = len(raw)

        chunk_size = 500
        for i in range(0, total_raw, chunk_size):
            chunk = raw[i:i + chunk_size]
            with transaction.atomic():
                for item in chunk:
                    question_id = uuid.UUID(item['id'])
                    subject = Subject.objects.filter(id=uuid.UUID(item['subject_id'])).first() if item.get('subject_id') else None
                    teacher = Teacher.objects.filter(id=uuid.UUID(item['created_by'])).first() if item.get('created_by') else None
                    level = item.get('level')

                    ans = str(item.get('correct_answer') or 'A').upper().strip()
                    if ans not in ['A', 'B', 'C', 'D', 'E']:
                        ans = 'A'

                    Question.objects.update_or_create(
                        id=question_id,
                        defaults={
                            'subject': subject,
                            'created_by': teacher,
                            'level': level if level in [10, 11, 12] else None,
                            'question_text': item.get('question_text') or '',
                            'question_image': item.get('question_image') or '',
                            'option_a': item.get('option_a') or '',
                            'image_a': item.get('image_a') or '',
                            'option_b': item.get('option_b') or '',
                            'image_b': item.get('image_b') or '',
                            'option_c': item.get('option_c') or '',
                            'image_c': item.get('image_c') or '',
                            'option_d': item.get('option_d') or '',
                            'image_d': item.get('image_d') or '',
                            'option_e': item.get('option_e') or '',
                            'image_e': item.get('image_e') or '',
                            'correct_answer': ans,
                        }
                    )
                    count += 1

            if on_progress:
                on_progress(f"7/7 Menyimpan bank soal: {count}/{total_raw} butir soal...")

        return count


legacy_db_sync_service = LegacyDatabaseSyncService()

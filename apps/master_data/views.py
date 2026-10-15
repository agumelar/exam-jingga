import io
import json
import openpyxl
from openpyxl.styles import Font, Alignment, PatternFill
from django.shortcuts import render, get_object_or_404, redirect
from django.urls import reverse
from django.views.generic import View, ListView, TemplateView
from django.utils.decorators import method_decorator
from django.contrib import messages
from django.http import HttpResponse, JsonResponse
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Q
from django.contrib.auth import get_user_model
from apps.accounts.decorators import admin_required
from apps.accounts.models import Role
from .models import Major, ClassRoom, Teacher, Student, Subject, TeacherAssignment
from .services.openapi_sync import master_data_sync_service
from apps.reports.utils import excel_safe


def excel_row(values):
    return [excel_safe(v) for v in values]

MAX_IMPORT_BYTES = 5 * 1024 * 1024
MAX_IMPORT_ROWS = 3000


def _safe_return_url(request, fallback):
    """Tujuan kembali dari form: hanya URL di aplikasi ini (next/Referer bisa diisi pihak luar)."""
    from django.utils.http import url_has_allowed_host_and_scheme
    for candidate in (request.POST.get('next'), request.META.get('HTTP_REFERER')):
        if candidate and url_has_allowed_host_and_scheme(candidate, allowed_hosts={request.get_host()},
                                                         require_https=request.is_secure()):
            return candidate
    return fallback


def _excel_upload_problem(excel_file):
    if not excel_file.name.lower().endswith('.xlsx'):
        return "Berkas harus berformat .xlsx (Excel 2007 ke atas)."
    if excel_file.size > MAX_IMPORT_BYTES:
        return "Ukuran berkas maksimal 5 MB."
    return None


User = get_user_model()


@method_decorator(admin_required, name='dispatch')
class MajorListView(ListView):
    """View to list and manage Majors / Konsentrasi Keahlian."""
    model = Major
    template_name = 'master_data/majors.html'
    context_object_name = 'majors'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = 'Data Konsentrasi Keahlian / Jurusan'
        context['page_subtitle'] = 'Daftar Program & Konsentrasi Keahlian Resmi SMKN 1 Rongga'
        context['active_menu'] = 'jurusan'
        context['majors_count'] = Major.objects.count()
        return context


@method_decorator(admin_required, name='dispatch')
class ClassRoomListView(ListView):
    """View to list and manage ClassRooms / Rombel."""
    model = ClassRoom
    template_name = 'master_data/classes.html'
    context_object_name = 'classes'

    def get_queryset(self):
        qs = ClassRoom.objects.select_related('major').all().order_by('level', 'name')
        q = self.request.GET.get('q', '').strip()
        major_id = self.request.GET.get('major', '').strip()
        level = self.request.GET.get('level', '').strip()

        if q:
            qs = qs.filter(Q(name__icontains=q) | Q(major__name__icontains=q) | Q(major__code__icontains=q))
        if major_id:
            qs = qs.filter(major_id=major_id)
        if level:
            qs = qs.filter(level=level)
        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = 'Data Rombel & Kelas'
        context['page_subtitle'] = 'Daftar Rombongan Belajar (Tingkat 10, 11, 12)'
        context['active_menu'] = 'kelas'
        context['majors'] = Major.objects.all().order_by('name')
        context['classes_count'] = ClassRoom.objects.count()
        context['search_query'] = self.request.GET.get('q', '').strip()
        context['selected_major'] = self.request.GET.get('major', '').strip()
        context['selected_level'] = self.request.GET.get('level', '').strip()
        return context


@method_decorator(admin_required, name='dispatch')
class TeacherListView(ListView):
    """View to list and search Teachers & Staff."""
    model = Teacher
    template_name = 'master_data/teachers.html'
    context_object_name = 'teachers'

    def get_queryset(self):
        qs = Teacher.objects.all().order_by('full_name')
        q = self.request.GET.get('q', '').strip()
        role = self.request.GET.get('role', '').strip()

        if q:
            qs = qs.filter(
                Q(full_name__icontains=q) |
                Q(nip__icontains=q) |
                Q(email__icontains=q)
            )
        if role:
            qs = qs.filter(role_level=role)
        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = 'Data Guru & Pembuat Soal'
        context['page_subtitle'] = 'Daftar PTK & Pembuat Soal Terhubung Keycloak SSO'
        context['active_menu'] = 'guru'
        context['teachers_count'] = Teacher.objects.count()
        context['search_query'] = self.request.GET.get('q', '').strip()
        context['selected_role'] = self.request.GET.get('role', '').strip()
        return context


@method_decorator(admin_required, name='dispatch')
class TeacherExportExcelView(View):
    """Export teachers data to Excel."""
    def get(self, request, *args, **kwargs):
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Data Guru CBT"

        # Headers
        headers = ["No", "Nama Lengkap", "NIP", "Email SSO", "Peran / Hak Akses"]
        ws.append(headers)

        header_font = Font(bold=True, color="FFFFFF")
        header_fill = PatternFill(start_color="EA580C", end_color="EA580C", fill_type="solid")
        for col_num in range(1, len(headers) + 1):
            cell = ws.cell(row=1, column=col_num)
            cell.font = header_font
            cell.fill = header_fill
            cell.alignment = Alignment(horizontal="center", vertical="center")

        teachers = Teacher.objects.all().order_by('full_name')
        for idx, t in enumerate(teachers, start=1):
            ws.append(excel_row([
                idx,
                t.full_name,
                t.nip or '-',
                t.email or '-',
                t.get_role_level_display().upper()
            ]))

        # Adjust column widths
        ws.column_dimensions['A'].width = 6
        ws.column_dimensions['B'].width = 35
        ws.column_dimensions['C'].width = 22
        ws.column_dimensions['D'].width = 32
        ws.column_dimensions['E'].width = 18

        output = io.BytesIO()
        wb.save(output)
        output.seek(0)

        response = HttpResponse(
            output.read(),
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
        response['Content-Disposition'] = 'attachment; filename="Data_Guru_CBT_Jingga.xlsx"'
        return response


@method_decorator(admin_required, name='dispatch')
class StudentListView(View):
    """View to list students with HTMX search, filtering, and pagination."""
    template_name = 'master_data/students.html'
    partial_template_name = 'master_data/partials/student_table.html'

    def get(self, request, *args, **kwargs):
        qs = Student.objects.select_related('class_room', 'major').all().order_by('full_name')
        
        q = request.GET.get('q', '').strip()
        class_id = request.GET.get('class_id', '').strip()
        major_id = request.GET.get('major_id', '').strip()
        status = request.GET.get('status', '').strip()

        if q:
            qs = qs.filter(
                Q(full_name__icontains=q) |
                Q(nis__icontains=q) |
                Q(email__icontains=q)
            )
        if class_id:
            qs = qs.filter(class_room_id=class_id)
        if major_id:
            qs = qs.filter(major_id=major_id)
        if status:
            qs = qs.filter(status=status)

        page_number = request.GET.get('page', 1)
        paginator = Paginator(qs, 50)
        page_obj = paginator.get_page(page_number)

        context = {
            'page_obj': page_obj,
            'students': page_obj.object_list,
            'classes': ClassRoom.objects.all().order_by('level', 'name'),
            'majors': Major.objects.all().order_by('name'),
            'search_query': q,
            'filter_class': class_id,
            'filter_major': major_id,
            'filter_status': status,
            'total_students_count': Student.objects.count(),
            'filtered_count': qs.count(),
            'page_title': 'Data Siswa Peserta CBT',
            'page_subtitle': 'Database Terpusat Siswa Terdaftar & Akun CBT',
            'active_menu': 'siswa',
        }

        if request.headers.get('HX-Request') or request.GET.get('partial') == 'true':
            return render(request, self.partial_template_name, context)

        return render(request, self.template_name, context)


@method_decorator(admin_required, name='dispatch')
class StudentExportExcelView(View):
    """Export students to Excel."""
    def get(self, request, *args, **kwargs):
        class_id = request.GET.get('class_id', '').strip()
        qs = Student.objects.select_related('class_room').filter(status='aktif').order_by('class_room__name', 'full_name')

        class_name = "Semua_Kelas"
        if class_id:
            qs = qs.filter(class_room_id=class_id)
            c = ClassRoom.objects.filter(id=class_id).first()
            if c:
                class_name = c.name.replace(' ', '_')

        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Data Siswa CBT"

        headers = ["No", "NIS", "Nama Lengkap", "Kelas / Rombel", "Email Siswa", "Status"]
        ws.append(headers)

        header_font = Font(bold=True, color="FFFFFF")
        header_fill = PatternFill(start_color="EA580C", end_color="EA580C", fill_type="solid")
        for col_num in range(1, len(headers) + 1):
            cell = ws.cell(row=1, column=col_num)
            cell.font = header_font
            cell.fill = header_fill
            cell.alignment = Alignment(horizontal="center", vertical="center")

        for idx, s in enumerate(qs, start=1):
            ws.append(excel_row([
                idx,
                s.nis,
                s.full_name.upper(),
                s.class_room.name if s.class_room else '-',
                s.email or f"{s.nis}@student.smkn1rongga.sch.id",
                s.status
            ]))

        ws.column_dimensions['A'].width = 6
        ws.column_dimensions['B'].width = 15
        ws.column_dimensions['C'].width = 35
        ws.column_dimensions['D'].width = 18
        ws.column_dimensions['E'].width = 32
        ws.column_dimensions['F'].width = 12

        output = io.BytesIO()
        wb.save(output)
        output.seek(0)

        response = HttpResponse(
            output.read(),
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
        response['Content-Disposition'] = f'attachment; filename="Data_Siswa_CBT_{class_name}.xlsx"'
        return response


@method_decorator(admin_required, name='dispatch')
class StudentImportTemplateView(View):
    """View to download Excel template for importing students."""
    def get(self, request, *args, **kwargs):
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Template_Siswa"

        headers = ["nis", "nama", "nama_kelas"]
        ws.append(headers)
        for col_num, h in enumerate(headers, 1):
            cell = ws.cell(row=1, column=col_num)
            cell.font = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
            cell.fill = PatternFill(start_color="EA580C", end_color="EA580C", fill_type="solid")
            cell.alignment = Alignment(horizontal="center", vertical="center")

        samples = [
            ["252610001", "CONTOH SISWA BARU", "X RPL 1"],
            ["252610002", "CONTOH SISWA KEDUA", "XI TBSM 2"],
            ["252610003", "CONTOH SISWA KETIGA", "XII TKRO 1"],
        ]
        for s in samples:
            ws.append(s)

        ws.column_dimensions['A'].width = 18
        ws.column_dimensions['B'].width = 35
        ws.column_dimensions['C'].width = 20

        buffer = io.BytesIO()
        wb.save(buffer)
        buffer.seek(0)

        response = HttpResponse(
            buffer.getvalue(),
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
        response['Content-Disposition'] = 'attachment; filename="Template_SIAKAD_Jingga.xlsx"'
        return response


@method_decorator(admin_required, name='dispatch')
class StudentImportView(View):
    """View to upload Excel file and bulk import students."""
    template_name = 'master_data/import_students.html'

    def get(self, request, *args, **kwargs):
        classes = ClassRoom.objects.select_related('major').all().order_by('level', 'name')
        classes_data = [
            {
                'id': str(c.id),
                'name': c.name,
                'major': c.major.code if c.major else '',
            }
            for c in classes
        ]
        context = {
            'classes': classes,
            'classes_json': classes_data,
            'classes_count': classes.count(),
            'page_title': 'Import Siswa',
            'page_subtitle': 'Unggah Berkas Excel (.xlsx) untuk Impor Data Siswa Massal',
            'active_menu': 'import_siswa',
        }
        return render(request, self.template_name, context)

    def post(self, request, *args, **kwargs):
        excel_file = request.FILES.get('excel_file')
        target_url = _safe_return_url(request, reverse('import_siswa'))

        if not excel_file:
            messages.error(request, "Harap pilih berkas Excel (.xlsx) untuk diimpor!")
            return redirect(target_url)
        problem = _excel_upload_problem(excel_file)
        if problem:
            messages.error(request, problem)
            return redirect(target_url)

        try:
            wb = openpyxl.load_workbook(excel_file, data_only=True, read_only=False)
            ws = wb.active
            if ws.max_row > MAX_IMPORT_ROWS + 1:
                messages.error(request, f"Maksimal {MAX_IMPORT_ROWS} baris siswa per berkas.")
                return redirect(target_url)

            header_row = [str(cell.value).strip().lower() if cell.value else '' for cell in ws[1]]
            col_nis = None
            col_nama = None
            col_kelas = None

            for idx, h in enumerate(header_row):
                if h in ['nis', 'nisn', 'nomor induk', 'no_induk']:
                    col_nis = idx + 1
                elif h in ['nama', 'nama lengkap', 'full_name', 'name', 'nama_siswa']:
                    col_nama = idx + 1
                elif h in ['nama_kelas', 'kelas', 'class', 'rombel', 'class_name']:
                    col_kelas = idx + 1

            if not col_nis or not col_nama or not col_kelas:
                messages.error(request, "Format kolom tidak sesuai. Berkas Excel wajib memiliki kolom: nis, nama, nama_kelas.")
                return redirect(target_url)

            class_map = {}
            for c in ClassRoom.objects.select_related('major').all():
                norm = c.name.strip().upper()
                class_map[norm] = c
                if norm.startswith('X '):
                    class_map['10 ' + norm[2:]] = c
                elif norm.startswith('XI '):
                    class_map['11 ' + norm[3:]] = c
                elif norm.startswith('XII '):
                    class_map['12 ' + norm[4:]] = c

            with transaction.atomic():
                created_count = 0
                updated_count = 0
                errors = []

                for row_idx in range(2, ws.max_row + 1):
                    raw_nis = ws.cell(row=row_idx, column=col_nis).value
                    raw_nama = ws.cell(row=row_idx, column=col_nama).value
                    raw_kelas = ws.cell(row=row_idx, column=col_kelas).value

                    if not raw_nis or not raw_nama:
                        continue

                    nis = str(raw_nis).strip()
                    full_name = str(raw_nama).strip()
                    class_name = str(raw_kelas or '').strip()

                    norm_class = class_name.upper()
                    classroom = class_map.get(norm_class)

                    if not classroom:
                        errors.append(f"Baris {row_idx}: {full_name} (Kelas '{class_name}' tidak ditemukan)")
                        continue

                    email = f"{nis}@student.smkn1rongga.sch.id"
                    user, user_created = User.objects.get_or_create(
                        username=nis,
                        defaults={
                            'role': Role.SISWA,
                            'full_name': full_name,
                            'nis': nis,
                            'email': email,
                        }
                    )
                    user.full_name = full_name
                    user.role = Role.SISWA
                    user.nis = nis
                    if user_created:
                        # Siswa login lewat SSO (username = NIS); akun lokal tidak punya kata sandi
                        user.set_unusable_password()
                    user.save()

                    _, s_created = Student.objects.update_or_create(
                        nis=nis,
                        defaults={
                            'user': user,
                            'full_name': full_name,
                            'class_room': classroom,
                            'major': classroom.major,
                            'email': email,
                            'status': 'aktif',
                        }
                    )

                    if s_created:
                        created_count += 1
                    else:
                        updated_count += 1

            msg = f"Berhasil memproses data: {created_count} siswa baru ditambahkan, {updated_count} siswa diperbarui."
            if errors:
                err_summary = ", ".join(errors[:5])
                if len(errors) > 5:
                    err_summary += f" dan {len(errors) - 5} baris lainnya."
                messages.warning(request, f"{msg} Catatan kelas tidak cocok: {err_summary}")
            else:
                messages.success(request, msg)

        except Exception as exc:
            messages.error(request, f"Gagal membaca berkas Excel: {exc}")

        return redirect(target_url)


@method_decorator(admin_required, name='dispatch')
class TeacherAssignmentListView(View):
    """View to list and manage Teacher Subject-Class Assignments."""
    template_name = 'master_data/assignments.html'

    def get(self, request, *args, **kwargs):
        qs = TeacherAssignment.objects.select_related('teacher', 'subject', 'class_room').all().order_by('teacher__full_name')
        
        q = request.GET.get('q', '').strip()
        subject_id = request.GET.get('subject_id', '').strip()
        class_id = request.GET.get('class_id', '').strip()

        if q:
            qs = qs.filter(
                Q(teacher__full_name__icontains=q) |
                Q(subject__name__icontains=q) |
                Q(subject_name__icontains=q)
            )
        if subject_id:
            qs = qs.filter(subject_id=subject_id)
        if class_id:
            qs = qs.filter(class_room_id=class_id)

        context = {
            'assignments': qs,
            'teachers': Teacher.objects.active().order_by('full_name'),
            'subjects': Subject.objects.all().order_by('name'),
            'classes': ClassRoom.objects.all().order_by('level', 'name'),
            'search_query': q,
            'filter_subject': subject_id,
            'filter_class': class_id,
            'page_title': 'Penugasan Pengampu',
            'page_subtitle': 'Atur Guru yang Mengampu Mata Pelajaran di Tiap Kelas',
            'active_menu': 'penugasan',
        }
        return render(request, self.template_name, context)

    def post(self, request, *args, **kwargs):
        action = request.POST.get('action', 'create')
        target_url = _safe_return_url(request, None) or reverse('penugasan_guru')

        if action == 'create':
            teacher_id = request.POST.get('teacher_id')
            subject_id = request.POST.get('subject_id')
            class_ids = request.POST.getlist('class_ids')

            if not teacher_id or not subject_id or not class_ids:
                messages.error(request, "Harap pilih Guru, Mata Pelajaran, dan minimal satu Kelas!")
                return redirect(target_url)

            teacher = get_object_or_404(Teacher, id=teacher_id)
            subject = get_object_or_404(Subject, id=subject_id)

            created_count = 0
            for cid in class_ids:
                classroom = ClassRoom.objects.filter(id=cid).first()
                if classroom:
                    _, created = TeacherAssignment.objects.get_or_create(
                        teacher=teacher,
                        subject=subject,
                        class_room=classroom,
                        defaults={'subject_name': subject.name}
                    )
                    if created:
                        created_count += 1

            messages.success(request, f"Berhasil menambahkan {created_count} penugasan guru.")
            return redirect(target_url)

        elif action == 'update':
            assignment_id = request.POST.get('assignment_id')
            teacher_id = request.POST.get('teacher_id')
            subject_id = request.POST.get('subject_id')
            class_id = request.POST.get('class_id')

            assignment = get_object_or_404(TeacherAssignment, id=assignment_id)
            teacher = get_object_or_404(Teacher, id=teacher_id)
            subject = get_object_or_404(Subject, id=subject_id)
            classroom = get_object_or_404(ClassRoom, id=class_id)

            if TeacherAssignment.objects.filter(teacher=teacher, subject=subject, class_room=classroom).exclude(pk=assignment.pk).exists():
                messages.error(request, f"{teacher.full_name} sudah ditugaskan mengajar {subject.name} di {classroom.name}.")
                return redirect(target_url)
            assignment.teacher = teacher
            assignment.subject = subject
            assignment.subject_name = subject.name
            assignment.class_room = classroom
            assignment.save()

            messages.success(request, "Penugasan guru berhasil diperbarui.")
            return redirect(target_url)

        elif action == 'delete':
            assignment_id = request.POST.get('assignment_id')
            assignment = get_object_or_404(TeacherAssignment, id=assignment_id)
            assignment.delete()
            messages.success(request, "Penugasan guru berhasil dihapus.")
            return redirect(target_url)

        return redirect(target_url)


@method_decorator(admin_required, name='dispatch')
class SubjectListView(View):
    """View to list, search, add, and edit Subjects (Mata Pelajaran)."""
    template_name = 'master_data/subjects.html'

    def get(self, request, *args, **kwargs):
        subjects = Subject.objects.all().order_by('name')
        context = {
            'subjects': subjects,
            'subjects_count': subjects.count(),
            'page_title': 'Master Mata Pelajaran',
            'page_subtitle': 'Daftar Mata Pelajaran Resmi SMKN 1 Rongga',
            'active_menu': 'mapel',
        }
        return render(request, self.template_name, context)

    def post(self, request, *args, **kwargs):
        action = request.POST.get('action', 'create')
        target_url = _safe_return_url(request, None) or reverse('master_mapel')

        if action == 'create':
            name = request.POST.get('name', '').strip()
            if not name:
                messages.error(request, "Nama mata pelajaran wajib diisi!")
                return redirect(target_url)

            if Subject.objects.filter(name__iexact=name).exists():
                messages.warning(request, f"Mata pelajaran '{name}' sudah ada.")
                return redirect(target_url)

            Subject.objects.create(name=name)
            messages.success(request, f"Mata pelajaran '{name}' berhasil ditambahkan.")
            return redirect(target_url)

        elif action == 'update':
            subject_id = request.POST.get('subject_id')
            name = request.POST.get('name', '').strip()
            if not subject_id or not name:
                messages.error(request, "ID dan Nama mata pelajaran wajib diisi!")
                return redirect(target_url)

            subject = get_object_or_404(Subject, id=subject_id)
            if Subject.objects.filter(name__iexact=name).exclude(id=subject_id).exists():
                messages.warning(request, f"Mata pelajaran dengan nama '{name}' sudah ada.")
                return redirect(target_url)

            old_name = subject.name
            subject.name = name
            subject.save()

            # Sinkronkan kolom subject_name di TeacherAssignment jika ada
            TeacherAssignment.objects.filter(subject=subject).update(subject_name=name)

            messages.success(request, f"Mata pelajaran '{name}' berhasil diperbarui.")
            return redirect(target_url)

        elif action == 'delete':
            subject_id = request.POST.get('subject_id')
            subject = get_object_or_404(Subject, id=subject_id)
            name = subject.name
            subject.delete()
            messages.success(request, f"Mata pelajaran '{name}' berhasil dihapus.")
            return redirect(target_url)

        return redirect(target_url)


@method_decorator(admin_required, name='dispatch')
class SubjectDeleteView(View):
    """View to delete a subject via POST with SweetAlert2 or standard redirect."""
    def post(self, request, pk, *args, **kwargs):
        subject = get_object_or_404(Subject, id=pk)
        name = subject.name
        subject.delete()
        if request.headers.get('x-requested-with') == 'XMLHttpRequest' or request.content_type == 'application/json':
            return JsonResponse({'status': 'success', 'message': f"Mata pelajaran '{name}' berhasil dihapus."})
        messages.success(request, f"Mata pelajaran '{name}' berhasil dihapus.")
        target_url = _safe_return_url(request, None) or reverse('master_mapel')
        return redirect(target_url)


@method_decorator(admin_required, name='dispatch')
class SubjectTemplateExportView(View):
    """View to download Excel template for importing subjects."""
    def get(self, request, *args, **kwargs):
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Template Mapel"

        # Header styling
        ws.append(["Nama_Mapel"])
        header_cell = ws.cell(row=1, column=1)
        header_cell.font = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
        header_cell.fill = PatternFill(start_color="EA580C", end_color="EA580C", fill_type="solid")
        header_cell.alignment = Alignment(horizontal="center", vertical="center")

        # Contoh data
        samples = [
            "Konsentrasi Keahlian RPL",
            "Dasar-Dasar PPLG",
            "Bahasa Indonesia",
        ]
        for s in samples:
            ws.append([s])

        ws.column_dimensions['A'].width = 35

        buffer = io.BytesIO()
        wb.save(buffer)
        buffer.seek(0)

        response = HttpResponse(
            buffer.getvalue(),
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
        response['Content-Disposition'] = 'attachment; filename="Template_Import_Mapel_Jingga.xlsx"'
        return response


@method_decorator(admin_required, name='dispatch')
class SubjectImportExcelView(View):
    """View to import subjects from uploaded Excel file."""
    def post(self, request, *args, **kwargs):
        target_url = _safe_return_url(request, None) or reverse('master_mapel')
        excel_file = request.FILES.get('excel_file')

        if not excel_file:
            messages.error(request, "Harap pilih file Excel (.xlsx) untuk diimpor!")
            return redirect(target_url)
        problem = _excel_upload_problem(excel_file)
        if problem:
            messages.error(request, problem)
            return redirect(target_url)

        try:
            wb = openpyxl.load_workbook(excel_file, data_only=True)
            ws = wb.active

            header_row = [str(cell.value).strip().lower() if cell.value else '' for cell in ws[1]]
            col_idx = None
            for idx, h in enumerate(header_row):
                if h in ['nama_mapel', 'nama mapel', 'mapel', 'name', 'mata pelajaran', 'mata_pelajaran']:
                    col_idx = idx + 1
                    break

            if col_idx is None:
                col_idx = 1

            imported_count = 0
            for row in range(2, ws.max_row + 1):
                val = ws.cell(row=row, column=col_idx).value
                if val:
                    name_str = str(val).strip()
                    if name_str:
                        # Nama mapel dibandingkan tanpa beda huruf besar/kecil supaya tidak terbuat ganda
                        if not Subject.objects.filter(name__iexact=name_str).exists():
                            Subject.objects.create(name=name_str)
                            imported_count += 1

            messages.success(request, f"Berhasil mengimpor {imported_count} mata pelajaran baru.")
        except Exception as exc:
            messages.error(request, f"Gagal mengimpor file Excel: {exc}. Pastikan format file valid.")

        return redirect(target_url)


@method_decorator(admin_required, name='dispatch')
class SyncMasterDataView(View):
    """
    Endpoint triggered via HTMX (POST /master/sync/) or AJAX.
    Runs synchronization and returns status card or JSON.
    """
    def post(self, request, *args, **kwargs):
        sync_type = request.POST.get('type', 'all')
        bearer_token = None  # selalu token mesin dari client sinkron (DATA_MASTER_CLIENT_ID)

        try:
            if sync_type == 'majors':
                result = master_data_sync_service.sync_majors(bearer_token=bearer_token)
            elif sync_type == 'classes':
                result = master_data_sync_service.sync_classes(bearer_token=bearer_token)
            elif sync_type == 'teachers':
                result = master_data_sync_service.sync_teachers(bearer_token=bearer_token)
            elif sync_type == 'students':
                result = master_data_sync_service.sync_students(bearer_token=bearer_token)
            else:
                result = master_data_sync_service.sync_all(bearer_token=bearer_token)

            context = {
                'success': True,
                'sync_type': sync_type,
                'result': result,
                'message': result.get('message', 'Sinkronisasi data master berhasil diselesaikan.'),
                'majors_count': Major.objects.count(),
                'classes_count': ClassRoom.objects.count(),
                'teachers_count': Teacher.objects.count(),
                'students_count': Student.objects.count(),
            }
        except Exception as e:
            logger_err = str(e)
            context = {
                'success': False,
                'sync_type': sync_type,
                'error': logger_err,
                'message': f"Gagal sinkronisasi data: {logger_err}"
            }

        if request.headers.get('HX-Request') or request.GET.get('format') == 'html':
            return render(request, 'master_data/partials/sync_status.html', context)

        return JsonResponse(context)



def _normalize_student_status(raw):
    value = str(raw or 'aktif').strip().lower()
    return 'aktif' if value in ('aktif', 'active') else value


def _parse_uuid(value):
    import uuid
    try:
        return uuid.UUID(str(value)) if value else None
    except (ValueError, TypeError, AttributeError):
        return None


@method_decorator(__import__('django.views.decorators.csrf', fromlist=['csrf_exempt']).csrf_exempt, name='dispatch')
class WebhookSyncView(View):
    """
    Endpoint Webhook Real-Time dari School Data Platform (POST /api/webhook/sync/).
    Menerima mutasi siswa dan staf. Header keamanan: x-api-key: <WEBHOOK_SECRET_KEY>.

    Webhook hanya menyalin data identitas. Peran admin/kurikulum datang dari SSO Keycloak,
    dan akun tidak pernah diberi kata sandi lokal karena semua peran login lewat SSO.
    """
    def post(self, request, *args, **kwargs):
        import hmac
        import logging
        from django.conf import settings

        logger = logging.getLogger(__name__)
        api_key = request.headers.get('x-api-key') or ''
        expected_key = getattr(settings, 'WEBHOOK_SECRET_KEY', '') or ''
        if not expected_key or not hmac.compare_digest(api_key.encode(), expected_key.encode()):
            return JsonResponse({'error': 'Unauthorized: Invalid API Key'}, status=401)

        try:
            body = json.loads(request.body.decode('utf-8'))
        except (ValueError, UnicodeDecodeError):
            return JsonResponse({'error': 'Invalid JSON body'}, status=400)

        action = str(body.get('action') or 'update').lower()
        item_type = str(body.get('type') or '').lower()
        data = body.get('data') or {}
        if not item_type or not data:
            return JsonResponse({'error': 'Missing type or data in payload'}, status=400)

        try:
            if item_type in ['student', 'siswa']:
                return self._sync_student(action, data)
            if item_type in ['staff', 'teacher', 'guru']:
                return self._sync_staff(action, data)
            return JsonResponse({'error': f'Unknown type: {item_type}'}, status=400)
        except Exception:
            logger.exception("Webhook sync gagal untuk type=%s action=%s", item_type, action)
            return JsonResponse({'error': 'Sync processing failed'}, status=500)

    def _sync_student(self, action, data):
        User = get_user_model()
        nis = str(data.get('nis') or '').strip()
        if not nis:
            return JsonResponse({'error': 'NIS is required for student'}, status=400)

        if action == 'delete':
            Student.objects.filter(nis=nis).update(status='keluar')
            User.objects.filter(username=nis, is_superuser=False).update(is_active=False)
            return JsonResponse({'status': 'success', 'message': f'Student {nis} marked as inactive'})

        full_name = data.get('nama_siswa') or data.get('fullName') or data.get('full_name') or 'Siswa'
        sso_uuid = _parse_uuid(data.get('id') or data.get('sso_id'))
        status = _normalize_student_status(data.get('status_siswa') or data.get('status'))
        email = data.get('email') or f'{nis}@student.smkn1rongga.sch.id'

        class_name = data.get('class_name') or data.get('kelas') or data.get('rombel')
        matched_class = None
        class_uuid = _parse_uuid(data.get('kelas_id') or data.get('classGroupId'))
        if class_uuid:
            matched_class = ClassRoom.objects.filter(id=class_uuid).first()
        if not matched_class and class_name:
            matched_class = ClassRoom.objects.filter(name__iexact=str(class_name).strip()).first()

        user = User.objects.filter(username=nis).first()
        if user is None:
            user = User(username=nis, nis=nis, full_name=full_name, email=email, role=Role.SISWA, sso_id=sso_uuid)
            user.set_unusable_password()
        if not user.is_superuser:
            user.full_name = full_name
            if sso_uuid and not user.sso_id:
                user.sso_id = sso_uuid
            user.is_active = status == 'aktif'
            user.save()

        defaults = {'user': user, 'full_name': full_name, 'status': status, 'email': email}
        if sso_uuid:
            defaults['sso_id'] = sso_uuid
        if matched_class or not class_name:
            defaults['class_room'] = matched_class
        Student.objects.update_or_create(nis=nis, defaults=defaults)
        return JsonResponse({'status': 'success', 'message': 'Student data synced successfully'})

    def _sync_staff(self, action, data):
        User = get_user_model()
        nip = str(data.get('nip') or '').strip() or None
        email = str(data.get('email') or '').lower().strip()
        if not email and not nip:
            return JsonResponse({'error': 'email or nip is required for staff'}, status=400)
        if not email:
            email = f"{nip}@smkn1rongga.sch.id"

        teacher = Teacher.objects.filter(email__iexact=email).first()
        if action == 'delete':
            # Guru tidak dihapus: bank soal dan riwayat ujiannya tetap utuh, hanya aksesnya dicabut
            if teacher and teacher.user_id:
                User.objects.filter(pk=teacher.user_id, is_superuser=False).update(is_active=False)
            return JsonResponse({'status': 'success', 'message': f'Staff {email} deactivated'})

        full_name = data.get('fullName') or data.get('full_name') or data.get('name') or 'Guru'
        sso_uuid = _parse_uuid(data.get('id') or data.get('sso_id'))
        raw_role = str(data.get('ptkType') or data.get('role_level') or '').strip().lower()
        role_level = 'kurikulum' if raw_role == 'kurikulum' else 'guru'

        username = email.split('@')[0].replace('.', '_')
        user = User.objects.filter(email__iexact=email).first() or User.objects.filter(username=username).first()
        if user is None:
            user = User(username=username, email=email, full_name=full_name, role=Role.GURU, sso_id=sso_uuid)
            user.set_unusable_password()
            user.save()
        elif not user.is_superuser:
            user.full_name = full_name
            if sso_uuid and not user.sso_id:
                user.sso_id = sso_uuid
            user.save(update_fields=['full_name', 'sso_id'])

        defaults = {'user': user, 'full_name': full_name, 'nip': nip, 'role_level': role_level}
        if sso_uuid:
            defaults['sso_id'] = sso_uuid
        Teacher.objects.update_or_create(email=email, defaults=defaults)
        return JsonResponse({'status': 'success', 'message': 'Staff data synced successfully'})

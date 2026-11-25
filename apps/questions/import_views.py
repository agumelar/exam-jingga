"""Halaman impor soal dari Word untuk guru: unduh template, unggah, pratinjau, simpan."""
from django.contrib import messages
from django.http import Http404, HttpResponse
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils.decorators import method_decorator
from django.views.generic import View

from apps.accounts.decorators import teacher_required
from apps.master_data.models import Subject

from . import word_import
from .views import get_current_teacher, teacher_subject_levels

DOCX_TYPE = 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'


@method_decorator(teacher_required, name='dispatch')
class QuestionTemplateDownloadView(View):
    def get(self, request):
        response = HttpResponse(word_import.build_template(), content_type=DOCX_TYPE)
        response['Content-Disposition'] = 'attachment; filename="template-soal-exam-jingga.docx"'
        return response


@method_decorator(teacher_required, name='dispatch')
class QuestionImportView(View):
    template_name = 'questions/import.html'

    def dispatch(self, request, *args, **kwargs):
        self.teacher = get_current_teacher(request.user)
        self.subjects = teacher_subject_levels(self.teacher)
        if not self.subjects:
            messages.warning(request, 'Impor dari Word hanya untuk guru yang punya penugasan mapel. Hubungi bagian kurikulum.')
            return redirect('questions:bank_soal')
        return super().dispatch(request, *args, **kwargs)

    def _render(self, request, status=200, **extra):
        context = {
            'page_title': 'Impor Soal dari Word',
            'page_subtitle': 'Bank Soal',
            'active_menu': 'bank_soal',
            'subjects': self.subjects,
            'max_questions': word_import.MAX_QUESTIONS,
            'max_mb': word_import.MAX_FILE_BYTES // (1024 * 1024),
            **extra,
        }
        return render(request, self.template_name, context, status=status)

    def get(self, request):
        return self._render(request)

    def post(self, request):
        subject_id = request.POST.get('subject', '').strip()
        level = request.POST.get('level', '').strip()
        chosen = next((s for s in self.subjects if s['id'] == subject_id), None)
        form = {'subject': subject_id, 'level': level}

        if chosen is None:
            return self._render(request, 400, form=form, upload_error='Pilih mata pelajaran yang Anda ajar.')
        if not level.isdigit() or int(level) not in chosen['levels']:
            return self._render(request, 400, form=form,
                                upload_error=f'Pilih tingkat kelas yang Anda ajar untuk {chosen["name"]}.')
        upload = request.FILES.get('file')
        if upload is None:
            return self._render(request, 400, form=form, upload_error='Pilih file Word (.docx) yang akan diunggah.')
        if not upload.name.lower().endswith('.docx'):
            return self._render(request, 400, form=form, upload_error=word_import.NOT_DOCX)
        if upload.size > word_import.MAX_FILE_BYTES:
            return self._render(request, 400, form=form,
                                upload_error=f'Ukuran file melebihi {word_import.MAX_FILE_BYTES // (1024 * 1024)} MB.')

        result = word_import.parse_document(upload)
        if result.file_error:
            return self._render(request, 400, form=form, upload_error=result.file_error)

        subject = Subject.objects.get(id=subject_id)
        word_import.mark_duplicates(result, subject, self.teacher)
        token = word_import.stash(result, user_id=request.user.id, subject_id=subject.id, level=int(level),
                                  filename=upload.name)
        counts = {status: result.count(status) for status in ('siap', 'peringatan', 'gagal', 'sudah_ada')}
        return self._render(request, form=form, result=result, counts=counts, token=token, subject=subject,
                            level=int(level), filename=upload.name)


@method_decorator(teacher_required, name='dispatch')
class QuestionImportConfirmView(View):
    def post(self, request):
        token = request.POST.get('token', '')
        state, data = word_import.load_stash(token, request.user.id)
        if state == 'forbidden':
            raise Http404
        if state == 'missing':
            messages.warning(request, 'Pratinjau sudah kedaluwarsa atau sudah disimpan. Unggah ulang file bila perlu.')
            return redirect('questions:import')

        teacher = get_current_teacher(request.user)
        allowed = {s['id']: s['levels'] for s in teacher_subject_levels(teacher)}
        if data['level'] not in allowed.get(data['subject_id'], []):
            word_import.discard(token)
            raise Http404

        subject = Subject.objects.get(id=data['subject_id'])
        created, skipped = word_import.save_import(token, data, subject, teacher)
        word_import.discard(token)

        text = f'{created} soal ditambahkan ke bank soal {subject.name} kelas {data["level"]}.'
        if skipped:
            text += f' {skipped} soal dilewati karena sudah ada.'
        messages.success(request, text)
        return redirect(f"{reverse('questions:bank_soal')}?subject_id={subject.id}&level={data['level']}")

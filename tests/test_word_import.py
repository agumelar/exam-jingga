"""Impor soal dari template Word: pembacaan tabel, gambar, rumus, dan alur unggah-pratinjau-simpan guru."""
import io

import pytest
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from django.urls import reverse
from docx import Document
from docx.oxml import parse_xml
from PIL import Image

from apps.accounts.models import Role
from apps.master_data.models import ClassRoom, Subject, Teacher, TeacherAssignment
from apps.questions import word_import
from apps.questions.models import Question

User = get_user_model()
DOCX = 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
M_NS = 'xmlns:m="http://schemas.openxmlformats.org/officeDocument/2006/math"'


def _png(size=(8, 8), color=(200, 80, 20)):
    buf = io.BytesIO()
    Image.new('RGB', size, color).save(buf, 'PNG')
    buf.seek(0)
    return buf


def _soal(doc, soal='Ibu kota Jawa Barat adalah ....', options=('Bandung', 'Bogor', 'Garut', 'Cianjur', 'Bekasi'),
          kunci='A', cp='', labels=None):
    """Tambahkan satu tabel soal sesuai template. Nilai sel boleh berupa fungsi pengisi sel."""
    labels = labels or ['Soal', 'A', 'B', 'C', 'D', 'E', 'Kunci', 'CP']
    values = [soal, *options, kunci, cp]
    table = doc.add_table(rows=len(labels), cols=2)
    for row, label, value in zip(table.rows, labels, values):
        row.cells[0].text = label
        if callable(value):
            value(row.cells[1])
        else:
            row.cells[1].text = value
    doc.add_paragraph('')
    return table


def _bytes(doc):
    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()


def _parse(doc):
    return word_import.parse_document(io.BytesIO(_bytes(doc)))


def _math(xml):
    def fill(cell):
        p = cell.paragraphs[0]
        p.add_run('Hasil dari ')
        p._p.append(parse_xml(f'<m:oMath {M_NS}>{xml}</m:oMath>'))
        p.add_run(' adalah ....')
    return fill


# ---------------------------------------------------------------- pembacaan dokumen

def test_filled_table_becomes_ready_question():
    doc = Document()
    _soal(doc, kunci='b.', cp='CP 2 - Statistika')
    result = _parse(doc)

    assert result.file_error == ''
    [item] = result.items
    assert item.question_text == 'Ibu kota Jawa Barat adalah ....'
    assert [item.options[k] for k in 'ABCDE'] == ['Bandung', 'Bogor', 'Garut', 'Cianjur', 'Bekasi']
    assert item.correct_answer == 'B'
    assert (item.cp_code, item.cp_name) == ('CP 2', 'Statistika')
    assert item.status == 'siap'


def test_labels_are_recognised_by_name_not_position():
    doc = Document()
    _soal(doc, labels=['Pertanyaan', 'Opsi A', 'Pilihan B', 'C.', 'd', 'E:', 'Kunci Jawaban', 'Capaian Pembelajaran'])
    [item] = _parse(doc).items
    assert item.status == 'siap'
    assert item.options['D'] == 'Cianjur'


def test_template_alone_imports_nothing():
    result = word_import.parse_document(io.BytesIO(word_import.build_template()))
    assert result.file_error == ''
    assert result.items == []
    assert result.skipped_examples == 2


def test_multi_paragraph_question_keeps_line_breaks():
    def fill(cell):
        cell.paragraphs[0].text = 'Perhatikan pernyataan berikut!'
        cell.add_paragraph('1. Jujur')
        cell.add_paragraph('2. Disiplin')
    doc = Document()
    _soal(doc, soal=fill)
    [item] = _parse(doc).items
    assert item.question_text == 'Perhatikan pernyataan berikut!\n1. Jujur\n2. Disiplin'


def test_superscript_and_subscript_runs_become_unicode():
    def fill(cell):
        p = cell.paragraphs[0]
        p.add_run('Nilai x')
        p.add_run('2').font.superscript = True
        p.add_run(' + H')
        p.add_run('2').font.subscript = True
        p.add_run('O')
    doc = Document()
    _soal(doc, soal=fill)
    [item] = _parse(doc).items
    assert item.question_text == 'Nilai x² + H₂O'


def test_equation_is_converted_to_text_with_warning():
    doc = Document()
    _soal(doc, soal=_math('<m:f><m:num><m:r><m:t>1</m:t></m:r></m:num><m:den><m:r><m:t>2</m:t></m:r></m:den></m:f>'
                          '<m:r><m:t>+</m:t></m:r>'
                          '<m:sSup><m:e><m:r><m:t>x</m:t></m:r></m:e><m:sup><m:r><m:t>2</m:t></m:r></m:sup></m:sSup>'
                          '<m:r><m:t>+</m:t></m:r>'
                          '<m:rad><m:deg/><m:e><m:r><m:t>9</m:t></m:r></m:e></m:rad>'))
    [item] = _parse(doc).items
    assert item.question_text == 'Hasil dari 1/2+x²+√9 adalah ....'
    assert item.status == 'peringatan'
    assert any('rumus' in w.lower() for w in item.warnings)


def test_compound_fraction_gets_parentheses():
    doc = Document()
    _soal(doc, soal=_math('<m:f><m:num><m:r><m:t>a+b</m:t></m:r></m:num><m:den><m:r><m:t>2c</m:t></m:r></m:den></m:f>'))
    [item] = _parse(doc).items
    assert 'Hasil dari (a+b)/(2c) adalah' in item.question_text


def test_images_in_question_and_option_cells_are_taken():
    def question(cell):
        cell.paragraphs[0].text = 'Perhatikan gambar berikut!'
        cell.add_paragraph().add_run().add_picture(_png((3000, 1500)))

    def option_b(cell):
        cell.paragraphs[0].add_run().add_picture(_png((40, 40), (0, 120, 0)))

    doc = Document()
    _soal(doc, soal=question, options=('a', option_b, 'c', 'd', 'e'))
    [item] = _parse(doc).items

    assert item.status == 'siap'
    assert item.options['B'] == ''
    big = Image.open(io.BytesIO(item.images['question'].data))
    assert max(big.size) == word_import.MAX_IMAGE_SIDE
    assert Image.open(io.BytesIO(item.images['B'].data)).size == (40, 40)
    assert item.images['question'].preview.startswith('data:image/')


def test_image_only_paragraph_leaves_no_blank_line():
    def question(cell):
        cell.paragraphs[0].text = 'Perhatikan diagram berikut!'
        cell.add_paragraph().add_run().add_picture(_png((20, 20)))
        cell.add_paragraph('Jenis korelasinya adalah ....')

    doc = Document()
    _soal(doc, soal=question)
    [item] = _parse(doc).items
    assert item.question_text == 'Perhatikan diagram berikut!\nJenis korelasinya adalah ....'


def test_two_images_in_one_cell_keeps_first_with_warning():
    def question(cell):
        cell.paragraphs[0].text = 'Bandingkan kedua gambar.'
        run = cell.add_paragraph().add_run()
        run.add_picture(_png((20, 20)))
        run.add_picture(_png((30, 30)))

    doc = Document()
    _soal(doc, soal=question)
    [item] = _parse(doc).items
    assert item.status == 'peringatan'
    assert Image.open(io.BytesIO(item.images['question'].data)).size == (20, 20)


def test_missing_key_or_option_fails():
    doc = Document()
    _soal(doc, kunci='')
    _soal(doc, options=('a', 'b', 'c', 'd', ''))
    _soal(doc, kunci='F')
    items = _parse(doc).items
    assert [i.status for i in items] == ['gagal', 'gagal', 'gagal']
    assert 'Kunci' in items[0].errors[0]
    assert 'E' in items[1].errors[0]


def test_question_without_text_fails():
    doc = Document()
    _soal(doc, soal='')
    [item] = _parse(doc).items
    assert item.status == 'gagal'


def test_table_inside_question_fails():
    def question(cell):
        cell.paragraphs[0].text = 'Tabel berikut menyajikan data berat badan.'
        cell.add_table(rows=2, cols=2)

    doc = Document()
    _soal(doc, soal=question)
    [item] = _parse(doc).items
    assert item.status == 'gagal'
    assert 'tabel' in item.errors[0].lower()


def test_empty_tables_are_ignored_and_numbers_follow_order():
    doc = Document()
    _soal(doc, soal='Soal pertama', options=('a', 'b', 'c', 'd', 'e'))
    _soal(doc, soal='', options=('', '', '', '', ''), kunci='')
    _soal(doc, soal='Soal kedua', options=('a', 'b', 'c', 'd', 'e'))
    items = _parse(doc).items
    assert [(i.number, i.question_text) for i in items] == [(1, 'Soal pertama'), (2, 'Soal kedua')]


def test_cross_referencing_options_lock_the_order():
    doc = Document()
    _soal(doc, options=('1 saja', '2 saja', '1 dan 2', 'Semua benar', 'Tidak ada yang benar'))
    [item] = _parse(doc).items
    assert item.lock_option_order is True
    assert item.status == 'peringatan'


def test_tables_without_question_label_are_ignored():
    doc = Document()
    info = doc.add_table(rows=1, cols=2)
    info.rows[0].cells[0].text = 'Mapel'
    info.rows[0].cells[1].text = 'Matematika'
    _soal(doc)
    assert len(_parse(doc).items) == 1


def test_non_docx_file_is_rejected():
    result = word_import.parse_document(io.BytesIO(b'bukan file word'))
    assert result.items == []
    assert '.docx' in result.file_error


def test_too_many_questions_rejects_whole_file():
    doc = Document()
    for n in range(word_import.MAX_QUESTIONS + 1):
        _soal(doc, soal=f'Soal nomor {n}')
    result = _parse(doc)
    assert result.items == []
    assert str(word_import.MAX_QUESTIONS) in result.file_error


# ---------------------------------------------------------------- alur halaman guru

@pytest.fixture
def guru(db):
    user = User.objects.create_user(username='198001012010011001', role=Role.GURU)
    teacher = Teacher.objects.create(user=user, full_name='Ade Sandi', nip='198001012010011001')
    mtk = Subject.objects.create(name='Matematika')
    other = Subject.objects.create(name='Sejarah')
    kelas = ClassRoom.objects.create(name='11 RPL-1', level=11)
    TeacherAssignment.objects.create(teacher=teacher, subject=mtk, class_room=kelas)
    return {'user': user, 'teacher': teacher, 'mtk': mtk, 'other': other}


@pytest.fixture
def media(tmp_path):
    with override_settings(MEDIA_ROOT=str(tmp_path / 'media'), QUESTION_IMPORT_DIR=str(tmp_path / 'impor')):
        yield tmp_path


def _upload(client, doc, subject, level=11, name='soal.docx'):
    data = _bytes(doc) if not isinstance(doc, bytes) else doc
    return client.post(reverse('questions:import'), {
        'subject': str(subject.id), 'level': level, 'file': SimpleUploadedFile(name, data, content_type=DOCX),
    })


def _token(response):
    return response.context['token']


@pytest.mark.django_db
def test_template_download_is_a_word_file(client, guru):
    client.force_login(guru['user'])
    res = client.get(reverse('questions:import_template'))
    assert res.status_code == 200
    assert res['Content-Type'] == DOCX
    assert 'attachment' in res['Content-Disposition']
    assert word_import.parse_document(io.BytesIO(res.content)).file_error == ''


@pytest.mark.django_db
def test_import_page_offers_only_assigned_subjects(client, guru):
    client.force_login(guru['user'])
    html = client.get(reverse('questions:import')).content.decode()
    assert 'Matematika' in html
    assert 'Sejarah' not in html


@pytest.mark.django_db
def test_upload_for_unassigned_subject_is_refused(client, guru, media):
    client.force_login(guru['user'])
    doc = Document()
    _soal(doc)
    res = _upload(client, doc, guru['other'])
    assert res.status_code == 400
    assert not (media / 'impor').exists() or not any((media / 'impor').iterdir())


@pytest.mark.django_db
def test_upload_for_unassigned_level_is_refused(client, guru, media):
    client.force_login(guru['user'])
    doc = Document()
    _soal(doc)
    assert _upload(client, doc, guru['mtk'], level=12).status_code == 400


@pytest.mark.django_db
def test_upload_preview_then_save_creates_questions_with_images(client, guru, media):
    def question(cell):
        cell.paragraphs[0].text = 'Perhatikan diagram pencar berikut!'
        cell.add_paragraph().add_run().add_picture(_png((60, 40)))

    doc = Document()
    _soal(doc, soal=question, cp='CP 3 - Statistika')
    _soal(doc, soal='Soal tanpa kunci', kunci='')
    client.force_login(guru['user'])

    preview = _upload(client, doc, guru['mtk'])
    assert preview.status_code == 200
    html = preview.content.decode()
    assert 'Perhatikan diagram pencar berikut!' in html
    assert 'Kunci jawaban' in html
    assert Question.objects.count() == 0

    res = client.post(reverse('questions:import_confirm'), {'token': _token(preview)})
    assert res.status_code == 302

    q = Question.objects.get()
    assert q.question_text == 'Perhatikan diagram pencar berikut!'
    assert (q.subject, q.level, q.created_by) == (guru['mtk'], 11, guru['teacher'])
    assert (q.cp_code, q.cp_name, q.correct_answer) == ('CP 3', 'Statistika', 'A')
    assert q.question_image and q.question_image.storage.exists(q.question_image.name)
    assert q.question_image.name.startswith('questions/')
    assert not any((media / 'impor').iterdir())


@pytest.mark.django_db
def test_same_file_twice_does_not_duplicate(client, guru, media):
    doc = Document()
    _soal(doc)
    _soal(doc)  # soal kembar di dalam file yang sama
    client.force_login(guru['user'])

    first = _upload(client, doc, guru['mtk'])
    client.post(reverse('questions:import_confirm'), {'token': _token(first)})
    assert Question.objects.count() == 1

    again = _upload(client, doc, guru['mtk'])
    assert [i.status for i in again.context['result'].items] == ['sudah_ada', 'sudah_ada']
    client.post(reverse('questions:import_confirm'), {'token': _token(again)})
    assert Question.objects.count() == 1


@pytest.mark.django_db
def test_token_of_another_user_is_refused(client, guru, media):
    doc = Document()
    _soal(doc)
    client.force_login(guru['user'])
    token = _token(_upload(client, doc, guru['mtk']))

    other = User.objects.create_user(username='guru_lain', role=Role.GURU)
    Teacher.objects.create(user=other, full_name='Guru Lain')
    client.force_login(other)
    res = client.post(reverse('questions:import_confirm'), {'token': token})
    assert res.status_code == 404
    assert Question.objects.count() == 0


@pytest.mark.django_db
def test_admin_without_teacher_profile_cannot_import(client, media):
    admin = User.objects.create_user(username='kurikulum', role=Role.KURIKULUM)
    client.force_login(admin)
    res = client.get(reverse('questions:import'))
    assert res.status_code == 302


@pytest.mark.django_db
def test_bank_soal_shows_import_button_only_for_teachers(client, guru):
    client.force_login(guru['user'])
    assert reverse('questions:import') in client.get(reverse('questions:bank_soal')).content.decode()

    admin = User.objects.create_user(username='admin_exam', role=Role.ADMIN, is_staff=True)
    client.force_login(admin)
    assert reverse('questions:import') not in client.get(reverse('questions:bank_soal')).content.decode()


@pytest.mark.django_db
def test_broken_file_shows_message_without_staging(client, guru, media):
    client.force_login(guru['user'])
    res = _upload(client, b'bukan word', guru['mtk'], name='soal.doc')
    assert res.status_code == 400
    assert '.docx' in res.content.decode()

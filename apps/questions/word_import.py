"""
Impor butir soal dari template Word (.docx).

Satu tabel dua kolom = satu soal. Kolom kiri berisi label (Soal, A-E, Kunci, CP) yang dikenali dari
namanya, kolom kanan isinya. Gambar diambil dari sel tempat gambar ditempel. Rumus Equation Word
diubah menjadi teks sederhana dan selalu diberi peringatan agar guru memeriksanya di pratinjau.

Alur: parse_document() -> mark_duplicates() -> stash() (file sementara, maks 1 jam) -> pratinjau ->
load_stash() -> save_import(). Tidak ada soal yang masuk bank soal tanpa pratinjau.
"""
import base64
import hashlib
import io
import json
import math
import re
import shutil
import tempfile
import time
import uuid
import zipfile
from dataclasses import dataclass, field
from datetime import timedelta
from pathlib import Path

from django.conf import settings
from django.core.files.base import ContentFile
from django.db import transaction
from django.utils import timezone
from docx import Document
from docx.enum.text import WD_BREAK
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt
from PIL import Image, ImageDraw, ImageOps, UnidentifiedImageError

from .models import Question, detect_cross_referencing_options

MAX_QUESTIONS = 200
MAX_FILE_BYTES = 20 * 1024 * 1024
MAX_UNZIPPED_BYTES = 150 * 1024 * 1024
MAX_IMAGE_SIDE = 1600
PREVIEW_SIDE = 480
STASH_TTL_SECONDS = 60 * 60
OPTION_KEYS = 'ABCDE'
SLOTS = ('question', *OPTION_KEYS)
TEMPLATE_LABELS = ('Soal', 'A', 'B', 'C', 'D', 'E', 'Kunci', 'CP')
TEMPLATE_BLANK_TABLES = 10

NOT_DOCX = ("File bukan dokumen Word .docx. Bila file masih berformat .doc, buka di Word lalu pilih "
            "Simpan Sebagai > Dokumen Word (.docx).")

EXAMPLES = (
    {
        'soal': 'Hasil dari 2³ + 4 adalah ....',
        'options': ('6', '8', '10', '12', '14'),
        'kunci': 'D',
        'cp': 'CP 1 - Bilangan berpangkat',
    },
    {
        'soal': ('Perhatikan pernyataan berikut!\n1. Datang tepat waktu\n2. Menyontek saat ujian\n'
                 '3. Mengerjakan tugas sendiri\nPernyataan yang menunjukkan sikap jujur dan disiplin adalah ....'),
        'options': ('1 dan 2', '1 dan 3', '2 dan 3', '1, 2, dan 3', '2 saja'),
        'kunci': 'B',
        'cp': '',
    },
    {
        'soal': ('Perhatikan gambar berikut!\nBangun datar yang jumlah sisinya sama dengan bangun pada gambar '
                 'adalah ....'),
        'options': ('', '', '', '', ''),
        'kunci': 'B',
        'cp': 'CP 5 - Bangun datar',
        'pictures': {'Soal': (3, False), 'A': (4, False), 'B': (3, True), 'C': (5, False), 'D': (0, False),
                     'E': (6, False)},
    },
)
PICTURE_SENTENCE = 'Perhatikan gambar berikut! Benda pada gambar digunakan untuk ....'

_VML_IMAGEDATA = '{urn:schemas-microsoft-com:vml}imagedata'
_MC_CHOICE = '{http://schemas.openxmlformats.org/markup-compatibility/2006}Choice'
_MC_ALTERNATE = '{http://schemas.openxmlformats.org/markup-compatibility/2006}AlternateContent'
_M = '{http://schemas.openxmlformats.org/officeDocument/2006/math}'
_SUP = str.maketrans('0123456789+-=()n', '⁰¹²³⁴⁵⁶⁷⁸⁹⁺⁻⁼⁽⁾ⁿ')
_SUB = str.maketrans('0123456789+-=()', '₀₁₂₃₄₅₆₇₈₉₊₋₌₍₎')
_SUP_CHARS = set('0123456789+-=()n')
_SUB_CHARS = set('0123456789+-=()')


def _slot_name(slot):
    return 'Sel Soal' if slot == 'question' else f'Pilihan {slot}'


def _normalize(text):
    return re.sub(r'\s+', ' ', (text or '')).strip().lower()


_EXAMPLE_TEXTS = {_normalize(e['soal']) for e in EXAMPLES}


@dataclass
class ImportImage:
    data: bytes
    ext: str
    preview: str


@dataclass
class ImportItem:
    number: int
    question_text: str = ''
    options: dict = field(default_factory=dict)
    correct_answer: str = ''
    cp_code: str = ''
    cp_name: str = ''
    lock_option_order: bool = False
    images: dict = field(default_factory=dict)
    errors: list = field(default_factory=list)
    warnings: list = field(default_factory=list)
    duplicate: bool = False

    @property
    def status(self):
        if self.errors:
            return 'gagal'
        if self.duplicate:
            return 'sudah_ada'
        return 'peringatan' if self.warnings else 'siap'

    @property
    def importable(self):
        return self.status in ('siap', 'peringatan')

    def option_rows(self):
        return [{'key': k, 'text': self.options.get(k, ''), 'image': self.images.get(k),
                 'is_correct': k == self.correct_answer} for k in OPTION_KEYS]

    def fingerprint(self):
        parts = [_normalize(self.question_text)] + [_normalize(self.options.get(k)) for k in OPTION_KEYS]
        parts += [hashlib.sha1(self.images[s].data).hexdigest() if s in self.images else '' for s in SLOTS]
        return '\x1f'.join(parts)


@dataclass
class ImportResult:
    items: list = field(default_factory=list)
    file_error: str = ''
    skipped_examples: int = 0

    def count(self, status):
        return sum(1 for i in self.items if i.status == status)

    @property
    def importable_count(self):
        return sum(1 for i in self.items if i.importable)


# ---------------------------------------------------------------- membaca isi sel

@dataclass
class _Cell:
    text: str = ''
    image_ids: list = field(default_factory=list)
    math_count: int = 0
    math_failed: bool = False
    objects: int = 0
    nested_tables: int = 0

    @property
    def is_empty(self):
        return not (self.text or self.image_ids or self.objects or self.nested_tables)


def _script(text, align):
    if align == 'superscript':
        return text.translate(_SUP) if set(text) <= _SUP_CHARS else f'^{_group(text)}'
    if align == 'subscript':
        return text.translate(_SUB) if set(text) <= _SUB_CHARS else f'_{_group(text)}'
    return text


def _group(text):
    """Kurung bila bukan satu bilangan atau satu huruf, supaya 1/2 tetap 1/2 tetapi (a+b)/(2c)."""
    if re.fullmatch(r'\d+(?:[.,]\d+)?|\w', text):
        return text
    return f'({text})'


def _sup_text(text):
    return text.translate(_SUP) if text and set(text) <= _SUP_CHARS else (f'^{_group(text)}' if text else '')


def _sub_text(text):
    return text.translate(_SUB) if text and set(text) <= _SUB_CHARS else (f'_{_group(text)}' if text else '')


def _m(el, name):
    return el.find(f'{_M}{name}')


def _omml(el):
    """Ubah elemen rumus Office Math menjadi teks satu baris."""
    if el is None:
        return ''
    tag = el.tag.replace(_M, '') if el.tag.startswith(_M) else None
    if tag is None:
        if el.tag == qn('w:t'):
            return el.text or ''
        return ''.join(_omml(c) for c in el)
    if tag.endswith('Pr'):
        return ''
    if tag == 'r':
        return ''.join(t.text or '' for t in el.iter(f'{_M}t', qn('w:t')))
    if tag == 'f':
        return f"{_group(_omml(_m(el, 'num')))}/{_group(_omml(_m(el, 'den')))}"
    if tag == 'sSup':
        return _omml(_m(el, 'e')) + _sup_text(_omml(_m(el, 'sup')))
    if tag == 'sSub':
        return _omml(_m(el, 'e')) + _sub_text(_omml(_m(el, 'sub')))
    if tag == 'sSubSup':
        return _omml(_m(el, 'e')) + _sub_text(_omml(_m(el, 'sub'))) + _sup_text(_omml(_m(el, 'sup')))
    if tag == 'rad':
        degree = _omml(_m(el, 'deg'))
        return (_sup_text(degree) if degree else '') + '√' + _group(_omml(_m(el, 'e')))
    if tag == 'd':
        pr = _m(el, 'dPr')
        def chr_of(name, default):
            node = _m(pr, name) if pr is not None else None
            return node.get(f'{_M}val', default) if node is not None else default
        parts = [_omml(e) for e in el.findall(f'{_M}e')]
        return chr_of('begChr', '(') + chr_of('sepChr', '|').join(parts) + chr_of('endChr', ')')
    if tag == 'nary':
        pr = _m(el, 'naryPr')
        node = _m(pr, 'chr') if pr is not None else None
        symbol = node.get(f'{_M}val', '∫') if node is not None else '∫'
        return (symbol + _sub_text(_omml(_m(el, 'sub'))) + _sup_text(_omml(_m(el, 'sup')))
                + ' ' + _omml(_m(el, 'e')))
    if tag == 'func':
        return f"{_omml(_m(el, 'fName'))} {_omml(_m(el, 'e'))}"
    return ''.join(_omml(c) for c in el)


class _CellReader:
    def __init__(self):
        self.cell = _Cell()
        self.lines = []
        self.current = []

    def read(self, tc):
        for child in tc:
            if child.tag == qn('w:p'):
                self._paragraph(child)
            elif child.tag == qn('w:tbl'):
                self.cell.nested_tables += 1
            elif child.tag == qn('w:sdt'):
                content = child.find(qn('w:sdtContent'))
                if content is not None:
                    self.read(content)
        lines = [line.replace('\xa0', ' ').rstrip() for line in self.lines]
        self.cell.text = '\n'.join(lines).strip('\n').strip()
        return self.cell

    def _paragraph(self, p):
        self.current = []
        graphics_before = len(self.cell.image_ids) + self.cell.objects
        self._inline(p)
        text = ''.join(self.current)
        only_graphic = not text.strip() and len(self.cell.image_ids) + self.cell.objects > graphics_before
        if not only_graphic:
            self.lines.extend(text.split('\n'))

    def _inline(self, parent):
        for child in parent:
            tag = child.tag
            if tag == qn('w:r'):
                self._run(child)
            elif tag in (qn('w:hyperlink'), qn('w:ins'), qn('w:smartTag'), qn('w:fldSimple'), qn('w:customXml')):
                self._inline(child)
            elif tag == qn('w:sdt'):
                content = child.find(qn('w:sdtContent'))
                if content is not None:
                    self._inline(content)
            elif tag == f'{_M}oMathPara':
                for math in child.iter(f'{_M}oMath'):
                    self._math(math)
            elif tag == f'{_M}oMath':
                self._math(child)

    def _math(self, el):
        text = _omml(el).strip()
        self.cell.math_count += 1
        if not text:
            self.cell.math_failed = True
        self.current.append(text)

    def _run(self, r):
        rpr = r.find(qn('w:rPr'))
        va = rpr.find(qn('w:vertAlign')) if rpr is not None else None
        align = va.get(qn('w:val')) if va is not None else None
        for child in r:
            tag = child.tag
            if tag == qn('w:t'):
                self.current.append(_script(child.text or '', align))
            elif tag == qn('w:tab'):
                self.current.append(' ')
            elif tag in (qn('w:br'), qn('w:cr')):
                self.current.append('\n')
            elif tag == qn('w:drawing'):
                self._graphic(child)
            elif tag == qn('w:pict'):
                self._vml(child)
            elif tag == qn('w:object'):
                self.cell.objects += 1
            elif tag == _MC_ALTERNATE:
                choice = child.find(_MC_CHOICE)
                target = choice if choice is not None else child
                drawing = target.find('.//' + qn('w:drawing'))
                if drawing is not None:
                    self._graphic(drawing)
                else:
                    self.cell.objects += 1

    def _graphic(self, drawing):
        blip = drawing.find('.//' + qn('a:blip'))
        rid = blip.get(qn('r:embed')) if blip is not None else None
        if rid:
            self.cell.image_ids.append(rid)
        else:
            self.cell.objects += 1

    def _vml(self, pict):
        data = pict.find('.//' + _VML_IMAGEDATA)
        rid = data.get(qn('r:id')) if data is not None else None
        if rid:
            self.cell.image_ids.append(rid)
        else:
            self.cell.objects += 1


def _label(text):
    t = re.sub(r'[\s.:)\-]+', ' ', (text or '').strip().lower()).strip()
    t = re.sub(r'^(opsi|pilihan|jawaban)\s+', '', t)
    if t in ('soal', 'pertanyaan', 'butir soal', 'teks soal'):
        return 'question'
    if t in ('a', 'b', 'c', 'd', 'e'):
        return t.upper()
    if t.startswith('kunci'):
        return 'key'
    if t == 'cp' or t.startswith('capaian'):
        return 'cp'
    return None


def _table_cells(table):
    """Petakan label -> elemen sel isi. None bila tabel bukan tabel soal."""
    cells = {}
    for tr in table._tbl.tr_lst:
        tcs = tr.tc_lst
        if len(tcs) < 2:
            continue
        label = _label(''.join(t.text or '' for t in tcs[0].iter(qn('w:t'))))
        if label and label not in cells:
            cells[label] = tcs[-1]
    return cells if 'question' in cells else None


# ---------------------------------------------------------------- gambar

def _process_image(blob):
    try:
        img = Image.open(io.BytesIO(blob))
        fmt = img.format
        if fmt not in ('PNG', 'JPEG', 'GIF', 'BMP', 'WEBP', 'TIFF'):
            return None
        img.seek(0)
        img.load()
    except (UnidentifiedImageError, OSError, ValueError, Image.DecompressionBombError, EOFError):
        return None

    img = ImageOps.exif_transpose(img)
    has_alpha = img.mode in ('RGBA', 'LA') or (img.mode == 'P' and 'transparency' in img.info)
    img = img.convert('RGBA' if has_alpha else 'RGB')
    img.thumbnail((MAX_IMAGE_SIDE, MAX_IMAGE_SIDE))

    lossless = has_alpha or fmt in ('PNG', 'GIF', 'BMP')
    out = io.BytesIO()
    if lossless:
        img.save(out, 'PNG', optimize=True)
        ext = 'png'
    else:
        img.save(out, 'JPEG', quality=85, optimize=True)
        ext = 'jpg'

    thumb = img.copy()
    thumb.thumbnail((PREVIEW_SIDE, PREVIEW_SIDE))
    if thumb.mode == 'RGBA':
        background = Image.new('RGB', thumb.size, (255, 255, 255))
        background.paste(thumb, mask=thumb.split()[-1])
        thumb = background
    preview = io.BytesIO()
    thumb.save(preview, 'JPEG', quality=75)
    data_uri = 'data:image/jpeg;base64,' + base64.b64encode(preview.getvalue()).decode()
    return ImportImage(data=out.getvalue(), ext=ext, preview=data_uri)


# ---------------------------------------------------------------- dokumen

def _open_docx(data):
    if len(data) > MAX_FILE_BYTES:
        return None, f'Ukuran file melebihi {MAX_FILE_BYTES // (1024 * 1024)} MB. Perkecil gambar atau bagi menjadi beberapa file.'
    buf = io.BytesIO(data)
    if not zipfile.is_zipfile(buf):
        return None, NOT_DOCX
    try:
        with zipfile.ZipFile(buf) as zf:
            infos = zf.infolist()
            if 'word/document.xml' not in {i.filename for i in infos}:
                return None, NOT_DOCX
            if sum(i.file_size for i in infos) > MAX_UNZIPPED_BYTES:
                return None, 'Isi file terlalu besar untuk dibaca. Perkecil gambar atau bagi menjadi beberapa file.'
        return Document(io.BytesIO(data)), ''
    except Exception:  # noqa: BLE001 - file rusak dalam bentuk apa pun ditolak dengan pesan yang sama
        return None, 'File Word tidak bisa dibuka, kemungkinan rusak. Buka di Word, simpan ulang sebagai .docx, lalu unggah lagi.'


def _parse_cp(text, item):
    text = re.sub(r'\s+', ' ', text).strip()
    match = re.match(r'^cp\s*[-.:]?\s*(\d{1,2})\b\s*[-:.–—]?\s*(.*)$', text, re.IGNORECASE)
    if match and 1 <= int(match.group(1)) <= 10:
        item.cp_code, name = f'CP {int(match.group(1))}', match.group(2).strip()
    else:
        name = text
    if len(name) > 255:
        item.warnings.append('Keterangan CP lebih dari 255 huruf dan dipotong.')
        name = name[:255]
    item.cp_name = name


def _parse_key(text, item):
    raw = text.strip()
    match = re.fullmatch(r'(?:opsi|pilihan|jawaban)?\s*([A-Ea-e])\s*[.)]?', raw, re.IGNORECASE)
    if match:
        item.correct_answer = match.group(1).upper()
    elif not raw:
        item.errors.append('Kunci jawaban belum diisi. Tulis satu huruf: A, B, C, D, atau E.')
    else:
        item.errors.append(f'Kunci jawaban harus A, B, C, D, atau E (tertulis: "{raw[:20]}").')


def _build_item(number, cells, part):
    item = ImportItem(number=number)
    for slot in SLOTS:
        cell = cells.get(slot) or _Cell()
        name = _slot_name(slot)
        if cell.nested_tables:
            item.errors.append(f'{name} berisi tabel di dalam sel. Tabel tidak ikut terbaca; tempel tabel itu sebagai gambar.')
        if cell.objects:
            item.errors.append(f'{name} berisi objek (grafik, bentuk, atau rumus versi lama) yang tidak bisa dibaca. '
                               'Ubah menjadi gambar lalu tempel lagi.')
        if cell.math_failed:
            item.errors.append(f'Rumus di {name} tidak terbaca. Ganti rumus itu dengan gambar.')
        elif cell.math_count:
            item.warnings.append(f'Rumus di {name} diubah menjadi teks. Periksa hasilnya; ganti dengan gambar bila tidak sesuai.')
        if cell.image_ids:
            if len(cell.image_ids) > 1:
                item.warnings.append(f'{name} berisi {len(cell.image_ids)} gambar; hanya gambar pertama yang dipakai.')
            image = None
            try:
                image = _process_image(part.related_parts[cell.image_ids[0]].blob)
            except KeyError:
                pass
            if image is None:
                item.errors.append(f'Gambar di {name} tidak bisa dibaca (misalnya format EMF/WMF). '
                                   'Simpan ulang gambar sebagai PNG atau JPG lalu tempel lagi.')
            else:
                item.images[slot] = image
        if slot == 'question':
            item.question_text = cell.text
        else:
            item.options[slot] = cell.text

    if not item.question_text and 'question' in item.images:
        item.errors.append(f'Soal bergambar tetap perlu kalimat pertanyaan, misalnya "{PICTURE_SENTENCE}". '
                           'Tulis kalimatnya di sel Soal, di atas atau di bawah gambar.')
    elif not item.question_text:
        item.errors.append('Teks soal kosong. Tulis kalimat soal, misalnya "Perhatikan gambar berikut!".')
    for key in OPTION_KEYS:
        if not item.options[key] and key not in item.images:
            item.errors.append(f'Pilihan {key} kosong. Isi dengan teks atau gambar.')
    _parse_key((cells.get('key') or _Cell()).text, item)
    _parse_cp((cells.get('cp') or _Cell()).text, item)

    if detect_cross_referencing_options([item.options[k] for k in OPTION_KEYS]):
        item.lock_option_order = True
        item.warnings.append('Urutan pilihan tidak akan diacak karena ada pilihan yang merujuk pilihan lain.')
    return item


def parse_document(fileobj):
    """Baca file .docx dan kembalikan ImportResult. Tidak menyentuh database."""
    data = fileobj.read()
    result = ImportResult()
    doc, error = _open_docx(data)
    if doc is None:
        result.file_error = error
        return result

    candidates = []
    for table in doc.tables:
        tcs = _table_cells(table)
        if tcs is None:
            continue
        cells = {label: _CellReader().read(tc) for label, tc in tcs.items()}
        if all(c.is_empty for label, c in cells.items() if label in SLOTS):
            continue
        if _normalize(cells['question'].text) in _EXAMPLE_TEXTS:
            result.skipped_examples += 1
            continue
        candidates.append(cells)

    if len(candidates) > MAX_QUESTIONS:
        result.file_error = (f'File berisi {len(candidates)} soal. Maksimal {MAX_QUESTIONS} soal per file; '
                             'bagi menjadi beberapa file.')
        return result

    result.items = [_build_item(n, cells, doc.part) for n, cells in enumerate(candidates, start=1)]
    return result


def mark_duplicates(result, subject, teacher):
    """Tandai soal kembar di dalam file, dan soal tanpa gambar yang sama persis dengan bank soal guru di mapel ini."""
    existing = _existing_fingerprints(subject, teacher)
    seen = set()
    for item in result.items:
        if item.errors:
            continue
        key = item.fingerprint()
        if key in seen:
            item.duplicate = True
            continue
        seen.add(key)
        if item.images:
            if _text_key(item) in existing['any']:
                item.warnings.append('Teks soal dan pilihan sama dengan soal yang sudah ada; pastikan gambarnya berbeda.')
        elif _text_key(item) in existing['no_image']:
            item.duplicate = True


def _text_key(item):
    return '\x1f'.join([_normalize(item.question_text)] + [_normalize(item.options.get(k)) for k in OPTION_KEYS])


def _existing_fingerprints(subject, teacher):
    rows = Question.objects.filter(subject=subject, created_by=teacher).values_list(
        'question_text', 'option_a', 'option_b', 'option_c', 'option_d', 'option_e',
        'question_image', 'image_a', 'image_b', 'image_c', 'image_d', 'image_e')
    any_keys, no_image = set(), set()
    for row in rows:
        key = '\x1f'.join(_normalize(v) for v in row[:6])
        any_keys.add(key)
        if not any(row[6:]):
            no_image.add(key)
    return {'any': any_keys, 'no_image': no_image}


# ---------------------------------------------------------------- penyimpanan sementara

def import_dir():
    configured = getattr(settings, 'QUESTION_IMPORT_DIR', None)
    return Path(configured) if configured else Path(tempfile.gettempdir()) / 'exam-jingga-impor'


def purge_stale(now=None):
    root = import_dir()
    if not root.is_dir():
        return
    now = now or time.time()
    for path in root.iterdir():
        if path.is_dir() and now - path.stat().st_mtime > STASH_TTL_SECONDS:
            shutil.rmtree(path, ignore_errors=True)


def stash(result, *, user_id, subject_id, level, filename):
    """Simpan soal yang bisa diimpor ke folder sementara dan kembalikan token pratinjau."""
    purge_stale()
    token = uuid.uuid4().hex
    folder = import_dir() / token
    folder.mkdir(parents=True)
    items = []
    for item in result.items:
        if not item.importable:
            continue
        images = {}
        for slot, image in item.images.items():
            name = f'{item.number}-{slot}.{image.ext}'
            (folder / name).write_bytes(image.data)
            images[slot] = name
        items.append({
            'number': item.number, 'question_text': item.question_text, 'options': item.options,
            'correct_answer': item.correct_answer, 'cp_code': item.cp_code, 'cp_name': item.cp_name,
            'lock_option_order': item.lock_option_order, 'images': images,
        })
    meta = {'user_id': str(user_id), 'subject_id': str(subject_id), 'level': int(level), 'filename': filename,
            'created': time.time(), 'items': items}
    (folder / 'data.json').write_text(json.dumps(meta), encoding='utf-8')
    return token


def load_stash(token, user_id):
    """Kembalikan (status, data). Status: 'ok', 'missing' (kedaluwarsa/sudah disimpan), atau 'forbidden'."""
    if not re.fullmatch(r'[0-9a-f]{32}', token or ''):
        return 'missing', None
    path = import_dir() / token / 'data.json'
    if not path.is_file():
        return 'missing', None
    data = json.loads(path.read_text(encoding='utf-8'))
    if data.get('user_id') != str(user_id):
        return 'forbidden', None
    if time.time() - data.get('created', 0) > STASH_TTL_SECONDS:
        discard(token)
        return 'missing', None
    return 'ok', data


def discard(token):
    if re.fullmatch(r'[0-9a-f]{32}', token or ''):
        shutil.rmtree(import_dir() / token, ignore_errors=True)


def save_import(token, data, subject, teacher):
    """Buat soal dari data pratinjau. Soal tanpa gambar yang sudah ada di bank guru dilewati. Kembalikan (dibuat, dilewati)."""
    folder = import_dir() / token
    existing = _existing_fingerprints(subject, teacher)['no_image']
    created = skipped = 0
    saved = []
    with transaction.atomic():
        for entry in data['items']:
            options = entry['options']
            key = '\x1f'.join([_normalize(entry['question_text'])] + [_normalize(options.get(k)) for k in OPTION_KEYS])
            if not entry['images'] and key in existing:
                skipped += 1
                continue
            question = Question(
                subject=subject, level=data['level'], created_by=teacher,
                question_text=entry['question_text'], correct_answer=entry['correct_answer'],
                cp_code=entry['cp_code'], cp_name=entry['cp_name'], lock_option_order=entry['lock_option_order'],
                **{f'option_{k.lower()}': options.get(k, '') for k in OPTION_KEYS},
            )
            for slot, name in entry['images'].items():
                field_name = 'question_image' if slot == 'question' else f'image_{slot.lower()}'
                ext = name.rsplit('.', 1)[-1]
                getattr(question, field_name).save(f'{uuid.uuid4()}.{ext}', ContentFile((folder / name).read_bytes()),
                                                   save=False)
            question.save()
            saved.append(question)
            if not entry['images']:
                existing.add(key)
            created += 1
        # Bank soal diurutkan dari yang terbaru. Beri soal pertama di file waktu paling baru (selisih 1 ms per
        # soal) supaya urutan di Bank Soal sama dengan urutan di Word, di jam server mana pun.
        newest = timezone.now()
        for index, question in enumerate(saved):
            question.created_at = newest - timedelta(milliseconds=index)
        Question.objects.bulk_update(saved, ['created_at'])
    return created, skipped


# ---------------------------------------------------------------- template

def _shade(cell, color='EDE7E3'):
    tc_pr = cell._tc.get_or_add_tcPr()
    shd = OxmlElement('w:shd')
    shd.set(qn('w:val'), 'clear')
    shd.set(qn('w:color'), 'auto')
    shd.set(qn('w:fill'), color)
    tc_pr.append(shd)


def _shape_png(sides, flipped):
    """Gambar bangun datar sederhana untuk contoh soal bergambar. sides=0 berarti lingkaran."""
    img = Image.new('RGBA', (240, 160), (255, 255, 255, 0))
    draw = ImageDraw.Draw(img)
    cx, cy, r = 120, 82, 62
    if sides == 0:
        draw.ellipse((cx - r, cy - r, cx + r, cy + r), outline=(154, 52, 18), width=5)
    else:
        start = math.pi / 2 if flipped else -math.pi / 2
        if sides == 4:
            start = -math.pi / 4
        points = [(cx + r * math.cos(start + 2 * math.pi * i / sides), cy + r * math.sin(start + 2 * math.pi * i / sides))
                  for i in range(sides)]
        draw.polygon(points, outline=(154, 52, 18), width=5)
    buf = io.BytesIO()
    img.save(buf, 'PNG')
    buf.seek(0)
    return buf


def _template_table(doc, values=None, pictures=None):
    table = doc.add_table(rows=len(TEMPLATE_LABELS), cols=2)
    table.style = 'Table Grid'
    values = values or {}
    for row, label in zip(table.rows, TEMPLATE_LABELS):
        left, right = row.cells
        left.width, right.width = Cm(2.6), Cm(13.4)
        left.text = ''
        run = left.paragraphs[0].add_run(label)
        run.bold = True
        _shade(left)
        lines = str(values.get(label, '')).split('\n')
        right.paragraphs[0].text = lines[0]
        for line in lines[1:]:
            right.add_paragraph(line)
        if pictures and label in pictures:
            paragraph = right.paragraphs[0] if not any(lines) else right.add_paragraph()
            width = Cm(3.6) if label == 'Soal' else Cm(2.4)
            paragraph.add_run().add_picture(_shape_png(*pictures[label]), width=width)
    doc.add_paragraph('')


def build_template():
    """File template Word yang selalu cocok dengan pembaca impor."""
    doc = Document()
    doc.styles['Normal'].font.size = Pt(11)
    doc.add_heading('Template Impor Soal Exam Jingga', level=1)
    steps = (
        'Satu tabel untuk satu soal. Jangan mengubah tulisan di kolom kiri (Soal, A sampai E, Kunci, CP).',
        'Tulis kalimat soal di baris Soal. Gambar boleh ditempel langsung di sel Soal atau di sel pilihan A sampai E, '
        'satu gambar per sel.',
        f'Soal bergambar tetap wajib punya kalimat pertanyaan, misalnya: "{PICTURE_SENTENCE}". '
        'Tanpa kalimat, soal gagal diimpor. Lihat contoh ketiga.',
        'Semua pilihan A sampai E wajib diisi, berupa teks atau gambar.',
        'Isi Kunci dengan satu huruf: A, B, C, D, atau E.',
        'CP boleh kosong. Contoh pengisian: CP 2 - Statistika.',
        'Simbol yang diketik biasa (x², √, ½, °, ×) terbaca apa adanya. Rumus dari Insert > Equation diubah menjadi '
        'teks dan perlu diperiksa di pratinjau. Tabel di dalam soal dan rumus yang rumit tempel sebagai gambar.',
        'Untuk menambah soal, blok satu tabel kosong beserta baris kosong di bawahnya, salin (Ctrl+C), lalu tempel '
        '(Ctrl+V) di akhir dokumen.',
        f'Mata pelajaran dan tingkat kelas dipilih saat mengunggah, jadi satu file untuk satu mapel dan satu tingkat. '
        f'Maksimal {MAX_QUESTIONS} soal dan {MAX_FILE_BYTES // (1024 * 1024)} MB per file.',
        'Tiga tabel contoh di bawah ini otomatis dilewati saat impor dan boleh dihapus.',
    )
    for step in steps:
        doc.add_paragraph(step, style='List Number')

    doc.add_heading('Contoh', level=2)
    for example in EXAMPLES:
        values = {'Soal': example['soal'], 'Kunci': example['kunci'], 'CP': example['cp']}
        values.update(dict(zip(OPTION_KEYS, example['options'])))
        _template_table(doc, values, example.get('pictures'))

    doc.paragraphs[-1].add_run().add_break(WD_BREAK.PAGE)
    doc.add_heading('Soal', level=2)
    for _ in range(TEMPLATE_BLANK_TABLES):
        _template_table(doc)

    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()

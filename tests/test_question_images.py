"""Gambar soal dan opsi tersimpan saat form dikirim persis seperti browser (tanda hapus tersembunyi bernilai "0")."""
import io

import pytest
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from django.urls import reverse
from PIL import Image

from apps.master_data.models import Subject
from apps.questions.models import Question

User = get_user_model()
CLEAR_FLAGS = ['clear_question_image'] + [f'clear_image_{o}' for o in 'abcde']


def _png(name):
    buf = io.BytesIO()
    Image.new('RGB', (8, 8), (200, 80, 20)).save(buf, 'PNG')
    return SimpleUploadedFile(name, buf.getvalue(), content_type='image/png')


def _browser_post(subject, **extra):
    """Data seperti yang dikirim modal soal: semua tanda hapus bernilai "0" kecuali diubah."""
    data = {
        'subject': str(subject.id), 'level': 10, 'question_text': 'Perhatikan gambar berikut.',
        'option_a': 'a', 'option_b': 'b', 'option_c': 'c', 'option_d': 'd', 'option_e': 'e', 'correct_answer': 'A',
    }
    data.update({flag: '0' for flag in CLEAR_FLAGS})
    data.update(extra)
    return data


@pytest.fixture
def admin(db):
    return User.objects.create_superuser(username='admin_gambar', email='g@x.id', password='x-Strong-1')


@pytest.mark.django_db
def test_new_question_keeps_uploaded_images(client, admin, tmp_path):
    subject = Subject.objects.create(name='Mapel Gambar')
    client.force_login(admin)
    with override_settings(MEDIA_ROOT=str(tmp_path)):
        client.post(reverse('questions:create'),
                    _browser_post(subject, question_image=_png('soal.png'), image_b=_png('opsi-b.png')),
                    HTTP_HX_REQUEST='true')

        q = Question.objects.get(question_text='Perhatikan gambar berikut.')
        assert q.question_image and q.question_image.storage.exists(q.question_image.name)
        assert q.image_b and q.image_b.storage.exists(q.image_b.name)
        assert not q.image_a


@pytest.mark.django_db
def test_editing_question_keeps_existing_images(client, admin, tmp_path):
    subject = Subject.objects.create(name='Mapel Gambar')
    client.force_login(admin)
    with override_settings(MEDIA_ROOT=str(tmp_path)):
        client.post(reverse('questions:create'), _browser_post(subject, question_image=_png('soal.png')),
                    HTTP_HX_REQUEST='true')
        q = Question.objects.get()
        name = q.question_image.name
        assert name, 'gambar harus tersimpan saat soal dibuat'

        client.post(reverse('questions:edit', args=[q.id]),
                    _browser_post(subject, question_text='Perhatikan gambar berikut (revisi).'), HTTP_HX_REQUEST='true')

        q.refresh_from_db()
        assert q.question_text == 'Perhatikan gambar berikut (revisi).'
        assert q.question_image.name == name
        assert q.question_image.storage.exists(name)


@pytest.mark.django_db
def test_clear_flag_one_removes_image(client, admin, tmp_path):
    subject = Subject.objects.create(name='Mapel Gambar')
    client.force_login(admin)
    with override_settings(MEDIA_ROOT=str(tmp_path)):
        client.post(reverse('questions:create'), _browser_post(subject, image_c=_png('opsi-c.png')),
                    HTTP_HX_REQUEST='true')
        q = Question.objects.get()
        assert q.image_c, 'gambar opsi C harus tersimpan saat soal dibuat'

        client.post(reverse('questions:edit', args=[q.id]), _browser_post(subject, clear_image_c='1'),
                    HTTP_HX_REQUEST='true')

        q.refresh_from_db()
        assert not q.image_c

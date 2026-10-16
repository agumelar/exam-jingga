"""Kartu peserta: tanpa kotak QR palsu, dan cap kepala sekolah menimpa sebagian tanda tangan."""
import re

import pytest

from apps.core.models import SchoolSetting

from .test_reports import test_setup  # noqa: F401  (fixture)

SEAL = 'data:image/png;base64,Y2Fw'
SIGNATURE = 'data:image/png;base64,dHRk'


def _cards(client, setup):
    settings = SchoolSetting.get_settings()
    settings.school_seal_url = SEAL
    settings.headmaster_signature_url = SIGNATURE
    settings.save()
    client.force_login(setup['admin_user'])
    return client.get('/exam-cards/').content.decode()


@pytest.mark.django_db
def test_card_has_no_placeholder_qr(client, test_setup):  # noqa: F811
    html = _cards(client, test_setup)
    assert 'print-qr-box' not in html
    assert not re.search(r'>\s*QR \d+', html)


@pytest.mark.django_db
def test_seal_sits_on_the_signature(client, test_setup):  # noqa: F811
    html = _cards(client, test_setup)
    stack = re.search(r'<div class="print-sig-stack">(.*?)</div>', html, re.S)
    assert stack, 'tanda tangan dan cap harus berada dalam satu tumpukan'
    inner = stack.group(1)
    assert inner.index(SIGNATURE) < inner.index(SEAL)
    css = re.search(r'\.print-img-cap \{(.*?)\}', html, re.S).group(1)
    assert 'rotate(' in css

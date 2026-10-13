"""NIP sebagai kunci identitas guru: username Keycloak guru adalah NIP, data pusat hanya mengenal NIP."""
import base64
import io
import json
import uuid
from unittest.mock import patch

import pytest
from django.contrib.auth import get_user_model
from django.core.management import call_command

from apps.accounts.models import Role
from apps.accounts.services import keycloak_auth
from apps.master_data.models import Teacher
from apps.master_data.services.openapi_sync import MasterDataSyncService
from apps.master_data.services.teacher_identity import match_staff_to_teachers, normalize_person_name

User = get_user_model()
NIP_A = '198610282022211009'
NIP_B = '199409282022212023'
NIP_C = '199306012022211013'


def _jwt(payload):
    body = base64.urlsafe_b64encode(json.dumps(payload).encode()).decode().rstrip('=')
    return f"eyJhbGciOiJub25lIn0.{body}.sig"


def _login(sub, username, roles=('guru',)):
    payload = {'sub': str(sub), 'preferred_username': username, 'name': 'Guru', 'realm_access': {'roles': list(roles)}}
    return keycloak_auth.parse_and_sync_user({'id_token': _jwt(payload)})


def _legacy_teacher(username, full_name, nip=None):
    sub = uuid.uuid4()
    user = User.objects.create_user(username=username, role=Role.GURU, sso_id=sub, email=f'{username}@smkn1rongga.sch.id')
    return sub, Teacher.objects.create(user=user, full_name=full_name, sso_id=sub, nip=nip, email=user.email)


# ==============================================================================
# Login SSO menyimpan NIP
# ==============================================================================

@pytest.mark.django_db
def test_login_with_nip_username_stores_nip_on_legacy_teacher():
    sub, teacher = _legacy_teacher('gumelar', 'Agung Gumelar Saputra')
    user = _login(sub, NIP_A)
    teacher.refresh_from_db()
    assert teacher.nip == NIP_A
    assert user.username == 'gumelar'


@pytest.mark.django_db
def test_login_links_teacher_profile_by_nip_for_new_account():
    teacher = Teacher.objects.create(full_name='Guru Baru', nip=NIP_B, email='baru@smkn1rongga.sch.id')
    user = _login(uuid.uuid4(), NIP_B)
    teacher.refresh_from_db()
    assert teacher.user == user


@pytest.mark.django_db
def test_login_does_not_steal_nip_owned_by_another_teacher():
    Teacher.objects.create(full_name='Pemilik NIP', nip=NIP_A, email='pemilik@smkn1rongga.sch.id')
    sub, teacher = _legacy_teacher('lain', 'Guru Lain')
    _login(sub, NIP_A)
    teacher.refresh_from_db()
    assert teacher.nip is None


@pytest.mark.django_db
def test_student_login_does_not_touch_teacher_nip():
    Student_nis = '9999000001'
    user = _login(uuid.uuid4(), Student_nis, roles=())
    assert user.role == Role.SISWA
    assert not Teacher.objects.filter(nip=Student_nis).exists()


# ==============================================================================
# Sinkron guru: cocokkan lewat NIP, laporkan, jangan membuat guru
# ==============================================================================

STAFF = [
    {'id': str(uuid.uuid4()), 'nip': NIP_A, 'fullName': 'Agung Gumelar Saputra', 'ptkType': 'Guru'},
    {'id': str(uuid.uuid4()), 'nip': NIP_B, 'fullName': 'Guru Belum Ada', 'ptkType': 'Guru'},
    {'id': str(uuid.uuid4()), 'nip': NIP_C, 'fullName': 'Staf TU', 'ptkType': 'Tenaga Kependidikan'},
    {'id': str(uuid.uuid4()), 'nip': None, 'fullName': 'Petugas Piket', 'ptkType': 'Piket'},
]


@pytest.mark.django_db
def test_teacher_sync_creates_missing_teachers_from_central():
    _legacy_teacher('gumelar', 'Agung Gumelar Saputra', nip=NIP_A)
    before_users = User.objects.count()

    res = MasterDataSyncService().sync_teachers(raw_staff=STAFF)

    assert res['success'] is True
    assert res['created'] == ['Guru Belum Ada']
    created = Teacher.objects.get(nip=NIP_B)
    assert (created.full_name, created.role_level, created.user) == ('Guru Belum Ada', 'guru', None)
    # Tenaga kependidikan dan staf tanpa NIP tidak dijadikan guru; akun login tidak dibuat sinkron
    assert not Teacher.objects.filter(nip=NIP_C).exists()
    assert Teacher.objects.count() == 2
    assert User.objects.count() == before_users
    assert 'Guru Belum Ada' in res['message']


@pytest.mark.django_db
def test_created_teacher_links_on_first_sso_login():
    MasterDataSyncService().sync_teachers(raw_staff=[STAFF[1]])
    user = _login(uuid.uuid4(), NIP_B)
    assert Teacher.objects.get(nip=NIP_B).user == user
    assert Teacher.objects.count() == 1


@pytest.mark.django_db
def test_teacher_sync_links_legacy_teacher_by_exact_name_instead_of_duplicating():
    _, legacy = _legacy_teacher('asep', 'ASEP AGUS SOLEH, S.Sos')
    staff = [{'id': str(uuid.uuid4()), 'nip': NIP_A, 'fullName': 'Asep Agus Soleh', 'ptkType': 'Guru'}]

    res = MasterDataSyncService().sync_teachers(raw_staff=staff)

    legacy.refresh_from_db()
    assert legacy.nip == NIP_A
    assert res['linked'] == ['Asep Agus Soleh']
    assert res['created'] == []
    assert Teacher.objects.count() == 1


@pytest.mark.django_db
def test_teacher_sync_is_idempotent():
    service = MasterDataSyncService()
    service.sync_teachers(raw_staff=STAFF)
    res = service.sync_teachers(raw_staff=STAFF)
    assert res['created'] == []
    assert Teacher.objects.filter(nip=NIP_B).count() == 1


@pytest.mark.django_db
def test_teacher_sync_reports_teachers_missing_from_central():
    _legacy_teacher('pensiun', 'Guru Pensiun', nip='196001012000011001')
    res = MasterDataSyncService().sync_teachers(raw_staff=STAFF)
    assert res['missing_from_central'] == ['Guru Pensiun']
    assert Teacher.objects.filter(nip='196001012000011001').exists()


# ==============================================================================
# Pengisian NIP awal lewat nama
# ==============================================================================

@pytest.mark.parametrize('raw,expected', [
    ('ASEP AGUS SOLEH, S.Sos', 'asep agus soleh'),
    ('SOPIYUDIN LATIF,S.T,  ', 'sopiyudin latif'),
    ('Drs. H. Dede Kusnadi, M.Pd', 'dede kusnadi'),
    ('  Agung   Gumelar Saputra ', 'agung gumelar saputra'),
])
def test_normalize_person_name(raw, expected):
    assert normalize_person_name(raw) == expected


@pytest.mark.django_db
def test_match_staff_only_accepts_unique_exact_names():
    _, asep = _legacy_teacher('asep', 'ASEP AGUS SOLEH, S.Sos')
    _, siti1 = _legacy_teacher('siti1', 'Siti Aminah')
    _, siti2 = _legacy_teacher('siti2', 'SITI AMINAH, S.Pd')
    staff = [
        {'nip': NIP_A, 'fullName': 'Asep Agus Soleh', 'ptkType': 'Guru'},
        {'nip': NIP_B, 'fullName': 'Siti Aminah', 'ptkType': 'Guru'},
        {'nip': NIP_C, 'fullName': 'Tidak Ada Di Exam', 'ptkType': 'Guru'},
    ]
    result = match_staff_to_teachers(staff, Teacher.objects.all())
    assert [(t.id, nip) for t, nip in result['matches']] == [(asep.id, NIP_A)]
    assert result['ambiguous'] == ['Siti Aminah']
    assert result['unmatched_staff'] == ['Tidak Ada Di Exam']


@pytest.mark.django_db
def test_fill_teacher_nip_command_dry_run_then_apply():
    _, asep = _legacy_teacher('asep', 'ASEP AGUS SOLEH, S.Sos')
    _, punya = _legacy_teacher('punya', 'Guru Sudah Ber NIP', nip=NIP_B)
    staff = [{'nip': NIP_A, 'fullName': 'Asep Agus Soleh', 'ptkType': 'Guru'},
             {'nip': NIP_C, 'fullName': 'Guru Sudah Ber NIP', 'ptkType': 'Guru'}]

    with patch.object(MasterDataSyncService, 'fetch_master_api', return_value=staff):
        out = io.StringIO()
        call_command('fill_teacher_nip', stdout=out)
        asep.refresh_from_db()
        assert asep.nip is None
        assert 'uji kering' in out.getvalue().lower()

        call_command('fill_teacher_nip', '--apply', stdout=io.StringIO())

    asep.refresh_from_db()
    punya.refresh_from_db()
    assert asep.nip == NIP_A
    assert punya.nip == NIP_B


@pytest.mark.django_db
def test_placeholder_nip_from_central_is_ignored():
    # Data pusat menulis "admin" di kolom NIP untuk akun Administrator Sekolah
    _legacy_teacher('admin_sekolah', 'Administrator Sekolah')
    staff = [{'nip': 'admin', 'fullName': 'Administrator Sekolah', 'ptkType': None}]
    assert match_staff_to_teachers(staff, Teacher.objects.all())['matches'] == []
    res = MasterDataSyncService().sync_teachers(raw_staff=staff + [STAFF[1]])
    assert res['created'] == ['Guru Belum Ada']
    assert Teacher.objects.get(full_name='Administrator Sekolah').nip is None


@pytest.mark.django_db
def test_teacher_listed_as_other_staff_type_is_not_reported_missing():
    # Kepala sekolah yang juga mengajar ada di data pusat dengan ptkType "Kepala Sekolah"
    _legacy_teacher('kepsek', 'Rizal Firmansyah, S.Hut', nip='197001012000011003')
    staff = STAFF + [{'nip': '197001012000011003', 'fullName': 'Rizal Firmansyah', 'ptkType': 'Kepala Sekolah'}]
    res = MasterDataSyncService().sync_teachers(raw_staff=staff)
    assert res['missing_from_central'] == []
    assert Teacher.objects.filter(nip='197001012000011003').count() == 1

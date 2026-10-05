"""Tests for Task 2: Core Module, M3 Design Tokens, Base Layouts, and Reusable Partials."""
from pathlib import Path
import pytest
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from django.contrib.sessions.middleware import SessionMiddleware
from django.template.loader import render_to_string
from django.test import RequestFactory
from apps.core.models import SchoolSetting
from apps.core.views import DashboardView
from apps.accounts.views import LoginView


@pytest.mark.django_db
def test_school_setting_defaults():
    """Verify SchoolSetting default values match institutional requirements."""
    setting = SchoolSetting.objects.create()

    assert setting.school_name == 'SMK NEGERI 1 RONGGA'
    assert setting.academic_year == '2025/2026'
    assert setting.semester == 'Ganjil'
    assert setting.exam_name == 'Penilaian Akhir Semester (PAS)'
    assert setting.exam_city == 'Rongga'
    assert setting.school_address == ''
    assert setting.headmaster_name == ''
    assert setting.headmaster_nip == ''
    assert setting.curriculum_vicedir_name == ''
    assert setting.curriculum_vicedir_nip == ''
    assert setting.committee_chairman == ''
    assert setting.header_1 == ''
    assert setting.header_2 == ''
    assert setting.header_3 == ''
    assert str(setting) == 'SMK NEGERI 1 RONGGA (2025/2026 - Ganjil)'


@pytest.mark.django_db
def test_school_setting_singleton_helper():
    """Verify SchoolSetting.get_settings() retrieves or creates instance."""
    setting1 = SchoolSetting.get_settings()
    assert setting1.id == 1
    assert setting1.school_name == 'SMK NEGERI 1 RONGGA'

    setting1.school_name = 'SMKN 1 RONGGA UPDATED'
    setting1.save()

    setting2 = SchoolSetting.get_settings()
    assert setting2.id == 1
    assert setting2.school_name == 'SMKN 1 RONGGA UPDATED'


def test_m3_tokens_css_exists_and_contains_definitions():
    """Verify static/css/m3-tokens.css defines light and dark tokens and elevation."""
    base_dir = settings.BASE_DIR
    tokens_file = base_dir / 'static' / 'css' / 'm3-tokens.css'
    assert tokens_file.is_file()

    content = tokens_file.read_text(encoding='utf-8')
    assert '--md-sys-color-primary: #ea580c;' in content
    assert '--md-sys-color-primary: #fb923c;' in content
    assert '--md-sys-elevation-1:' in content
    assert '--md-sys-elevation-5:' in content
    assert '.m3-elevation-1' in content
    assert '.m3-state-layer' in content


def test_compiled_css_exists_and_non_empty():
    """Verify static/css/app.css is compiled and contains Tailwind and M3 rules."""
    base_dir = settings.BASE_DIR
    app_css = base_dir / 'static' / 'css' / 'app.css'
    assert app_css.is_file()
    assert app_css.stat().st_size > 10000

    content = app_css.read_text(encoding='utf-8')
    assert 'md-sys-color-primary' in content
    assert 'm3-elevation-1' in content


def test_base_template_rendering():
    """Verify base.html renders meta tags, stylesheets, and vendor scripts."""
    rendered = render_to_string('base.html', {'csrf_token': 'dummy-csrf-token'})

    assert '<meta name="google" content="notranslate">' in rendered
    assert 'static/css/app.css' in rendered
    assert 'static/vendor/htmx.min.js' in rendered
    assert 'static/vendor/alpine.min.js' in rendered
    assert 'static/vendor/lucide.min.js' in rendered
    assert 'hx-headers=' in rendered
    assert 'window.toggleTheme' in rendered
    assert 'initIcons' in rendered


def test_auth_layout_rendering():
    """Verify layouts/auth.html renders centered card and theme switcher FAB."""
    rendered = render_to_string('layouts/auth.html', {'csrf_token': 'dummy-token'})

    assert 'EXAM' in rendered
    assert 'JINGGA' in rendered
    assert 'window.toggleTheme()' in rendered
    assert 'logo_sekolah.png' in rendered


@pytest.mark.django_db
def test_app_layout_rendering():
    """Verify layouts/app.html renders sidebar, top bar, and content area."""
    User = get_user_model()
    user = User.objects.create_user(
        username='admin_layout',
        email='admin@smkn1rongga.sch.id',
        password='password123',
        role='admin'
    )

    rendered = render_to_string('layouts/app.html', {
        'user': user,
        'page_title': 'Dashboard Admin',
        'heading': 'Ringkasan Sistem',
        'csrf_token': 'dummy-token'
    })

    assert 'Dashboard Admin' in rendered
    assert 'Ringkasan Sistem' in rendered
    assert 'sidebarOpen' in rendered
    assert 'Master Data' in rendered
    assert 'Akademik' in rendered
    assert 'Siswa &amp; Logistik' in rendered or 'Siswa & Logistik' in rendered


def test_exam_layout_rendering():
    """Verify layouts/exam.html renders fullscreen sterile anti-cheat structure."""
    rendered = render_to_string('layouts/exam.html', {
        'exam_title': 'Penilaian Akhir Semester Ganjil',
        'csrf_token': 'dummy-token'
    })

    assert 'oncontextmenu="return false;"' in rendered
    assert 'ondragstart="return false;"' in rendered
    assert 'exam-timer' in rendered
    assert 'Penilaian Akhir Semester Ganjil' in rendered


def test_m3_button_component_rendering():
    """Verify button.html renders all variants, sizes, icons, and link mode."""
    # Filled button with icon
    btn1 = render_to_string('components/m3/button.html', {
        'text': 'Simpan Data',
        'variant': 'filled',
        'size': 'md',
        'icon': 'save'
    })
    assert 'Simpan Data' in btn1
    assert 'bg-orange-600' in btn1
    assert 'data-lucide="save"' in btn1
    assert '<button' in btn1

    # Outlined link button
    btn2 = render_to_string('components/m3/button.html', {
        'text': 'Kembali',
        'variant': 'outlined',
        'href': '/dashboard/',
        'icon': 'arrow-left'
    })
    assert '<a' in btn2
    assert 'href="/dashboard/"' in btn2
    assert 'border-stone-300' in btn2


def test_m3_card_component_rendering():
    """Verify card.html renders surface styles."""
    card = render_to_string('components/m3/card.html', {
        'variant': 'elevated',
        'interactive': True,
        'class': 'p-6',
        'content': '<p>Card Content</p>'
    })
    assert 'm3-elevation-1' in card
    assert 'm3-state-layer' in card
    assert 'Card Content' in card


def test_m3_radio_card_component_rendering():
    """Verify radio_card.html renders option key, content, and selected state."""
    radio = render_to_string('components/m3/radio_card.html', {
        'option_key': 'A',
        'option_text': 'Ibu kota Indonesia adalah Nusantara',
        'selected': True,
        'doubtful': False,
        'name': 'answer_1'
    })
    assert 'Ibu kota Indonesia adalah Nusantara' in radio
    assert 'bg-orange-600' in radio
    assert 'name="answer_1"' in radio
    assert 'Dipilih' in radio


def test_m3_badge_and_chip_components_rendering():
    """Verify badge.html and chip.html render status and filter tags."""
    badge = render_to_string('components/m3/badge.html', {
        'text': 'Aktif',
        'variant': 'success',
        'size': 'sm'
    })
    assert 'Aktif' in badge
    assert 'bg-emerald-100' in badge

    chip = render_to_string('components/m3/chip.html', {
        'label': 'Kelas X PPLG',
        'selected': True,
        'color_scheme': 'orange'
    })
    assert 'Kelas X PPLG' in chip
    assert 'bg-orange-100' in chip


def test_m3_drawer_and_modal_components_rendering():
    """Verify drawer.html and modal.html integrate with Alpine.js."""
    drawer = render_to_string('components/m3/drawer.html', {
        'alpine_model': 'openQuestions',
        'title': 'Daftar Nomor Soal'
    })
    assert 'openQuestions' in drawer
    assert 'Daftar Nomor Soal' in drawer

    modal = render_to_string('components/m3/modal.html', {
        'alpine_model': 'confirmSubmit',
        'title': 'Konfirmasi Kumpulkan Ujian',
        'icon': 'alert-triangle'
    })
    assert 'confirmSubmit' in modal
    assert 'Konfirmasi Kumpulkan Ujian' in modal
    assert 'data-lucide="alert-triangle"' in modal


@pytest.mark.django_db
def test_dashboard_view_authentication_and_role_redirect():
    """Verify DashboardView redirects anonymous users and students, but allows staff."""
    factory = RequestFactory()
    User = get_user_model()

    # 1. Anonymous User: must redirect 302 to login
    request_anon = factory.get('/')
    request_anon.user = AnonymousUser()
    response_anon = DashboardView.as_view()(request_anon)
    assert response_anon.status_code == 302
    assert '/accounts/login/' in response_anon.url

    # 2. Student User: must redirect 302 to student dashboard
    student_user = User.objects.create_user(
        username='siswa_test',
        role='siswa',
        password='password123'
    )
    request_student = factory.get('/')
    request_student.user = student_user
    response_student = DashboardView.as_view()(request_student)
    assert response_student.status_code == 302
    assert '/student/dashboard/' in response_student.url

    # 3. Staff/Admin User: must render HTTP 200
    admin_user = User.objects.create_user(
        username='admin_test',
        role='admin',
        password='password123'
    )
    request_admin = factory.get('/')
    request_admin.user = admin_user
    response_admin = DashboardView.as_view()(request_admin)
    assert response_admin.status_code == 200
    rendered = response_admin.render()
    assert 'EXAM' in rendered.rendered_content or 'Dashboard' in rendered.rendered_content


@pytest.mark.django_db
def test_login_view_via_request_factory():
    """Verify login view renders login page for anonymous users."""
    factory = RequestFactory()
    request_login = factory.get('/auth/login/')
    request_login.user = AnonymousUser()
    response_login = LoginView.as_view()(request_login)
    assert response_login.status_code == 200
    if hasattr(response_login, 'render'):
        response_login.render()
    content_login = response_login.rendered_content if hasattr(response_login, 'rendered_content') else response_login.content.decode()
    assert 'EXAM' in content_login


def test_custom_error_pages_render():
    """Verify custom 404 and 500 templates render with M3 styling."""
    rendered_404 = render_to_string('404.html', {'csrf_token': 'dummy'})
    assert '404' in rendered_404
    assert 'Halaman Tidak Ditemukan' in rendered_404
    assert 'Kembali ke Beranda' in rendered_404

    rendered_500 = render_to_string('500.html', {'csrf_token': 'dummy'})
    assert '500' in rendered_500
    assert 'Terjadi Kesalahan Server' in rendered_500
    assert 'Muat Ulang Halaman' in rendered_500


@pytest.mark.django_db
def test_dashboard_caching_and_partial_recent_sessions(client):
    """Verify DashboardView caching and HTMX partial recent_sessions response."""
    admin_user = User.objects.create_superuser(username='admin_dash_test', email='adm_d@test.com', password='password123')
    client.force_login(admin_user)

    # 1. Full page request
    res = client.get('/dashboard/')
    assert res.status_code == 200
    content = res.content.decode()
    assert 'Aktivitas Sesi Peserta Terkini' in content
    assert 'recent-sessions-tbody' in content

    # 2. HTMX partial recent_sessions request
    res_partial = client.get('/dashboard/?partial=recent_sessions')
    assert res_partial.status_code == 200
    partial_content = res_partial.content.decode()
    assert 'Aktivitas Sesi Peserta Terkini' not in partial_content  # Only tbody rows
    assert '<tr' in partial_content or 'Belum ada aktivitas sesi' in partial_content




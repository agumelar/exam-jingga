# 🚀 Exam Jingga DATH Stack Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Membangun ulang (*re-engineer*) aplikasi CBT SMKN 1 Rongga dari React SPA ke Modern Monolith **DATH Stack (Django + Alpine.js + Tailwind CSS + HTMX)** dengan 100% kesesuaian alur kerja (*workflow*) dan desain Material Design 3 (M3 Tokens) Jingga.

**Architecture:** Django Modern Monolith dengan arsitektur modular per domain (`apps/`), server-rendered templates dengan HTMX HTML-over-the-Wire (OOB swaps untuk navigasi dan auto-save jawaban tanpa reload), Alpine.js untuk state lokal (timer, modal, drawer, anti-cheat), dan self-contained offline-first static assets.

**Tech Stack:** Python 3.12+, Django 5.1+, HTMX 2.0+, Alpine.js 3.14+, Tailwind CSS v4, Lucide Icons, SQLite (Development) / PostgreSQL 17 (Production VPS), Keycloak OIDC.

## Global Constraints

- **Workflow & UI 100% Fidelity**: Seluruh alur (Login SSO -> Dashboard -> Penjadwalan -> Bank Soal -> CBT Engine -> Rekap Nilai) dan tata letak UI (Jingga Material 3, Dark/Light Mode) harus identik dengan versi React sebelumnya.
- **Offline-First Intranet Compatibility**: Semua aset frontend (HTMX, Alpine.js, Lucide, CSS) harus tersimpan lokal di `static/vendor/` tanpa ketergantungan CDN internet luar saat ujian berlangsung.
- **Zero-Latency Anti Data-Loss**: Engine pengerjaan soal siswa harus melakukan auto-save per perubahan jawaban via HTMX dengan update status nomor soal instan.

---

### Task 1: Environment & Project Scaffolding

**Files:**
- Create: `_legacy_react/` (Arsip file React lama)
- Create: `requirements.txt`
- Create: `package.json`
- Create: `config/__init__.py`, `config/asgi.py`, `config/wsgi.py`, `config/urls.py`
- Create: `config/settings/base.py`, `config/settings/development.py`, `config/settings/production.py`
- Create: `manage.py`
- Create: `static/vendor/htmx.min.js`, `static/vendor/alpine.min.js`, `static/vendor/lucide.min.js`
- Test: `tests/test_scaffolding.py`

**Interfaces:**
- Produces: Django project runtime yang dapat dijalankan via `python manage.py runserver` dan aset vendor lokal yang siap digunakan.

- [ ] **Step 1: Pindahkan source code React lama ke folder `_legacy_react/`**
  Pindahkan file `src/`, `public/`, `index.html`, `vite.config.js`, `eslint.config.js` ke `_legacy_react/` agar repositori bersih.

- [ ] **Step 2: Buat file `requirements.txt`**
```text
Django>=5.1,<5.2
psycopg[binary]>=3.2.0
requests>=2.32.0
python-dotenv>=1.0.1
openpyxl>=3.1.5
Pillow>=10.4.0
whitenoise>=6.7.0
pytest-django>=4.9.0
```

- [ ] **Step 3: Setup Virtual Environment & Install Dependencies**
  Jalankan: `python3 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt`

- [ ] **Step 4: Buat file `package.json` untuk kompilasi Tailwind CSS v4 lokal**
```json
{
  "name": "exam-jingga-dath",
  "private": true,
  "scripts": {
    "build:css": "npx @tailwindcss/cli -i ./static/css/input.css -o ./static/css/app.css --minify",
    "watch:css": "npx @tailwindcss/cli -i ./static/css/input.css -o ./static/css/app.css --watch"
  },
  "devDependencies": {
    "@tailwindcss/cli": "^4.0.0",
    "tailwindcss": "^4.0.0"
  }
}
```

- [ ] **Step 5: Setup Django Base & Environment Settings (`config/settings/base.py` & `development.py`)**
  Konfigurasikan modular apps, template engine, static files, dan SQLite default.

- [ ] **Step 6: Unduh & siapkan vendor static library (`htmx.min.js`, `alpine.min.js`, `lucide.min.js`) ke `static/vendor/`**

- [ ] **Step 7: Tulis dan jalankan test validasi scaffolding**
  Jalankan: `pytest tests/test_scaffolding.py` -> PASS.

---

### Task 2: Core Module, Material Design 3 (M3) System & Base Layouts

**Files:**
- Create: `apps/core/__init__.py`, `apps/core/apps.py`, `apps/core/models.py`
- Create: `apps/core/templatetags/m3_tags.py`
- Create: `static/css/m3-tokens.css`, `static/css/input.css`
- Create: `templates/base.html`
- Create: `templates/layouts/app.html` (Sidebar + Top Bar untuk Admin/Guru)
- Create: `templates/layouts/exam.html` (Layout steril untuk Siswa)
- Create: `templates/layouts/auth.html` (Layout Login)
- Create: `templates/components/m3/button.html`, `card.html`, `radio_card.html`, `chip.html`, `drawer.html`
- Test: `tests/test_core_layouts.py`

**Interfaces:**
- Produces: Komponen UI M3 Jingga, layout template dasar dengan Dark/Light theme toggle yang bekerja instan.

- [ ] **Step 1: Implementasikan `SchoolSetting` model di `apps/core/models.py`**
  Menyimpan konfigurasi identitas sekolah (Nama Sekolah, NIP Kepsek, NIP Waka Kurikulum, logo, stempel).

- [ ] **Step 2: Definisikan M3 CSS Tokens (`static/css/m3-tokens.css`)**
  Variabel CSS palet jingga SMKN 1 Rongga (`--md-sys-color-primary: #ea580c`, `--md-sys-color-surface`, `--md-sys-color-on-surface`, dll).

- [ ] **Step 3: Buat `templates/base.html` dengan inisialisasi HTMX, Alpine.js, dan Dark Mode Script**

- [ ] **Step 4: Buat layout `templates/layouts/app.html` dengan Sidebar M3 persisten dan Top AppBar**

- [ ] **Step 5: Buat komponen UI partials (`templates/components/m3/*.html`)**

- [ ] **Step 6: Jalankan test validasi rendering template layout M3**
  Jalankan: `pytest tests/test_core_layouts.py` -> PASS.

---

### Task 3: Accounts Module & Hybrid Authentication (Keycloak OIDC + Local)

**Files:**
- Create: `apps/accounts/models.py` (`CustomUser`)
- Create: `apps/accounts/services/keycloak_auth.py` (OIDC PKCE & Token Validation)
- Create: `apps/accounts/views.py` (`LoginView`, `SSOCallbackView`, `LogoutView`, `LocalLoginView`)
- Create: `apps/accounts/decorators.py` (`@role_required`)
- Create: `templates/accounts/login.html` (100% match React Login UI)
- Test: `tests/test_accounts.py`

**Interfaces:**
- Produces: Autentikasi SSO Keycloak SMKN 1 Rongga + Local Emergency Login, session cookies terenkripsi, RBAC role guard.

- [ ] **Step 1: Implementasikan `CustomUser` model dengan role (`ADMIN`, `KURIKULUM`, `GURU`, `PENGAWAS`, `SISWA`)**

- [ ] **Step 2: Implementasikan OIDC PKCE service untuk komunikasi ke `https://sso.smkn1rongga.sch.id`**

- [ ] **Step 3: Buat views otentikasi (`login_view`, `sso_callback_view`, `logout_view`)**

- [ ] **Step 4: Desain template `templates/accounts/login.html` dengan kartu elevated M3 Jingga, logo sekolah, dan tombol SSO**

- [ ] **Step 5: Buat decorator `@role_required` dan middleware proteksi rute**

- [ ] **Step 6: Jalankan test flow login, token parsing, dan role redirection**
  Jalankan: `pytest tests/test_accounts.py` -> PASS.

---

### Task 4: Master Data Module & Swagger OpenAPI Sync

**Files:**
- Create: `apps/master_data/models.py` (`Major`, `ClassRoom`, `Teacher`, `Student`, `TeacherAssignment`)
- Create: `apps/master_data/services/openapi_sync.py` (Koneksi ke `data.smkn1rongga.sch.id`)
- Create: `apps/master_data/views.py` (CRUD & list views untuk Jurusan, Kelas, Guru, Siswa, Penugasan, Sync Trigger)
- Create: `templates/master_data/*.html` + `templates/master_data/partials/*.html`
- Test: `tests/test_master_data.py`

**Interfaces:**
- Produces: Data master 722+ Siswa, Guru, Kelas, Jurusan, dan fitur sinkronisasi langsung dari server pusat data sekolah.

- [ ] **Step 1: Definisikan Django Models untuk `Major`, `ClassRoom`, `Teacher`, `Student`, `TeacherAssignment`**

- [ ] **Step 2: Buat service `openapi_sync.py` untuk menarik data siswa (`/v1/students`) dan guru (`/v1/staff`) dari server data master**

- [ ] **Step 3: Implementasikan views untuk Master Data dengan tabel interaktif HTMX (Search, Filter, Pagination tanpa reload)**

- [ ] **Step 4: Buat endpoint HTMX untuk trigger sinkronisasi data master dengan live progress indicator**

- [ ] **Step 5: Jalankan test CRUD master data dan mock OpenAPI sync**
  Jalankan: `pytest tests/test_master_data.py` -> PASS.

---

### Task 5: Question Bank Module (Bank Soal)

**Files:**
- Create: `apps/questions/models.py` (`Subject`, `Question`)
- Create: `apps/questions/views.py` (Bank Soal list, filter per mapel & tingkat, modal input/edit soal pilihan ganda A-E, upload gambar soal/opsi)
- Create: `templates/questions/bank_soal.html` + partials
- Test: `tests/test_questions.py`

**Interfaces:**
- Produces: Bank soal lengkap per mata pelajaran dengan dukungan gambar dan opsi A-E.

- [ ] **Step 1: Definisikan Django Models `Subject` dan `Question` (dengan field `question_text`, `question_image`, `option_a`..`option_e`, `correct_answer`, `level`)**

- [ ] **Step 2: Buat views & forms untuk pembuatan serta penyuntingan butir soal (support HTMX modal)**

- [ ] **Step 3: Implementasikan penanganan upload dan kompresi gambar soal/opsi**

- [ ] **Step 4: Buat antarmuka filter bank soal berdasarkan mapel, guru pembuat, dan tingkat kelas**

- [ ] **Step 5: Jalankan test validasi pembuatan soal dan kunci jawaban**
  Jalankan: `pytest tests/test_questions.py` -> PASS.

---

### Task 6: Schedules & Exam Lifecycle Module

**Files:**
- Create: `apps/schedules/models.py` (`Exam`, `ExamQuestion`, `Schedule`)
- Create: `apps/schedules/views.py` (Manajemen jadwal, pemilihan butir soal ke paket ujian, generator token, verifikasi jadwal admin)
- Create: `templates/schedules/schedule_list.html`, `select_questions.html`
- Test: `tests/test_schedules.py`

**Interfaces:**
- Produces: Alur lengkap penjadwalan ujian (`draft` -> `verified` -> `active` -> `closed`), pemilihan soal oleh guru, dan token rilis oleh admin.

- [ ] **Step 1: Definisikan Django Models `Exam`, `ExamQuestion`, `Schedule`**

- [ ] **Step 2: Implementasikan fitur pemilihan butir soal ke paket ujian (`SelectQuestionsView`) dengan indikator jumlah soal terpilih**

- [ ] **Step 3: Implementasikan sistem workflow jadwal (Admin buat jadwal -> Guru pilih soal -> Admin verifikasi & rilis token)**

- [ ] **Step 4: Buat antarmuka Card & Table Jadwal dengan status badge Material 3**

- [ ] **Step 5: Jalankan test lifecycle status jadwal dan token validation**
  Jalankan: `pytest tests/test_schedules.py` -> PASS.

---

### Task 7: Exam Engine (CBT Core) & HTMX HTML-over-the-Wire

**Files:**
- Create: `apps/exam_engine/models.py` (`ExamSession`, `StudentAnswer`)
- Create: `apps/exam_engine/views.py` (`StudentDashboardView`, `ConfirmTokenView`, `ExamInterfaceView`, `QuestionSwapView`, `SaveAnswerView`, `ViolationHandlerView`, `StatusCheckView`, `FinishExamView`)
- Create: `templates/exam_engine/student_dashboard.html`, `exam_interface.html`
- Create: `templates/exam_engine/partials/question_card.html`, `nav_drawer.html`, `lock_overlay.html`
- Test: `tests/test_exam_engine.py`

**Interfaces:**
- Produces: Pengalaman pengerjaan ujian siswa zero-latency, auto-save instan via HTMX OOB, anti-cheat detection, radar unlock, dan auto-submit.

- [ ] **Step 1: Definisikan Django Models `ExamSession` dan `StudentAnswer` (dengan field `chosen_answer`, `is_doubt`, `is_correct`)**

- [ ] **Step 2: Buat `StudentDashboardView` yang menampilkan daftar ujian aktif dan modal input token OTP**

- [ ] **Step 3: Implementasikan `ExamInterfaceView` yang memuat layout pengerjaan ujian steril (Top bar timer, Main card, Nav drawer)**

- [ ] **Step 4: Implementasikan HTMX endpoint `QuestionSwapView` untuk pergantian nomor soal tanpa reload**

- [ ] **Step 5: Implementasikan HTMX endpoint `SaveAnswerView` dengan OOB Swap pada badge nomor drawer navigasi**

- [ ] **Step 6: Implementasikan Anti-Cheat Engine (Alpine.js tab switch listener, toleransi 1x warning, 2x red screen lock)**

- [ ] **Step 7: Implementasikan Radar Polling Auto-Unlock (`StatusCheckView` tiap 3 detik)**

- [ ] **Step 8: Implementasikan Auto-Submit & Grading Engine (`FinishExamView`) saat waktu habis atau submit manual**

- [ ] **Step 9: Jalankan test simulasi pengerjaan soal, auto-save jawaban, dan kalkulasi nilai otomatis**
  Jalankan: `pytest tests/test_exam_engine.py` -> PASS.

---

### Task 8: Reports, Logistics & Live Monitoring Module

**Files:**
- Create: `apps/reports/views.py` (`LiveMonitoringView`, `UnlockSessionView`, `ExamResultsView`, `DistractorAnalysisView`, `ExamCardsView`, `AttendanceListView`, `ExportExcelView`)
- Create: `templates/reports/live_monitoring.html`, `exam_results.html`, `distractor_analysis.html`, `exam_cards.html`, `attendance_list.html`
- Test: `tests/test_reports.py`

**Interfaces:**
- Produces: Dashboard monitoring real-time (bisa unlock siswa terkunci), cetak kartu ujian, daftar hadir, analisis daya beda/pengecoh butir soal, dan ekspor Excel.

- [ ] **Step 1: Implementasikan `LiveMonitoringView` dengan HTMX auto-refresh polling tiap 3 detik dan tombol Unlock siswa**

- [ ] **Step 2: Implementasikan `ExamResultsView` (rekapitulasi nilai per kelas, filter siswa, status pengerjaan)**

- [ ] **Step 3: Implementasikan `DistractorAnalysisView` (analisis sebaran pilihan jawaban A-E dan tingkat kesulitan butir soal)**

- [ ] **Step 4: Buat halaman cetak kartu ujian peserta dan daftar hadir terformat rapi sesuai kop sekolah**

- [ ] **Step 5: Implementasikan ekspor laporan nilai ke format file Excel (`.xlsx`) via openpyxl**

- [ ] **Step 6: Jalankan test kalkulasi analisis butir soal dan ekspor Excel**
  Jalankan: `pytest tests/test_reports.py` -> PASS.

---

### Task 9: Production Deployment Config & Final Verification

**Files:**
- Create: `config/settings/production.py` (PostgreSQL VPS Supavisor connection, WhiteNoise, Security Headers)
- Create: `scripts/deploy_vps_dath.sh` (Skrip deploy otomatis ke server 145.241.157.243)
- Create: `scripts/gunicorn_conf.py`, `scripts/nginx_dath.conf`
- Modify: `HANDOFF.md`, `log.md`
- Test: `tests/test_e2e_workflow.py`

**Interfaces:**
- Produces: Konfigurasi produksi siap jalan di VPS Ubuntu 24.04 ARM64, dokumentasi otomatis terbarui.

- [ ] **Step 1: Konfigurasikan `config/settings/production.py` untuk PostgreSQL 17 VPS (`dbexam.smkn1rongga.sch.id`)**

- [ ] **Step 2: Setup konfigurasi WhiteNoise untuk kompresi dan caching file statis**

- [ ] **Step 3: Buat skrip Nginx & Gunicorn service configuration**

- [ ] **Step 4: Jalankan Full Test Suite (Unit + Integration + E2E Workflow)**
  Jalankan: `pytest` -> 100% PASS.

- [ ] **Step 5: Update dokumentasi `HANDOFF.md` dan `log.md`**

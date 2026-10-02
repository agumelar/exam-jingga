# 📐 Spesifikasi Desain: Re-Engineering Exam Jingga ke DATH Stack

## 📌 Ringkasan Eksekutif
* **Nama Proyek**: Exam Jingga CBT (Modern Monolith)
* **Arsitektur Baru**: **DATH Stack (Django + Alpine.js + Tailwind CSS + HTMX)**
* **Tujuan**: Membangun ulang (*re-engineering*) aplikasi CBT SMKN 1 Rongga dari React SPA + Supabase API menjadi Modern Monolith berbasis HTML-over-the-Wire dengan performa tinggi, zero latency, offline-first assets, integrasi Keycloak SSO, dan Material Design 3 (M3) Jingga UI.
* **Prinsip Utama**: **100% Workflow & UI Fidelity** (seluruh tata letak, fungsi anti-cheat, hierarki menu, alur ujian, dan skema data dipertahankan sama persis).

---

## 🏗️ 1. Struktur Modul & Direktori (Clean Monolith)

Struktur repositori diatur menjadi struktur standar modular Django dengan pengarsipan source React lama:

```
exam-jingga/
├── _legacy_react/             # Arsip source code React + Vite sebelumnya
├── config/                    # Django core project configuration
│   ├── __init__.py
│   ├── asgi.py
│   ├── settings/
│   │   ├── base.py            # Konfigurasi umum, apps, middleware, auth
│   │   ├── development.py     # SQLite, DEBUG=True
│   │   └── production.py      # PostgreSQL VPS, Supavisor, WhiteNoise, HTTPS
│   ├── urls.py                # Root routing
│   └── wsgi.py
│
├── apps/                      # Domain-driven Django modular apps
│   ├── core/                  # Base helpers, M3 template tags, context processors, SchoolSetting
│   ├── accounts/              # Custom User, Keycloak OIDC authentication, RBAC decorators
│   ├── master_data/           # Jurusan, Kelas, Siswa, Guru, Swagger API sync
│   ├── questions/             # Bank Soal, opsi A-E, upload gambar
│   ├── schedules/             # Penjadwalan, rilis token, verifikasi jadwal
│   ├── exam_engine/           # CBT Engine, HTMX question swap, auto-save, anti-cheat
│   └── reports/               # Live monitoring, kartu ujian, daftar hadir, analisis soal
│
├── templates/                 # Django Templates (HTML-over-the-Wire)
│   ├── base.html              # Shell dasar (Head, Theme Switcher, M3 theme classes)
│   ├── layouts/
│   │   ├── app.html           # Layout Admin/Guru dengan M3 Sidebar & Top AppBar
│   │   ├── exam.html          # Layout steril khusus Siswa saat Ujian
│   │   └── auth.html          # Layout Login SSO & Local
│   ├── components/m3/         # Reusable M3 UI partials (Button, Card, Modal, Chip, Drawer)
│   └── [app_name]/            # Template per fitur + folder /partials/ untuk respon HTMX
│
├── static/                    # Aset statis lokal (Offline-First)
│   ├── css/
│   │   ├── m3-tokens.css      # CSS Variables Material Design 3 (Tonal palette Jingga)
│   │   └── app.css            # Compiled Tailwind CSS
│   ├── js/
│   │   └── app.js             # Inisialisasi tema M3 & global event listener
│   ├── vendor/
│   │   ├── htmx.min.js        # HTMX core lokal
│   │   ├── alpine.min.js      # Alpine.js core lokal
│   │   └── lucide.min.js      # Ikonografi lokal
│   └── img/                   # Logo sekolah & grafis statis
│
├── manage.py
├── package.json               # Build script untuk Tailwind CSS v4
├── requirements.txt           # Python dependencies (Django, psycopg, requests, etc.)
└── .env                       # Variabel lingkungan
```

---

## 🗄️ 2. Data Models & Django ORM (PostgreSQL & SQLite)

### A. `apps.accounts` & `apps.master_data`
* **`CustomUser`**: `AbstractUser` dengan field `sso_id` (UUID), `role` (`ADMIN`, `KURIKULUM`, `GURU`, `PENGAWAS`, `SISWA`).
* **`Major`**: `id` (UUID), `code` (RPL, TBSM, TKRO, ATPH), `name`.
* **`ClassRoom`**: `id` (UUID), `major` (FK), `name` (e.g. `X RPL 1`, `XII TBSM 2`).
* **`Teacher`**: `id` (UUID), `user` (OneToOne), `full_name`, `email`, `role_level`.
* **`Student`**: `id` (UUID), `user` (OneToOne), `nis`, `full_name`, `major` (FK), `class_room` (FK), `status` (`aktif`).
* **`TeacherAssignment`**: `teacher` (FK), `subject` (FK), `class_room` (FK).

### B. `apps.questions` & `apps.schedules`
* **`Subject`**: `id` (UUID), `name`.
* **`Question`**: `id` (UUID), `subject` (FK), `question_text`, `question_image`, `option_a`..`option_e`, `image_a`..`image_e`, `correct_answer` (`A`-`E`), `level`, `created_by` (Teacher FK).
* **`Exam`**: `id` (UUID), `title`, `exam_type` (`UH`, `PTS`, `PAS`, `SAJ`), `duration` (menit), `target_question_count`, `level`, `shuffle_questions` (boolean), `subject` (FK), `teacher` (FK).
* **`ExamQuestion`**: `exam` (FK), `question` (FK), `order_number`.
* **`Schedule`**: `id` (UUID), `exam` (FK), `class_room` (FK), `teacher` (FK), `start_time`, `end_time`, `token`, `session_no`, `room_name`, `status` (`draft`, `verified`, `active`, `closed`), `teacher_quota`.

### C. `apps.exam_engine` & `apps.reports`
* **`ExamSession`**: `id` (UUID), `student` (FK), `schedule` (FK), `status` (`active`, `locked`, `finished`), `violation_count`, `score`, `started_at`, `finished_at`.
* **`StudentAnswer`**: `id` (UUID), `session` (FK), `question` (FK), `chosen_answer` (`A`-`E`), `is_correct`, `is_doubt` (boolean), `updated_at`.
* **`StudentLogistic`**: `student` (FK), `room_name`, `session_name`, `exam_period`.
* **`SchoolSetting`**: Konfigurasi nama sekolah, alamat, NIP Kepsek, NIP Waka Kurikulum, logo kiri/kanan, stempel sekolah, tanda tangan digital.

---

## 🔐 3. Autentikasi & RBAC (Hybrid SSO + Local Superuser)

1. **Keycloak OIDC Flow**:
   - Client ID: `exam-jingga`, Realm: `sekolah`, URL: `https://sso.smkn1rongga.sch.id`.
   - Menggunakan PKCE Authorization Code flow dengan parameter `prompt=login` (mencegah tabrakan sesi di lab komputer).
   - Sinkronisasi profil otomatis ke `CustomUser` saat callback OIDC berhasil diverifikasi.
2. **Local Superuser / Emergency Login**:
   - URL `/accounts/login/local/` untuk akses darurat administrator atau saat pengujian lokal tanpa internet.
3. **Role Routing Enforcement**:
   - Siswa yang berhasil login langsung diarahkan ke `/student/dashboard/`.
   - Admin / Kurikulum / Guru diarahkan ke `/dashboard/`.
   - Proteksi decorator `@role_required(['admin', 'kurikulum'])` pada seluruh rute sensitif.

---

## ⚡ 4. CBT Engine & Pola Interaksi HTMX (HTML-over-the-Wire)

### A. Tampilan Pengerjaan Ujian (`/exam/session/<uuid>/`)
* **Struktur Layout**:
  - **Top Bar**: Judul Mapel, Indikator Sisa Waktu (Alpine.js Timer), Tombol Selesai Ujian.
  - **Main Viewport (`#question-card`)**: Pertanyaan, zoomable images, dan opsi pilihan ganda A–E (`M3RadioCard`).
  - **Footer Action**: Tombol `[ Sebelumnya ]`, Checkbox `[ Ragu-ragu ]`, Tombol `[ Selanjutnya ]`.
  - **Drawer Navigasi Soal**: Grid tombol nomor soal 1..N dengan indikator warna status.

### B. Interaksi HTMX Asinkron:
1. **Pindah Nomor Soal**:
   - URL: `GET /exam/session/<id>/question/<num>/`
   - Target: `hx-target="#question-card" hx-swap="innerHTML"`
   - Respon: Kartu soal nomor target tanpa memuat ulang header dan drawer.
2. **Auto-Save Pilihan Jawaban & Ragu-Ragu**:
   - URL: `POST /exam/session/<id>/save-answer/`
   - Trigger: `hx-trigger="change"` pada radio button atau checkbox ragu-ragu.
   - Respon: HTTP 200 dengan **Out-of-Band (OOB)** HTML swap pada elemen tombol nomor drawer terkait (`#nav-btn-<num>`) untuk langsung memperbarui warna (Hijau/Kuning/Abu).
3. **Anti-Cheat Enforcement**:
   - Alpine.js mendeteksi event `document.visibilitychange` dan `window.blur`.
   - Pelanggaran 1: Modal peringatan keras.
   - Pelanggaran 2+: Mengirim sinyal lock ke server via `POST /exam/session/<id>/record-violation/` dan menampilkan **Red Screen Lock Overlay**.
   - **Radar Auto-Unlock Polling**: Elemen lock screen melakukan polling tiap 3 detik (`hx-get="/exam/session/<id>/check-lock/" hx-trigger="every 3s"`). Jika admin menekan *Unlock*, overlay langsung hilang dan ujian berlanjut.
4. **Auto-Submit Timer**:
   - Jika timer mundur mencapai 00:00:00, form ujian otomatis mengirim `POST /exam/session/<id>/finish/` untuk kalkulasi nilai akhir di database.

---

## 🎨 5. Material Design 3 (M3) Frontend Library

* **Tonal Palette Jingga SMKN 1 Rongga**:
  - Primary: `#ea580c` (`orange-600`) / Dark Primary: `#fb923c` (`orange-400`).
  - Surface: `#fafaf9` (`stone-50`) / Dark Surface: `#0c0a09` (`stone-950`).
  - Surface Container: `#f5f5f4` (`stone-100`) / Dark Surface Container: `#1c1917` (`stone-900`).
* **Komponen M3 Reusable**:
  - `m3_button.html` (Filled, Outlined, Text, Tonal, Elevated).
  - `m3_card.html` (Elevated with M3 shadows, Filled, Outlined with `rounded-3xl`).
  - `m3_radio_card.html` (Opsi jawaban pilihan ganda responsif dengan border state).
  - `m3_drawer.html` (Bottom sheet mobile drawer & desktop sidebar).
  - `m3_top_app_bar.html` (Header dengan tema toggle & user avatar).

---

## 🚀 6. Rencana Migrasi & Deployment VPS

1. **Lingkungan Lokal (Development)**:
   - Python 3.12+ dengan Virtual Environment (`.venv`).
   - Database SQLite untuk pengembangan cepat.
   - Tailwind CLI untuk live CSS hot-reload.
2. **Lingkungan Produksi (VPS 145.241.157.243)**:
   - Database PostgreSQL 17 (Supavisor connection pooler).
   - WSGI Gunicorn / ASGI Uvicorn di belakang Nginx Reverse Proxy.
   - Static files dioptimalkan dengan WhiteNoise / Nginx direct serve.

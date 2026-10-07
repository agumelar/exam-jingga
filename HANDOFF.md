# 🤝 Living Handoff Document - Exam Jingga

> **Dokumen Transisi & Konteks Sistem CBT SMKN 1 Rongga**  
> *Dokumen ini diperbarui secara otomatis setiap kali ada pekerjaan/perubahan selesai.*

---

## 📌 1. Ringkasan Eksekutif & Status Terkini
* **Nama Proyek**: Exam Jingga (Aplikasi CBT Ujian Sekolah SMKN 1 Rongga)
* **Arsitektur**: **DATH Modern Monolith** (Django 5.1 LTS, Alpine.js, Tailwind CSS v4, HTMX) menggantikan arsitektur SPA React lama.
* **Tujuan Utama**: Membangun sistem CBT sekolah yang kokoh, zero-CORS browser dependency, offline-first vendor assets, real-time HTMX auto-save & polling, mitigasi beban 722+ siswa serentak di VPS ARM64, integrasi Keycloak SSO & OpenAPI Central Data Master, serta otomatisasi deployment produksi dengan Gunicorn + WhiteNoise + Nginx + Systemd.
* **Status Keseluruhan**: **🎉 SELURUH RE-ENGINEERING DATH STACK (TASK 1 s/d TASK 12) 100% SELESAI, PASS 128 TESTS (100% PASS RATE), DAN PRODUCTION-READY UNTUK VPS UBUNTU ARM64**.

---

## 🖥️ 2. Spesifikasi Infrastruktur Server & VPS (Live Production)

| Komponen | Detail Spesifikasi | Catatan Konfigurasi |
| :--- | :--- | :--- |
| **Server OS** | Ubuntu 24.04 LTS (ARM64 / aarch64) | 4 vCPU, 24 GB RAM, 193 GB NVMe |
| **IP Server** | `145.241.157.243` (User: `ubuntu`) | Akses SSH: `ssh openclaw-server` atau key `oc-server.key` |
| **Repository GitHub** | `https://github.com/suhendararyadi/exam-jingga.git` | Branch `main` (Authenticated under `suhendararyadi`) |
| **Application Server** | Gunicorn 26+ (`scripts/gunicorn_conf.py`) | Port `127.0.0.1:8005`, 4 Workers, `gthread` mode, 4 Threads per worker (16 concurrent threads) |
| **Process Manager** | Systemd (`scripts/exam_jingga.service`) | Service `exam_jingga.service`, auto-restart, isolated environment |
| **Web Server / Reverse Proxy** | Nginx & Certbot (`scripts/nginx_dath.conf`) | SSL Let's Encrypt, HTTP/2, Static caching (`/static/`), Media proxy (`/media/`), Upstream Gunicorn `:8005`, **M3 Maintenance Page Mode** with Developer Preview Bypass (`?preview=1`) |
| **Static & Media Files** | WhiteNoise + Self-Hosted Nginx Media (`/opt/exam-jingga/media/`) | Offline vendor assets (HTMX, Alpine.js, Lucide), auto-cache busting & gzip compression, 100% self-hosted question media storage (persiapan decommissioning Supabase self-hosted) |
| **Deploy Path** | `/opt/exam-jingga/` | Automated runbook via `scripts/deploy_vps_dath.sh` |
| **Domain Aplikasi** | `https://exam.smkn1rongga.sch.id` | Pointing ke `145.241.157.243` • Status: Live Production Mode (200 OK) • SSO-First Login |
| **Database** | PostgreSQL 17 (Self-Hosted / VPS DB) | Database: `postgres`, `CONN_MAX_AGE = 600`, Port 5432 / Supavisor pooler 6543 |
| **Centralized SSO** | Keycloak SSO Server | `https://sso.smkn1rongga.sch.id/realms/sekolah` (Client `exam-jingga` Aktif, 47 Guru 100% Terhubung) |
| **Data Master Pusat** | Single Source of Truth | `https://data.smkn1rongga.sch.id` (OpenAPI Swagger `/v1/students` & `/v1/staff`) |

---

## 🏛️ 3. Rekapitulasi Modul & Pencapaian DATH Stack

| Modul / Task | Ruang Lingkup & Fitur Utama | Status & Verifikasi |
| :--- | :--- | :---: |
| **Task 1: Scaffolding & Vendor Assets** | Struktur Django 5.1, Custom User model, Offline Vendor static assets (HTMX, Alpine, Lucide), `_legacy_react/` archiving. | ✅ PASS (4 tests) |
| **Task 2: Design System M3 Jingga** | Material Design 3 + Jingga tokens, full color roles, elevation 0-5, shape tokens (rounded-xs to rounded-3xl), state layer (8%/10%/12%), Tailwind v4 compiler, base responsive layouts (`base.html`, `app.html`, `auth.html`, `exam.html`), reusable M3 atomic components (`button.html`, `card.html`, `radio_card.html`, `chip.html`, `badge.html`, `drawer.html`, `modal.html`, `sidebar.html`, `top_app_bar.html`). | ✅ PASS (10 tests) |
| **Task 3: Keycloak SSO & RBAC** | Pure Keycloak SSO button, PKCE auth code exchange, role mapping (`admin`, `kurikulum`, `guru`, `pengawas`, `siswa`), single logout. | ✅ PASS (4 tests) |
| **Task 4: Master Data & OpenAPI Sync** | CRUD Jurusan, Kelas, Guru, Siswa, Import Siswa Excel (`/import-siswa/` & template download, resolusi parser collision dengan ekstraksi fungsi Alpine & JSON safe tag, penyelarasan tipografi M3), Master Mapel (`/master-mapel/` adopsi 100% UI fidelity React + Card Grid M3 + Alpine real-time search & modal + Excel template & import, penyelarasan tipografi M3), Penugasan Mengajar (`/penugasan-guru/` + Alpine filter + SweetAlert2 + tipografi M3), background sync service dengan Swagger OpenAPI Central, Excel export. | ✅ PASS (24 tests) |
| **Task 5: Bank Soal & Rich Media** | Manajemen butir soal, opsi A-E, upload gambar soal/opsi, direct option card answer key selection (Native radio inputs + emerald highlight pada kartu opsi terintegrasi, interactive status pills [Jadikan Kunci] / [✓ KUNCI JAWABAN], dark-mode high contrast, eliminasi selektor bawah yang redundan untuk efektivitas UI/UX modal), filter jenjang & mapel, filter dinamis guru pembuat soal per mapel terdaftar (Alpine.js helper + SSR + application/json script isolation untuk eliminasi tabrakan parser HTML), role-based scoping, pemulihan penuh 284 field gambar soal & opsi dari Supabase Cloud (db.vlawnrlczxagcitlaokh.supabase.co) + sinkronisasi 284 file fisik ke media storage VPS /opt/exam-jingga/media/questions/ via restore_supabase_images. | ✅ PASS (14 tests) |
| **Task 6: Jadwal Ujian & Kolaborasi** | Paket Ujian (UH, PTS, PAS, PAT, SAJ), pemilihan butir soal dengan filter & kuota kolaboratif, generator token 6 karakter, verifikasi jadwal, route Info Peserta (`/exam-participants/<schedule_id>/`). | ✅ PASS (20 tests) |
| **Task 7: Core CBT Exam Engine** | Sterile Student Exam Interface, validasi token OTP, dynamic timer, real-time HTMX auto-save jawaban & ragu-ragu via OOB swaps, anti-cheat violation lock overlay, automated grading. | ✅ PASS (8 tests) |
| **Task 8: Laporan, Logistik & Monitoring** | Live Monitoring center HTMX polling 3s, Buka Kunci/Reset/Paksa Selesai sesi, penyelarasan parameter schedule_id, Rekap Nilai & Analisis Pengecoh (Distractor Analysis), Cetak Kartu Peserta A4 & Daftar Hadir, Alokasi Logistik Ruang & Sesi, Pengaturan Lembaga. | ✅ PASS (11 tests) |
| **Task 9: Production Configs, E2E & Deploy** | `config/settings/production.py`, Gunicorn conf, Systemd service, Nginx conf, `deploy_vps_dath.sh`, 10-stage End-to-End workflow verification test. | ✅ PASS (2 tests) |
| **Task 10: Google Material 3 (M3) UI Overhaul** | Overhaul UI menyeluruh ke Google Material Design 3 (M3): tokens CSS lengkap (Light & Dark), atomic M3 components, responsive layouts, floating timer pill, filter chips drawer, thumb-zone bottom navigation bar dengan ragu-ragu tonal toggle, M3 search bars & cards. | ✅ PASS (120 tests) |
| **Task 11: Security Hardening & M3 Error Handling** | Pengamanan rute root (`/`) dan (`/dashboard/`) dengan `LoginRequiredMixin` & auto-redirect role (anonim ke login 302, siswa ke portal siswa 302, staf ke dashboard), mitigasi total kebocoran PII & token ujian aktif, halaman error kustom M3 (`404.html` & `500.html`), perbaikan text wrapping widget pintasan cepat, dan validasi durasi jadwal ujian (min 15 menit, `end_time > start_time`). | ✅ PASS (124 tests) |
| **Task 12: CBT Operational Hardening, Hard-Stop Gates, Role Scoping & Anti-Slop UI Craft** | Caching agregasi metrik dashboard (TTL 30 detik), live monitoring HTMX polling halus (15s) pada tabel sesi terkini, penegakan Opsi A (Strict Hard-Stop) pada timer & gerbang token ujian (siswa terlambat ditolak, timer capped di waktu selesai jadwal), pembatasan peran jadwal (guru hanya Ulangan Harian, admin/kurikulum mengelola PTS/PAS/PAT/SAJ, durasi kuis min 1 menit), tombol token interaktif (copy-to-clipboard dengan Alpine visual feedback), dan empty state jadwal ujian berilustrasi kalender dengan tombol aksi (+ Buat Jadwal Baru). Sesuai standar Anti-Slop Craftmanship. | ✅ PASS (128 tests) |
| **Task 13: Capaian Pembelajaran (CP) Tagging, Penegakan 5 Opsi SMK & Robust HTMX Pagination** | Penegakan wajib 5 opsi jawaban (A, B, C, D, E) untuk seluruh soal CBT baru/edit standar SMK; Metadata Capaian Pembelajaran (`cp_code` CP 1-10 & `cp_name`) pada model & form soal; Filter CP terintegrasi pada Bank Soal (`/bank-soal/`) dan Pemilihan Soal Ujian (`/select-questions/`) lengkap dengan quick-filter chips; Perbaikan bug kritis HTMX pagination drop pada aksi CRUD soal via helper `_render_question_list_partial()`; Event listener Escape modal keyboard accessibility; Peringatan `[⚠️ Opsi E Kosong]` non-blocking untuk 38 soal legacy. | ✅ PASS (130 tests) |
| **Task 14: Penyelarasan Menyeluruh Sesuai Source of Truth (`ketentuan.md`)** | Pengelompokan paket ujian berdasarkan kesamaan himpunan guru rombel (`build_teacher_set_groups`) & pembagian kuota proporsional (`build_teacher_quota_map`); Guru rombel terpisah (misal Ade di 10 RPL 1-2 vs Beni di 10 TSM 1) menghasilkan paket ujian mandiri per rombel dengan kuota penuh 40 butir; Guru rombel bersama (mapel produktif Konsentrasi Keahlian Diman, Lucky, Husam, Janjan) kuota dibagi rata 10 butir/guru; Filter kelayakan jadwal di Student Dashboard diselaraskan berbasis `TeacherAssignment` kelas siswa (siswa hanya melihat & mengerjakan ujian dari guru kelasnya); Deduplikasi kartu kolaboratif per `exam_id`; Kebijakan Anti-Cheat: UH & PTS hanya peringatan toast (tidak pernah dikunci), sedangkan PAS/PAT/SAJ mengunci layar merah saat pelanggaran >= 2. | ✅ PASS (135 tests) |
| **TOTAL TEST SUITE** | **Seluruh 135 Pengujian Django & Integration Tests Lulus 100% (0 Error, 0 Failure)** | 🏆 **135 / 135 PASS** |

---

## 🔄 4. Prosedur Deployment VPS Produksi (`scripts/deploy_vps_dath.sh`)

Untuk mendeploy pembaharuan ke server produksi `145.241.157.243`:

```bash
# Opsi 1: Eksekusi otomatis dari lokal (via SSH)
bash scripts/deploy_vps_dath.sh main

# Opsi 2: Eksekusi manual di dalam VPS
cd /opt/exam-jingga
git pull origin main
source .venv/bin/activate
pip install -r requirements.txt
npm run build:css
python manage.py migrate --noinput
python manage.py collectstatic --noinput --clear
sudo cp scripts/exam_jingga.service /etc/systemd/system/exam_jingga.service
sudo cp scripts/nginx_dath.conf /etc/nginx/sites-available/exam.smkn1rongga.sch.id
sudo systemctl daemon-reload
sudo nginx -t && sudo systemctl reload nginx
sudo systemctl restart exam_jingga.service
```

---

## 🧪 5. Verifikasi End-to-End Lifecycle (10 Tahapan)

Test suite `tests/test_e2e_workflow.py` mensimulasikan siklus penuh asesmen sekolah secara komprehensif:
1. **Master Data Setup**: Pembuatan Jurusan TKJ, Kelas XII TKJ 1, Mapel TLJ, Akun & Profil Guru, Penugasan, dan Siswa.
2. **Question Bank**: Pembuatan 5 butir soal pilihan ganda A-E dengan kunci jawaban dan pembahasan.
3. **Exam & Schedule**: Pembuatan paket ujian PAS tingkat 12, mapping soal, pembuatan jadwal aktif dengan token `JNG888`, dan validasi status.
4. **Student Login**: Siswa login dan mengakses Student Dashboard yang menampilkan kartu ujian aktif.
5. **Token Confirmation**: Siswa menginput token 6 digit dan sistem menginisialisasi lembar jawaban `ExamSession` secara atomik.
6. **Live Exam & Auto-Save**: Siswa menjawab soal 1..5 dengan auto-save HTMX instan dan update status drawer OOB.
7. **Anti-Cheat & Radar Unlock**: Deteksi pelanggaran tab blur (toast warning pada pelanggaran 1, lock overlay pada pelanggaran 2), proktor membuka kunci sesi via endpoint proktor, dan sesi kembali aktif.
8. **Exam Completion**: Siswa menyelesaikan ujian, sistem menghitung nilai secara otomatis (skor 100.0, status tuntas).
9. **Monitoring & Results**: Proktor melihat live monitoring table, detail rekap hasil ujian, dan analisis sebaran pengecoh A-E.
10. **Excel Export**: Administrator mengunduh rekapitulasi nilai resmi (.xlsx) yang tervalidasi integritas datanya menggunakan `openpyxl`.

---

## ⚡ 6. Pembaruan Operasional Terkini (Live Ready)
* **Sentralisasi Media Storage**: 282 media gambar bank soal tersimpan permanen di storage NVMe VPS (`/opt/exam-jingga/media/`) dengan streaming Nginx CORS dan smart resolver `image_url`. Lingkungan lokal streaming langsung dari VPS tanpa membebani disk lokal.
* **Form Login Mandiri & Logout Normal**: Form login utama di depan mendukung NIS siswa & Username/NIP guru secara instan. Logout membersihkan sesi dan me-redirect langsung ke halaman login lokal.
* **Jadwal Ujian Aktif & Aturan Hard-Stop Opsi A**: Paket ujian Ulangan Harian Matematika Kelas 11 RPL 1 aktif dengan Token `MAT11X`. Siswa yang mencoba masuk setelah batas `end_time` jadwal (misal 13:31 pada jadwal 12:30-13:30) secara otomatis ditolak gerbang ujian (*strict token gate*), dan durasi sisa pengerjaan siswa terpotong otomatis agar tepat berakhir bersamaan dengan waktu penutupan jadwal.
* **Scoping Hak Akses Jadwal Guru**: Guru kini dibatasi secara eksklusif hanya dapat menjadwalkan jenis **Ulangan Harian (UH)**. Jenis ujian besar (PTS, PAS, PAT, SAJ) dikelola terpusat oleh Admin/Waka Kurikulum.
* **Standar SMK 5 Opsi & Tagging Capaian Pembelajaran (CP)**: Seluruh pembuatan dan pembaruan butir soal CBT wajib mengisi 5 pilihan jawaban (A, B, C, D, E) untuk standar SMK. Guru dapat menandai Capaian Pembelajaran (`CP 1` s/d `CP 10`) beserta topik materi untuk mempermudah penyusunan bank soal dengan ratusan butir. Filter CP hadir di halaman Bank Soal (`/bank-soal/`) dan Pemilihan Soal Ujian (`/select-questions/`) lengkap dengan quick-filter chips dan pencarian topik CP. Paginasi HTMX post-mutation distabilkan dengan helper paginator, dan 38 soal warisan legacy yang belum beropsi E diberi penanda `[⚠️ Opsi E Kosong]` non-blocking.
* **Anti-Slop Craftmanship & Live Polling**: Pemasangan live stream aktivitas ujian HTMX (interval 15 detik), caching agregasi kartu metrik dashboard (TTL 30 detik), interaktivitas tombol salin token dengan feedback visual Alpine.js, dan Empty State jadwal ujian berorientasi aksi (+ Buat Jadwal Baru).

---

## 🏛️ 7. Integrasi Keycloak SSO & Master Data Hub (School Data Platform)
* **Pilar 1 - OIDC PKCE Login**: Terhubung ke `https://sso.smkn1rongga.sch.id/realms/sekolah` dengan `prompt=login` (anti-tabrak sesi di lab komputer), pemetaan klaim `student` -> `Role.SISWA`, `ptk` -> `Role.GURU`/`Role.ADMIN`, dan auto-linking ke profil `Student` / `Teacher`.
* **Pilar 2 - M2M Client Credentials Sync**: Service `MasterDataSyncService` mendukung pengambilan token M2M dari Keycloak dan paginasi otomatis 722+ siswa aktif dari `GET https://data.smkn1rongga.sch.id/v1/students` serta guru dari `GET /v1/staff`.
* **Pilar 3 - Real-time Webhook Receiver**: Endpoint `POST https://exam.smkn1rongga.sch.id/api/webhook/sync/` terproteksi `x-api-key: exam-jingga-webhook-secret-key-2026` untuk menerima sinyal mutasi data (tambah siswa baru, mutasi rombel, update data guru) secara instan dari panel [Data Admin](https://data-admin.smkn1rongga.sch.id).



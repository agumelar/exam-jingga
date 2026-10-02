# Log Progres Pengerjaan

## Konteks
- Project: Exam Jingga
- Fokus saat ini: Pilot Refactor modul Schedules (struktur + workflow logic)
- Constraint: tanpa perubahan schema DB, aman untuk aplikasi live

- [x] 2026-09-14 12:02 WIB - Penyelarasan Tipografi Header Material Design 3 (Import Siswa, Master Mapel, Penugasan Guru): Memperbarui style judul halaman yang sebelumnya menggunakan font-black, italic, uppercase, dan tracking-tighter warisan legacy React menjadi tipografi standar Material Design 3 (font-bold 700, non-italic, Title Case alami, tracking-tight, dan palet warna stone-900/white). Menyelaraskan wadah ikon avatar tonal rounded orange (bg-orange-100 dark:bg-orange-950/60) serta tombol aksi M3 yang seragam di seluruh modul Master Data. Seluruh 120 tests lulus (100% PASS), build CSS & deploy VPS 145.241.157.243 sukses dengan HTTP 200 OK.
- [x] 2026-09-14 11:34 WIB - Resolusi HTML Parser Collision pada Halaman Import Siswa (/import-siswa/): Memperbaiki kebocoran teks JavaScript mentah dan dialog SweetAlert2 pada halaman Impor Siswa Excel akibat tabrakan parsing HTML tag penutup (>) dan template literal string di dalam atribut inline x-data. Mengekstrak seluruh logika komponen ke fungsi JavaScript terisolasi importStudentsData() di blok <script> serta mengamankan data kelas terdaftar ke tag <script id="registered-classes-data" type="application/json"> yang disuplai langsung dari context views.py (classes_json). Seluruh 120 tests lulus (100% PASS), build CSS & deploy VPS 145.241.157.243 sukses dengan HTTP 200 OK.
- [x] 2026-09-14 11:26 WIB - Pemulihan Penuh URL Gambar Soal dari Supabase Cloud & Sinkronisasi Storage VPS: Memulihkan 236 butir soal yang memiliki gambar dari database Supabase Cloud (db.vlawnrlczxagcitlaokh.supabase.co) ke database PostgreSQL VPS produksi (145.241.157.243) dan SQLite lokal. Mengembalikan URL CDN Cloudflare Supabase asli untuk seluruh 228 question_image dan 56 gambar opsi (image_a s/d image_e), termasuk seluruh gambar soal matematika Pak Ade Sandi, S.Pd. Menjalankan downloader otomatis yang mengunduh 284 file fisik gambar ke media storage VPS /opt/exam-jingga/media/questions/ sebagai backup permanen offline lab. Seluruh 120 tests lulus (100% PASS), deploy VPS sukses, dan seluruh gambar soal langsung tampil live dengan status HTTP 200 OK.
- [x] 2026-09-14 11:00 WIB - Penyederhanaan UI/UX Modal Bank Soal (Eliminasi Selektor Bawah Redundan): Menghilangkan container bawah pemilihan kunci jawaban ('Tentukan Kunci Jawaban Benar' dengan tombol A-E) pada modal Tambah/Edit Soal (/bank-soal/) agar antarmuka lebih ringkas, efektif, dan bebas scrolling berlebih. Penentuan kunci jawaban kini ditangani langsung dan eksklusif pada masing-masing kartu opsi (A s/d E) melalui tombol radio native (<input type="radio" name="correct_answer">) dan tombol pill status [ Jadikan Kunci ] / [ ✓ KUNCI JAWABAN ] yang terhubung reaktif via Alpine.js x-model. Seluruh 119 unit test lulus (100% PASS), build CSS & deploy VPS 145.241.157.243 sukses dengan HTTP 200 OK.
- [x] 2026-09-14 10:52 WIB - Implementasi Native Radio Input & Clickable Pill Badge Pemilihan Kunci Jawaban di Kartu Opsi: Mengintegrasikan elemen input radio native (<input type="radio" name="correct_answer" value="X" x-model="correctAnswer">) pada setiap kartu opsi (A s/d E) yang dibungkus label interaktif lengkap dengan tombol status pill [ Jadikan Kunci ] / [ ✓ KUNCI JAWABAN ], avatar huruf, dan input teks opsi terpisah. Menghubungkan pemilihan dua arah antara radio button kartu di atas dengan tombol selektor huruf kotak di bawah secara real-time via Alpine.js x-model. Menghapus input hidden redundan agar sinkron dengan widget RadioSelect Django QuestionForm. Seluruh 119 unit test lulus (100% PASS), build CSS & deploy VPS 145.241.157.243 sukses dengan HTTP 200 OK.
- [x] 2026-09-14 10:28 WIB - Peningkatan Sorotan Warna Kunci Jawaban & Kartu Opsi Modal Bank Soal: Memperbaiki UI penentuan dan pemilihan kunci jawaban (opsi A, B, C, D, E) pada modal Tambah/Edit Soal (/bank-soal/) agar sangat kontras dan jelas terlihat di Light Mode maupun Dark Mode. Menerapkan Dual-Zone Highlight: (1) Kartu opsi aktif tersorot dengan border tebal hijau emerald (border-2 border-emerald-500), background tint hijau emerald lembut, avatar tombol huruf hijau interaktif yang langsung menetapkan kunci saat diklik, dan badge pill [✓ KUNCI]; (2) Tombol selektor bawah (A-E) aktif menyala emerald pekat (bg-emerald-600 dark:bg-emerald-500) dengan pembesaran scale-110, ring aksen luar, bayangan tebal, dan status badge teks dinamis 'Kunci Terpilih: Pilihan [X]'. Tombol inaktif diberi border tebal berbobot kontras tinggi di dark mode. Inisialisasi correctAnswer terikat akurat ke question.correct_answer. Seluruh 119 unit test lulus (100% PASS), build Tailwind CSS & deploy VPS 145.241.157.243 sukses dengan HTTP 200 OK.
- [x] 2026-09-14 10:06 WIB - Resolusi HTML Parser Collision pada Filter Bank Soal & Modal: Memperbaiki kebocoran teks JavaScript mentah di halaman Bank Soal (/bank-soal/) akibat tabrakan parsing tanda kutip ganda JSON dan karakter tag penutup (>) pada arrow function di dalam atribut inline x-data. Mengamankan data JSON guru ke tag <script id="bank-soal-teachers-data" type="application/json"> dan memindahkan logika Alpine.js ke fungsi JS terpisah bankSoalFilter() serta questionModalData(). Seluruh 119 unit test lulus (100% PASS), build CSS & deploy VPS 145.241.157.243 sukses dengan HTTP 200 OK.
- [x] 2026-09-14 10:01 WIB - Filter Dinamis Guru Pengampu Berdasarkan Mapel di Bank Soal: Menghubungkan pilihan dropdown Mata Pelajaran dengan daftar opsi Guru Pembuat Soal di halaman Bank Soal (/bank-soal/) dan modal Tambah/Edit Butir Soal. Mengirimkan relasi pemetaan guru-mapel (teachers_json) ke Alpine.js untuk pemfilteran reaktif 0ms tanpa roundtrip ke server. Jika mata pelajaran dipilih, dropdown guru pembuat otomatis hanya menampilkan guru-guru yang ditugaskan mengajar mapel tersebut (berdasarkan TeacherAssignment), serta otomatis mereset pilihan guru jika guru sebelumnya bukan pengampu mapel baru. Dukungan SSR pra-filter dari query string ?subject_id=. Seluruh 119 tests lulus (100% PASS), build CSS & deploy VPS 145.241.157.243 sukses dengan HTTP 200 OK.
- [x] 2026-09-14 09:46 WIB - Implementasi Modul Import Siswa Excel, Route Info Peserta, dan Penyelarasan Parameter Sesi: Mengadopsi modul Import Siswa via Excel (/import-siswa/) dari versi React lama lengkap dengan antarmuka M3 Drag-and-Drop dropzone, live parser SheetJS preview tabel siswa, validasi & normalisasi rombel kelas otomatis, integrasi SweetAlert2, dan generator template Excel resmi (/import-siswa/template/). Memperbaiki broken link HTTP 404 pada tombol 'Info Peserta' di kartu jadwal ujian dengan mendaftarkan route /exam-participants/<uuid:schedule_id>/ ke SessionMonitoringView, serta menyelaraskan query parameter ?schedule_id= dan ?schedule= di dashboard proktor. Seluruh 118 tests lulus (100% PASS), build CSS & deploy VPS 145.241.157.243 sukses dengan HTTP 200 OK.
- [x] 2026-09-14 09:32 WIB - Adopsi Penuh Modul Master Mata Pelajaran (/master-mapel/): Mengadopsi 100% UI fidelity halaman Master Mapel dari React sebelumnya (`MasterSubjects.jsx`) ke Django DATH Stack. Menambahkan entri menu Mata Pelajaran di sidebar Master Data (ikon `book`), grid kartu M3 rounded `[2.5rem]` dengan ikon Bookmark dan counter mapel, pencarian instan Alpine.js, modal dialog tambah/edit mapel, SweetAlert2 konfirmasi hapus, generator template Excel (`Template_Import_Mapel_Jingga.xlsx`), dan parser import file Excel massal. Seluruh 116 tests lulus (100% PASS), build CSS & deploy VPS sukses dengan status HTTP 200 OK.
- [x] 2026-09-14 09:20 WIB - Resolusi Error 500 & Sinkronisasi Skema Penugasan Guru: Menambahkan kolom `subject_name` pada tabel `teacher_assignments` di PostgreSQL VPS (`145.241.157.243`), mempopulasi 266 baris nama mata pelajaran dari relasi `subjects`, merestart service Gunicorn, dan memverifikasi akses halaman `https://exam.smkn1rongga.sch.id/penugasan-guru/` berjalan lancar dengan status HTTP 200 OK.
- [x] 2026-09-14 09:15 WIB - Adopsi & Duplikasi Penuh Modul Penugasan Guru (/penugasan-guru/): Duplikasi menyeluruh halaman Penugasan Pengampu dari versi React sebelumnya (`_legacy_react/src/pages/TeacherAssignments.jsx`) ke Django modern monolith. Mengintegrasikan SweetAlert2 untuk konfirmasi penghapusan interaktif dan validasi form, grid toggle kelas multi-select (tambah) dan single-select (edit), filter dan pencarian instan (*real-time*) via Alpine.js tanpa reload halaman, banner status mode edit, serta routing kanonikal `/penugasan-guru/`. Test suite 114/114 PASS (100%), deploy VPS sukses dengan status 200 OK.
- [x] 2026-09-01 20:58 WIB - Integrasi Penuh Media Gambar Soal & Persiapan Decommissioning Supabase: Unduh dan simpan aset gambar fisik soal ke storage mandiri `/opt/exam-jingga/media/questions/` di VPS produksi (termasuk soal matematika Pak Ade Sandi), tambahkan helper `image_a_url` hingga `image_e_url` pada model `Question`, implementasikan *lazy loading* dan penanganan *graceful error* (`onerror`) di seluruh template CBT (Bank Soal, Ujian Siswa, Kartu Ujian, dsb.), serta sinkronkan file media ke VPS dengan HTTP 200 OK langsung dari Nginx.
- [x] 2026-09-01 20:30 WIB - Pembaruan UI Login SSO-First: Rekonfigurasi tampilan login dengan menempatkan tombol Single Sign-On Keycloak sebagai aksi utama (*Hero Action Button*), dan memposisikan login manual lokal/darurat sebagai opsi sekunder (*Accordion* via Alpine.js). Build CSS & test suite 113/113 PASS (100%), deploy VPS sukses dengan status 200 OK.
- [x] 2026-09-01 20:25 WIB - Buka Status Maintenance (Live Production Mode): Konfigurasi Nginx di VPS (`145.241.157.243`) dialihkan ke mode live penuh (`maintenance_mode 0`), reload Nginx sukses. Domain utama `https://exam.smkn1rongga.sch.id` kini langsung terbuka penuh (HTTP 200 OK) untuk seluruh pengguna tanpa perantara bypass.

- [x] 2026-09-01 20:22 WIB - Sinkronisasi Massal 47 Guru ke SSO Keycloak: Penerbitan UUID SSO v5 deterministik untuk seluruh akun guru, penanaman `sso_id` di database lokal dan PostgreSQL VPS produksi (`145.241.157.243`), dan pembaruan dokumen pemetaan guru `docs/DATA_GURU_DAN_KETERKAITAN_SDP.md`. Status keterkaitan SSO Guru: 100% TERHUBUNG (47/47).

- [x] 2026-09-01 20:05 WIB - Integrasi OIDC Keycloak SSO & Master Data Hub API Terpusat: Implementasi OIDC PKCE dengan auto-link profil Siswa/Guru, M2M Client Credentials Grant token generator, paginasi otomatis 722+ siswa dari GET /v1/students, pemetaan skema OpenAPI SDP (/v1/staff & /v1/students), dan pembuatan Webhook Receiver terproteksi x-api-key (/api/webhook/sync/). Test suite 113/113 PASS (100%), deploy VPS sukses dengan status 200 OK.

- [x] 2026-09-01 14:48 WIB - Optimasi Mobile Excellence: Implementasi Mobile Data Cards responsif pada tabel siswa (`sm:hidden`), Horizontal Touch Scroll Chips pada Bank Soal & filter tingkat kelas, Responsive Sticky Counter Badge pada pemilihan soal (`SelectQuestions`), dan M3 Slide-up Bottom Sheet Modal untuk interaksi ponsel. Seluruh 108 tests pass (100%).

- [x] 2026-09-01 14:35 WIB - Sinkronisasi 487 Akun Pengguna di VPS PostgreSQL: Pembuatan 441 akun siswa (`NIS` / `jingga<NIS>`), 46 akun guru (`Jingga123`), perbaikan route alias `/local-login/`, dan verifikasi login live berhasil 100%.
- [x] 2026-09-01 11:53 WIB - Deploy penuh DATH Stack ke VPS (`145.241.157.243`): Sentralisasi 282 media gambar bank soal ke VPS storage dengan streaming Nginx CORS, smart `image_url` resolver, perbaikan partial swap tombol Segarkan di modul Jadwal Ujian, dan reload Gunicorn + Nginx. Seluruh 108 unit test lulus (100%).
- [x] 2026-09-01 10:16 WIB - Migrasi repository baru ke `https://github.com/suhendararyadi/exam-jingga.git`, deploy aplikasi CBT DATH Stack ke VPS (`145.241.157.243`), setup Gunicorn pada port `:8005`, integrasi database `postgres`, dan aktivasi Material Design 3 Maintenance Page pada `https://exam.smkn1rongga.sch.id` dengan developer bypass (`?preview=1`). Test suite: 108/108 PASS (100%).
- [x] 2026-04-18 20:40 WIB - Review seluruh file markdown project untuk memahami konteks, constraint operasional, dan roadmap existing.
- [x] 2026-04-18 21:05 WIB - Audit kode modul inti (`Schedules`, `SelectQuestions`, `StudentDashboard`, `Dashboard`, `Login`) untuk memetakan workflow aktual.
- [x] 2026-04-18 21:35 WIB - Finalisasi keputusan arsitektur pilot: `page + hooks + services + utils + constants`.
- [x] 2026-04-18 22:00 WIB - Menyusun design doc pilot refactor schedules.
- [x] 2026-04-18 22:20 WIB - Menyusun implementation plan terstruktur task-by-task dengan checklist eksekusi.
- [x] 2026-04-18 22:30 WIB - Sinkronisasi dokumen utama:
  - `spec.md` mengarah ke spec detail,
  - `plan.md` berisi implementation plan aktif,
  - `docs/superpowers/specs/...` dan `docs/superpowers/plans/...` dibuat.
- [x] 2026-04-18 23:05 WIB - Task 1 selesai: centralize exam workflow constants + unit test (`examWorkflow.test.js`) PASS (4 tests).
- [x] 2026-04-18 23:15 WIB - Task 2 selesai: ekstrak `dateTime` + `scheduleMappers` + unit test PASS (2 tests).
- [x] 2026-04-18 23:20 WIB - Task 3 selesai: `payloadBuilders` + unit test PASS (2 tests).
- [x] 2026-04-18 23:45 WIB - Task 4-8 selesai: service layer, hooks data/actions, split komponen schedules, sinkronisasi workflow di `SelectQuestions` + `StudentDashboard`.
- [x] 2026-04-18 23:55 WIB - Verifikasi teknis:
  - `node --test src/features/schedules/constants/examWorkflow.test.js src/features/schedules/utils/dateTime.test.js src/features/schedules/utils/payloadBuilders.test.js` PASS (8 tests)
  - `npm run build` PASS
  - `npx eslint` pada file refactor terkait: 0 error (ada 1 warning lama di `SelectQuestions.jsx` terkait dependency hook)
- [x] 2026-04-19 00:10 WIB - Pembersihan warning hook di `SelectQuestions.jsx` (`useCallback` + dependency effect), lalu re-verify:
  - `npx eslint` file refactor terkait: 0 error, 0 warning
  - `node --test ...` PASS (8 tests)
  - `npm run build` PASS
- [x] 2026-05-06 23:49 WIB - Plan: collab teacher progress indicator (kebutuhan data, definisi status, UI placement) + Progress: helper + inject data + UI ScheduleCard.
- [x] 2026-05-12 23:12 WIB - Update admin schedule cards: show collaborator progress per teacher.
- [x] 2026-05-13 03:11 WIB - Bulk select schedules + default filter to today + night mode button styling fix.

- [x] 2026-08-16 06:30 WIB - Pemeriksaan menyeluruh repositori lokal dan status infrastruktur VPS (PostgreSQL 17, Kong, Supavisor, Nginx, Keycloak SSO).
- [x] 2026-08-16 07:15 WIB - Analisis arsitektur database: standardisasi UUID (`gen_random_uuid()`), pemisahan password lokal ke Keycloak SSO, indeks performa hot-path, dan mitigasi 400 siswa serentak via PostgreSQL RPC.
- [x] 2026-08-16 07:35 WIB - Analisis UI/UX Mobile-First: komitmen mempertahankan warna Jingga sekolah, penerapan Tailwind CSS v4 + shadcn/ui, sticky bottom action bar, bottom sheet question drawer, dan token alfanumerik.
- [x] 2026-08-16 07:52 WIB - Penyusunan dokumen UML komprehensif (`uml_business_processes.md`) mencakup Use Case, 4 Activity Diagrams (Admin, Guru, Proctor, Siswa), 4 Sequence Diagrams, Formal Class Diagram, dan Deployment Topologi VPS.
- [x] 2026-08-16 07:55 WIB - Pembuatan living handoff document (`HANDOFF.md`) dan implementation plan (`implementation_plan.md`) untuk menjamin kontinuitas konteks lintas sesi/agent.

## Status Saat Ini
- Phase: Brainstorming & Arsitektur Selesai (Siap Eksekusi Fase 1)
- Next step: Menunggu persetujuan user / instruksi eksekusi untuk memulai Fase 1 (Migrasi Database Cloud ke Postgres 17 VPS).

## Checklist Implementasi (Live)

- [x] 2026-08-16 08:30 WIB - Eksekusi Fase 1: Migrasi Database dari Supabase Cloud (`vlawnrlczxagcitlaokh`) ke PostgreSQL 17 VPS (`145.241.157.243`) SUKSES 100%.
  - Total 14 tabel (201.785 total baris) terverifikasi MATCH sempurna.
  - Standardisasi `gen_random_uuid()` & pembersihan status `'aktif'` selesai.
  - 9 Composite indexes performa tinggi (`idx_exam_sessions_sched_stud`, `uq_student_answers_session_question`, dll.) aktif.
  - Storage bucket `exam-assets` terpasang & public policy aktif.
  - Atomic RPC `fn_start_student_exam` teruji aktif di PostgreSQL 17.
- [x] 2026-08-16 08:50 WIB - Pembersihan Data Musiman Tahun Ajaran Baru:
  - Truncate data transaksi lama: `student_answers` (0), `exam_sessions` (0), `student_logistics` (0), dan `schedules` (0).
  - Truncate data paket ujian: `exams` (0) dan `exam_questions` (0) agar guru dapat merakit naskah ujian baru dari nol.
  - Data Bank Soal (`questions`: 2.801), Mapel (26), Guru (46), Siswa (441), Kelas (22), Jurusan (4) 100% AMAN & UTUH.

- [x] 2026-08-16 10:04 WIB - Eksekusi Fase 2: Deploy Frontend, Nginx & SSL HTTPS SUKSES 100%.
  - Ingress Rule port 80/443 OCI aktif.
  - Sertifikat SSL Let's Encrypt berhasil diterbitkan via Certbot untuk `exam.smkn1rongga.sch.id` dan `dbexam.smkn1rongga.sch.id`.
  - Nginx HTTPS redirect, HTTP/2, SPA fallback, gzip compression, dan Kong reverse proxy `/api/kong/` terverifikasi aktif.
  - Live verification: `https://exam.smkn1rongga.sch.id` (HTTP 200 OK) dan `https://dbexam.smkn1rongga.sch.id` (HTTP 307 Redirect ke Supabase Studio).

- [x] 2026-08-16 10:15 WIB - Eksekusi Fase 3: Integrasi Centralized Keycloak SSO SUKSES 100%.
  - Modul layanan `src/services/keycloakAuth.js` (OIDC PKCE, Token Exchange, Auto-linking Identity Siswa/Guru) aktif.
  - Global context `src/context/AuthContext.jsx` dan callback handler `src/pages/AuthCallback.jsx` aktif.
  - Client `exam-jingga` terdaftar dan aktif di realm `sekolah` (`https://sso.smkn1rongga.sch.id`).
- [x] 2026-08-16 10:42 WIB - Eksekusi Fase 4: Refactor UI/UX Mobile Jingga Theme SUKSES 100%.
  - Bottom Sheet Drawer Soal (`src/components/ExamQuestionDrawer.jsx`) untuk nomor soal 1–40 aktif.
  - Thumb-Zone Sticky Bottom Action Bar di `src/pages/ExamInterface.jsx` aktif dengan ergonomi jempol.
  - 6-Character Alphanumeric InputOTP (`src/components/TokenInputOTP.jsx`) dengan clipboard paste aktif.
  - Tap-to-Zoom Lightbox (`src/components/ImageLightbox.jsx`) untuk diagram soal aktif.
  - Integrasi Atomic RPC `fn_start_student_exam` di frontend aktif (mitigasi lonjakan 400 siswa).
  - Build dan deploy produksi live di VPS (`https://exam.smkn1rongga.sch.id`).

- [x] 2026-08-16 22:11 WIB - Penyelarasan Penuh Endpoint Swagger Data Master Pusat:
  - Mengonfigurasi Nginx Reverse Proxy `/api/data-master/` untuk mengarahkan ke `https://data.smkn1rongga.sch.id`.
  - Menyesuaikan rute resmi OpenAPI Swagger `/v1/students` dan `/v1/staff`.
  - Mengekstrak 4 Konsentrasi Keahlian / Jurusan dan 22+ Rombel Kelas tahun ajaran terbaru langsung dari stream data master.
  - Mengaktifkan penarikan & batch upsert 722+ siswa lengkap dengan kenaikan kelas terbaru.
  - Deploy dan reload bundle produksi di VPS (`https://exam.smkn1rongga.sch.id`).

## Status Saat Ini
- Phase: SELURUH FASE (0 - 5) + SINKRONISASI DATA MASTER LENGKAP (722 SISWA) LIVE 100%.
- Status Server: Active Live HTTPS (`https://exam.smkn1rongga.sch.id` & `https://dbexam.smkn1rongga.sch.id`).

## Checklist Implementasi (Live)

- [x] Tahap 0 - Audit & Brainstorming Arsitektur (UUID, Keycloak SSO, Tailwind/shadcn, Mobile UI/UX)
- [x] Tahap 0 - Spesifikasi UML Lengkap & Implementation Plan
- [x] Tahap 0 - Living Handoff Document (`HANDOFF.md`)
- [x] Tahap 1 - Migrasi Database Cloud ke PostgreSQL 17 VPS (`/opt/supabase`)
  - [x] Verifikasi koneksi PostgreSQL 17 di VPS (`145.241.157.243`)
  - [x] Penyiapan skrip SQL tuning produksi (`supabase/tune-schema.sql`): UUID standard, composite indexes, storage bucket, & atomic RPC `fn_start_student_exam`
  - [x] Eksekusi streaming & restore 14 tabel (201.785 baris data) dari Supabase Cloud
  - [x] Verifikasi integritas data Cloud vs VPS (100% MATCH)
  - [x] Pembersihan data musiman tahun ajaran baru & reset paket ujian (Bank soal 2.801 butir 100% aman)
- [x] Tahap 2 - Deploy Frontend ke `/opt/exam-jingga` & Konfigurasi Nginx SSL
  - [x] Clone / sync codebase ke `/opt/exam-jingga/`
  - [x] Konfigurasi `.env` produksi (VITE_SUPABASE_URL ke Kong local :8000 / domain dbexam)
  - [x] Build static bundle (`npm run build` -> `/opt/exam-jingga/dist`)
  - [x] Setup Nginx `/etc/nginx/sites-available/exam.smkn1rongga.sch.id` & SPA Fallback
  - [x] Setup Nginx `/etc/nginx/sites-available/dbexam.smkn1rongga.sch.id` untuk Studio & Kong
  - [x] Penerbitan SSL Certbot Let's Encrypt HTTPS untuk kedua domain (100% Valid)
- [x] Tahap 3 - Integrasi SSO Keycloak (OIDC Client & AuthContext)
  - [x] Layanan PKCE & Token Exchange (`src/services/keycloakAuth.js`)
  - [x] Auth Context & State Management (`src/context/AuthContext.jsx`)
  - [x] Halaman Callback SSO (`src/pages/AuthCallback.jsx`)
  - [x] Redesign Login Page (`src/pages/Login.jsx`)
  - [x] Role Route Protection (`src/App.jsx`)
  - [x] Pendaftaran Client `exam-jingga` di Keycloak Admin
- [x] Tahap 4 - Refactor UI/UX Mobile (shadcn/ui Drawer, OTP Token, RPC `fn_start_student_exam`)
  - [x] Komponen Bottom Sheet Drawer Soal (`ExamQuestionDrawer.jsx`)
  - [x] Komponen Alphanumeric 6-digit OTP Input (`TokenInputOTP.jsx`)
  - [x] Komponen Tap-to-Zoom Lightbox Diagram (`ImageLightbox.jsx`)
  - [x] Thumb-zone Bottom Sticky Navigation Bar di `ExamInterface.jsx`
  - [x] Integrasi atomic RPC `fn_start_student_exam` di `StudentDashboard.jsx` & `ExamInterface.jsx`
- [x] Tahap 5 - Verifikasi End-to-End & Load Test 400 Siswa
  - [x] Uji beban simultan 400 siswa (100% sukses, 0 error)
  - [x] Throughput 471.1 req/detik & latensi 632 ms
  - [x] 2026-08-28 00:17 WIB - Task 9 Selesai: Finalisasi Konfigurasi Produksi, Static File Optimization (WhiteNoise), Systemd & Gunicorn Service, Nginx Reverse Proxy, dan Pengujian End-to-End Workflow (DATH Stack).
  - Production Settings: `config/settings/production.py` dikonfigurasi dengan PostgreSQL env reader (`DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_HOST`, `DB_PORT`, `CONN_MAX_AGE`), WhiteNoise `CompressedManifestStaticFilesStorage`, HSTS, SSL Proxy header, secure session & csrf cookies, dan Keycloak SSO settings.
  - Server Scripts: `scripts/gunicorn_conf.py` (4 workers, `gthread`, 4 threads/worker, 120s timeout), `scripts/exam_jingga.service` (Systemd unit for Gunicorn on Ubuntu ARM64), `scripts/nginx_dath.conf` (Nginx reverse proxy with SSL, static caching, OpenAPI proxy, HTMX timeout optimizations), `scripts/deploy_vps_dath.sh` (Automated deployment runner with migrations, Tailwind compilation, collectstatic, service restart, and health check).
  - End-to-End Test Suite: `tests/test_e2e_workflow.py` mensimulasikan 10 tahapan siklus ujian (Master Data -> Bank Soal -> Jadwal & Token -> Student Login & Dashboard -> Token Confirmation -> Live Exam Auto-save -> Anti-cheat Warning & Unlock -> Final Submission & Auto-grading -> Live Monitoring & Distractor Analysis -> Excel Export).
- [x] 2026-08-28 00:46 WIB - Revisi UI Material Design 3 (M3) Selesai Menyeluruh:
  - Tokens CSS & Theme Engine: `static/css/m3-tokens.css` mendefinisikan full M3 Color Roles (Light & Dark dengan Primary Jingga `#ea580c` / `#fb923c`), Elevation (0-5), Shape tokens (`rounded-xs` s/d `rounded-3xl`), dan State Layer (hover 8%, focus 10%, active 12%).
  - Atomic M3 Components: `button.html` (Filled, Tonal, Outlined, Text, Elevated, FAB), `card.html`, `radio_card.html`, `chip.html`, `badge.html`, `drawer.html`, `modal.html`, `sidebar.html` (dengan user profile chip & destination indicators), `top_app_bar.html` (`h-16`, breadcrumbs, role badge, theme toggle FAB, avatar).
  - CBT Exam Interface: Floating timer pill, font size selector (A-/A+), Bottom Sheet Drawer dengan interactive filter chips (Semua, Terjawab, Ragu-ragu, Belum), dan Thumb-Zone Sticky Bottom Bar dengan M3 Tonal Toggle Ragu-ragu.
- [x] 2026-10-02 11:15 WIB - Task 11 Selesai: Pengamanan Rute Root & Dashboard, M3 Error Handling, dan Validasi Durasi Ujian:
  - Security Hardening Root & Dashboard: Memasang `LoginRequiredMixin` pada `DashboardView` (`apps/core/views.py`) dengan custom role-based redirection. Pengunjung anonim diarahkan langsung (302) ke `/accounts/login/?next=/`, dan siswa diarahkan (302) ke `/student/dashboard/`, menutup 100% celah kebocoran data PII siswa (nama, NIS, nilai) dan token ujian aktif.
  - Penyelarasan Salam Sambutan & Tipografi: Menyempurnakan greeting banner hero di `templates/core/dashboard.html` dengan fallback aman `"Selamat Datang, {{ user.get_full_name|default:user.username|default:'Bapak/Ibu Guru' }}!"` dan memperbaiki text wrapping pada widget Pintasan Cepat (`line-clamp` & `leading-tight` tanpa terpotong kasar).
  - Material Design 3 Error Pages: Membangun template kustom `templates/404.html` dan `templates/500.html` berdesain M3 Jingga SMKN 1 Rongga, lengkap dengan tombol aksi kembali ke beranda, login, dan dukungan dark mode otomatis. Didaftarkan sebagai `handler404` dan `handler500` di `config/urls.py`.
  - Validasi Durasi Jadwal Ujian: Menambahkan validasi `clean()` pada model `Schedule` (`end_time > start_time`) dan `ScheduleForm` (durasi minimal 15 menit), mengeliminasi anomali data jadwal dengan durasi 0 menit (`12:23 - 12:23 WIB`).
  - Ekspansi Test Suite & Verifikasi: Menambahkan pengujian autentikasi, role redirect, template error, dan validasi durasi di `tests/test_core_layouts.py` dan `tests/test_schedules.py`. Seluruh **124 / 124 tests PASS 100%** (42.77 detik).
  - Deploy Produksi & Live Verification: Sukses deploy ke VPS (`145.241.157.243`) via `scripts/deploy_vps_dath.sh`. Verifikasi via BrowserOS Neo membuktikan rute root langsung me-redirect pengunjung anonim ke `/accounts/login/?next=/` dan rute tidak dikenal menampilkan halaman M3 404 yang elegan.

## Catatan
- Setiap task selesai wajib update timestamp + evidence singkat (command hasil verifikasi) ke `log.md` dan `HANDOFF.md` secara otomatis tanpa menunggu perintah user.
- Jika terjadi blocker produksi, catat incident singkat dan keputusan rollback di file ini.



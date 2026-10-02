---
inclusion: manual
---

# Exam Jingga — CBT SMKN 1 Rongga (Project Overview)

> Dokumen konteks aplikasi. Panggil dengan `#project-overview` di chat kalau butuh Kiro menjelaskan / mengingat aplikasi ini.
> Repo: **https://github.com/agumelar/exam-jingga.git**

Aplikasi **CBT (Computer Based Test) / ujian sekolah berbasis web** untuk SMK Negeri 1 Rongga. Mendukung ujian real-time dengan monitoring, auto-grading, dan sistem anti-curang (anti-cheat lock).

---

## 1. Tech Stack

| Layer | Teknologi |
|-------|-----------|
| Frontend | React 19 + Vite 7 |
| Routing | react-router-dom 7 |
| Styling | Tailwind CSS 4 (via PostCSS) |
| Icons | lucide-react |
| Alerts/Modal | sweetalert2 |
| Backend / DB | Supabase (PostgreSQL) — Free Tier |
| Import/Export | xlsx (Excel), browser-image-compression |
| Lint | ESLint 9 |

Script utama: `npm run dev` (dev server), `npm run build`, `npm run lint`, `npm run preview`.

---

## 2. Aktor / Role

- **Admin / Kurikulum** — manajemen jadwal global, pembuatan token, kontrol status sesi siswa, monitoring live.
- **Guru** — input bank soal per mata pelajaran, pilih soal untuk paket ujian, analisis hasil (sebaran pengecoh).
- **Siswa** — mengerjakan ujian dengan batas waktu dan pengawasan aktivitas browser.

Autentikasi saat ini berbasis **session manual di `localStorage`** (`user_session`), bukan Supabase Auth penuh (lihat `App.jsx`).

---

## 3. Alur Utama

1. Guru input **Bank Soal** (`questions`).
2. Admin buat paket ujian (`exams`) & jadwal per kelas (`schedules`) + token.
3. Siswa login via token → sistem membuat **sesi** (`exam_sessions`).
4. Jawaban tersimpan otomatis ke `student_answers` (auto-sync).
5. Ujian selesai → nilai dikalkulasi otomatis → masuk analisis guru.

### Anti-Cheat
- **Tab switching**: peringatan (UH/PTS) atau penguncian sesi (PAS/PAT).
- **Auto-unlock**: polling status sesi tiap ±3 detik jika dikunci admin.
- **Auto-submit**: saat waktu habis / sesi berhenti terkunci, nilai dihitung dari jawaban terakhir di DB.
- Proteksi client-side: anti-translate (meta tag), disable right-click.

---

## 4. Struktur Kode

```
src/
├── App.jsx              # Root + definisi routing
├── main.jsx             # Entry point
├── supabaseClient.js    # Inisialisasi Supabase
├── components/
│   └── Sidebar.jsx
├── pages/               # Halaman per fitur (routing berbasis file)
│   ├── Login.jsx, Dashboard.jsx, StudentDashboard.jsx
│   ├── Master*.jsx      # MasterMajors/Classes/Students/Teachers/Subjects
│   ├── BankSoal.jsx, SelectQuestions.jsx, TeacherAssignments.jsx
│   ├── Schedules.jsx, ExamParticipants.jsx, ExamInterface.jsx
│   ├── ExamResults.jsx, ExamCards.jsx, SessionManagement.jsx
│   ├── Logistics.jsx, AttendanceList.jsx, ImportStudents.jsx
│   └── Settings.jsx
└── features/            # Modul hasil refactor (page + hooks + services + utils + constants)
    ├── schedules/       # Pilot refactor (fase 1)
    └── examSessions/    # Auto-save & anti-cheat signals
```

**Catatan arsitektur:** proyek sedang dalam **pilot refactor** — memindahkan logika dari `pages/*.jsx` monolitik ke struktur modular `features/*` (page + hooks + services + utils + constants). Modul `schedules` dan `examSessions` sudah punya unit test (`*.test.js`).

---

## 5. Skema Database (Supabase / PostgreSQL)

Tabel inti:

- `majors`, `classes`, `subjects` — master data akademik.
- `teachers` — guru + `role_level` (admin/kurikulum/guru).
- `students` — data siswa (NIS unik, relasi ke class & major).
- `teacher_assignments` — pemetaan guru ↔ mapel ↔ kelas.
- `questions` — bank soal (5 opsi A–E + gambar per opsi, `correct_answer`, `level`).
- `exams` — paket ujian (tipe UH/PTS/PAS, durasi, token, shuffle).
- `exam_questions` — soal yang dipilih untuk sebuah ujian.
- `schedules` — jadwal per kelas (start/end, token, room, kuota guru, status).
- `exam_sessions` — sesi siswa (status `active/locked/finished`, `violation_count`, `score`).
- `student_answers` — jawaban per soal (`chosen_answer`, `is_correct`, `is_doubt`).
- `student_logistics` — ruang/sesi/periode ujian siswa.
- `settings` — konfigurasi sekolah (identitas, kop, tanda tangan, dsb).

Skema lengkap ada di `DB.md`. Migrasi SQL di `supabase/migrations/`.

---

## 6. Status & Prioritas

**Sudah jadi:** Core UI/UX, anti-cheat logic, timer, auto-sync jawaban, analisis butir soal.

**Belum jadi:** Rekap cetak PDF (masih via Excel), bank soal multimedia yang lebih kompleks.

**Prioritas dekat:**
- Optimasi concurrency (limit connection pool Supabase Free Tier) untuk ujian massal (100–200 concurrent users).
- Akurasi kunci jawaban pada auto-grading.
- Pengamanan client-side tambahan.

**Batasan operasional:**
- Deploy setelah jam 16.00 (di luar jam sekolah).
- Supabase Free Tier: monitor ketat kuota Egress (2GB/minggu), DB (500MB), realtime & direct connection.

**Kriteria sukses:** zero data loss, akurasi nilai 100%, stabil hingga 100–200 concurrent users tanpa kena limit kuota.

---

## 7. Dokumen Terkait

- `spec.md`, `plan.md`, `log.md` — spec, plan, dan log progres.
- `fitur.md`, `ketentuan.md` — dokumentasi fitur & aturan bisnis.
- `runbook-deploy.md`, `migration-checklist-auth.md` — operasional deploy & migrasi auth.
- `docs/superpowers/specs/` & `docs/superpowers/plans/` — spec & plan detail per fitur.
- `DB.md` — skema database (context only).

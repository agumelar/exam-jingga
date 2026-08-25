# Analisis Proyek Exam Jingga — Skalabilitas & Efisiensi Supabase

> Dokumen analisis teknis. Fokus: kesehatan proyek CBT `exam-jingga` terhadap dua mode operasi Supabase, plus temuan keamanan.
> Tanggal analisis: 2026-07-18. Berdasarkan kondisi kode setelah pull `origin/main` (fe8a353).

---

## 0. Mode Operasi (Konteks Penting)

Aplikasi berjalan di **dua mode** tergantung musim:

| Mode | Kapan | Plan Supabase | Beban |
|------|-------|---------------|-------|
| **Harian** | UH / PTS, penggunaan rutin | **Free Tier** (500MB DB, egress 2GB/mgg) | Kecil, per kelas |
| **Ujian besar** | PAS / PAT / Ujian Akhir | **Berlangganan (Pro/berbayar)** | **±400 siswa serentak per sesi** |

Implikasi: batasan Free Tier relevan untuk pemakaian harian, tapi **event paling menegangkan adalah burst ±400 concurrent user per sesi** saat ujian akhir. Meski di plan berbayar (egress & DB size lebih longgar), **connection pool dan lonjakan serentak (thundering herd)** tetap jadi risiko nyata dan itulah fokus utama optimasi.

---

## 1. Ringkasan Eksekutif

Proyek sudah **cukup sadar batasan Supabase** di jalur paling kritis (auto-save jawaban efisien, tidak memakai realtime). Untuk skenario **400 siswa serentak per sesi**, risiko utama bergeser dari egress ke **tekanan connection pool** dan **lonjakan query/egress serempak saat semua siswa mulai di menit yang sama**.

**Status risiko:**

| Aspek | Harian (Free) | Ujian ±400 (berbayar) | Catatan |
|-------|:---:|:---:|---------|
| Kuota Realtime | ✅ | ✅ | Tidak ada subscription |
| Auto-save jawaban (write) | ✅ | ✅ | Batched upsert 1.2s — tapi lihat §3.5 (write storm) |
| Egress gambar soal | ⚠️ | ⚠️ | Base64 → spike serempak saat start |
| Connection pool | ✅ | ❌ **kritis** | `startExam` 5–7 query serial × 400 |
| `select('*')` tanpa limit | ⚠️ | ⚠️ | Beberapa halaman tarik seluruh tabel |
| Ukuran DB | ⚠️ | ⚠️ | Base64 gambar + akumulasi baris sesi |
| Keamanan (password/auth/RLS) | ❌ | ❌ | Password plaintext, auth localStorage |

---

## 2. Yang Sudah Bagus (Dipertahankan)

### 2.1 Auto-save jawaban efisien
File: `src/features/examSessions/hooks/useExamAnswerSync.js`, `services/answerService.js`, `utils/answerCache.js`

- Bukan per-keystroke. Jawaban masuk ke `Map` queue + `localStorage` dulu (tanpa network) via `enqueue()`.
- Di-*flush* tiap **1200ms** sebagai **satu batched `upsert`** dengan `onConflict: 'session_id, question_id'`.
- Jika queue kosong, `runFlush` return lebih awal → **tidak ada network call** saat idle.
- Juga di-flush saat `beforeunload` / tab hidden dan sebelum submit.
- Payload kecil (`session_id, question_id, chosen_answer, is_doubt`).

➡️ Pola tepat; mendukung klaim "zero data loss". (Catatan skala 400: lihat §3.5.)

### 2.2 Tidak memakai Realtime
Grep `.channel(`, `.subscribe(`, `postgres_changes` → **0 hasil**. Semua sinkronisasi pakai HTTP polling/manual refresh. Kuota realtime praktis tidak terpakai (bagus untuk 400 concurrent — realtime justru mahal di skala ini).

### 2.3 Monitoring proctor manual (bukan polling)
File: `src/pages/ExamParticipants.jsx`

`fetchLiveSessions()` hanya jalan saat tombol **"Refresh Live Data"** ditekan. Tidak ada beban egress terus-menerus dari dashboard pengawas. (Di skala 400, `select('*')` per refresh perlu diperketat — lihat §3.3.)

### 2.4 Optimasi query yang sudah ada
- `!inner` join untuk filter server-side (`ExamInterface` ~126/~138, `scheduleService`).
- Select kolom spesifik di hot path (`answerService` ~9, auto-unlock poll `status, violation_count`).
- `head:true` count di `Dashboard` → nol row egress.
- `.limit(1)` / `.maybeSingle()` untuk cek eksistensi (`ExamInterface` ~183, ~244).

---

## 3. Risiko Utama & Rekomendasi

### 3.1 [KRITIS di skala 400] Connection pool saat `startExam` serentak
File: `src/pages/ExamInterface.jsx` ~151–312 (`startExam`)

Setiap siswa menjalankan **5–7 query berurutan (serial `await`)**: `schedules` → `exam_sessions` → `students` → `teacher_assignments` → `exam_questions` (+ `student_answers`).

Saat **400 siswa menekan "Mulai" dalam jendela waktu yang sama** (khas awal sesi ujian akhir), ini menghasilkan **~2000–2800 query dalam beberapa detik**, semua menahan koneksi. Postgres punya batas koneksi langsung yang terbatas bahkan di plan berbayar.

**Rekomendasi:**
- **Wajib pakai connection pooler (Supavisor) mode transaction** — gunakan connection string port **6543**, bukan direct 5432. Ini penentu apakah 400 concurrent lolos atau tumbang.
- Paralelkan query independen dengan `Promise.all` (mis. `students` + `teacher_assignments`).
- Gabung logika start ke **satu RPC / Postgres function** → 1 round-trip per siswa (dari ~6 menjadi 1 → beban pool turun drastis).
- Pertimbangkan **staggering/jitter** kecil di sisi klien (delay acak 0–3 dtk saat mulai) untuk meratakan burst.

### 3.2 [TINGGI] Egress gambar soal via `questions!inner(*)` — spike serempak
File: `src/pages/ExamInterface.jsx` ~125 & ~138 (`fetchExamQuestionsWithFallback`)

Query soal menarik **seluruh kolom** termasuk `question_image` dan `image_a`..`image_e`. Jika gambar base64/data-URL, maka saat 400 siswa mulai bersamaan terjadi **lonjakan egress serempak**:

```
egress_burst ≈ jumlah_soal × ukuran_gambar × 400 (dalam waktu singkat)
```

Meski di plan berbayar kuota egress besar, spike serempak ini membebani bandwidth dan memperlambat load soal untuk semua siswa.

**Rekomendasi:**
- Pindahkan gambar ke **Supabase Storage** / CDN. File statis di CDN **di-cache browser & edge**, jadi 400 siswa tidak menarik ulang dari DB. Ini sekaligus menurunkan ukuran DB.
- Jika terpaksa base64: `select` kolom eksplisit; jangan tarik kolom gambar bila soal tak punya gambar.

### 3.3 [SEDANG] `select('*')` tanpa limit/pagination
- `fetchLiveSessions` — `exam_sessions.select('*')` semua kolom (`ExamParticipants.jsx` ~166). Di sesi 400 siswa, tiap refresh proctor menarik 400+ baris penuh.
- `student_logistics.select('*')` — seluruh tabel tanpa limit (`SessionManagement.jsx` ~35, `AttendanceList.jsx`, `ExamCards.jsx`).
- `students.select('*, classes(name)')` — full student row (`ExamParticipants.jsx` ~85).

**Rekomendasi:** select kolom yang dipakai saja + `.limit()`/pagination.

> `student_logistics.select('student_id, room_name')` tanpa `.in()` (`ExamParticipants.jsx` ~130) sengaja menarik semua baris (kolom sempit) untuk hindari `.in()` besar — trade-off yang bisa diterima.

### 3.4 [SEDANG] Pertumbuhan ukuran DB
Pendorong: base64 gambar di `questions` + akumulasi baris `student_answers`/`exam_sessions`. Satu sesi 400 siswa × 40 soal = **16.000 baris `student_answers` per sesi**; berlipat tiap sesi & mapel.

**Rekomendasi:**
- Pindahkan gambar keluar DB (§3.2).
- Job arsip/hapus sesi & jawaban lama berkala (sudah disebut di `fitur.md`).
- Pastikan ada **index** di kolom filter panas: `student_answers(session_id)`, `exam_sessions(schedule_id)`, `exam_sessions(student_id, schedule_id)`, `exam_questions(exam_id)`.

### 3.5 [PERHATIAN skala 400] Write storm dari auto-save
Auto-save flush tiap 1.2s per siswa. Dengan 400 siswa aktif → **~333 upsert/detik** konstan sepanjang ujian. Batched sudah bagus, tapi di 400 concurrent tetap beban tulis signifikan.

**Rekomendasi:**
- Tetap lewat pooler (§3.1).
- Pertimbangkan menaikkan interval flush ke 2–3 dtk saat mode ujian besar (localStorage tetap jadi jaring pengaman → zero data loss terjaga), untuk memangkas frekuensi tulis tanpa mengorbankan keamanan data.
- Pastikan unique constraint `student_answers(session_id, question_id)` ada (dipakai `onConflict`) — cek migrasi `20260506_add_student_answers_unique.sql`.

---

## 4. Temuan Keamanan

### 4.1 [TINGGI] Password plaintext
Tabel `students.password_plain` dan `teachers.password` (default `'Jingga123'`). Password plaintext ikut ter-`select` di beberapa halaman (`AttendanceList`, `ExamCards`).

**Rekomendasi:** hash password; jangan pernah `select` password ke client.

### 4.2 [TINGGI] Auth berbasis localStorage + anon key
Auth pakai `localStorage` (`user_session`) tanpa Supabase Auth/JWT. Dikombinasi `anon key`, proteksi data **bergantung penuh pada RLS**.

**Rekomendasi:** pastikan RLS aktif & ketat di semua tabel. Tanpa RLS, siapa pun dengan anon key bisa membaca/menulis tabel — makin krusial saat 400 siswa memegang anon key yang sama.

### 4.3 [RENDAH] Route `/exam-interface/:examId` tanpa guard
Di `src/App.jsx` route ini tidak dicek `session` (berbeda dari route lain). Pengecekan dilakukan di dalam `ExamInterface` via `startExam`. Perlu dikonfirmasi apakah disengaja.

---

## 5. Detail Polling / Interval (Referensi)

| Lokasi | Interval | Sentuh DB? | Beban di 400 concurrent |
|--------|----------|-----------|-------------------------|
| `ExamInterface` driftTimer | 1000ms | Tidak | Lokal |
| `ExamInterface` focusTimer | 1500ms | Tidak | Lokal |
| `ExamInterface` auto-unlock radar | 3000ms | **Ya** | Hanya sesi terkunci; ringan (2 kolom, 1 baris) |
| `ExamInterface` countdown | 1000ms | Tidak | Lokal |
| `useExamAnswerSync` flush | 1200ms | **Ya** | ~333 upsert/dtk agregat (lihat §3.5) |
| `ExamParticipants` monitoring | manual | Ya | Tarik 400+ baris tiap klik refresh |
| `SessionManagement` | on-mount | Ya | Sekali |

---

## 6. Prioritas Tindak Lanjut

1. **[Connection pool]** Pastikan koneksi lewat **Supavisor pooler (port 6543)**, paralelkan/RPC-kan `startExam` — penentu kestabilan 400 concurrent.
2. **[Egress + DB]** Pindahkan gambar soal ke Storage/CDN — hilangkan spike serempak & kecilkan DB.
3. **[Index]** Tambahkan index di kolom filter panas (§3.4).
4. **[Write]** Tinjau interval flush untuk mode ujian besar (§3.5).
5. **[Egress]** Ganti `select('*')` dengan kolom eksplisit + limit.
6. **[Keamanan]** Hash password, hentikan kirim `password_plain`, audit RLS.

---

## 7. Referensi File

- `src/supabaseClient.js` — init client (default, tanpa tuning).
- `src/features/examSessions/` — auto-save & anti-cheat signals.
- `src/pages/ExamInterface.jsx` — sesi ujian siswa, polling, `startExam`.
- `src/pages/ExamParticipants.jsx` — monitoring proctor.
- `src/pages/SessionManagement.jsx` — logistik ruang/sesi (generate ±400 siswa).
- `supabase/migrations/` — termasuk `20260506_add_student_answers_unique.sql`.
- `DB.md` — skema database.
- `fitur.md` — dokumentasi fitur & batasan operasional.

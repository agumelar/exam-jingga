# Migration Checklist Auth (Hybrid, No Downtime)

Checklist ini untuk migrasi auth dari plaintext ke hash secara bertahap, tanpa mematikan aplikasi live dan tanpa merusak alur import akun.

## Target
1. Login tetap berjalan selama migrasi.
2. Import akun tetap lancar.
3. Plaintext tidak lagi dipakai untuk autentikasi aktif.
4. Cutover aman dengan rollback cepat.

## Strategi Singkat
- Mode awal: `legacy`
- Mode transisi: `hybrid` (hash-first, fallback legacy)
- Mode akhir: `hardened` (hash-only)

## Phase A - Persiapan (Wajib sebelum implementasi)
1. Buat backup database.
2. Pastikan ada feature flag `AUTH_MODE` yang bisa diubah cepat.
3. Tentukan window deploy: 22.00-04.00 WIB.
4. Siapkan metrik baseline login:
   - success rate
   - failed rate
   - error message dominan

## Phase B - Perubahan Skema Additive
1. Tambah kolom hash password baru:
   - `teachers.password_hash` (nullable)
   - `students.password_hash` (nullable)
2. Jangan hapus kolom lama (`teachers.password`, `students.password_plain`) dulu.
3. Tambah kolom audit opsional:
   - `last_login_at`
   - `password_migrated_at`

## Phase C - Implementasi Login Hybrid
1. Login flow baru:
   - Cek `password_hash` jika tersedia.
   - Jika belum ada hash, fallback ke validasi legacy.
2. Jika login legacy sukses:
   - generate hash
   - simpan ke `password_hash`
   - isi `password_migrated_at`
3. Tambahkan logging hasil login (tanpa menyimpan password).

## Phase D - Hardening Session
1. Tambahkan `expires_at` pada session client.
2. Tambahkan idle-timeout.
3. Re-check role/status pada aksi sensitif.

## Phase E - Hardening Import Akun
1. Gunakan tabel staging untuk import massal.
2. Validasi duplikat (`nis`, `email`) sebelum commit ke tabel utama.
3. Hash password saat proses finalisasi.
4. Purge plaintext di staging setelah sukses.

## Phase F - Rollout Bertahap
1. Aktifkan `AUTH_MODE=hybrid` untuk internal (admin/guru inti).
2. Pantau 2-3 hari operasional.
3. Jika stabil, perluas ke semua user.
4. Setelah stabil >= 2 minggu, aktifkan `AUTH_MODE=hardened`.

## Phase G - Cleanup Aman
1. Pastikan >99% user sudah punya `password_hash`.
2. Pastikan tidak ada query login yang membaca plaintext.
3. Baru jadwalkan penghapusan kolom plaintext (di window malam).

## SQL Checklist (Template)
Gunakan sebagai panduan; sesuaikan nama tipe/constraint sesuai kebutuhan.

```sql
-- 1) Additive columns
alter table public.teachers add column if not exists password_hash text;
alter table public.students add column if not exists password_hash text;

alter table public.teachers add column if not exists password_migrated_at timestamptz;
alter table public.students add column if not exists password_migrated_at timestamptz;

-- 2) Integrity support for exam answers upsert
create unique index if not exists uq_student_answers_session_question
on public.student_answers(session_id, question_id);

-- 3) Optional indexes for critical filters
create index if not exists idx_exam_sessions_student_id on public.exam_sessions(student_id);
create index if not exists idx_exam_sessions_schedule_id on public.exam_sessions(schedule_id);
create index if not exists idx_schedules_teacher_id on public.schedules(teacher_id);
create index if not exists idx_schedules_exam_id on public.schedules(exam_id);
create index if not exists idx_schedules_status on public.schedules(status);
```

## Kriteria Sukses
1. Tidak ada gangguan operasional di jam 07.00-16.00 WIB.
2. Login success rate stabil atau membaik.
3. Import akun tetap normal.
4. Plaintext berhenti digunakan untuk autentikasi.

## Trigger Rollback
1. Lonjakan login failure pasca deploy.
2. Import akun gagal pada file normal.
3. Flow inti sekolah tidak bisa dipakai.

## Langkah Rollback
1. Set `AUTH_MODE=legacy`.
2. Redeploy commit stabil terakhir.
3. Validasi login admin, guru, siswa.
4. Tunda migrasi lanjutan sampai RCA selesai.

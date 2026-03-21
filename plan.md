# Audit Arsitektur Exam Jingga

## Ringkasan Masalah
Struktur aplikasi saat ini sudah berjalan, namun belum optimal untuk skalabilitas jangka menengah/panjang. Masalah utama ada pada ketercampuran tanggung jawab (UI, business logic, query data), keamanan autentikasi, dan konsistensi skema database.

## Penilaian Singkat
- Keterbacaan: **6/10**
- Penempatan source: **5/10**
- Scalability: **4/10**

## Temuan Kunci
1. **File monolitik di layer page**
   - Contoh: `src/pages/Schedules.jsx` sangat besar dan memuat UI + query + workflow bisnis sekaligus.
   - Dampak: sulit diuji, sulit dipelihara, rawan regresi saat fitur bertambah.

2. **Struktur source belum berbasis domain/feature**
   - Saat ini dominan page-based.
   - Dampak: logika fitur tersebar dan berulang antar halaman.

3. **Auth & session belum production-grade**
   - Penggunaan password plaintext (`teachers.password`, `students.password_plain`).
   - Session berbasis `localStorage` tanpa penguatan token flow yang aman.
   - Dampak: risiko keamanan tinggi dan sulit memenuhi best practice compliance.

4. **Isu integritas skema database**
   - Nilai default `students.status` terlihat tidak konsisten (`'''aktif'''`).
   - Pola upsert di `student_answers` mengandalkan `(session_id, question_id)`, tetapi skema belum menegaskan unique constraint tersebut.
   - Dampak: potensi data duplikat atau perilaku update tidak deterministik.

5. **Kesiapan build & maintainability**
   - Build berhasil, namun bundle frontend masih besar (~1.2MB JS output).
   - Lint menunjukkan cukup banyak error/warning yang menandakan technical debt aktif.

## Rekomendasi Prioritas
1. **Security & Access Control (Paling prioritas)**
   - Migrasi login ke Supabase Auth yang benar.
   - Hilangkan plaintext password di tabel aplikasi.
   - Terapkan RLS policy per role (`admin`, `kurikulum`, `guru`, `siswa`).

2. **Refactor Arsitektur Frontend**
   - Ubah struktur ke feature/domain-based (contoh: `features/schedules`, `features/exam-session`, `features/master-data`).
   - Pisahkan:
     - UI components
     - Data access layer (services/repositories)
     - Business/use-case logic
   - Targetkan pemecahan file besar menjadi modul kecil yang fokus.

3. **Hardening Database**
   - Rapikan enum/status value dan default value.
   - Tambah unique constraint/index yang mendukung query kritikal:
     - `student_answers(session_id, question_id)` unique
     - index pada kolom join/filter utama (`schedule_id`, `student_id`, `teacher_id`, `exam_id`, `status`).

4. **Performance & Delivery**
   - Lakukan code-splitting berbasis route/feature.
   - Kurangi beban initial bundle.
   - Audit query N+1 dan optimasi select field seperlunya.

## Proposed Approach (Tahapan Implementasi)
1. Stabilkan fondasi keamanan (Auth + RLS + schema constraints).
2. Refactor modul `Schedules` sebagai pilot domain.
3. Terapkan pola arsitektur yang sama ke modul lain.
4. Tutup dengan hardening lint/test/build + optimasi bundle.

## Catatan
Dokumen ini adalah baseline arsitektur untuk pengambilan keputusan refactor berikutnya.

I. FORMAT SEDERHANA (DOKUMENTASI FITUR)

Tujuan Fitur: Digitalisasi ujian sekolah (CBT) dengan sistem real-time monitoring, integrasi nilai otomatis, dan fitur anti-curang (anti-cheat lock system).

Aktor/Role:

Admin/Kurikulum: Manajemen jadwal global, pembuatan token, dan kontrol status sesi siswa.

Guru: Input Bank Soal per mata pelajaran dan analisis hasil ujian (sebaran pengecoh).

Siswa: Mengerjakan ujian dengan batasan waktu dan pengawasan browser activity.

Langkah Alur:

Guru input Bank Soal (questions).

Admin buat paket ujian (exams) & jadwal spesifik per kelas (schedules).

Siswa masuk via token, sistem membuat sesi (exam_sessions).

Jawaban tersimpan otomatis per detik ke student_answers.

Ujian selesai -> Nilai dikalkulasi otomatis & masuk ke tab Analisis Guru.

Kondisi Khusus:

Tab Switching: Peringatan otomatis (UH/PTS) atau penguncian sesi (PAS/PAT).

Auto-Unlock: Radar otomatis mengecek status sesi tiap 3 detik jika sesi terkunci oleh Admin.

Auto-Submit: Jika waktu habis atau sesi terhenti saat terkunci, sistem menghitung nilai berdasarkan jawaban terakhir di DB.

Data/Tabel Terlibat: exams, schedules, questions, exam_questions, exam_sessions, student_answers, teacher_assignments.

Catatan Infra: Menggunakan Supabase Free Tier (Egress 2GB/week, DB 500MB), sehingga optimasi query dan pembersihan log sesi lama dilakukan secara berkala agar tetap dalam kuota.

Status Saat Ini:

Sudah Jadi: Core UI/UX, Anti-cheat logic, Timer, Auto-sync answers, Analisis butir soal.

Belum Jadi: Fitur rekap cetak PDF (masih via Excel) dan sistem bank soal multimedia yang lebih kompleks.

Prioritas: Tinggi (Sedang berjalan untuk musim PTS/PAS).

II. JAWABAN 6 POIN TAMBAHAN (RENCANA IMPLEMENTASI)

Alur Final per Role:

Admin: Dashboard -> Create Schedule -> Monitoring Live -> Close Exam.

Guru: Bank Soal -> Filter Assignments -> Lihat Hasil & Analisis Soal.

Siswa: Login -> Dashboard -> Konfirmasi Token -> Kerja Soal -> Selesai.

Prioritas 2 Minggu Ke Depan:

Optimasi concurrency (mengingat limitasi connection pool pada Free Tier Supabase) agar tetap stabil saat diakses serentak.

Perbaikan akurasi kunci jawaban pada sistem auto-grading (Analisis Butir Soal).

Pengamanan client-side (Anti-Translate & Disable Right Click).

Daftar Pain Point Nyata:

Browser sering auto-translate soal bahasa Inggris (Sudah ditangani via Meta Tag).

Siswa sering keluar tab secara tidak sengaja (Sudah ditangani via sistem Peringatan vs Lock).

Nilai 0 saat auto-submit karena kunci jawaban tidak ter-load (Sudah ditangani via query !inner).

Aturan Bisnis yang Fix:

Satu siswa hanya boleh punya satu sesi aktif per jadwal.

Kunci sesi bersifat mutlak untuk ujian formal (PAS/PAT).

Nilai yang sudah masuk ke exam_sessions tidak bisa diubah oleh siswa.

Batasan Operasional:

Deploy: Di atas jam 16.00 (setelah jam sekolah) untuk menghindari gangguan akses siswa.

Infrastruktur: Berjalan di Supabase Free Tier. Perlu monitoring ketat pada Realtime quota dan Direct Connection limits saat ujian massal (satu angkatan).



Kriteria Sukses:

Zero data loss (100% jawaban tersimpan di database).

Akurasi kalkulasi nilai 100% sesuai kunci jawaban.

Sistem mampu menangani lonjakan traffic hingga 100-200 concurrent users tanpa terkena limit kuota Supabase.
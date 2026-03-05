Pedoman Pengembangan Aplikasi CBT Jingga
📌 Status Terakhir:
Modul Logistik & Settings: ✅ DONE & CLOSED

Master Data (Admin/Kurikulum): ✅ DONE & CLOSED

Bank Soal (Dasar): ✅ DONE & CLOSED

🚀 Rencana Sprint (Roadmap)
[Sprint 1] Sinkronisasi Role & UI Security
Tujuan: Memastikan setiap Role hanya melihat apa yang menjadi haknya.

[ ] Guru: Hapus tautan "Pengaturan Sistem" yang mengarah ke Dashboard Admin.

[ ] Kurikulum: Implementasi Read-Only Mode. Sembunyikan tombol Tambah/Edit/Hapus pada Master Data & Bank Soal.

[ ] Sidebar: Filter menu berdasarkan role_level dari database.

[Sprint 2] Penjadwalan & Lifecycle Ujian (Kunci Utama)
Tujuan: Memperbaiki alur rilis ujian dari Guru ke Admin.

[ ] Pembatasan Tipe:

Guru: Hanya bisa buat jadwal tipe UH.

Admin: Bisa buat jadwal PTS, PAS/PAT, dan SAJ.

[ ] Pembersihan Modul: Hapus fitur cetak kartu di menu Schedules. Ganti dengan ringkasan informasi (Total Peserta dari tabel Logistik, Sesi, Status).

[ ] Workflow Rilis:

Admin buat jadwal kosong.

Guru pilih soal.

Admin verifikasi jadwal.

Ujian berubah status jadi Ready/Live.

[ ] Token System: Token hanya bisa digenerate/aktif setelah verifikasi Admin.

[Sprint 3] Dashboard Agregator (Real-time Info)
Tujuan: Dashboard tidak lagi sekedar UI kosong, tapi pusat data.

[ ] Admin: Total Siswa Aktif, Guru, Bank Soal, & Ujian yang sedang berjalan.

[ ] Guru: Notifikasi jadwal yang belum diisi soal & ringkasan nilai rata-rata kelas.

[ ] Kurikulum/Siswa: Monitoring progres ujian secara real-time.

[Sprint 4] Fitur Anti-Nyontek & Student Exam (Zero-Cheat)
Tujuan: Mengunci kecurangan siswa secara otomatis.

[ ] Anti-Tab Switch: Deteksi siswa pindah tab/minimize browser di PC atau Smartphone.

[ ] Sistem Toleransi (Logika 1x):

Kejadian ke-1: Muncul Peringatan Keras (Warning).

Kejadian ke-2: Status Lock. Layar siswa terkunci (Red Screen).

[ ] Pengecekan Tipe: Fitur Auto-Lock ini Wajib Aktif di tipe PAS/PAT dan SAJ. Untuk UH bersifat fleksibel (bisa hanya peringatan).

[ ] Integrasi Logistik: Siswa hanya bisa mulai ujian jika sudah terdaftar di student_logistics (Ruang & Sesi cocok).

[Sprint 5] Monitoring & Unlock Master
Tujuan: Manajemen saat ujian berlangsung dan pelaporan.

[ ] Monitoring Center: Admin/Kurikulum bisa melihat daftar siswa yang statusnya locked.

[ ] Unlock Feature: Tombol khusus bagi Kurikulum/Admin untuk mengaktifkan kembali sesi siswa yang terkunci.

[ ] Export Hasil: Cetak laporan nilai per kelas dalam format Excel/PDF.

🛠 Aturan Main (Development Rules)
Database First: Setiap penambahan fitur harus dicek kesesuaian kolomnya dengan skema Supabase.

UI Dark Mode: Gunakan utility dark:text-white dan dark:bg-zinc-900 untuk semua komponen baru.

Anti-Cheat Logic: Gunakan exam_sessions.status sebagai penentu layar kunci di sisi siswa.
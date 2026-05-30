# Desain Penyimpanan Waktu WIB Literal

## Ringkas
Sistem akan menyimpan semua waktu sebagai WIB literal (tanpa konversi UTC) agar nilai yang tersimpan sama persis dengan input admin/guru, dan tampilan/jadwal siswa tidak bergeser tanggal.

## Tujuan
- Input jam 08:00 tersimpan sebagai 08:00 di database.
- Penyaringan jadwal siswa akurat untuk WIB.
- Mencegah error jadwal “tidak muncul” akibat perbedaan UTC.

## Non-Tujuan
- Dukungan multi-timezone.
- Penyesuaian waktu otomatis selain WIB.

## Status Saat Ini (Ringkas)
- `datetime-local` di form jadwal menyimpan nilai yang kemudian terbaca sebagai UTC.
- Filter jadwal siswa membandingkan tanggal lokal vs tanggal hasil parsing, yang bisa bergeser.

## Desain

### 1) Skema & Konvensi Waktu
- Semua kolom waktu yang relevan disimpan sebagai `timestamp without time zone`.
- Konvensi aplikasi: setiap nilai waktu dianggap WIB.
- Kolom utama yang terdampak:
  - `schedules.start_time`
  - `schedules.end_time`
  - `exams.start_time` (jika dipakai)
  - `exam_sessions.started_at`
  - `exam_sessions.finished_at`

### 2) Alur Input & Tampilan
- Input `datetime-local` tetap dipakai di form jadwal.
- Nilai input disimpan apa adanya tanpa konversi UTC.
- Tampilan waktu menggunakan util `formatWIB` karena data sudah WIB.

### 3) Filter Jadwal Siswa
- Ganti filter “tanggal sama” menjadi “now berada dalam rentang `start_time`–`end_time`”.
- Semua perbandingan waktu dilakukan dengan asumsi WIB.
- Efek: jadwal ujian yang melewati tengah malam tetap muncul dengan benar.

### 4) Migrasi Data Existing
- Konversi sekali dari data UTC ke WIB literal.
- Contoh:
  - Sebelum: `2026-05-30 21:32:00+00`
  - Sesudah: `2026-05-31 04:32:00`
- Setelah migrasi, data tidak bergeser lagi.

## Risiko & Mitigasi
- Risiko: data lama terlihat berubah tanggal setelah migrasi.
  - Mitigasi: komunikasikan bahwa itu konversi ke WIB literal, bukan perubahan jadwal.
- Risiko: query yang mengasumsikan UTC perlu disesuaikan.
  - Mitigasi: audit query waktu di kode sebelum implementasi.

## Verifikasi
- Buat jadwal jam 08:00 WIB dan pastikan di DB tersimpan 08:00.
- Siswa melihat jadwal pada tanggal yang sama dengan input.
- Ujian yang dimulai sebelum tengah malam dan selesai setelahnya tetap muncul.

## Dampak File (Estimasi)
- `src/features/schedules/components/ScheduleFormModal.jsx`
- `src/pages/StudentDashboard.jsx`
- `src/features/schedules/utils/dateTime.js`
- Migrasi database untuk tipe kolom waktu

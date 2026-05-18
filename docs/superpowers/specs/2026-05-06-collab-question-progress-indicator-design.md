# Collab Question Progress Indicator Design

## Latar Belakang
Pada ujian kolaborasi (PAS/PAT/SAJ), soal disusun oleh beberapa guru dan kuota dibagi per guru. Admin perlu indikator yang jelas untuk melihat progres pengumpulan soal per guru langsung dari halaman Schedules, tanpa masuk detail per jadwal.

Saat ini:
- `my_question_count` sudah dihitung per schedule (jumlah soal yang dibuat guru tersebut).
- `teacher_quota` sudah dibagi saat pembuatan jadwal kolaborasi.
- UI hanya menampilkan progres per guru pada card masing-masing, belum ada daftar semua guru dalam satu exam.

## Tujuan
1. Menampilkan indikator progres pengumpulan soal per guru pada jadwal kolaborasi.
2. Indikator tampil di halaman Schedules (admin), per schedule card.
3. Format informasi jelas: `Nama Guru 30/40`.

## Non-Tujuan
1. Tidak menambah query baru ke Supabase.
2. Tidak mengubah workflow jadwal/soal (hanya indikator UI).
3. Tidak mengubah schema DB.

## Batasan
1. Supabase free tier: harus hemat query.
2. Tidak mengubah UI utama secara besar.
3. Indikator hanya untuk admin.

## Arsitektur Singkat
Data progres dihitung dari data yang sudah ada:
- `exams` di `useSchedulesData` (hasil `mapScheduleCards`).
- `my_question_count` dari `mapScheduleCardItem`.
- `teacher_quota` dari schedule.
Semua progress dikelompokkan per `exam_id` dan disuntikkan ke setiap schedule yang berada pada exam tersebut.

## Data Model (Front-End)
Tambahan field pada setiap item schedule:
```
teacher_progress_list: Array<{
  teacher_id: string,
  name: string,
  filled: number,
  quota: number
}>
```

## Logika Perhitungan
1. Ambil semua schedule hasil `mapScheduleCards`.
2. Group by `exam_id`.
3. Untuk setiap group:
   - Ambil semua schedule dalam exam tersebut.
   - Bangun `teacher_progress_list`:
     - `filled`: `my_question_count` per schedule.
     - `quota`: `teacher_quota` per schedule.
     - `name`: `teachers.full_name`.
4. Set `teacher_progress_list` ke setiap schedule dalam group.

## UI/UX
Lokasi: `Schedules` -> `ScheduleCard` (admin only).

Aturan tampil:
- Jika exam type kolaborasi (`PAS/PAT`, `SAJ`): tampil list semua guru + progress `filled/quota`.
- Jika non-kolaborasi: tampil 1 guru saja (tetap dengan `filled/quota`).
- Indikator tampil saat `status = pending_selection`.

Contoh tampilan:
```
Progres Soal (Kolaborasi)
- Beni 30/40
- Cece 10/40
```

## Error Handling
- Jika data `teacher_quota` null, fallback ke `exams.target_question_count`.
- Jika `teachers.full_name` kosong, fallback ke label `Guru`.

## Testing
Manual smoke check:
1. Admin buka Schedules untuk PAS/PAT/SAJ.
2. Lihat daftar guru dan progres angka tampil.
3. Pastikan non-kolaborasi hanya menampilkan 1 guru.
4. Pastikan indikator tidak muncul untuk status selain `pending_selection`.

## Definition of Done
1. Admin melihat daftar guru + progres `filled/quota` di Schedules untuk PAS/PAT/SAJ.
2. Data dihitung tanpa query tambahan.
3. Non-kolaborasi tampil 1 guru dengan format sama.
4. Tidak ada perubahan workflow/DB.

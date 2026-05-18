# Pilot Refactor Schedules Design

## Latar Belakang
Modul `src/pages/Schedules.jsx` saat ini menampung UI, query Supabase, business rule status, form payload, dan role guard dalam satu file besar. Kondisi ini memperlambat pengembangan, memperbesar risiko bug saat perubahan kecil, dan menyulitkan onboarding developer baru.

Refactor fase pilot difokuskan ke domain jadwal ujian karena domain ini adalah pusat alur inti aplikasi:
- admin menjadwalkan,
- guru memilih soal,
- admin verifikasi,
- siswa mulai ujian.

## Tujuan
1. Memecah tanggung jawab file agar modul jadwal mudah dikembangkan.
2. Menjaga kompatibilitas logic workflow yang sudah berjalan di produksi.
3. Menambah guard role dan guard status agar aksi sensitif lebih aman.
4. Tidak mengubah schema database pada fase pilot.

## Non-Tujuan
1. Tidak melakukan migrasi auth/session global.
2. Tidak mengubah desain UI secara signifikan.
3. Tidak melakukan refactor besar ke modul non-jadwal selain sinkronisasi helper status.

## Batasan Operasional
1. Aplikasi live dipakai jam 07.00-16.00 WIB, jadi perubahan harus low-risk.
2. Deploy/validasi final dilakukan di luar jam aktif.
3. Supabase free tier: query harus tetap hemat dan tidak menambah beban berlebihan.

## Arsitektur yang Dipilih
Pendekatan **vertical slice** pada domain `schedules` dengan pemisahan:

1. `page` - composition UI dan wiring event.
2. `hooks` - orchestration state/effect/action per domain.
3. `services` - semua akses Supabase domain jadwal.
4. `utils` - helper murni (formatter, mapper, payload builder).
5. `constants` - status workflow, policy role, label dan rule transisi.

### Kenapa model ini dipilih
1. Mengurangi coupling antara tampilan dan data source.
2. Memudahkan test helper murni tanpa framework tambahan.
3. Memudahkan rollback per layer bila ada masalah.
4. Pola yang sama bisa direplikasi ke modul lain setelah pilot stabil.

## Desain Struktur File

### File Baru
1. `src/features/schedules/constants/examWorkflow.js`
2. `src/features/schedules/constants/rolePolicies.js`
3. `src/features/schedules/constants/index.js`
4. `src/features/schedules/utils/dateTime.js`
5. `src/features/schedules/utils/scheduleMappers.js`
6. `src/features/schedules/utils/payloadBuilders.js`
7. `src/features/schedules/utils/index.js`
8. `src/features/schedules/services/scheduleService.js`
9. `src/features/schedules/hooks/useSchedulesData.js`
10. `src/features/schedules/hooks/useScheduleActions.js`
11. `src/features/schedules/components/ScheduleFilters.jsx`
12. `src/features/schedules/components/ScheduleCard.jsx`
13. `src/features/schedules/components/ScheduleFormModal.jsx`
14. `src/features/schedules/index.js`

### File yang Diubah
1. `src/pages/Schedules.jsx`
2. `src/pages/SelectQuestions.jsx`
3. `src/pages/StudentDashboard.jsx`

## Desain Workflow Status

### Status yang dipakai
1. `pending_selection`
2. `waiting_validation`
3. `validated`
4. `ready` (kompatibilitas data lama)
5. `live` (kompatibilitas data lama)

### Rule transisi utama
1. Saat soal penuh:
   - `UH` -> `validated`
   - `PTS/PAS/PAT/SAJ` -> `waiting_validation`
2. Admin verifikasi:
   - `waiting_validation` -> `validated`
3. Guru unlock khusus UH:
   - `validated/ready` -> `pending_selection`
4. Siswa boleh mulai hanya jika status ujian siap (`validated/ready/live`) dan jadwal aktif.

## Desain Guard Role

### Aksi per role
1. `admin`
   - Buat/edit jadwal PTS/PAS/PAT/SAJ.
   - Verifikasi ujian.
   - Monitoring peserta/hasil.
2. `guru`
   - Buat/edit jadwal UH.
   - Pilih soal sesuai penugasan.
   - Unlock ulang UH untuk revisi.
3. `kurikulum`
   - Monitoring read-only (fase pilot, tanpa mutasi data).
4. `siswa`
   - Akses ujian siap dan sesuai eligibility.

### Layer guard
1. UI guard: kontrol visibilitas tombol.
2. Action guard: validasi role + validasi transisi sebelum mutate.
3. Query guard: filter data sesuai assignment/teacher_id.

## Data Flow Ringkas
1. Page memanggil `useSchedulesData` untuk load list/filter state.
2. Page memanggil `useScheduleActions` untuk create/edit/verify/unlock.
3. Hook memanggil `scheduleService` untuk query DB.
4. Service return data mentah, lalu util mapper membentuk data siap UI.

## Error Handling
1. Semua action mutate mengembalikan error terstruktur agar bisa ditampilkan konsisten via SweetAlert.
2. Guard failure mengembalikan pesan jelas (`Aksi tidak diizinkan`, `Transisi status tidak valid`, dsb).
3. Fallback: jika fetch gagal, UI tetap render state aman (`[]` + notifikasi).

## Strategi Testing
1. Unit test helper murni:
   - workflow status,
   - formatter datetime,
   - payload builder.
2. Manual smoke test role-based:
   - admin flow,
   - guru flow,
   - siswa readiness.
3. Regression matrix workflow:
   - UH otomatis validated,
   - PTS/PAS/PAT/SAJ menunggu verifikasi,
   - unlock UH kembali pending,
   - token readiness sinkron.

## Rencana Rollout
1. Ekstrak constants + utils dahulu (paling aman).
2. Pindah query ke service.
3. Pindah orchestration ke hooks.
4. Pecah komponen UI.
5. Sinkronisasi helper status lintas halaman.
6. Jalankan verifikasi akhir lint/build/test/manual matrix.

## Risiko dan Mitigasi
1. Risiko: regressi logic status antar halaman.
   - Mitigasi: source of truth tunggal di constants + unit test.
2. Risiko: role bypass karena URL direct.
   - Mitigasi: guard di hook action selain guard UI.
3. Risiko: perubahan terlalu besar untuk sekali rilis.
   - Mitigasi: incremental commit per task dan smoke test per tahap.

## Definisi Selesai (Design Acceptance)
1. `Schedules.jsx` menjadi file tipis (container/composition).
2. Rule status tidak lagi tersebar sebagai string literal acak.
3. Query domain jadwal terpusat di service.
4. Workflow lama tetap berjalan sesuai perilaku produksi saat ini.
5. Pilot siap dijadikan template refactor modul berikutnya.

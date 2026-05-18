# Spec - Pilot Refactor Schedules

Dokumen spec detail berada di:
`docs/superpowers/specs/2026-04-18-pilot-schedules-refactor-design.md`

## Ringkasan
- Fokus fase 1: modul `Schedules` sebagai pilot refactor agar struktur file lebih mudah dikembangkan.
- Strategi: pecah jadi `page + hooks + services + utils + constants` tanpa migration schema DB.
- Workflow dijaga tetap kompatibel:
  - admin menjadwalkan,
  - guru memilih soal,
  - admin verifikasi,
  - ujian bisa dimulai siswa.

## Constraint
- Tidak ada downtime pada jam aktif sekolah.
- Tidak ada perubahan schema DB di fase pilot.
- Kompatibilitas status lama (`ready/live`) tetap dipertahankan.

## Referensi
- Spec lengkap: `docs/superpowers/specs/2026-04-18-pilot-schedules-refactor-design.md`
- Plan implementasi: `plan.md`
- Plan detail mirror: `docs/superpowers/plans/2026-04-18-pilot-schedules-refactor-implementation.md`
- Log progres: `log.md`

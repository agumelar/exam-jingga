# Anti-Cheat Mobile Detection (Web-Only) - Design

Date: 2026-05-18

## Context
Siswa bisa membuka floating menu/overlay di HP tanpa memicu deteksi anti-cheat saat ujian. Logika saat ini hanya mengandalkan `visibilitychange` dan `blur` sehingga beberapa overlay tidak terdeteksi. Batasan: solusi harus gratis dan web-only (tanpa MDM/kiosk berbayar).

## Goals
- Menjaga rule pelanggaran yang sudah ada (PAS/PAT/SAJ: lock >= 2; UH/PTS: warning).
- Menambah sinyal deteksi agar “keluar aplikasi” di HP lebih sering terhitung.
- Perubahan minimal pada UI dan struktur data (tanpa migrasi DB).

## Non-Goals
- Blokir overlay OS-level secara absolut (tidak mungkin dengan web-only).
- Menambah layanan berbayar atau SDK proctoring.

## Approach (Recommended)
Multi-signal detection pada sisi client dengan satu pintu pelaporan pelanggaran, ditambah deteksi “timer drift” untuk menangkap jeda eksekusi saat aplikasi di-background.

### Signals
High confidence:
- `document.visibilitychange` (pasang di `document`, bukan `window`)
- `window.blur`
- `pagehide`
- Timer drift (selisih tick > 3500–4000ms)

Low confidence (opsional, hanya tambahan bukti):
- `document.hasFocus()` polling
- Page lifecycle `freeze`/`resume`
- `fullscreenchange` (jika nanti diaktifkan)

### Violation Rules
- Gunakan satu fungsi `reportViolation(source)`.
- Debounce 2 detik (pakai `lastCheatTime`).
- Increment `violation_count` dan update `exam_sessions` seperti sekarang.
- UH/PTS: warning saja. PAS/PAT/SAJ: lock saat count >= 2.

## Data Flow
1. Event/sinyal terpicu -> `reportViolation(source)`.
2. `reportViolation` cek kondisi guard (session aktif, tidak locked, tidak loading).
3. Update state local `violationCount`, update DB (`exam_sessions`).
4. Jika strict exam dan count >= 2 -> set locked.

## Error Handling & Guards
- Aktif hanya saat `!loading && !isLocked && sessionId && schedule`.
- Timer drift hanya dihitung jika interval berjalan normal sebelumnya (hindari false positive saat tab baru aktif).
- Cooldown mencegah double count dari event beruntun.

## Testing Notes
- Manual di HP: buka overlay/floating menu lalu kembali; cek count naik.
- Uji tab switch di desktop; pastikan count naik.
- Pastikan lock behavior untuk PAS/PAT/SAJ tetap sama.

## Affected File
- `src/pages/ExamInterface.jsx`

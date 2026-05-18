# Exam Session Autosave Optimization Design

## Latar Belakang
Pada ujian massal, beberapa siswa melakukan refresh/reload halaman saat ujian berlangsung. Saat ini, jawaban di UI bisa kembali kosong walaupun waktu tetap berjalan. Hal ini memicu kehilangan jawaban atau ketidaksinkronan antara UI dan database. Selain itu, autosave per klik berpotensi memicu write terlalu sering di Supabase free tier.

## Tujuan
1. Jawaban tetap muncul setelah refresh/reload (rehydrate dari DB dan cache lokal).
2. Autosave tetap aman namun lebih hemat query/write.
3. Tidak mengubah workflow ujian yang sudah stabil (UH/PTS/PAS/PAT/SAJ).
4. Tetap kompatibel dengan Supabase free tier.

## Non-Tujuan
1. Tidak mengubah UI/UX secara besar-besaran.
2. Tidak mengubah alur anti-cheat dan timer inti.
3. Tidak menambah layanan berbayar atau infrastruktur baru.

## Batasan Operasional
1. Supabase free tier: optimasi query dan write frequency wajib.
2. Waktu operasional aktif 07.00-16.00 WIB, deploy dilakukan di luar jam aktif.
3. Tidak mengubah skema tabel selain constraint yang dibutuhkan untuk upsert stabil.

## Arsitektur yang Dipilih
**DB-first + resilient autosave**:
1. Menjadikan database sebagai source of truth untuk jawaban.
2. Menambahkan unique constraint agar upsert idempotent.
3. Menyimpan cache lokal untuk menahan jawaban saat refresh/retry.
4. Menjalankan batch flush terjadwal untuk mengurangi write spam.

## Struktur File

### File Baru
1. `src/features/examSessions/services/answerService.js`
   - `fetchSessionAnswers(sessionId)`
   - `upsertSessionAnswers(sessionId, rows)`
2. `src/features/examSessions/utils/answerCache.js`
   - `readLocal(sessionId)`
   - `writeLocal(sessionId, payload)`
   - `clearLocal(sessionId)`
3. `src/features/examSessions/hooks/useExamAnswerSync.js`
   - load DB + cache, queue changes, batch flush + retry
4. `src/features/examSessions/index.js`

### File yang Diubah
1. `src/pages/ExamInterface.jsx` (integrasi hook autosave baru)

## Perubahan Database

### Unique Constraint (wajib)
Untuk memastikan `upsert` bekerja stabil dan mencegah duplikasi jawaban:

```sql
ALTER TABLE public.student_answers
ADD CONSTRAINT student_answers_session_question_unique
UNIQUE (session_id, question_id);
```

### Index (opsional, tapi direkomendasikan)
Mempercepat rehydrate jawaban per sesi:

```sql
CREATE INDEX IF NOT EXISTS student_answers_session_id_idx
ON public.student_answers (session_id);
```

## Desain Data Cache Lokal
Cache disimpan di `localStorage` dengan key:
`exam_answers_cache:<sessionId>`.

Format cache:
```json
{
  "version": 1,
  "updatedAt": 1710000000000,
  "answers": {
    "<questionId>": {
      "choice": "A",
      "isDoubt": false,
      "updatedAt": 1710000000000
    }
  }
}
```

## Alur Data
1. **Start Exam**
   - Dapatkan `sessionId`.
   - Fetch jawaban dari DB (`student_answers`).
   - Read cache lokal; jika ada, cache override DB untuk questionId yang sama.
   - Set `answers` + `doubtfulQuestions` di UI.

2. **On Answer Change / Toggle Doubt**
   - Update state lokal.
   - Tulis ke cache lokal.
   - Tambahkan ke queue untuk batch flush.

3. **Batch Flush**
   - Trigger interval 1000-1500ms atau saat queue >= 10.
   - Kirim `upsert` batch ke Supabase dengan `onConflict: session_id, question_id`.
   - Jika gagal, simpan queue, retry dengan backoff (1s, 2s, 5s) maksimal 3 kali.

4. **Before Unload / Hidden**
   - Jalankan flush cepat (best-effort) agar perubahan terakhir tersimpan.

5. **Finish Exam**
   - Setelah submit sukses, clear cache lokal untuk sessionId.

## Error Handling
1. Jika fetch jawaban gagal, gunakan cache lokal (jika ada), tampilkan notifikasi ringan.
2. Jika upsert gagal, jangan reset state; simpan ke queue dan retry.
3. Tidak ada perubahan ke flow anti-cheat/lock; autosave berhenti saat `isLocked`.

## Testing Strategy
1. **Unit test** untuk `answerCache` (read/write/clear) dan `queue merge` di hook.
2. **Manual test**:
   - Jawab beberapa soal, refresh, jawaban tetap tampil.
   - Simulasikan offline sebentar (devtools), jawaban tetap tersimpan di cache lalu tersinkron saat online.
   - Pastikan tidak ada duplikasi jawaban di `student_answers`.

## Definisi Selesai
1. Refresh/reload tidak menghapus jawaban di UI.
2. `student_answers` tidak memiliki duplikasi per session/question.
3. Write ke Supabase berkurang (batch), namun jawaban tetap aman.
4. Tidak ada perubahan alur ujian dan anti-cheat.

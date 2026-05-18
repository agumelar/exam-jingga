# Runbook Deploy Malam - Exam Jingga

Dokumen ini adalah SOP deploy produksi untuk aplikasi yang aktif dipakai pada **07.00-16.00 WIB**.

## Tujuan
- Menjaga deploy tetap aman tanpa mengganggu user aktif.
- Menjamin setiap rilis punya jalur rollback cepat.
- Menstandarkan eksekusi tim agar konsisten dan tidak panik saat incident.

## Jadwal Operasional
- Window deploy utama: **22.00-04.00 WIB**
- Validasi akhir: **05.30-06.30 WIB**
- Freeze perubahan produksi: **06.30-16.30 WIB** (kecuali incident kritikal)

## Aturan Emas
1. Satu rilis hanya satu tema perubahan.
2. Tidak ada perubahan schema destruktif saat sistem live.
3. Wajib backup sebelum deploy.
4. Wajib siapkan rollback sebelum mulai deploy.

## Checklist Pra-Deploy (H-0)
1. Pastikan perubahan sudah dites di lokal/staging.
2. Pastikan commit yang akan dirilis sudah final dan review selesai.
3. Catat baseline metrik:
   - login success rate
   - jumlah error login
   - error pada flow jadwal/ujian
4. Konfirmasi feature flag aktif sesuai rencana (mis. `AUTH_MODE`).
5. Siapkan pesan status untuk operator sekolah.

## Eksekusi Deploy (22.00-04.00)
1. **22.00-22.15 - Backup & persiapan**
   - Backup database (snapshot/export).
   - Simpan ID backup dan timestamp di log operasional.
2. **22.15-22.30 - Release**
   - Merge/push perubahan ke branch deploy (`main`).
   - Pantau GitHub Actions hingga build + upload selesai.
3. **22.30-23.00 - Smoke test produksi**
   - Login admin.
   - Login guru.
   - Login siswa.
   - Buka dashboard.
   - Buka jadwal.
   - Akses halaman ujian (tanpa submit real jika tidak perlu).
4. **23.00-00.00 - Monitoring intensif**
   - Pantau error log dan respons operator.
   - Bandingkan metrik terhadap baseline.
5. **00.00-04.00 - Stabilization window**
   - Tidak menambah perubahan baru kecuali fix kritikal.

## Validasi Pagi (05.30-06.30)
1. Jalankan checklist smoke test ulang.
2. Konfirmasi aplikasi siap dipakai sebelum 07.00 WIB.
3. Kirim status ke stakeholder: `AMAN` atau `ROLLBACK`.

## Kriteria Rollback Wajib
Lakukan rollback jika salah satu terjadi:
1. Login gagal meningkat signifikan dari baseline.
2. Import akun gagal untuk skenario normal.
3. Flow inti tidak bisa diakses (dashboard, jadwal, ujian).

## Prosedur Rollback Cepat
1. Ubah feature flag ke mode aman (contoh: `AUTH_MODE=legacy`).
2. Redeploy commit stabil terakhir.
3. Validasi ulang flow login dan jadwal.
4. Umumkan status rollback + dampak ke operator.
5. Catat akar masalah untuk perbaikan rilis berikutnya.

## Template Laporan Singkat (Setiap Rilis)
Gunakan format ini setelah deploy:

```text
[Exam Jingga - Deploy Report]
Tanggal/Jam: YYYY-MM-DD HH:mm WIB
Versi/Commit: <hash>
Tema Rilis: <judul singkat>
Backup ID: <id backup>
Hasil Build: SUCCESS/FAILED
Smoke Test: PASS/FAIL
Status Akhir: AMAN/ROLLBACK
Catatan: <ringkas>
```

## Catatan Praktis
- Jika rilis menyentuh auth, prioritaskan canary internal (admin/guru inti) dulu.
- Hindari perubahan besar beruntun dalam satu malam.
- Simpan semua log eksekusi agar transfer knowledge ke tim lebih cepat.

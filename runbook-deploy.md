# Runbook Deploy & Operasional - Exam Jingga

Aplikasi aktif dipakai pada **07.00-16.00 WIB**. Server: VPS Ubuntu 24.04 ARM64 `145.241.157.243` (SSH alias `openclaw-server`), aplikasi di `/opt/exam-jingga`, database PostgreSQL 17 di container `supabase-db`.

## Jadwal Operasional
- Window deploy utama: **22.00-04.00 WIB**
- Validasi akhir: **05.30-06.30 WIB**
- Freeze perubahan produksi: **06.30-16.30 WIB** (kecuali incident kritikal)

## Aturan Emas
1. Satu rilis hanya satu tema perubahan.
2. Tidak ada perubahan schema destruktif saat sistem live.
3. Wajib backup sebelum deploy (skrip deploy melakukannya otomatis).
4. Wajib siapkan rollback sebelum mulai deploy.

## Checklist Pra-Deploy
1. Perubahan lulus `pytest` dan `npm run build` di lokal.
2. Commit final sudah di-push ke `main`.
3. Test juga lulus di PostgreSQL: `bash scripts/test_postgres_vps.sh` (container PostgreSQL sementara di VPS, terhapus otomatis). Wajib bila perubahan menyentuh query, penguncian baris, atau migrasi; test lokal memakai SQLite yang mengabaikan `SELECT ... FOR UPDATE`.
4. Catat baseline: jumlah error login, error pada flow jadwal/ujian (`journalctl -u exam_jingga.service`).
5. Siapkan pesan status untuk operator sekolah.

## Eksekusi Deploy (22.00-04.00)
1. **Release + backup**: dari komputer lokal jalankan

   ```bash
   bash scripts/deploy_vps_dath.sh
   ```

   Skrip menjalankan di server: `git merge --ff-only origin/main`, `pip install -r requirements.txt`, **backup database pra-migrasi**, `check --deploy`, `migrate`, `createcachetable`, build CSS, `collectstatic`, memasang unit systemd (aplikasi, penilai otomatis, backup) dan konfigurasi Nginx, restart, health check. Catat nama berkas backup pra-migrasi yang dicetak skrip.
2. **Smoke test produksi**: login admin/kurikulum, login guru, login siswa (SSO), dashboard, jadwal, halaman ujian (tanpa submit real bila tidak perlu).
3. **Monitoring intensif** satu jam pertama, lalu stabilization window tanpa perubahan baru kecuali fix kritikal.

## Validasi Pagi (05.30-06.30)
1. Ulangi smoke test.
2. Konfirmasi siap dipakai sebelum 07.00 WIB.
3. Kirim status ke stakeholder: `AMAN` atau `ROLLBACK`.

## Kriteria Rollback Wajib
1. Login gagal meningkat signifikan dari baseline.
2. Flow inti tidak bisa diakses (dashboard, jadwal, ujian).
3. Error 500 berulang pada endpoint ujian siswa.

## Prosedur Rollback Cepat
1. Deploy commit stabil terakhir: `bash scripts/deploy_vps_dath.sh <commit-stabil>` (tanpa migrasi baru, skrip hanya maju ke commit tersebut bila riwayatnya linear; bila perlu mundur, di server jalankan `git reset --hard <commit-stabil>` lalu `RUN_ON_VPS=1 bash scripts/deploy_vps_dath.sh <commit-stabil>`).
2. Bila migrasi rilis merusak data, pulihkan dari backup pra-migrasi (lihat Restore).
3. Validasi ulang flow login, jadwal, dan ujian.
4. Umumkan status rollback + dampak ke operator, catat akar masalah.

## Template Laporan Singkat (Setiap Rilis)

```text
[Exam Jingga - Deploy Report]
Tanggal/Jam: YYYY-MM-DD HH:mm WIB
Versi/Commit: <hash>
Tema Rilis: <judul singkat>
Backup ID: <nama berkas backup pra-migrasi>
Hasil Build: SUCCESS/FAILED
Smoke Test: PASS/FAIL
Status Akhir: AMAN/ROLLBACK
Catatan: <ringkas>
```

## Rahasia (`/opt/exam-jingga/.env`, mode 600)

| Variabel | Keterangan |
|---|---|
| `DJANGO_SETTINGS_MODULE` | Wajib di server: `config.settings.production`. `manage.py` membacanya dari `.env`; tanpa ini perintah `manage.py` jatuh ke settings development (sqlite), bukan database produksi. |
| `SECRET_KEY` | Wajib. Aplikasi menolak start bila kosong. |
| `WEBHOOK_SECRET_KEY` | Wajib. Kunci header `x-api-key` dari panel Data Admin. |
| `DB_*` | Koneksi PostgreSQL. |
| `DATA_MASTER_CLIENT_ID` | Client Keycloak confidential khusus sinkron data pusat, bawaan `exam-jingga-sync`. Client login `exam-jingga` bertipe public dan tidak bisa dipakai untuk sinkron. |
| `DATA_MASTER_CLIENT_SECRET` | Wajib untuk tombol Tarik Data Master. Tanpa ini sinkron menampilkan "Gagal sinkronisasi" dan tidak mengubah data. Setelah diubah: `sudo systemctl restart exam_jingga.service`. |
| `RCLONE_REMOTE` | Opsional. Tujuan salinan backup di Google Drive, contoh `gdrive-sekolah:exam-jingga-backup`. |

Rahasia tidak boleh ditulis di repo atau dokumen.

## Backup
- Harian 01.30 WIB (`exam_jingga_backup.timer`) dan otomatis sebelum setiap migrasi.
- Lokasi: `/opt/exam-jingga-backups/` (database `*.dump` format custom, media `*.tar.gz`), disimpan 14 hari.
- Manual: `bash /opt/exam-jingga/scripts/backup_db.sh manual`.
- `legacy-dev-db-20261007.sqlite3`: database sqlite development lama yang dulu tertinggal di folder aplikasi. Tidak dipakai produksi; namanya sengaja tidak diawali `exam-jingga-` agar tidak terhapus retensi 14 hari.

### Arsip dan hapus permanen paket ujian
- Paket yang semua jadwalnya sudah lewat bisa diarsipkan dari kartu jadwal (admin/kurikulum semua jenis, guru UH miliknya). Paket arsip hanya tampil di filter Arsip; nilainya tetap di Hasil Ujian dan bisa dikembalikan.
- Hapus permanen hanya admin, hanya untuk paket yang sudah diarsipkan: satu paket dengan mengetik ulang nama paket, atau beberapa paket sekaligus dari filter Arsip dengan mengetik `HAPUS PERMANEN`. Aplikasi lebih dulu menyimpan rekap Excel dan menjalankan `backup_db.sh hapus-<paket> --arsip`; bila backup gagal, tidak ada yang dihapus. Catatan penghapusan ada di tabel `exam_purge_logs`.
- File ada di `/opt/exam-jingga-backups/arsip-hapus/` dan disalin ke `<RCLONE_REMOTE>/arsip-hapus`. Folder ini tidak ikut dibersihkan otomatis (14 hari di server, 60 hari di Drive hanya berlaku untuk `database/` dan `media/`). Nilai wajib disimpan satu tahun pelajaran; hapus file arsip secara manual setelah itu.
- Memulihkan satu paket: restore dump arsip ke database sementara, lalu ambil baris paketnya; rekap Excel bisa langsung dibuka tanpa restore.

### Mengaktifkan salinan ke Google Drive sekolah (sekali saja)
1. Di VPS: `rclone config`, buat remote bertipe `drive` (misal `gdrive-sekolah`) dengan akun Google Drive sekolah. VPS tidak punya browser: jawab *Use auto config? n*, lalu jalankan `rclone authorize "drive"` di komputer yang punya browser dan tempel token yang dihasilkan.
2. Tambahkan ke `.env`: `RCLONE_REMOTE=gdrive-sekolah:exam-jingga-backup`.
3. Uji: `bash /opt/exam-jingga/scripts/backup_db.sh manual`, lalu periksa folder di Drive. Salinan di Drive disimpan 60 hari.

### Restore

```bash
sudo systemctl stop exam_jingga.service exam_jingga_grader.timer
set -a; . /opt/exam-jingga/.env; set +a
docker exec -i -e PGPASSWORD="$DB_PASSWORD" supabase-db \
  pg_restore -h 127.0.0.1 -U "$DB_USER" -d "$DB_NAME" --clean --if-exists -n public < /opt/exam-jingga-backups/<berkas>.dump
tar -xzf /opt/exam-jingga-backups/<berkas-media>.tar.gz -C /opt/exam-jingga   # bila media perlu dipulihkan
sudo systemctl start exam_jingga.service exam_jingga_grader.timer
```

## Layanan Terjadwal

| Unit | Fungsi |
|---|---|
| `exam_jingga.service` | Gunicorn (port 8005) |
| `exam_jingga_grader.timer` | Tiap 2 menit menilai sesi ujian yang waktunya habis |
| `exam_jingga_backup.timer` | Backup harian 01.30 WIB |

Cek: `systemctl list-timers | grep exam_jingga`, `journalctl -u exam_jingga.service -n 50`.

## Login Darurat
Bila SSO tidak bisa diakses, superuser masuk di `/accounts/darurat/` (5 percobaan gagal per 15 menit, plus rate limit Nginx). Akun lain tidak punya kata sandi lokal.

## Catatan Praktis
- Jika rilis menyentuh auth, uji dulu dengan akun admin/guru inti.
- Hindari perubahan besar beruntun dalam satu malam.
- Simpan log eksekusi agar transfer knowledge ke tim lebih cepat.

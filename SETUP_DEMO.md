# Panduan Setup Demo Application Exam Jingga

## 📋 Overview
Aplikasi demo ini telah berhasil dibuat dengan fitur login berbasis role. Pengguna dapat langsung login dengan mengklik tombol role yang tersedia tanpa perlu memasukkan kredensial.

## ✨ Fitur Demo Login

### Quick Login Buttons
Demo aplikasi menyediakan 4 tombol role untuk login cepat:

1. **🔧 ADMINISTRATOR** - Login sebagai Admin dengan akses penuh
2. **📚 KURIKULUM** - Login sebagai Kurikulum Officer
3. **👨‍🏫 GURU** - Login sebagai Teacher/Guru
4. **🎓 SISWA** - Login sebagai Student

### Manual Login
Jika ingin login dengan kredensial spesifik, klik tombol "atau login manual" di bagian bawah halaman quick login.

## 🚀 Cara Deploy Demo ke Shared Hosting

### Step 1: Setup Domain/Subdomain
1. Login ke cPanel shared hosting Anda
2. Buat subdomain baru: `demo.exam.smkn1rongga.sch.id`
3. Atau gunakan domain terpisah untuk demo
4. Catat path direktori subdomain (biasanya: `/public_html/demo.exam.smkn1rongga.sch.id/`)

### Step 2: Setup GitHub Secrets
Tambahkan secrets berikut di GitHub Repository Settings → Secrets and variables → Actions:

**Untuk Demo Deployment:**
- `DEMO_FTP_SERVER` = FTP server hosting (contoh: `ftp.namahostinganda.com`)
- `DEMO_FTP_USERNAME` = Username FTP untuk demo subdomain
- `DEMO_FTP_PASSWORD` = Password FTP untuk demo subdomain

**Environment Variables (jika belum ada):**
- `VITE_SUPABASE_URL` = URL Supabase project Anda
- `VITE_SUPABASE_ANON_KEY` = Anon key dari Supabase project

### Step 3: Setup GitHub Actions Workflow
File workflow sudah dibuat di `.github/workflows/deploy-demo.yml`

Workflow ini akan otomatis deploy saat:
- Push ke branch `demo`, atau
- Push ke branch `claude/create-demo-app-with-role-login`

### Step 4: Deploy Manual (Opsional)
Jika ingin deploy manual tanpa GitHub Actions:

```bash
# 1. Clone repository
git clone https://github.com/agumelar/exam-jingga.git
cd exam-jingga

# 2. Checkout branch demo
git checkout claude/create-demo-app-with-role-login

# 3. Install dependencies
npm install

# 4. Build aplikasi
npm run build

# 5. Upload folder dist/ ke hosting
# Upload semua isi folder dist/ ke:
# /public_html/demo.exam.smkn1rongga.sch.id/
```

**Upload via FTP Client:**
- FileZilla
- WinSCP
- CyberDuck

atau gunakan **File Manager** di cPanel.

### Step 5: Test Demo Application
1. Akses URL demo: `https://demo.exam.smkn1rongga.sch.id/demo`
2. Klik salah satu tombol role untuk login cepat
3. Sistem akan otomatis login dan redirect ke dashboard sesuai role

## 📝 Konfigurasi Database

### Persyaratan Minimal
Untuk demo berfungsi dengan baik, pastikan database Supabase memiliki:

1. **Tabel `teachers`** dengan minimal:
   - 1 record dengan `role_level = 'admin'`
   - 1 record dengan `role_level = 'kurikulum'`
   - 1 record dengan `role_level = 'guru'`

2. **Tabel `students`** dengan minimal:
   - 1 record dengan `status = 'aktif'`

### Contoh Data Demo (SQL)
Jika belum ada data, jalankan query berikut di Supabase SQL Editor:

```sql
-- Insert demo teachers
INSERT INTO teachers (full_name, email, password, role_level)
VALUES
  ('Admin Demo', 'admin@demo.com', 'demo123', 'admin'),
  ('Kurikulum Demo', 'kurikulum@demo.com', 'demo123', 'kurikulum'),
  ('Guru Demo', 'guru@demo.com', 'demo123', 'guru')
ON CONFLICT DO NOTHING;

-- Insert demo student (pastikan class_id sudah ada)
INSERT INTO students (nis, full_name, class_id, password_plain, status)
VALUES
  ('123456', 'Siswa Demo', 1, 'demo123', 'aktif')
ON CONFLICT DO NOTHING;
```

## 🎯 Cara Menggunakan Demo

### Akses Demo
1. **URL Demo:** `https://demo.exam.smkn1rongga.sch.id/demo`
2. **URL Login Manual:** `https://demo.exam.smkn1rongga.sch.id/login`

### Quick Login
1. Buka halaman demo
2. Pilih role yang ingin dicoba (Admin/Kurikulum/Guru/Siswa)
3. Klik tombol role
4. Sistem akan otomatis login dengan user demo pertama yang ditemukan

### Auto Redirect
Aplikasi akan otomatis redirect ke demo login jika:
- Diakses dari subdomain yang mengandung `demo.`
- URL mengandung parameter `?demo=true`
- Path diakses `/demo`

## 🔒 Keamanan

### ⚠️ Peringatan Penting
Demo mode ini hanya cocok untuk **demonstrasi/presentasi**. Untuk production yang aman:

1. ✅ **Database Terpisah** - Gunakan Supabase project terpisah untuk demo
2. ✅ **Read-Only Mode** - Implementasikan mode read-only untuk mencegah perubahan data
3. ✅ **Rate Limiting** - Tambahkan rate limiting untuk mencegah abuse
4. ✅ **Session Timeout** - Set session timeout lebih pendek (5-10 menit)
5. ✅ **IP Restriction** - Batasi akses hanya dari IP tertentu jika perlu
6. ⛔ **Jangan di Production** - Jangan expose demo login di environment production utama

### Rekomendasi
- Gunakan domain/subdomain terpisah untuk demo
- Gunakan database Supabase project terpisah
- Set environment variables berbeda untuk demo
- Monitoring akses demo untuk mendeteksi abuse

## 📂 File Structure

```
exam-jingga/
├── src/
│   ├── pages/
│   │   ├── Login.jsx              # Login page original
│   │   └── DemoLogin.jsx          # NEW: Demo login page
│   └── App.jsx                    # Updated: Added demo route
├── .github/
│   └── workflows/
│       ├── deploy.yml             # Deploy production
│       └── deploy-demo.yml        # NEW: Deploy demo
└── DEMO_README.md                 # NEW: Documentation
```

## 🛠️ Troubleshooting

### Demo Login Tidak Muncul Data
**Problem:** Klik tombol role tapi muncul error "Tidak ada data ... demo yang tersedia!"

**Solution:**
- Pastikan database memiliki user dengan role tersebut
- Jalankan query SQL di atas untuk insert data demo
- Check koneksi Supabase (VITE_SUPABASE_URL dan VITE_SUPABASE_ANON_KEY)

### Redirect Loop
**Problem:** Halaman terus redirect tanpa henti

**Solution:**
- Clear browser cache dan cookies
- Clear localStorage: Buka DevTools → Application → Local Storage → Clear All
- Periksa logic redirect di App.jsx line 40-46

### FTP Deploy Gagal
**Problem:** GitHub Actions workflow gagal saat deploy

**Solution:**
- Periksa FTP credentials di GitHub Secrets
- Test koneksi FTP manual dengan FileZilla
- Pastikan direktori target di server sudah ada
- Periksa permission direktori (755 untuk folder, 644 untuk file)

### Build Gagal
**Problem:** npm run build error

**Solution:**
```bash
# Clear cache dan reinstall
rm -rf node_modules package-lock.json
npm install
npm run build
```

### Domain Tidak Bisa Diakses
**Problem:** `demo.exam.smkn1rongga.sch.id` tidak bisa diakses

**Solution:**
- Tunggu DNS propagation (1-24 jam)
- Check subdomain di cPanel
- Pastikan file `.htaccess` ada dan berisi redirect ke index.html
- Test dengan IP address langsung

## 📚 Resources

### Files Terkait
- **Demo Login Component:** `src/pages/DemoLogin.jsx`
- **Main App Router:** `src/App.jsx`
- **Deploy Workflow:** `.github/workflows/deploy-demo.yml`
- **Documentation:** `DEMO_README.md`

### GitHub Repository
- **Repo:** https://github.com/agumelar/exam-jingga
- **Branch Demo:** `claude/create-demo-app-with-role-login`

### Supabase
- **Dashboard:** https://app.supabase.com
- **Documentation:** https://supabase.com/docs

## 🎨 Customization

### Mengubah Warna Button
Edit file `src/pages/DemoLogin.jsx`:

```jsx
// Admin (Orange) - line 122
className="... from-orange-600 to-orange-700 ..."

// Kurikulum (Blue) - line 136
className="... from-blue-600 to-blue-700 ..."

// Guru (Green) - line 150
className="... from-green-600 to-green-700 ..."

// Siswa (Purple) - line 164
className="... from-purple-600 to-purple-700 ..."
```

### Mengubah Domain Demo
Edit file `.github/workflows/deploy-demo.yml`:

```yaml
server-dir: ./public_html/DOMAIN_ANDA_DISINI/
```

### Menonaktifkan Auto Redirect
Edit file `src/App.jsx` dan comment baris 40-46:

```jsx
// Comment untuk disable auto redirect
/*
const isDemoDomain = window.location.hostname.includes('demo.') ||
                     window.location.pathname === '/demo' ||
                     window.location.search.includes('demo=true');

if (isDemoDomain && !user && window.location.pathname === '/login') {
  window.location.href = '/demo';
}
*/
```

## 🚀 Next Steps

### Opsi 1: Deploy Otomatis (Recommended)
1. Push code ke branch `demo` atau `claude/create-demo-app-with-role-login`
2. GitHub Actions akan otomatis build & deploy
3. Tunggu 1-2 menit sampai selesai
4. Akses URL demo

### Opsi 2: Deploy Manual
1. Build aplikasi: `npm run build`
2. Upload folder `dist/` ke hosting via FTP
3. Akses URL demo

### Opsi 3: Merge ke Main
1. Merge branch `claude/create-demo-app-with-role-login` ke `main`
2. Demo akan tersedia di aplikasi production
3. Akses via path `/demo`

## 📞 Support
Untuk pertanyaan atau masalah terkait demo:
1. Buka issue di GitHub repository
2. Contact: admin@smkn1rongga.sch.id

---

**Last Updated:** 2026-03-19
**Version:** 1.0.0
**Author:** Claude Code Assistant

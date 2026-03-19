# Demo Application - Quick Start Guide

## 🎉 Selamat! Demo Application Sudah Siap

Demo aplikasi dengan fitur login berbasis role telah berhasil dibuat!

## 🚀 Cara Menggunakan

### Akses Demo Lokal
```bash
npm install
npm run dev
# Akses: http://localhost:5173/demo
```

### Akses Demo Production
**URL:** `https://demo.exam.smkn1rongga.sch.id/demo`

atau tambahkan parameter `?demo=true` ke URL login normal:
`https://exam.smkn1rongga.sch.id/login?demo=true`

## 🎯 Fitur Quick Login

### 4 Tombol Login Role:

1. **🔧 ADMINISTRATOR** (Orange)
   - Full system access
   - Manage master data, teachers, students
   - Create and manage exams

2. **📚 KURIKULUM** (Blue)
   - View master data (read-only)
   - Monitor exam schedules
   - Dashboard access

3. **👨‍🏫 GURU** (Green)
   - Create questions
   - Manage personal exam schedules
   - Select questions for exams

4. **🎓 SISWA** (Purple)
   - View available exams
   - Take exams
   - View results

## 📝 Catatan Penting

### Database Requirements
Pastikan database memiliki minimal:
- 1 teacher dengan `role_level = 'admin'`
- 1 teacher dengan `role_level = 'kurikulum'`
- 1 teacher dengan `role_level = 'guru'`
- 1 student dengan `status = 'aktif'`

Jika belum ada, jalankan query SQL di `SETUP_DEMO.md` bagian "Contoh Data Demo"

### Environment Variables
Pastikan sudah set di GitHub Secrets:
- `VITE_SUPABASE_URL`
- `VITE_SUPABASE_ANON_KEY`
- `DEMO_FTP_SERVER`
- `DEMO_FTP_USERNAME`
- `DEMO_FTP_PASSWORD`

## 📂 File yang Dibuat

```
✅ src/pages/DemoLogin.jsx           # Demo login page dengan quick login buttons
✅ .github/workflows/deploy-demo.yml # GitHub Actions untuk auto-deploy demo
✅ DEMO_README.md                    # Dokumentasi lengkap demo
✅ SETUP_DEMO.md                     # Panduan setup dan troubleshooting
✅ QUICKSTART.md                     # Guide ini
✅ public/.htaccess                  # Routing untuk shared hosting
✅ src/App.jsx                       # Updated dengan route /demo
✅ vite.config.js                    # Updated untuk copy .htaccess
```

## 🔄 Auto Deploy

Workflow GitHub Actions akan otomatis deploy saat:
- Push ke branch `demo`
- Push ke branch `claude/create-demo-app-with-role-login`

**Target Deploy:** `./public_html/demo.exam.smkn1rongga.sch.id/`

## 📱 Demo Features

### Quick Login
- Click tombol role → otomatis login → redirect ke dashboard

### Manual Login
- Click "atau login manual" → form login normal

### Auto Redirect
Auto redirect ke `/demo` jika:
- Domain mengandung `demo.`
- URL path = `/demo`
- URL parameter `?demo=true`

## ⚡ Testing

```bash
# Build test
npm run build

# Check build output
ls -la dist/

# Local dev
npm run dev
```

## 🎨 Customization

Lihat `SETUP_DEMO.md` untuk:
- Mengubah warna button
- Mengubah domain demo
- Menonaktifkan auto redirect
- Custom styling

## 🔒 Security Warning

⚠️ Demo mode tidak direkomendasikan untuk production!

Untuk production yang aman:
- Gunakan database terpisah
- Implementasi read-only mode
- Add rate limiting
- Set session timeout pendek

Lihat `SETUP_DEMO.md` bagian "Keamanan" untuk detail.

## 📚 Documentation

- **Lengkap:** `SETUP_DEMO.md`
- **Overview:** `DEMO_README.md`
- **Quick:** `QUICKSTART.md` (ini)

## 💡 Tips

1. Test demo dengan semua 4 role
2. Periksa database memiliki data untuk semua role
3. Set up GitHub Secrets sebelum push
4. Monitor first deployment di GitHub Actions
5. Test URL demo setelah deploy selesai

## 🆘 Troubleshooting

Lihat `SETUP_DEMO.md` bagian "Troubleshooting" untuk:
- Demo login tidak muncul data
- Redirect loop
- FTP deploy gagal
- Build gagal
- Domain tidak bisa diakses

## ✅ Next Steps

1. **Test Lokal:**
   ```bash
   npm run dev
   # Visit: http://localhost:5173/demo
   ```

2. **Setup GitHub Secrets:**
   - Tambahkan secrets di GitHub
   - Lihat list di atas

3. **Push ke GitHub:**
   ```bash
   git push origin claude/create-demo-app-with-role-login
   ```

4. **Monitor Deploy:**
   - Check GitHub Actions tab
   - Tunggu sampai selesai (1-2 menit)

5. **Test Production:**
   - Akses URL demo
   - Test semua 4 role
   - Verifikasi redirect ke dashboard

## 🎊 Selesai!

Demo aplikasi siap digunakan untuk:
- Presentasi ke klien
- Demo ke stakeholder
- Testing fitur
- Training user

---

**Butuh bantuan?** Lihat dokumentasi lengkap di `SETUP_DEMO.md`

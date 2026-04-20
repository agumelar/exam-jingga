# 🎯 STANDALONE DEMO - EXAM JINGGA

## ✨ DEMO TANPA DATABASE

Demo aplikasi ini **SEPENUHNYA TERPISAH** dari aplikasi utama dan **TIDAK MEMERLUKAN DATABASE** sama sekali.

## 🎉 Fitur Utama

### ✅ Completely Standalone
- ❌ **TIDAK** terhubung ke Supabase
- ❌ **TIDAK** memerlukan database
- ❌ **TIDAK** mempengaruhi aplikasi utama
- ✅ **100%** menggunakan mock data
- ✅ Build terpisah (demo.html)
- ✅ Codebase terpisah (DemoApp.jsx)

### 🔧 Karakteristik
- **Ukuran:** Demo JS hanya ~22KB (vs Main App 904KB)
- **Dependencies:** Minimal - hanya React, React Router, SweetAlert2, Lucide Icons
- **Data:** Mock data hardcoded di `src/demoData.js`
- **Login:** Quick login tanpa kredensial
- **Dashboard:** Simulasi data untuk semua role

## 📂 File Structure

```
exam-jingga/
├── src/
│   ├── demoData.js                    # ✨ NEW: Mock data
│   ├── DemoApp.jsx                    # ✨ NEW: Demo app (terpisah)
│   ├── main-demo.jsx                  # ✨ NEW: Demo entry point
│   └── pages/
│       ├── StandaloneDemoLogin.jsx    # ✨ NEW: Demo login
│       └── DemoDashboard.jsx          # ✨ NEW: Demo dashboard
├── demo.html                          # ✨ NEW: Demo HTML
├── index.html                         # Main app HTML
└── vite.config.js                     # Multi-entry build
```

## 🚀 Deployment

### Build Commands
```bash
# Build semua (main + demo)
npm run build

# Dev demo
npm run dev:demo

# Preview demo
npm run preview:demo
```

### Output
```
dist/
├── index.html              # Main app
├── demo.html               # ✨ Demo standalone
├── assets/
│   ├── main-*.js          # Main app bundle (904KB)
│   ├── demo-*.js          # ✨ Demo bundle (22KB)
│   └── ...
└── .htaccess
```

### GitHub Actions
Workflow di `.github/workflows/deploy-demo.yml`:
- **Trigger:** Push ke branch `demo` atau `claude/create-demo-app-with-role-login`
- **Build:** `npm run build` (termasuk demo)
- **Deploy:** Upload ke `./public_html/demo.exam.smkn1rongga.sch.id/`
- **⚡ NO DATABASE SECRETS REQUIRED!**

## 🔐 GitHub Secrets (Minimal!)

Hanya perlu FTP credentials:
```
DEMO_FTP_SERVER      # FTP server
DEMO_FTP_USERNAME    # FTP username
DEMO_FTP_PASSWORD    # FTP password
```

**TIDAK PERLU:**
- ❌ `VITE_SUPABASE_URL`
- ❌ `VITE_SUPABASE_ANON_KEY`

## 🌐 URLs

### Production
- **Main App:** `https://exam.smkn1rongga.sch.id/`
- **Demo:** `https://demo.exam.smkn1rongga.sch.id/demo.html`

### Local Development
```bash
# Install
npm install

# Run demo
npm run dev:demo

# Akses: http://localhost:5173/demo.html
```

## 🎮 Cara Menggunakan Demo

### 1. Akses Demo
Buka: `https://demo.exam.smkn1rongga.sch.id/demo.html`

### 2. Quick Login
Pilih salah satu role:
- 🔧 **ADMINISTRATOR** - Full system access
- 📚 **KURIKULUM** - Monitoring access
- 👨‍🏫 **GURU** - Teacher features
- 🎓 **SISWA** - Student exam interface

### 3. Explore
- Dashboard dengan data simulasi
- Statistik dummy
- UI/UX sesuai aplikasi asli
- Semua data adalah mock/hardcoded

## 📊 Mock Data

File: `src/demoData.js`

### Users
```javascript
mockUsers = {
  admin: { fullName: 'Administrator Demo', ... },
  kurikulum: { fullName: 'Kurikulum Demo', ... },
  guru: { fullName: 'Guru Demo', ... },
  siswa: { fullName: 'Siswa Demo', nis: '123456789', ... }
}
```

### Dashboard Data
- **Admin:** Total siswa, guru, soal, ujian aktif
- **Kurikulum:** Jadwal, ujian aktif/selesai/mendatang
- **Guru:** Soal saya, jadwal, tugas pending
- **Siswa:** Ujian tersedia, selesai, nilai

### Other Mock Data
- Exams
- Questions
- Students (5 records)
- Teachers (4 records)
- Classes (5 records)
- Subjects (6 records)

## 🔒 Security & Isolation

### Completely Isolated
1. **Separate Build**
   - Demo: `demo.html` + `demo-*.js`
   - Main: `index.html` + `main-*.js`

2. **No Database Access**
   - Demo tidak import `supabaseClient.js`
   - Tidak ada API calls
   - Semua data di memory

3. **Separate Session**
   - Demo session memiliki flag `isDemoMode: true`
   - DemoApp hanya terima session dengan flag ini
   - Main App TIDAK terima demo session

4. **No Cross-Contamination**
   - Demo tidak bisa akses data production
   - Main app tidak terpengaruh demo
   - Database aman dari demo users

## ✅ Kelebihan

### 1. **Zero Database Dependency**
- Tidak perlu Supabase
- Tidak perlu koneksi internet (setelah load)
- Tidak ada database setup

### 2. **Fast & Lightweight**
- Demo bundle hanya 22KB
- Load time sangat cepat
- Minimal dependencies

### 3. **Safe for Production**
- Tidak ada risiko data corruption
- Tidak ada akses ke database production
- Isolasi sempurna

### 4. **Easy Deployment**
- Upload file static
- Tidak perlu environment variables (kecuali FTP)
- Works di shared hosting biasa

### 5. **Perfect for Demos**
- Presentasi ke klien
- Testing UI/UX
- Training users
- Marketing material

## 📝 Customization

### Update Mock Data
Edit `src/demoData.js`:
```javascript
export const mockUsers = {
  admin: {
    fullName: 'Your Name',  // ← Edit here
    email: 'your@email.com' // ← Edit here
  }
}
```

### Add More Mock Data
```javascript
export const mockNewData = [
  { id: 1, ... },
  { id: 2, ... }
];
```

### Update Dashboard Stats
```javascript
export const mockDashboardData = {
  admin: {
    totalStudents: 1000,  // ← Change numbers
    totalTeachers: 50,
    ...
  }
}
```

## 🔧 Technical Details

### Build Configuration
**vite.config.js:**
```javascript
build: {
  rollupOptions: {
    input: {
      main: resolve(__dirname, 'index.html'),
      demo: resolve(__dirname, 'demo.html')  // ← Demo entry
    }
  }
}
```

### Entry Points
- **Main:** `src/main.jsx` → `App.jsx` → Full application
- **Demo:** `src/main-demo.jsx` → `DemoApp.jsx` → Demo only

### Demo App Router
```javascript
<Routes>
  <Route path="/" element={<StandaloneDemoLogin />} />
  <Route path="/dashboard" element={<DemoDashboard />} />
  <Route path="*" element={<Navigate to="/" />} />
</Routes>
```

Simple! Hanya 2 pages.

## 🚨 Troubleshooting

### Demo tidak muncul data
**Problem:** Dashboard kosong

**Solution:**
- Mock data sudah hardcoded di `src/demoData.js`
- Tidak perlu database
- Refresh page

### Build error
**Problem:** `npm run build` error

**Solution:**
```bash
rm -rf node_modules package-lock.json
npm install
npm run build
```

### Demo mengarah ke main app
**Problem:** Redirect ke aplikasi utama

**Solution:**
- Pastikan akses `demo.html` bukan `index.html`
- URL: `/demo.html` atau `/demo.html#/`

## 📊 Size Comparison

| File | Size | Description |
|------|------|-------------|
| `demo-*.js` | ~22KB | Demo bundle (lightweight!) |
| `main-*.js` | ~904KB | Main app bundle (full features) |
| **Difference** | **97% lighter!** | Demo 41x lebih kecil |

## 🎯 Use Cases

### ✅ Cocok untuk:
1. Presentasi ke stakeholder
2. Demo ke calon client
3. Testing UI/UX tanpa data real
4. Training users baru
5. Marketing material
6. Portfolio showcase

### ❌ Tidak cocok untuk:
1. Production usage
2. Real data testing
3. Performance testing
4. Integration testing
5. Database-related features

## 🔄 Updates

### Update Demo
1. Edit mock data di `src/demoData.js`
2. Update UI di `src/pages/DemoDashboard.jsx`
3. Build: `npm run build`
4. Deploy: Push ke GitHub (auto-deploy)

### Sync dengan Main App
Demo UI otomatis sync dengan main app karena:
- Same Tailwind config
- Same component structure
- Same design system

Hanya data yang berbeda (mock vs database).

## 📞 Support

**Questions?**
- Check `DEMO_README.md` untuk overview
- Check `SETUP_DEMO.md` untuk setup details
- Open issue di GitHub

## 🎊 Summary

**Demo Standalone Exam Jingga:**
- ✅ 100% terpisah dari aplikasi utama
- ✅ Tidak perlu database
- ✅ Tidak perlu Supabase
- ✅ Mock data hardcoded
- ✅ Build terpisah
- ✅ Deploy terpisah
- ✅ Aman untuk production
- ✅ Lightweight (22KB!)
- ✅ Perfect untuk demonstrasi

**Aplikasi utama TIDAK terpengaruh sama sekali!** 🎉

---

**Version:** 2.0.0 (Standalone)
**Last Updated:** 2026-03-19
**Author:** Claude Code Assistant

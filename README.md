# Exam Jingga - Sistem CBT SMKN 1 Rongga

Aplikasi Computer-Based Test (CBT) berbasis web untuk SMKN 1 Rongga. Dibangun dengan React + Vite dan Supabase sebagai backend.

## 🎯 Fitur Utama

- ✅ **Multi-Role System** - Admin, Kurikulum, Guru, Siswa
- ✅ **Bank Soal** - Kelola soal dengan mudah
- ✅ **Ujian Online** - Interface ujian yang user-friendly
- ✅ **Auto Grading** - Penilaian otomatis untuk soal pilihan ganda
- ✅ **Jadwal Ujian** - Kelola jadwal ujian dengan fleksibel
- ✅ **Dashboard** - Dashboard berbeda untuk setiap role
- ✅ **Dark Mode** - Tema gelap untuk kenyamanan mata
- ✅ **Responsive** - Bekerja di desktop, tablet, dan mobile

## 🚀 Quick Start

### Prerequisites

- Node.js 18+ atau 22+ (LTS recommended)
- npm atau yarn
- Akun Supabase (gratis di https://supabase.com)

### Installation

```bash
# Clone repository
git clone https://github.com/agumelar/exam-jingga.git
cd exam-jingga

# Install dependencies
npm install

# Setup environment variables
cp .env.example .env
# Edit .env dengan Supabase credentials Anda

# Run development server
npm run dev
```

Aplikasi akan berjalan di http://localhost:5173

### Environment Variables

Buat file `.env` di root project:

```bash
VITE_SUPABASE_URL=https://your-project-id.supabase.co
VITE_SUPABASE_ANON_KEY=your-anon-key-here
```

Lihat [ENV_CONFIG.md](ENV_CONFIG.md) untuk panduan lengkap konfigurasi environment variables.

## 📦 Build

```bash
# Build untuk production
npm run build

# Preview production build
npm run preview
```

Hasil build akan tersimpan di folder `dist/`.

## 🌐 Deployment

Aplikasi ini dapat di-deploy ke berbagai platform:

### 1. Shared Hosting (cPanel/FTP)

Deployment otomatis via GitHub Actions ke shared hosting:

- **Main App:** `exam.smkn1rongga.sch.id`
- **Demo App:** `demo.exam.smkn1rongga.sch.id`

Lihat [SETUP_DEMO.md](SETUP_DEMO.md) untuk panduan lengkap.

### 2. VPS (Virtual Private Server) ⭐ **RECOMMENDED**

Deploy ke VPS dengan domain custom Anda sendiri:

- Full control atas server
- Better performance
- Custom domain support
- SSL/HTTPS dengan Let's Encrypt

📘 **[Baca Panduan VPS Deployment](DEPLOY_VPS.md)**

File bantuan untuk VPS:
- `nginx.conf.example` - Nginx config untuk main app
- `nginx-demo.conf.example` - Nginx config untuk demo app

### 3. Platform Cloud

- **Vercel** - Import dari GitHub, auto-deploy
- **Netlify** - Drag & drop atau Git integration
- **Cloudflare Pages** - Edge network deployment
- **GitHub Pages** - Static hosting gratis

## 📚 Dokumentasi

### Setup & Deployment
- [DEPLOY_VPS.md](DEPLOY_VPS.md) - 🆕 Panduan deploy ke VPS dengan domain custom
- [ENV_CONFIG.md](ENV_CONFIG.md) - 🆕 Konfigurasi environment variables
- [SETUP_DEMO.md](SETUP_DEMO.md) - Setup aplikasi demo
- [QUICKSTART.md](QUICKSTART.md) - Quick start guide

### Demo Application
- [STANDALONE_DEMO.md](STANDALONE_DEMO.md) - Standalone demo app (no database)
- [DEMO_VS_MAIN.md](DEMO_VS_MAIN.md) - Perbandingan demo vs main app
- [DEMO_README.md](DEMO_README.md) - Demo app overview

### Development
- [development.md](development.md) - Development roadmap

## 🎮 Demo

**Live Demo:** https://demo.exam.smkn1rongga.sch.id/demo

Demo dengan quick login (tanpa database):
- 🔧 **Administrator** - Akses penuh sistem
- 📚 **Kurikulum** - Kelola soal dan jadwal ujian
- 👨‍🏫 **Guru** - Buat dan kelola ujian
- 🎓 **Siswa** - Ikut ujian

## 🛠️ Tech Stack

- **Frontend:** React 18 + Vite
- **Styling:** Tailwind CSS
- **Routing:** React Router v6
- **State Management:** React Context + Hooks
- **Backend:** Supabase (PostgreSQL)
- **Authentication:** Supabase Auth
- **Deployment:** GitHub Actions + FTP / VPS + Nginx

## 📁 Project Structure

```
exam-jingga/
├── src/
│   ├── pages/           # Page components
│   ├── components/      # Reusable components
│   ├── supabaseClient.js
│   ├── App.jsx
│   ├── main.jsx         # Main app entry
│   └── main-demo.jsx    # Demo app entry
├── public/              # Static assets
├── dist/                # Build output
├── .github/
│   └── workflows/       # GitHub Actions
├── nginx.conf.example   # Nginx config template
├── DEPLOY_VPS.md        # VPS deployment guide
└── ENV_CONFIG.md        # Environment config guide
```

## 🔒 Security

- ✅ Row Level Security (RLS) enabled di Supabase
- ✅ HTTPS enforced (SSL/TLS)
- ✅ Environment variables untuk secrets
- ✅ Input sanitization
- ✅ XSS protection
- ✅ CSRF protection

## 📝 Scripts

```bash
npm run dev              # Start development server
npm run dev:demo         # Start demo development server
npm run build            # Build untuk production (main + demo)
npm run build:demo       # Build demo saja
npm run preview          # Preview production build
npm run preview:demo     # Preview demo build
```

## 🤝 Contributing

1. Fork repository
2. Create feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to branch (`git push origin feature/AmazingFeature`)
5. Open Pull Request

## 📞 Support

- **Email:** admin@smkn1rongga.sch.id
- **GitHub Issues:** https://github.com/agumelar/exam-jingga/issues

## 📄 License

This project is licensed under the MIT License.

---

## 🚀 Getting Started dengan VPS

Jika Anda ingin deploy ke VPS dengan domain sendiri:

1. **Siapkan VPS** - Ubuntu 20.04/22.04 dengan minimal 1GB RAM
2. **Beli Domain** - Atau gunakan subdomain yang sudah ada
3. **Ikuti Panduan** - Baca [DEPLOY_VPS.md](DEPLOY_VPS.md) untuk step-by-step
4. **Konfigurasi DNS** - Point domain ke IP VPS
5. **Deploy** - Clone, build, dan setup Nginx
6. **SSL** - Install SSL certificate dengan Let's Encrypt

Total waktu setup: **30-60 menit** untuk yang sudah familiar dengan Linux.

**Need help?** Open an issue atau kontak email di atas.

---

**Made with ❤️ by SMKN 1 Rongga**

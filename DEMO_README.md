# Demo Application - Exam Jingga

## Overview
Aplikasi demo ini adalah versi demonstrasi dari Exam Jingga yang dilengkapi dengan login berbasis role. Pengguna dapat langsung login dengan mengklik tombol role yang tersedia tanpa perlu memasukkan kredensial.

## Demo Access
URL Demo: `https://demo.exam.smkn1rongga.sch.id/demo`

## Quick Login Features
Demo aplikasi ini menyediakan 4 role untuk login cepat:

### 1. Administrator
- **Role**: Admin
- **Access**: Full system access
- **Features**:
  - Master Data Management
  - Teacher & Student Management
  - Question Bank
  - Exam Schedules
  - System Settings

### 2. Kurikulum (Curriculum Officer)
- **Role**: Kurikulum
- **Access**: Read/Monitor + Limited Edit
- **Features**:
  - View Master Data
  - View Question Bank
  - View Exam Schedules
  - Dashboard monitoring

### 3. Guru (Teacher)
- **Role**: Guru
- **Access**: Subject-specific content management
- **Features**:
  - Create questions
  - Manage exam schedules
  - Select questions for exams
  - View personal dashboard

### 4. Siswa (Student)
- **Role**: Siswa
- **Access**: Exam participant
- **Features**:
  - View available exams
  - Take exams
  - View exam results
  - Access logistics information

## How It Works
1. Kunjungi URL demo: `https://demo.exam.smkn1rongga.sch.id/demo`
2. Pilih role yang ingin Anda coba dengan mengklik tombol yang sesuai
3. Sistem akan otomatis login menggunakan akun demo pertama yang ditemukan untuk role tersebut
4. Anda akan diarahkan ke dashboard sesuai dengan role yang dipilih

## Manual Login Option
Jika Anda ingin login dengan kredensial tertentu, klik tombol "atau login manual" di bagian bawah halaman quick login.

## Technical Implementation

### Demo Login Page
- **File**: `src/pages/DemoLogin.jsx`
- **Route**: `/demo`
- **Features**:
  - Quick role-based login buttons
  - Manual login fallback
  - Dark mode support
  - Beautiful UI with gradient buttons

### Deployment
Demo aplikasi ini di-deploy ke domain terpisah menggunakan GitHub Actions:
- **Workflow**: `.github/workflows/deploy-demo.yml`
- **Trigger**: Push to `demo` or `claude/create-demo-app-with-role-login` branch
- **Target**: `demo.exam.smkn1rongga.sch.id`

## Database Requirements
Untuk demo berfungsi dengan baik, pastikan database memiliki:
1. Minimal 1 teacher dengan `role_level = 'admin'`
2. Minimal 1 teacher dengan `role_level = 'kurikulum'`
3. Minimal 1 teacher dengan `role_level = 'guru'`
4. Minimal 1 student dengan `status = 'aktif'`

## Environment Variables
Demo menggunakan environment variables yang sama dengan aplikasi utama:
- `VITE_SUPABASE_URL`: Supabase project URL
- `VITE_SUPABASE_ANON_KEY`: Supabase anonymous key

## Deployment Setup

### GitHub Secrets Required
Untuk deploy demo aplikasi, tambahkan secrets berikut di GitHub repository:
- `DEMO_FTP_SERVER`: FTP server untuk demo site
- `DEMO_FTP_USERNAME`: FTP username untuk demo site
- `DEMO_FTP_PASSWORD`: FTP password untuk demo site
- `VITE_SUPABASE_URL`: Supabase URL (sama dengan production)
- `VITE_SUPABASE_ANON_KEY`: Supabase anon key (sama dengan production)

### Manual Deployment
Untuk deploy manual:
```bash
# Build aplikasi
npm run build

# Deploy menggunakan FTP client ke:
# Server: demo.exam.smkn1rongga.sch.id
# Directory: ./public_html/demo.exam.smkn1rongga.sch.id/
```

## Development
Untuk menjalankan demo aplikasi di local:

```bash
# Install dependencies
npm install

# Run development server
npm run dev

# Akses demo page di:
# http://localhost:5173/demo
```

## Notes
- Demo aplikasi menggunakan database yang sama dengan aplikasi production
- Data yang dibuat dalam demo mode akan tersimpan di database production
- Untuk demo yang aman, pertimbangkan menggunakan database terpisah atau mode read-only
- Quick login akan mengambil user pertama yang ditemukan untuk role tersebut

## Security Considerations
⚠️ **PENTING**: Demo mode ini hanya cocok untuk demonstrasi/presentasi. Untuk production:
1. Pertimbangkan menggunakan database terpisah untuk demo
2. Implementasikan rate limiting untuk mencegah abuse
3. Tambahkan session timeout yang lebih pendek
4. Pertimbangkan mode read-only untuk demo data
5. Jangan expose demo login di production environment

## Support
Untuk pertanyaan atau issues terkait demo aplikasi, silakan buka issue di repository GitHub.

# Panduan Konfigurasi Environment Variables

## 📋 Overview
File ini menjelaskan cara mengatur environment variables untuk berbagai skenario deployment:
- Shared Hosting (FTP)
- VPS dengan domain custom
- Local development
- GitHub Actions CI/CD

## 🔑 Environment Variables yang Dibutuhkan

### 1. Supabase Configuration

```bash
VITE_SUPABASE_URL=https://your-project-id.supabase.co
VITE_SUPABASE_ANON_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

**Cara mendapatkan:**
1. Login ke https://app.supabase.com
2. Pilih project Anda
3. Settings → API
4. Copy **Project URL** dan **anon/public key**

---

## 🖥️ Setup untuk Development (Local)

### Metode 1: File .env (Recommended)

Buat file `.env` di root project:

```bash
# .env
VITE_SUPABASE_URL=https://your-project-id.supabase.co
VITE_SUPABASE_ANON_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

**PENTING:** File `.env` sudah ada di `.gitignore` - jangan commit file ini ke Git!

### Metode 2: Export di Terminal

```bash
# Linux/Mac
export VITE_SUPABASE_URL=https://your-project-id.supabase.co
export VITE_SUPABASE_ANON_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...

# Windows Command Prompt
set VITE_SUPABASE_URL=https://your-project-id.supabase.co
set VITE_SUPABASE_ANON_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...

# Windows PowerShell
$env:VITE_SUPABASE_URL="https://your-project-id.supabase.co"
$env:VITE_SUPABASE_ANON_KEY="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
```

### Jalankan Development Server

```bash
# Dengan .env file (otomatis loaded oleh Vite)
npm run dev

# Atau dengan inline env vars
VITE_SUPABASE_URL=https://xxx.supabase.co VITE_SUPABASE_ANON_KEY=xxx npm run dev
```

Akses aplikasi di: http://localhost:5173

---

## 🚀 Setup untuk VPS Deployment

### Metode 1: Environment Variables di Build Time

```bash
# SSH ke VPS
ssh user@your-vps-ip

# Navigate ke directory project
cd /var/www/exam-jingga

# Build dengan inline env vars
VITE_SUPABASE_URL=https://your-project-id.supabase.co \
VITE_SUPABASE_ANON_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9... \
npm run build
```

### Metode 2: File .env.production (Recommended)

Buat file `.env.production` di VPS:

```bash
# Buat file
nano /var/www/exam-jingga/.env.production
```

Isi dengan:

```bash
VITE_SUPABASE_URL=https://your-project-id.supabase.co
VITE_SUPABASE_ANON_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

Secure file permissions:

```bash
chmod 600 /var/www/exam-jingga/.env.production
chown root:root /var/www/exam-jingga/.env.production
```

Build dengan .env.production:

```bash
cd /var/www/exam-jingga

# Vite otomatis load .env.production saat build
npm run build -- --mode production
```

### Metode 3: Shell Script dengan Source

Buat script deploy:

```bash
# Buat script
nano /root/deploy-exam-jingga.sh
```

Isi dengan:

```bash
#!/bin/bash
set -e

# Load environment variables
source /var/www/exam-jingga/.env.production

# Navigate to project
cd /var/www/exam-jingga

# Pull latest code
git pull origin main

# Install dependencies
npm install

# Build with env vars
npm run build

echo "Deployment completed at $(date)"
```

Jalankan script:

```bash
chmod +x /root/deploy-exam-jingga.sh
/root/deploy-exam-jingga.sh
```

---

## 🔐 Setup untuk GitHub Actions (CI/CD)

### Step 1: Tambahkan GitHub Secrets

1. Buka repository di GitHub
2. Settings → Secrets and variables → Actions
3. Klik "New repository secret"
4. Tambahkan secrets berikut:

**Untuk Main App:**
- `VITE_SUPABASE_URL`
- `VITE_SUPABASE_ANON_KEY`
- `FTP_SERVER`
- `FTP_USERNAME`
- `FTP_PASSWORD`

**Untuk Demo App (jika terpisah):**
- `DEMO_FTP_SERVER`
- `DEMO_FTP_USERNAME`
- `DEMO_FTP_PASSWORD`

### Step 2: Gunakan di Workflow

File `.github/workflows/deploy.yml` sudah dikonfigurasi:

```yaml
- name: Build Project
  env:
    VITE_SUPABASE_URL: ${{ secrets.VITE_SUPABASE_URL }}
    VITE_SUPABASE_ANON_KEY: ${{ secrets.VITE_SUPABASE_ANON_KEY }}
  run: npm run build
```

Secrets akan otomatis di-inject saat build.

---

## 🌍 Multiple Environment (Dev, Staging, Production)

### Structure File .env

```
.env                    # Default (loaded di development)
.env.local             # Local overrides (git ignored)
.env.development       # Development environment
.env.staging           # Staging environment
.env.production        # Production environment
```

### Contoh .env.development

```bash
# .env.development
VITE_SUPABASE_URL=https://dev-project.supabase.co
VITE_SUPABASE_ANON_KEY=dev_anon_key_here
```

### Contoh .env.staging

```bash
# .env.staging
VITE_SUPABASE_URL=https://staging-project.supabase.co
VITE_SUPABASE_ANON_KEY=staging_anon_key_here
```

### Contoh .env.production

```bash
# .env.production
VITE_SUPABASE_URL=https://prod-project.supabase.co
VITE_SUPABASE_ANON_KEY=prod_anon_key_here
```

### Build untuk Environment Tertentu

```bash
# Development (default)
npm run dev

# Build untuk staging
npm run build -- --mode staging

# Build untuk production
npm run build -- --mode production
```

---

## 🔍 Verifikasi Environment Variables

### Check di Build Output

Setelah build, check file JavaScript yang di-generate:

```bash
# Search untuk Supabase URL di build files
grep -r "supabase" dist/assets/*.js

# Output akan menunjukkan URL yang ter-embed
```

**PENTING:** Jangan expose secrets di output! VITE hanya embed variables yang prefix `VITE_`. Variables lain (tanpa prefix) tidak akan ter-embed.

### Check di Runtime (Browser Console)

```javascript
// Buka browser DevTools Console
console.log(import.meta.env.VITE_SUPABASE_URL)
console.log(import.meta.env.MODE)
console.log(import.meta.env.PROD)
console.log(import.meta.env.DEV)
```

---

## ⚠️ Security Best Practices

### 1. Jangan Commit Secrets ke Git

File yang harus di-ignore (sudah di `.gitignore`):

```gitignore
.env
.env.local
.env.*.local
.env.production
```

### 2. Use Different Keys untuk Environment Berbeda

```
Development → Dev Supabase Project
Staging     → Staging Supabase Project
Production  → Production Supabase Project
```

Jangan gunakan production keys di development!

### 3. Rotate Keys Secara Berkala

1. Generate new anon key di Supabase
2. Update di semua environment
3. Deploy ulang aplikasi
4. Revoke old key

### 4. Monitor Usage

Check Supabase dashboard untuk API usage:
- Request count
- Error rate
- Rate limiting hits

### 5. Enable RLS (Row Level Security)

Pastikan RLS enabled di semua tabel Supabase:

```sql
-- Enable RLS
ALTER TABLE teachers ENABLE ROW LEVEL SECURITY;
ALTER TABLE students ENABLE ROW LEVEL SECURITY;

-- Create policies
CREATE POLICY "Users can read own data" ON teachers
    FOR SELECT USING (auth.uid() = id);
```

---

## 🧪 Testing Environment Variables

### Test Script

Buat file `test-env.js`:

```javascript
// test-env.js
console.log('=== Environment Variables Test ===')
console.log('SUPABASE_URL:', import.meta.env.VITE_SUPABASE_URL)
console.log('MODE:', import.meta.env.MODE)
console.log('PROD:', import.meta.env.PROD)
console.log('DEV:', import.meta.env.DEV)
console.log('==================================')
```

Jalankan:

```bash
# Development
npm run dev
# Buka browser console, check output

# Production build
npm run build
# Check dist/assets/*.js untuk embedded values
```

---

## 📝 Template .env

Copy template ini untuk setup baru:

```bash
# ==============================================
# Exam Jingga - Environment Configuration
# ==============================================
#
# INSTRUCTIONS:
# 1. Copy this file to .env (for development)
#    or .env.production (for production)
# 2. Fill in your actual values
# 3. NEVER commit this file to Git
#
# ==============================================

# Supabase Configuration
# Get from: https://app.supabase.com → Your Project → Settings → API
VITE_SUPABASE_URL=https://your-project-id.supabase.co
VITE_SUPABASE_ANON_KEY=your-anon-key-here

# Example:
# VITE_SUPABASE_URL=https://xyzabc123def.supabase.co
# VITE_SUPABASE_ANON_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Inh5emFiYzEyM2RlZiIsInJvbGUiOiJhbm9uIiwiaWF0IjoxNjAwMDAwMDAwLCJleHAiOjE5MTU1MjAwMDB9.xxxxxxxxxxxxxxxxxxxxxx

# ==============================================
# Optional: Custom Configuration
# ==============================================

# App URL (untuk redirects, webhooks, etc)
# VITE_APP_URL=https://yourdomain.com

# API Timeout (milliseconds)
# VITE_API_TIMEOUT=30000

# Debug Mode
# VITE_DEBUG=false
```

Save template ini sebagai `.env.example` di root project.

---

## 🔄 Migration dari Shared Hosting ke VPS

Jika Anda pindah dari shared hosting ke VPS:

### 1. Export Current Config

Di shared hosting, check environment variables yang digunakan.

### 2. Setup di VPS

```bash
# SSH ke VPS
ssh user@vps-ip

# Clone project
cd /var/www
git clone https://github.com/agumelar/exam-jingga.git
cd exam-jingga

# Buat .env.production dengan values dari shared hosting
nano .env.production
```

### 3. Test Build

```bash
npm install
npm run build

# Check jika build berhasil
ls -la dist/
```

### 4. Update DNS

Point domain dari shared hosting IP ke VPS IP:

```
Type: A
Name: @
Value: VPS_IP_ADDRESS
```

### 5. Verify

Tunggu DNS propagation (1-24 jam), lalu test:

```bash
curl -I https://yourdomain.com
```

---

## 📚 Resources

- **Vite Env Vars:** https://vitejs.dev/guide/env-and-mode.html
- **Supabase API Keys:** https://supabase.com/docs/guides/api
- **GitHub Secrets:** https://docs.github.com/en/actions/security-guides/encrypted-secrets

---

**Last Updated:** 2026-03-20
**Version:** 1.0.0

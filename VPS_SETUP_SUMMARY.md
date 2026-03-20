# Jawaban untuk Pertanyaan VPS dengan Domain Custom

## ❓ Pertanyaan Anda
> "kalau saya menggunakan vps bagaimana?"
> "domainnya adanya di vps"

## ✅ Solusi Lengkap Telah Dibuat

Saya telah membuat dokumentasi lengkap untuk deploy aplikasi Exam Jingga ke VPS dengan domain custom Anda sendiri.

---

## 📚 File-File yang Dibuat

### 1. **DEPLOY_VPS.md** (771 baris)
Panduan lengkap deploy ke VPS meliputi:

✅ **Setup VPS dari Awal**
- Install Ubuntu/Debian
- Install Node.js, Nginx, Git
- Setup firewall (UFW)
- Setup Fail2Ban untuk security

✅ **Deploy Aplikasi**
- Clone repository
- Build aplikasi dengan environment variables
- Konfigurasi Nginx untuk serve static files
- Setup multiple domains (main + demo)

✅ **SSL/HTTPS**
- Install SSL certificate dengan Let's Encrypt (gratis)
- Auto-renewal certificate
- HTTPS enforcement

✅ **DNS Configuration**
- Setup A records untuk domain
- Setup subdomain untuk demo
- DNS propagation check

✅ **Auto-Deploy**
- Script untuk update otomatis
- GitHub webhook integration (opsional)
- PM2 untuk process management

✅ **Monitoring & Maintenance**
- View logs
- Server resource monitoring
- Log rotation
- Update procedures

✅ **Security Best Practices**
- Firewall configuration
- SSH hardening
- Environment variables security
- Fail2Ban setup

✅ **Troubleshooting**
- Common issues dan solusinya
- Debug procedures
- Fix permission errors

✅ **VPS Provider Recommendations**
- Indonesia: Niagahoster, Dewaweb, IDCloudHost
- International: DigitalOcean, Linode, Vultr, Hetzner

### 2. **nginx.conf.example**
Template konfigurasi Nginx untuk main application:
- Gzip compression
- Browser caching
- SPA routing (React Router support)
- Security headers
- SSL-ready configuration

### 3. **nginx-demo.conf.example**
Template konfigurasi Nginx untuk demo application:
- Separate subdomain support (demo.yourdomain.com)
- Optimized untuk demo app
- Separate logs

### 4. **ENV_CONFIG.md** (466 baris)
Panduan lengkap environment variables:

✅ **Setup untuk Development**
- File .env local
- Export di terminal
- Testing environment variables

✅ **Setup untuk VPS**
- .env.production file
- Build-time environment injection
- Shell scripts untuk deploy

✅ **Setup untuk GitHub Actions**
- GitHub Secrets configuration
- CI/CD workflow integration

✅ **Multiple Environments**
- Development, Staging, Production
- Environment-specific builds
- Configuration management

✅ **Security**
- Secrets management
- Key rotation
- RLS (Row Level Security)

### 5. **README.md** (Updated)
README yang lebih lengkap dengan:
- Project overview
- Quick start guide
- **VPS deployment section** dengan link ke DEPLOY_VPS.md
- Documentation index
- Tech stack
- Contributing guide

---

## 🚀 Cara Menggunakan

### Step 1: Baca Dokumentasi VPS
```bash
# Buka file ini untuk panduan lengkap
DEPLOY_VPS.md
```

### Step 2: Setup Environment Variables
```bash
# Baca panduan konfigurasi env vars
ENV_CONFIG.md
```

### Step 3: Copy Nginx Configuration
```bash
# Copy template Nginx untuk main app
nginx.conf.example

# Copy template Nginx untuk demo app (opsional)
nginx-demo.conf.example
```

### Step 4: Deploy ke VPS
Ikuti step-by-step di DEPLOY_VPS.md:

1. **Siapkan VPS** (Ubuntu 20.04/22.04, min 1GB RAM)
2. **Install Dependencies** (Node.js, Nginx, Git)
3. **Clone & Build Aplikasi**
4. **Setup Nginx** dengan template yang disediakan
5. **Konfigurasi DNS** - Point domain ke IP VPS
6. **Install SSL** dengan Let's Encrypt (gratis)
7. **Test & Monitor**

**Estimasi waktu:** 30-60 menit untuk yang sudah familiar dengan Linux

---

## 🎯 Fitur-Fitur yang Didukung

✅ **Custom Domain Apapun**
- yourdomain.com
- subdomain.yourdomain.com
- demo.yourdomain.com
- Bisa multi-domain dalam 1 VPS

✅ **SSL/HTTPS Gratis**
- Let's Encrypt certificate
- Auto-renewal setiap 90 hari
- Grade A SSL configuration

✅ **Performance Optimization**
- Gzip compression
- Browser caching
- Static asset optimization
- CDN support (via Cloudflare)

✅ **Auto-Deploy**
- Git pull + build script
- GitHub webhook integration
- Zero-downtime deployment

✅ **Security**
- Firewall (UFW)
- Fail2Ban anti brute-force
- SSH key authentication
- Environment variables encryption

✅ **Monitoring**
- Nginx access logs
- Error logs
- Server resource monitoring
- Uptime monitoring

---

## 💡 Contoh Konfigurasi

### Contoh 1: Domain Utama
```
Domain: myschool.com
VPS IP: 123.45.67.89

DNS A Record:
- @ → 123.45.67.89
- www → 123.45.67.89

Hasil:
✅ https://myschool.com
✅ https://www.myschool.com
```

### Contoh 2: Domain + Subdomain Demo
```
Domain: myschool.com
Subdomain: demo.myschool.com
VPS IP: 123.45.67.89

DNS A Records:
- @ → 123.45.67.89
- www → 123.45.67.89
- demo → 123.45.67.89

Hasil:
✅ https://myschool.com (Main App)
✅ https://demo.myschool.com (Demo App)
```

### Contoh 3: Multiple Domains dalam 1 VPS
```
Domain 1: school-a.com
Domain 2: school-b.com
VPS IP: 123.45.67.89

Buat 2 Nginx config files:
- /etc/nginx/sites-available/school-a
- /etc/nginx/sites-available/school-b

Hasil:
✅ https://school-a.com
✅ https://school-b.com
(Semua di 1 VPS yang sama!)
```

---

## 🆚 Perbandingan: Shared Hosting vs VPS

| Aspek | Shared Hosting | VPS dengan Domain Custom |
|-------|---------------|--------------------------|
| **Domain** | Subdomain hosting | Domain apapun yang Anda punya |
| **Control** | Terbatas (cPanel) | Full root access |
| **Performance** | Shared resources | Dedicated resources |
| **SSL** | Auto via cPanel | Let's Encrypt (gratis) |
| **Cost** | $2-5/bulan | $5-10/bulan |
| **Setup** | Mudah (FTP) | Perlu knowledge Linux |
| **Scalability** | Sulit | Mudah upgrade |
| **Flexibility** | Terbatas | Unlimited |

---

## 📋 Checklist Deploy VPS

Copy checklist ini untuk deploy:

```
VPS Setup:
- [ ] VPS sudah ready (Ubuntu/Debian)
- [ ] SSH access sudah bisa login
- [ ] Domain sudah dibeli/ready
- [ ] DNS A record sudah diarahkan ke IP VPS

Software Installation:
- [ ] Nginx sudah terinstall
- [ ] Node.js 22+ sudah terinstall
- [ ] Git sudah terinstall
- [ ] UFW firewall sudah dikonfigurasi

Application Deployment:
- [ ] Repository sudah di-clone
- [ ] Dependencies sudah di-install (npm install)
- [ ] Environment variables sudah di-set
- [ ] Build berhasil (npm run build)

Nginx Configuration:
- [ ] Nginx config sudah dibuat (copy dari template)
- [ ] Config sudah aktif (symbolic link)
- [ ] nginx -t passed
- [ ] Nginx sudah di-reload

SSL & Security:
- [ ] SSL certificate sudah terinstall (certbot)
- [ ] HTTPS redirect sudah aktif
- [ ] Firewall rules sudah benar (UFW)
- [ ] Fail2Ban sudah aktif

Testing:
- [ ] Aplikasi bisa diakses via HTTPS
- [ ] Demo app juga bisa diakses (jika ada)
- [ ] SSL certificate valid (green padlock)
- [ ] Logs tidak ada error

Optional:
- [ ] Auto-update script sudah dibuat
- [ ] Monitoring sudah di-setup
- [ ] Backup system sudah diatur
- [ ] Cloudflare CDN sudah dikonfigurasi
```

---

## 🎓 Tutorial Singkat (TL;DR)

Jika Anda sudah familiar dengan VPS:

```bash
# 1. Setup VPS
apt update && apt upgrade -y
apt install nginx nodejs npm git -y

# 2. Clone & Build
cd /var/www
git clone https://github.com/agumelar/exam-jingga.git
cd exam-jingga
npm install

# 3. Set env vars & build
export VITE_SUPABASE_URL=https://xxx.supabase.co
export VITE_SUPABASE_ANON_KEY=xxx
npm run build

# 4. Setup Nginx
cp nginx.conf.example /etc/nginx/sites-available/exam-jingga
nano /etc/nginx/sites-available/exam-jingga  # Edit domain
ln -s /etc/nginx/sites-available/exam-jingga /etc/nginx/sites-enabled/
nginx -t && systemctl reload nginx

# 5. Install SSL
apt install certbot python3-certbot-nginx -y
certbot --nginx -d yourdomain.com -d www.yourdomain.com

# 6. Done! Access via HTTPS
```

---

## 📞 Need Help?

Jika ada pertanyaan atau kesulitan:

1. **Baca dokumentasi lengkap:** `DEPLOY_VPS.md`
2. **Check troubleshooting section** di dokumentasi
3. **Open GitHub Issue:** https://github.com/agumelar/exam-jingga/issues
4. **Email:** admin@smkn1rongga.sch.id

---

## ✨ Kesimpulan

Dengan dokumentasi ini, Anda bisa deploy aplikasi Exam Jingga ke VPS dengan domain custom Anda sendiri. Tidak ada lagi keterbatasan shared hosting - full control, better performance, dan domain sesuai keinginan Anda!

**Total file baru:** 4 files (+ 1 updated)
**Total dokumentasi:** 1,592 lines
**Estimasi waktu setup:** 30-60 menit

Selamat mencoba! 🚀

---

**Dibuat:** 2026-03-20
**Files:**
- DEPLOY_VPS.md
- ENV_CONFIG.md
- nginx.conf.example
- nginx-demo.conf.example
- README.md (updated)

# Panduan Deploy ke VPS (Virtual Private Server)

## 📋 Overview
Panduan ini menjelaskan cara mendeploy aplikasi Exam Jingga ke VPS dengan domain custom Anda sendiri. Berbeda dengan shared hosting yang menggunakan FTP, VPS memberikan kontrol penuh atas server dan konfigurasi.

## 🎯 Keuntungan Deploy ke VPS
- ✅ **Full Control** - Akses root server penuh
- ✅ **Better Performance** - Resources dedicated untuk aplikasi Anda
- ✅ **Custom Domain** - Gunakan domain apapun yang Anda miliki
- ✅ **Flexible Configuration** - Konfigurasi server sesuai kebutuhan
- ✅ **Scalability** - Mudah upgrade resources saat traffic meningkat

## 🛠️ Persyaratan

### 1. VPS Requirements
- **OS:** Ubuntu 20.04 LTS / 22.04 LTS atau Debian 11/12
- **RAM:** Minimal 1GB (Recommended 2GB+)
- **Storage:** Minimal 10GB
- **CPU:** Minimal 1 vCore
- **Akses:** SSH root atau sudo access

### 2. Domain Requirements
- Domain yang sudah Anda miliki (contoh: `yourdomain.com`)
- Akses ke DNS management untuk pointing domain

### 3. Software yang Dibutuhkan
- Node.js 18+ atau 22+ (LTS recommended)
- Nginx (web server)
- PM2 (process manager) - opsional tapi recommended
- Git
- SSL Certificate (Let's Encrypt - gratis)

## 📦 Metode Deployment

Ada 2 metode deployment yang bisa dipilih:

### Metode A: Static Build + Nginx (Recommended)
Aplikasi di-build menjadi static files dan di-serve oleh Nginx. Ini adalah metode paling efisien untuk React SPA.

### Metode B: Node.js Server + Nginx Reverse Proxy
Aplikasi dijalankan dengan Vite preview server dan Nginx sebagai reverse proxy.

**Rekomendasi:** Gunakan **Metode A** untuk production karena lebih cepat dan resource-efficient.

---

## 🚀 Metode A: Static Build + Nginx (Recommended)

### Step 1: Setup VPS & Install Dependencies

```bash
# Login ke VPS via SSH
ssh root@your-vps-ip

# Update system packages
apt update && apt upgrade -y

# Install Nginx
apt install nginx -y

# Install Node.js 22 (LTS)
curl -fsSL https://deb.nodesource.com/setup_22.x | bash -
apt install nodejs -y

# Install Git
apt install git -y

# Verify installations
node --version  # Should show v22.x.x
npm --version   # Should show 10.x.x
nginx -v        # Should show nginx version
```

### Step 2: Clone & Build Aplikasi

```bash
# Buat direktori untuk aplikasi
mkdir -p /var/www
cd /var/www

# Clone repository
git clone https://github.com/agumelar/exam-jingga.git
cd exam-jingga

# Install dependencies
npm install

# Build aplikasi dengan environment variables
# Ganti dengan URL Supabase Anda sendiri
export VITE_SUPABASE_URL=https://your-project.supabase.co
export VITE_SUPABASE_ANON_KEY=your-anon-key-here

npm run build

# Files hasil build ada di folder dist/
ls -la dist/
```

### Step 3: Konfigurasi Nginx untuk Domain Utama

Buat file konfigurasi Nginx untuk domain Anda:

```bash
# Buat file konfigurasi
nano /etc/nginx/sites-available/exam-jingga
```

Isi dengan konfigurasi berikut (ganti `yourdomain.com` dengan domain Anda):

```nginx
server {
    listen 80;
    listen [::]:80;
    server_name yourdomain.com www.yourdomain.com;

    root /var/www/exam-jingga/dist;
    index index.html;

    # Gzip compression
    gzip on;
    gzip_vary on;
    gzip_min_length 1024;
    gzip_types text/plain text/css text/xml text/javascript application/javascript application/json application/xml+rss;

    # SPA routing - redirect all requests to index.html
    location / {
        try_files $uri $uri/ /index.html;
    }

    # Cache static assets
    location ~* \.(jpg|jpeg|png|gif|ico|svg|css|js|woff|woff2|ttf|eot)$ {
        expires 1y;
        add_header Cache-Control "public, immutable";
    }

    # Security headers
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;

    # Logs
    access_log /var/log/nginx/exam-jingga-access.log;
    error_log /var/log/nginx/exam-jingga-error.log;
}
```

Aktifkan konfigurasi:

```bash
# Buat symbolic link
ln -s /etc/nginx/sites-available/exam-jingga /etc/nginx/sites-enabled/

# Test konfigurasi Nginx
nginx -t

# Reload Nginx
systemctl reload nginx
```

### Step 4: Setup SSL (HTTPS) dengan Let's Encrypt

```bash
# Install Certbot
apt install certbot python3-certbot-nginx -y

# Generate SSL certificate (ganti yourdomain.com)
certbot --nginx -d yourdomain.com -d www.yourdomain.com

# Follow prompts:
# - Enter email address
# - Agree to Terms of Service
# - Choose: Redirect HTTP to HTTPS (recommended)

# Certificate akan auto-renew setiap 90 hari
# Test auto-renewal:
certbot renew --dry-run
```

Setelah SSL aktif, Nginx config akan otomatis di-update dengan HTTPS configuration.

### Step 5: Setup Demo Subdomain (Opsional)

Jika ingin deploy demo di subdomain (contoh: `demo.yourdomain.com`):

```bash
# Build demo app
cd /var/www/exam-jingga
npm run build  # Build sudah include demo.html

# Buat konfigurasi Nginx untuk subdomain demo
nano /etc/nginx/sites-available/demo-exam-jingga
```

Isi dengan:

```nginx
server {
    listen 80;
    listen [::]:80;
    server_name demo.yourdomain.com;

    root /var/www/exam-jingga/dist;
    index demo.html;

    # Gzip compression
    gzip on;
    gzip_vary on;
    gzip_min_length 1024;
    gzip_types text/plain text/css text/xml text/javascript application/javascript application/json application/xml+rss;

    # SPA routing for demo
    location / {
        try_files $uri $uri/ /demo.html;
    }

    # Cache static assets
    location ~* \.(jpg|jpeg|png|gif|ico|svg|css|js|woff|woff2|ttf|eot)$ {
        expires 1y;
        add_header Cache-Control "public, immutable";
    }

    # Security headers
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;

    access_log /var/log/nginx/demo-exam-jingga-access.log;
    error_log /var/log/nginx/demo-exam-jingga-error.log;
}
```

Aktifkan dan setup SSL:

```bash
# Aktifkan konfigurasi
ln -s /etc/nginx/sites-available/demo-exam-jingga /etc/nginx/sites-enabled/

# Test dan reload
nginx -t
systemctl reload nginx

# Setup SSL untuk subdomain demo
certbot --nginx -d demo.yourdomain.com
```

### Step 6: Test Aplikasi

```bash
# Test akses aplikasi
curl -I http://yourdomain.com
# Should return: HTTP/1.1 301 Moved Permanently (redirect to HTTPS)

curl -I https://yourdomain.com
# Should return: HTTP/2 200

# Test demo (jika ada)
curl -I https://demo.yourdomain.com
```

Buka browser dan akses:
- **Main App:** `https://yourdomain.com`
- **Demo App:** `https://demo.yourdomain.com`

---

## 🔄 Update & Maintenance

### Update Aplikasi (Git Pull)

```bash
# Login ke VPS
ssh root@your-vps-ip

# Navigate ke direktori aplikasi
cd /var/www/exam-jingga

# Pull latest changes
git pull origin main

# Install new dependencies (jika ada)
npm install

# Rebuild dengan environment variables
export VITE_SUPABASE_URL=https://your-project.supabase.co
export VITE_SUPABASE_ANON_KEY=your-anon-key-here
npm run build

# Nginx akan otomatis serve file yang baru
# Tidak perlu reload Nginx kecuali ada perubahan config
```

### Automated Update dengan Script

Buat script untuk update otomatis:

```bash
# Buat script
nano /root/update-exam-jingga.sh
```

Isi dengan:

```bash
#!/bin/bash
set -e

echo "Starting update process..."

# Navigate to app directory
cd /var/www/exam-jingga

# Pull latest code
echo "Pulling latest code..."
git pull origin main

# Install dependencies
echo "Installing dependencies..."
npm install

# Build application
echo "Building application..."
export VITE_SUPABASE_URL=https://your-project.supabase.co
export VITE_SUPABASE_ANON_KEY=your-anon-key-here
npm run build

echo "Update completed successfully!"
echo "Deployed at: $(date)"
```

Buat executable:

```bash
chmod +x /root/update-exam-jingga.sh

# Test run
/root/update-exam-jingga.sh
```

### Auto-Deploy dengan GitHub Webhook (Advanced)

Untuk deploy otomatis setiap kali push ke GitHub:

```bash
# Install webhook handler
npm install -g webhook

# Buat webhook config
mkdir -p /root/webhooks
nano /root/webhooks/hooks.json
```

Isi dengan:

```json
[
  {
    "id": "exam-jingga-deploy",
    "execute-command": "/root/update-exam-jingga.sh",
    "command-working-directory": "/var/www/exam-jingga",
    "response-message": "Deployment triggered",
    "trigger-rule": {
      "match": {
        "type": "payload-hash-sha1",
        "secret": "your-webhook-secret-here",
        "parameter": {
          "source": "header",
          "name": "X-Hub-Signature"
        }
      }
    }
  }
]
```

Run webhook server:

```bash
# Install PM2 untuk keep webhook running
npm install -g pm2

# Start webhook with PM2
pm2 start webhook -- -hooks /root/webhooks/hooks.json -verbose

# Save PM2 process list
pm2 save

# Setup PM2 to run on boot
pm2 startup
```

Setup GitHub webhook:
1. Buka GitHub Repository → Settings → Webhooks → Add webhook
2. **Payload URL:** `http://your-vps-ip:9000/hooks/exam-jingga-deploy`
3. **Content type:** `application/json`
4. **Secret:** (sama dengan yang di hooks.json)
5. **Events:** Push events
6. Save

---

## 🔧 Konfigurasi Domain

### DNS Configuration

Di provider domain Anda (Namecheap, GoDaddy, Cloudflare, dll), tambahkan DNS records:

**Untuk Main App:**
```
Type: A
Name: @
Value: IP_VPS_ANDA
TTL: 3600
```

```
Type: A
Name: www
Value: IP_VPS_ANDA
TTL: 3600
```

**Untuk Demo Subdomain:**
```
Type: A
Name: demo
Value: IP_VPS_ANDA
TTL: 3600
```

**Opsional - Gunakan Cloudflare untuk CDN + DDoS Protection:**
1. Pindahkan nameserver domain ke Cloudflare
2. Cloudflare akan otomatis proxy traffic (orange cloud icon)
3. Enable:
   - Auto minify (HTML, CSS, JS)
   - Brotli compression
   - Browser cache TTL
   - Always Use HTTPS

### Tunggu DNS Propagation

DNS propagation biasanya memakan waktu 1-24 jam. Check status:

```bash
# Check DNS resolution
dig yourdomain.com
dig demo.yourdomain.com

# atau pakai online tool
# https://dnschecker.org
```

---

## 📊 Monitoring & Logs

### View Nginx Logs

```bash
# Access logs (traffic)
tail -f /var/log/nginx/exam-jingga-access.log

# Error logs
tail -f /var/log/nginx/exam-jingga-error.log

# Demo logs (jika ada)
tail -f /var/log/nginx/demo-exam-jingga-access.log
```

### Monitor Server Resources

```bash
# CPU & Memory usage
htop

# Disk usage
df -h

# Network traffic
iftop
```

### Setup Log Rotation

Nginx logs akan membesar seiring waktu. Setup log rotation:

```bash
# Edit logrotate config
nano /etc/logrotate.d/nginx
```

Isi dengan:

```
/var/log/nginx/*.log {
    daily
    missingok
    rotate 14
    compress
    delaycompress
    notifempty
    create 0640 www-data adm
    sharedscripts
    postrotate
        [ -f /var/run/nginx.pid ] && kill -USR1 `cat /var/run/nginx.pid`
    endscript
}
```

---

## 🔒 Security Best Practices

### 1. Firewall (UFW)

```bash
# Install UFW
apt install ufw -y

# Allow SSH (IMPORTANT! Jangan lupa atau Anda bisa terkunci)
ufw allow ssh
ufw allow 22/tcp

# Allow HTTP & HTTPS
ufw allow 80/tcp
ufw allow 443/tcp

# Enable firewall
ufw enable

# Check status
ufw status
```

### 2. Fail2Ban (Anti Brute Force)

```bash
# Install Fail2Ban
apt install fail2ban -y

# Start service
systemctl start fail2ban
systemctl enable fail2ban

# Check status
fail2ban-client status
```

### 3. Keep System Updated

```bash
# Setup automatic security updates
apt install unattended-upgrades -y
dpkg-reconfigure -plow unattended-upgrades

# Manual update
apt update && apt upgrade -y
```

### 4. Secure SSH

Edit SSH config:

```bash
nano /etc/ssh/sshd_config
```

Recommended settings:

```
Port 22                          # Atau ganti ke port lain (e.g., 2222)
PermitRootLogin prohibit-password
PasswordAuthentication no        # Force SSH key authentication
PubkeyAuthentication yes
```

Restart SSH:

```bash
systemctl restart sshd
```

### 5. Environment Variables Security

Jangan hardcode secrets di script. Gunakan file `.env`:

```bash
# Buat .env file
nano /var/www/exam-jingga/.env.production
```

Isi dengan:

```
VITE_SUPABASE_URL=https://your-project.supabase.co
VITE_SUPABASE_ANON_KEY=your-anon-key-here
```

Update script untuk load dari .env:

```bash
# Di update script, load .env
source /var/www/exam-jingga/.env.production
npm run build
```

Secure file permissions:

```bash
chmod 600 /var/www/exam-jingga/.env.production
```

---

## 🆚 Perbandingan VPS vs Shared Hosting

| Aspek | Shared Hosting | VPS |
|-------|---------------|-----|
| **Control** | Terbatas | Full root access |
| **Performance** | Shared resources | Dedicated resources |
| **Scalability** | Sulit upgrade | Mudah upgrade RAM/CPU |
| **Cost** | Mulai $2-5/bulan | Mulai $5-10/bulan |
| **Setup** | Mudah (cPanel) | Perlu knowledge Linux |
| **Deployment** | FTP Upload | Git + Build + Nginx |
| **SSL** | Auto (cPanel) | Manual (Certbot) |
| **Backup** | Auto (biasanya) | Manual/Script |
| **Maintenance** | Managed oleh host | Self-managed |
| **Recommended For** | Small projects | Production apps |

---

## 🛠️ Troubleshooting

### 1. Nginx 502 Bad Gateway

**Problem:** Aplikasi tidak bisa diakses, error 502.

**Solution:**
```bash
# Check Nginx status
systemctl status nginx

# Restart Nginx
systemctl restart nginx

# Check error logs
tail -50 /var/log/nginx/exam-jingga-error.log
```

### 2. Domain Tidak Bisa Diakses

**Problem:** Domain mengarah ke IP tapi tidak bisa diakses.

**Solution:**
```bash
# Check DNS resolution
dig yourdomain.com

# Check Nginx is running
systemctl status nginx

# Check Nginx listening on port 80/443
netstat -tlnp | grep nginx

# Check firewall
ufw status
```

### 3. SSL Certificate Error

**Problem:** Certificate expired atau error.

**Solution:**
```bash
# Renew certificate
certbot renew

# Force renew
certbot renew --force-renewal

# Check certificate
certbot certificates
```

### 4. Build Gagal

**Problem:** `npm run build` error.

**Solution:**
```bash
# Clear cache
rm -rf node_modules package-lock.json
npm install

# Check Node version
node --version  # Should be 18+ or 22+

# Build with verbose
npm run build -- --debug
```

### 5. File Permission Denied

**Problem:** Cannot write files, permission denied.

**Solution:**
```bash
# Fix ownership
chown -R www-data:www-data /var/www/exam-jingga

# Fix permissions
chmod -R 755 /var/www/exam-jingga
```

---

## 📚 Rekomendasi VPS Providers

### Indonesia
- **Niagahoster VPS** - Mulai Rp 100.000/bulan
- **Dewaweb VPS** - Mulai Rp 150.000/bulan
- **IDCloudHost** - Mulai Rp 75.000/bulan
- **Alibaba Cloud Indonesia** - Mulai $5/bulan

### International
- **DigitalOcean** - Mulai $6/bulan (Recommended)
- **Linode (Akamai)** - Mulai $5/bulan
- **Vultr** - Mulai $6/bulan
- **AWS Lightsail** - Mulai $5/bulan
- **Hetzner** - Mulai €4.15/bulan (cheapest, tapi server di EU)

**Rekomendasi untuk pemula:** DigitalOcean atau Niagahoster (support Bahasa Indonesia).

---

## 📞 Support

### Official Documentation
- **Nginx:** https://nginx.org/en/docs/
- **Let's Encrypt:** https://letsencrypt.org/docs/
- **Vite:** https://vitejs.dev/guide/

### Community
- **GitHub Issues:** https://github.com/agumelar/exam-jingga/issues
- **Email:** admin@smkn1rongga.sch.id

---

## 📝 Checklist Deploy VPS

- [ ] VPS sudah siap (Ubuntu/Debian)
- [ ] SSH access sudah bisa login
- [ ] Domain sudah dibeli
- [ ] DNS A record sudah diarahkan ke IP VPS
- [ ] Nginx sudah terinstall
- [ ] Node.js 22+ sudah terinstall
- [ ] Repository sudah di-clone
- [ ] Dependencies sudah di-install (`npm install`)
- [ ] Environment variables sudah di-set
- [ ] Build berhasil (`npm run build`)
- [ ] Nginx config sudah dibuat dan aktif
- [ ] SSL certificate sudah terinstall (Certbot)
- [ ] Firewall sudah dikonfigurasi (UFW)
- [ ] Aplikasi bisa diakses via HTTPS
- [ ] Auto-update script sudah dibuat (opsional)
- [ ] Monitoring logs sudah di-setup

---

**Last Updated:** 2026-03-20
**Version:** 1.0.0
**Author:** Claude Code Assistant

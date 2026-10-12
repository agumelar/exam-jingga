#!/usr/bin/env bash
# ==============================================================================
# Deploy Exam Jingga ke VPS produksi.
#
# Dari komputer lokal (commit sudah di-push ke GitHub):
#   bash scripts/deploy_vps_dath.sh            # deploy origin/main
#   bash scripts/deploy_vps_dath.sh <commit>   # deploy commit tertentu
#
# Server menarik kode dengan git (bukan menyalin folder lokal), jadi berkas lokal yang belum
# di-commit tidak pernah ikut terkirim. Database dibackup otomatis sebelum migrasi.
# ==============================================================================
set -euo pipefail

VPS_SSH="${VPS_SSH:-openclaw-server}"
DEPLOY_DIR="${DEPLOY_DIR:-/opt/exam-jingga}"
REF="${1:-origin/main}"

if [ "${RUN_ON_VPS:-0}" != "1" ]; then
    echo "==> Deploy ${REF} ke ${VPS_SSH}:${DEPLOY_DIR}"
    # Merge dulu sebelum skrip dijalankan, supaya bash tidak membaca skrip yang berubah di tengah eksekusi
    ssh "${VPS_SSH}" "cd ${DEPLOY_DIR} && git fetch --quiet origin && git merge --ff-only ${REF} && RUN_ON_VPS=1 bash scripts/deploy_vps_dath.sh ${REF}"
    echo "==> Cek domain publik"
    curl -s -o /dev/null -w "login: %{http_code}\n" https://exam.smkn1rongga.sch.id/accounts/login/
    exit 0
fi

cd "${DEPLOY_DIR}"
echo "[1/7] Checkout ${REF}"
git fetch --quiet origin
git merge --ff-only "${REF}"
git log --oneline -1

echo "[2/7] Dependency Python"
# shellcheck disable=SC1091
source .venv/bin/activate
pip install --quiet -r requirements.txt

set -a
# shellcheck disable=SC1091
. ./.env
set +a
export DJANGO_SETTINGS_MODULE=config.settings.production

echo "[3/7] Backup database sebelum migrasi"
sudo install -d -o "$(id -un)" -g "$(id -gn)" -m 700 /opt/exam-jingga-backups
bash scripts/backup_db.sh pra-migrasi

echo "[4/7] Migrasi + tabel cache"
python manage.py check --deploy --fail-level ERROR
python manage.py migrate --noinput
python manage.py createcachetable

echo "[5/7] Build CSS + static"
npm run build:css > /dev/null
python manage.py collectstatic --noinput

echo "[6/7] Unit systemd + Nginx"
sudo cp scripts/exam_jingga.service scripts/exam_jingga_grader.service scripts/exam_jingga_grader.timer \
    scripts/exam_jingga_backup.service scripts/exam_jingga_backup.timer /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now exam_jingga_grader.timer exam_jingga_backup.timer > /dev/null
sudo cp scripts/nginx_dath.conf /etc/nginx/sites-available/exam.smkn1rongga.sch.id
sudo nginx -t
sudo systemctl reload nginx

echo "[7/7] Restart aplikasi"
sudo systemctl restart exam_jingga.service
sleep 3
systemctl is-active exam_jingga.service
curl -sf -o /dev/null http://127.0.0.1:8005/accounts/login/ && echo "health check OK"

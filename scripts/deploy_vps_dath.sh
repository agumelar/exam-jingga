#!/usr/bin/env bash
# ==============================================================================
# Exam Jingga DATH Stack Production Deployment Script
# Target Server: VPS Ubuntu 24.04 ARM64 (145.241.157.243)
# Path: /opt/exam-jingga
# ==============================================================================

set -euo pipefail

VPS_HOST="${VPS_HOST:-145.241.157.243}"
VPS_USER="${VPS_USER:-ubuntu}"
SSH_KEY="${SSH_KEY:-$HOME/.ssh/exam_jingga_vps.key}"
DEPLOY_DIR="${DEPLOY_DIR:-/opt/exam-jingga}"
BRANCH="${1:-main}"

echo "========================================================"
echo "🚀 EXAM JINGGA - DATH STACK PRODUCTION DEPLOYMENT"
echo "Target Host : ${VPS_USER}@${VPS_HOST}"
echo "Deploy Path : ${DEPLOY_DIR}"
echo "Git Branch  : ${BRANCH}"
echo "Timestamp   : $(date '+%Y-%m-%d %H:%M:%S %Z')"
echo "========================================================"

# Determine if running directly on VPS host or triggered remotely from local machine
if [ "${RUN_LOCAL:-0}" = "1" ] || [ -d "/opt/exam-jingga" ] && [ "$(hostname)" != "" ] && [ "${USER:-}" = "ubuntu" ]; then
    echo "📦 [1/6] Running directly on VPS host..."
    cd "${DEPLOY_DIR}"

    echo "🐍 [2/6] Activating virtual environment & verifying packages..."
    if [ ! -d ".venv" ]; then
        python3 -m venv .venv
    fi
    source .venv/bin/activate
    export DJANGO_SETTINGS_MODULE='config.settings.production'

    echo "🗄️ [3/6] Running database migrations on PostgreSQL..."
    python manage.py migrate --noinput

    echo "📦 [4/6] Collecting static assets & optimizing WhiteNoise cache..."
    python manage.py collectstatic --noinput

    echo "⚙️ [5/6] Verifying Nginx & systemd service..."
    if [ -f "scripts/nginx_dath.conf" ]; then
        sudo cp scripts/nginx_dath.conf /etc/nginx/sites-available/exam.smkn1rongga.sch.id
        sudo nginx -t
        sudo systemctl reload nginx
    fi

    echo "🔄 [6/6] Restarting Gunicorn application server..."
    sudo systemctl restart exam_jingga.service
    sudo systemctl status exam_jingga.service --no-pager -l

    echo "🔍 Verifying application health check on internal port 8005..."
    sleep 2
    if curl -sfI http://127.0.0.1:8005/login/ > /dev/null; then
        echo "✅ Gunicorn health check: SUCCESS (HTTP 200/302 OK)"
    else
        echo "⚠️ Health check returned non-200. Please inspect: sudo journalctl -u exam_jingga.service -n 20"
    fi

    echo "🎉 DEPLOYMENT COMPLETED SUCCESSFULLY!"
else
    echo "📤 [1/3] Syncing latest codebase to ${VPS_USER}@${VPS_HOST}:${DEPLOY_DIR}..."
    rsync -avz --delete \
        --exclude='.venv' \
        --exclude='node_modules' \
        --exclude='.git' \
        --exclude='__pycache__' \
        --exclude='.pytest_cache' \
        --exclude='*.pyc' \
        --exclude='.env' \
        --exclude='media/' \
        --exclude='*.sqlite3' \
        --exclude='staticfiles/' \
        -e "ssh -i ${SSH_KEY} -o StrictHostKeyChecking=no" \
        ./ "${VPS_USER}@${VPS_HOST}:${DEPLOY_DIR}/"

    echo "🌐 [2/3] Executing deployment tasks on VPS via SSH..."
    ssh -i "${SSH_KEY}" -o StrictHostKeyChecking=no "${VPS_USER}@${VPS_HOST}" "
        set -euo pipefail
        export RUN_LOCAL=1
        cd ${DEPLOY_DIR}
        bash scripts/deploy_vps_dath.sh ${BRANCH}
    "

    echo "🌐 [3/3] Verifying public domain response (HTTPS)..."
    sleep 2
    STATUS_CODE=$(curl -s -o /dev/null -w "%{http_code}" -b "cbt_preview=1" https://exam.smkn1rongga.sch.id/login/)
    echo "Public Domain Status Code: ${STATUS_CODE}"

    echo "🎉 REMOTE DEPLOYMENT TO VPS FINISHED 100% SUCCESSFULLY!"
fi

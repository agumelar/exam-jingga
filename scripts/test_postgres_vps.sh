#!/usr/bin/env bash
# ==============================================================================
# Jalankan seluruh test di PostgreSQL sungguhan, di VPS, sebelum deploy.
#
# Test lokal memakai SQLite, yang mengabaikan perilaku khusus PostgreSQL (misalnya
# SELECT ... FOR UPDATE). Skrip ini membuat container PostgreSQL sementara yang hanya
# terbuka di 127.0.0.1, menyalin kode dari commit yang diminta ke /tmp, menjalankan
# pytest, lalu menghapus semuanya. Database produksi tidak disentuh.
#
#   bash scripts/test_postgres_vps.sh            # commit origin/main
#   bash scripts/test_postgres_vps.sh <commit>
# ==============================================================================
set -euo pipefail

VPS_SSH="${VPS_SSH:-openclaw-server}"
REF="${1:-origin/main}"

ssh "${VPS_SSH}" "REF='${REF}' bash -s" <<'REMOTE'
set -euo pipefail
WORK=$(mktemp -d /tmp/exam-pgtest.XXXXXX)
NAME="exam-pgtest-$$"
cleanup() { docker stop "$NAME" >/dev/null 2>&1 || true; rm -rf "$WORK"; }
trap cleanup EXIT

cd /opt/exam-jingga && git fetch -q origin
mkdir -p "$WORK/src" && git archive "$REF" | tar -x -C "$WORK/src"
echo "==> Test PostgreSQL untuk $(git rev-parse --short "$REF")"

openssl rand -hex 16 > "$WORK/pw" && chmod 600 "$WORK/pw"
PORT=$(( 55000 + RANDOM % 900 ))
docker run -d --rm --name "$NAME" -p "127.0.0.1:${PORT}:5432" -e POSTGRES_PASSWORD="$(cat "$WORK/pw")" postgres:17-alpine >/dev/null

python3 -m venv "$WORK/venv"
"$WORK/venv/bin/pip" install -q -r "$WORK/src/requirements-dev.txt"
cat > "$WORK/src/config/settings/pgtest.py" <<EOF
from .development import *  # noqa
DATABASES = {"default": {"ENGINE": "django.db.backends.postgresql", "NAME": "postgres", "USER": "postgres",
             "PASSWORD": open("$WORK/pw").read().strip(), "HOST": "127.0.0.1", "PORT": "$PORT"}}
EOF

for _ in $(seq 1 30); do docker exec "$NAME" pg_isready -U postgres >/dev/null 2>&1 && break; sleep 1; done
cd "$WORK/src"
env -u DJANGO_SETTINGS_MODULE "$WORK/venv/bin/python" -m pytest -q -p no:cacheprovider --ds=config.settings.pgtest
REMOTE

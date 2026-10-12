#!/usr/bin/env bash
# ==============================================================================
# Backup Exam Jingga: database (skema public) + media soal.
#
#   bash scripts/backup_db.sh            # backup harian (dipanggil exam_jingga_backup.timer)
#   bash scripts/backup_db.sh pra-migrasi  # dipanggil deploy sebelum migrate
#
# PostgreSQL 17 berjalan di container supabase-db, sedangkan pg_dump di host masih versi 16
# (pg_dump menolak server yang lebih baru), jadi dump dijalankan di dalam container.
#
# Salinan ke Google Drive sekolah memakai rclone. Aktif bila RCLONE_REMOTE diisi di .env,
# contoh: RCLONE_REMOTE=gdrive-sekolah:exam-jingga-backup (remote dibuat dengan `rclone config`).
# ==============================================================================
set -euo pipefail

APP_DIR="${APP_DIR:-/opt/exam-jingga}"
BACKUP_DIR="${BACKUP_DIR:-/opt/exam-jingga-backups}"
RETENTION_DAYS="${RETENTION_DAYS:-14}"
REMOTE_RETENTION_DAYS="${REMOTE_RETENTION_DAYS:-60}"
DB_CONTAINER="${DB_CONTAINER:-supabase-db}"
LABEL="${1:-harian}"

set -a
# shellcheck disable=SC1091
. "${APP_DIR}/.env"
set +a

umask 077
mkdir -p "${BACKUP_DIR}"
STAMP="$(TZ=Asia/Jakarta date +%Y%m%d-%H%M)"
DB_FILE="${BACKUP_DIR}/exam-jingga-db-${LABEL}-${STAMP}.dump"
MEDIA_FILE="${BACKUP_DIR}/exam-jingga-media-${LABEL}-${STAMP}.tar.gz"

echo "[backup] dump database ${DB_NAME} (skema public) -> ${DB_FILE}"
docker exec -e PGPASSWORD="${DB_PASSWORD}" "${DB_CONTAINER}" \
    pg_dump -h 127.0.0.1 -U "${DB_USER}" -d "${DB_NAME}" -n public -Fc > "${DB_FILE}.tmp"

# Dump yang tidak bisa dibaca pg_restore dianggap gagal dan tidak menggantikan backup lama
docker exec -i "${DB_CONTAINER}" pg_restore --list < "${DB_FILE}.tmp" > /dev/null
mv "${DB_FILE}.tmp" "${DB_FILE}"

if [ "${LABEL}" = "harian" ] && [ -d "${APP_DIR}/media" ]; then
    echo "[backup] arsip media -> ${MEDIA_FILE}"
    tar -czf "${MEDIA_FILE}" -C "${APP_DIR}" media
fi

find "${BACKUP_DIR}" -name 'exam-jingga-*' -type f -mtime "+${RETENTION_DAYS}" -delete

if [ -n "${RCLONE_REMOTE:-}" ]; then
    if command -v rclone > /dev/null; then
        echo "[backup] salin ke ${RCLONE_REMOTE}"
        rclone copy "${DB_FILE}" "${RCLONE_REMOTE}/database"
        [ -f "${MEDIA_FILE}" ] && rclone copy "${MEDIA_FILE}" "${RCLONE_REMOTE}/media"
        rclone delete --min-age "${REMOTE_RETENTION_DAYS}d" "${RCLONE_REMOTE}" || true
    else
        echo "[backup] PERINGATAN: RCLONE_REMOTE diisi tetapi rclone belum terpasang" >&2
    fi
else
    echo "[backup] RCLONE_REMOTE belum diisi; backup hanya tersimpan di ${BACKUP_DIR}"
fi

echo "[backup] selesai: $(du -h "${DB_FILE}" | cut -f1) database"

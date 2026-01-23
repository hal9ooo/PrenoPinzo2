#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DB_PATH="${DB_PATH:-${ROOT_DIR}/db.sqlite3}"
BACKUP_DIR="${BACKUP_DIR:-${ROOT_DIR}/backups}"
RETENTION_DAYS="${RETENTION_DAYS:-180}"

if [[ ! -f "${DB_PATH}" ]]; then
  echo "[backup] DB not found: ${DB_PATH}" >&2
  exit 1
fi

mkdir -p "${BACKUP_DIR}"

timestamp="$(date +%Y%m%d_%H%M%S)"
backup_file="${BACKUP_DIR}/db_${timestamp}.sqlite3"

if command -v sqlite3 >/dev/null 2>&1; then
  sqlite3 "${DB_PATH}" ".backup '${backup_file}'"
else
  # Fallback (less safe under write load, but DB is small)
  cp "${DB_PATH}" "${backup_file}"
fi

# Retention (delete older than N days)
find "${BACKUP_DIR}" -type f -name 'db_*.sqlite3' -mtime +"${RETENTION_DAYS}" -print -delete

echo "[backup] OK: ${backup_file} (retention ${RETENTION_DAYS}d)"

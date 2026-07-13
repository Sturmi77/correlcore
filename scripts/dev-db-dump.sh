#!/usr/bin/env bash
# Create a development Postgres dump (custom format) plus meta sidecar.
# Usage: scripts/dev-db-dump.sh [output-dir]
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
OUT_DIR="${1:-${DEV_DB_BACKUP_DIR:-/tmp/correlcore-backups}}"
CONTAINER="${POSTGRES_CONTAINER:-correlcore-postgres}"
DB_USER="${POSTGRES_USER:-correlcore}"
DB_NAME="${POSTGRES_DB:-correlcore}"
APP_ENV="${APP_ENV:-development}"

if [[ "${APP_ENV}" != "development" && "${APP_ENV}" != "test" ]]; then
  echo "Refusing dump: APP_ENV=${APP_ENV} (allowed: development|test)" >&2
  exit 1
fi

mkdir -p "${OUT_DIR}"
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
DUMP_PATH="${OUT_DIR%/}/correlcore-dev-${STAMP}.dump"
META_PATH="${DUMP_PATH}.meta.json"

if ! docker inspect -f '{{.State.Running}}' "${CONTAINER}" 2>/dev/null | grep -qi true; then
  echo "Container ${CONTAINER} is not running." >&2
  exit 1
fi

docker exec "${CONTAINER}" pg_dump -U "${DB_USER}" -Fc --no-owner "${DB_NAME}" > "${DUMP_PATH}"

ALEMBIC_HEAD="unknown"
if [[ -d "${ROOT}/backend" ]]; then
  ALEMBIC_HEAD="$(
    cd "${ROOT}/backend" &&
      uv run --python 3.12 alembic -c migrations/alembic.ini current 2>/dev/null |
      awk '{print $1; exit}' || true
  )"
fi

cat > "${META_PATH}" <<EOF
{
  "created_at": "${STAMP}",
  "app_env": "${APP_ENV}",
  "container": "${CONTAINER}",
  "database": "${DB_NAME}",
  "alembic_head": "${ALEMBIC_HEAD}",
  "ops_ready": false,
  "note": "Keep ENCRYPTION_KEY with this dump; ciphertext notes require the same Fernet master key."
}
EOF

echo "Wrote ${DUMP_PATH}"
echo "Meta  ${META_PATH}"
echo "Remember: ENCRYPTION_KEY must travel with usable dumps."

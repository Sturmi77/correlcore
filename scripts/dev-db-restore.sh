#!/usr/bin/env bash
# Restore a development Postgres dump created by scripts/dev-db-dump.sh.
# Usage: scripts/dev-db-restore.sh <dump-file> [--yes]
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DUMP_PATH="${1:-}"
CONFIRM="${2:-}"
CONTAINER="${POSTGRES_CONTAINER:-correlcore-postgres}"
DB_USER="${POSTGRES_USER:-correlcore}"
DB_NAME="${POSTGRES_DB:-correlcore}"
APP_ENV="${APP_ENV:-development}"

if [[ -z "${DUMP_PATH}" ]]; then
  echo "Usage: $0 <dump-file> [--yes]" >&2
  exit 1
fi

if [[ "${APP_ENV}" != "development" && "${APP_ENV}" != "test" ]]; then
  echo "Refusing restore: APP_ENV=${APP_ENV} (allowed: development|test)" >&2
  exit 1
fi

if [[ ! -f "${DUMP_PATH}" ]]; then
  echo "Dump not found: ${DUMP_PATH}" >&2
  exit 1
fi

if [[ "${CONFIRM}" != "--yes" ]]; then
  echo "This will restore into ${DB_NAME} on ${CONTAINER}." >&2
  echo "Re-run with --yes to confirm." >&2
  exit 1
fi

if ! docker inspect -f '{{.State.Running}}' "${CONTAINER}" 2>/dev/null | grep -qi true; then
  echo "Container ${CONTAINER} is not running." >&2
  exit 1
fi

echo "Restoring ${DUMP_PATH} -> ${CONTAINER}:${DB_NAME}"
# pg_restore --clean may exit 1 with ignorable errors; allow that.
set +e
docker exec -i "${CONTAINER}" pg_restore -U "${DB_USER}" -d "${DB_NAME}" \
  --clean --if-exists --no-owner --role="${DB_USER}" < "${DUMP_PATH}"
RC=$?
set -e
if [[ "${RC}" -gt 1 ]]; then
  echo "pg_restore failed with exit ${RC}" >&2
  exit "${RC}"
fi

if [[ -d "${ROOT}/backend" ]]; then
  echo "Running alembic upgrade head (safe no-op when dump is current)..."
  (
    cd "${ROOT}/backend"
    export APP_ENV="${APP_ENV}"
    uv run --python 3.12 alembic -c migrations/alembic.ini upgrade head
  )
fi

echo "Restore complete. Restart API/worker if sessions look stale."
echo "ENCRYPTION_KEY must match the dump environment."

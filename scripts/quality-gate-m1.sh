#!/usr/bin/env bash
# Reproducible M1 quality gate for local runs.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

"$ROOT/backend/scripts/check.sh"

cd "$ROOT"
pnpm format:check
pnpm lint
pnpm test

# Lightweight stale-comment sentinel for review drift found during M1 review.
if rg -n "TODO M1|M1 stores plaintext|offline-first sync layer \(M1|M1 follow-up" \
  backend/app apps/web/src docs backend/migrations; then
  echo "Stale M1 review markers found; update comments or document a tracked follow-up." >&2
  exit 1
fi

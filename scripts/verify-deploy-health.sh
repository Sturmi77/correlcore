#!/usr/bin/env bash
# Verify a CorrelCore deployment exposes the expected build identity (#587).
#
# Usage:
#   ./scripts/verify-deploy-health.sh https://correlcore.com
#   ./scripts/verify-deploy-health.sh https://correlcore.com a7de9fb
#
# The optional second argument is a minimum git_commit prefix (short or full).
set -euo pipefail

BASE_URL="${1:?Usage: $0 <base-url> [min-git-commit-prefix]}"
MIN_COMMIT="${2:-}"

HEALTH_URL="${BASE_URL%/}/api/v1/health/live"
RESPONSE="$(curl -fsS "$HEALTH_URL")"

echo "$RESPONSE" | python3 -m json.tool

GIT_COMMIT="$(echo "$RESPONSE" | python3 -c "import json,sys; print(json.load(sys.stdin).get('git_commit',''))")"
IMAGE_TAG="$(echo "$RESPONSE" | python3 -c "import json,sys; print(json.load(sys.stdin).get('image_tag',''))")"

if [[ -z "$GIT_COMMIT" ]]; then
  echo "ERROR: health response missing git_commit" >&2
  exit 1
fi

echo "Running: git_commit=$GIT_COMMIT image_tag=$IMAGE_TAG"

if [[ -n "$MIN_COMMIT" ]]; then
  if [[ "$GIT_COMMIT" == "$MIN_COMMIT"* ]]; then
    echo "OK: git_commit matches required prefix $MIN_COMMIT"
  else
    echo "FAIL: git_commit $GIT_COMMIT is older than required $MIN_COMMIT — redeploy needed." >&2
    echo "See infra/dockhand/README.md § Redeploy and IMAGE_TAG pinning." >&2
    exit 1
  fi
fi

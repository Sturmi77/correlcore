#!/usr/bin/env bash
# Prepend (or refresh) a mobile-friendly Android download block at the top of a
# GitHub Release body. Safe to re-run; uses HTML comment markers as sentinels.
#
# Usage:
#   scripts/github-release-android-downloads.sh <tag> [version_name]
#
# Requires: gh, GITHUB_REPOSITORY (or --repo), GH_TOKEN / gh auth.
set -euo pipefail

TAG="${1:?tag required (e.g. v1.1.0)}"
VERSION_NAME="${2:-}"
if [[ -z "${VERSION_NAME}" ]]; then
  VERSION_NAME="${TAG#v}"
fi

REPO="${GITHUB_REPOSITORY:?GITHUB_REPOSITORY must be set (owner/repo)}"
BASE="https://github.com/${REPO}/releases/download/${TAG}"
APK_URL="${BASE}/correlcore-${VERSION_NAME}.apk"
AAB_URL="${BASE}/correlcore-${VERSION_NAME}.aab"
SUMS_URL="${BASE}/SHA256SUMS.txt"
DOCS_URL="https://github.com/${REPO}/blob/${TAG}/docs/selfhost/ANDROID_SIDELOAD.md"
BEGIN="<!-- correlcore:android-downloads:begin -->"
END="<!-- correlcore:android-downloads:end -->"

BLOCK=$(
  cat <<EOF
${BEGIN}
## Android APK (sideload)

Tap to download on your phone (no GitHub account needed):

- **[⬇️ Download APK](${APK_URL})** — \`correlcore-${VERSION_NAME}.apk\`
- [AAB (Play Console upload)](${AAB_URL})
- [SHA-256 checksums](${SUMS_URL})

Install help: [ANDROID_SIDELOAD.md](${DOCS_URL}) · Obtainium: subscribe to this repo’s releases.

${END}
EOF
)

TMP="$(mktemp)"
BODY_FILE="$(mktemp)"
trap 'rm -f "${TMP}" "${BODY_FILE}"' EXIT

# softprops / gh may create the release slightly later — retry briefly.
for _ in 1 2 3 4 5 6 7 8 9 10; do
  if gh release view "${TAG}" --repo "${REPO}" --json body -q .body >"${BODY_FILE}" 2>/dev/null; then
    break
  fi
  sleep 3
done

if [[ ! -s "${BODY_FILE}" ]] && ! gh release view "${TAG}" --repo "${REPO}" >/dev/null 2>&1; then
  echo "Release ${TAG} not found yet; creating notes-only placeholder is out of scope." >&2
  exit 1
fi

python3 - "${BODY_FILE}" "${TMP}" <<'PY'
import re
import sys
from pathlib import Path

body_path, out_path = Path(sys.argv[1]), Path(sys.argv[2])
body = body_path.read_text(encoding="utf-8")
# Strip previous sentinel block (any content between markers).
pattern = re.compile(
    r"<!-- correlcore:android-downloads:begin -->.*?<!-- correlcore:android-downloads:end -->\s*",
    re.DOTALL,
)
body = pattern.sub("", body).lstrip("\n")
out_path.write_text(body, encoding="utf-8")
PY

{
  printf '%s\n\n' "${BLOCK}"
  cat "${TMP}"
} >"${BODY_FILE}"

gh release edit "${TAG}" --repo "${REPO}" --notes-file "${BODY_FILE}"
echo "Updated ${TAG} release notes with Android download links at the top."

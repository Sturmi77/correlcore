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
APK_NAME="correlcore-${VERSION_NAME}.apk"
AAB_NAME="correlcore-${VERSION_NAME}.aab"
SUMS_NAME="SHA256SUMS.txt"
DOCS_URL="https://github.com/${REPO}/blob/${TAG}/docs/selfhost/ANDROID_SIDELOAD.md"
BEGIN="<!-- correlcore:android-downloads:begin -->"
END="<!-- correlcore:android-downloads:end -->"

TMP="$(mktemp)"
BODY_FILE="$(mktemp)"
ASSETS_FILE="$(mktemp)"
trap 'rm -f "${TMP}" "${BODY_FILE}" "${ASSETS_FILE}"' EXIT

# strip_block <in> <out> — remove any previous sentinel block from a release body.
strip_block() {
  python3 - "$1" "$2" <<'PY'
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
}

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

# Never advertise a download that is not attached to the release (#450). The APK
# is uploaded by the signed Android job, which only runs when ANDROID_* secrets
# are configured; without this gate every `v*` tag published a 404 link.
gh release view "${TAG}" --repo "${REPO}" --json assets -q '.assets[].name' >"${ASSETS_FILE}" 2>/dev/null || true

has_asset() {
  grep -Fxq "$1" "${ASSETS_FILE}"
}

if ! has_asset "${APK_NAME}"; then
  echo "::warning::No ${APK_NAME} attached to ${TAG}; skipping Android download block."
  # Drop a stale block from an earlier run whose asset is gone.
  if grep -qF "${BEGIN}" "${BODY_FILE}"; then
    strip_block "${BODY_FILE}" "${TMP}"
    cp "${TMP}" "${BODY_FILE}"
    gh release edit "${TAG}" --repo "${REPO}" --notes-file "${BODY_FILE}"
    echo "Removed stale Android download block from ${TAG}."
  fi
  exit 0
fi

LINKS="- **[⬇️ Download APK](${BASE}/${APK_NAME})** — \`${APK_NAME}\`"
if has_asset "${AAB_NAME}"; then
  LINKS="${LINKS}
- [AAB (Play Console upload)](${BASE}/${AAB_NAME})"
fi
if has_asset "${SUMS_NAME}"; then
  LINKS="${LINKS}
- [SHA-256 checksums](${BASE}/${SUMS_NAME})"
fi

BLOCK=$(
  cat <<EOF
${BEGIN}
## Android APK (sideload)

Tap to download on your phone (no GitHub account needed):

${LINKS}

Install help: [ANDROID_SIDELOAD.md](${DOCS_URL}) · Obtainium: subscribe to this repo’s releases.

${END}
EOF
)

strip_block "${BODY_FILE}" "${TMP}"

{
  printf '%s\n\n' "${BLOCK}"
  cat "${TMP}"
} >"${BODY_FILE}"

gh release edit "${TAG}" --repo "${REPO}" --notes-file "${BODY_FILE}"
echo "Updated ${TAG} release notes with Android download links at the top."

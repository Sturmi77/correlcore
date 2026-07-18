#!/usr/bin/env bash
# Decode ANDROID_KEYSTORE_BASE64 into a temp keystore path for Gradle.
# Exports ANDROID_KEYSTORE_PATH for the current shell when sourced:
#   source apps/android/scripts/prepare-release-signing.sh
set -euo pipefail

if [[ -z "${ANDROID_KEYSTORE_BASE64:-}" ]]; then
  echo "ANDROID_KEYSTORE_BASE64 is not set" >&2
  exit 1
fi

OUT_DIR="${RUNNER_TEMP:-${TMPDIR:-/tmp}}/correlcore-android-signing"
mkdir -p "$OUT_DIR"
# Restrict directory permissions (contains signing material).
chmod 700 "$OUT_DIR"
KEYSTORE_PATH="${OUT_DIR}/release.keystore"

echo "${ANDROID_KEYSTORE_BASE64}" | base64 -d >"${KEYSTORE_PATH}"
chmod 600 "${KEYSTORE_PATH}"

export ANDROID_KEYSTORE_PATH="${KEYSTORE_PATH}"
echo "ANDROID_KEYSTORE_PATH=${ANDROID_KEYSTORE_PATH}"

# When not sourced, print path for GitHub Actions $GITHUB_ENV
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
  if [[ -n "${GITHUB_ENV:-}" ]]; then
    echo "ANDROID_KEYSTORE_PATH=${ANDROID_KEYSTORE_PATH}" >>"${GITHUB_ENV}"
  fi
fi

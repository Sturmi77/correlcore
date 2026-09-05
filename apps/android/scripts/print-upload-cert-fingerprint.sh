#!/usr/bin/env bash
# Print the SHA-256 certificate fingerprint of the Android upload keystore.
# Use this to verify Play Console → App integrity → Upload key certificate
# matches the CI signing key (AP-1 / #719).
#
# Usage:
#   apps/android/scripts/print-upload-cert-fingerprint.sh <keystore> [alias]
#
# Env (optional):
#   ANDROID_KEYSTORE_PASSWORD — store password (otherwise keytool prompts)
#   ANDROID_KEY_ALIAS         — default alias if not passed as $2
#
# Example:
#   apps/android/scripts/print-upload-cert-fingerprint.sh ./correlcore-upload.keystore correlcore
set -euo pipefail

KEYSTORE="${1:-}"
ALIAS="${2:-${ANDROID_KEY_ALIAS:-correlcore}}"

if [[ -z "${KEYSTORE}" || ! -f "${KEYSTORE}" ]]; then
  echo "Usage: $0 <keystore-file> [alias]" >&2
  echo "  Prints SHA-256 of the upload certificate for Play App Signing checks." >&2
  exit 1
fi

if ! command -v keytool >/dev/null 2>&1; then
  echo "keytool not found — install a JDK and ensure keytool is on PATH." >&2
  exit 1
fi

KEYTOOL_ARGS=(-list -v -keystore "${KEYSTORE}" -alias "${ALIAS}")
if [[ -n "${ANDROID_KEYSTORE_PASSWORD:-}" ]]; then
  KEYTOOL_ARGS+=(-storepass "${ANDROID_KEYSTORE_PASSWORD}")
fi

# keytool prints the full certificate block; extract SHA-256 only for a clean diff.
OUTPUT="$(keytool "${KEYTOOL_ARGS[@]}" 2>/dev/null)" || {
  echo "keytool failed — check path, alias, and password." >&2
  exit 1
}

echo "Keystore: ${KEYSTORE}"
echo "Alias:    ${ALIAS}"
echo "${OUTPUT}" | awk '
  BEGIN { ignore = 0 }
  /^Certificate fingerprints:/ { ignore = 1; next }
  ignore && /SHA256:/ {
    sub(/^[[:space:]]*SHA256:[[:space:]]*/, "")
    print "SHA-256:  " $0
    exit
  }
  # Some keytool locales use "SHA-256:"
  ignore && /SHA-256:/ {
    sub(/^[[:space:]]*SHA-256:[[:space:]]*/, "")
    print "SHA-256:  " $0
    exit
  }
'

echo
echo "Compare with Play Console → Setup → App integrity → Upload key certificate."

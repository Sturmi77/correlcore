#!/usr/bin/env bash
# Assert whether a built APK declares Health Connect (android.permission.health.*)
# permissions. Guards AP-HC Option A: the Play flavor must ship HC-free, the
# sideload flavor must keep HC. See docs/M11_PLAY_STORE_GAP_ANALYSIS.md §4.
#
# Usage:
#   assert-health-permissions.sh absent  <apk>   # fail if any health.* permission present (Play)
#   assert-health-permissions.sh present <apk>   # fail if no health.* permission present (sideload)
set -euo pipefail

MODE="${1:?mode required: absent|present}"
APK="${2:?apk path required}"

if [[ ! -f "${APK}" ]]; then
  echo "::error::APK not found: ${APK}" >&2
  exit 1
fi

# Locate aapt2 (preferred) or aapt from the Android SDK build-tools.
find_tool() {
  local name="$1"
  if command -v "${name}" >/dev/null 2>&1; then
    command -v "${name}"
    return 0
  fi
  local sdk="${ANDROID_SDK_ROOT:-${ANDROID_HOME:-}}"
  if [[ -n "${sdk}" ]]; then
    # newest build-tools first
    local found
    found="$(find "${sdk}/build-tools" -maxdepth 2 -name "${name}" 2>/dev/null | sort -V | tail -n1)"
    if [[ -n "${found}" ]]; then
      echo "${found}"
      return 0
    fi
  fi
  return 1
}

PERMS=""
if TOOL="$(find_tool aapt2)"; then
  PERMS="$("${TOOL}" dump permissions "${APK}")"
elif TOOL="$(find_tool aapt)"; then
  PERMS="$("${TOOL}" dump permissions "${APK}")"
else
  echo "::error::Neither aapt2 nor aapt found (set ANDROID_SDK_ROOT or add build-tools to PATH)." >&2
  exit 1
fi

if grep -q "android.permission.health" <<<"${PERMS}"; then
  HAS_HEALTH=1
else
  HAS_HEALTH=0
fi

case "${MODE}" in
  absent)
    if [[ "${HAS_HEALTH}" -eq 1 ]]; then
      echo "::error::Play build unexpectedly declares Health Connect permissions:" >&2
      grep "android.permission.health" <<<"${PERMS}" >&2 || true
      echo "The Play flavor must ship HC-free (AP-HC Option A)." >&2
      exit 1
    fi
    echo "OK: ${APK} declares no android.permission.health.* (Play HC-free)."
    ;;
  present)
    if [[ "${HAS_HEALTH}" -eq 0 ]]; then
      echo "::error::Sideload build is missing Health Connect permissions — HC was stripped from the wrong flavor." >&2
      exit 1
    fi
    echo "OK: ${APK} declares Health Connect permissions (sideload keeps HC)."
    grep "android.permission.health" <<<"${PERMS}" || true
    ;;
  *)
    echo "::error::Unknown mode '${MODE}' (expected absent|present)." >&2
    exit 1
    ;;
esac

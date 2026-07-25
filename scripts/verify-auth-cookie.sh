#!/usr/bin/env bash
#
# verify-auth-cookie.sh — deploy-time auth-cookie self-test (ADR-0040).
#
# Confirms the login session cookie survives the edge:
#   1. POST /auth/login returns 200
#   2. the response carries a Set-Cookie header
#   3. the cookie is accepted, so GET /auth/me returns 200
#
# A green run means login persists the session. A red run pinpoints which step
# breaks — the failure the landing-page login otherwise mislabels as
# "E-Mail oder Passwort ist falsch".
#
# Usage:
#   scripts/verify-auth-cookie.sh
#   BASE_URL=https://correlcore.com scripts/verify-auth-cookie.sh
#   BASE_URL=https://app.correlcore.com EMAIL=you@example.com scripts/verify-auth-cookie.sh
#
# EMAIL may be passed via env or entered interactively.
# PASSWORD is read interactively unless exported (export avoids shell history).
# The password is never written to disk; a temp cookie jar is used and removed.
#
# Requires: curl.

set -euo pipefail

BASE_URL="${BASE_URL:-https://correlcore.com}"
API="${BASE_URL%/}/api/v1"

if [ -z "${EMAIL:-}" ]; then
  read -rp "E-Mail: " EMAIL
fi
if [ -z "${PASSWORD:-}" ]; then
  read -rsp "Passwort: " PASSWORD
  echo
fi

JAR="$(mktemp)"
HDR="$(mktemp)"
trap 'rm -f "$JAR" "$HDR"' EXIT

# Build the JSON body without exposing the password on the process list.
body=$(printf '{"email":"%s","password":"%s","remember_me":true}' "$EMAIL" "$PASSWORD")

echo "→ POST $API/auth/login"
login_status=$(curl -sS -o /dev/null -D "$HDR" -c "$JAR" -w '%{http_code}' \
  -X POST "$API/auth/login" \
  -H 'Content-Type: application/json' \
  --data "$body")

# Count Set-Cookie headers without printing their (secret) values.
set_cookie=$(grep -ic '^set-cookie:' "$HDR" || true)

echo "→ GET  $API/auth/me"
me_status=$(curl -sS -o /dev/null -b "$JAR" -w '%{http_code}' "$API/auth/me")

echo
echo "  login    HTTP $login_status"
echo "  Set-Cookie on login response: $set_cookie header(s)"
echo "  me       HTTP $me_status"
echo

if [ "$login_status" = "200" ] && [ "${set_cookie:-0}" -ge 1 ] && [ "$me_status" = "200" ]; then
  echo "PASS — auth cookie round-trip works. Login persists the session."
  exit 0
fi

echo "FAIL — the session cookie is not surviving the edge:"
if [ "$login_status" != "200" ]; then
  echo "  • login returned $login_status (not 200) → credentials/backend issue,"
  echo "    NOT the cookie path. Check the account exists in THIS deployment's DB."
elif [ "${set_cookie:-0}" -lt 1 ]; then
  echo "  • login was 200 but NO Set-Cookie reached the client → the edge/proxy"
  echo "    strips it. Ensure every proxy location includes"
  echo "    correlcore-proxy-params.conf and does NOT set 'proxy_hide_header"
  echo "    Set-Cookie'. See ADR-0040 and infra/nginx/."
else
  echo "  • Set-Cookie was sent but /auth/me is $me_status → the browser/jar did"
  echo "    not resend it. Check COOKIE_SECURE vs scheme, X-Forwarded-Proto=https,"
  echo "    and that /api stays same-origin with the app."
fi
exit 1

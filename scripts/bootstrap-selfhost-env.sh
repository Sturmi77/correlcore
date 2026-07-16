#!/usr/bin/env bash
# Generate secrets and bootstrap .env for CorrelCore selfhost stacks.
#
# Usage:
#   scripts/bootstrap-selfhost-env.sh --quickstart   # homelab eval (infra/docker/.env)
#   scripts/bootstrap-selfhost-env.sh --production   # hint only; production needs manual DOMAIN/SMTP
#
# Idempotent: will not overwrite an existing .env unless --force is passed.

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DOCKER_DIR="${ROOT}/infra/docker"
FORCE=0
MODE=""

usage() {
  echo "Usage: $0 --quickstart [--force] | --production [--force]"
  exit 1
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --quickstart) MODE=quickstart; shift ;;
    --production) MODE=production; shift ;;
    --force) FORCE=1; shift ;;
    -h|--help) usage ;;
    *) echo "Unknown option: $1"; usage ;;
  esac
done

[[ -n "$MODE" ]] || usage

gen_urlsafe() {
  python3 -c 'import secrets; print(secrets.token_urlsafe('"$1"'))'
}

gen_fernet() {
  python3 -c 'from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())'
}

write_quickstart_env() {
  local env_file="${DOCKER_DIR}/.env"
  local example="${DOCKER_DIR}/.env.quickstart.example"

  if [[ -f "$env_file" && "$FORCE" -ne 1 ]]; then
    echo "Refusing to overwrite ${env_file} (use --force)."
    exit 1
  fi

  if [[ ! -f "$example" ]]; then
    echo "Missing ${example}"
    exit 1
  fi

  local ts_ip="${TAILSCALE_IP:-127.0.0.1}"
  local web_port="${WEB_HOST_PORT:-3010}"
  local pg_pass app_pass redis_pass secret_key enc_key slug_hmac_key

  pg_pass="$(gen_urlsafe 24)"
  app_pass="$(gen_urlsafe 24)"
  redis_pass="$(gen_urlsafe 24)"
  secret_key="$(gen_urlsafe 48)"
  enc_key="$(gen_fernet)"
  slug_hmac_key="$(python3 -c 'import secrets; print(secrets.token_hex(32))')"

  cp "$example" "$env_file"

  sed -i "s|^POSTGRES_PASSWORD=.*|POSTGRES_PASSWORD=${pg_pass}|" "$env_file"
  sed -i "s|^APP_DB_PASSWORD=.*|APP_DB_PASSWORD=${app_pass}|" "$env_file"
  sed -i "s|^REDIS_PASSWORD=.*|REDIS_PASSWORD=${redis_pass}|" "$env_file"
  sed -i "s|^SECRET_KEY=.*|SECRET_KEY=${secret_key}|" "$env_file"
  sed -i "s|^ENCRYPTION_KEY=.*|ENCRYPTION_KEY=${enc_key}|" "$env_file"
  sed -i "s|^SLUG_HMAC_KEY=.*|SLUG_HMAC_KEY=${slug_hmac_key}|" "$env_file"
  sed -i "s|^TAILSCALE_IP=.*|TAILSCALE_IP=${ts_ip}|" "$env_file"
  sed -i "s|^WEB_HOST_PORT=.*|WEB_HOST_PORT=${web_port}|" "$env_file"
  sed -i "s|^CORS_ORIGINS=.*|CORS_ORIGINS=http://${ts_ip}:${web_port}|" "$env_file"
  sed -i "s|^FRONTEND_BASE_URL=.*|FRONTEND_BASE_URL=http://${ts_ip}:${web_port}|" "$env_file"

  echo "Wrote ${env_file} (quickstart secrets generated)."
  echo ""
  echo "Store ENCRYPTION_KEY offline — required to decrypt health data from backups:"
  echo "  ENCRYPTION_KEY=${enc_key}"
  echo ""
  echo "Next:"
  echo "  cd infra/docker"
  echo "  docker compose -f docker-compose.quickstart.yml up -d"
  echo ""
  echo "Mailpit UI: http://${ts_ip}:8025"
  echo "App:        http://${ts_ip}:${web_port}"
  echo ""
  echo "For insights + cleanup, add to .env: COMPOSE_PROFILES=worker"
}

write_production_hint() {
  local env_file="${DOCKER_DIR}/.env"
  local example="${DOCKER_DIR}/.env.example"

  if [[ -f "$env_file" && "$FORCE" -ne 1 ]]; then
    echo "Refusing to overwrite ${env_file} (use --force)."
    exit 1
  fi

  cp "$example" "$env_file"

  local pg_pass app_pass redis_pass secret_key enc_key slug_hmac_key
  pg_pass="$(gen_urlsafe 24)"
  app_pass="$(gen_urlsafe 24)"
  redis_pass="$(gen_urlsafe 24)"
  secret_key="$(gen_urlsafe 48)"
  enc_key="$(gen_fernet)"
  slug_hmac_key="$(python3 -c 'import secrets; print(secrets.token_hex(32))')"

  sed -i "s|^POSTGRES_PASSWORD=.*|POSTGRES_PASSWORD=${pg_pass}|" "$env_file"
  sed -i "s|^APP_DB_PASSWORD=.*|APP_DB_PASSWORD=${app_pass}|" "$env_file"
  sed -i "s|^REDIS_PASSWORD=.*|REDIS_PASSWORD=${redis_pass}|" "$env_file"
  sed -i "s|^SECRET_KEY=.*|SECRET_KEY=${secret_key}|" "$env_file"
  sed -i "s|^ENCRYPTION_KEY=.*|ENCRYPTION_KEY=${enc_key}|" "$env_file"
  sed -i "s|^SLUG_HMAC_KEY=.*|SLUG_HMAC_KEY=${slug_hmac_key}|" "$env_file"

  echo "Wrote ${env_file} from .env.example with generated secrets."
  echo ""
  echo "You MUST still set manually before production deploy:"
  echo "  DOMAIN, LETSENCRYPT_EMAIL (traefik/traefik.yml), FRONTEND_BASE_URL, CORS_ORIGINS, SMTP_*"
  echo ""
  echo "Store ENCRYPTION_KEY offline:"
  echo "  ENCRYPTION_KEY=${enc_key}"
  echo ""
  echo "Next: cd infra/docker && docker compose up -d"
}

case "$MODE" in
  quickstart) write_quickstart_env ;;
  production) write_production_hint ;;
esac

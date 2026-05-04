# Changelog

Alle signifikanten Änderungen werden hier dokumentiert.
Format basiert auf [Keep a Changelog](https://keepachangelog.com/).
Versionierung nach [Semantic Versioning](https://semver.org/).

---

## [Unreleased] — M1 Vorbereitung

### Fixed

- `infra/docker/.env.example` und `infra/docker/docker-compose.yml` konsistent mit `backend/app/core/config.py` gemacht (Issue #41):
  - MinIO-Env-Vars im API/Worker-Service vereinheitlicht (`MINIO_ENDPOINT`/`MINIO_ACCESS_KEY`/`MINIO_SECRET_KEY`/`MINIO_BUCKET_PHOTOS`/`MINIO_SECURE` statt der nirgends gelesenen `S3_*`-Variablen)
  - SMTP-Schema (`SMTP_HOST`/`SMTP_PORT`/`SMTP_USER`/`SMTP_PASSWORD`/`SMTP_FROM`) in `.env.example` dokumentiert (statt nicht gelesenem `EMAIL_URL`/`FROM_EMAIL`)
  - `CORS_ORIGINS`, `APP_VERSION`, `DEBUG`, `JWT_ALGORITHM` in `.env.example` ergänzt
  - Compose erzwingt jetzt explizit `ENCRYPTION_KEY` als Pflichtvariable (`:?error`)
  - Anmerkung: Der ursprüngliche `SECRET_KEY`/`JWT_SECRET`-Mismatch war bereits durch `AliasChoices` in `config.py` behoben — Restscope war Vollständigkeits-Check

## [0.6.0] — M0 Fundament — 2026-04-28

### Added

- Initiales Monorepo-Setup
- Docker Compose Stack (Traefik, FastAPI, SvelteKit, PostgreSQL, Redis, MinIO)
- Authentik OIDC-Integration
- Basis-Dokumentation: DESIGN_DOCUMENT, ARCHITECTURE, API, FRONTEND, MARKET_ANALYSIS
- Architecture Decision Records (ADR) Framework
- `.env.example` für Selfhost-Setup
- GitHub Issue-Templates
- CONTRIBUTING.md

### Infrastructure

- Verzeichnisstruktur: `apps/web`, `apps/android`, `backend/app`, `backend/migrations`, `backend/workers`, `infra/docker`, `docs/adr`

---

_Nächstes Release: M1 — Core Entry (Täglicher Eintrag, Tags, Symptome, Offline-Sync)_

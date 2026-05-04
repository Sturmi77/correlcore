# Changelog

Alle signifikanten Änderungen werden hier dokumentiert.
Format basiert auf [Keep a Changelog](https://keepachangelog.com/).
Versionierung nach [Semantic Versioning](https://semver.org/).

---

## [Unreleased] — M1 Vorbereitung

### Added

- E-Mail-Verifikation komplett umgesetzt (Issue #39): `POST /api/v1/auth/verify-email`,
  `POST /api/v1/auth/resend-verification` (rate-limitiert 3/min/IP), Single-Use-Token
  in neuer Tabelle `email_verification_tokens` mit SHA-256-Hash + 24h TTL (ADR-0004).
  `POST /api/v1/auth/register` versendet Verify-Mail asynchron via BackgroundTask.
- MailPit-Service in `infra/docker/docker-compose.yml` als Dev/Test-SMTP-Catcher
  (Web-UI an `127.0.0.1:8025`, kein externer Zugriff).
- Verify-Mail-Templates (HTML + Plain-Text) in `backend/app/templates/email/`,
  ohne Tracking-Pixel und ohne externe Assets (DSGVO).
- `aiosmtplib`-basierter Async-`EmailService` ersetzt sync `emails`-Lib.
- Migration `002_create_email_verification_tokens.sql` (Cascade-Delete bei User-Erasure).
- API.md: vollständige Auth-Endpoint-Dokumentation; Phase-1-Native-JWT vs.
  Phase-2-OIDC-Block sauber getrennt (war zuvor inkonsistent).

### Fixed

- `infra/docker/.env.example` und `infra/docker/docker-compose.yml` konsistent mit `backend/app/core/config.py` gemacht (Issue #41):
  - MinIO-Env-Vars im API/Worker-Service vereinheitlicht (`MINIO_ENDPOINT`/`MINIO_ACCESS_KEY`/`MINIO_SECRET_KEY`/`MINIO_BUCKET_PHOTOS`/`MINIO_SECURE` statt der nirgends gelesenen `S3_*`-Variablen)
  - SMTP-Schema (`SMTP_HOST`/`SMTP_PORT`/`SMTP_USER`/`SMTP_PASSWORD`/`SMTP_FROM`) in `.env.example` dokumentiert (statt nicht gelesenem `EMAIL_URL`/`FROM_EMAIL`)
  - `CORS_ORIGINS`, `APP_VERSION`, `DEBUG`, `JWT_ALGORITHM` in `.env.example` ergänzt
  - Compose erzwingt jetzt explizit `ENCRYPTION_KEY` als Pflichtvariable (`:?error`)
  - Anmerkung: Der ursprüngliche `SECRET_KEY`/`JWT_SECRET`-Mismatch war bereits durch `AliasChoices` in `config.py` behoben — Restscope war Vollständigkeits-Check

### Security

- Verify-Endpoint gibt einheitlich `Invalid or expired verification token` (kein
  Detail über Ursache) — verhindert Enumeration.
- Resend-Endpoint antwortet immer mit generischem 202 — verhindert E-Mail-Enumeration.
- Plaintext-Token wird nie persistiert, nur SHA-256-Hash; Token-Versand ausschließlich über Mail.

---

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

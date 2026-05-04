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

### Security

- Verify-Endpoint gibt einheitlich `Invalid or expired verification token` (kein
  Detail über Ursache) — verhindert Enumeration.
- Resend-Endpoint antwortet immer mit generischem 202 — verhindert E-Mail-Enumeration.
- Plaintext-Token wird nie persistiert, nur SHA-256-Hash; Token-Versand ausschließlich über Mail.

---

## [0.6.0] — 2026-04-28 (M0 Fundament)

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

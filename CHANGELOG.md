# Changelog

Alle signifikanten Änderungen werden hier dokumentiert.
Format basiert auf [Keep a Changelog](https://keepachangelog.com/).
Versionierung nach [Semantic Versioning](https://semver.org/).

---

## [Unreleased] — M1 Core Auth & Entry

### Added

- **Frontend-Auth-Flow** (Issue #40):
  - Zentraler `apiFetch`-Client mit `credentials: 'include'` + Single-Flight-Refresh auf 401.
  - Auth-API-Modul (`register`, `login`, `logout`, `fetchCurrentUser`, `verifyEmail`, `resendVerification`).
  - Auth-Store (`loading | authenticated | anonymous`) mit `hydrate()`, abgeleitete Stores (`currentUser`, `isAuthenticated`).
  - Routen: `/auth/login`, `/auth/register`, `/auth/check-email`, `/auth/verify-email`, `/auth/resend-verification`.
  - Auth-Layout für `/auth/*` (zentriert, ohne Hauptnavigation).
  - Reaktiver Auth-Guard im Root-Layout: Redirect auf `/auth/login?next=…` für geschützte Routen.
  - Verify-Page mit explizitem Confirm-Button (kein Auto-Submit — Schutz gegen Mail-Scanner).
  - Password-Strength-Indicator (Score 0–4, Live-Validierung gegen Backend-Regeln).
  - i18n-Strings für Auth-Flow (de/en).
  - Vitest-Suite: 24 Tests für Client, Store und Password-Strength.

## [Unreleased] — M0 Fundament

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

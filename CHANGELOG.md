# Changelog

Alle signifikanten Änderungen werden hier dokumentiert.
Format basiert auf [Keep a Changelog](https://keepachangelog.com/).
Versionierung nach [Semantic Versioning](https://semver.org/).

---

## [Unreleased] — M1 Vorbereitung

### Documentation

- ADR-0005 (Verschlüsselung at-rest) re-evaluiert und nachgeschärft (2026-05-04):
  - Bedrohungsmodell-Tabelle hinzugefügt
  - Begründung gegen pgcrypto explizit dokumentiert (Connection-Pool-Risiko, teure Key-Rotation, pro-User-Key-Overhead)
  - Konkretes Schlüssel-Rotationsverfahren via `MultiFernet.rotate()` mit Code-Skizze
  - Datenmodell-Erweiterung `user_encryption_keys` definiert (KEK/DEK-Pattern)
  - Cryptographic-Erasure-Hinweis für Account-Löschung (Art. 17 DSGVO)
- DESIGN_DOCUMENT.md: D-011 von „Offen“ auf „Entschieden“ gesetzt; DSGVO-01 als entschieden markiert; Version 0.7

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

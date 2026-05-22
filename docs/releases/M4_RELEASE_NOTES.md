# M4 Release Notes

Stand: 2026-05-22

## Highlights

- CI-Hardening für API und Web:
  - Backend-Lint, Format, Typecheck, voller Pytest-Lauf mit Coverage.
  - Alembic-Smoke gegen echten Postgres inklusive Downgrade-/Upgrade-Roundtrip.
  - Readiness-Smoke gegen echte Postgres- und Redis-Services plus Encryption-Check.
  - Frontend-Lint, Typecheck, Unit-Tests, Build und Playwright-Smoke.
  - Gitleaks-Secret-Scan als eigenes Security-Gate.
- Playwright-Smoke deckt die M4-Kernflüsse ab:
  - Login mit Redirect in einen geschützten Flow.
  - Entry-Erstellung über Autosave.
  - Trends- und Insights-Ansichten für authentifizierte Nutzer.
- Security-Re-Audit nach Sprint-1- bis Sprint-3-Fixes:
  - Keine offenen High/Critical-Findings.
  - SQL-Injection-, Auth/Cookie-, RLS-, Secret- und Proxy-Header-Pfade erneut geprüft.
- Dokumentationsstand für M4:
  - Release-Readiness, Go/No-Go-Kriterien und bekannte Einschränkungen sind dokumentiert.

## Bekannte Einschränkungen

- Offline/PWA ist in M4 noch kein vollständiger Offline-first-Sync. Das Manifest ist vorhanden; Sync-/Conflict-Handling bleibt nach M4.
- Attachment-/EXIF-Verarbeitung ist nicht produktiv aktiviert und muss vor Aktivierung erneut sicherheitsgeprüft werden.
- OpenAPI TypeScript Client ist noch nicht eingeführt. API-/Frontend-Verträge werden für M4 über zentrale Konstanten und Contract-Tests abgesichert.
- Lokale Entwicklerumgebungen können weiterhin weniger Gates ausführen als CI, wenn Docker, Gitleaks, Playwright-Browser oder externe Services fehlen.

## Upgrade-/Deploy-Hinweise

- `pnpm install --frozen-lockfile` installiert nun auch `@playwright/test`.
- Für lokale E2E-Tests muss Chromium einmalig installiert sein:
  `pnpm --filter @correlcore/web exec playwright install chromium`
- Der Backend-Health-Integrationstest ist lokal opt-in:
  `CORRELCORE_RUN_INTEGRATION=1` plus laufende PostgreSQL- und Redis-Services.
- Vor Release müssen die GitHub Actions `CI - API`, `CI - Web` und `CI - Security` grün sein.

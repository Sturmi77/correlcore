# M4 Release Readiness

Stand: 2026-05-25

## Zielbild

M4 ist releasebereit, wenn die Kernflüsse lokal und in CI regressionssicher
laufen, keine offenen High/Critical-Security-Findings vorliegen und die
verbleibenden Einschränkungen bewusst akzeptiert sind.

## Go/No-Go-Checkliste

| Gate                    | Status           | Evidenz                                                                                                 |
| ----------------------- | ---------------- | ------------------------------------------------------------------------------------------------------- |
| Backend Lint/Format     | Go, wenn CI grün | `ci-api.yml`: `ruff check .`, `ruff format --check .`                                                   |
| Backend Typecheck       | Go, wenn CI grün | `ci-api.yml`: `mypy app`                                                                                |
| Backend Tests           | Go, wenn CI grün | `ci-api.yml`: voller `pytest` mit Coverage-Gate                                                         |
| Migrationen             | Go, wenn CI grün | `migrations-smoke`: `alembic upgrade head`, `downgrade base`, erneutes `upgrade head` gegen Postgres 16 |
| Backend Health          | Go, wenn CI grün | `health-smoke`: echte Postgres- und Redis-Services plus Encryption-Readiness                            |
| Frontend Lint/Typecheck | Go, wenn CI grün | `ci-web.yml`: `pnpm lint`, `pnpm typecheck`                                                             |
| Frontend Unit Tests     | Go, wenn CI grün | `ci-web.yml`: `pnpm test`                                                                               |
| Frontend Build          | Go, wenn CI grün | `ci-web.yml`: `pnpm build` mit `/api/v1`                                                                |
| E2E Smoke               | Go, wenn CI grün | Playwright-Smoke für Login, Entry-Autosave, Trends und Insights                                         |
| Secret Scan             | Go, wenn CI grün | `ci-security.yml`: Gitleaks gegen Working Tree und Git-History                                          |
| Security Re-Audit       | Go               | Keine validierten High/Critical-Kandidaten im Sprint-4-Review                                           |
| Release Notes           | Go               | `docs/releases/M4_RELEASE_NOTES.md`                                                                     |

No-Go-Kriterien:

- Ein High/Critical-Security-Finding ist offen oder nicht bewertet.
- Migration-Smoke oder Health-Smoke schlagen in CI fehl.
- Login, Entry-Erstellung oder Insights/Trends können im E2E-Smoke nicht geladen werden.
- Secret-Scan findet ein echtes Secret.
- Ein Dokument widerspricht bewusst dem Ist-Stand, ohne als Soll/Restthema markiert zu sein.

## Lokale Verifikation

Ausgeführt am 2026-05-22:

| Check                   | Ergebnis                | Hinweis                                                           |
| ----------------------- | ----------------------- | ----------------------------------------------------------------- |
| Backend Lint            | Pass                    | `ruff check app tests migrations`                                 |
| Backend Format          | Pass                    | `ruff format --check app tests migrations`                        |
| Backend Typecheck       | Pass                    | `mypy app`                                                        |
| Backend Tests           | Pass                    | `396 passed, 1 skipped` mit `pytest -q --no-cov`                  |
| Health Integration      | Lokal skipped, CI aktiv | `CORRELCORE_RUN_INTEGRATION=1` läuft in CI mit Postgres und Redis |
| Frontend Lint           | Pass                    | `eslint apps/web`                                                 |
| Frontend Typecheck      | Pass                    | `svelte-check --tsconfig ./tsconfig.json`                         |
| Frontend Unit Tests     | Pass                    | `327 passed` mit `vitest run --passWithNoTests`                   |
| Frontend Build          | Pass                    | `vite build`                                                      |
| Playwright E2E Smoke    | Pass                    | `3 passed`: Login, Entry-Autosave, Trends/Insights                |
| Geänderte Formatfiles   | Pass                    | Prettier-Check auf Sprint-4-Änderungsumfang                       |
| Whitespace/Diff-Hygiene | Pass                    | `git diff --check` ohne Whitespace-Fehler                         |
| Lokaler Secret-Scan     | Pass                    | Regex-Scan ohne Treffer; Gitleaks bleibt verbindliches CI-Gate    |

## Security Re-Audit

### Threat Model

Schützenswerte Assets:

- Gesundheits- und Stimmungsdaten in Entries, Tags, Symptomen, Insights und Exporten.
- Authentifizierungszustand in HttpOnly-Cookies und Redis-Refresh-Token-Store.
- App-Level-Verschlüsselung: Master-Key, gewrappte User-DEKs und Request-gebundene DEKs.
- Tenant-Isolation über `user_id`, Service-Layer-Checks und PostgreSQL RLS.
- CI/CD-Integrität inklusive Lockfiles, Container-Builds und Secret-Scan.

Wichtige Trust Boundaries:

- Browser zu SvelteKit-Web-Container.
- SvelteKit-Proxy zu FastAPI.
- FastAPI zu PostgreSQL/Redis/SMTP.
- Authentifizierter User zu fremden User-Daten.
- CI-Ausführung zu Repository-Secrets und Artefakten.

Attacker-kontrollierte Inputs:

- Auth-Payloads, Entry-/Tag-/Symptom-/Profile-Payloads, Query-Parameter, Export/Delete-Requests.
- Cookies und weitergeleitete Proxy-Header aus dem Browser; der Web-Proxy überschreibt Forwarding-Header.
- Upload-/Attachment-Daten sind für M4 noch kein produktiver Runtime-Pfad.

### Discovery & Validation Summary

| Bereich                   | Ergebnis                                                                                                                                                                                           |
| ------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| SQL Injection             | Keine plausible SQLi-Kandidatur gefunden. Runtime-Code nutzt SQLAlchemy-Statements und gebundene Parameter. Dynamische SQL-Treffer sind migrationsinterne, konstante Tabellennamen aus Allowlists. |
| Auth/Cookies/CSRF         | Access- und Refresh-Cookies sind HttpOnly, SameSite=Strict und in Production Secure. Refresh-Cookie ist auf `/api/v1/auth/refresh` beschränkt.                                                     |
| Tenant-Isolation          | RLS wird per `app.current_user_id` gebunden; Migration 012 erzwingt RLS für User-Datentabellen. Service-Layer filtert zusätzlich nach `user_id`.                                                   |
| Secrets                   | Lokaler Regex-Scan auf private Keys, GitHub/OpenAI/Slack/AWS-Token und direkte `secret/password/token = "..."`-Muster ohne Treffer. Gitleaks bleibt CI-Gate.                                       |
| SSRF/RCE/Deserialisierung | Keine erreichbaren `subprocess`, `eval`, unsichere Deserialisierung oder ausgehenden HTTP-Request-Sinks in produktiven API-Pfaden gefunden.                                                        |
| Upload/EXIF/Attachments   | Kein produktiver Attachment-/EXIF-Verarbeitungspfad in M4. Das bleibt bewusst ein späteres Design-/Implementierungsthema.                                                                          |
| Logging                   | Relevante Services loggen IDs und Exception-Klassen, nicht Freitext-Gesundheitsdaten oder Secret-Werte.                                                                                            |

Bewertung: Es gibt nach diesem Re-Audit keine offenen High/Critical Findings.
Die Aussage ist eine code- und konfigurierte-CI-basierte Bewertung, kein
Ersatz für einen externen Penetrationstest gegen eine produktive Umgebung.

## Bekannte Restthemen

| Priorität | Thema                                                             | Entscheidung für M4                                                                                                   |
| --------- | ----------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------- |
| P1        | Externer Penetrationstest gegen Staging/Production                | Nicht Blocker für internen M4, Blocker vor öffentlicher Beta.                                                         |
| P1        | Gitleaks lokal nicht überall verfügbar                            | CI-Gate ist maßgeblich; lokale Entwickler können Gitleaks optional installieren.                                      |
| P2        | Dependency-Audit mit `pip-audit`/`pnpm audit` als eigenes CI-Gate | Für M4 dokumentiert, nach M4 als Security-Backlog ergänzen.                                                           |
| P2        | OpenAPI TypeScript Client                                         | Contract-Test und zentrale Contract-Konstanten decken M4 ab; echte Client-Generation bleibt evaluiertes Folgeprojekt. |
| P2        | Offline/PWA                                                       | M4 dokumentiert ehrlich: Manifest vorhanden, kein vollständiges Offline-first/Sync.                                   |
| P3        | Attachment/EXIF/Audit-Log                                         | Kein produktiver M4-Pfad; vor Aktivierung eigener Upload-Flows erneut auditieren.                                     |

### Meilenstein-Zuordnung der Restthemen

Die folgenden Punkte bleiben bewusst offen, sind aber einem Zielmeilenstein
oder einem verbindlichen Gate zugeordnet:

| Priorität | Thema                                                                                | Ziel / Link                                                                        | M4-Entscheidung                                                                                                       |
| --------- | ------------------------------------------------------------------------------------ | ---------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------- |
| P1        | Externer Penetrationstest gegen Staging/Production                                   | [M9 Beta-Härtung](../DESIGN_DOCUMENT.md#m9--beta-h%C3%A4rtung-woche-2224)          | Nicht Blocker für internen M4, Blocker vor öffentlicher Beta.                                                         |
| P1        | Lokaler Gitleaks-Scan nicht überall verfügbar                                        | [CI - Security](../../.github/workflows/ci-security.yml)                           | CI-Gate ist maßgeblich; lokale Entwickler können Gitleaks optional installieren.                                      |
| P2        | Dependency-Audit mit `pip-audit`/`pnpm audit` als eigenes CI-Gate                    | [M9 Beta-Härtung](../DESIGN_DOCUMENT.md#m9--beta-h%C3%A4rtung-woche-2224)          | Für M4 dokumentiert, nach M4 als Security-Backlog ergänzen.                                                           |
| P2        | OpenAPI TypeScript Client                                                            | [API Contract Strategy](../API_CONTRACTS.md)                                       | Contract-Test und zentrale Contract-Konstanten decken M4 ab; echte Client-Generation bleibt evaluiertes Folgeprojekt. |
| P2        | Vollständiger Offline-first/PWA-Sync                                                 | [M4 Mobile/PWA](../DESIGN_DOCUMENT.md#m4--mobile-polish--pwa-hardening-woche-1112) | M4 dokumentiert ehrlich: Manifest vorhanden, kein vollständiges Offline-first/Sync.                                   |
| P2        | Mobile Screenshot-QA für Home, Entry Sheet, Insights, Trends und Settings bei 375 px | [M4 Mobile/PWA](../DESIGN_DOCUMENT.md#m4--mobile-polish--pwa-hardening-woche-1112) | Nicht Blocker für diesen UI-Hardening-Push, solange Playwright-Smoke, Browser-QA und CI grün bleiben.                 |
| P2        | Vollständige Ablösung route-lokaler Button-Klassen durch Common-Primitives           | [Frontend Component System](../frontend/UI_COMPONENT_SYSTEM.md#migration-backlog)  | Begonnen in Sprints B-E; weitere Ersetzung bleibt Follow-up für Mobile-Hardening.                                     |
| P2        | Style-Contract/Lint für unbekannte Design-Tokens und Varianten                       | [M9 Beta-Härtung](../DESIGN_DOCUMENT.md#m9--beta-h%C3%A4rtung-woche-2224)          | Nach M4 als Qualitäts-Guardrail ergänzen.                                                                             |
| P3        | Attachment/EXIF/Audit-Log                                                            | [M6 Fotos & Medien](../DESIGN_DOCUMENT.md#m6--fotos--medien-woche-1516)            | Kein produktiver M4-Pfad; vor Aktivierung eigener Upload-Flows erneut auditieren.                                     |

## Release-Entscheidung

Empfehlung: Go für M4, sobald die oben gelisteten CI-Gates grün sind.

Bewusst akzeptiert werden für M4:

- Keine vollständige Offline-first-Synchronisation.
- Keine produktive Attachment-/EXIF-Pipeline.
- Kein generierter OpenAPI-Client, solange Contract-Test und geteilte Konstanten grün bleiben.
- Security-Re-Audit ist intern; externer Pentest bleibt vor breiterer Verteilung sinnvoll.

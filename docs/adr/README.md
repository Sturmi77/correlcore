# Architecture Decision Records (ADR)

Jede signifikante Architekturentscheidung wird hier als ADR dokumentiert.

## Format

Dateiname: `NNNN-kurzer-titel.md`
Status: `Vorgeschlagen | Accepted | Abgelehnt | Ersetzt durch ADR-XXXX`

## Index

| ADR                                                     | Titel                                                       | Status   | Datum      |
| ------------------------------------------------------- | ----------------------------------------------------------- | -------- | ---------- |
| [ADR-0001](0001-sveltekit-vs-nextjs.md)                 | SvelteKit als Web-Framework (statt Next.js)                 | Accepted | –          |
| [ADR-0002](0002-capacitor-statt-twa.md)                 | Capacitor statt TWA als Mobile-Strategie                    | Accepted | 2026-04-20 |
| [ADR-0003](0003-sync-conflict-log.md)                   | Sync-Protokoll: Conflict-Log statt stilles LWW              | Accepted | 2026-04-20 |
| [ADR-0004](0004-auth-strategie.md)                      | Auth-Strategie: Native JWT in Phase 1, Authentik ab Phase 2 | Accepted | 2026-04-20 |
| [ADR-0005](0005-verschluesselung-at-rest.md)            | Datenverschlüsselung at-rest: Zweistufige Strategie         | Accepted | 2026-04-20 |
| [ADR-0006](0006-cookie-auth-mit-capacitor-migration.md) | Cookie-Auth im Web mit geplanter Capacitor-Bearer-Migration | Accepted | 2026-05-04 |
| [ADR-0007](0007-healthchecks-and-logging.md)            | Healthchecks und strukturiertes Logging                     | Accepted | 2026-05-04 |
| [ADR-0008](0008-symptom-master-tabelle.md)              | Symptom-Master-Tabelle für Custom-Symptome                  | Accepted | 2026-05-04 |

## Kurzübersicht der Entscheidungen

### ADR-0001 – SvelteKit als Web-Framework

SvelteKit wird gegenüber Next.js bevorzugt: kleinere Bundle-Größen, bessere PWA-Integration, kein React-Overhead.

### ADR-0002 – Capacitor statt TWA

TWA/Bubblewrap wird aufgegeben. Capacitor wrappt die SvelteKit-Codebase mit nativen Android-Bridges für Health Connect und FCM.

### ADR-0003 – Sync: LWW + Conflict-Log

Last-Write-Wins bleibt das Merge-Prinzip. Alle Konflikte werden in der Tabelle `sync_conflicts` geloggt und sind für den User in den Einstellungen einsehbar (90-Tage-Retention).

### ADR-0004 – Auth: Native JWT → Authentik

Phase 1 (Selfhost, bis M10): Native JWT Auth in FastAPI mit Refresh-Token-Rotation, HttpOnly-Cookies, Rate-Limiting und TOTP-MFA. Phase 2 (SaaS, M12+): Authentik als OIDC-Provider.

### ADR-0005 – Verschlüsselung at-rest

Zweistufig: Stufe 1 = MinIO SSE + LUKS-Volumes + HSTS (Infrastruktur, M0). Stufe 2 = App-Level Fernet-Verschlüsselung mit pro-User-Keys für `entries.note`, `entry_symptoms.details`, `insights.statement` (M1).

### ADR-0006 – Cookie-Auth im Web mit Capacitor-Migration

Phase 1 (Web): HttpOnly-Cookies (SameSite=Strict, Secure) für maximale XSS-Resistenz auf Art.-9-Daten. Phase 2 (Capacitor, M11+): In-Memory-Bearer-Token, da `capacitor://`-Cookies geblockt werden. Migration ist auf `apiFetch` lokalisiert; UI und Stores bleiben unberührt.

### ADR-0007 – Healthchecks und strukturiertes Logging

Drei-Tier-Healthchecks (`/health/live` nie 5xx, `/health/ready` 503 bei Dep-Ausfall, `/health` aggregierte Summary) verhindern Restart-Loops. JSON-Logging mit fixem Schema nach STDOUT plus Request-ID-Middleware (UUID4 oder vom Client übernommen) erlaubt Korrelation ohne externes Tracing-System. Logs enthalten niemals Art.-9-Gesundheitsdaten — abgesichert durch automatischen Log-Scrubbing-Test (`tests/test_log_scrubbing.py`).

### ADR-0008 – Symptom-Master-Tabelle für Custom-Symptome

Neue Tabelle `symptoms` analog `tags` mit Owner-Trennung (`user_id NULL = curated`, `is_default`), Slug-Uniqueness via Partial-Indexes und 4 RLS-Policies. `entry_symptoms` referenziert künftig `symptoms.id` per FK statt String-`symptom_key`. Migration 006 transformiert die fünf Standard-Keys aus PR #56 zu Default-Rows mit deterministischen UUIDs (UUID5). Erlaubt User-eigene Symptome mit gleichem CRUD-Modell wie Tags (Issue #57). DSGVO: `symptoms.name` ist Art.-9-relevant und wird mit Issue #26 (App-Level Fernet) verschlüsselt.

---

## Neue ADRs hinzufügen

1. Nächste freie Nummer ermitteln
2. Datei `NNNN-kurzer-titel.md` in diesem Verzeichnis anlegen
3. Eintrag in den Index oben sowie in die Kurzübersicht aufnehmen
4. Status initial auf `Vorgeschlagen`, nach Team-Review auf `Accepted` oder `Abgelehnt` setzen

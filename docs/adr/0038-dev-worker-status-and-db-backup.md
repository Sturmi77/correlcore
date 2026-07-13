# ADR-0038 - Developer Worker-Status und Dev-DB Backup/Restore

## Status

Akzeptiert (2026-07-13)

## Kontext

Developer Mode und `/dev` (ADR-0015, ADR-0019) konnten Deployment-Metadaten
zeigen, aber nicht, welcher Analytics-Worker zuletzt lief und mit welchem
Ergebnis. Für GUI-Validierung von Insights fehlte eine abfragbare Historie.
Gleichzeitig waren Postgres-Dumps nur dokumentiert (Selfhost/M9), nicht als
lokales Dev-Tooling bzw. gated API.

## Entscheidung

1. **Worker runs:** Neue Tabelle `worker_runs` speichert Start/Ende, Status,
   `trigger_source`, optionales `scope_user_id` und JSON-Ergebnis. Instrumentation
   in Daily Bundle, Fleet-Insights, User-Regenerate und Post-Batch.
2. **Dev API:** Unter `DEV_VIEW_ENABLED` und verified user:
   `GET /api/v1/dev/workers`, `/workers/latest`, sowie
   `POST /workers/insights/run-once` (zusätzlich nur `APP_ENV=development|test`).
3. **DB Backup/Restore:** Scripts `scripts/dev-db-*.sh` plus gated Endpoints
   `/api/v1/dev/db/backups` und `/db/restore`, nur bei
   `DEV_VIEW_ENABLED` und `APP_ENV=development|test`. Responses tragen
   `ops_ready=false` als Extension Point für späteren Betrieb.
4. **Encryption:** Dumps ohne passendes `ENCRYPTION_KEY` sind für Notes
   unbrauchbar; Meta/UI weisen darauf hin.

## Konsequenzen

- GUI auf `/dev` kann Insights gegen Run-Ergebnisse abgleichen.
- Production-Restore bleibt bewusst out of scope; kein Object-Storage, keine
  Offline-Fenster-Orchestrierung.
- Soft-Fail auf `/dev` nutzt den persistierten `devMode`-Store (ADR-0019), nicht
  mehr den orphaned in-memory `developerMode`-Store.

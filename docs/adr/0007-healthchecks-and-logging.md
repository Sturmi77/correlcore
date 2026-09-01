# ADR-0007: Healthchecks und strukturiertes Logging

**Datum:** 2026-05-04
**Status:** Accepted

---

## Kontext

CorrelCore ist eine Selfhost-Anwendung mit verteilten Komponenten (FastAPI-API, SvelteKit-Web, Worker, PostgreSQL, Redis, MinIO, Mailpit, optional Glitchtip). Ein Selfhoster ohne Vollzeit-DevOps-Team braucht zwei Dinge zuverlässig:

1. **Healthchecks**, die _zuverlässig_ unterscheiden zwischen „Container-Prozess hängt" (→ Restart sinnvoll) und „abhängiger Dienst kurzzeitig nicht erreichbar" (→ Restart wäre kontraproduktiv und verstärkt die Störung).
2. **Logs**, die ohne externes Logging-System (ELK, Loki, Datadog) auf der Kommandozeile auswertbar sind und gleichzeitig für eine spätere Aggregation strukturiert genug bleiben.

In der ersten Roadmap-Skizze war Observability als „nice to have, kommt mit M3+" geplant. Im Gap-Audit (siehe `docs/DESIGN_DOCUMENT.md`, Risiko OBS-01) wurde dies als blockierend für M0 eingestuft: ohne Healthchecks gibt es keine zuverlässige `depends_on`-Verkettung in Compose, und ohne strukturiertes Logging mit Korrelations-IDs ist Fehlersuche bei einem verteilten Stack nicht effizient möglich.

Die hier dokumentierte Entscheidung wurde im Code seit PR #35 gelebt, aber bisher nirgends als ADR festgehalten — `docs/DESIGN_DOCUMENT.md` verwies an drei Stellen auf eine `ADR-0003-healthchecks-and-logging.md`, die nie existiert hat. Dieses ADR schließt diese Doku-Lücke.

---

## Entscheidung

### 1. Healthcheck-Architektur: 3-Tier-Pattern

Drei semantisch getrennte HTTP-Endpunkte:

| Endpunkt        | Zweck                                                 | Verhalten bei Dep-Ausfall     | Konsument                                 |
| --------------- | ----------------------------------------------------- | ----------------------------- | ----------------------------------------- |
| `/health/live`  | Liveness — Prozess lebt                               | **Immer 200**, _nie_ 5xx      | Docker `HEALTHCHECK`, Kubernetes liveness |
| `/health/ready` | Readiness — alle externen Deps (DB, Redis) erreichbar | 503 bei Dep-Ausfall           | Traefik, Uptime-Kuma, K8s readiness       |
| `/health`       | Aggregierte Summary (mensch-lesbar)                   | **Immer 200**, Status im Body | Browser, Ops-Person                       |

**Begründung der Trennung:**

- Würde Liveness 5xx zurückgeben, wenn die DB kurz weg ist, würde Docker den API-Container zyklisch neu starten und damit die Recovery-Zeit der DB verlängern (Restart-Loop-Anti-Pattern).
- Readiness 503 ist hingegen genau das richtige Signal an den Reverse-Proxy: „nimm mich aus der Rotation, ich kann gerade keine Requests bedienen, aber ich bin am Leben".
- Die Summary-Variante ist eine Komfortfunktion für Menschen — `curl https://api/health` gibt eine vollständige JSON-Übersicht ohne Statuscode-Interpretation.

**Implementierung:** `backend/app/services/health_service.py` (Probes) und `backend/app/api/v1/endpoints/health.py` (Routing). Liveness ist reine Prozess-Bestätigung ohne I/O. Readiness führt einen `SELECT 1` gegen Postgres und ein `PING` gegen Redis aus, jeweils mit kurzem Timeout (2s) und Exception-Klassennamen statt Stacktrace im Response (kein Detail-Leak).

**Doppel-Mount:** `/health/live` ist sowohl unter `/api/v1/health/live` (regulär) als auch direkt unter `/health/live` (Root) erreichbar. Damit kann der Docker-`HEALTHCHECK` ohne Pfad-Präfix-Annahmen arbeiten und bleibt robust gegenüber späteren Reverse-Proxy-Rewrites.

### 2. Strukturiertes JSON-Logging

Alle API-Logs werden als einzeiliges JSON nach STDOUT geschrieben, mit einem festen Schema:

```json
{
  "timestamp": "2026-05-04T13:42:11.123Z",
  "level": "INFO",
  "service": "correlcore-api",
  "environment": "production",
  "logger": "app.api.v1.endpoints.auth",
  "request_id": "f3c4e1a2-...",
  "method": "POST",
  "path": "/api/v1/auth/login",
  "status_code": 200,
  "duration_ms": 47.3,
  "message": "request completed"
}
```

**Begründung:**

- JSON nach STDOUT ist die Container-Standard-Konvention. Docker, Podman und Kubernetes leiten STDOUT automatisch ab; spätere Aggregation in Loki/Vector benötigt keinen Code-Eingriff.
- Ein **fixes Schema** (statt freier `extra`-Felder) erlaubt sofortige Filterbarkeit per `jq`, `grep` und `awk` und macht später Loki-Label-Mappings trivial.
- `request_id`, `method`, `path`, `status_code`, `duration_ms` sind über ContextVars an den jeweiligen Request gebunden (siehe Punkt 3) und werden _automatisch_ in jedes Log-Record gesetzt — Entwickler müssen sich nicht selbst darum kümmern.
- Stacktraces werden nur bei `record.exc_info` über `traceback.format_exception()` angehängt. **Das ist die einzige Stelle, an der unkontrolliert große Strings in Logs landen können** — siehe DSGVO-Konsequenzen unten.

**Implementierung:** `backend/app/core/logging.py` (`_JsonFormatter` + `setup_logging()`). Im Production-Mode werden `sqlalchemy.engine` und `uvicorn.access` auf `WARNING` gedämpft, um Log-Spam und Query-Daten-Leaks zu vermeiden. `setup_logging()` wird einmalig im FastAPI-Lifespan aufgerufen.

### 3. Request-ID-/Correlation-ID-Middleware

Jede HTTP-Anfrage erhält eine `request_id`:

- **Erzeugung:** UUID4, **außer** der Client liefert bereits einen `X-Request-ID`-Header — dann wird dieser übernommen. So bleiben Trace-Chains von Traefik oder Capacitor-Clients erhalten.
- **Verteilung:** ContextVars (`contextvars.ContextVar`) tragen die ID asynchron-sicher durch alle Coroutines des Requests. Der `_JsonFormatter` greift sie aus den ContextVars ab — kein manuelles Durchreichen über Funktionssignaturen.
- **Rückgabe:** Die ID wird als `X-Request-ID`-Response-Header zurückgegeben, damit der Client (oder der Reverse-Proxy) sie in seinem eigenen Log mitführen kann.
- **Timing:** `duration_ms` wird mit `time.perf_counter()` (monotonic clock) gemessen, nicht mit `time.time()` — letzteres würde bei NTP-Sprüngen negative Werte erzeugen.

**Implementierung:** `backend/app/core/request_id.py` (`RequestIDMiddleware`). Wird als äußerste Middleware registriert, damit alle anderen Middlewares (CORS, RateLimit) bereits in einem Request-Kontext mit ID laufen.

### 4. Docker-Compose-Healthchecks

Jeder Long-Running-Service hat einen `healthcheck:`-Block:

| Service    | Test                                              | Hinweis                            |
| ---------- | ------------------------------------------------- | ---------------------------------- |
| `api`      | `curl -sf http://localhost:8000/health/live`      | Liveness, kein Dep-Check           |
| `web`      | `wget -qO- http://localhost:3000`                 | SvelteKit-Node-Server-Reachability |
| `postgres` | `pg_isready`                                      | Standard-Pattern                   |
| `redis`    | `redis-cli -a $REDIS_PASSWORD ping`               | Auth-Variante                      |
| `minio`    | `mc ready local`                                  | MinIO-Client                       |
| `mailpit`  | `wget --spider http://localhost:8025/api/v1/info` | Dev/Test-only                      |

Konsumenten verwenden `depends_on: { service: { condition: service_healthy } }`, damit der API-Container nicht startet, bevor Postgres und Redis bereit sind. Das verhindert Bootstrap-Race-Conditions.

**Bewusste Lücken** (ab M3 / M9 nachzuziehen):

- `worker`: Code existiert noch nicht (`backend/app/workers/` ist leer). Sobald M3 (Analytics-Worker) startet, wird ein File-basierter Liveness-Probe ergänzt: Worker schreibt alle 60s einen Timestamp in `/tmp/worker-alive`, Healthcheck prüft Alter dieser Datei.
  **Update (#756, Phase 3 Worker-Robustheit):** Der file-basierte Heartbeat wurde nie umgesetzt — stattdessen exponiert `GET /api/v1/worker/status` seit #756 Alter und Status des letzten _erfolgreichen_ Laufs pro `WorkerJobKind` (gelesen aus `worker_runs`), was den ursprünglich geplanten Container-Heartbeat als Signal ersetzt: eine reine Prozess-Liveness-Datei hätte nicht erkannt, dass der Worker zwar läuft, aber seine nächtlichen Jobs nicht mehr erfolgreich abschließt. Externe Monitore (Uptime-Kuma, healthchecks.io, GlitchTip-Cron-Monitor) pollen diesen Endpoint statt eines Docker-`healthcheck:`-Blocks auf dem Worker-Container. Mit #757 (Umstieg von Dauerprozess auf extern getriggerte `--once`-Läufe via `supercronic`) bleibt der Worker-Container bewusst ohne eigenen `healthcheck:`-Block (wie zuvor) — ein zusätzlicher Prozess-Liveness-Check (`pgrep -f supercronic`) wurde erwogen, aber verworfen, um den Compose-Diff für Self-Hoster minimal zu halten und keine zweite, redundante Signalquelle neben `/worker/status` einzuführen; `/worker/status` bleibt die alleinige Quelle für "funktioniert der Worker tatsächlich".
- `glitchtip`: Optionaler Monitoring-Service mit Profile `monitoring`. **Update (M9 Sprint 2):** Der Healthcheck wurde ergänzt (siehe Implementierungs-Status unten) — diese Lücke ist geschlossen.

### 5. Privacy-Konsequenzen (DSGVO Art. 5, Art. 32)

**Logs dürfen niemals personenbezogene Gesundheitsdaten enthalten** (Art. 9 DSGVO):

- ❌ Verboten in Logs: `mood_score`, `energy_level`, `stress_level`, Tagebuch-Notizen, Symptom-Werte, E-Mail-Adressen, Klartext-Tokens
- ✅ Erlaubt in Logs: `request_id`, `method`, `path`, `status_code`, `duration_ms`, `user_id` (UUID, kein direkter Personenbezug), Exception-Klassennamen, Stacktraces (System-Frames)

**Durchgesetzt durch drei Mechanismen:**

1. **Konvention + Code-Review:** Keine `logger.info(f"mood: {entry.mood_score}")`-Aufrufe.
2. **`sqlalchemy.engine`-Logger gedämpft:** Im Production-Mode auf `WARNING`, damit Query-Bind-Parameter nie in Logs erscheinen.
3. **Automatischer Test:** `backend/tests/test_log_scrubbing.py` simuliert einen Entry-Schreibvorgang und assertet, dass weder `mood_score`-Werte noch Notiz-Inhalte im Log-Output erscheinen (Issue M1-DSGVO-Checkpoint, Zeile 647 im DESIGN_DOCUMENT).

Stacktraces dürfen Pfade und System-Variablen enthalten, aber keine Tagebucheinträge — das wird bei jedem `logger.exception()`-Call manuell überprüft (Code-Review-Checklist).

---

## Konsequenzen

**Positiv:**

- Restart-Loop-Anti-Pattern vermieden (Liveness niemals 5xx auf Dep-Ausfall).
- Vollständige Request-Korrelation über alle Schichten ohne externes Tracing-System.
- JSON-Logs ab Tag 1 aggregierbar; späterer Loki/Vector-Anschluss ohne Code-Änderung möglich.
- DSGVO-Compliance bei Logging durch Schema-Disziplin abgesichert.

**Negativ / Trade-offs:**

- ContextVars erfordern, dass _alle_ Logger über das Standard-`logging`-Modul gehen — `print()`-Aufrufe würden die Korrelation verlieren. Wird per Lint/Code-Review durchgesetzt.
- ~~Worker- und Glitchtip-Healthchecks fehlen aktuell bewusst (siehe Punkt 4) — stellt sich erst ab M3 als Schmerzpunkt dar.~~ **Update 2026-09 (Audit Q8):** beide Lücken sind geschlossen — Worker-Liveness läuft über `GET /api/v1/worker/status` (#756/#757, bewusst kein Container-`healthcheck:`), Glitchtip hat seit M9 Sprint 2 einen Healthcheck.
- Kein `/metrics`-Prometheus-Endpoint. Bewusste Entscheidung (D-012 „schlanker Ansatz"): Selfhoster bekommt Healthchecks + Logs, Prometheus/Grafana ist Opt-in via späterer `docker-compose.ops.yml`. Nachteil: keine historischen Metriken im Default-Stack.

**Folge-ADRs:**

- _Keiner geplant._ Diese ADR ist als „Single Source of Truth" für Observability bis M9 (Beta-Härtung) gedacht. Falls dort ein vollständiger Metrics-Stack ergänzt wird, kommt ein eigener ADR-0008.

---

## Bezug zu anderen Entscheidungen

- **D-012 (Observability-Tiefe in M0):** Diese ADR ist die ausgelagerte Begründung dazu.
- **OBS-01 (Risiko aus Gap-Audit):** Mit dieser ADR und PR #35 als behoben markiert.
- **ADR-0004 (Auth):** Refresh-Token-Operationen werden als Audit-Logs ohne Token-Inhalte protokolliert — dieselbe Logging-Disziplin gilt.
- **ADR-0005 (Verschlüsselung at-rest):** Verschlüsselte Felder dürfen in keinem Code-Pfad ent-verschlüsselt geloggt werden, auch nicht zu Debugging-Zwecken.

---

## Implementierungs-Status

| Komponente                         | Datei                                           | Status                                               |
| ---------------------------------- | ----------------------------------------------- | ---------------------------------------------------- |
| Liveness/Readiness/Summary         | `backend/app/api/v1/endpoints/health.py`        | ✅ PR #35                                            |
| Probe-Service                      | `backend/app/services/health_service.py`        | ✅ PR #35                                            |
| JSON-Logging                       | `backend/app/core/logging.py`                   | ✅ PR #35                                            |
| Request-ID-Middleware              | `backend/app/core/request_id.py`                | ✅ PR #35                                            |
| Docker-Healthchecks (6 Services)   | `infra/docker/docker-compose.yml`               | ✅ PR #35                                            |
| DSGVO-Log-Scrubbing-Test           | `backend/tests/test_log_scrubbing.py`           | ✅ Diese ADR                                         |
| Worker-Liveness (`/worker/status`) | `backend/app/api/v1/endpoints/worker_status.py` | ✅ #756/#757 (bewusst kein Container-`healthcheck:`) |
| Glitchtip-Healthcheck              | `infra/docker/docker-compose.yml`               | ✅ M9 Sprint 2                                       |

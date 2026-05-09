# Architecture Decision Records (ADR)

Jede signifikante Architekturentscheidung wird hier als ADR dokumentiert.

## Format

Dateiname: `NNNN-kurzer-titel.md`
Status: `Vorgeschlagen | Accepted | Abgelehnt | Ersetzt durch ADR-XXXX`

## Index

| ADR                                                         | Titel                                                        | Status        | Datum      |
| ----------------------------------------------------------- | ------------------------------------------------------------ | ------------- | ---------- |
| [ADR-0001](0001-sveltekit-vs-nextjs.md)                     | SvelteKit als Web-Framework (statt Next.js)                  | Accepted      | –          |
| [ADR-0002](0002-capacitor-statt-twa.md)                     | Capacitor statt TWA als Mobile-Strategie                     | Accepted      | 2026-04-20 |
| [ADR-0003](0003-sync-conflict-log.md)                       | Sync-Protokoll: Conflict-Log statt stilles LWW               | Accepted      | 2026-04-20 |
| [ADR-0004](0004-auth-strategie.md)                          | Auth-Strategie: Native JWT in Phase 1, Authentik ab Phase 2  | Accepted      | 2026-04-20 |
| [ADR-0005](0005-verschluesselung-at-rest.md)                | Datenverschlüsselung at-rest: Zweistufige Strategie          | Accepted      | 2026-04-20 |
| [ADR-0006](0006-cookie-auth-mit-capacitor-migration.md)     | Cookie-Auth im Web mit geplanter Capacitor-Bearer-Migration  | Accepted      | 2026-05-04 |
| [ADR-0007](0007-healthchecks-and-logging.md)                | Healthchecks und strukturiertes Logging                      | Accepted      | 2026-05-04 |
| [ADR-0008](0008-symptom-master-tabelle.md)                  | Symptom-Master-Tabelle für Custom-Symptome                   | Accepted      | 2026-05-04 |
| [ADR-0009](0009-offline-sync-nach-m4.md)                    | Offline-Sync nach M4 verschieben (Scope-Reduktion M1)        | Accepted      | 2026-05-04 |
| [ADR-0010](0010-build-toolchain-pinning.md)                 | Build-Toolchain-Pinning (pnpm-Version)                       | Accepted      | 2026-05-07 |
| [ADR-0011](0011-web-internal-reverse-proxy.md)              | Interner Reverse-Proxy im Web-Container                      | Accepted      | 2026-05-08 |
| [ADR-0012](0012-m2-m5-streak-semantik.md)                   | M2/M5 Streak-Semantik + Habit-Schema-Vorgriff                | Vorgeschlagen | 2026-05-08 |
| [ADR-0013](0013-autosave-day-entries.md)                    | Auto-Save für Day-Entries (M1.5)                             | Akzeptiert    | 2026-05-09 |
| [ADR-0014](0014-home-dashboard-recent-entries-sparkline.md) | Home-Dashboard mit Recent-Entries + 14-Tage-Sparkline (M1.5) | Akzeptiert    | 2026-05-09 |

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

### ADR-0009 – Offline-Sync nach M4 verschieben

Issues #10 (Offline-Sync) und #24 (Sync-Conflict-Log) werden von M1 nach M4 (Mobile Polish & PWA-Hardening) verschoben. M1-Exit ist 'Produktive Online-Nutzung im Browser' und für den Eigen-User-Test ohne Offline-Sync erreichbar; #10 ist substantieller Aufwand (Dexie + Sync-Endpoints + LWW-Merge + Conflict-Reports), der M1 unnötig blockiert. M4 enthält bereits einen Offline-Modus-Akzeptanztest — Verschmelzung ist sauber. Issue #26 (Fernet at-rest) bleibt M1, da DSGVO-blockierend.

### ADR-0010 – Build-Toolchain-Pinning (pnpm-Version)

pnpm-Version wird in Root-`package.json` (`packageManager: "pnpm@11.0.8"`) und in allen `pnpm/action-setup`-Workflow-Steps (`version: '11.0.8'`) explizit gepinnt. Hintergrund: `pnpm/action-setup@v4 version: 'latest'` zog je nach Tag pnpm 10.x oder 11.x, was zu Drift in der `pnpm-workspace.yaml`-Konfiguration führte (`onlyBuiltDependencies` in v10 vs. `allowBuilds` in v11) und reproduzierbar `ERR_PNPM_IGNORED_BUILDS` auf Branches ohne Cache-Hit auslöste. Mit dem Pin ist Toolchain-Verhalten zwischen CI und Image-Build deterministisch; Updates werden zu bewussten Commits statt zu stillen Drift-Effekten. `pnpm-workspace.yaml` nutzt nur noch v11-Syntax (`allowBuilds`-Map). Update-Pfad in der ADR dokumentiert.

### ADR-0011 – Interner Reverse-Proxy im Web-Container (M2)

Der `moodsync-web`-Container bekommt in M2 einen integrierten Reverse-Proxy via SvelteKit `hooks.server.ts`, der `/api/*`-Requests intern an `http://api:8000/*` weiterleitet. Hintergrund: `VITE_API_BASE_URL` ist eine Build-Time-Variable und wird ins JS-Bundle einkompiliert — PR #92 hat das via `workflow_dispatch`-Input parametrisierbar gemacht (Sofort-Fix), aber das Bundle bleibt an die im Build angegebene URL gekoppelt (Rebuild bei IP-/Port-Wechsel) und der API-Port muss am Host gemappt sein. Der interne Proxy löst beides: Ein Image für alle Topologien (`/api/v1` bleibt immer korrekt), API-Port nur noch via `expose` intern (Sicherheitsplus), Same-Origin für Cookie-Auth (vereinfacht ADR-0006-Setup). Gewählt wurde Variante B (SvelteKit-Handle-Hook, ~140 Zeilen TS inkl. Hop-by-Hop-Stripping und Set-Cookie-Behandlung) statt Sidecar-nginx (Variante A) oder Caddy-im-Image (Variante C). **Status `Accepted` seit 2026-05-08:** Implementierung in `apps/web/src/hooks.server.ts`, `release-images.yml` `workflow_dispatch`-Input `vite_api_base_url` entfernt, `VITE_API_BASE_URL` ist nun fix `/api/v1`, Topologie zur Laufzeit über `INTERNAL_API_URL` (Default `http://api:8000`).

### ADR-0012 – M2/M5 Streak-Semantik + Habit-Schema-Vorgriff

Löst die im Design-Doc unsaubere Abgrenzung zwischen M2 (Visualisierung) und M5 (Habits & Ziele) auf: M2 liefert ausschließlich **Eintrags-Streaks** (aufeinanderfolgende Tage mit Eintrag) und Tag-Frequenz-Heatmap (Roh-Häufigkeiten ohne Habit-Semantik). M5 liefert **Habit-Streaks** (zielbezogen via `habit_type` + `target_frequency`) und das Habit-Dashboard. Begriffe „Eintrags-Streak" und „Habit-Streak" werden kanonisch. Schema-Vorgriff in M2: `tags`-Tabelle bekommt zwei nullable Spalten `habit_type` (Default `'none'`) und `target_frequency`, abgesichert durch CHECK-Constraints — API/UI/Streak-Logik bleiben M5-Lieferung. Vermeidet Daten-Backfill in M5 und macht M5 zu einer reinen Frontend-/Service-Erweiterung. Status `Vorgeschlagen`, Schema-Migration in M2, volle Habit-Funktionalität in M5.

### ADR-0013 – Auto-Save für Day-Entries

Die Tagesansicht wechselt von manuellem Submit auf Hybrid Auto-Save mit sichtbarer Status-Anzeige (`idle | dirty | saving | saved | error`) und 800 ms-Debounce. Erste Save-Operation eines Tages bleibt POST, anschließend PATCH (POST→PATCH-Flip aus PR #117). Konflikte: LWW (Single-Device-M1-Scope, ADR-0003 wird erst Multi-Device aktiv). Offline-Verhalten: explizit online-only, kein localStorage-Buffer (siehe ADR-0009). Submit-Button entfällt; Cancel-Button bleibt; `beforeunload`-Listener fängt Tab-Close während `saving` ab. State-Machine ist offline-erweiterungsfähig (M4).

### ADR-0014 – Home-Dashboard mit Recent-Entries und 14-Tage-Sparkline

Recent-Entries-Liste (7 Tage, klickbar mit `?date=`-Param), 7-Tage-Summary (Mood/Energy/Stress-Avg + Eintrags-Streak per ADR-0012) und 14-Tage-Mood-Sparkline werden von M2 nach M1.5 vorgezogen. Keine neue Dependency: Sparkline ist eigenes SVG (~80 LOC, theme-aware, wiederverwendbar für M2-Charts). Kein neuer Backend-Endpoint; alles aus dem bestehenden `listEntries`-Pfad. Streak-Berechnung clientseitig in `lib/utils/streak.ts`, in M2 wechselt nur die Datenquelle wenn der Backend-Streak-Endpoint kommt. Anonymous-Landing bleibt unverändert.

---

## Neue ADRs hinzufügen

1. Nächste freie Nummer ermitteln
2. Datei `NNNN-kurzer-titel.md` in diesem Verzeichnis anlegen
3. Eintrag in den Index oben sowie in die Kurzübersicht aufnehmen
4. Status initial auf `Vorgeschlagen`, nach Team-Review auf `Accepted` oder `Abgelehnt` setzen

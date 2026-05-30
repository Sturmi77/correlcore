# Architecture Decision Records (ADR)

Jede signifikante Architekturentscheidung wird hier als ADR dokumentiert.

## Format

Dateiname: `NNNN-kurzer-titel.md`
Status: `Vorgeschlagen | Accepted | Abgelehnt | Ersetzt durch ADR-XXXX`

## Index

| ADR                                                              | Titel                                                        | Status        | Datum      |
| ---------------------------------------------------------------- | ------------------------------------------------------------ | ------------- | ---------- |
| [ADR-0001](0001-sveltekit-vs-nextjs.md)                          | SvelteKit als Web-Framework (statt Next.js)                  | Accepted      | –          |
| [ADR-0002](0002-capacitor-statt-twa.md)                          | Capacitor statt TWA als Mobile-Strategie                     | Accepted      | 2026-04-20 |
| [ADR-0003](0003-sync-conflict-log.md)                            | Sync-Protokoll: Conflict-Log statt stilles LWW               | Accepted      | 2026-04-20 |
| [ADR-0004](0004-auth-strategie.md)                               | Auth-Strategie: Native JWT in Phase 1, Authentik ab Phase 2  | Accepted      | 2026-04-20 |
| [ADR-0005](0005-verschluesselung-at-rest.md)                     | Datenverschlüsselung at-rest: Zweistufige Strategie          | Accepted      | 2026-04-20 |
| [ADR-0006](0006-cookie-auth-mit-capacitor-migration.md)          | Cookie-Auth im Web mit geplanter Capacitor-Bearer-Migration  | Accepted      | 2026-05-04 |
| [ADR-0007](0007-healthchecks-and-logging.md)                     | Healthchecks und strukturiertes Logging                      | Accepted      | 2026-05-04 |
| [ADR-0008](0008-symptom-master-tabelle.md)                       | Symptom-Master-Tabelle für Custom-Symptome                   | Accepted      | 2026-05-04 |
| [ADR-0009](0009-offline-sync-nach-m4.md)                         | Offline-Sync nach M4 verschieben (Scope-Reduktion M1)        | Accepted      | 2026-05-04 |
| [ADR-0010](0010-build-toolchain-pinning.md)                      | Build-Toolchain-Pinning (pnpm-Version)                       | Accepted      | 2026-05-07 |
| [ADR-0011](0011-web-internal-reverse-proxy.md)                   | Interner Reverse-Proxy im Web-Container                      | Accepted      | 2026-05-08 |
| [ADR-0012](0012-m2-m5-streak-semantik.md)                        | M2/M5 Tracking-Semantik + Habit-Adherence                    | Accepted      | 2026-05-28 |
| [ADR-0013](0013-autosave-day-entries.md)                         | Auto-Save für Day-Entries (M1.5)                             | Akzeptiert    | 2026-05-09 |
| [ADR-0014](0014-home-dashboard-recent-entries-sparkline.md)      | Home-Dashboard mit Recent-Entries + 14-Tage-Sparkline (M1.5) | Akzeptiert    | 2026-05-09 |
| [ADR-0015](0015-developer-view-version-identifikation.md)        | Developer-View fuer Versionsidentifikation                   | Akzeptiert    | 2026-05-10 |
| [ADR-0016](0016-timeseries-split-ml-models.md)                   | Timeseries Split für ML-Modelle                              | Akzeptiert    | 2026-05-10 |
| [ADR-0017](0017-frontend-screen-architecture.md)                 | Frontend Screen Architecture (M3.1)                          | Accepted      | 2026-05-13 |
| [ADR-0018](0018-insight-confidence-visualisation.md)             | Insight Confidence Visualisation                             | Accepted      | 2026-05-13 |
| [ADR-0019](0019-dev-mode-settings-toggle.md)                     | Developer Mode Toggle in Settings                            | Accepted      | 2026-05-13 |
| [ADR-0020](0020-primary-color-system.md)                         | Primary Color System for M3.5 Frontend                       | Accepted      | 2026-05-15 |
| [ADR-0021](0021-insight-maturity-phases.md)                      | Insight Maturity Phases as a First-Class Frontend Concept    | Accepted      | 2026-05-16 |
| [ADR-0025](0025-symptom-analytics.md)                            | Symptom Analytics — Univariate, Co-Occurrence, Multivariate  | Vorgeschlagen | 2026-05-19 |
| [ADR-0026](0026-color-scheme-evaluation-orange-vs-violet.md)     | Color Scheme Evaluation: Orange/Dark vs. Violet/Dark         | Accepted      | 2026-05-26 |
| [ADR-0027](0027-light-mode-color-requirements.md)                | Light Mode Color Requirements (WCAG contrast)                | Accepted      | 2026-05-26 |
| [ADR-0028](0028-entry-slot-model.md)                             | Entry Slot Model (`day` / `morning` / `noon` / `evening`)    | Accepted      | 2026-05-28 |
| [ADR-0029](0029-trend-smoothing-frontend.md)                     | Client-Side 7-Day SMA Trend Smoothing                        | Accepted      | 2026-05-28 |
| [ADR-0030](0030-onboarding-tag-suggestions.md)                   | Guided Onboarding Tag Suggestions by Slug                    | Accepted      | 2026-05-28 |
| [ADR-0031](0031-cycle-tracking-scope.md)                         | Neutral `cycle_day` Scope (no medical inference)             | Accepted      | 2026-05-28 |
| [ADR-0032](0032-cycle-tracking-as-domain-extension.md)           | Cycle Tracking as Domain Extension                           | Accepted      | 2026-05-28 |
| [ADR-0033](0033-sensitive-health-data-handling-cycle-signals.md) | Sensitive Health Data Handling for Cycle Signals             | Accepted      | 2026-05-28 |
| [ADR-0034](0034-onboarding-cycle-tracking-toggle.md)             | Onboarding Cycle Tracking Toggle                             | Accepted      | 2026-05-28 |
| [ADR-0035](0035-temporal-correspondence-pattern.md)              | Temporal Correspondence Pattern for Trend+Heatmap Alignment  | Accepted      | 2026-05-30 |

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

Der `correlcore-web`-Container bekommt in M2 einen integrierten Reverse-Proxy via SvelteKit `hooks.server.ts`, der `/api/*`-Requests intern an `http://api:8000/*` weiterleitet. Hintergrund: `VITE_API_BASE_URL` ist eine Build-Time-Variable und wird ins JS-Bundle einkompiliert — PR #92 hat das via `workflow_dispatch`-Input parametrisierbar gemacht (Sofort-Fix), aber das Bundle bleibt an die im Build angegebene URL gekoppelt (Rebuild bei IP-/Port-Wechsel) und der API-Port muss am Host gemappt sein. Der interne Proxy löst beides: Ein Image für alle Topologien (`/api/v1` bleibt immer korrekt), API-Port nur noch via `expose` intern (Sicherheitsplus), Same-Origin für Cookie-Auth (vereinfacht ADR-0006-Setup). Gewählt wurde Variante B (SvelteKit-Handle-Hook, ~140 Zeilen TS inkl. Hop-by-Hop-Stripping und Set-Cookie-Behandlung) statt Sidecar-nginx (Variante A) oder Caddy-im-Image (Variante C). **Status `Accepted` seit 2026-05-08:** Implementierung in `apps/web/src/hooks.server.ts`, `release-images.yml` `workflow_dispatch`-Input `vite_api_base_url` entfernt, `VITE_API_BASE_URL` ist nun fix `/api/v1`, Topologie zur Laufzeit über `INTERNAL_API_URL` (Default `http://api:8000`).

### ADR-0012 – M2/M5 Tracking-Semantik + Habit-Adherence

M2 liefert Tracking-Consistency und Tag-Frequenz-Heatmaps ohne Habit-Semantik.
M5 aktiviert `tags.habit_type` und `tags.target_frequency` für ein
zielbasiertes Habit-Dashboard. Habit-Streaks werden nicht umgesetzt:
kanonische M5-Metrik ist Adherence Rate plus neutrale Heatmap und optionaler
Correlation Contribution Score.

### ADR-0013 – Auto-Save für Day-Entries

Die Tagesansicht wechselt von manuellem Submit auf Hybrid Auto-Save mit sichtbarer Status-Anzeige (`idle | dirty | saving | saved | error`) und 800 ms-Debounce. Erste Save-Operation eines Tages bleibt POST, anschließend PATCH (POST→PATCH-Flip aus PR #117). Konflikte: LWW (Single-Device-M1-Scope, ADR-0003 wird erst Multi-Device aktiv). Offline-Verhalten: explizit online-only, kein localStorage-Buffer (siehe ADR-0009). Submit-Button entfällt; Cancel-Button bleibt; `beforeunload`-Listener fängt Tab-Close während `saving` ab. State-Machine ist offline-erweiterungsfähig (M4).

### ADR-0014 – Home-Dashboard mit Recent-Entries und 14-Tage-Sparkline

Recent-Entries-Liste (7 Tage, klickbar mit `?date=`-Param), 7-Tage-Summary (Mood/Energy/Stress-Avg + Eintrags-Streak per ADR-0012) und 14-Tage-Mood-Sparkline werden von M2 nach M1.5 vorgezogen. Keine neue Dependency: Sparkline ist eigenes SVG (~80 LOC, theme-aware, wiederverwendbar für M2-Charts). Kein neuer Backend-Endpoint; alles aus dem bestehenden `listEntries`-Pfad. Streak-Berechnung clientseitig in `lib/utils/streak.ts`, in M2 wechselt nur die Datenquelle wenn der Backend-Streak-Endpoint kommt. Anonymous-Landing bleibt unverändert.

### ADR-0015 - Developer-View fuer Versionsidentifikation

`/dev` wird als default-off Diagnose-View fuer verifizierte User eingefuehrt. `git_commit`/`git_branch`/`build_time` werden beim API-Image-Build eingebettet und beantworten, welche GitHub-Version laeuft. `image_tag` und optional `image_digest` kommen aus dem Deployment; der echte RepoDigest wird nicht im Container ermittelt und der Docker-Socket bleibt bewusst ungemountet. Fehlt `IMAGE_DIGEST`, zeigt API/UI `null` bzw. "Digest not provided".

### ADR-0016 – Timeseries Split für ML-Modelle

Zeit-basierter Train/Test-Split (kein random-shuffle) für alle ML/Statistik-Modelle in CorrelCore. Sichert zeitliche Kausalität in Korrelationsberechnungen ab.

### ADR-0017 – Frontend Screen Architecture (M3.1)

CorrelCore hat genau 5 primäre Screens (Home, Entry Sheet, Insights, Trends, Settings). Kein neuer Screen ohne ADR-Begründung. Der `/dev`-Screen zählt nicht als User-facing Screen. Der `[Streak: 🔥 7]`-Sketch aus dem alten FRONTEND.md wird formal entfernt. Insights werden nach `confidence × effect_size` sortiert, jede Card hat 3 Disclosure-Level.

### ADR-0018 – Insight Confidence Visualisation

Confidence wird als einfarbiger Fortschrittsbalken mit semantischem Label dargestellt (`Early signal` / `Emerging pattern` / `Moderate finding` / `Strong finding` / `Very strong finding`). Kein Prozentwert auf der Collapsed-Card (Pseudo-Präzision), keine Punkte/Sterne (Gamification-Assoziation). Raw-Wert und `sample_n` nur in Expanded State sichtbar.

### ADR-0019 – Developer Mode Toggle in Settings

Developer Mode wird über 7× Tap auf den Version-String im Settings-Footer aktiviert. Persistenz in localStorage (client-only). Wenn aktiv: `DEVELOPER`-Sektion in Settings sichtbar mit Toggle + Link zu `/dev`. Die Route `/dev` wird nicht in der Bottom Navigation gezeigt.

### ADR-0020 - Primary Color System for M3.5 Frontend

CorrelCore verwendet Violet als kanonische Primary-Farbfamilie fuer interaktive Elemente, Fokuszustaende und Mood-Metriken. Die frueheren Teal-Defaults bleiben nur als bewusst migrierte Legacy-Referenzen erlaubt. Heatmaps verwenden neutrale Blauabstufungen ohne Rot/Gruen-Wertung.

### ADR-0021 – Insight Maturity Phases as a First-Class Frontend Concept

Insight maturity wird zum gemeinsamen Domain-Konzept von Backend und Frontend erhoben. Vier Phasen (`collecting` 1–6, `early_patterns` 7–13, `provisional` 14–29, `robust` 30+) bestimmen welche Inhalte in der UI erscheinen. Jede `/api/v1/insights/*`-Antwort enthält ein `insight_maturity`-Objekt mit `phase`, `phase_index`, `current_entries`, `next_phase_at`, `next_phase_label`, `entries_until_next` und `user_message_key`. Frontend-Komponenten (`InsightJourneyBanner`, `InsightMaturityBadge`, Phase-Milestone-Karten) und phasen-spezifische Sprache sind verpflichtend; das Frontend berechnet Phasen niemals selbst. Confidence-Visualisierung aus ADR-0018 wird durch das kombinierte Phase+Confidence-Modell teilweise abgelöst.

### ADR-0035 – Temporal Correspondence Pattern for Trend+Heatmap Alignment

Die Trend-Visualisierung in `/trends` (und später `/insights`) wird auf ein dreistufiges **Temporal Correspondence**-Muster ausgerichtet: gemeinsame `dates[]`-Achse, geteilter Timeline-Cursor, neutrale Event-Marker sowie ein optionaler **Unified-Strip**-Render-Modus, in dem Mood/Energy/Stress als divergente Strips über den Tag- und Symptom-Heatmap-Zeilen liegen. Für `/trends`- und `/insights`-Deep-Views wird **LayerChart** (MIT, Svelte 5 nativ, ~55–65 KB gz) als optionale Chart-Library eingeführt; das Default-Rendering (Sparklines, M2-Heatmap, Home) bleibt Custom-SVG. Damit wird D-002 **teilweise abgelöst** (harte Marginal-Bundle-Grenze 80 KB gz für die Lib in den genannten Routen; Adapter-Pattern unter `apps/web/src/lib/charts/adapter/`). Alle divergenten Skalen folgen einer **theme-agnostischen Farbregel**: entweder Single-Hue mit zwei Extremen oder zwei nicht-rot↔grün Hue-Paare aus dem Theme-Accent-System; verboten ist jedes Paar innerhalb 20° von Rot (H 0°/360°) und Grün (H 120°). Theme-Tokens (`--color-divergent-neg/pos/mid`, `--color-event-marker-*`) werden vom aktiven GUI-Theme befüllt — keine Hue-Härtekodierung in Komponenten. Implementierung sequenziell in M3.8 (Sprint 0–3, siehe `docs/M3_8_SPRINT_PLAN.md`).

### ADR-0025 – Symptom Analytics: Univariate, Co-Occurrence, Multivariate

Symptome werden in drei analytischen Ebenen behandelt: **univariat** (Pointbiserial, Mann-Whitney-U, Cliff's Delta gegen Mood/Energy/Stress), **Ko-Okkurrenz** (Phi, Jaccard, Lift/PMI, Fisher Exact gegen Tags) und **multivariat** (Symptome als binäre Features in Lasso #144, Lag-Analyse #145, hierarchischem Clustering #150). Phase-Gating folgt ADR-0021: Level 1 und 2 ab `provisional` (≥15 Einträge), Level 3 ab `robust` (≥30). Methodische Guardrails sind zwingend: FDR-Korrektur (Benjamini-Hochberg) über alle Symptom-Tests, Min-Frequenz 5× pro Symptom, Wiederverwendung des bestehenden Weekday-Confounder-Checks, durchgehend Assoziations-statt-Kausalitäts-Sprache. Engine-seitig neuer Modul `symptom_analytics.py` integriert in den bestehenden Nightly-Worker; keine Schema-Änderung. API: neue Insight-Typen `symptom_mood_association`, `symptom_tag_cooccurrence`, `symptom_cluster` ohne Breaking Changes. Frontend integriert in den bestehenden `/insights`-Feed (keine separate Route) plus drei neue Visualisierungen (Co-Occurrence-Heatmap, Symptom-Kalender-Heatmap, Symptom-Trend-Overlay). Symptom-Intensität (0–3) bleibt explizit Future Work. Vollständige Spezifikation in `docs/features/symptom-analytics.md` und `docs/frontend/SYMPTOM_VISUALIZATION.md`.

---

## Neue ADRs hinzufügen

1. Nächste freie Nummer ermitteln
2. Datei `NNNN-kurzer-titel.md` in diesem Verzeichnis anlegen
3. Eintrag in den Index oben sowie in die Kurzübersicht aufnehmen
4. Status initial auf `Vorgeschlagen`, nach Team-Review auf `Accepted` oder `Abgelehnt` setzen

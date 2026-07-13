# Freigabe-Vorschlag: Insight-Pipeline, Trigger & Tag-Gruppen-Reifegrad

| Feld | Wert |
| ---- | ---- |
| **Status** | Zur Freigabe |
| **Datum** | 2026-07-13 |
| **Autor** | Cloud Agent (Analyse `correlcore-export-2026-07-13.csv`) |
| **Bezug** | [ADR-0037](../adr/0037-insight-triggers-tag-cluster-maturity.md) (Entwurf) |
| **Auslöser** | 67 Tracking-Tage mit reifen Daten, aber leere Wochentags-Übersicht, keine Tag-Gruppen, kein Daily-Brief-Insight |

---

## 1. Executive Summary

Dieser Vorschlag bündelt drei zusammenhängende Lücken, die bei „reifen“ Nutzerdaten wie einem 67-Tage-Export als Bug wahrgenommen werden, obwohl Teile davon **by design** sind:

1. **Insight-Sichtbarkeit** — Analytics laufen primär über den Nightly Worker; es fehlen ergänzende Trigger (Import, On-Demand).
2. **Wochentags-Übersicht** — UI hängt ausschließlich am inferenziellen `weekday_pattern`-Insight (Schwelle Δ ≥ 0,5), nicht an vorhandenen Rohdaten.
3. **Tag-Gruppen** — Harte 90-Tage-Schwelle blockiert ein essentielles Feature, obwohl die 90-Tage-Regel aus ADR-0016 **nur ML (Lasso/Lag)** betrifft, nicht Jaccard/K-Means-Clustering.

**Kernentscheidungen (Freigabe erforderlich):**

| # | Entscheidung | Kurz |
| - | ------------ | ---- |
| D1 | **Mehrere Insight-Trigger** neben Nightly Worker (Import, User On-Demand, Admin) | Pipeline bleibt eine |
| D2 | **Deskriptive Wochentags-Aggregation** im Dashboard-API, getrennt von `weekday_pattern` | Server-authoritative |
| D3 | **Dreistufiges Tag-Gruppen-Modell** (Paare → provisional K-Means → robust) | 90 Tage nur für ML + robuste Cluster |
| D4 | **`MIN_WEEKDAY_DELTA` und inferenzielle Tag-Schwellen unverändert** | M9-Entscheidung bleibt |
| D5 | **Neue ADR-0037** formalisiert Trigger + Cluster-Reifegrad | Siehe ADR-Entwurf |

---

## 2. Ausgangslage (Datenanalyse)

Export `correlcore-export-2026-07-13.csv`:

| Kennzahl | Wert |
| -------- | ---- |
| Kalendertage (dedupliziert) | **67** |
| Insight-Maturity-Phase | **provisional** (14–29 wäre 14+, robust ab 30) |
| Engine-Kandidaten (Simulation) | **13** (Spearman, Symptom, Urlaub-Kontext, Point-biserial …) |
| `weekday_pattern` | **0** — max. Wochentags-Δ = **0,29** (Freitag), Schwelle **0,5** |
| Tag-Gruppen (aktuell) | **insufficient_data** — `67 < MIN_TAG_CLUSTER_ENTRIES (90)` |
| K-Means-Simulation bei 67 Tagen | **4 Cluster**, Silhouette **0,115** — inhaltlich plausibel |

**Schlussfolgerung:** Die Daten sind für viele Features reif; die Mechanik und Betriebsmodell blockieren die Sichtbarkeit.

---

## 3. Ist-Zustand vs. erwartetes Verhalten

### 3.1 Nightly Worker bei 67 Tagen

**Wenn der Worker läuft** (verified User, DEK, `analytics_enabled ≠ false`):

| Komponente | Ergebnis bei 67 Tagen |
| ---------- | --------------------- |
| `generate_and_store_insights` | ✅ ~13 persistierte Insights |
| `recompute_tag_vectors_and_clusters` | ⚙️ läuft, Response aber `insufficient_data` |
| `weekday_pattern` | ❌ Δ < 0,5 |
| Lasso / Lag | ❌ `MIN_ML_ENTRIES = 90` (ADR-0016) |

**Tag-Gruppen hängen nicht am Worker-Lauf:** `GET /insights/tag-clusters` berechnet bei jedem Request neu (`get_tag_clusters` → `recompute_tag_vectors_and_clusters`). Die 90-Tage-Hürde sitzt in `build_tag_cluster_response`.

**Wenn gar nichts sichtbar ist**, liegt das eher an:

- Worker-Container nicht aktiv (lokales Dev: `AGENTS.md` listet nur API + Web)
- `docker-compose.user-test.yml`: Worker hinter `--profile worker`
- `analytics_enabled = false`
- Insights-API-Fehler (Home zeigt Maturity-Fallback)

→ **Kein klassischer Code-Bug**, aber ein **Betriebs- und UX-Gap**.

### 3.2 Dokumentierte Architektur-Lücken

| Quelle | Aussage |
| ------ | ------- |
| `CHANGELOG.md` (M3) | „kein manueller Trigger in diesem Sprint“ |
| `docs/API.md` | `POST /insights/trigger` **geplant**, M3 nicht implementiert |
| `docs/M9_SPRINT_PLAN.md` | „Heavy analytics stay in nightly worker“ |
| `docs/adr/0017` | Insights **worker-generated**, server-authoritative |

---

## 4. Entscheidungen im Detail

### D1 — Insight-Trigger-Architektur

**Ein Engine-Pfad, mehrere Auslöser.** Alle Trigger rufen dieselben Services auf wie der Worker:

```
insight_worker_service.generate_insights_for_job()
  → generate_and_store_insights()
  → recompute_tag_vectors_and_clusters()
```

#### Trigger-Matrix

| ID | Trigger | Ereignis | Scope | Rate-Limit | Priorität |
| -- | ------- | -------- | ----- | ---------- | --------- |
| T1 | **Nightly Worker** | 03:00 UTC (`run_daily_jobs_once`) | Alle eligible User | — | Bleibt Basis |
| T2 | **Post-Import** | Erfolgreiches `POST /entries/batch` (Retro, Bulk) | Nur betroffener User | Debounce 5 min | **P0** |
| T3 | **User On-Demand** | `POST /api/v1/insights/regenerate` | Nur Owner | 1× / 60 min | **P0** |
| T4 | **Admin** | `POST /api/v1/insights/trigger` | Admin / Dev-Rolle | Unbegrenzt (Audit-Log) | P1 |
| T5 | **Entry-Save** | Nach jedem Auto-Save | — | — | **Abgelehnt** (M9) |

#### Gemeinsame Regeln (alle Trigger)

- `analytics_enabled` respektieren (DSGVO Art. 18 / User-Pref)
- User-DEK binden (`set_current_user_dek`) wie im Worker
- Idempotent pro `(user_id, generated_for_date)`
- Fehler pro User isolieren (kein Batch-Abbruch)
- Kein synchroner Trigger im Entry-Save-Hot-Path

#### API-Ergänzungen

```
POST /api/v1/insights/regenerate     # neu — Owner, verified
POST /api/v1/insights/trigger        # bestehend geplant — Admin only
```

**Response (beide):**

```json
{
  "status": "ok",
  "generated_for_date": "2026-07-13",
  "insight_count": 13,
  "tag_clusters_status": "ok",
  "trigger_source": "user_regenerate"
}
```

#### Betrieb / Dev

- `AGENTS.md` + `docs/DEVELOPMENT.md`: Worker-Start für lokale Insight-Entwicklung dokumentieren
- Optional: `make insights-run` / `uv run python -m app.workers.analytics --once` CLI-Flag für Einmal-Lauf

---

### D2 — Wochentags-Übersicht entkoppeln

**Problem:** `HomeWeekdayOverview` zeigt Balken nur aus `weekday_pattern.payload.weekday_mood_avgs`. Ohne inferenziellen Insight bleibt die UI leer — auch bei 10× Daten pro Wochentag.

**Lösung:** Deskriptive Aggregation serverseitig (wie `work_context_summary`), inferenzielle Befunde optional als Labels.

#### API-Erweiterung

`GET /api/v1/dashboard/summary` ergänzt:

```json
{
  "weekday_summary": [
    { "weekday": 0, "entry_count": 10, "mood_avg": 3.4 },
    { "weekday": 4, "entry_count": 10, "mood_avg": 3.9 }
  ]
}
```

- Berechnung: deduplizierte Tagesvektoren, `entry_date.weekday()`, Mittelwert `mood_score`
- Verfügbar ab **7 distinct weekdays mit je ≥ 1 Eintrag** (nicht ab Δ ≥ 0,5)
- Kein Insight-Objekt, keine inferenzielle Aussage

#### Frontend

- `HomeWeekdayOverview`: primär `weekday_summary` vom Dashboard; Insight-Labels weiter aus confounded/ranked Insights
- `weekday_pattern`-Statement nur wenn Insight existiert (Badge „Erstes Signal“)

#### Bewusst unverändert

- `MIN_WEEKDAY_DELTA = 0.5` in `insight_engine.py` (**M9-Entscheidung**)
- `weekday_pattern` bleibt inferenzieller Befund, nicht reine Statistik

---

### D3 — Tag-Gruppen: Dreistufiges Reifegrad-Modell

**Problem:** `MIN_TAG_CLUSTER_ENTRIES = 90` wurde an die ML-Schwelle (ADR-0016) gekoppelt. Tag-Clustering nutzt **keine** TimeSeriesSplit-CV — die 90-Tage-Regel ist für dieses Feature zu streng.

#### Neue Konstanten (`tag_cluster_service.py`)

| Konstante | Wert | Bedeutung |
| --------- | ---- | --------- |
| `MIN_TAG_CLUSTER_PAIR_ENTRIES` | **30** | Paar-basierte Gruppen |
| `MIN_TAG_CLUSTER_PROVISIONAL_ENTRIES` | **45** | K-Means provisional |
| `MIN_TAG_CLUSTER_ROBUST_ENTRIES` | **90** | Volles K-Means (unverändert) |
| `MIN_SIGNAL_CLUSTER_NODES` | **5** | Unverändert |
| `TAG_CLUSTER_WINDOW_DAYS` | **90** | Rolling window; nutzt `min(available, 90)` Tage |

#### Modi

| Stufe | `cluster_maturity` | `cluster_mode` | Algorithmus | UI |
| ----- | ------------------ | -------------- | ----------- | -- |
| A | — | — | — | `< 30` Tage: `insufficient_data` |
| B | `early` | `pair` | Top-N Jaccard-Paare (2–3 Tags), `min_co_count ≥ 5` | „Erste gemeinsame Muster“ |
| C | `provisional` | `kmeans` | K-Means, `k ≤ 3`, Silhouette-Gate ≥ 0.08 | „Vorläufige Tag-Gruppen“ |
| D | `robust` | `kmeans` | K-Means `k` 3–6, Symptome gemischt | „Tag-Gruppen“ (heute) |

#### API-Erweiterung `TagClustersResponse`

```json
{
  "status": "ok",
  "cluster_maturity": "provisional",
  "cluster_mode": "kmeans",
  "entry_count": 67,
  "entries_until_robust": 23,
  "silhouette_score": 0.115,
  "window_days": 67,
  "clusters": [...]
}
```

#### Guards (provisional)

- `k` maximal **3**
- Silhouette **< 0.08** → Fallback auf `pair`-Modus
- Cluster-Größe max. **5** Signale
- Hub-Tags (optional Phase 2): Tags in > 60 % der Tage nicht als Cluster-Anker

#### Copy / Semantik

- Neutral: „Tags, die häufig gemeinsam auftreten“
- Provisional-Zusatz: „Vorläufig — Muster können sich mit mehr Einträgen ändern“
- **Keine** Insight-Card, **kein** kausaler Anspruch
- Stärke-% wie heute, mit Reifegrad-Badge (`emerging_pattern` / ADR-0021)

#### Bewusst unverändert

- `MIN_ML_ENTRIES = 90` für Lasso/Lag (**ADR-0016**)
- `ANALYTICS_MIN_TAG_USAGES = 10` für Point-biserial (**M9**)
- Inferenzielle Tag→Mood-Insights: Schwellen nicht senken

---

## 5. Was bewusst NICHT geändert wird

| Thema | Begründung |
| ----- | ---------- |
| `MIN_WEEKDAY_DELTA = 0.5` senken | M9_ANALYTICS_THRESHOLDS_REVIEW: bewusst streng |
| `ANALYTICS_MIN_TAG_USAGES` senken | M9: False-Positive-Risiko |
| Tag-Gruppen ab pauschal 60 ohne Stufen | Instabilität; Paar-Modus ab 30 ist sicherer |
| Insights bei jedem Entry-Save | M9: Heavy analytics im Worker |
| Frontend berechnet Insights selbst | ADR-0017, M4.1: server-authoritative |
| ML-Schwelle 90 Tage | ADR-0016: TimeSeriesSplit-Validität |

---

## 6. Implementierungsphasen

**Detaillierter Sprintplan:** [`M10_1_INSIGHT_PIPELINE_SPRINT_PLAN.md`](../M10_1_INSIGHT_PIPELINE_SPRINT_PLAN.md)  
**Tracking:** [`M10_1_INSIGHT_PIPELINE_SPRINT_STATUS.md`](../M10_1_INSIGHT_PIPELINE_SPRINT_STATUS.md)

### Phase 1 — P0 (Beta-Blocker) → Paket A + B + D

| Task | Dateien |
| ---- | ------- |
| `POST /insights/regenerate` Endpoint | `backend/app/api/v1/endpoints/insights.py` |
| Trigger nach `POST /entries/batch` | `backend/app/api/v1/endpoints/entries.py` oder `entry_service` |
| Tag-Cluster Stufen B+C (`pair` + `provisional`) | `tag_cluster_service.py`, `schemas/stats.py` |
| `TagGroupsSection` Reifegrad-Badge | `TagGroupsSection.svelte`, i18n |
| Worker in Dev-Doku | `AGENTS.md`, `docs/DEVELOPMENT.md` |
| Tests | `test_tag_clusters.py`, `test_insights.py`, API contract |

### Phase 2 — P1 (Home-Vollständigkeit) → Paket C + A5/A7

| Task | Dateien |
| ---- | ------- |
| `weekday_summary` im Dashboard | `dashboard_service.py`, `schemas/dashboard.py` |
| `HomeWeekdayOverview` nutzt Dashboard | `homeWeekdayOverview.ts`, `+page.svelte` |
| `POST /insights/trigger` Admin | `insights.py`, Admin-Guard |
| CLI `--once` für Worker | `workers/analytics.py` |

### Phase 3 — P2 (Feinschliff) → Paket E + optional Hub-Tags

| Task | Dateien |
| ---- | ------- |
| Hub-Tag-Dämpfung in Clustering | `tag_cluster_service.py` |
| Rate-Limit Redis für regenerate | `config.py`, endpoint |
| E2E: Import → Insights sichtbar | `user-journeys.spec.ts` |
| Dev-Fixtures `weekday_summary` | `phaseFixtures.ts` |

---

## 7. Dokumentations-Impact-Matrix

Bei Freigabe und Umsetzung sind folgende Dateien **anzupassen** (Pflicht vs. optional):

### 7.1 Architektur & ADR (Pflicht)

| Datei | Änderung |
| ----- | -------- |
| [docs/adr/0037-insight-triggers-tag-cluster-maturity.md](../adr/0037-insight-triggers-tag-cluster-maturity.md) | Status → **Accepted** nach Freigabe |
| [docs/adr/README.md](../adr/README.md) | Index ADR-0037 |
| [docs/ARCHITECTURE.md](../ARCHITECTURE.md) | §6 Analytics Worker: Trigger-Matrix, Trennung ML 90d / Cluster-Stufen |
| [docs/adr/0016-timeseries-split-ml-models.md](../adr/0016-timeseries-split-ml-models.md) | Klarstellung: 90d gilt **nur** für CV-ML, Verweis ADR-0037 |
| [docs/adr/0021-insight-maturity-phases.md](../adr/0021-insight-maturity-phases.md) | Verweis: Tag-Gruppen `cluster_maturity` ergänzt Phasenmodell |

### 7.2 API & Verträge (Pflicht)

| Datei | Änderung |
| ----- | -------- |
| [docs/API.md](../API.md) | `POST /insights/regenerate`, `TagClustersResponse` Felder, Dashboard `weekday_summary`, Trigger-Status |
| [docs/PHASE_INSIGHT_MATRIX.md](../PHASE_INSIGHT_MATRIX.md) | Tag-Cluster-Stufen, Weekday deskriptiv vs. inferenziell |
| [docs/quality/M9_ANALYTICS_THRESHOLDS_REVIEW.md](../quality/M9_ANALYTICS_THRESHOLDS_REVIEW.md) | Addendum: Tag-Cluster entkoppelt von ML-90d |
| OpenAPI / `test_api_contract.py` | Neue Felder und Endpoints |

### 7.3 Betrieb & Selfhost (Pflicht)

| Datei | Änderung |
| ----- | -------- |
| [AGENTS.md](../../AGENTS.md) | Worker-Start lokal, `insights/regenerate` für Dev |
| [docs/DEVELOPMENT.md](../DEVELOPMENT.md) | Worker + Einmal-Lauf |
| [docs/selfhost/INSTALL.md](../selfhost/INSTALL.md) | On-Demand regenerate für Homelab |
| [docs-site/docs/user-guide/index.md](../../docs-site/docs/user-guide/index.md) | Trigger, Tag-Gruppen provisional |
| [docs-site/docs/api/overview.md](../../docs-site/docs/api/overview.md) | Neue Endpoints |

### 7.4 Frontend-Doku (Pflicht)

| Datei | Änderung |
| ----- | -------- |
| [docs/frontend/INSIGHT_METRICS_IMPLEMENTATION_PLAN.md](../frontend/INSIGHT_METRICS_IMPLEMENTATION_PLAN.md) | A-06 Weekday: Dashboard-Feed statt nur Insight |
| [docs/frontend/FRONTEND.md](../FRONTEND.md) | Home Weekday-Quelle |
| [docs/adr/0017-frontend-screen-architecture.md](../adr/0017-frontend-screen-architecture.md) | Home: deskriptiv + inferenziell getrennt |
| [apps/web/src/lib/i18n/locales/de.json](../../apps/web/src/lib/i18n/locales/de.json) | `tag_groups.provisional`, `regenerate`, `weekday_summary` |
| [apps/web/src/lib/i18n/locales/en.json](../../apps/web/src/lib/i18n/locales/en.json) | analog |

### 7.5 Milestone / Changelog (Pflicht bei Merge)

| Datei | Änderung |
| ----- | -------- |
| [CHANGELOG.md](../../CHANGELOG.md) | Eintrag M10.x |
| [docs/M7_SPRINT9_PLAN.md](../M7_SPRINT9_PLAN.md) | Addendum D4: Schwellen revidiert |
| [README.md](../../README.md) | Nur wenn User-facing Feature-Liste betroffen |

### 7.6 Bewusst nicht ändern

| Datei | Grund |
| ----- | ----- |
| `docs/DSGVO.md` § Retention 90d | Rolling Window bleibt |
| `docs/PRIVACY.md` | Analytics-Fenster unverändert |
| Inferenzielle Engine-Konstanten | M9-Review |

---

## 8. Risiken & Mitigationen

| Risiko | Schwere | Mitigation |
| ------ | ------- | ---------- |
| Provisional-Cluster instabil | Mittel | `cluster_maturity`, Silhouette-Gate, `k ≤ 3` |
| Hub-Tags verfälschen Cluster | Mittel | Paar-Modus; optional Hub-Dämpfung Phase 2 |
| On-Demand missbraucht (Last) | Niedrig | Rate-Limit 1/h, nur Owner |
| Doppel-Regeneration Import + Nightly | Niedrig | Idempotent pro Datum |
| Dokumentations-Drift | Mittel | Impact-Matrix §7, ADR-0037 als Single Source |
| Widerspruch ADR-0016 | — | **Ausgeschlossen** — ML 90d bleibt; nur Cluster entkoppelt |

---

## 9. Testplan (Akzeptanz)

### Backend

- [ ] 67-Tage-Fixture: `tag-clusters` → `status: ok`, `cluster_maturity: provisional`
- [ ] 29-Tage-Fixture: `cluster_mode: pair`
- [ ] 89 Tage: provisional; 90 Tage: robust
- [ ] `regenerate` respektiert `analytics_enabled=false` → 403 oder leer
- [ ] Batch-Import triggert Regeneration (Mock)
- [ ] Dashboard `weekday_summary` ab 7 Tagen

### Frontend

- [ ] Home Weekday-Balken mit 67 Tagen ohne `weekday_pattern`
- [ ] Tag-Gruppen zeigen provisional-Badge
- [ ] Daily Brief zeigt Insight nach manuellem regenerate
- [ ] i18n DE/EN vollständig

### E2E

- [ ] Retro-Import → Insights + Tag-Gruppen innerhalb 60s (mit Worker oder regenerate)

---

## 10. Freigabe-Checkliste

| # | Frage | Entscheidung | Freigabe |
| - | ----- | ------------ | -------- |
| 1 | Trigger T2+T3 (Import + User regenerate) umsetzen? | ☐ Ja ☐ Nein ☐ Phase 2 |
| 2 | Dashboard `weekday_summary` (deskriptiv)? | ☐ Ja ☐ Nein |
| 3 | Tag-Gruppen Stufen: 30 pair / 45 provisional / 90 robust? | ☐ Ja ☐ Anpassung: ___ |
| 4 | ADR-0037 auf Accepted setzen? | ☐ Ja ☐ Nein |
| 5 | `MIN_WEEKDAY_DELTA` unverändert lassen? | ☐ Ja (empfohlen) ☐ Nein |
| 6 | ML `MIN_ML_ENTRIES=90` unverändert? | ☐ Ja (empfohlen) ☐ Nein |
| 7 | Phase-1-Priorität für Beta? | ☐ Ja ☐ Nein |

**Freigegeben von:** _________________ **Datum:** _________

**Anmerkungen:**

---

## 11. Referenzen

- Analyse-Thread: Cloud Agent Run 2026-07-13 (`correlcore-export-2026-07-13.csv`)
- Engine-Simulation: 13 Kandidaten bei 67 Tagen; K-Means Silhouette 0,115
- [ADR-0037 Entwurf](../adr/0037-insight-triggers-tag-cluster-maturity.md)
- [M10.1 Umsetzungs-Sprintplan](../M10_1_INSIGHT_PIPELINE_SPRINT_PLAN.md)
- [M10.1 Sprint Status](../M10_1_INSIGHT_PIPELINE_SPRINT_STATUS.md)
- [M9 Analytics Threshold Review](../quality/M9_ANALYTICS_THRESHOLDS_REVIEW.md)
- [PHASE_INSIGHT_MATRIX](../PHASE_INSIGHT_MATRIX.md)

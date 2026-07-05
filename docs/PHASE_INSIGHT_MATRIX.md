# Phasen- & Insight-Referenz (Entwickler-Doku)

> **Status:** Draft · **Bezug:** [ADR-0021](adr/0021-insight-maturity-phases.md), [INSIGHT_MATURITY.md](frontend/INSIGHT_MATURITY.md), Milestone **M3.6** · **Zielgruppe:** Entwickler:innen (nicht Endnutzer)
>
> Diese Datei ist die **entwicklerseitige Single Source of Truth** dafür, welche Reifephasen es gibt,
> **wodurch** eine Phase freigeschaltet wird, welche **Insights / Trend-Visualisierungen** je Phase verfügbar sind
> und **wie** jeder Insight berechnet wird (Methode, Eingangsdaten, Schwellenwerte, erwartete Aussage).
>
> Wo Werte direkt aus dem Code stammen, ist die Quelle in Backticks referenziert (Datei + Konstante),
> damit die Doku bei Code-Änderungen gezielt nachgeführt werden kann. Stabile Vertragswerte
> (Phase-Keys, `insight_type`-Werte, i18n-Keys, Feldnamen) bleiben in Original-Schreibweise.

---

## 0. Wie dieses Dokument zu lesen ist

Es gibt in CorrelCore **zwei getrennte, aber gekoppelte Stufensysteme**. Das ist die häufigste Verwechslungsquelle:

| System | Zweck | Wertebereich | Quelle |
| --- | --- | --- | --- |
| **Insight Maturity Phase** (ADR-0021) | **Freischalt-/UX-Gating** — was der User in der App überhaupt zu sehen bekommt | `collecting` / `early_patterns` / `provisional` / `robust` (Phase 1–4) | `backend/app/services/insight_service.py` → `calculate_insight_maturity()` |
| **Insight Tier** (Confidence-Ladder) | **statistische Verlässlichkeit** eines konkret berechneten Insights | `none` / `early` / `preliminary` / `developing` / `robust` | `backend/app/services/insight_engine.py` → `confidence_tier_for_sample()` |

- Die **Phase** entscheidet, ob eine Insight-/Trend-Kategorie im Frontend **sichtbar/aktiv** ist (Gate).
- Der **Tier** und die **methodenspezifischen statistischen Schwellen** entscheiden, ob ein einzelner Insight
  überhaupt **erzeugt** wird und mit welchem Confidence-Label er erscheint.
- Beide basieren auf derselben Grundgröße: **eindeutige Eintragstage** (`COUNT(DISTINCT entry_date)` pro User),
  nicht auf der Anzahl der Roh-Einträge (Multi-Slot pro Tag wird per `_dedupe_daily_entries()` zu einem Tagesvektor kollabiert).

> ⚠️ **Wichtige Schwellen-Divergenz:** Die Phasengrenzen (7 / 14 / 30) sind **nicht identisch** mit den
> Tier-Grenzen der Analytics-Engine (3 / 8 / 15 / 30). Deshalb ist z.B. in Phase 3 (`provisional`, ab Tag 14)
> die bivariate Analyse (Spearman/Point-biserial) technisch erst ab **15** Tagen aktiv (`MIN_BIVARIATE_ENTRIES = 15`).
> Diese Divergenz ist gewollt (siehe [§5](#5-bekannte-schwellen-divergenzen--gotchas)), muss aber bei jeder
> Erweiterung mitgedacht werden.

---

## 1. Überblick — Phasen & Unlock-Schwellen

![Phasen-Timeline mit Unlock-Schwellen](assets/phase_matrix/fig1_phase_timeline.png)

| Phase | Key | Eintragstage | UI-Label | Badge-Farbe (Token) | Icon | Nächste Schwelle |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | `collecting` | **1–6** | Collecting Data | `--color-text-muted` | `loader-circle` | 7 → First Patterns |
| 2 | `early_patterns` | **7–13** | First Patterns | `--color-gold` | `sparkles` | 14 → Provisional Insights |
| 3 | `provisional` | **14–29** | Provisional Insights | `--color-warning` | `flask-conical` | 30 → Robust Insights |
| 4 | `robust` | **30+** | Robust Insights | `--color-success` | `shield-check` | — (Endzustand) |

**Freischaltbedingung (formal):** Der User erreicht Phase _n_, sobald die Anzahl **eindeutiger Eintragstage**
den unteren Schwellenwert erreicht. Es gibt kein Zurückfallen im UI-Contract (die Phase leitet sich rein aus
dem aktuellen Count ab; ein sinkender Count wäre nur durch Löschungen möglich).

### API-Vertrag (in **jeder** `/api/v1/insights/*`-Response verpflichtend)

Quelle: `backend/app/schemas/insight.py` → `InsightMaturity`, erzeugt in `calculate_insight_maturity(entry_count)`.

```json
{
  "insight_maturity": {
    "phase": "early_patterns",
    "phase_index": 2,
    "current_entries": 9,
    "next_phase_at": 14,
    "next_phase_label": "Provisional Insights",
    "entries_until_next": 5,
    "user_message_key": "maturity.early_patterns.description"
  }
}
```

- Das Frontend **berechnet die Phase nie selbst**, sondern liest sie aus diesem Objekt (ADR-0021, M3.6-Akzeptanzkriterium).
- In Phase 4 (`robust`) sind `next_phase_at`, `next_phase_label`, `entries_until_next` = `null`.
- `user_message_key` verweist auf i18n; das Backend erzeugt **nie** direkt user-sichtbaren Text.

---

## 2. Capability-Unlock-Matrix

Welche Insight-Familien und Trend-Visualisierungen sind je Phase sichtbar/aktiv?
`✓` = verfügbar · `◐` = bedingt (zusätzliche Anzahl-/Datenschwelle) · `—` = in dieser Phase gesperrt.

![Capability-Unlock-Matrix](assets/phase_matrix/fig2_capability_matrix.png)

| Capability | P1 `collecting` | P2 `early_patterns` | P3 `provisional` | P4 `robust` | Frontend-Gate (Quelle) |
| --- | :---: | :---: | :---: | :---: | --- |
| Streaks · Raw Counts · Entry History | ✓ | ✓ | ✓ | ✓ | immer (keine Korrelation) |
| Timeseries-Trend (mood/energy/stress) | — | ✓ | ✓ | ✓ | `canShowAdvancedAnalytics(phase)` ≠ `collecting` |
| Häufigkeits-Charts · Tag/Symptom Heatmap | — | ✓ | ✓ | ✓ | `canShowAdvancedAnalytics()` |
| Weekday-Pattern (Wochentag) | — | ✓ | ✓ | ✓ | Engine ab `MIN_WEEKDAY_ENTRIES = 7` |
| Simple Comparisons | — | ✓ | ✓ | ✓ | `canShowAdvancedAnalytics()` |
| Correlation Matrix Tab | — | ◐ | ✓ | ✓ | `canShowMatrixTab()` + `≥ 2` Matrix-Insights |
| Tag Co-occurrence Heatmap | — | ✓ | ✓ | ✓ | `canShowTagCooccurrence()` (early+) |
| Spearman (energy/stress ↔ mood) | — | — | ✓ | ✓ | Engine ab `MIN_BIVARIATE_ENTRIES = 15` |
| Point-biserial (Tag ↔ mood) | — | — | ✓ | ✓ | Engine ab `15` + `ANALYTICS_MIN_TAG_USAGES = 10` |
| Symptom ↔ Mood Association | — | — | ✓ | ✓ | Engine ab `MIN_SYMPTOM_ANALYTICS_ENTRIES = 15` |
| Symptom ↔ Tag Co-occurrence | — | — | ✓ | ✓ | `canShowSymptomCooccurrence()` (provisional+) |
| Dashboard Correlation Summary | — | — | ✓ | ✓ | rendert Korrelationen erst ab `provisional` |
| Robust Insight Cards + Recommendations | — | — | — | ✓ | Tier `robust` ab `ROBUST_ENTRY_COUNT = 30` |
| Multivariate LASSO / Lag (ML) | — | — | — | ◐ | Engine ab `MIN_ML_ENTRIES = 90` |

**Frontend-Gate-Funktionen** (`apps/web/src/lib/utils/insightAnalyticsGate.ts`):

```ts
canShowAdvancedAnalytics(phase)  // phase !== null && phase !== 'collecting'
canShowMatrixTab(phase, insights) // early_patterns+ UND countMatrixInsights(insights) >= 2
canShowTagCooccurrence(phase)     // early_patterns | provisional | robust
canShowSymptomCooccurrence(phase) // provisional | robust
```

`isMatrixInsight()` (`insightMatrixGate.ts`): zählt nur `pointbiserial` / `symptom_mood_association`
mit `effect_size !== null` **und** `confidence >= 0.2`. `MATRIX_TAB_MIN_INSIGHTS = 2`.

> Merke: In Phase 2 ist der Matrix-Tab per Phase-Gate erlaubt (`◐`), aber es existieren praktisch noch keine
> qualifizierenden Insights, weil deren Engine-Schwelle erst bei 15 Tagen greift → Tab bleibt de facto leer,
> bis Phase 3 erreicht ist.

---

## 3. Phasendetails — was der User pro Phase sieht

### Phase 1 — `collecting` (Tag 1–6)

- **Verfügbar:** Streaks, Roh-Counts, Eintragshistorie. **Keine** Korrelationsinhalte, **keine** Trend-Analytics.
- **Empty/Locked-States:** phase-aware, erklären _warum_ (nicht generischer Lock). i18n: `maturity.collecting.*`.
- **Tonalität:** ermutigend („We're building your foundation.") — nie „No data yet".
- **Dev-Fixture:** `phaseFixtures.ts` → 3 Einträge, Insight-Feed leer, Analytics gesperrt.

### Phase 2 — `early_patterns` (Tag 7–13)

- **Neu freigeschaltet:** Timeseries-Trend, Häufigkeits-Charts, Tag-Heatmap, **Weekday-Pattern**, einfache Vergleiche, Tag-Co-occurrence.
- **Bewusst noch gesperrt:** bivariate Korrelationen (Spearman/Point-biserial), Symptom-Analytics, Dashboard-Correlation-Summary.
- **Badge-Beispiel:** „First hint · 7 entries" + Warn-Icon; Tooltip „Based on limited data — patterns may change."
- **Milestone-Card (einmalig):** „🔍 New: First Patterns unlocked!" (i18n: `maturity.milestone.collecting_to_early_patterns`).
- **Dev-Fixture:** 9 Einträge.

### Phase 3 — `provisional` (Tag 14–29)

- **Neu freigeschaltet:** volle bivariate Korrelationen (Spearman, Point-biserial), Symptom↔Mood, Symptom↔Tag-Co-occurrence, Dashboard-Correlation-Summary.
- **Pflicht-UX:** Uncertainty-Ribbon an allen Korrelations-Charts; Badge „Provisional · N entries"; Copy „Early correlation — more data will clarify this."
- **Dev-Fixture:** 21 Einträge.

### Phase 4 — `robust` (Tag 30+)

- **Neu freigeschaltet:** vollwertige Robust-Insight-Cards mit Recommendations; Confidence-Tier `robust`.
- **Bedingt (`◐`):** Multivariate ML (LASSO / Lag) erst ab **90** Eintragstagen — de-facto Sub-Gate innerhalb von Phase 4.
- **UX:** Abschluss-Zustand im Journey-Banner (einmalige Celebration-Animation); Copy „Your data shows a consistent pattern."
- **Dev-Fixture:** 42 Einträge (deckt ML nicht ab; für LASSO/Lag manuell ≥ 90 Tage nötig).

---

## 4. Insight-Katalog — Berechnung, Eingaben, erwartete Aussage

Alle Werte aus `backend/app/services/insight_engine.py`, `multivariate_analytics.py`, `symptom_analytics.py`,
`weekday_confounder.py`. Persistiertes Schema: `backend/app/models/insight.py` (`Insight`).

### 4.0 Gemeinsame Konzepte

- **Grundeinheit:** deduplizierte **Tagesvektoren** (`mood_score`, `energy`, `stress` ∈ 1–5; Tag-/Symptom-Mengen).
  `stress` wird nur in der View invertiert (`display_metric_value`), **roh** in der DB & Berechnung.
- **Temporale Integrität:** Analytics nutzt ausschließlich `entry_date < as_of` (`_load_analytics_inputs`) —
  kein Look-ahead-Bias durch `created_at`/`updated_at` bei nachgetragenen Einträgen.
- **Multiple-Testing-Korrektur:** Benjamini-Hochberg FDR pro Insight-Familie (`_fdr_results`, `FDR_ALPHA = 0.05`;
  Symptom/ML nutzen `α = 0.10`). Nicht-signifikante Kandidaten werden verworfen.
- **Mindest-Effektgröße:** `MIN_ABS_EFFECT_SIZE = 0.25` (bivariate), analog in Symptom-/Lag-Analyse.
- **Confidence-Score** (`_confidence`): `tier_weight · effect_weight · p_weight`, gerundet auf 2 Nachkommastellen,
  wobei `tier_weight` = {early 0.35, preliminary 0.55, developing 0.75, robust 0.95},
  `effect_weight = min(1, |effect|/0.8)`, `p_weight = 1 − p_corrected` (bzw. 0.65 falls kein p-Wert).
  **Wird dem User nie als Zahl gezeigt** (nur als Maturity-Badge, ADR-0018 abgelöst durch ADR-0021).
- **Confounder-Check (Wochentag):** OLS mit Newey-West/HAC-Standardfehlern (`weekday_confounder.py`),
  Mo–Sa-Dummies, Sonntag = Referenz, `MIN_OLS_ROWS = 10`, `α = 0.10`. Ist eine Assoziation nach Wochentags-
  Adjustierung nicht mehr signifikant, wird der Insight mit Hinweis versehen
  („Note: this pattern occurs primarily on specific weekdays.") bzw. bei Co-occurrence als confounded markiert.
- **Sprach-Prinzip:** nie kausal/medizinisch. Immer „pattern / association / co-occurrence, not a cause/diagnosis".

### 4.1 Confidence-Tier-Ladder (interne Verlässlichkeit)

`confidence_tier_for_sample(sample_n)` in `insight_engine.py`:

| Tier | Schwelle (Eintragstage) | Konstante |
| --- | --- | --- |
| `none` | < 3 → keine Insights | — |
| `early` | ≥ 3 | `EARLY_ENTRY_COUNT = 3` |
| `preliminary` | ≥ 8 | `PRELIMINARY_ENTRY_COUNT = 8` |
| `developing` | ≥ 15 | `DEVELOPING_ENTRY_COUNT = 15` |
| `robust` | ≥ 30 | `ROBUST_ENTRY_COUNT = 30` |

Der Tier wird beim Generieren allen an diesem Tag berechneten Kandidaten zugewiesen (`generate_insight_candidates`).

### 4.2 Insight-Familien im Detail

Legende: **Methode** · **Eingangsdaten** · **Min-Schwellen** · **Effektgröße** · **erwartete Aussage** · **`insight_type`**.

---

#### A) Weekday-Pattern — `weekday_pattern`

- **Methode:** Delta des mittleren `mood_score` je Wochentag gegen den Gesamtmittelwert; ausgewählt wird der Wochentag mit größter absoluter Abweichung. (`_weekday_candidates`)
- **Eingangsdaten:** alle Tagesvektoren, gruppiert nach `entry_date.weekday()`.
- **Min-Schwellen:** `MIN_WEEKDAY_ENTRIES = 7`; ausgelöst, wenn `|delta| ≥ MIN_WEEKDAY_DELTA = 0.5`.
- **Effektgröße:** `delta` (Wochentag-Mittel − Gesamtmittel). Kein p-Wert (Flag `method="weekday_delta"`).
- **Payload:** `weekday_mood_avgs`, `weekday_entry_counts`, `overall_mood_avg`, `early_pattern` (bool bei < 15 Tagen).
- **Erwartete Aussage:** „Mondays currently line up with higher/lower mood than your overall average. This is an early calendar pattern, not a diagnosis."
- **Erste Phase mit Sichtbarkeit:** **Phase 2** (`early_patterns`).

#### B) Spearman-Rangkorrelation (Metrik ↔ Metrik) — `spearman`

- **Methode:** `scipy.stats.spearmanr` für die Paare `(energy, mood_score)` und `(stress, mood_score)`; anschließend BH-FDR.
- **Eingangsdaten:** Tagesvektoren; benötigt ≥ 2 verschiedene Werte je Metrik.
- **Min-Schwellen:** `MIN_BIVARIATE_ENTRIES = 15`; `|rho| ≥ 0.25`; signifikant nach FDR (`α = 0.05`).
- **Effektgröße:** `rho`. Payload: `left_metric`, `right_metric`, `rho`, `p_corrected`.
- **Erwartete Aussage:** „In your entries so far, energy tends to be higher/lower when mood is higher. This is a data pattern, not a diagnosis."
- **Erste Phase mit Sichtbarkeit:** **Phase 3** (`provisional`) — obwohl Phase 3 ab Tag 14 beginnt, greift die Engine erst ab 15.

#### C) Point-biserial (Tag ↔ Mood) — `pointbiserial`

- **Methode:** `scipy.stats.pointbiserialr` zwischen Tag-Präsenz (binär) und `mood_score`; BH-FDR + Wochentags-Confounder-Check.
- **Eingangsdaten:** Tagesvektoren + Tag-Zuordnungen (aktive Tags, Alias-kanonisiert via Slug).
- **Min-Schwellen:** `MIN_BIVARIATE_ENTRIES = 15`; getaggte Tage ≥ `ANALYTICS_MIN_TAG_USAGES = 10`; ungetaggte Tage ≥ `MIN_TAG_GROUP_SIZE = 2`; `|coef| ≥ 0.25`.
- **Effektgröße:** `coefficient`. Payload: `tagged_count`, `untagged_count`, `tagged_mood_avg`, `untagged_mood_avg`, `p_corrected`; Flag `weekday_confounded`.
- **Erwartete Aussage:** „Days tagged Walk currently line up with higher mood scores in your data. Treat this as a pattern to reflect on, not a cause." (+ ggf. Wochentags-Hinweis)
- **Erste Phase mit Sichtbarkeit:** **Phase 3**. Speist zusammen mit (D) die **Correlation-Matrix** (ab 2 qualifizierenden Insights mit `confidence ≥ 0.2`).

#### D) Symptom ↔ Mood/Energy/Stress-Association — `symptom_mood_association`

- **Methode:** Point-biserial Symptom-Präsenz ↔ Metrik (`compute_symptom_metric_associations`); BH-FDR (`α = 0.10`) + Wochentags-Confounder.
- **Eingangsdaten:** Tagesvektoren + Symptom-Zuordnungen (`intensity > 0`).
- **Min-Schwellen:** `MIN_SYMPTOM_ANALYTICS_ENTRIES = 15`; Symptom-Tage ≥ `MIN_SYMPTOM_USAGES = 5` (und Vergleichsgruppe ≥ 5); `|coef| ≥ 0.25`.
- **Effektgröße:** `coefficient`. Payload u.a. `symptom_metric_avg`, `comparison_metric_avg`, `symptom_n`, `comparison_n`, `confounder`.
- **Erwartete Aussage:** „Days with Headache currently line up with lower energy in your data. Treat this as an association, not a cause."
- **Erste Phase mit Sichtbarkeit:** **Phase 3**.

#### E) Symptom ↔ Tag Co-occurrence — `symptom_tag_cooccurrence`

- **Methode:** Kontingenz (Fisher/Lift) mit `phi`, `jaccard`, `lift`; BH-FDR (`α = 0.10`) + Wochentags-Confounder für Paare (`is_pair_cooccurrence_weekday_confounded`).
- **Eingangsdaten:** Symptom- und Tag-Präsenz pro Tag.
- **Min-Schwellen:** `MIN_SYMPTOM_ANALYTICS_ENTRIES = 15`; Symptom ≥ 5 & Tag ≥ 5 Nutzungen; Karten-Schwelle `MIN_CARD_LIFT_DELTA = 0.67`, Heatmap `MIN_HEATMAP_LIFT_DELTA = 0.50`.
- **Effektgröße:** `phi` (fällt auf `lift − 1` zurück, falls `phi == 0`). Payload: `phi`, `jaccard`, `lift`, `co_count`, Einzel-Counts.
- **Erwartete Aussage:** „Headache currently appears together with Coffee more than expected from their individual frequencies. This is a co-occurrence pattern, not a cause."
- **Erste Phase mit Sichtbarkeit:** **Phase 3** (Frontend-Gate `canShowSymptomCooccurrence` = provisional+).

#### F) Multivariate LASSO — `symptom_cluster` (payload `method="lasso"`)

- **Methode:** LASSO-Regression über Design-Matrix aller Signale; TimeSeriesSplit-CV (`TIMESERIES_SPLITS = 5`). (`run_lasso_models`)
- **Eingangsdaten:** Tagesvektoren + Tags + Symptome (binäre Features ab `MIN_BINARY_FEATURE_USAGES = 5`).
- **Min-Schwellen:** `MIN_ML_ENTRIES = 90`; `|coef| ≥ MIN_ABS_LASSO_COEFFICIENT = 0.05`.
- **Effektgröße:** größter absoluter Koeffizient. Payload: Top-Features + Koeffizienten, `alpha`, `cv_score`.
- **Erwartete Aussage:** „Across your tracked signals, mood currently varies most with Walk, Coffee, Sleep. This is a multivariate pattern, not a cause."
- **Erste Phase mit Sichtbarkeit:** **Phase 4**, aber erst ab **90** Eintragstagen (`◐`).

#### G) Lag-Analyse (zeitversetzt) — `symptom_cluster` (payload `method="lag"`)

- **Methode:** Kreuzkorrelation Feature(t−k) ↔ Target(t) über Lags 1..`MAX_LAG_DAYS = 7`; BH-FDR (`LAG_FDR_ALPHA = 0.10`). (`run_lag_analysis`)
- **Eingangsdaten:** wie (F); benötigt `MIN_LAG_OBSERVATIONS = 10` je Lag-Paar.
- **Min-Schwellen:** `MIN_ML_ENTRIES = 90`; `|correlation| ≥ MIN_ABS_LAG_CORRELATION = 0.25`.
- **Effektgröße:** `correlation`. Payload: `lag_days`, `feature`, `target`, `p_value_corrected`.
- **Erwartete Aussage:** „Poor sleep logged 1 day(s) earlier currently lines up with lower mood. Treat this as a time-shifted pattern, not a cause."
- **Erste Phase mit Sichtbarkeit:** **Phase 4** (≥ 90 Tage).

---

## 5. Bekannte Schwellen-Divergenzen & Gotchas

1. **Phase-Grenze ≠ Engine-Grenze.** Phase 3 startet bei 14 Tagen, bivariate/Symptom-Analytics aber erst bei **15**
   (`MIN_BIVARIATE_ENTRIES` / `MIN_SYMPTOM_ANALYTICS_ENTRIES`). → Am Tag 14 ist die Phase „provisional", der Insight-Feed
   kann jedoch noch leer sein. Empty-State muss das abfangen.
2. **Matrix-Tab in Phase 2 leer.** Gate erlaubt ab `early_patterns` (`◐`), qualifizierende Insights entstehen aber frühestens
   in Phase 3. Nicht als Bug melden.
3. **ML als Sub-Gate.** LASSO/Lag hängen an `MIN_ML_ENTRIES = 90`, nicht an der Phase. Dev-Fixture `robust` (42) deckt das nicht ab.
4. **`ANALYTICS_MIN_TAG_USAGES = 10`** ist bewusst strenger als die globale Tier-Schwelle — ein selten genutzter Tag erzeugt nie einen Insight.
5. **Zwei „robust".** `InsightTier.ROBUST` (Engine) ≠ `InsightMaturityPhase.ROBUST` (Phase). Beide bei 30, aber unterschiedliche Bedeutung.
6. **Frontend rechnet nicht.** Phase kommt immer aus der API (`insight_maturity`). Gates in `insightAnalyticsGate.ts` konsumieren nur den gelieferten Phase-Key.

---

## 6. Erweiterbarkeit — geplante & künftige Dimensionen

Das Modell ist bewusst additiv. Beim Hinzufügen einer neuen Insight-/Trend-Dimension sind folgende Stellen zu berühren:

**Checkliste „neuer Insight-Typ / neue Kontext-Dimension"**

- [ ] `InsightType` in `backend/app/models/insight.py` ergänzen (+ Alembic-Migration wie `014_/015_`).
- [ ] Compute-Funktion + Statement in `insight_engine.py` (oder Fach-Service) mit **eigenen** Min-Schwellen & FDR-Familie.
- [ ] In `generate_insight_candidates()` einhängen (Tier wird global gesetzt).
- [ ] Phase-Zuordnung in dieser Matrix (§2) + ggf. neues Gate in `insightAnalyticsGate.ts`.
- [ ] i18n-Keys (`maturity.*` bzw. neue `insight.*`), Copy-Tonalität je Phase (nicht-kausal).
- [ ] Dev-Fixture in `phaseFixtures.ts` erweitern (GUI-QA je Preset).
- [ ] DSGVO-Checkpoint: keine sensiblen Rohdaten in `insight_maturity`/Notification-Payloads.

### Bereits vorgesehene, noch nicht (voll) ausgewertete Dimensionen

| Dimension | Status im Code | Geplante Auswertung | Erwartete Aussage (später) |
| --- | --- | --- | --- |
| **Wochentag** | Feld vorhanden; `weekday_pattern`-Insight aktiv; Confounder-Check produktiv | Erweiterung zu Wochentag-Segmenten je Metrik/Tag | „An welchen Wochentagen häufen sich bestimmte Muster" |
| **Office/Homeoffice-Kontext** (`entries.work_context`: `homeoffice` / `office` / `vacation` / `sick` / `weekend` / `travel`) | **Feld existiert** (Design §2.7), fließt noch **nicht** in einen eigenen Insight-Typ ein | Kategoriale Assoziation `work_context ↔ mood/energy/stress` (analog Point-biserial/ANOVA), als eigener `insight_type` z.B. `work_context_association` | „Büro-Tage stehen mit niedrigerer/höherer Stimmung in Zusammenhang als Homeoffice-Tage" |
| **Schlaf/Wearables** (Garmin/Health Connect, Design §2.8) | v1 manuell; Import geplant | Schlafdauer/-qualität, HRV, Ruhepuls als Features in Spearman/LASSO/Lag | „Schlafqualität am Vortag hängt mit heutiger Energie zusammen" (zeitversetzt) |
| **Zyklus-Tracking** (ADR-0031/0032/0033) | als Domain-Extension modelliert | sensible Behandlung, opt-in | phasenbezogene Muster mit strengem Sensibilitäts-Handling |
| **Fotos/Medien** (M13) | post-SaaS-Backlog | keine Analytik in Kernpfad | — |

> **Design-Prinzip für neue Dimensionen:** Jede neue Dimension erhält (a) eine **Phase-Sichtbarkeit** in §2,
> (b) **eigene statistische Min-Schwellen** (nicht die globale Tier-Grenze wiederverwenden), (c) einen
> **Wochentags-/Confounder-Check**, wo eine Verwechslung plausibel ist, und (d) nicht-kausale Copy je Phase.

---

## 7. Quellen (Repo-intern)

- Phasenmodell / API-Vertrag: `docs/adr/0021-insight-maturity-phases.md`, `docs/frontend/INSIGHT_MATURITY.md`, `docs/DESIGN_DOCUMENT.md` (§ „Insight Maturity", M3.6)
- Phasenberechnung: `backend/app/services/insight_service.py` → `calculate_insight_maturity()`
- Schema/Modell: `backend/app/schemas/insight.py`, `backend/app/models/insight.py`
- Insight-Engine: `backend/app/services/insight_engine.py`
- Fach-Services: `backend/app/services/symptom_analytics.py`, `backend/app/services/multivariate_analytics.py`, `backend/app/services/weekday_confounder.py`
- Frontend-Gates: `apps/web/src/lib/utils/insightAnalyticsGate.ts`, `insightMatrixGate.ts`, `insightMaturityMilestones.ts`
- Dev-QA-Fixtures: `apps/web/src/lib/dev/phaseFixtures.ts`
- Office/Wearables/Zyklus (geplant): `docs/DESIGN_DOCUMENT.md` §2.7/§2.8, ADR-0031/0032/0033

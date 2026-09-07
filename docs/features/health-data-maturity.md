# Feature Spec: Health Data Maturity (Trends „Health Context")

**Status:** Draft — NICHT eingefroren (Spec-Dialog zu Issue #852)
**Version:** 0.1.0
**Created:** 2026-09-07
**Updated:** 2026-09-07
**Owner:** @Sturmi77
**Tracking-Issue:** [#852](https://github.com/Sturmi77/correlcore/issues/852) — „[UX] Trends Gesundheitsbereitschaft zeigt nur Kontinuitäts-Tage"
**Richtung (entschieden):** **C-full** — dediziertes Backend-DTO + Spec, ersetzt die Ad-hoc-Streak-Anzeige.

---

## 0. Legende & Status dieses Dokuments

Dieses Dokument ist ein **Spec-Entwurf im Dialog**. Bereits getroffene Entscheidungen sind
als **[ENTSCHIEDEN]** markiert, noch offene Forks als **[OFFEN]** mit einer Empfehlung.
Die Spec gilt erst als _freezebar_, wenn (a) alle **[OFFEN]**-Punkte aufgelöst und (b) die
drei Beispiel-Fixtures (§9) ohne Diskussion passen (Issue-Schritt 4 + 5).

Änderungen an Formeln, Fenstern oder Gates nach dem Freeze nur mit Spec-Diff (Issue-Schritt 5).

---

## 1. Zweck & Non-Goals

### 1.1 Problem (Ist-Zustand)

Der Trends-Block `TrendsHealthContext.svelte` trägt den Titel „Gesundheitsbereitschaft"
(`trends.health.heading`), zeigt darunter aber ausschließlich rohe Eintrags-Streak-Zahlen
(`current_streak`, `longest_streak`, `total_entry_days` aus `EntryStreakResponse`) plus optional
einen Cycle-Strip. Titel und Inhalt sind entkoppelt → **Naming-/Promise-Schuld**. Zusätzlich
verletzen die großen Rekord-Zahlen (z. B. 122) die No-Gamification-Policy:

- `docs/FRONTEND.md`: „**No** streak counters anywhere in the UI"; die Berechnung ist explizit als
  „Tracking consistency calculation (**not streak**)" dokumentiert.
- [ADR-0012](../adr/0012-m2-m5-streak-semantik.md): „Streak" ist für M5-Habits reserviert; die
  M2-Größe ist eine reine **Eintrags-Streak** ohne Health-Semantik. Habit-Streaks/Badges/Punkte sind
  zugunsten von Adherence verworfen.
- [ADR-0017](../adr/0017-frontend-screen-architecture.md): Home-Streak-Widget entfernt.

### 1.2 Ziel

Unter einem **ehrlichen Titel** echte, schon vorhandene Signale zur **Datenreife / Abdeckung** der
Gesundheitsdaten zeigen — geliefert durch ein **dediziertes Backend-DTO**, damit Trends (und ggf.
später Home) dieselbe Quelle konsumieren. „Bereitschaft" bedeutet hier **Datenreife / Abdeckung**,
niemals physiologische oder medizinische Bereitschaft.

### 1.3 Non-Goals

- **Kein** 0–100 „Gesundheits-Score", **keine** Ampel-Physiologie, **kein** Wearable-Readiness-Score
  (kein Whoop-Äquivalent).
- **Keine** gamifizierenden Streak-Rekord-Zahlen (FRONTEND.md / ADR-0012).
- **Keine** diagnostische Bereitschaft, **keine** Cycle-Phasen-Inferenz.
- **Keine** Doppel-Dashboards zu Insights-Symptom-Analytics oder zum Health-Connect-Hub — dieser Block
  ist ein **Reife-/Abdeckungs-Überblick mit Deep-Links**, keine zweite Analyse-Oberfläche (§7).

---

## 2. Signal-Set [ENTSCHIEDEN]

Vier Signale, alle aus **bereits vorhandenen** Quellen (kein neuer Score, keine neue Statistik):

| # | Signal | Quelle (Ist) | Bedeutung |
| - | ------ | ------------ | --------- |
| 1 | **Maturity-Phase** | `insight_maturity` (Insights-Service, Backend-owned) | Wie weit ist die Insight-Engine? `collecting → early_patterns → provisional → robust` |
| 2 | **Entry-Coverage %** | `entries.entry_date` im Fenster | Anteil Tage mit ≥1 Eintrag — neutrales Konsistenz-Signal, **ersetzt** die Streak-Rekorde |
| 3 | **Sleep-Coverage %** | Timeseries `sleep_quality_avg` / Entry `sleep_*` im Fenster | Anteil Tage mit Sleep-Wert — erklärt, warum Sleep-Insights ggf. noch fehlen |
| 4 | **Symptom-Coverage %** | Symptom-Heatmap `days[].count` im Fenster | Anteil Tage mit ≥1 Symptom-Log — Dichte, **nicht** Inhalt |

**Grundsatz (Issue):** Streichen, was wir nicht ehrlich erklären können. Alle vier sind erklärbar und
belegbar aus dem Repo.

---

## 3. Metrik-Tabelle (Formeln, Fenster, Min-n, Darstellung)

> **Fenster/Gate-Kopplung ist [OFFEN] — siehe §4.** Die Zahlen unten sind die realen Engine-Schwellen
> aus dem Code und dienen als Kandidaten für die Kopplung.

| Metrik | Formel | Fenster | Min-n / Schwelle (Code-Referenz) | UI-Darstellung |
| ------ | ------ | ------- | -------------------------------- | -------------- |
| `maturity_phase` | direkt aus `insight_maturity.phase` (nicht neu berechnen!) | Engine-intern | Phasen bei 7 / 14 / 30 Entries (`insight_service.py` `next_phase_at`) | Phasen-Chip + „noch N Einträge bis X" |
| `entry_coverage_pct` | `Tage mit ≥1 entry / Fensterlänge` | **[OFFEN] §4** | — (immer anzeigbar) | Neutraler %-Meter + „X von Y Tagen" |
| `sleep_coverage_pct` | `Tage mit sleep-Wert / Fensterlänge` | **[OFFEN] §4** | Engine-Sleep-Gate: Coverage ≥ **0.5** **und** ≥ **15** Beobachtungen (`multivariate_analytics.py` `MIN_SLEEP_COLUMN_COVERAGE=0.5`, `MIN_SLEEP_COLUMN_OBSERVATIONS=15`) | %-Meter + „Sleep-Insights ab 50 % Abdeckung" |
| `symptom_coverage_pct` | `Tage mit ≥1 Symptom-Log / Fensterlänge` | **[OFFEN] §4** | Symptom-Analytics ab **15** Entries (`symptom_analytics.py` `MIN_SYMPTOM_ANALYTICS_ENTRIES=15`) | %-Meter + Deep-Link Insights-Symptom |

**No-Streak-Regel:** Entry-Coverage wird **nur** als „X von Y Tagen" / % dargestellt — **keine**
„Beste Kontinuität"/Rekord-Zahl, kein 🔥, keine Red/Green-Ampel (FRONTEND.md, ADR-0035 divergent-scale).

---

## 4. Fenster & Gate-Kopplung [OFFEN]

Es gibt **kein** einheitliches „Engine-Fenster" — der Code nutzt mehrere:

| Kontext | Fenster / Schwelle | Datei |
| ------- | ------------------ | ----- |
| Maturity-Phasen | 7 / 14 / 30 Entries (kumulativ, kein Zeitfenster) | `insight_service.py` |
| Symptom-Analytics | ≥ 15 Entries | `symptom_analytics.py` |
| Sleep-Spalte (multivariat) | Coverage ≥ 0.5 & ≥ 15 Beobachtungen | `multivariate_analytics.py` |
| Tag-Cluster | 90-Tage-Fenster; provisional 45 / robust 90 Entries | `tag_cluster_service.py` |
| Changepoint | ≥ 60 Entries | `changepoint.py` |

**Empfehlung (zur Entscheidung):**
- **Coverage-Fenster:** rollierend **90 Tage** (deckungsgleich mit Tag-Cluster-Fenster, glättet lange
  Historie, macht die „122-Tage-Zahl" gegenstandslos). `coverage_window_days` als DTO-Feld (Default 90)
  ausliefern, damit UI es beschriften kann.
- **Gates:** pro Sektion an den **echten Feature-Threshold** koppeln (Symptom ab 15 Entries, Sleep ab
  0.5/15, Cluster ab 45/90) statt an eine Sammel-Phase — so bleibt die Freischaltung konsistent mit dem,
  was die Engine tatsächlich rechnet.

**Zu entscheiden:** 90 vs. 30 Tage; Feature-Threshold-Gates vs. Maturity-Phase-Gates; ob
`coverage_window_days` konfigurierbar ist.

---

## 5. Progressive Disclosure / Gates [ENTSCHIEDEN: explizite Flags + Copy-Keys]

Das DTO liefert **explizite Gate-Flags** samt Begründung; das Frontend **rendert nur** und berechnet
keine Schwellen (FRONTEND.md: „frontend components must not recompute the phase from entry count").

Pro Sektion:
- `unlocked: boolean`
- `reason: enum` (`ok` | `insufficient_entries` | `insufficient_coverage` | `no_consent` | …)
- `entries_until_unlock: int | null` (für „noch N Einträge")
- `copy_key: string` (i18n-Key für Insufficient-/Empty-Text; kein freier Text im DTO)

---

## 6. API-Shape [ENTSCHIEDEN: neues DTO/Endpoint — Feinschliff offen]

**Neuer, dedizierter Endpoint** (ein Owner, cachebar, saubere Trennung von `stats`).

- **Pfad (Vorschlag, [OFFEN] Feinschliff mit Backend):** `GET /api/v1/entries/stats/health-context`
  oder `GET /api/v1/health/context`.
- **Auth:** wie übrige Stats-Endpoints (Session/Cookie).
- **Caching:** kurzlebig (z. B. 5–15 min), da rein abgeleitet; ETag optional.

**Response (Entwurf):**

```jsonc
{
  "as_of": "2026-09-07",
  "coverage_window_days": 90,
  "maturity": {
    "phase": "provisional",           // aus insight_maturity, NICHT neu berechnet
    "current_entries": 52,
    "next_phase_at": 30,              // Backend-owned
    "entries_until_next": 0
  },
  "coverage": {
    "entry":   { "days_with_data": 61, "window_days": 90, "pct": 0.68 },
    "sleep":   { "days_with_data": 30, "window_days": 90, "pct": 0.33 },
    "symptom": { "days_with_data": 44, "window_days": 90, "pct": 0.49 }
  },
  "sections": [
    { "id": "symptom", "unlocked": true,  "reason": "ok",                    "entries_until_unlock": null, "copy_key": "trends.maturity.symptom.ok" },
    { "id": "sleep",   "unlocked": false, "reason": "insufficient_coverage", "entries_until_unlock": null, "copy_key": "trends.maturity.sleep.insufficient" }
  ],
  "health_connect": null              // [OFFEN] §8 — optionales Meta-Signal
}
```

**Fehler:** `401` (unauth), `200` mit leeren/`unlocked:false`-Sektionen für Neu-User (kein `404` bei
„zu wenig Daten"). **Keine** Klartext-Symptom-/Sleep-Werte im Payload (§8).

---

## 7. UI-Wire & Abgrenzung

### 7.1 Surfaces [OFFEN]

**Empfehlung:** v1 **Trends-only** (Block ersetzt die heutige Streak-Anzeige in
`TrendsHealthContext.svelte`). DTO bewusst **surface-agnostisch** halten, damit Home später ein
kompaktes Signal konsumieren kann — **aber** ohne Maturity-Journey-Banner/Streak auf Home
(FRONTEND.md verbietet das dort).

### 7.2 Panel-Aufbau (Trends)

- Titel/Copy (**[OFFEN] §Label**) statt „Gesundheitsbereitschaft".
- Maturity-Chip + 3 Coverage-Meter (entry/sleep/symptom), jeweils mit Insufficient-Copy aus `copy_key`.
- Deep-Links: Insights-Symptom-Bereich, Health-Connect-Hub (`/health-connect`).

### 7.3 Label [OFFEN]

Arbeitstitel „Datenreife Health". **Empfehlung:** DE **„Datenreife"**, EN **„Data readiness"** oder
**„Health data coverage"**. Zu entscheiden + i18n-Keys festziehen (`trends.health.*` → neue Keys).

### 7.4 Cycle-Strip [OFFEN]

**Empfehlung:** als **neutraler Kontext** klar getrennt (eigene Sektion/Überschrift), **nicht** als
Readiness-/Reife-Faktor gewertet. Migration in eigenen Bereich möglich; Beachtung von
[ADR-0031](../adr/0031-cycle-tracking-scope.md)/[ADR-0033](../adr/0033-sensitive-health-data-handling-cycle-signals.md).

### 7.5 Abgrenzung (keine Doppel-Dashboards)

Dieser Block zeigt **Reife/Abdeckung + Deep-Links**, **nicht** die Analyse selbst. Symptom-Muster leben
in Insights-Symptom-Analytics; Wearable-Import/Consent lebt im HC-Hub.

---

## 8. Privacy / Logging

- **Art. 9 / DSGVO:** keine Klartext-Symptomnamen, keine konkreten Sleep-Werte in DTO **oder Logs** —
  nur **Zähler/Anteile** (`days_with_data`, `pct`). (Issue C-full DoD: „keine Art.-9-Leaks in Logs".)
- **Health-Connect-Status [OFFEN]:** falls aufgenommen, nur `consent: bool`, `last_sync_at`,
  `sleep_import_ok: bool` — **keine** importierten Gesundheitswerte. HC ist consent-gated (403 ohne
  Consent, `HEALTH_CONNECT.md`). **Empfehlung:** als optionales Feld vorsehen, Anzeige v1 optional.

---

## 9. Beispiel-Fixtures [SPÄTER — Freeze-Kriterium]

Drei User-Profile als JSON-Fixtures mit erwarteter Panel-Ausgabe; Spec gilt erst als freezebar, wenn
alle drei ohne Diskussion passen (Issue-Schritt 4):

1. **Neu** (< 7 Entries): Phase `collecting`, alle Sektionen `unlocked:false`, Coverage niedrig.
2. **Sleep-arm** (viele Entries, wenig Sleep): Symptom unlocked, Sleep `insufficient_coverage`.
3. **Symptom-reich**: Symptom + Maturity hoch, Sleep mittel.

_(Werte werden nach Auflösung von §4 ergänzt.)_

---

## 10. Definition of Done (C-full, aus Issue)

- [ ] Diese Spec (Metriken, Fenster, Gates, Non-Goals) merged **oder** als Issue-AC eingefroren.
- [ ] Backend-DTO + Tests (Coverage-Formeln, keine Art.-9-Leaks in Logs).
- [ ] Trends-Panel an DTO; Streak-Placeholder entfernt/entschärft.
- [ ] Contract-/UI-Tests (`trends/page.test.ts` + Komponenten-/API-Tests).
- [ ] Titel und Inhalt deckungsgleich; keine gamifizierenden Streak-Rekord-Zahlen.
- [ ] Cycle-Overlay klar getrennt oder mit migriert.

---

## 11. Offene Entscheidungen (Decision-Log)

| # | Frage | Status | Empfehlung |
| - | ----- | ------ | ---------- |
| D1 | Surfaces: Trends-only vs. auch Home | **OFFEN** | Trends-only v1, DTO surface-agnostisch |
| D2 | Label DE/EN | **OFFEN** | „Datenreife" / „Data readiness" |
| D3 | Cycle-Strip: getrennt / auslagern / mit migrieren | **OFFEN** | getrennt, neutraler Kontext |
| D4 | Coverage-Fenster 90 vs. 30 Tage | **OFFEN** | 90 Tage (wie Tag-Cluster) |
| D5 | Gates: Feature-Threshold vs. Maturity-Phase | **OFFEN** | Feature-Threshold (15 / 0.5·15 / 45·90) |
| D6 | Health-Connect-Status ins DTO? | **OFFEN** | optionales Feld, Anzeige v1 optional |
| D7 | Endpoint-Pfad `/entries/stats/health-context` vs. `/health/context` | **OFFEN** | mit Backend im Review-Gate |

---

## Referenzen

- Issue [#852](https://github.com/Sturmi77/correlcore/issues/852)
- [ADR-0012](../adr/0012-m2-m5-streak-semantik.md) — Streak-Semantik / No-Gamification
- [ADR-0017](../adr/0017-frontend-screen-architecture.md) — Frontend-Screen-Architektur
- [ADR-0021](../adr/0021-insight-maturity-phases.md) — Insight-Maturity-Phasen
- [ADR-0025](../adr/0025-symptom-analytics.md) — Symptom-Analytics
- `docs/FRONTEND.md` — No-Streak-Policy, Maturity-Rendering
- `docs/features/symptom-analytics.md`, `docs/features/HEALTH_CONNECT.md`
- Code: `apps/web/src/lib/components/trends/TrendsHealthContext.svelte`,
  `backend/app/services/insight_service.py`, `symptom_analytics.py`, `multivariate_analytics.py`,
  `tag_cluster_service.py`

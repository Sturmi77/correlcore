# Feature Spec: Health Data Maturity (Trends „Health Context")

**Status:** Umgesetzt (C-full Phase 1–3) — Backend-DTO + Trends-Panel live, Tests grün; offen: Review-Gate + finaler 360px-Geräte-Check
**Version:** 1.0.0
**Created:** 2026-09-07
**Updated:** 2026-09-07
**Owner:** @Sturmi77
**Tracking-Issue:** [#852](https://github.com/Sturmi77/correlcore/issues/852) — „[UX] Trends Gesundheitsbereitschaft zeigt nur Kontinuitäts-Tage"
**Richtung (entschieden):** **C-full** — dediziertes Backend-DTO + Spec, ersetzt die Ad-hoc-Streak-Anzeige.

---

## 0. Legende & Status dieses Dokuments

Dieses Dokument ist ein **Spec-Entwurf im Dialog**. Bereits getroffene Entscheidungen sind
als **[ENTSCHIEDEN]** markiert, noch offene Forks als **[OFFEN]** mit einer Empfehlung.
Stand v1.0.0-rc: (a) alle **[OFFEN]**-Punkte sind aufgelöst und (b) die drei Beispiel-Fixtures (§9)
sind ausformuliert und folgen ohne Diskussion aus §3–§5. Damit ist die Spec inhaltlich freezebar;
es fehlt nur noch das Review-Gate (Issue-Schritt 5).

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

## 4. Fenster & Gate-Kopplung [ENTSCHIEDEN]

Es gibt **kein** einheitliches „Engine-Fenster" — der Code nutzt mehrere:

| Kontext | Fenster / Schwelle | Datei |
| ------- | ------------------ | ----- |
| Maturity-Phasen | 7 / 14 / 30 Entries (kumulativ, kein Zeitfenster) | `insight_service.py` |
| Symptom-Analytics | ≥ 15 Entries | `symptom_analytics.py` |
| Sleep-Spalte (multivariat) | Coverage ≥ 0.5 & ≥ 15 Beobachtungen | `multivariate_analytics.py` |
| Tag-Cluster | 90-Tage-Fenster; provisional 45 / robust 90 Entries | `tag_cluster_service.py` |
| Changepoint | ≥ 60 Entries | `changepoint.py` |

**Entscheidungen (D4 / D5):**
- **Coverage-Fenster [D4]:** rollierend **90 Tage** (deckungsgleich mit Tag-Cluster-Fenster, glättet lange
  Historie, macht die „122-Tage-Zahl" gegenstandslos). `coverage_window_days` wird als DTO-Feld
  (fest **90**, nicht per Query konfigurierbar in v1) ausgeliefert, damit die UI es beschriften kann.
- **Gate-Kopplung [D5 — Hybrid]:** Zwei Ebenen:
  1. **Maturity-Phase** (`collecting → early_patterns → provisional → robust`) dient als **grobe
     Fortschritts-/Kontext-Anzeige**. Diese Ebene wird **nicht neu gebaut**, sondern durch
     Wiederverwendung der bestehenden Komponente **`InsightStageHeader`** dargestellt (siehe §7.6 / G1) —
     es darf keine zweite Readiness-Fläche entstehen (FRONTEND.md:352).
  2. Die **tatsächliche Sektions-Freischaltung** (`unlocked`) hängt am **echten Feature-Threshold**:
     Symptom ab 15 Entries, Sleep ab Coverage ≥ 0.5 **und** ≥ 15 Beobachtungen, (später) Cluster 45/90.

  Damit zeigt der Reife-Kopf den Gesamtfortschritt, während jede Sektion unabhängig freischaltet —
  konsistent mit dem, was die Engine je Feature wirklich rechnet. Das Backend bleibt einziger Owner
  beider Ebenen; das Frontend rendert nur (§5).

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

## 6. API-Shape [ENTSCHIEDEN]

**Neuer, dedizierter Endpoint** (ein Owner, cachebar, saubere Trennung von `stats`).

- **Pfad [D7]:** `GET /api/v1/entries/stats/health-context` — reiht sich in die bestehende
  Stats-Namensfamilie ein (`timeseries`, `tag/symptom-heatmap`, `streak`).
- **Auth:** wie übrige Stats-Endpoints (Session/Cookie).
- **Caching:** kurzlebig (z. B. 5–15 min), da rein abgeleitet; ETag optional.
- **Gates:** `sections[].unlocked` folgt der Hybrid-Regel aus §4/§5 (Feature-Threshold), `maturity.phase`
  liefert die grobe Fortschrittsebene.

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

### 7.1 Surfaces [ENTSCHIEDEN — D1]

v1 ist **Trends-only**: der Block ersetzt die heutige Streak-Anzeige in `TrendsHealthContext.svelte`.
Das DTO wird bewusst **surface-agnostisch** gehalten, damit Home später ein kompaktes Signal konsumieren
kann — **aber** ohne Maturity-Journey-Banner/Streak auf Home (FRONTEND.md verbietet das dort). Home ist
in v1 **kein** Scope.

### 7.2 Panel-Aufbau (Trends)

- Titel/Copy (**[OFFEN] §Label**) statt „Gesundheitsbereitschaft".
- Maturity-Chip + 3 Coverage-Meter (entry/sleep/symptom), jeweils mit Insufficient-Copy aus `copy_key`.
- Deep-Links: Insights-Symptom-Bereich, Health-Connect-Hub (`/health-connect`).

### 7.3 Label [ENTSCHIEDEN — D2]

DE **„Datenreife"**, EN **„Data readiness"**. Die i18n-Keys werden neu gezogen: `trends.health.heading`
und `trends.health.body` werden umtextet (oder auf neue `trends.maturity.*`-Keys migriert); die alten
`trends.consistency.*`-Streak-Labels entfallen im Panel.

### 7.4 Cycle-Strip [ENTSCHIEDEN — D3]

Der Cycle-Strip bleibt im Panel, aber als **eigene Sektion „neutraler Kontext"** klar getrennt und
**nicht** als Readiness-/Reife-Faktor gewertet (siehe Mockup, Profil „Symptom-reich"). Beachtung von
[ADR-0031](../adr/0031-cycle-tracking-scope.md)/[ADR-0033](../adr/0033-sensitive-health-data-handling-cycle-signals.md).
Eine spätere Auslagerung in einen eigenen Bereich bleibt möglich, ist aber v1 nicht nötig.

### 7.5 Abgrenzung (keine Doppel-Dashboards)

Dieser Block zeigt **Reife/Abdeckung + Deep-Links**, **nicht** die Analyse selbst. Symptom-Muster leben
in Insights-Symptom-Analytics; Wearable-Import/Consent lebt im HC-Hub.

### 7.6 UI-Konventionen (Abgleich mit realem UI — G1–G6)

Aus dem Abgleich Mockup ↔ echte Komponenten (`InsightStageHeader.svelte`) + FRONTEND.md. Diese Regeln
sind **verbindlich** für die Implementierung:

| # | Regel | Referenz |
| - | ----- | -------- |
| **G1** | **Keine zweite Readiness-Fläche.** Die Reife/Phase wird ausschließlich über die geteilte Komponente **`InsightStageHeader`** dargestellt (wiederverwenden, nicht nachbauen). Alternativ nur Deep-Link zu Insights. | FRONTEND.md:352 „only default phase/readiness surface" |
| **G2** | **Keine Emoji** in Progress-/Lock-/Warn-Anzeigen. Lucide-Icons (`@lucide/svelte`, z. B. `Lock`, `HelpCircle`). | FRONTEND.md:601, :73/:77 |
| **G3** | Coverage-Balken als **`role="meter"`** mit `aria-valuemin/max/now` + `aria-label` (analog `.stage__track`). | `InsightStageHeader.svelte:78-85` |
| **G4** | Interaktive Elemente (Deep-Links, Hilfe) mit **≥ 44px** Trefferfläche. | `.stage__text-button { min-height: 44px }` |
| **G5** | **Bestehende i18n-Keys wiederverwenden** (`maturity.{phase}.label`, `maturity.journey.compact_entries_until_next`, `insights.stage.readiness_label`) statt neuer Reife-Copy — verhindert Wording-Drift. | en/de.json `maturity.*` |
| **G6** | Falls Reife-Kopf gerendert wird: exakter Stil der Komponente (`N/4`-Marker, `--color-text-inverse`, `--radius-full`), keine Bespoke-Chips. | `InsightStageHeader.svelte` |
| **G7** | **Mobile-first responsiv.** Panel primär für schmale Viewports (~360–430px) ausgelegt: Reife-Kopf-Zeile darf umbrechen / Controls stapeln (analog Komponenten-Breakpoints `@media 767px` + `360px`), Coverage-Meter volle Breite, Metrik-Fußzeile (Note + Deep-Link) umbruchsicher, **kein** horizontaler Seiten-Scroll; Cycle-Strip scrollt in eigenem Container (`overflow-x`). Desktop ist die Aufweitung, nicht der Ausgangspunkt. | FRONTEND.md „mobile-first"; `InsightStageHeader.svelte:238-267` |

**Bereits konform (kein Handlungsbedarf):** einfarbige Meter-Skala ohne Rot/Grün-Urteil
(FRONTEND.md/ADR-0035), keine Streak-Rekorde (neutrales „X von Y Tagen"), deskriptive statt imperative
Copy (FRONTEND.md:601), Theme-aware, Progressive Disclosure statt leerer „unavailable"-Fläche.

---

## 8. Privacy / Logging

- **Art. 9 / DSGVO:** keine Klartext-Symptomnamen, keine konkreten Sleep-Werte in DTO **oder Logs** —
  nur **Zähler/Anteile** (`days_with_data`, `pct`). (Issue C-full DoD: „keine Art.-9-Leaks in Logs".)
- **Health-Connect-Status [ENTSCHIEDEN — D6]:** `health_connect` ist ein **optionales DTO-Feld** mit nur
  `consent: bool`, `last_sync_at`, `sleep_import_ok: bool` — **keine** importierten Gesundheitswerte.
  HC ist consent-gated (403 ohne Consent, `HEALTH_CONNECT.md`); ohne Consent ist das Feld `null`.
  Die **UI-Anzeige** ist in v1 optional (Feld wird geliefert, Darstellung kann später ergänzt werden);
  der Deep-Link zum HC-Hub (`/health-connect`) bleibt in jedem Fall.

---

## 9. Beispiel-Fixtures [ENTSCHIEDEN — Freeze-Kriterium]

Drei User-Profile als Fixtures (DTO-Response + erwartete Panel-Ausgabe). Die Spec gilt als **freezebar**,
weil alle drei ohne Diskussion aus den Regeln §3–§5 folgen (Issue-Schritt 4/5). Fenster überall 90 Tage,
Gates per Feature-Threshold (Symptom ≥ 15 Entries; Sleep Coverage ≥ 0.5 & ≥ 15 Beobachtungen).
Diese JSON-Blöcke sind die kanonische Grundlage für die Backend- und Contract-Tests.

### 9.1 Profil „Neu" (< 7 Entries)

```json
{
  "as_of": "2026-09-07",
  "coverage_window_days": 90,
  "maturity": { "phase": "collecting", "phase_index": 1, "current_entries": 4, "next_phase_at": 7, "entries_until_next": 3 },
  "coverage": {
    "entry":   { "days_with_data": 4, "window_days": 90, "pct": 0.04 },
    "sleep":   { "days_with_data": 2, "window_days": 90, "pct": 0.02 },
    "symptom": { "days_with_data": 1, "window_days": 90, "pct": 0.01 }
  },
  "sections": [
    { "id": "symptom", "unlocked": false, "reason": "insufficient_entries",  "entries_until_unlock": 11,   "copy_key": "trends.maturity.symptom.insufficient_entries" },
    { "id": "sleep",   "unlocked": false, "reason": "insufficient_coverage", "entries_until_unlock": null, "copy_key": "trends.maturity.sleep.insufficient_coverage" }
  ],
  "health_connect": null
}
```

**Erwartete Panel-Ausgabe:** Reife-Kopf `1/4 · Daten sammeln · 4/7 Einträge, noch 3 bis Erste Muster`
(Meter ~57 %). Entry-Coverage 4 % („4 von 90 Tagen"). Symptom **gesperrt** („noch 11 Einträge …"),
Sleep **gesperrt** („zu wenig Schlafdaten …"). Kein Cycle-Strip.

### 9.2 Profil „Sleep-arm" (viele Entries, wenig Sleep)

```json
{
  "as_of": "2026-09-07",
  "coverage_window_days": 90,
  "maturity": { "phase": "provisional", "phase_index": 3, "current_entries": 24, "next_phase_at": 30, "entries_until_next": 6 },
  "coverage": {
    "entry":   { "days_with_data": 61, "window_days": 90, "pct": 0.68 },
    "sleep":   { "days_with_data": 18, "window_days": 90, "pct": 0.20 },
    "symptom": { "days_with_data": 44, "window_days": 90, "pct": 0.49 }
  },
  "sections": [
    { "id": "symptom", "unlocked": true,  "reason": "ok",                    "entries_until_unlock": null, "copy_key": "trends.maturity.symptom.ok" },
    { "id": "sleep",   "unlocked": false, "reason": "insufficient_coverage", "entries_until_unlock": null, "copy_key": "trends.maturity.sleep.insufficient_coverage" }
  ],
  "health_connect": null
}
```

**Erwartete Panel-Ausgabe:** Reife-Kopf `3/4 · Vorläufig · 24/30 Einträge, noch 6 bis Robust`
(Meter ~62 %). Entry 68 %, Symptom 49 % **frei** (+ Deep-Link Insights-Symptome), Sleep 20 %
**gesperrt** („Sleep-Insights ab 50 % Abdeckung"). Kein Cycle-Strip.

### 9.3 Profil „Symptom-reich" (robust, mit Health-Connect)

```json
{
  "as_of": "2026-09-07",
  "coverage_window_days": 90,
  "maturity": { "phase": "robust", "phase_index": 4, "current_entries": 96, "next_phase_at": null, "entries_until_next": null },
  "coverage": {
    "entry":   { "days_with_data": 82, "window_days": 90, "pct": 0.91 },
    "sleep":   { "days_with_data": 58, "window_days": 90, "pct": 0.64 },
    "symptom": { "days_with_data": 75, "window_days": 90, "pct": 0.83 }
  },
  "sections": [
    { "id": "symptom", "unlocked": true, "reason": "ok", "entries_until_unlock": null, "copy_key": "trends.maturity.symptom.ok" },
    { "id": "sleep",   "unlocked": true, "reason": "ok", "entries_until_unlock": null, "copy_key": "trends.maturity.sleep.ok" }
  ],
  "health_connect": { "consent": true, "last_sync_at": "2026-09-06T22:10:00Z", "sleep_import_ok": true }
}
```

**Erwartete Panel-Ausgabe:** Reife-Kopf `4/4 · Robust · 96 Einträge, robust` (Meter 100 %). Entry 91 %,
Symptom 83 %, Sleep 64 % — alle **frei**. Cycle-Strip erscheint als **eigene, neutrale** Sektion.
`health_connect` belegt (Anzeige v1 optional; kein Klartext-Gesundheitswert, nur Meta).

---

## 10. Definition of Done (C-full, aus Issue)

- [ ] Diese Spec (Metriken, Fenster, Gates, Non-Goals) merged **oder** als Issue-AC eingefroren.
- [x] Backend-DTO + Tests (Coverage-Formeln, keine Art.-9-Leaks in Logs). — Phase 1, s. §12.
- [x] Trends-Panel an DTO; Streak-Placeholder entfernt/entschärft. — Phase 2, s. §12.
- [x] Contract-/UI-Tests (`trends/page.test.ts` + Komponenten-/API-Tests). — 19 Web-Tests grün.
- [x] Titel und Inhalt deckungsgleich; keine gamifizierenden Streak-Rekord-Zahlen.
- [x] Cycle-Overlay klar getrennt oder mit migriert.
- [x] UI-Konventionen §7.6 erfüllt: `InsightStageHeader` wiederverwendet (G1), keine Emoji (G2),
      `role="meter"` (G3), 44px-Trefferflächen (G4), i18n-Reuse (G5).
- [ ] Mobile-first responsiv (G7): CSS umgesetzt (Umbruch/Meter volle Breite); finaler 360px-Check
      am echten Gerät steht noch aus.

---

## 11. Decision-Log

Alle sieben Forks sind im Spec-Dialog (2026-09-07) entschieden:

| # | Frage | Status | Entscheidung |
| - | ----- | ------ | ------------ |
| D1 | Surfaces: Trends-only vs. auch Home | ✅ ENTSCHIEDEN | **Trends-only** v1, DTO surface-agnostisch (Home kein Scope) |
| D2 | Label DE/EN | ✅ ENTSCHIEDEN | **„Datenreife"** / **„Data readiness"** |
| D3 | Cycle-Strip: getrennt / auslagern / mit migrieren | ✅ ENTSCHIEDEN | **getrennt**, eigene Sektion „neutraler Kontext" |
| D4 | Coverage-Fenster 90 vs. 30 Tage | ✅ ENTSCHIEDEN | **90 Tage** rollierend, `coverage_window_days=90` fix |
| D5 | Gates: Feature-Threshold vs. Maturity-Phase | ✅ ENTSCHIEDEN | **Hybrid** — Phase grob, Freischaltung per Feature-Threshold (15 / 0.5·15 / 45·90) |
| D6 | Health-Connect-Status ins DTO? | ✅ ENTSCHIEDEN | **optionales Feld** `health_connect`, Anzeige v1 optional |
| D7 | Endpoint-Pfad | ✅ ENTSCHIEDEN | **`/api/v1/entries/stats/health-context`** |

**Verbleibend bis Freeze:** nur noch das **Review-Gate** (Frontend + Backend gegenzeichnen,
Issue-Schritt 5). Inhaltlich ist die Spec vollständig — alle Entscheidungen (D1–D7), UI-Konventionen
(G1–G7) und Fixtures (§9) sind ausformuliert. Nach dem Gegenzeichnen: Status → `Accepted`, dann C-full
implementieren.

---

## 12. Umsetzungsplan (C-full)

Aufwand ~2–4 Personentage (Issue-Schätzung). Reihenfolge folgt der Issue-Empfehlung: Spec-Freeze →
Backend-DTO → Frontend-Panel → Tests → Cleanup. Umsetzung auf dem Branch
`claude/issue-852-spec-konzept-4ry2jd` (bzw. Folge-Branch).

### Phase 0 — Review-Gate (Voraussetzung, ~0,5d)

- [ ] Frontend + Backend zeichnen Spec gegen (Issue-Schritt 5); Status → `Accepted`.
- [ ] i18n-Copy-Keys final abstimmen (`trends.maturity.*`, Reuse von `maturity.*`).

### Phase 1 — Backend-DTO (~1–1,5d) — ✅ UMGESETZT

- [x] **Schema** `backend/app/schemas/stats.py`: `HealthContextResponse` + Sub-Modelle
  (`HealthContextMaturity`, `CoverageMetric`, `HealthContextCoverage`, `HealthContextSection`,
  `HealthConnectStatus | None`).
- [x] **Service** `backend/app/services/health_context_service.py`: `get_health_context(db, user_id, as_of)`.
  - Maturity aus `insight_service.get_insight_maturity` beziehen (nicht neu berechnen).
  - Coverage über **90-Tage-Fenster** (`HEALTH_CONTEXT_WINDOW_DAYS`): `entry`/`sleep`/`symptom`
    = distinkte Tage-mit-Daten ÷ 90.
  - Gates (Hybrid): `unlocked` je Sektion aus Feature-Threshold (Symptom ≥ 15 Entries;
    Sleep Coverage ≥ 0.5 & ≥ 15 Beob.), `reason`/`entries_until_unlock`/`copy_key` gesetzt.
  - `health_connect` optional, consent-gated; v1 liefert nur `consent`, `null` ohne Consent.
  - **Modul-Abweichung vom Plan:** eigenes `health_context_service.py` statt `stats_service.py`,
    weil `insight_service` bereits `stats_service` importiert (sonst zirkulär).
  - **Sleep-Quelle aufgelöst (Risiko):** kanonisches Signal = `Entry.sleep_minutes` (die Spalte,
    die das Engine-Sleep-Gate `MIN_SLEEP_COLUMN_COVERAGE` steuert).
- [x] **Router** `backend/app/api/v1/endpoints/entries.py`: `GET /entries/stats/health-context`
  (Auth wie übrige Stats-Endpoints, `120/minute` Rate-Limit).
- [x] **Privacy:** Response/Service emittieren nur Zähler/Ratios/Enums — kein Klartext, kein Logging.
- [x] **Tests** `backend/tests/test_health_context_service.py`: drei §9-Fixtures, Gate-Grenzfälle
  (14/15 Entries; 44/45 Tage = 0.49/0.50 Coverage; 18 Tage), `health_connect=null`-Pfad,
  Art.-9-No-Leak-Guard, Endpoint 200 + 401. **12 Tests grün**, ruff + mypy sauber.

### Phase 2 — Frontend-Anbindung (~1d) — ✅ UMGESETZT

- [x] **Client** `apps/web/src/lib/api/stats.ts`: `HealthContextResponse`-Typ (+ Sub-Typen) +
  `fetchHealthContext()`.
- [x] **Panel** `apps/web/src/lib/components/trends/TrendsHealthContext.svelte` umgebaut:
  - Titel/Copy → „Datenreife" (`trends.maturity.*`), Streak-Trio entfernt.
  - Reife-Kopf via **wiederverwendetem `InsightStageHeader`** (G1), gespeist aus der kanonischen
    `InsightMaturity` (kein Bespoke-Chip).
  - 3 Coverage-Meter mit `role="meter"` + aria (G3), Lucide-`Lock` statt Emoji (G2), Deep-Links ≥44px (G4).
  - Gesperrte Sektionen: `copy_key` + `entries_until_unlock` gerendert (Progressive Disclosure).
  - Cycle-Strip als getrennte, neutrale Sektion (D3); Meter einfarbig, kein Rot/Grün (ADR-0035).
- [x] **Page** `apps/web/src/routes/trends/+page.svelte`: `fetchHealthContext()` statt `fetchEntryStreak()`
  (soft-fail, nicht mehr „core"); Maturity aus `$insightStore.insightMaturity` bzw. Dev-Fixture.
  - **Maturity-Quelle:** Für die wiederverwendete Komponente wird die kanonische `InsightMaturity`
    durchgereicht (voller Kontrakt inkl. `user_message_key`), nicht die schlankere DTO-Maturity.
  - **Dev-Fixture:** `phaseFixtures.ts` um `healthContext` erweitert (Gates spiegeln die Backend-Schwellen).
- [x] **i18n** `apps/web/src/lib/i18n/locales/{de,en}.json`: neue `trends.maturity.*`-Keys; alte
  `trends.health.*`/`trends.consistency.*`-Keys bleiben unangetastet (nur nicht mehr vom Panel genutzt).

### Phase 3 — Tests & Cleanup (~0,5d) — ✅ UMGESETZT (bis auf Geräte-Check)

- [x] **Component-/UI-Tests** `TrendsHealthContext.test.ts`: Meter je Coverage-Zeile, Gate-Zustände
  (locked + Copy-Key, kein Deep-Link), keine Streak-Labels, Cycle-Sektion, `InsightStageHeader`-Reuse.
- [x] **Contract-Test** DTO ↔ Frontend-Typ: `test_health_context_endpoint_contract_shape` prüft die
  serialisierten JSON-Keys gegen das `HealthContextResponse`-Interface (Drift-Guard).
- [x] `trends/page.test.ts` an den neuen Datenfluss angepasst (Mock `fetchHealthContext`, Heading-Key).
- [x] **Streak-Rückbau geprüft:** `fetchEntryStreak`/`EntryStreakResponse` sind frontendseitig nur noch
  vom eigenen Client-Test + der Dev-Fixture referenziert; der Backend-`/stats/streak`-Endpoint bleibt
  reale API → **bewusst belassen** (kein durch diese Änderung erzeugter Dead Code).
- [x] `docs/FRONTEND.md`-Verweis auf den Trends-Datenreife-Block aktualisiert (Screen 4).
- [ ] **Mobile-Check auf 360px** (echtes Gerät / DevTools): CSS umgesetzt (mobile-first, Umbruch,
  einspaltige Meter, Cycle-Strip mit eigenem `overflow-x`); der visuelle Geräte-Check steht als
  einziger offener Punkt aus (headless im CI-Container nicht sinnvoll ausführbar).

### Risiken / Hinweise

- **Sleep-Coverage-Quelle:** ✅ aufgelöst in Phase 1 — kanonisch `Entry.sleep_minutes` (die Spalte,
  die das Engine-Sleep-Gate `MIN_SLEEP_COLUMN_COVERAGE` steuert).
- **Kein neuer Screen** (ADR-0017): alles bleibt im Trends-Panel.
- **PR erst auf Zuruf** — kein automatischer PR (siehe Projektregeln).

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

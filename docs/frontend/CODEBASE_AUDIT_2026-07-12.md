# Frontend-Codebase-Audit — toter Code, Inkonsistenzen, Metrik-Fluss

**Datum:** 2026-07-12
**Scope:** `apps/web` + Metrik-/Insight-Fluss Backend → Frontend
**Methode:** Statische Analyse (Grep über Call-Sites, nicht Namen) **plus
Browser-Verifikation** jedes UI-relevanten Befunds mit Dev-Mode-Mockdaten
(`dev_force_viz`) bei 375×812 (Mobile-First). Zwei Regressionen wurden
erst durch die Browser-Verifikation sichtbar und sind im begleitenden PR
gefixt; alle übrigen Befunde sind hier zur Umsetzung dokumentiert.

> Ergänzt [`GUI_CONSISTENCY_AUDIT_2026-07-12.md`](GUI_CONSISTENCY_AUDIT_2026-07-12.md)
> (Styles/Tokens/Breakpoints). Dieses Audit deckt die andere Hälfte ab:
> tote Komponenten, tote Exports, Datenfluss-Lücken.

---

## Im begleitenden PR gefixt (Browser-Funde)

### X-01: Maturity-Chip zeigte „· 0 Einträge" neben „Basierend auf 42 Eintraegen"

**Fund:** Screenshot der Insights-Seite (robust-Preset): Tier-Chip
„Stabil · 0 Eintraege" direkt über der Meta-Zeile mit 42 Einträgen.
**Ursache:** Beim ISP-4-Merge (`InsightEvidence`) verlor die
Meta-Zeilen-Aufrufstelle in `InsightCard.svelte` das
`entryCount={insight.sample_n}` — der i18n-Platzhalter `{n}` interpolierte
den Default 0. **Fix:** Prop ergänzt + Regressionstest
(`InsightCard.test.ts`), Badge-Interpolation jetzt im i18n-Mock abgedeckt.

### X-02: Bester Wochentag wurde nie grün markiert

**Fund:** Screenshot der Weekday-Übersicht (early_patterns): Di/So (3.0,
Minimum) amber markiert, Fr (3.8, Maximum) aber ohne Highlight.
**Ursache:** `HomeWeekdayOverview` verglich `data-highlight='high'` gegen
`maxMood`, das für die Balkenskalierung auf ≥ 5 geclamped ist — der
Bestwert matcht nie, außer der Schnitt ist exakt 5.0. **Fix:** getrennte
`highMood`-Ableitung (echtes Maximum) fürs Highlight, Skalen-Clamp bleibt
für Balkenhöhen; kein Highlight, wenn alle Tage gleich sind. Live
verifiziert: `Fr=3.8:high`.

---

## Offene Befunde (zur Umsetzung)

### A-01: Sieben Komponenten ohne einzige Verwendung

Null Nicht-Test-Import-Sites (verifiziert per Call-Site-Grep, nicht nur
Namen; `HomeSparkline`/`InsightPhaseMilestoneCard` werden von
`routes/page.test.ts` sogar explizit als „darf nicht auf Home" asserted):

| Komponente                                      | Anmerkung                                                                                                                                             |
| ----------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------- |
| `home/HomeInsight.svelte`                       | Vor-Daily-Brief-Ära; nur `home.insight.empty_statement` lebt noch (via `InsightCard`)                                                                 |
| `home/HomeRecentEntries.svelte`                 | + i18n-Gruppe `home.recent.*` verwaist                                                                                                                |
| `home/HomeSparkline.svelte`                     | O-55 entfernte die Nutzung, Datei blieb; `home.sparkline.*` verwaist                                                                                  |
| `home/HomeSummary.svelte`                       | + totes Figma-Template `HomeSummary.figma.ts` (gleiche Klasse wie das in #346 entfernte `InsightQualityMeter.figma.ts`) + Contract-Test-Case          |
| `home/WeekdayPatternChart.svelte`               | Durch `HomeWeekdayOverview` ersetzt (PR #340); `home.weekday_pattern.early_signal` bleibt (von `HomeWeekdayOverview` genutzt), Rest der Gruppe prüfen |
| `insights/InsightPhaseMilestoneCard.svelte`     | —                                                                                                                                                     |
| `trends/EventAlignedSmallMultiplesSheet.svelte` | Siehe A-03 — Teil einer toten Kette                                                                                                                   |

**Maßnahme:** Komponenten + zugehörige `.test.ts` löschen; verwaiste
i18n-Gruppen (en+de) und das Figma-Template mit entfernen; Contract-Test
in `code-connect-contract.test.ts` bereinigen. Vorgehen wie ISP-4 in
[#346](https://github.com/Sturmi77/correlcore/pull/346): erst Call-Sites
tracen, dann löschen, dann Voll-Grep als Akzeptanz.

### A-02: Tote Exports

- `listInsights()` + `fetchLatestInsight()` in `lib/api/insights.ts` —
  seit PR #350 ohne Frontend-Aufrufer (Endpoint `/insights` existiert im
  Backend weiter; nur die Client-Wrapper sind tot).
- `estimateInsightReadiness()` in `lib/utils/insightQuality.ts` — einziger
  Konsument (`InsightQualityMeter`) wurde in #346 gelöscht;
  `dayEntryDatesFromIsoEntries` aus derselben Datei ist weiterhin live.

### A-03: Tote Explore-Events-Kette (ADR-0035 §6, nie verdrahtet)

`InsightCard.enableExploreEvents`-Prop + `canExploreEvents`-Gate +
`insight-card__explore`-Button + `smallMultiplesGate.ts` (einziger
Import: dieser tote Pfad) + `EventAlignedSmallMultiplesSheet.svelte` +
i18n-Gruppe `trends.esm.*` — **kein Parent** setzt die Prop oder hört auf
das Event. Browser-verifiziert: 0 Explore-Buttons über alle Presets.
**Entscheidung nötig:** Feature fertig verdrahten (ADR-0035 §6 umsetzen)
oder Kette komplett entfernen. Nicht halb liegen lassen.

### A-04: Phantom-Metrik `sleep_quality` / toter „Schlaf"-Filter-Tab

- Frontend-Contract (`apiContract.ts:18`, `metrics.ts:44`) definiert
  `sleep_quality` — das Backend-`Entry`-Modell hat **keine** Spalte dafür,
  die Insight-Engine (`MetricName`-Literal) kennt nur
  `mood_score|energy|stress`, und kein Eingabefeld existiert
  (browser-verifiziert: Entry-Sheet hat exakt 3 Slider, „Schlaf" kommt im
  gesamten DOM nicht vor).
- Der „Schlaf"-Tab in `InsightFeed` (`insightFeedFilter.ts`) kann daher
  **nie** matchen. Browser-verifiziert: 0 Karten, und der Empty-State rät
  dem Nutzer „erfasse weiter, damit neue Muster sichtbar werden" — ein
  falsches Versprechen, da kein Weg existiert, Schlafdaten zu erfassen.

**Entscheidung nötig:** (a) Sleep-Metrik wirklich bauen (Backend-Spalte,
Entry-UI, Engine) oder (b) Tab + Contract-Eintrag entfernen, bis (a)
geplant ist. Empfehlung: (b) — ein permanent leerer Tab mit irreführender
Copy schadet dem Kernziel „Erkenntnisse eindeutig transportieren".

### A-05: Metriken kommen an, werden aber nicht angezeigt

`work_context_summary` liefert pro Kontext `mood_avg`, `energy_avg`,
`stress_avg` (`lib/api/dashboard.ts:8-10`) — gerendert wird nur Mood
(browser-verifiziert: „3.4 · 4 Tage"-Format). Entweder Energy/Stress in
der Work-Context-Ansicht nutzen (z. B. Umschalter analog Trends) oder die
Felder bewusst als „nur für Export/Trends" dokumentieren.

### A-06: `symptom_cluster` ohne Frontend-Sonderbehandlung

Das Backend emittiert 8 Insight-Typen; `buildTitle()` behandelt 4 explizit

- generischen Fallback. Für `symptom_cluster` (Lasso) gilt
  `metric == subject_label` → Caption wird redundant („mood_score →
  mood_score"). Zudem decken die Dev-Fixtures nur 5 von 8 Typen ab —
  `symptom_cluster` (lasso+lag), `work_context_pattern` und
  `weekday_context_pattern` sind in keinem Preset visuell prüfbar, und
  `weekday_pattern` fehlt in `provisional`/`robust` (deshalb zeigt das
  robust-Preset den Weekday-Empty-State — gewollt als Empty-State-Demo oder
  Fixture-Lücke? Klären und ggf. ergänzen).

### A-07: Service Worker cached im Dev-Modus aggressiv

Beobachtung aus der Verifikation: der SW (`correlcore-app-*`-Cache) lieferte
nach Code-Änderungen mehrfach veraltete Module aus (leere Seite bzw. alte
Komponentenlogik), bis Registration + Cache manuell entfernt wurden.
Prüfen: SW-Registrierung in Dev deaktivieren (`import.meta.env.DEV`-Guard)
und die Update-Strategie für Prod bewusst dokumentieren (betrifft, wie
schnell Nutzer Fixes erhalten).

---

## Browser-Verifikationsmatrix (Mock-Daten, 375×812)

| Fall                                  | Preset                | Erwartet                                            | Ergebnis           |
| ------------------------------------- | --------------------- | --------------------------------------------------- | ------------------ |
| Weekday-Empty-State statt Stille      | collecting            | Empty-State-Copy                                    | ✅                 |
| Weekday-Chart mit Fr-Peak             | early_patterns        | 7 Balken, Fr 3.8                                    | ✅                 |
| Weekday bei Phase 4 ohne Insight      | robust                | Empty-State (Fixture-Lücke sichtbar)                | ✅ (→ A-06)        |
| Statement-first (Daily Brief + Cards) | early_patterns/robust | Statement groß, Label als Caption                   | ✅                 |
| Featured-Karte                        | robust                | `data-featured=true`, 24px-Statement, Metrik-Akzent | ✅                 |
| Evidence-Row                          | robust                | Tier-Chip 1× pro Karte, Dots + Label + Sample       | ✅ (X-01 gefunden) |
| „Schlaf"-Tab                          | robust                | 0 Karten, irreführender Empty-State                 | ✅ (→ A-04)        |
| Explore-Events-Button                 | alle                  | nirgends vorhanden                                  | ✅ (→ A-03)        |
| Work-Context nur Mood                 | alle                  | „{mood} · {n} Tage"                                 | ✅ (→ A-05)        |
| Entry-Sheet-Metriken                  | —                     | 3 Slider, kein Schlaf-Feld                          | ✅ (→ A-04)        |
| Kein horizontaler Scroll              | Home + Insights       | `scrollWidth ≤ 375`                                 | ✅                 |
| High/Low-Highlight                    | early_patterns        | Fr=high, Di/So=low                                  | ✅ nach Fix (X-02) |

## Empfohlene Reihenfolge

1. **Sofort (dieser PR):** X-01, X-02.
2. **Cleanup-PR** (A-01, A-02, Teile von A-03 falls „entfernen" entschieden):
   mechanisch, gut testbar, ~1.200 Zeilen weniger.
3. **Produktentscheidungen einholen:** A-03 (verdrahten vs. entfernen),
   A-04 (Sleep bauen vs. Tab raus), A-05 (Energy/Stress anzeigen vs.
   dokumentiert weglassen).
4. **A-06/A-07** als kleinere Einzeltickets.

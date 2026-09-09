# [FEATURE] Home: Trendindikator für Wochenmuster & Arbeitssituationsmuster

> Analyse / Design-Vorschlag. Noch keine Implementierung.
> Labels: `enhancement`, `design`
> Milestone: Backlog / Post-M10.1

---

## Feature-Beschreibung

Auf der Startseite sollen das **Wochenmuster**
([`HomeWeekdayOverview.svelte`](../../apps/web/src/lib/components/home/HomeWeekdayOverview.svelte))
und das **Arbeitssituationsmuster**
([`HomeWorkContextSummary.svelte`](../../apps/web/src/lib/components/home/HomeWorkContextSummary.svelte))
einen **Trendindikator** erhalten, der zeigt, ob sich ein Wert zuletzt nach oben,
unten oder kaum bewegt hat.

Diese Analyse beschreibt, **wie** sich ein solcher Indikator umsetzen lässt —
in Einklang mit den Design-Vorgaben und **ohne die bestehende Platzaufteilung
zu sprengen oder negativ zu beeinflussen**.

## Ausgangslage (Ist-Zustand)

### Datenlage — der Kernpunkt

`GET /dashboard/summary`
([`dashboard_service.py`](../../backend/app/services/dashboard_service.py),
[`schemas/dashboard.py`](../../backend/app/schemas/dashboard.py)) liefert
ausschließlich **All-Time-Aggregate**:

- `work_context_summary[]`: `mood_avg` / `energy_avg` / `stress_avg` / `entry_count`
  je Arbeitssituation — gemittelt über **alle** Einträge (`entry_date <= as_of`).
- `weekday_summary[]`: `mood_avg` / `entry_count` / `top_signal` je Wochentag —
  ebenfalls über das gesamte Fenster.

Ein Trend ist per Definition ein **Vergleich über die Zeit**. Die aktuelle API
enthält **keinerlei Vergleichswert** (weder Vorperiode noch Zeitreihe). Weder
`dashboard_service.py` noch `insight_engine.py` berechnen heute ein
Perioden-Delta. **Der Trendindikator erfordert also zwingend neue Vergleichsdaten** —
er lässt sich nicht rein clientseitig aus dem vorhandenen Payload ableiten.

> Hinweis: Es existiert bereits ein Delta-Muster an anderer Stelle —
> [`DayDeltaCard.svelte`](../../apps/web/src/lib/components/entries/DayDeltaCard.svelte)
> (`EntryDeltaResponse`, Richtung `up|down|same|unknown`) und das
> Habit-Trend-Muster in
> [`HabitsPanel.svelte`](../../apps/web/src/lib/components/trends/HabitsPanel.svelte)
> (`trend_direction`, Icons `TrendingUp` / `TrendingDown` / `Minus`). Beide
> dienen als Vorlage für Benennung, Richtungs-Enum und visuelle Sprache.

### Layout heute (was nicht gesprengt werden darf)

**Wochenmuster** — dichtes 7-Spalten-Grid (`repeat(7, minmax(0, 1fr))`),
Zellen stapeln vertikal: Zahl → Mood-Balken (max. Höhe 56 px) → Finding (2 Zeilen,
`min-height: 1.45rem`) → Wochentags-Label. `min-height` des Charts: 8.5 rem. Pro
Zelle ist horizontal praktisch **kein** Platz (`minmax(0, 1fr)`, `--text-2xs`).

**Arbeitssituationsmuster** — Tabelle/Heatmap, Grid
`minmax(6rem, 1.1fr) repeat(3, minmax(3rem, 1fr))` (auf ≤480 px enger). Pro Zeile:
Kontext-Label + Tage-Anzahl, dann drei Heatmap-Zellen (Mood/Energy/Stress) mit
je einem Wert-Chip. Die Zellen sind bewusst quadratisch-kompakt (`min-height: 2rem`).

### Relevante Design-Vorgaben

1. **Keine Kausalität / vorsichtige Sprache**
   ([`DESIGN_DOCUMENT.md`](../DESIGN_DOCUMENT.md) §2.9, Z. 648/658/686): „The
   system must never imply causality where only correlation or weak pattern
   evidence exists." Ein Trendpfeil ist deskriptiv („zuletzt höher"), **nie**
   prädiktiv oder wertend.
2. **Kein Rot/Grün-Urteil** (ADR-0035 / `FRONTEND.md`; vgl. Kommentar in
   [`HomeWorkContextSummary.svelte:202`](../../apps/web/src/lib/components/home/HomeWorkContextSummary.svelte)
   „intentionally no red/green" und
   [`TrendsHealthContext.svelte:255`](../../apps/web/src/lib/components/trends/TrendsHealthContext.svelte)
   „read as neutral, not a red/green verdict"). **Besonders heikel:** „hoch" ist
   nicht per se „gut" — steigender **Stress** ist negativ, steigende **Mood**
   positiv. Ein naives Grün-für-oben wäre falsch und verstößt gegen die Vorgabe.
3. **Farbe nie allein** — Richtung muss zusätzlich über Icon/Form/Text kodiert
   sein (bestehende Praxis: `data-*`-Attribut + Glyph + Screenreader-Text).
4. **Frühsignal-Gating** — Muster erscheinen erst ab genug Daten
   (`MIN_WEEKDAY_ENTRIES`, Tier-Badge „early_signal"). Ein Trend braucht **zwei**
   ausreichend befüllte Perioden, sonst `unknown` (kein Indikator).
5. **Custom-SVG / kein neues Chart-Budget** (D-002 / ADR-0035): Der Indikator
   muss ein leichtes Primitiv sein (Icon/Glyph), keine eingebettete Sparkline-Lib.

## Vorgeschlagene Lösung

### A. Backend — Vergleichsdaten bereitstellen

`dashboard_service.py` / `schemas/dashboard.py` um ein **optionales Perioden-Delta**
pro Metrik erweitern. Die aktuelle Aggregation bleibt der Anzeigewert; zusätzlich
wird je Wert ein Delta gegenüber einer **Vorperiode** geliefert.

Vorgeschlagene Felder (additiv, optional → bricht keine bestehenden Clients):

```
# weekday_summary[]: je Wochentag
mood_trend: { direction: "up"|"down"|"flat"|"unknown", delta: float|null }

# work_context_summary[]: je Arbeitssituation & Metrik
mood_trend:   { direction, delta }
energy_trend: { direction, delta }
stress_trend: { direction, delta }
```

Berechnung (Vorschlag): Fenster „letzte N Tage" (z. B. 28) vs. „davorliegende N
Tage" für dieselbe Gruppierung. `direction`:

- `up` / `down`, wenn `|delta|` eine **Mindest-Schwelle** (z. B. ≥ 0.3 auf der
  1–5-Skala) überschreitet — verhindert, dass Rauschen als Trend erscheint
  (analog `WORK_CONTEXT_RELATIVE_MIN_SPAN` in
  [`homeWorkContextSummary.ts`](../../apps/web/src/lib/utils/homeWorkContextSummary.ts)).
- `flat`, wenn beide Perioden genug Daten haben, Delta aber unter Schwelle.
- `unknown`, wenn eine der beiden Perioden zu wenige Einträge hat → **kein**
  Indikator wird gerendert.

> **Semantik statt Richtung speichern:** Alternativ kann das Backend direkt eine
> *neutrale* Richtung liefern und die Bewertung ganz dem Frontend/Copy überlassen.
> Empfehlung: Backend liefert nur `direction` + `delta` (Fakt), keine
> Gut/Schlecht-Wertung — Bewertung ist reine Darstellungsfrage (siehe B.3).

### B. Frontend — Darstellung ohne Layout-Sprengung

#### B.1 Wochenmuster (`HomeWeekdayOverview`)

Das 7-Spalten-Grid hat **horizontal keinen** Platz. Optionen:

- **Option W1 (empfohlen): Ein einziger Perioden-Trend im Header**, nicht pro
  Zelle. Neben die Überschrift (bzw. neben das `weekday-overview__tier`-Badge)
  ein kleines Glyph + Kurztext: z. B. „Diese Woche ø höher". Nutzt den bereits
  vorhandenen `__header`-Flex-Slot (Z. 68–73) — **null zusätzliche Höhe**, keine
  Änderung am Grid.
- **Option W2: Micro-Caret an der Mood-Zahl.** In `weekday-overview__value`
  (Z. 87–89) ein ▲/▼/– als `::after` oder Inline-Glyph in `--text-2xs`. Sehr
  dezent, aber 7× visuelles Rauschen in einem ohnehin dichten Strip → höheres
  Risiko, die Aufteilung „negativ zu beeinflussen". Nur wenn pro-Tag-Trend
  explizit gewünscht ist.

**Empfehlung W1** — ein aggregierter Trend pro Woche ist aussagekräftiger als
sieben verrauschte Einzeltrends und passt in den freien Header-Platz.

#### B.2 Arbeitssituationsmuster (`HomeWorkContextSummary`)

Die Heatmap-Zellen tragen bereits einen zentrierten Wert-Chip
(`work-context-summary__value`, Z. 82–85). Optionen:

- **Option C1 (empfohlen): Trend-Glyph im Wert-Chip.** Ein kleines ▲/▼/–
  (`--text-2xs`) direkt neben/unter dem Zahlenwert im Chip. Der Chip hat
  (`min-width: 1.75rem`, Padding) minimal Reserve; ein 8–10 px-Glyph passt, ohne
  die `min-height: 2rem`-Zelle zu vergrößern. Kodierung über `data-trend` am Chip,
  Farbe **metrik-bewusst** (siehe B.3).
- **Option C2: Trend als Rand/Ecke der Zelle** (z. B. dünner Top-Border oder
  Eck-Dreieck). Layout-neutral, aber visuell subtiler/schwerer lesbar; kollidiert
  farblich mit der Heatmap-Intensität → verworfen.
- **Option C3: Separate Trend-Spalte.** Sprengt das `repeat(3, …)`-Grid und die
  mobile Breite → **verworfen** (verletzt die No-Layout-Bruch-Vorgabe).

**Empfehlung C1.**

#### B.3 Farb- & Richtungssemantik (kritisch)

Richtung immer über **Icon + `data-*`-Attribut + Screenreader-Text**, nie über
Farbe allein. Farbgebung bewusst **zurückhaltend**:

- Default: **neutral** (`--color-text-muted`) für `up`, `down` und `flat` — wie
  beim Habit-Trend (`HabitsPanel` färbt nur `down` via `--color-warning`, Rest
  muted). Das ist der sicherste, vorgabenkonforme Default.
- Falls eine leichte Akzentuierung gewünscht: **metrik-bewusst**, nicht
  richtungs-bewusst. „Besser" = Mood/Energy ↑ **oder** Stress ↓ darf dezent
  `--color-success` bekommen, „schlechter" dezent `--color-warning`. Dafür
  existiert serverseitig bereits die Goodness-Normalisierung
  (`workContextMetricGoodness`, Stress invertiert) in
  [`homeWorkContextSummary.ts`](../../apps/web/src/lib/utils/homeWorkContextSummary.ts) —
  wiederverwendbar, damit „hoch ≠ automatisch grün".
- Glyph-Icons konsistent zum Bestand: `TrendingUp` / `TrendingDown` / `Minus`
  (`@lucide/svelte`), Größe `ICON_SIZE_SM`.

#### B.4 Wording (vorsichtig, deskriptiv)

Nur Vergangenheits-/Beschreibungssprache, keine Prognose/Kausalität. Beispiele:
„zuletzt höher", „ø gesunken ggü. Vorperiode", „kaum verändert". Keine Aussagen
wie „verbessert sich" (wertend/kausal).

### C. Utilities & Typen

- Web-Typen in [`dashboard.ts`](../../apps/web/src/lib/api/dashboard.ts) um die
  optionalen Trend-Felder erweitern (Richtungs-Enum wiederverwenden, analog
  `trend_direction` aus [`habits.ts`](../../apps/web/src/lib/api/habits.ts)).
- Mapping in `homeWeekdayOverview.ts` / `homeWorkContextSummary.ts` um das
  Trend-Feld pro Zelle/Header ergänzen; Schwellen-/`unknown`-Logik dort testbar
  kapseln.

### Umsetzungsplan

1. Backend: `schemas/dashboard.py` (optionale Trend-Objekte) → `dashboard_service.py`
   (Vorperioden-Aggregation + Schwellen-/Richtungs-Logik, rein, separat testbar).
2. Web-Typen (`dashboard.ts`) + Mapping-Utils (`homeWeekdayOverview.ts`,
   `homeWorkContextSummary.ts`).
3. UI: Header-Trend im Wochenmuster (W1), Chip-Glyph im Arbeitssituationsmuster (C1).
4. i18n DE/EN (neue Keys, vorsichtige Copy).
5. Tests: Backend-Aggregation/Schwellen, Util-Mapping, Komponenten-Unit
   (Richtung, `unknown`-Gating, A11y-Label), Dashboard-Mocks/Fixtures erweitern.

## Barrierefreiheit

- Wochenmuster-Chart ist `role="img"` mit einem atomaren `aria-label`
  (Z. 75, `chartLabel`). Ein Header-Trend (W1) liegt **außerhalb** des `img` und
  ist damit separat vorlesbar — oder wird, falls pro-Tag (W2), in `chartLabel`
  mit aufgenommen.
- Arbeitssituations-Zellen haben je ein `aria-label`
  (`home.brief.work_context_cell`); Trendrichtung in dieses Label als Klartext
  ergänzen („…, zuletzt höher"). Glyph bleibt `aria-hidden`.

## Alternativen

- **Rein clientseitig** aus vorhandenem Payload — **nicht möglich**, es fehlt jeder
  Vergleichswert (siehe „Datenlage").
- **Eigene Zeitreihe/Sparkline pro Zelle** — verstößt gegen Platz- und
  Bundle-Budget (ADR-0035), sprengt beide Layouts → verworfen.
- **Trend nur auf einer der beiden Karten** — möglich als schrittweise Einführung
  (z. B. zuerst Wochenmuster-Header), reduziert Risiko.

## Risiken / offene Fragen

- **Fenstergröße N** (28 Tage?) und **Delta-Schwelle** müssen mit echten Daten
  kalibriert werden, damit `flat`/`up`/`down` sinnvoll trennen.
- Viele Nutzer haben anfangs **keine zwei vollen Perioden** → Indikator bleibt
  oft `unknown`. Das ist korrekt (vorsichtig), aber der Nutzen greift erst später;
  UX-seitig nicht als „leer/kaputt" wirken lassen (einfach weglassen).
- Gefahr, dass der Trend als **Wertung/Kausalaussage** gelesen wird — durch
  neutrale Default-Farbe und deskriptive Copy aktiv vermeiden.

## Datenschutz-Impact

Aggregierte Mittelwerte über zwei Zeitfenster aus bestehenden Entry-Daten; keine
neuen PII-Felder, keine neue Datenerhebung.

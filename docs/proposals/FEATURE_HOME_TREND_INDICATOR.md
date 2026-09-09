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
Der Header (`weekday-overview__header`, Z. 68–73) ist eine
`justify-content: space-between`-Zeile und trägt **bei aktivem Frühsignal bereits
zwei** Elemente: Überschrift + `weekday-overview__tier`-Badge.

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
2. **Kein Rot/Grün- bzw. Ampel-Urteil** (ADR-0035 / `FRONTEND.md:173–181`; vgl.
   Kommentar in
   [`HomeWorkContextSummary.svelte:202`](../../apps/web/src/lib/components/home/HomeWorkContextSummary.svelte)
   „intentionally no red/green" und
   [`TrendsHealthContext.svelte:255`](../../apps/web/src/lib/components/trends/TrendsHealthContext.svelte)
   „read as neutral, not a red/green verdict"). Wichtig: Anders als bei
   Habit-Adherence gibt es für Mood/Energy/Stress **kein nutzerdefiniertes Ziel**
   — „hoch" ist nicht per se „gut", steigender **Stress** ist sogar ungünstig.
   Eine Gut/Schlecht-Einfärbung (grün/gelb) ist daher **ausgeschlossen**
   (siehe B.3).
3. **Farbe nie allein** — Richtung muss zusätzlich über Icon/Form/Text kodiert
   sein (bestehende Praxis: `data-*`-Attribut + Glyph + Screenreader-Text).
4. **Frühsignal-Gating** — Muster erscheinen erst ab genug Daten
   (`MIN_WEEKDAY_ENTRIES`, Tier-Badge „early_signal"). Ein Trend braucht **zwei**
   ausreichend befüllte Perioden, sonst `unknown` (kein Indikator).
5. **Custom-SVG / kein neues Chart-Budget** (D-002 / ADR-0035): Der Indikator
   muss ein leichtes Primitiv sein (Icon/Glyph), keine eingebettete Sparkline-Lib.

## Vorgeschlagene Lösung

### A. Backend — Vergleichsdaten bereitstellen

`dashboard_service.py` / `schemas/dashboard.py` um ein **Perioden-Modell** mit
**zwei gleitenden Fenstern** erweitern: „aktuelles Fenster" = letzte `N` Tage vor
`as_of`, „Vorperiode" = die `N` Tage davor. `N` ist konfigurierbar (Start:
**28 Tage**) und wird als Teil der Antwort (`trend_window_days`) mitgeliefert,
damit das Frontend die Copy korrekt beschriften kann (→ Codex #3).

**Wichtig (→ Codex #1, #2):** Es genügt **nicht**, nur ein Delta zu liefern. Das
Frontend braucht (a) den **Fenster-Mittelwert**, der *neben* dem Trend
angezeigt wird, und (b) genug Rohdaten, um einen **korrekten Aggregat-Trend**
zu bilden (gewichtet nach Einträgen, nicht als naiver Mittelwert der Einzeldeltas).

Vorgeschlagene, **additive** Felder (optional → bricht keine bestehenden Clients):

```
# Gemeinsames Teilmodell
MetricTrend {
  current_avg:  float|null     # Ø im aktuellen Fenster (DER Anzeigewert, siehe B)
  previous_avg: float|null     # Ø in der Vorperiode
  current_n:    int            # Einträge im aktuellen Fenster (Gating/Gewichtung)
  previous_n:   int            # Einträge in der Vorperiode
  delta:        float|null     # current_avg - previous_avg
  direction:    "up"|"down"|"flat"|"unknown"
}

# Antwort-Ebene
trend_window_days: int                    # z. B. 28

# weekday_summary[]: je Wochentag (für optionale Variante W2)
mood_trend: MetricTrend

# work_context_summary[]: je Arbeitssituation & Metrik
mood_trend:   MetricTrend
energy_trend: MetricTrend
stress_trend: MetricTrend

# NEU, Summary-Ebene: EIN aggregierter Wochen-Mood-Trend für W1 (→ Codex #1)
# Aggregiert serverseitig über alle Tage des Fensters (nach entry_count
# gewichtet), NICHT aus den sieben weekday-Deltas rekonstruiert.
weekday_mood_trend: MetricTrend
```

`direction`:

- `up` / `down`, wenn `|delta|` eine **Mindest-Schwelle** (Start: ≥ 0.3 auf der
  1–5-Skala) überschreitet — verhindert, dass Rauschen als Trend erscheint
  (analog `WORK_CONTEXT_RELATIVE_MIN_SPAN` in
  [`homeWorkContextSummary.ts`](../../apps/web/src/lib/utils/homeWorkContextSummary.ts)).
- `flat`, wenn beide Perioden genug Daten haben (`current_n` und `previous_n` ≥
  Mindestanzahl), Delta aber unter Schwelle.
- `unknown`, wenn eine der beiden Perioden zu wenige Einträge hat → **kein**
  Indikator wird gerendert.

Das Backend liefert nur **Fakten** (`current_avg`, `delta`, `direction`), **keine**
Gut/Schlecht-Wertung — die Bewertung ist ausschließlich Darstellungsfrage und
bleibt neutral (siehe B.3).

### B. Frontend — Darstellung ohne Layout-Sprengung

**Grundregel (→ Codex #2): Angezeigter Wert und Trend müssen dieselbe Größe
beschreiben.** Der sichtbare Zahlenwert ist künftig `current_avg` (Fenster-Ø),
**nicht** mehr das All-Time-Mittel. Damit beschreiben Zahl und Pfeil dasselbe
Fenster; ein irreführendes „2.0 ↑" (alt: All-Time 2.0 neben Rolling-Anstieg)
kann nicht entstehen.

> Trade-off: Der auf Home gezeigte Ø ändert seine Bedeutung von „alle Zeit" zu
> „letzte N Tage". Das ist bewusst — ein Trend neben einem All-Time-Wert ist
> inkonsistent. Bleibt zu wenig Historie für ein Fenster, wird `current_avg`
> `null`/`unknown` und die Karte verhält sich wie heute ohne Trend.

#### B.1 Wochenmuster (`HomeWeekdayOverview`)

Das 7-Spalten-Grid hat **horizontal keinen** Platz. Optionen:

- **Option W1 (empfohlen): Ein einziger aggregierter Wochen-Trend**, gespeist aus
  `weekday_mood_trend` (serverseitig korrekt aggregiert — **nicht** aus sieben
  Zell-Deltas gemittelt, → Codex #1). Platzierung im Header — aber **nicht** als
  drittes konkurrierendes Element (→ Codex #5): Der Header trägt bei aktivem
  Frühsignal schon Überschrift + `weekday-overview__tier`-Badge. Lösung:
  - Trend und Tier-Badge in einer **gemeinsamen, rechtsbündigen Badge-Gruppe**
    bündeln (ein Flex-Container als *ein* Kind der `space-between`-Zeile), sodass
    weiterhin nur zwei Top-Level-Kinder existieren.
  - Trend als **kompaktes Badge** (Glyph + `--text-2xs`-Kurzlabel) im selben Stil
    wie `__tier`; bei `unknown` wird es weggelassen.
  - Responsive: unterhalb einer schmalen Breite darf die Badge-Gruppe unter die
    Überschrift umbrechen (Gruppe bleibt zusammen); ggf. reduziert sich der Trend
    auf das reine Glyph ohne Textlabel. So entsteht **kein** Overflow und keine
    erzwungene Zusatzhöhe im Normalfall.
- **Option W2: Micro-Caret pro Tag** an `weekday-overview__value` (Z. 87–89),
  gespeist aus `weekday_summary[].mood_trend`. Dezent, aber 7× visuelles Rauschen
  im ohnehin dichten Strip → höheres Risiko, die Aufteilung „negativ zu
  beeinflussen". Nur wenn pro-Tag-Trend explizit gewünscht ist.

**Empfehlung W1** — ein aggregierter, serverseitig korrekter Wochen-Trend ist
aussagekräftiger als sieben verrauschte Einzeltrends und kommt mit der
Badge-Gruppe ohne Layout-Bruch aus.

#### B.2 Arbeitssituationsmuster (`HomeWorkContextSummary`)

Die Heatmap-Zellen tragen bereits einen zentrierten Wert-Chip
(`work-context-summary__value`, Z. 82–85). Der Chip zeigt künftig `current_avg`
(Fenster-Ø, → Codex #2). Optionen:

- **Option C1 (empfohlen): Trend-Glyph im Wert-Chip.** Ein kleines ▲/▼/–
  (`--text-2xs`) direkt neben dem Zahlenwert im Chip. Der Chip hat
  (`min-width: 1.75rem`, Padding) minimal Reserve; ein 8–10 px-Glyph passt, ohne
  die `min-height: 2rem`-Zelle zu vergrößern. Kodierung über `data-trend` am Chip;
  Farbe **neutral** (siehe B.3).
- **Option C2: Trend als Rand/Ecke der Zelle** — layout-neutral, aber kollidiert
  farblich mit der Heatmap-Intensität → verworfen.
- **Option C3: Separate Trend-Spalte** — sprengt das `repeat(3, …)`-Grid und die
  mobile Breite → **verworfen** (verletzt die No-Layout-Bruch-Vorgabe).

**Empfehlung C1.**

#### B.3 Farb- & Richtungssemantik (kritisch)

Richtung immer über **Icon + `data-*`-Attribut + Screenreader-Text**, nie über
Farbe allein.

**Keine Gut/Schlecht-Einfärbung (→ Codex #4).** Eine frühere Variante schlug
optional `--color-success`/`--color-warning` je nach „Verbesserung/Verschlechterung"
vor. Das ist ein **Ampel-Urteil** und wird gestrichen: Die Vorgabe (ADR-0035 /
`FRONTEND.md:173–181`) verbietet Rot/Grün-Wertungen, und für Mood/Energy/Stress
gibt es **kein nutzerdefiniertes Ziel**, das „besser/schlechter" rechtfertigen
würde (anders als Habit-Adherence). Auch die metrik-bewusste Invertierung
(Stress hoch = schlecht) behebt nur die *Richtung*, nicht das *Urteil*.

Verbindliche Regel:

- Alle Richtungen (`up`, `down`, `flat`) werden **neutral** dargestellt
  (`--color-text-muted`) — identisch zum Habit-Trend-Default in `HabitsPanel`.
- Unterschieden wird ausschließlich über die **Form** des Glyphs
  (`TrendingUp` / `TrendingDown` / `Minus`, `@lucide/svelte`, Größe
  `ICON_SIZE_SM`), nicht über die Farbe.
- Falls später eine Hervorhebung gewünscht wird, ist **nur** die freigegebene
  Nicht-Urteil-Kodierung (Metrik-/Divergenz-Tokens aus `FRONTEND.md:173–181`)
  zulässig — **kein** success/warning.

#### B.4 Wording (vorsichtig, deskriptiv, fenster-genau)

Nur Vergangenheits-/Beschreibungssprache, keine Prognose/Kausalität — und das
**tatsächliche Fenster korrekt benennen** (→ Codex #3). Da verglichen wird:
„letzte `N` Tage gegenüber den `N` Tagen davor". Mit `N = trend_window_days` aus
dem Payload, z. B.:

- „Ø Stimmung letzte 28 Tage höher als in den 28 Tagen davor"
- Kurzform im Badge/Chip: „28 T ↑" bzw. per i18n „{n} T" + Glyph.

**Nicht** „diese Woche" (das suggeriert die Kalenderwoche; ein gleitendes Fenster
ist das nicht, und `as_of` kann es historisch verschieben). Keine wertenden
Formulierungen wie „verbessert sich".

### C. Utilities & Typen

- Web-Typen in [`dashboard.ts`](../../apps/web/src/lib/api/dashboard.ts) um
  `MetricTrend`, die optionalen Trend-Felder und `trend_window_days` erweitern
  (Richtungs-Enum wiederverwenden, analog `trend_direction` aus
  [`habits.ts`](../../apps/web/src/lib/api/habits.ts)).
- Mapping in `homeWeekdayOverview.ts` / `homeWorkContextSummary.ts`: Anzeigewert
  auf `current_avg` umstellen, Trend-Feld pro Zelle/Header ergänzen, Schwellen-/
  `unknown`-Gating dort rein und testbar kapseln.

### Umsetzungsplan

1. Backend: `schemas/dashboard.py` (`MetricTrend`, Trend-Felder,
   `weekday_mood_trend`, `trend_window_days`) → `dashboard_service.py`
   (zwei-Fenster-Aggregation inkl. gewichtetem Summary-Trend + Schwellen-/
   Richtungs-Logik, rein, separat testbar).
2. Web-Typen (`dashboard.ts`) + Mapping-Utils (`homeWeekdayOverview.ts`,
   `homeWorkContextSummary.ts`), Anzeigewert = `current_avg`.
3. UI: aggregiertes Wochen-Trend-Badge in einer Badge-Gruppe (W1) +
   Chip-Glyph im Arbeitssituationsmuster (C1), Richtungen neutral.
4. i18n DE/EN (neue Keys, fenster-genaue Copy mit `{n}`).
5. Tests: Backend-Aggregation/Gewichtung/Schwellen, Util-Mapping, Komponenten-Unit
   (Richtung, `unknown`-Gating, Header-Badge-Gruppe bei aktivem Frühsignal,
   A11y-Label), Dashboard-Mocks/Fixtures erweitern.

## Barrierefreiheit

- Wochenmuster-Chart ist `role="img"` mit einem atomaren `aria-label`
  (Z. 75, `chartLabel`). Das Header-Trend-Badge (W1) liegt **außerhalb** des `img`
  und ist separat vorlesbar — oder wird, falls pro-Tag (W2), in `chartLabel`
  mit aufgenommen.
- Arbeitssituations-Zellen haben je ein `aria-label`
  (`home.brief.work_context_cell`); Trendrichtung als Klartext ergänzen
  („…, letzte 28 Tage höher"). Glyph bleibt `aria-hidden`.

## Alternativen

- **Rein clientseitig** aus vorhandenem Payload — **nicht möglich**, es fehlt jeder
  Vergleichswert (siehe „Datenlage").
- **Eigene Zeitreihe/Sparkline pro Zelle** — verstößt gegen Platz- und
  Bundle-Budget (ADR-0035), sprengt beide Layouts → verworfen.
- **Trend nur auf einer der beiden Karten** — möglich als schrittweise Einführung
  (z. B. zuerst Wochenmuster-Header), reduziert Risiko.

## Risiken / offene Fragen

- **Fenstergröße N** (Start 28 Tage) und **Delta-Schwelle** (Start 0.3) müssen mit
  echten Daten kalibriert werden, damit `flat`/`up`/`down` sinnvoll trennen.
- **Bedeutungswechsel des Anzeigewerts** von All-Time auf Fenster-Ø (B): bewusst,
  aber kommunizieren — bei zu wenig Historie kein Wert/kein Trend statt „kaputt".
- Viele Nutzer haben anfangs **keine zwei vollen Perioden** → Indikator bleibt
  oft `unknown`. Das ist korrekt (vorsichtig); Indikator dann einfach weglassen.
- Gefahr, dass der Trend als **Wertung/Kausalaussage** gelesen wird — durch
  neutrale Farbe, reine Glyph-Form und deskriptive, fenster-genaue Copy vermeiden.

## Datenschutz-Impact

Aggregierte Mittelwerte über zwei Zeitfenster aus bestehenden Entry-Daten; keine
neuen PII-Felder, keine neue Datenerhebung.

---

### Änderungshistorie

- **v2** — Überarbeitung nach Codex-Review (PR #866): Backend liefert jetzt
  `MetricTrend` mit Fenster-Mittel + Counts und einen serverseitig aggregierten
  `weekday_mood_trend` (Codex #1); Anzeigewert = Fenster-Ø statt All-Time
  (Codex #2); fenster-genaue Copy „letzte N Tage" statt „diese Woche" (Codex #3);
  success/warning-Variante gestrichen, Richtungen strikt neutral (Codex #4);
  W1 nutzt eine Badge-Gruppe statt eines dritten Header-Elements (Codex #5).

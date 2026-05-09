# ADR-0014 — Home-Dashboard mit Recent-Entries-Liste und 14-Tage-Sparkline (M1.5-Vorzug aus M2)

**Status:** Vorgeschlagen
**Datum:** 2026-05-09
**Bezug:** Issue #97 (Home-Today-View), DESIGN_DOCUMENT.md §3 M1/M2, ADR-0012 (M2/M5 Streak-Semantik)

## Kontext

Die aktuelle Startseite (`apps/web/src/routes/+page.svelte`) zeigt im
authentifizierten Zustand:

- Zeit-bewusste Begrüßung
- Today-Status-Badge (Eintrag heute vorhanden? ja/nein)
- Hero-CTA „Neuer Eintrag" / „Eintrag von heute bearbeiten"
- Logout + Theme-Toggle

Der Code-Kommentar (Zeile 11–13) hält explizit fest:

> Deliberately minimal for M1. No streak counter, no recent-entries list,
> no charts — those land with M2 (visualisation milestone). See
> DESIGN_DOCUMENT.md "Home-Screen-Heuristik".

Aus dem produktiven Test (2026-05-09) kam der direkte User-Wunsch:

1. Startseite soll **bereits gespeicherte Tage auflisten und direkt anwählbar** machen
2. Eine **Summary** (Mood-/Energy-/Stress-Trend) wäre auf der Startseite gut

Beide Punkte sind **M2-Features** laut Design-Doc. Sie sind aber für den
Eigen-User-Test wertvoll und kein substantieller Aufwand (anders als
Offline-Sync, ADR-0009): keine neue Datenbank-Migration, keine neue
Backend-API (alle nötigen Endpoints existieren), keine Chart-Library.

## Entscheidung

**Recent-Entries-Liste, 7-Tage-Summary und 14-Tage-Sparkline werden von
M2 nach M1.5 vorgezogen.** Schema-/API-seitig keine Änderung; alles
clientseitig.

### Komponenten-Aufteilung

```
+page.svelte (authenticated)
├── Greeting                      (bestehend)
├── TodayStatusBadge              (bestehend, leichte Anpassung)
├── HomeSummary                   (neu) ── 7-Tage-Avg + Streak
├── HomeSparkline                 (neu) ── 14-Tage-Mood-Trend
├── HomeRecentEntries             (neu) ── 7-Tage-Liste, klickbar
└── HeroCta                       (bestehend, behält CTA-Card)
```

### HomeRecentEntries

- Lädt `listEntries({start: today-6, end: today, limit: 7})` parallel zum bestehenden Today-Load
- Zeigt 7 Cards (heute oben), je Card:
  - Datum (lokalisiert: „Heute", „Gestern", sonst Wochentag + ISO-Datum)
  - Mood-Emoji (1–5 Skala → 😢 😕 😐 🙂 😄)
  - Anzahl Tags (+ erste 2 Tag-Icons inline) und Anzahl Symptome (+ erste Symptom-Icons)
  - Klick → Navigation auf `/entries/new?date=YYYY-MM-DD`
- Leerer Tag (keine Card vorhanden) wird als gestrichelte Card mit „Kein Eintrag" + Klick auf den Tag (führt auf `/entries/new?date=...` zum Erfassen)
- Loading-Skeleton: 7 graue Karten während des Loads
- Fehler: dezenter Inline-Hinweis, der Rest der Seite bleibt funktionsfähig

### HomeSummary

7-Tage-Aggregation (Variante A im Plan):

| Kennzahl        | Berechnung                                     | Quelle         |
| --------------- | ---------------------------------------------- | -------------- |
| Mood-Avg        | Mittelwert über 7 Tage                         | `entry.mood`   |
| Energy-Avg      | Mittelwert über 7 Tage                         | `entry.energy` |
| Stress-Avg      | Mittelwert über 7 Tage                         | `entry.stress` |
| Eintrags-Streak | Aufeinanderfolgende Tage mit Eintrag bis heute | abgeleitet     |
| Anzahl Einträge | 7-Tage-Count                                   | abgeleitet     |

**Streak-Semantik:** „Eintrags-Streak" gemäß ADR-0012, **nicht** Habit-Streak. Lückenloser Tag-Count ab heute rückwärts; sobald ein Tag ohne Eintrag erscheint, endet der Streak. Heute ohne Eintrag bricht den Streak **nicht** sofort (Coulance bis Tagesende — erst der Folgetag bricht).

**Berechnung clientseitig** aus den ohnehin geladenen `recent-entries`. Kein neuer Backend-Endpoint. Falls die 7-Tage-Range für die Streak nicht ausreicht (Streak ≥ 7), erweitert der Loader on-demand auf 30 Tage; Anzeige wird mit `…+` angedeutet wenn Streak ≥ 30.

### HomeSparkline

14-Tage-Mood-Sparkline:

- **Eigenes SVG**, keine Chart-Library (Begründung unten)
- Höhe 32 px, Breite responsiv (`100%`)
- 14 Datenpunkte, x-Achse = Tag, y-Achse = Mood (1–5)
- Polyline für Trend, kleine Kreise auf jedem Datenpunkt
- Lücken (Tage ohne Eintrag) als unterbrochene Linie (`stroke-dasharray`) markiert
- Hover/Tap zeigt Tooltip mit Datum + Wert
- Theme-aware: `currentColor` für Linie, gefilterte Soft-Variante für Hintergrund

**Warum eigenes SVG statt Chart-Library?**

| Option          | Bundle-Impact | Aufwand | Verdict                  |
| --------------- | ------------- | ------- | ------------------------ |
| **Eigenes SVG** | 0 KB extra    | ~80 LOC | ✅ gewählt               |
| uPlot           | ~45 KB gz     | trivial | overkill für Sparkline   |
| Chart.js        | ~175 KB gz    | trivial | massiv überdimensioniert |
| ApexCharts      | ~400 KB gz    | trivial | absolut nicht            |
| Frappe Charts   | ~80 KB gz     | trivial | unnötig                  |

Sparkline ist visuell simpel; eigenes SVG ist günstiger, theme-tauglich (CSS-Variablen, kein Canvas), accessibility-fähiger (`<title>`-Element pro Datenpunkt). Falls in M2 Multi-Metric-Charts (Stack/Bar/Heatmap) kommen, kann dort uPlot oder ApexCharts dazukommen — aktuell wäre das verfrüht.

### Routing-Erweiterung

`/entries/new?date=YYYY-MM-DD` muss respektiert werden. Aktueller Loader in `routes/entries/new/+page.svelte` initialisiert `entryDate = todayIso` — Erweiterung:

```svelte
$: initialDate = $page.url.searchParams.get('date') ?? todayIso; let entryDate = initialDate;
```

Hydration läuft dann automatisch über den bestehenden `loadForDate`-Pfad (PR #117).

### Aufwand & Tests

- ~250 Zeilen TS+Svelte verteilt auf 3 neue Komponenten + Home-Page-Integration
- 6–8 neue Vitest-Tests:
  - Recent-Entries: Sortierung, fehlende Tage, Klick-Navigation
  - Summary: 7-Tage-Avg-Berechnung, leerer Zustand, Streak-Edge-Cases (heute leer, lückenhaft)
  - Sparkline: Pfad-Generierung, fehlende Datenpunkte als Dashed-Line
- Datums-Util-Tests: `dateLabel('today'|'yesterday'|...)`, lokale Wochentags-Formatierung
- A11y-Test: Sparkline hat `<title>`-Tooltips; Cards haben `aria-label` „Eintrag vom DD.MM.YYYY, Stimmung X von 5"

## Konsequenzen

### Positiv

- M1-Eigentest wird deutlich aussagekräftiger (Trend statt Punktbild)
- Reduziert Klick-Tiefe für „letzten Eintrag erneut öffnen" von 2 (Datum-Picker) auf 1 (Card-Klick)
- Vorbereitung für M2: Sparkline-Komponente lässt sich für Energy/Stress-Charts wiederverwenden
- Keine neue Dependency, kein Bundle-Wachstum

### Negativ / Trade-offs

- Startseite wird komplexer; Anonymous-Landing bleibt unverändert
- 7-Tage-Streak-Berechnung clientseitig ist eine Doppel-Implementierung mit der späteren Backend-Streak-API (M2). Mitigation: kleine `computeEntryStreak(entries)`-Util in `lib/utils/streak.ts` — wenn M2 die Backend-API liefert, bleibt der gleiche Aufruf-Punkt, nur die Datenquelle wechselt.
- Sparkline-SVG muss responsive sein → leichter ResizeObserver-Aufwand (~15 LOC)

### Abgrenzung zu ADR-0012

ADR-0012 reserviert „Habit-Streak" für M5. Diese ADR liefert nur **Eintrags-Streak** — semantisch unstrittig (siehe ADR-0012 Abschnitt „Begriffe"). Tag-Frequenz-Heatmap aus ADR-0012 (M2-Inhalt) bleibt M2.

### Design-Doc-Änderung

`DESIGN_DOCUMENT.md` „Home-Screen-Heuristik" wird aktualisiert:

- M1.5 erhält explizit die drei Bullets: Recent-Entries-Liste, 7-Tage-Summary, 14-Tage-Sparkline
- M2-Bullet „Streak-Counter / Recent-Entries / Charts" wird auf „erweiterte Charts (Bar/Heatmap), Habit-Dashboard-Vorbereitung" reduziert
- Sparkline-Komponente wird als wiederverwendbares M2-Asset markiert

## Status-Übergang

`Vorgeschlagen` → `Accepted` nach Implementierung in PR „feat(web): home dashboard with recent entries and 14-day sparkline".

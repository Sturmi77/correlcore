# Insight-/Metrik-Fluss — Umsetzungsplan (Entscheidungen 2026-07-13)

**Datum:** 2026-07-13
**Scope:** `apps/web` (ein Punkt, A-03, berührt zusätzlich Frontend-Daten­ableitung, **kein** Backend)
**Zielgruppe:** KI-Agent, der die Findings umsetzt. Jeder Punkt enthält
Entscheidung, Maßnahme, konkrete Datei-Anker (per `grep` re-verifizieren,
nicht blind an Zeilennummern editieren), Tests und Akzeptanzkriterien.

> Quelldokument der Findings: [`CODEBASE_AUDIT_2026-07-12.md`](CODEBASE_AUDIT_2026-07-12.md).
> Dieses Dokument hält die am 2026-07-13 getroffenen Produktentscheidungen
> fest **und** macht sie umsetzungsreif. Die Findings-IDs (A-01 … A-07,
> F-03) sind dieselben wie dort.

## Arbeitsregeln (wie in den bestehenden Sprint-Plänen)

1. Vor jeder Änderung Fundstelle per `grep` re-verifizieren.
2. Nach jeder Änderung lokal: `pnpm --filter @correlcore/web lint typecheck test`
   (und `pnpm check:contrast` **aus dem Repo-Root**, siehe
   `GUI_CONSISTENCY_SPRINT_PLAN.md`), bei UI-Verhalten zusätzlich
   `pnpm --filter @correlcore/web test:e2e:smoke`.
3. Keine neuen Hardcodings: Farben/Radius/Font-Size/Transition aus `app.css`-Tokens.
4. Dark **und** Light manuell prüfen, 375 px (Mobile-First) und 1280 px.
5. Insight-/Metrik-Copy bleibt neutral (No-Gamification, DESIGN_DOCUMENT §1.4).

## Getroffene Entscheidungen (Kurzfassung)

| ID | Finding | Entscheidung (2026-07-13) | Charakter |
| --- | --- | --- | --- |
| F-03 | Hardcodierte Tag-Default-Farbe | **Aktuelle Theme-Primary beim Anlegen übernehmen** | Kleiner FE-Fix |
| A-03 | Tote Explore-Events-Kette | **Fertig verdrahten** (ADR-0035 §6) | FE-Feature (Daten client-abgeleitet) |
| A-04 | Phantom-Metrik `sleep_quality` | **Tab + Contract-Eintrag entfernen** | FE-Removal |
| A-05 | `energy_avg`/`stress_avg` ungenutzt | **Anzeigen (Metrik-Umschalter)** | FE-Feature |
| A-06 | Fixture-Lücke Weekday | Klärung: siehe unten (ergänzen) | FE-Fixture |
| A-01/A-02/A-07 | Toter Code / Exports / SW-Cache | Unverändert entscheidungsfrei | Cleanup |

## Empfohlene PR-Aufteilung

- **PR C (Cleanup, entscheidungsfrei):** A-01, A-02, A-04, A-06, A-07.
  A-04 wandert bewusst hierher: „entfernen" ist reiner Removal, gleicher
  Charakter wie A-01/A-02.
- **PR D (Work-Context-Metriken):** A-05.
- **PR E (Explore-Events):** A-03 — eigenständig, größter Umfang, eigener Review.
- **F-03** gehört inhaltlich in **GUI-Sprint 1**
  (`GUI_CONSISTENCY_SPRINT_PLAN.md`), nicht in diese PRs — hier nur die
  konkretisierte Maßnahme, damit Sprint 1 sie direkt übernehmen kann.

---

## F-03 — Tag-Default-Farbe = aktuelle Theme-Primary

**Entscheidung:** Beim Anlegen eines neuen Tags die **gerade aktive**
Theme-Primary als Startfarbe setzen (statt des hardcodierten Light-Werts
`#6356d9`).

**Anker:** `routes/settings/tags/+page.svelte` — `#6356d9` an drei
Stellen (aktuell Zeilen ~44 „newDraft"-Init, ~62 Reset, ~73
`tag.color ?? '#6356d9'`-Fallback). Theme-Quelle:
`document.documentElement.getAttribute('data-theme')` (siehe
`lib/stores/theme.ts:13`); die Primary-Hexwerte je Theme stehen in
`app.css` (`--color-primary`: dark `#7c6af5`, light `#6356d9`).

**Maßnahme:**

1. Konstantenpaar in `lib/constants/` (z. B. `tagDefaults.ts`):
   `TAG_DEFAULT_COLOR_DARK = '#7c6af5'`, `TAG_DEFAULT_COLOR_LIGHT = '#6356d9'`
   — mit Kommentar, dass dies die `--color-primary`-Werte spiegelt (CSS-Var
   ist im JS-Kontext beim Speichern eines persistenten Hex nicht direkt
   nutzbar; Werte müssen synchron zu `app.css` gehalten werden).
2. Helper `defaultTagColorForCurrentTheme()`: liest `data-theme` und gibt
   den passenden Hex zurück, Fallback dark.
3. Die drei Literale ersetzen: Init/Reset des „neuer Tag"-Drafts rufen den
   Helper; der `?? '#6356d9'`-Render-Fallback nutzt ebenfalls den Helper
   (für Alt-Tags ohne gespeicherte Farbe).

**Tests:** `settings/tags`-Route-Test (falls vorhanden) bzw. neuer
Util-Test für `defaultTagColorForCurrentTheme` mit gesetztem/ungesetztem
`data-theme`.

**Akzeptanz:** Kein Hex-Literal mehr in der Route; im Dark-Theme angelegter
Tag startet mit `#7c6af5`, im Light-Theme mit `#6356d9`; Konstante mit
Sync-Kommentar zu `app.css`.

---

## A-03 — Explore-Events-Kette fertig verdrahten (ADR-0035 §6)

**Entscheidung:** Die vorhandene, aber tote Kette live schalten.

**Zentrale Vorab-Erkenntnis (verifiziert):** `EventAlignedSmallMultiplesSheet`
ist **nirgends importiert** und erwartet zwei Props:
`events: EventWindow[]` (Onset-Daten, `t=0`) und
`points: TimeseriesPoint[]`. Es gibt **keinen** Backend-Endpoint für
Event-Fenster und **kein** `onset`/`event_date` im Insight-Payload. Laut
ADR-0035 §6 ist ein „Event" jedoch **jede Occurrence des Tags/Symptoms**
des Insights (Tag 0 = Tag, an dem der Tag/das Symptom präsent war). Die
`events` sind daher **client-seitig aus den Einträgen ableitbar** — kein
Backend nötig:

- `points` = vorhandene Timeseries (`fetchTimeseries`, `lib/api/stats.ts:68`).
- `events` = Liste der Einträgs-Daten, an denen `insight.subject_id`/
  `subject_label` (Tag oder Symptom, `subject_type`) präsent war. Diese
  Präsenz steht in den Entry-Daten (Tags/Symptome pro Eintrag).

**Anker (Frontend-seitig bereits vorhanden, nur ungenutzt):**

- `InsightCard.svelte`: Prop `enableExploreEvents` (Z. 37), Gate
  `canExploreEvents` (Z. 52, nutzt `isSmallMultiplesUnlocked` aus
  `smallMultiplesGate.ts`), Button + Dispatch `exploreEvents` (Z. 288–293).
- `EventAlignedSmallMultiplesSheet.svelte`: fertige Rendering-Logik, nur
  ohne Aufrufer. i18n-Gruppe `trends.esm.*` vorhanden.
- Phasen-Gate: Sheet erst ab `phase >= 'provisional'` (ADR-0021).

**Maßnahme (im Insights-Screen, `routes/insights/+page.svelte`):**

1. `EventAlignedSmallMultiplesSheet` importieren; Sheet-State (`open`,
   aktueller Insight) im Screen halten.
2. `InsightCard`/`MobileInsightLead` mit `enableExploreEvents` rendern
   (nur wo die Phase es zulässt — das Gate in der Card greift ohnehin).
3. `on:exploreEvents={({detail}) => openSheet(detail.id)}` verdrahten.
4. `openSheet`: den Insight per ID auflösen; `EventWindow[]` aus den
   Präsenz-Daten des Subjekts ableiten (neue Util, z. B.
   `lib/utils/eventWindowsFromInsight.ts` — Input: Insight + geladene
   Einträge/Timeseries, Output: `EventWindow[]`); `metric` aus
   `insight.metric` mappen; `points` aus der bereits geladenen Timeseries;
   `phase` durchreichen.
5. Dev-Mode: passende Mock-Präsenzdaten ergänzen, damit das Sheet unter
   `provisional`/`robust` sichtbar prüfbar ist (siehe A-06).

**Tests:** neue Util `eventWindowsFromInsight` unit-getestet (Tag/Symptom
mit mehreren Präsenztagen → korrekte Onsets; ohne Präsenz → leer);
Insights-Page-Test: Explore-Button erscheint nur ab Phase `provisional`
und öffnet das Sheet; Sheet-Komponente hat bereits Tests — Gate-Verhalten
mitprüfen.

**Akzeptanz:** Auf `/insights` (Mock-Preset `provisional`+) erscheint an
qualifizierten Karten der „Explore"-Button; Klick öffnet das Sheet mit
echten, aus Präsenzdaten abgeleiteten Fenstern; unter `early_patterns`
kein Button; Token-only-Farben (kein hardcodierter Hue); kein
horizontaler Scroll bei 375 px.

**Wichtig:** Wenn sich bei der Umsetzung zeigt, dass die Präsenz-Daten
client-seitig **nicht** ohne zusätzlichen Entry-Fetch verfügbar sind,
STOPP und Rückfrage — dann ist zu entscheiden, ob ein schlanker
Backend-Endpoint (`GET /insights/{id}/event-windows`) die sauberere Lösung
ist, statt clientseitig viele Einträge nachzuladen.

---

## A-04 — `sleep_quality` + „Schlaf"-Tab entfernen

**Entscheidung:** Phantom-Metrik und Filter-Tab entfernen, bis Sleep echt
geplant ist.

**Anker (alle Vorkommen):**

- `lib/contracts/apiContract.ts:18` — `sleep_quality: { min, max, invert }`
- `lib/config/metrics.ts:44–48` — `sleep_quality`-Block (verweist auf den
  Contract-Eintrag)
- `lib/utils/insightFeedFilter.ts`: Typ `InsightFeedFilterTab` enthält
  `'sleep'` (Z. 5), Tab-Definition (Z. 18), `METRIC_MAP.sleep` (Z. 26)
- i18n: `insights.feed.tab_sleep` in `en.json`/`de.json`

**Maßnahme:** Alle obigen Einträge entfernen; `InsightFeedFilterTab`-Union
auf `'all' | 'mood' | 'symptoms' | 'context'` reduzieren; i18n-Key in
beiden Sprachen löschen. Prüfen, ob Tests die 5-Tab-Anzahl asserten
(`InsightFeed.test.ts` — Test „renders all 5 filter tabs" auf 4 anpassen).

**Akzeptanz:** `grep -rn "sleep_quality\|tab_sleep" apps/web/src` = 0;
Insights-Feed zeigt 4 Tabs; kein permanent leerer „Schlaf"-Tab mehr; Tests
grün.

---

## A-05 — Energy/Stress in Work-Context anzeigen (Umschalter)

**Entscheidung:** Metrik-Umschalter (Mood/Energy/Stress) in der
Work-Context-Ansicht ergänzen; nutzt die bereits gelieferten Felder.

**Anker:**

- Daten kommen bereits an: `lib/api/dashboard.ts` — `WorkContextSummaryItem`
  mit `mood_avg | energy_avg | stress_avg` (+ `entry_count`).
- Render/Logik: `HomeDailyBrief.svelte` (Work-Context-Zeilen, aktuell nur
  `mood_avg`, Z. ~35–115) + `lib/utils/homeWorkContextSummary.ts`
  (`buildWorkContextDisplayItems`, `workContextMoodBarWidth` — beide
  mood-fixiert).
- Metrik-Farbtokens vorhanden: `--color-metric-mood/-energy/-stress`
  (`app.css`).

**Maßnahme:**

1. `homeWorkContextSummary.ts` generalisieren: aktive Metrik als Parameter
   (`'mood' | 'energy' | 'stress'`), Bar-Width/Highlight auf das jeweilige
   `*_avg`-Feld beziehen. `workContextMoodBarWidth` → metrik-agnostisch
   umbenennen/erweitern (Rückwärtskompatibilität der Tests beachten).
2. Kleiner Umschalter (SegmentedControl-Primitive existiert:
   `lib/components/common/SegmentedControl.svelte`) über den
   Work-Context-Zeilen; Default `mood`.
3. Balkenfarbe je aktiver Metrik aus dem passenden `--color-metric-*`-Token.
4. i18n: Umschalter-Labels (en+de) unter `home.brief.*`.

**Tests:** `homeWorkContextSummary.test.ts` um Energy/Stress-Fälle
erweitern; `HomeDailyBrief.test.ts` um den Umschalter (Default mood,
Wechsel auf energy zeigt `energy_avg`-Werte).

**Akzeptanz:** Auf Home mit Work-Context-Daten sind alle drei Metriken
umschaltbar; Balkenfarbe folgt der Metrik (Token-basiert); Default
unverändert Mood; Dark/Light geprüft.

---

## A-06 — Fixture-Lücke Weekday (Klärung + ergänzen)

**Beobachtung:** `weekday_pattern` fehlt in den Dev-Presets `provisional`
und `robust` (`lib/dev/phaseFixtures.ts`) — nur `early_patterns` enthält
es (seit PR #350 mit befülltem `weekday_mood_avgs`). Deshalb zeigt das
robust-Preset den Weekday-**Empty-State**.

**Entscheidung/Maßnahme:** Als Fixture-Lücke behandeln, nicht als
Empty-State-Demo — `early_patterns` demonstriert den Empty-Fall bereits
über andere Wege. `weekday_pattern`-Mock (mit `weekday_mood_avgs`) auch in
`provisional` und `robust` ergänzen, damit die Weekday-Übersicht in den
höheren Phasen visuell prüfbar ist. Gleichzeitig (verwandt): Mock-Insights
für die aktuell ungedeckten Typen `symptom_cluster` (lasso+lag),
`work_context_pattern`, `weekday_context_pattern` ergänzen, damit alle 8
Backend-Insight-Typen ein Dev-Fixture haben (nötig für A-03-Verifikation
und die `buildTitle`-Fallback-Prüfung, siehe unten).

**Akzeptanz:** Alle 8 Insight-Typen in mindestens einem Preset sichtbar;
robust-Preset zeigt eine befüllte Weekday-Übersicht.

---

## A-06 (Teil 2) — `symptom_cluster` Rendering-Fallback

**Beobachtung:** `buildTitle()` in `InsightCard.svelte` behandelt 4 Typen
explizit + generischen Fallback. Für `symptom_cluster` (Lasso) gilt
`metric == subject_label` → Caption redundant (`mood_score → mood_score`).

**Maßnahme:** In `buildTitle()` einen `symptom_cluster`-Zweig ergänzen, der
die Feature-Liste aus dem Payload (`payload.features` / `payload.target`)
in eine lesbare Caption übersetzt (z. B. „Mehrere Faktoren → mood"), statt
`metric → metric`. Payload-Struktur: siehe
`insight_engine.py` `_lasso_statement`/`_lag_statement` (Backend, nur
lesen).

**Akzeptanz:** `symptom_cluster`-Karte zeigt keine `x → x`-Caption mehr;
Dev-Fixture aus A-06 Teil 1 macht es prüfbar.

---

## A-01 — Sieben tote Komponenten entfernen

Unverändert aus `CODEBASE_AUDIT_2026-07-12.md` A-01. **Ausnahme durch
A-03-Entscheidung:** `EventAlignedSmallMultiplesSheet.svelte` wird **nicht**
gelöscht (wird in PR E verdrahtet). Ebenso `smallMultiplesGate.ts` behalten.

Zu löschen (PR C): `HomeInsight`, `HomeRecentEntries`, `HomeSparkline`,
`HomeSummary`, `WeekdayPatternChart`, `InsightPhaseMilestoneCard` (+ deren
`.test.ts`), verwaiste i18n-Gruppen (`home.recent.*`, `home.summary.*`,
`home.sparkline.*`, ungenutzte `home.insight.*` außer
`empty_statement`), `HomeSummary.figma.ts` + dessen Contract-Test-Case.

**Akzeptanz:** Voll-Grep der gelöschten Namen = 0 (außer bewusst
behaltenen); `code-connect-contract.test.ts` grün; Build/Tests grün.

---

## A-02 — Tote Exports entfernen (PR C)

- `listInsights()`, `fetchLatestInsight()` in `lib/api/insights.ts` löschen
  (kein FE-Aufrufer seit #350).
- `estimateInsightReadiness()` in `lib/utils/insightQuality.ts` löschen;
  `dayEntryDatesFromIsoEntries` (weiterhin live) behalten.

**Akzeptanz:** Voll-Grep = 0 Aufrufer; typecheck/test grün.

---

## A-07 — Service-Worker-Caching im Dev (PR C)

SW-Registrierung hinter `import.meta.env.DEV`-Guard (in Dev nicht
registrieren), damit HMR-Änderungen nicht von einem alten Cache verdeckt
werden. Prod-Update-Strategie unverändert lassen und im Code kommentieren.

**Akzeptanz:** In `pnpm dev` registriert sich kein SW; Prod-Build
registriert ihn weiterhin.

---

## Verifikation (nach jedem PR)

```bash
pnpm check:contrast              # Repo-Root
cd apps/web
pnpm lint && pnpm typecheck && pnpm test
pnpm test:e2e:smoke              # bei UI-Verhalten
```

Manuelle Sichtprüfung mit Dev-Mode-Mockdaten (`dev_mode_enabled` +
`dev_force_viz` in localStorage, Phase via Settings-`developer-phase-select`)
bei **375×812** und Desktop, Dark **und** Light — analog der
Browser-Verifikationsmatrix in `CODEBASE_AUDIT_2026-07-12.md`.

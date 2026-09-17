# Darstellungsformen — Inventar, Überschneidungen und Lücken (2026-09-17)

> **Art dieses Dokuments:** ANALYSE aus der **User-Perspektive**. Kein Implementation-Scope,
> keine Entscheidung. Grundlage für das zugehörige `[ANALYSIS]`-Issue.
> Sprachwahl: Deutsch, analog zu den vorhandenen `[ANALYSIS]`-Issues (#875, #892).

Nach M3.8 (ADR-0035), #488 (Lag), #489 (Tag-Cluster), #601 (History) und den Compare-Overlays
(#908–#920) existieren **19 unterscheidbare Darstellungsformen** auf vier Screens. Dieses
Dokument beantwortet vier Fragen:

1. **Welche Darstellung gibt es** — inklusive Mockup?
2. **Welche Korrelationen oder Erkenntnisse** lassen sich daraus gewinnen?
3. **Wo gibt es Überschneidungen / Doppelgleisigkeiten**, und was sind jeweils Stärken und
   Schwächen?
4. **Wo sind Lücken**, und wie liessen sie sich decken?

Die Mockups unter `docs/assets/visualization_inventory/` sind **schematische Nachbauten** mit
synthetischen Daten, gerendert aus `docs/assets/visualization_inventory/src/` (Python + Headless
Chromium, `python3 build.py <out-dir>`). Sie verwenden die echten Design-Tokens aus
`apps/web/src/app.css` und die echten deutschen UI-Strings aus `de.json`, sind aber **keine**
Screenshots der laufenden App.

---

## A. Inventar

Legende **Reifegate** (ADR-0021): `collecting` 1–6 Einträge · `early_patterns` 7–13 ·
`provisional` 14–29 · `robust` 30+.

### A.1 Home (`/`)

| ID  | Darstellung                 | Komponente               | Kodierung                                                  | Erkenntnistyp                                | Gate                |
| --- | --------------------------- | ------------------------ | ---------------------------------------------------------- | -------------------------------------------- | ------------------- |
| H1  | Tageskontext-Karte          | `HomeTodayContext`       | Text/Status                                                | „habe ich heute schon erfasst?“              | —                   |
| H2  | Leitsatz + Reifefortschritt | `HomeDailyBrief`         | Satz + Fortschrittsbalken                                  | stärkster aktueller Zusammenhang, Reifegrad  | —                   |
| H3  | Wochenübersicht             | `HomeWeekdayOverview`    | 7 Balken (Ø Stimmung) + Top-Signal + Richtungspfeil        | Wochentagsmuster                             | ab `early_patterns` |
| H4  | Arbeitssituations-Matrix    | `HomeWorkContextSummary` | Tabelle Situation × {Stimmung, Energie, Stress}, Zellfarbe | Kontextvergleich (Homeoffice vs. Büro vs. …) | ab `early_patterns` |
| H5  | Trends-Kurzfassung          | `MobileTrendsSummary`    | KPI-Kacheln + Richtungspfeile                              | grobe Richtung der letzten N Tage            | —                   |

Mockup: **M13** (`m13_home.png`) zeigt H3 + H4.

### A.2 Trends (`/trends`) — Tabs „Vergleichen“ / „Gewohnheiten“

| ID  | Darstellung              | Komponente                                       | Kodierung                                                 | Erkenntnistyp                                          | Gate                  |
| --- | ------------------------ | ------------------------------------------------ | --------------------------------------------------------- | ------------------------------------------------------ | --------------------- |
| T1  | Metrik-Linien            | `MetricTimeseries`                               | Position (y) auf gemeinsamer Tagesachse                   | Verlauf, Niveauwechsel, Gleichlauf zweier Metriken     | —                     |
| T2  | Metrik-Streifen          | `UnifiedStripChart`                              | Divergente Farbe statt Position                           | dasselbe wie T1, lesbar bei hoher Tagesdichte          | —                     |
| T3  | Kontextzeilen-Heatmap    | `ComparisonHeatmap`                              | Zellfarbe = Häufigkeit/Intensität je Tag                  | „an welchen Tagen trat X auf?“ neben dem Metrikverlauf | —                     |
| T4  | Ereignis-Marker          | `EventMarkerLayer`                               | vertikale Linie / weiches Band                            | Ereigniszeitpunkte auf der Achse                       | —                     |
| T5  | Koinzidenz-Overlay (A∩B) | `coincidenceMarkers` + `CompareOverlayControls`  | Band über Spalten, an denen ≥2 gepinnte Zeilen aktiv sind | gemeinsame Tage — reine Präsenz, keine Statistik       | ≥2 Pins, ≥2 Tage      |
| T6  | Lag-1-Overlay (A→B +1d)  | `lag1Markers`                                    | gestrichelte Markierung am Tag von A                      | Folgetag-Sequenzen in Pin-Reihenfolge                  | ≥2 Pins, ≥2 Sequenzen |
| T7  | Zeit-Cursor              | `TimelineCursorOverlay`                          | synchronisierte Spalte über alle Ebenen                   | Querlesen eines Tages über alle Zeilen                 | —                     |
| T8  | Achsen-Zoom              | `compareAxisZoom`                                | 30 / 14 / 7 / 3 / 1 Tage pro Zelle                        | Übersicht ↔ Detail auf derselben Achse                 | —                     |
| T9  | Datenreife               | `TrendsHealthContext`                            | Balken für Eintrags-, Symptom- und Schlaf-Abdeckung       | „womit kann die Analyse überhaupt rechnen?“            | —                     |
| T10 | Gewohnheiten             | `HabitsPanel` + `HabitDetailBody` + `TagHeatmap` | Adherence-Balken, Δ pp, einzeiliges Tagesraster           | Zielerreichung, Tendenz, Korrelationsbeitrag (r)       | —                     |
| T11 | Eintragsdetail           | `EntryHistorySheet`                              | Liste                                                     | Drilldown auf den Tag                                  | —                     |

Mockups: **M01** (T1+T3+T4+T7), **M02** (T2), **M03** (T5+T6), **M04** (T8),
**M14** (T10), **M15** (T9).

### A.3 Erkenntnisse (`/insights`) — Sektionen frei sortier- und abschaltbar

| ID  | Darstellung               | Komponente                        | Kodierung                                                         | Erkenntnistyp                                     | Gate                                   |
| --- | ------------------------- | --------------------------------- | ----------------------------------------------------------------- | ------------------------------------------------- | -------------------------------------- |
| I1  | Reifephasen-Leiste        | `InsightStageHeader`              | 4-Segment-Balken + Meilensteinstreifen                            | „wie weit ist meine Datenbasis?“                  | —                                      |
| I2  | „Korrelations-Matrix“     | `InsightMatrix`                   | **Tabelle**: Effekt-Balken + Konfidenz in %                       | Rangliste der Zusammenhänge nach Effektstärke     | ≥2 Zeilen, Konfidenz ≥ 0,20            |
| I3  | Erkenntnis-Karte          | `InsightCard` + `InsightEvidence` | Satz + Reife-Chip + 5 Konfidenz-Punkte + n                        | eine Aussage in natürlicher Sprache               | je Insight-Typ                         |
| I4  | Lag-Profil (Mini)         | `InsightCard`                     | signierte Mini-Balken, Lag 1–7, Peak hervorgehoben                | „wann ist der Zusammenhang am stärksten?“         | nur `method = lag`                     |
| I5  | Zeitversatz-Heatmap       | `LagCorrelationHeatmap`           | divergente Zellfarbe, Paar × Lag 1–7                              | dieselbe Frage für mehrere Paare gleichzeitig     | ≥2 Zeilen                              |
| I6  | Tag-Kookkurrenz-Matrix    | `TagCooccurrenceHeatmap`          | quadratische Matrix, Zahl = gemeinsame Entries                    | welche Tags treten zusammen auf                   | ab `early_patterns`, ≥5 Paare          |
| I7  | Tag-Gruppen               | `TagGroupsSection`                | Cluster-Chips + Stärkeband                                        | dieselbe Rohgrösse, als Gruppierung gelesen       | ab `early_patterns`                    |
| I8  | Symptomverlauf-Heatmap    | `ComparisonHeatmap` (Reuse)       | Symptom × Tag, Zellfarbe                                          | Symptomtage im Zeitraum                           | ab `early_patterns`                    |
| I9  | Symptom-Kalender          | `SymptomCalendarHeatmap`          | Wochentag-Zeilen × Wochen-Spalten, binär                          | Saisonalität, Häufungen, Wochentagsbezug          | ab `early_patterns`                    |
| I10 | Symptom-/Stimmungsverlauf | `SymptomTrendOverlay`             | 2 Linien (Freq %, Stimmung 1–5) + **Unsicherheitsband**           | läuft ein Symptom mit der Stimmung mit?           | Band bis `robust`                      |
| I11 | Symptom×Tag-Lift-Heatmap  | `SymptomCooccurrenceHeatmap`      | Lift-Farbe, `*` = FDR p < 0,10, gestrichelt = Confounder          | über-/unterzufällige Kombinationen                | ab `provisional`                       |
| I12 | Ereignis-Klein-Multiples  | `EventAlignedSmallMultiplesSheet` | Episoden an T0 ausgerichtet, ±7 Tage, Median-Zeile, Partner-Split | Verlaufsform rund um ein Ereignis                 | ab `provisional`, Median ab 3 Episoden |
| I13 | Verworfene Erkenntnisse   | `DismissedInsightsSection`        | Liste                                                             | Archiv                                            | —                                      |
| I14 | Erkenntnis-Verlauf        | `InsightHistoryTimeline`          | nach Datum gruppierte Karten                                      | wie sich eine Aussage über die Zeit verändert hat | —                                      |
| I15 | Wochenrückblick           | `DigestInsightCards`              | Kartenstapel                                                      | wöchentliche Zusammenfassung                      | —                                      |

Mockups: **M05** (I2), **M06** (I3+I4), **M07** (I5), **M08** (I6+I7), **M09** (I9),
**M10** (I10), **M11** (I11), **M12** (I12), **M15** (I1).

### A.4 Eintrag / Tag

| ID  | Darstellung   | Komponente        | Erkenntnistyp                   |
| --- | ------------- | ----------------- | ------------------------------- |
| E1  | Tagesdelta    | `DayDeltaCard`    | heute vs. vorheriger Eintrag    |
| E2  | Notiz-Signale | `NoteSignalsList` | aus Freitext extrahierte Marker |

---

## B. Mockups

| Mockup | Datei                         | Zeigt                                                        |
| ------ | ----------------------------- | ------------------------------------------------------------ |
| M01    | `m01_compare_linien.png`      | Compare mit Linien, Kontextzeilen, Markern, Cursor           |
| M02    | `m02_compare_streifen.png`    | Compare im Streifen-Modus                                    |
| M03    | `m03_compare_overlays.png`    | Koinzidenz- und Lag-1-Overlay über gepinnten Zeilen          |
| M04    | `m04_compare_zoom.png`        | Achsen-Zoom 7 Tage/Zelle ↔ 1 Tag/Zelle                       |
| M05    | `m05_korrelations_matrix.png` | „Korrelations-Matrix“ (Tabelle mit Effekt-Balken)            |
| M06    | `m06_insight_card.png`        | Erkenntnis-Karte mit Evidenz-Zeile und Lag-Profil            |
| M07    | `m07_lag_heatmap.png`         | Zeitversatz-Heatmap Paar × Lag                               |
| M08    | `m08_tag_kookkurrenz.png`     | Tag-Kookkurrenz-Matrix neben Tag-Gruppen                     |
| M09    | `m09_symptom_kalender.png`    | Symptom-Kalender (Wochentag × Woche)                         |
| M10    | `m10_symptom_trend.png`       | Symptom-/Stimmungsverlauf mit Unsicherheitsband              |
| M11    | `m11_symptom_tag_lift.png`    | Symptom×Tag-Lift mit Signifikanz und Confounder-Markierung   |
| M12    | `m12_esm.png`                 | Ereignis-ausgerichtete Klein-Multiples mit Median            |
| M13    | `m13_home.png`                | Home: Wochenübersicht + Arbeitssituations-Muster             |
| M14    | `m14_gewohnheiten.png`        | Gewohnheiten mit Adherence und Tagesraster                   |
| M15    | `m15_reife_abdeckung.png`     | Reifephasen-Leiste + Datenreife-Abdeckung                    |
| G1     | `g1_streudiagramm.png`        | **Vorschlag** Streudiagramm / Signal-Detail                  |
| G2     | `g2_verteilungsvergleich.png` | **Vorschlag** Verteilungsvergleich + natürliche Häufigkeiten |
| G3     | `g3_changepoint.png`          | **Vorschlag** Changepoint-Annotation                         |
| G4     | `g4_forest_plot.png`          | **Vorschlag** Effektstärke mit Unsicherheitsintervall        |

---

## C. Was lässt sich woraus ablesen?

Die 19 Darstellungen beantworten im Kern **sechs** Fragen. Die Zuordnung zeigt bereits, wo es
eng wird.

| Frage der Nutzer:in                            | Darstellungen                          |
| ---------------------------------------------- | -------------------------------------- |
| F1 „Wie war es im Verlauf?“                    | T1, T2, I10, H5                        |
| F2 „An welchen Tagen trat X auf?“              | T3, I8, I9, T10 (Raster)               |
| F3 „Was hängt womit zusammen — und wie stark?“ | I2, I3, H2, T10 (r), I15               |
| F4 „Was tritt gemeinsam auf?“                  | I6, I7, I11, T5                        |
| F5 „Gibt es eine zeitliche Reihenfolge?“       | I4, I5, T6, I12                        |
| F6 „Wie sicher ist das?“                       | I1, I3 (Evidenz-Zeile), T9, I10 (Band) |

**F1** und **F2** sind gut abgedeckt. **F3** bis **F6** verteilen sich auf je drei bis vier
Surfaces mit unterschiedlichen Statistiken, Zeiträumen und Legenden — das ist der Kern der
Überschneidungsanalyse in Abschnitt D.

---

## D. Überschneidungen und Doppelgleisigkeiten

### O1 — Kookkurrenz dreimal, mit drei verschiedenen Statistiken

| Surface            | Grösse                               | Zeitraum                                                                      | Signifikanz          | Interaktion                 |
| ------------------ | ------------------------------------ | ----------------------------------------------------------------------------- | -------------------- | --------------------------- |
| I6 Tag-Kookkurrenz | absolute gemeinsame Entries          | aus dem globalen Analysezeitraum abgeleitet (`timeseriesRangeToCooccurrence`) | nein                 | Drilldown auf Entries       |
| I11 Symptom×Tag    | **Lift** (Beobachtung/Erwartung)     | globaler Analysezeitraum                                                      | ja (`*`, FDR p<0,10) | Detail-Sheet mit φ, Jaccard |
| T5 Koinzidenz      | Präsenz-Zählung der gepinnten Zeilen | **fix 365 Tage** — Compare ignoriert den globalen Zeitraum                    | nein                 | Band auf der Achse          |

**Stärken** — I6: direkt drilldownbar, clusterbar, dichteregelbar. I11: statistisch am
ehrlichsten (Lift + FDR + Confounder-Hinweis). T5: unmittelbar an der Zeitachse, zeigt _wann_
statt nur _wie oft_.

**Schwächen** — drei verschiedene Zahlen für dieselbe Alltagsfrage. „Sport und Spaziergang: 12"
(I6), „Lift 1,8*" (I11) und ein Band über drei Spalten (T5) sind nicht ineinander übersetzbar.
Die stärkste Statistik (Lift + Signifikanz) ist ausgerechnet auf Symptome beschränkt; für
Tag×Tag gibt es nur rohe Zählungen. Erschwerend: T5 rechnet über ein **fixes Jahresfenster**,
I6/I11 über den gewählten Analysezeitraum — dieselbe Frage, zwei Grundgesamtheiten.

### O2 — Zeitversatz viermal, mit zwei unvereinbaren Bedeutungen

| Surface               | Grösse                    | Aussage                           |
| --------------------- | ------------------------- | --------------------------------- |
| I4 Lag-Profil (Karte) | r je Lag 1–7, ein Paar    | „am stärksten bei +3 Tagen“       |
| I5 Lag-Heatmap        | r je Lag 1–7, viele Paare | dasselbe, in Übersicht            |
| T6 Lag-1-Overlay      | **Präsenz**, fix +1 Tag   | „A war aktiv, am Folgetag B“      |
| I12 ESM `lagOffset`   | markierte Spalte bei T+n  | „Ergebnis erwartet nach +n Tagen“ |

**Stärken** — I4 sitzt am Ort der Aussage. I5 macht Muster über Paare hinweg sichtbar
(z. B. „alles wirkt bei +1“). T6 braucht keine Engine und funktioniert schon in frühen Phasen.

**Schwächen** — I4/I5 zeigen eine **Korrelation** (r, ±), T6 eine **Abfolge von Präsenzen**
(kein r, keine Richtung, kein Vorzeichen). Beide heissen im UI „Lag“ bzw. „Zeitversatz“.
I5 ist ausserdem eine reine Aggregation der `lag_profile`-Daten aus I4 — dieselbe Zahl, zwei
Sektionen, unterschiedliche Farbskalen (Mini-Balken nutzen die Accent-Farbe, die Heatmap die
divergente Skala).

### O3 — Tagespräsenz viermal

T3 (Kontextzeilen), I8 (Symptomverlauf, **dieselbe Komponente**), I9 (Symptom-Kalender) und
das Tagesraster in T10 zeigen alle „an welchen Tagen trat X auf“.

**Stärken** — T3/I8: direkt neben dem Metrikverlauf, zoombar, pinnbar. I9: die einzige
Darstellung, die Wochentag und Woche als **zwei Achsen** auflöst — Saisonalität wird sichtbar.
T10: an das Habit-Ziel gebunden.

**Schwächen** — I8 ist buchstäblich `ComparisonHeatmap` mit anderer Überschrift, steht aber
auf einem anderen Screen mit anderem Zeitraumbegriff. I9 verliert die Intensität (binär),
T3 verliert die Wochentagsstruktur. Niemand kann beides gleichzeitig sehen.

### O4 — Effektstärke-Ranking vs. Kartenstapel

I2 („Korrelations-Matrix“) und I3 (`InsightFeed`) speisen sich aus **derselben** Insight-Liste.

**Stärken** — I2: dichter Überblick, sortiert, als PNG exportierbar. I3: verständlicher Satz,
Verwerfen, Aufklappen, Evidenz, Lag-Profil, ESM-Einstieg.

**Schwächen** — Der Name ist irreführend: I2 ist eine **sortierte Tabelle**, keine Matrix (siehe
M05). Ein Nutzer, der „Matrix“ liest, erwartet I6. Zwei Konfidenz-Darstellungen für denselben
Wert: Prozent in I2, 5 Punkte in I3. Und I2 blendet schwache Zeilen in ein `<details>` aus
(Konfidenz 0,10–0,20), während der Feed dieselben Insights ungefiltert als Karte zeigt.

### O5 — Vier Zeitfenster, ein Wort „Zeitraum“

| Surface                    | Fenster                                                                 |
| -------------------------- | ----------------------------------------------------------------------- |
| H3 / H4 (Home)             | fest 28 Tage (global konfigurierbar = offenes #867)                     |
| T1–T8 Compare              | **fest 365 Tage** — der Zeitraum-Regler ist auf diesem Tab ausgeblendet |
| T10 Gewohnheiten           | Habit-Fenster (28 / 90 Tage)                                            |
| Alle `/insights`-Sektionen | globaler Analysezeitraum (`analysisRange`)                              |

H3, H4, H5 und T10 beantworten alle „geht es hoch oder runter?“ — über verschiedene Fenster.
Auf einem Screen können damit zwei Pfeile mit gegensätzlicher Richtung stehen, ohne dass
irgendwo steht, dass sie verschiedene Grundgesamtheiten meinen.

Zusätzlich ist in H4 die **Zellfarbe** für Stress invertiert (heller = besser), der Pfeil
daneben aber reine Richtung ohne Wertung (`TrendDirectionGlyph` erbt `color`) — in derselben
Zelle zeigen zwei Kodierungen in entgegengesetzte Richtungen.

### O6 — „Wie sicher ist das?“ an vier Stellen

I1 (Phase), I3 (Reife-Chip + Konfidenz-Punkte + n), T9 (Abdeckung je Datenquelle) und das
Unsicherheitsband in I10. Die Konsolidierung von `InsightMaturityBadge` + `InsightConfidenceScale`
zu `InsightEvidence` (ISP-4) hat das Problem verkleinert, aber nicht gelöst: **Phase**
(Datenbasis global), **Konfidenz** (dieser Zusammenhang), **Abdeckung** (diese Datenquelle) und
**Band** (dieser Verlauf) sind vier verschiedene Unsicherheitsbegriffe mit vier Darstellungen
und keiner gemeinsamen Legende.

### O7 — Mobil/Desktop-Parallelbau

Unter 768 px (`DESKTOP_SHELL_BREAKPOINT_PX`) ersetzen `MobileInsightLead` und
`TrendsCompareSettingsSheet`/`TrendsCompareQuickFilters` die Desktop-Varianten.
`CompareOverlayControls` wurde in #919 genau deshalb extrahiert, damit Panel und Sheet nicht
auseinanderlaufen — für die Sortier-, Dichte- und Fokus-Regler gibt es diese gemeinsame Quelle
noch nicht.

---

## E. Lücken

### L1 — Keine Rohdaten-Sicht hinter einer Korrelationszahl → **G1**

Es gibt **kein XY-Diagramm** in der gesamten Anwendung (`grep -ri "scatter"` über
`apps/web/src` ist leer). Zwischen „r = 0,62“ und den Einzeleinträgen liegt nichts: keine
Punktwolke, keine Ausreisser, keine Information darüber, ob der Zusammenhang linear ist oder
ab 30 Minuten Sport ein Plateau erreicht. Für eine App, deren Kernversprechen „Korrelationen
statt Rohdaten“ ist, fehlt damit die Möglichkeit, eine Korrelation zu **prüfen**.

**Vorschlag G1:** ein „Signal-Detail“ als Sheet von der Insight-Karte aus — Streudiagramm
mit Regressionsgerade, Farbcodierung mit/ohne Merkmal, Klick öffnet den Tag. Reifegate wie
ESM (`provisional`).

### L2 — Effekt ohne Streuung → **G2**

`pointbiserial` ist der häufigste Insight-Typ. Seine Aussage („an Tagen mit X liegt die Stimmung
0,6 Punkte höher“) erscheint als Satz (I3) und als Balken (I2) — aber **nie** als Vergleich
zweier Verteilungen. Wie stark sich beide Gruppen überlappen, ist nirgends sichtbar, obwohl
genau das ein belastbares von einem zufälligen Muster trennt.

**Vorschlag G2:** Dot-Strip mit/ohne + Mediandifferenz, ergänzt um ein
**natürliche-Häufigkeiten**-Raster („an 62 von 100 Sport-Tagen …“). Das setzt die v1c-Entscheidung
aus `FEATURE_EVENT_INTERACTION_TIMELINE.md` (natürliche Häufigkeiten statt blosser Präsenz)
auf der Insight-Karte fort, wo sie bisher nur im ESM angekommen ist.

### L3 — Konfidenz ohne Intervall → **G4**

Konfidenz wird als 5-Punkte-Skala (I3) oder Prozentzahl (I2) dargestellt. Beides sagt nichts
über die **Breite** des Effekts. Ein Effekt von 0,33 bei n=18 und einer von 0,62 bei n=34
sehen in M05 fast gleich aus.

**Vorschlag G4:** Forest-Plot als alternative Darstellung derselben Zeilen — Punktschätzer plus
Intervall, Zeilen deren Intervall die Null kreuzt werden ausgegraut. Das ersetzt die heutige
`<details>`-Trennung „starke / schwache Zeilen“ durch eine ehrlich skalierte Achse.

### L4 — `changepoint` ohne visuelle Entsprechung → **G3**

Der Backend-Insight-Typ `changepoint` (`app/services/insights/changepoint.py`, mit
`changepoint_index` und der vollen `changepoints`-Liste im Payload) erzeugt heute nur einen
Satz im Feed. `grep -rn "changepoint" apps/web/src` ist leer. Gleichzeitig kennt
`EventMarkerLayer` bereits die Marker-Art `phase_transition` — es speist sie nur niemand.

**Vorschlag G3:** Changepoints als Marker plus Segment-Mittelwerte auf der Compare-Achse.
Erweiterung vorhandener Infrastruktur, kein Neubau.

### L5 — Multivariate Ergebnisse und Confounder nur als Text

`multivariate_analytics.py` liefert Lasso-Findings („X ist ein relevanter Prädiktor“), und
Confounder erscheinen als Hinweissätze (`insights.weekday_confounded_note`,
`insights.work_context_confounded_note`) bzw. als gestrichelter Zellrand in I11. Es gibt keine
Darstellung, die zeigt, **was übrig bleibt**, wenn man für den Wochentag oder die
Arbeitssituation adjustiert. Für Nutzer:innen bleibt „Hinweis: kann vor allem mit deiner
Arbeitssituation zusammenhängen“ eine Sackgasse.

_Mögliche Deckung:_ geschichtete Ansicht — derselbe Effekt je Arbeitssituation nebeneinander
(klein-multiples Variante von G2). Bewusst **nicht** als Mockup ausgearbeitet, weil zuerst die
Frage zu klären ist, ob adjustierte Effekte mit dem No-Diagnose-Anspruch vereinbar sind.

### L6 — Kein durchgehender Pfad für **eine** Hypothese

`AnalysisCrossLink` springt zwischen Trends und Erkenntnissen, aber nur auf Screen-Ebene. Wer
„Sport → Stimmung“ verfolgen will, muss den Zusammenhang selbst in vier Surfaces wiederfinden:
Karte (I3), Matrixzeile (I2), Compare-Zeile anpinnen (T3/T5), ESM öffnen (I12). Es gibt keine
Detailseite je Signal, auf der alle Sichten auf dasselbe Paar liegen. G1/G2/G4 wären die
natürlichen Bewohner einer solchen Seite.

### L7 — Verwaiste Trends-Tabs

`de.json` definiert `trends.tabs.mood`, `.activities` und `.health`; im Code existiert nur
`type TrendTab = 'compare' | 'habits'`. Die Strings sind tot. Entweder die Struktur nachziehen
(dann wäre es der Ort für eine Gesundheits-/Schlafsicht) oder die Keys entfernen.

### L8 — Schlaf ohne eigene Darstellung

`sleep_quality_avg` und `sleep_minutes` sind Metriken in T1/T2, aber es gibt keine Darstellung,
die Schlaf gegen den Folgetag stellt — obwohl genau das der prototypische Lag-1-Zusammenhang
ist und Health Connect die Daten liefert. Heute ist das nur über I5 (wenn die Engine ein Paar
findet) oder manuelles Pinnen in T5/T6 erreichbar.

### L9 — Keine Abwesenheits-Evidenz

Alle Darstellungen zeigen gefundene Muster. „X ist aufgetreten, hat aber nichts verändert“ ist
nirgends sichtbar. Für Nutzer:innen, die eine Hypothese _widerlegen_ wollen (der eigentliche
Wert eines Trackers), gibt es keine Oberfläche. G1/G2/G4 decken das implizit mit ab — eine
Punktwolke ohne Struktur ist eine Antwort.

---

## F. Bewertung und Priorisierung (nicht bindend)

| Rang | Massnahme                                                                | Wirkung                                                            | Aufwand |
| ---- | ------------------------------------------------------------------------ | ------------------------------------------------------------------ | ------- |
| 1    | **G2** Verteilungsvergleich auf der Insight-Karte                        | schliesst L2 + L9, macht den häufigsten Insight-Typ prüfbar        | mittel  |
| 2    | **I2 umbenennen** + Konfidenz vereinheitlichen (O4, O6)                  | reine Copy-/Token-Änderung, beseitigt die irreführendste Doppelung | klein   |
| 3    | **G1** Signal-Detail-Sheet (Streudiagramm)                               | schliesst L1, wird zum Anker für L6                                | mittel  |
| 4    | **O2 entflechten**: I5 in die Karte falten oder T6 umbenennen            | „Zeitversatz“ darf nicht zwei Dinge heissen                        | klein   |
| 5    | **G3** Changepoint-Marker                                                | schliesst L4, nutzt vorhandene Marker-Infrastruktur                | klein   |
| 6    | **O1 vereinheitlichen**: Lift auch für Tag×Tag                           | eine Statistik für alle Kookkurrenz-Sichten                        | mittel  |
| 7    | **G4** Forest-Plot als Modus von I2                                      | schliesst L3, ersetzt die `<details>`-Trennung                     | mittel  |
| 8    | **O5** Fenster beschriften (Compare = 365 T, Home = 28 T; hängt an #867) | verhindert widersprüchliche Pfeile und Kookkurrenz-Zahlen          | klein   |
| 9    | **L7** Tabs bereinigen                                                   | Hygiene                                                            | klein   |

Was **nicht** empfohlen wird:

- **Ersatzlos streichen.** Jede der 19 Darstellungen hat eine Stärke, die keine andere hat
  (Abschnitt D). Das Problem ist nicht Überfluss, sondern fehlende Übersetzbarkeit zwischen
  den Darstellungen.
- **Noch eine Sektion auf `/insights`.** Der Screen hat bereits acht sortierbare Sektionen.
  G1/G2/G4 gehören auf eine Signal-Detailseite (L6), nicht in die Liste.
- **Adjustierte Effekte (L5) ohne Produktentscheid.** Siehe Abschnitt G.

---

## G. Offene Produktentscheidungen

1. **Eine Kookkurrenz-Statistik oder drei?** Wenn Lift die Referenz wird, braucht I6 eine
   Migration und eine neue Legende.
2. **Heisst „Zeitversatz“ Korrelation oder Abfolge?** T6 und I4/I5 brauchen unterschiedliche
   Wörter, unabhängig davon, welche Darstellung bleibt.
3. **Gibt es eine Signal-Detailseite?** Ohne sie landen G1/G2/G4 als neunte, zehnte und elfte
   Sektion auf `/insights`.
4. **Sind adjustierte Effekte (L5) mit dem No-Diagnose-Anspruch vereinbar?** Ein „bereinigter“
   Effekt klingt kausaler als ein roher — genau das soll die Copy vermeiden.
5. **Zeigt CorrelCore Nicht-Ergebnisse (L9)?** Das berührt die Produktpositionierung stärker
   als die Technik.

---

## Referenzen

- ADR-0035 (Trends-Visualisierungs-Tokens, gemeinsame Achse), ADR-0021 (Reifephasen),
  ADR-0018 (Konfidenz-Visualisierung), ADR-0029 (Trend-Smoothing), ADR-0037 (Tag-Cluster-Reife)
- `docs/frontend/SYMPTOM_VISUALIZATION.md`, `docs/frontend/INSIGHT_STATEMENT_PATTERN.md`,
  `docs/frontend/LAYER_CHART_COMPLETION_PLAN.md`, `docs/frontend/COMPARE_AXIS_ZOOM_PLAN.md`
- `docs/proposals/FEATURE_EVENT_INTERACTION_TIMELINE.md` (v1c: natürliche Häufigkeiten),
  `docs/proposals/FEATURE_LAG_CORRELATION_VISUALIZATION.md`,
  `docs/proposals/FEATURE_HEATMAP_TAG_GROUP_CLUSTERS.md`
- Issues: #488 (Lag), #489 (Cluster), #601 (History), #725 (schwache Matrixzeilen),
  #867 (globales Trendfenster), #908/#910/#917/#919 (Compare-Overlays), #920 (ESM-Split)
- Code: `apps/web/src/lib/components/{trends,insights,home}`, `apps/web/src/lib/utils/*`,
  `backend/app/services/insights/*`

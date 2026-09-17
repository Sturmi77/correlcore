# [ANALYSIS → DECISION] Wechselwirkungen ausgerichteter Ereignisse auf der Zeitachse

> Produktentscheid zu [#891](https://github.com/Sturmi77/correlcore/issues/891).
> Kein Implementation-Scope in diesem Dokument — Folge-Issues tragen den Bau.
>
> Labels: `architecture`, `insights`, `trends`, `frontend`, `backend`
> Milestone: Backlog (Leuchtturm, gestaffelt)
>
> **Tracking:**
>
> - Analyse-Issue: #891
> - Docs-PR: #907
> - v1a Trends-Koinzidenz (Option 3): #908
> - v1b ESM-Partner-Overlay (Option 1): #909
> - v1.1 Lag-1-Markierung auf Compare: #910
> - v2 Event↔Event-Lag / Split-Mediane: später

---

## Problem

Die UI kann **ein** Ereignis auf die Achse legen und Metriken darum herum
zeigen. Die Frage „Was passiert, wenn Sport-Tage mit schlechtem Schlaf
_zusammen_ auftreten — und wie sieht das _nacheinander_ aus?“ ist nur
bruchstückhaft beantwortbar:

| Nutzerfrage                 | Heute                                      | Lücke                         |
| --------------------------- | ------------------------------------------ | ----------------------------- |
| Koinzidenz A∩B              | Zwei Heatmap-Zeilen + Sakkaden             | Keine Auto-Hervorhebung       |
| Sequenz A→B                 | Same-Day Co-occurrence; Feature→Metrik-Lag | Kein Event↔Event-Lag          |
| Wechselwirkung A×B auf Mood | Point-biserial / Spearmen einzeln          | Keine Stratifizierung / Split |

Kognitiv bleibt die Sakkaden-Arbeit aus
[ADR-0035](../adr/0035-temporal-correspondence-pattern.md) ungelöst für die
**A-vs-B**-Frage. Single-Event-Alignment (Zhang et al.) bleibt richtig für
Vorher/Nachher _eines_ Events; Dual-Event ist eine andere Frage.

### Schichten (verbindlich)

1. **Finden (Engine)** — Paare/Sequenzen über Zufall hinaus
2. **Markieren (Overlay)** — das andere Event in einer alignierten Ansicht
3. **Darstellen (Chart/Copy)** — lesbar, ohne Ampel-Kausalität

Ohne (1) ist (3) Dekoration. Ohne (2)/(3) bleibt (1) Feed-Spam
([#853](https://github.com/Sturmi77/correlcore/issues/853)).

---

## Reuse-first Bauflächen

| Fläche      | Pfad                                                                                                                        | Rolle                                                     |
| ----------- | --------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------- |
| Compare     | [`TrendsComparePanel.svelte`](../../apps/web/src/lib/components/trends/TrendsComparePanel.svelte)                           | Pins ≤3, Cursor-Detail, Heatmap-Rows                      |
| Marker      | [`EventMarkerLayer.svelte`](../../apps/web/src/lib/components/trends/EventMarkerLayer.svelte)                               | Soft-Bänder (`--color-event-marker-soft`), rendering-only |
| ESM         | [`EventAlignedSmallMultiplesSheet.svelte`](../../apps/web/src/lib/components/trends/EventAlignedSmallMultiplesSheet.svelte) | ±7 um Onset; Median; Lag-Spalte                           |
| Partnerwahl | Tag-/Symptom-Co-occurrence (Lift/Phi)                                                                                       | Default-B ohne neue Statistik                             |
| Lag heute   | `run_lag_analysis`                                                                                                          | Nur Feature→**Metrik**, nicht Event↔Event                 |

Episode-Collapse ([#809](https://github.com/Sturmi77/correlcore/issues/809)) ist
**erledigt** — stabile Occurrence-Atome für v2 Sequenzen sind vorhanden.

---

## Optionen (Kurzbewertung)

| Opt   | Idee                                  | User-Nutzen               | FE-Darstellung             | v-Phase           |
| ----- | ------------------------------------- | ------------------------- | -------------------------- | ----------------- |
| **1** | Zweit-Event-Glyphs im ESM (1 Partner) | Hoch (Explore)            | Gut, Mobile-Limit 1        | **v1 Vertiefung** |
| **2** | Dual-Event-Alignment                  | Mittel–hoch               | Schwach mobil              | Zurückstellen     |
| **3** | Koinzidenz-Bänder Compare (A∩B)       | **Höchster Sofortnutzen** | Beste chronologische Story | **v1 Anker**      |
| **4** | Event↔Event-Lag Engine                | Hoch (USP)                | Explore first, Feed später | **v2**            |
| **5** | Formale Interaktion A×B               | Hoch, n-hungrig           | Zwei Trajektorien          | nach Opt. 6       |
| **6** | Split-Mediane A mit/ohne B            | Hoch, visuell prüfbar     | Zwei Median-Kurven im ESM  | **v2** vor 5      |
| **7** | Multi-Event-Orchestrierung            | —                         | Scope-Explosion            | Nie v1–v2         |

Methoden-Guardrails unverändert: ADR-0021 Phasen, FDR, Assoziationssprache,
Disclaimer-Route (#632), keine Ampel-Farben (ADR-0035). Kein Sequential Pattern
Mining / HMM / Transfer Entropy.

---

## Produktentscheid (fest)

### v1 — Finden+Markieren ohne neue Engine

1. **Anker = Option 3 (Compare-Koinzidenz).**  
   Wenn ≥2 Zeilen gepinnt sind: Soft-Bänder an Tagen mit **A∩B** (UND).  
   Cursor-Detailkarte listet „A und B an diesem Tag“ — **ohne**
   Statistik-Versprechen. Pin-Limit 3 bleibt. Clientseitig aus geladenen
   Heatmap-Rows. Toggle „Koinzidenz hervorheben“; aus/disabled wenn &lt;N
   Koinzidenz-Tage (ehrlicher Empty-State, kein Scheinbefund).

2. **Vertiefung = Option 1 (ESM-Partner-Glyph).**  
   Align bleibt Event A (t=0). **Hart max. 1** Zweit-Subject B. Default =
   Top-Co-occurrence-Partner (Lift/Phi), überschreibbar. Legende analog
   [#631](https://github.com/Sturmi77/correlcore/issues/631).

3. **v1b Copy + Legende** — Alignment/Koinzidenz ≠ Ursache; Assoziationssprache.

4. **Lag-1 (A heute, B morgen)** — **nicht** in v1a. Eigenes kleines Follow-up
   **v1.1** als zweite Markierungsart hinter Toggle (Rauschen getrennt halten).

5. Sprint-Reihenfolge: **Compare (3) zuerst**, dann ESM-Overlay (1).

### v1c — Evidenz statt Präsenz (Nachtrag 2026-09-17)

**Befund nach #908 / #909 / #910.** Die gelieferten Overlays zeigen
ausschließlich **Präsenz**: ein Soft-Band (A∩B), eine gestrichelte Linie
(Lag-1), eine Eckmarke (ESM-Partner). Nirgends steht, **wie oft**. „Sport ∩
Müdigkeit an 8 von 10 Sport-Tagen“ und „2 von 30“ sehen in der UI identisch aus.
Zusätzlich verschweigt `deriveLag1`
([`lag1Markers.ts`](../../apps/web/src/lib/utils/lag1Markers.ts)) die
Richtungsasymmetrie: markiert wird nur A→B in Pin-Reihenfolge, nie B→A — dabei
ist genau diese Richtungsfrage der Grund für v1.1.

Das ist die Konstellation, für die Xiong et al. erhöhte Kausal-Zuschreibung
messen: starke Aggregation plus flächige Marks. Der vorhandene Disclaimer-Text
(„Zusammenhang, keine Ursache“) wirkt nachweislich schwächer als konkrete
Zahlen. Choe/Lee/schraefel ordnen _comparison_ und _data summary_ zu den
häufigsten Insight-Typen — beide fehlen der Overlay-UX bislang vollständig.

**Entscheid.** Jedes Overlay nennt seine Häufigkeit als **natürliche Frequenz**
(Gigerenzer/Hoffrage): ganze Zahlen mit Nenner, clientseitig aus den bereits
geladenen Heatmap-Rows bzw. Event-Windows. Keine neue Engine, kein Worker, kein
Insight-Typ — dieselbe Datenbasis wie die Marker selbst.

Copy-Muster (verbindlich, Beispiele EN/DE-neutral formuliert):

| Fläche        | Muster                                                                  |
| ------------- | ----------------------------------------------------------------------- |
| Compare A∩B   | „Beide an 6 von 22 Tagen mit Sport · 6 von 9 Tagen mit Schlaf schlecht“ |
| Compare Lag-1 | „Sport dann Müdigkeit: 5 · Müdigkeit dann Sport: 1“                     |
| ESM-Partner   | „Kaffee in 4 von 9 Ereignis-Fenstern“                                   |

Guardrails:

- Nur **ganze Zahlen mit Nenner**. Keine Prozente, Raten, p-Werte, Lift, Phi —
  das bleibt v2 vorbehalten.
- Zeitraumbezug immer mitnennen („im gewählten Zeitraum“); die Zahlen gelten für
  die sichtbare Analyse-Range, nicht für die Gesamthistorie.
- Gates unverändert: ≥2 Pins, `MIN_COINCIDENCE_DAYS` / `MIN_LAG1_DAYS` = 2.
- Lag-1 nennt **beide** Richtungen, auch wenn eine davon 0 ist — die Asymmetrie
  ist die Information.
- Keine Ampelfarben, keine Ranking- oder Stärke-Sprache („stärkster
  Zusammenhang“); die Zahl steht bei der Legende, nicht als eigene Karte
  (kein Feed-Spam, Lektion #853).

**Warum keine Statistik in v1c.** „Explore first, Feed later“ bleibt gültig.
Eine Häufigkeit mit Nenner ist eine Beschreibung der eigenen Einträge und
braucht weder FDR noch Reifegrad-Gate; ein Lift-/Phi-Wert oder p-Wert wäre ein
Befund und gehört damit in v2 (Option 4/6) mit den dortigen Guardrails.

### v2 — Finden mit Engine / Wechselwirkung

1. **Option 4** eng gescopt: Kandidaten nur aus Co-occurrence-Top-Paaren +
   min frequency, Lag 1–3, FDR, min count. **Zuerst nur Explore-Overlay**,
   keine automatischen Feed-Karten. Eigener `InsightType` erst nach
   Qualitätsnachweis (eine Card: Satz + Link „Ereignisse ausrichten“, kein
   Dritt-Chart — Lektion #853).

2. **Option 6 vor Option 5** — Split-Mediane visuell prüfbar; formaler
   Interaktionstest nur wenn 6 trägt und Zell-Minima greifen.

### Zurückgestellt

- Option 2 (Dual-Align), Option 7 (Multi-Event)
- `#892` `inferred_period` als Facette — Datenmodell mitdenken, kein v1-Scope

### UX-Prinzipien (verbindlich für Folge-Issues)

1. Explore first, Feed later
2. Eine dominante Fläche pro Phase (Compare Anker, ESM Vertiefung)
3. Copy ohne Ampel / Kausalität
4. Mobile: kein Dual-Chart &lt;768px; max. ein Overlay-Subject
5. Leere Ehrlichkeit bei insufficient_n
6. Legende wie #631
7. Jedes Overlay nennt seine Häufigkeit als natürliche Frequenz (v1c) —
   ganze Zahlen mit Nenner, keine Prozente/Raten/p-Werte

---

## Beantwortete Entscheidungsfragen

| #   | Frage          | Entscheidung                                                                 |
| --- | -------------- | ---------------------------------------------------------------------------- |
| 1   | v1-Fläche      | **Beides** (3 + 1); Compare zuerst                                           |
| 2   | Lag-1 in v1    | **Nein** — nur A∩B in v1a; Lag-1 in **v1.1**                                 |
| 3   | v2 InsightType | **Overlay zuerst**; InsightType später bei belegter Präzision                |
| 4   | Zahlen in v1   | **Ja, als natürliche Frequenz** (v1c) — Zähler + Nenner, keine Raten/p-Werte |

---

## Folge-Issues

| Phase | Issue | Scope                                                     |
| ----- | ----- | --------------------------------------------------------- |
| v1a   | #908  | Compare A∩B-Bänder                                        |
| v1b   | #909  | ESM Partner-Glyph (max. 1)                                |
| v1.1  | #910  | Lag-1-Markierung auf Compare                              |
| v1c   | #917  | Compare: natürliche Häufigkeiten A∩B + Lag-1 (beidseitig) |
| v1c   | #918  | ESM: Partner-Trefferquote, Lade- und Fehlerzustand        |
| v1c   | #919  | Overlay-Härtung: Entdeckbarkeit, Legenden-Swatch, a11y    |
| v2    | #920  | Opt. 6 Split-Mediane im ESM (A mit B vs. A ohne B)        |
| v2    | —     | Opt. 4 Event↔Event-Lag (noch kein Issue)                  |

Ready-to-paste Bodies (Referenz, Issues bereits angelegt):

#891 bleibt Analyse-/Entscheidungsartefakt; `Closes #891` **nicht** auf dem
ersten Overlay-PR — nur `Relates to #891` / `Part of #891`. Schließen erst wenn
die gewählte v1-Phase (#908+#909+Copy) gelandet ist oder Owner das Analyse-Issue
bewusst schließt.

### Draft A — v1a → #908

**Title:** `[FE] Trends Compare: Koinzidenz-Bänder für gepinnte Zeilen (A∩B)`

```markdown
## Relates to

Part of #891 (v1 Anker — Option 3). Produktentscheid:
`docs/proposals/FEATURE_EVENT_INTERACTION_TIMELINE.md`

## Ziel

Auf `/trends` Compare Soft-Bänder an Tagen hervorheben, an denen **zwei oder
mehr gepinnte** Tag-/Symptom-Zeilen gemeinsam aktiv sind (A∩B). Cursor-Detailkarte
listet die Koinzidenz — ohne Statistik-Versprechen.

## Scope (v1a)

- Clientseitig aus bereits geladenen Heatmap-Rows (kein Worker, kein neuer Insight-Typ)
- Trigger nur bei ≥2 Pins; Pin-Limit 3 unverändert
- Marker über `EventMarkerLayer` (`--color-event-marker-soft`)
- Toggle „Koinzidenz hervorheben“; disabled/empty wenn <N Koinzidenz-Tage
- i18n + Legende (Koinzidenz ≠ Ursache; Assoziationssprache)
- Unit-/Component-Tests für Marker-Ableitung und Toggle-Gate

## Out of scope

- Lag-1 (A→B +1d) — Draft C / v1.1
- ESM-Partner-Glyph — Draft B (Option 1)
- Event↔Event-Lag Engine / Feed-Karten

## Akzeptanz

- [ ] ≥2 Pins → Bänder an A∩B-Tagen sichtbar
- [ ] Cursor-Karte nennt beide Subjects am Tag
- [ ] <N Koinzidenz-Tage → Toggle aus / ehrlicher Empty-State
- [ ] Keine Ampel-Farben; Copy assoziativ
- [ ] Mobile: keine zusätzliche Chart-Fläche

## Datenschutz

Nur Aggregate/Präsenz aus bestehenden Rows; keine Rohnotizen.
```

### Draft B — v1b → #909

**Title:** `[FE] ESM: ein Partner-Glyph (Zweit-Event) in Event-Fenstern`

```markdown
## Relates to

Part of #891 (v1 Vertiefung — Option 1). Produktentscheid:
`docs/proposals/FEATURE_EVENT_INTERACTION_TIMELINE.md`

## Ziel

Im Event-Aligned Small Multiples Sheet (Align auf Event A, t=0) maximal **ein**
Zweit-Subject B als Glyph/getönte Zelle in den ±7-Fenstern zeigen.

## Scope

- Default B = Top-Co-occurrence-Partner (bestehendes Lift/Phi), überschreibbar
- Hartes Limit: 1 Partner (Mobile / ~3-Panel-Budget)
- Legende analog #631 (Overlay ≠ Ursache)
- Reuse Zell-/Marker-Encoding; keine Dual-Align-Layout-Änderung
- Tests für Limit, Default-Partner, Empty wenn kein Partner

## Out of scope

- Dual-Event-Alignment (Option 2)
- Split-Mediane (Option 6) / Interaktionstest (Option 5)
- Neue Engine-Familie

## Akzeptanz

- [ ] Bei geöffnetem ESM erscheint höchstens ein Partner-Overlay
- [ ] Default kommt aus Co-occurrence; User kann wechseln
- [ ] Unter 768px kein zweites Chart neben dem Align
- [ ] Copy/Legende assoziativ

## Datenschutz

Onsets/Aggregate wie bestehende event-windows; keine Rohnotizen.
```

### Draft C — v1.1 → #910

**Title:** `[FE] Trends Compare: optionale Lag-1-Markierung (A dann B +1d)`

```markdown
## Relates to

Part of #891 (v1.1). Baut auf Draft A (A∩B) auf.
Produktentscheid: `docs/proposals/FEATURE_EVENT_INTERACTION_TIMELINE.md`

## Ziel

Zweite Markierungsart hinter Toggle: Tage, an denen A aktiv und B am
**nächsten** Kalendertag aktiv ist (A→B +1d). Schmalerer Marker als A∩B-Band.

## Scope

- Nur wenn Draft A gelandet; eigener Toggle oder Modus neben A∩B
- Clientseitig; kein neuer Insight-Typ
- Cursor-Zeile „A dann B (+1d)“
- Gate bei zu wenigen Lag-1-Tagen

## Out of scope

- Lag 2–3, Event↔Event-Engine (v2 Option 4)
- Feed-Karten

## Akzeptanz

- [ ] Lag-1-Marker nur bei explizitem Toggle
- [ ] A∩B und Lag-1 visuell unterscheidbar
- [ ] Assoziative Copy; kein Kausal-Claim
```

### Später (v2, kein Draft hier)

- Option 4 Event↔Event-Lag (Explore first, eng gescopt)
- Option 6 Split-Mediane vor Option 5

---

## Datenschutz

Analyse ändert keine Verarbeitung. Umsetzung bleibt bei Entry-/Tag-/Symptom-
Aggregaten und Onsets. Keine Rohnotizen auf der Achse. Event↔Event-Insights
unterliegen `analytics_enabled` und Reifegrad-Gates.

---

## Referenzen

- [#891](https://github.com/Sturmi77/correlcore/issues/891) + Owner-Kommentare
- [ADR-0035](../adr/0035-temporal-correspondence-pattern.md) (+ Addendum Dual-event coincidence)
- [`PHASE_INSIGHT_MATRIX.md`](../PHASE_INSIGHT_MATRIX.md)
- [`FEATURE_LAG_CORRELATION_VISUALIZATION.md`](FEATURE_LAG_CORRELATION_VISUALIZATION.md) (Feature→Metrik, nicht Event↔Event)
- `#809` Episoden, `#488` Lag-Marker, `#631` ESM-Erklärung, `#853` Lag-UX, `#632` Disclaimer

### Forschung zu v1c (Evidenz statt Präsenz)

- Cindy Xiong, Joel Shapiro, Jessica Hullman, Steven Franconeri. „Illusion of
  Causality in Visualized Data.“ IEEE VIS 2019 —
  [PDF](https://mucollective.northwestern.edu/files/2019-Correlation%20Causation-VIS.pdf).
  Weniger Aggregation und punktförmige statt flächiger Marks senken die
  Kausal-Zuschreibung; erklärender Text allein wirkt schwächer als Zahlen.
- Eun Kyoung Choe, Bongshin Lee, m.c. schraefel. „Characterizing Visualization
  Insights from Quantified Selfers' Personal Data Presentations.“ IEEE CG&A
  35(4), 2015. DOI: [10.1109/MCG.2015.51](https://doi.org/10.1109/mcg.2015.51).
  Acht Insight-Typen; _comparison_ und _data summary_ fehlen der reinen
  Präsenz-Markierung.
- Simon Jones, Ryan Kelly. „Finding ‚Interesting‘ Correlations in Multi-Faceted
  Personal Informatics Systems.“ CHI EA 2016. DOI:
  [10.1145/2851581.2892401](https://doi.org/10.1145/2851581.2892401).
  Abgleich Erwartung ↔ Befund als Filter gegen Rausch-Insights.
- Gerd Gigerenzer, Ulrich Hoffrage. „How to Improve Bayesian Reasoning Without
  Instruction: Frequency Formats.“ _Psychological Review_ 102(4), 1995.
  Natürliche Frequenzen („6 von 22“) werden zuverlässiger verstanden als
  Prozente oder bedingte Wahrscheinlichkeiten.

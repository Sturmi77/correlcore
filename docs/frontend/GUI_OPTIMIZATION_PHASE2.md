# CorrelCore — GUI Optimization Phase 2

**Date:** 2026-06-30  
**Predecessor:** O-01–O-20 ([`OPTIMIZATION_BACKLOG.md`](OPTIMIZATION_BACKLOG.md), PR #281, #284)  
**Source audits:** [`FRICTION_AUDIT.md`](FRICTION_AUDIT.md) · [`FRONTEND_STREAMLINE_CONCEPT.md`](../FRONTEND_STREAMLINE_CONCEPT.md)

Phase 1 removed funnel friction, duplicate maturity UI, and legacy paths. Phase 2 targets **information architecture**, **progressive disclosure placement**, and **mobile vertical rhythm**.

---

## 1. Schlüsse aus Phase 1

| Erkenntnis                                                     | Umsetzung in Phase 2                             |
| -------------------------------------------------------------- | ------------------------------------------------ |
| Progressive Disclosure an den **falschen** Stellen erhöht Taps | Entry: Tags/Symptome nicht verstecken (O-21)     |
| Mehrere Kontroll-Reihen verwirren (Insights)                   | Eine Filterzeile + Matrix als Drill-down (O-22)  |
| Zeiträume fragmentiert                                         | Globales `analysisRange` (O-23)                  |
| Spacing nicht systematisch                                     | Token-Lücke + Doppel-Padding (O-30, siehe unten) |

---

## 2. Backlog O-21 – O-30

| ID       | Impact     | Effort  | Title                                                          | Klasse           |
| -------- | ---------- | ------- | -------------------------------------------------------------- | ---------------- |
| O-21     | High       | Medium  | Entry: Tags + Symptome immer sichtbar; Toggle nur Notiz/Zyklus ✅ | Vereinfachen     |
| O-22     | High       | Medium  | Insights: eine Kontrollzeile (Kategorie-Chips + Matrix-Link)   | Zusammenführen   |
| O-23     | High       | Medium  | Globales `analysisRange` für Trends + Insights                 | Zusammenführen   |
| O-24     | Medium     | Low     | Symptom-Analytik über Kategorie-Filter statt Checkbox          | Eliminieren      |
| O-25     | Medium     | High    | Entry: „Schnell“ vs. „Vollständig“ beim Öffnen                 | Umleiten         |
| O-26     | Medium     | Low     | Trends Mobile: Detail-Toggle vs. Scroll prüfen                 | Vereinfachen     |
| O-27     | Low        | Medium  | Settings-Vokabular-Hub (W8)                                    | Zusammenführen   |
| O-28     | Medium     | High    | Account-Löschung (M9)                                          | Vereinfachen     |
| O-29     | Low        | Low     | Trends Compare-Filter nur bei geöffnetem Mobile-Detail         | Vereinfachen     |
| **O-30** | **Medium** | **Low** | **Spacing-System: Token, screen-stack, Mobile-Dichte**         | **Vereinfachen** |

---

## 3. Spacing-Audit (Mobile)

### 3.1 Befunde vor O-30

| Problem                          | Beispiel                                                                    | Wirkung auf 390 px                                           |
| -------------------------------- | --------------------------------------------------------------------------- | ------------------------------------------------------------ |
| **Fehlendes Token `--space-5`**  | EntryForm, Home, Insights, EmptyState                                       | Inkonsistente Abstände (CSS ignoriert ungültige `var()`)     |
| **Doppeltes Horizontal-Padding** | Trends/Settings: `padding: 1.25rem` innerhalb `.page-shell`                 | ~32 px Seitenrand statt ~16 px — **~8 % weniger Nutzbreite** |
| **Addierte vertikale Gaps**      | Insights: Page-Gap + TabBar + Feed-Gap + Karten-Gap                         | „Totluft“ zwischen Kontrollen, Inhalt rutscht nach unten     |
| **Entry-Sheet Overhead**         | `padding-top: space-6` + Section-Cards mit `space-4`                        | Mood-Slider erst nach ~120 px sichtbar                       |
| **Hardcoded rem-Werte**          | `gap: 1rem`, `0.65rem`, `0.15rem` in Routes/Heatmaps                        | Brechen 4-px-Raster, schwer wartbar                          |
| **Uneinheitliche Page-Padding**  | Home `padding-block`, Insights `padding: 4 0 8`, Trends `1.25rem` allseitig | Jeder Screen fühlt sich anders „luftig“ an                   |

### 3.2 Spacing-Prinzipien (Zielvertrag)

1. **Horizontal:** Nur `.page-shell` setzt Seitenabstand (`--page-padding-x`). Routen nutzen **kein** zusätzliches `padding-inline`.
2. **Vertikal:** `.screen-stack` mit `--screen-gap` (Desktop 16 px, Mobile 12 px) zwischen Hauptblöcken.
3. **Dichte-Stufen:**
   - `--screen-gap-tight` (12 px / 12 px) — Listen, Feed-Karten
   - `--screen-gap` (16 px / 12 px) — Standard-Screens
   - `--screen-gap-loose` (24 px / 16 px) — Home-Zonen
4. **Sektionen in Sheets:** Flache Trennlinien statt verschachtelter Cards auf Mobile (EntryForm bereits so — beibehalten).
5. **Touch bleibt:** `min-height: 44px` für interaktive Elemente unverändert; Dichte durch **weniger Zwischenräume**, nicht kleinere Targets.

### 3.3 O-30 Umsetzung (Foundation)

**`apps/web/src/app.css`**

- `--space-5: 1.25rem` ergänzt (fehlende Stufe im 4-px-System)
- Rhythm-Tokens: `--screen-gap`, `--screen-gap-tight`, `--screen-gap-loose`, `--screen-padding-block*`
- Mobile Override (`max-width: 767px`): engere Gaps
- Utility `.screen-stack` (+ `--tight` / `--loose`)

**Routen/Komponenten**

| Datei                          | Änderung                                          |
| ------------------------------ | ------------------------------------------------- |
| `routes/+page.svelte` (Home)   | `screen-stack--loose`, kein eigenes Block-Padding |
| `routes/trends/+page.svelte`   | `screen-stack`, kein `padding: 1.25rem`           |
| `routes/insights/+page.svelte` | `screen-stack--tight`                             |
| `routes/settings/+page.svelte` | `screen-stack`, Token-Gaps in Panels              |
| `EntrySheet.svelte`            | Mobile: weniger Top/Side-Padding                  |
| `EntryForm.svelte`             | Mobile: `--screen-gap` zwischen Sektionen         |
| `InsightFeed.svelte`           | `--screen-gap` / `--screen-gap-tight` für Feed    |
| `TabBar.svelte`                | Etwas schmalere horizontale Item-Padding          |

### 3.4 Offene Spacing-Arbeit (O-31+)

| ID   | Titel                                                                                  |
| ---- | -------------------------------------------------------------------------------------- |
| O-31 | Settings-Unterrouten (`tags`, `symptoms`, `entries/day`) auf `screen-stack`            |
| O-32 | Heatmap-Mikro-Gaps (`0.15rem` …) auf `--space-1` / dedizierte `--heatmap-cell-gap`     |
| O-33 | `ScreenHeader` → erster Block: fester `--screen-header-gap` statt impliziter Page-Gap  |
| O-34 | InsightStageHeader / MobileInsightLead: kompaktere interne Padding auf Mobile          |
| O-35 | Lint/Contract-Test: verbietet `padding: 1.25rem` auf Route-Root innerhalb `page-shell` |

---

## 4. Entry: Aufklappen vs. Scroll

**Audit-W3 Schritt 6** bewertete „Mehr anzeigen“ als akzeptabel (Score 1). Für CorrelCore gilt:

| Feld                    | Disclosure                | Begründung                                              |
| ----------------------- | ------------------------- | ------------------------------------------------------- |
| Stimmung/Energie/Stress | immer sichtbar            | 60-Sekunden-Quick-Log                                   |
| Tags, Symptome          | **immer sichtbar** (O-21) | Treiber für Insights — Aufklappen = täglicher Extra-Tap |
| Notiz, Zyklus           | optional eingeklappt      | Selten, viel Platz                                      |
| Tageszeit-Slots         | in Datumszeile            | Weniger Sektionen                                       |

---

## 5. Insights: Kontroll-Schichten reduzieren

**Ist (bis zu 6 Ebenen):** Header → Maturity → View-Tabs → Kategorie-Tabs → Analytics-`<details>` → Range in Heatmap

**Soll (2 Ebenen):**

1. Kompakter Maturity-Kontext
2. Inhaltsfilter (Chips) + optional Matrix-Link
3. Feed (primär)
4. Sekundäranalyse lazy, **ohne** eigene Range-Leiste (an O-23 gekoppelt)

---

## 6. Globales Analysefenster (O-23)

Trends hat seit O-15 ein sticky `range`. Insights-Co-Occurrence nutzt noch lokale `30d|90d|1y`-Buttons.

**Ziel:** Shared Store `analysisRange` — Trends `week|month|quarter|year` ↔ Insights `30d|90d|1y` über `rangeToDays()`. Home-Brief bezieht sich auf abgeleitetes 7-Tage-Fenster.

---

## 7. Empfohlene Sprint-Reihenfolge

1. **O-30** Spacing Foundation _(dieser PR)_
2. **O-21** Entry flatten
3. **O-23** Globales Analysefenster
4. **O-22 + O-24** Insights IA
5. **O-31–O-35** Spacing-Härtung

---

## 8. Erfolgskriterien Phase 2

- Erster sichtbarer Inhalt auf Insights/Trends/Home **≥ 1 Viewport-Block höher** auf 390×844
- Kein Route-Root mit horizontalem Padding innerhalb `page-shell`
- Alle `--space-*` Tokens definiert und verwendet
- Nutzer mit täglichen Symptom-Logs: **0 Extra-Taps** für Symptom-Erfassung

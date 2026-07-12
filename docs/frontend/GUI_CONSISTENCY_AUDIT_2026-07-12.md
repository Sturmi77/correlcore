# GUI-Konsistenz-Audit — Findings & Umsetzungsplan

**Datum:** 2026-07-12
**Scope:** `apps/web` (SvelteKit 2, Tailwind 4, Token-System in `apps/web/src/app.css`)
**Zielgruppe:** KI-Agenten, die die Findings umsetzen. Jedes Finding enthält Evidenz (Datei/Zeile), Maßnahme und Akzeptanzkriterien.
**Referenzdokumente:** `docs/FRONTEND.md` (Prinzipien §1, Design System §4), `docs/frontend/UI_COMPONENT_SYSTEM.md`, `docs/frontend/COLOR_SCHEME_CONCEPT.md`, `apps/web/src/lib/ui/surfaceContract.ts`

> Zeilenangaben beziehen sich auf den Stand vom 2026-07-12. Vor jeder Änderung
> die Fundstelle per `grep` re-verifizieren, nicht blind an Zeilennummern editieren.

---

## Arbeitsregeln für umsetzende Agenten

1. Ein Finding = ein PR/Branch (Ausnahme: gebündelte Work Packages, siehe unten).
2. Nach jeder Änderung lokal verifizieren: `pnpm lint && pnpm typecheck && pnpm test && pnpm check:contrast && pnpm build` (aus `apps/web`), bei UI-Verhalten zusätzlich `pnpm test:e2e:smoke`.
3. Keine neuen Hardcodings einführen — jede Farbe, jeder Radius, jede Font-Size, jede Transition kommt aus einem Token in `app.css`.
4. Bestehende Tests (`*.test.ts` neben Komponenten) mitpflegen.
5. Dark **und** Light manuell prüfen (Toggle via `data-theme` auf `<html>`), sowie 390 px und 1280 px (Baseline-Viewports aus `surfaceContract.ts`).

---

## Prioritäten-Übersicht

| Prio | Findings         | Charakter                                                      |
| ---- | ---------------- | -------------------------------------------------------------- |
| P0   | F-01, F-02, F-03 | Sichtbare Bugs / kaputte Styles                                |
| P1   | F-04 … F-10      | Systematische Inkonsistenzen (Dark/Light, Mobile/Web, Screens) |
| P2   | F-11 … F-18      | Token-Hygiene, Prinzipien-Verstöße, Doku-Drift                 |
| P3   | F-19 … F-21      | Aufräumen, Guardrails, Nice-to-have                            |

---

## P0 — Bugs

### F-01: Undefinierte Skeleton-Klassen — Primary-Buttons ohne Fill

**Kategorie:** Screens untereinander, Dark/Light
**Evidenz:** `variant-filled-primary` wird **20×** verwendet (13 Dateien), ist aber **nirgends definiert**. `@skeletonlabs/skeleton` + `@skeletonlabs/tw-plugin` stehen in `apps/web/package.json`, werden aber nie eingebunden (kein `tailwind.config.*`, kein CSS-Import — Tailwind 4 läuft über `@tailwindcss/vite`). `app.css` shimt nur `variant-ghost-surface`, `variant-ghost-error`, `variant-soft-warning` (Zeilen 644–652). Undefiniert sind: `variant-filled-primary` (20×), `variant-soft-primary` (5×), `variant-ghost-primary` (1×).

Betroffen u. a.:

- `src/routes/auth/login/+page.svelte:86` (`class="btn variant-filled-primary auth-submit"`)
- alle weiteren Auth-Routen (`register`, `forgot-password`, `reset-password`, `resend-verification`, `verify-email`)
- `src/routes/onboarding/profile/+page.svelte`, `src/routes/onboarding/retro/+page.svelte`
- `src/routes/entries/day/[date]/+page.svelte`, `src/routes/settings/tags/+page.svelte`
- `src/lib/components/entries/TagPicker.svelte`, `SymptomChecker.svelte`, `src/lib/components/insights/InsightJourneyExplainer.svelte`

**Wirkung:** Primäre CTAs (u. a. Login-Submit) rendern als randloser Ghost-Button statt als gefüllter Primary-Button — in beiden Themes.

**Maßnahme:**

1. Alle Vorkommen auf die Shared-Primitive `Button` (`src/lib/components/common/Button.svelte`, Prop `variant`) migrieren — das ist der von `docs/FRONTEND.md` §4.5 geforderte Weg.
2. Wo ein natives `<button>` bleiben muss (z. B. Form-Submit mit Sonderlayout): definierte Klassen in `app.css` ergänzen (`.btn--primary` mit `background: var(--color-primary); color: var(--color-text-inverse);` + Hover/Active aus `--color-primary-hover/-active`).
3. `@skeletonlabs/*`-Dependencies aus `package.json` entfernen (siehe F-19).

**Akzeptanz:** `grep -rn 'variant-filled-primary\|variant-soft-primary\|variant-ghost-primary' apps/web/src` liefert 0 Treffer; Login/Register-Submit ist in Dark und Light sichtbar gefüllt; Unit-Tests grün.

### F-02: Fehlender Token `--color-success-highlight`

**Kategorie:** Dark/Light
**Evidenz:** `src/routes/auth/forgot-password/+page.svelte:127` — `background: var(--color-success-highlight, rgba(34, 197, 94, 0.1));`. Token existiert in keinem Theme; der Fallback ist in Dark und Light identisch und umgeht das Token-System. `--color-error-highlight` existiert dagegen in beiden Themes (`app.css:111`, `:181`).

**Maßnahme:** `--color-success-highlight` in `app.css` für Dark (`#1f3327` o. ä., analog `--color-error-highlight`) und Light (`#f0fdf4`) definieren; Fallback entfernen. Symmetrie herstellen: optional auch `--color-warning-highlight` gleich mitdefinieren, da `variant-soft-warning` (app.css:649) derzeit fälschlich **Error**-Farben nutzt (`--color-error` statt `--color-warning`) — das ist ein eigener Mini-Bug, bitte mitfixen.

**Akzeptanz:** Token in beiden Theme-Blöcken + im `prefers-color-scheme`-Fallback (falls dieser bleibt, siehe F-08) definiert; keine `rgba(34, 197, 94`-Literale mehr; `.variant-soft-warning` nutzt Warning-Farben.

### F-03: Hardcodierter Default-Tag-Farbwert `#6356d9`

**Kategorie:** Dark/Light
**Evidenz:** `src/routes/settings/tags/+page.svelte:44, :62, :73` — Default-Farbe neuer Tags ist das **Light**-Primary (`#6356d9`). Im Dark-Theme ist Primary `#7c6af5`; neu angelegte Tags wirken dort fremd/dunkler als die UI-Akzentfarbe.

**Maßnahme:** Default-Farbe als benannte Konstante nach `src/lib/constants/` extrahieren (z. B. `DEFAULT_TAG_COLOR`). Entscheidung dokumentieren: entweder (a) bewusst theme-unabhängiger Speicherwert (dann Kommentar + im UI-Swatch per Token rendern) oder (b) beim Anlegen die aktuelle Theme-Primary übernehmen. Empfehlung: (a) mit einem neutralen Mittelwert zwischen beiden Primaries, da der Wert persistiert wird und beide Themes überleben muss.

**Akzeptanz:** Kein Hex-Literal mehr in der Route; Konstante mit Begründungskommentar; Tag-Anlage in Dark und Light visuell geprüft.

---

## P1 — Systematische Inkonsistenzen

### F-04: Breakpoint-Wildwuchs (Mobile/Web)

**Kategorie:** Mobile vs. Web
**Evidenz:** `surfaceContract.ts` definiert **768 px** als einzigen Shell-Breakpoint; `docs/FRONTEND.md` §1.6 nennt 375/768/1024. Tatsächlich verwendet der Code **14 verschiedene** Breakpoints in `@media`-Queries (Svelte-Komponenten):

```
18× max-width: 520px   6× max-width: 420px   4× min-width: 768px
 4× max-width: 767px   3× max-width: 640px   3× max-width: 430px
 2× min-width: 48rem   2× max-width: 760px   je 1×: 360, 480(min), 640(min), 680, 720, 860
```

Problematisch: `max-width: 760px` (statt 767) in `InsightPhaseMilestoneCard.svelte` und `HabitsPanel.svelte` sowie `min-width: 48rem` (Einheiten-Mix) in `InsightJourneyExplainer.svelte` und `HabitDetailBody.svelte` — vier Komponenten schalten knapp **neben** dem Shell-Breakpoint um.

**Maßnahme:**

1. Kanonische Breakpoints festlegen und in `app.css` als Kommentar-Kontrakt dokumentieren: `360` (mini), `480` (schmal), `768` (Shell, = `DESKTOP_SHELL_BREAKPOINT_PX`), `1024` (wide). CSS Custom Media ist ohne PostCSS-Plugin nicht verfügbar — daher Kontrakt als dokumentierte Konvention + Lint-Gate (siehe F-21).
2. `760px` → `767px`, `48rem` → `768px` korrigieren (Mini-PR, sofort machbar).
3. `520/420/430/640/680/720/860` fallweise auf die kanonischen Werte mappen; wo ein komponenteninterner Umbruch wirklich nötig ist, Container-Query erwägen statt Viewport-Query.

**Akzeptanz:** Kein `760px`/`48rem` mehr; Anzahl distinkter Breakpoints ≤ 5; `pnpm test:e2e:mobile` grün; Screens bei 390/430/768/1280 px ohne Layoutbruch.

### F-05: Kein gemeinsames `BottomSheet`-Primitive — 9 Dialog-Implementierungen

**Kategorie:** Screens untereinander, Mobile/Web
**Evidenz:** `docs/FRONTEND.md` §4.5 fordert `BottomSheet` als Pflicht-Primitive. Es existiert nicht (`src/lib/components/common/` enthält keins). Stattdessen implementieren 9 Komponenten je eigenen Backdrop, Panel, Close-Logik:
`EntrySheet`, `CooccurrenceEntrySheet`, `CorrelationDisclaimer`, `InsightJourneyExplainer`, `SymptomCooccurrenceDetailSheet`, `EntryHistorySheet`, `EventAlignedSmallMultiplesSheet`, `HabitDetailSheet`, `TrendsCompareSettingsSheet` (+ 2 Modal-Backdrops in `routes/settings/+page.svelte:488, :550`).

**Maßnahme:** `BottomSheet.svelte` in `common/` extrahieren (Props: `open`, `titleId`, Slot für Header/Body/Footer; `<dialog>`-basiert gemäß `docs/frontend/ESLINT_SVELTE_GUARDRAILS.md` §1; Backdrop-Token aus F-06; `env(safe-area-inset-bottom)`-Padding gemäß §1.6). Sheets schrittweise migrieren — Reihenfolge: zuerst die 4 Trends/Insights-Sheets mit identischem `oklch(0 0 0 / 0.48)`-Backdrop, dann die Sonderfälle.

**Akzeptanz:** Primitive mit eigenem Test; ≥ 4 Sheets migriert; keine neue Sheet-Komponente ohne das Primitive (Guardrail-Eintrag in `UI_COMPONENT_SYSTEM.md`).

### F-06: Scrim/Backdrop uneinheitlich und nicht theme-differenziert

**Kategorie:** Dark/Light, Screens untereinander
**Evidenz:** Vier Sheets nutzen `background: oklch(0 0 0 / 0.48)` (`TrendsCompareSettingsSheet.svelte:174`, `CooccurrenceEntrySheet.svelte:97`, `HabitDetailSheet.svelte:78`, `EntryHistorySheet.svelte:128`); `SymptomCooccurrenceDetailSheet.svelte:129` nutzt abweichend `color-mix(in srgb, var(--color-surface-inverse, #000) 45%, transparent)` mit **undefiniertem** Token `--color-surface-inverse`. Der Scrim ist in Light identisch schwarz-stark wie in Dark.

**Maßnahme:** Token `--color-scrim` in beiden Themes definieren (Dark: `oklch(0 0 0 / 0.48)`, Light: schwächer, z. B. `oklch(0.2 0.01 80 / 0.35)`); alle Backdrops darauf umstellen; `--color-surface-inverse`-Verweis entfernen.

**Akzeptanz:** `grep -rn 'oklch(0 0 0 / 0.48)\|surface-inverse' apps/web/src --include='*.svelte'` = 0 Treffer (bewusst nur `*.svelte`, da `app.css` nach korrekter Umsetzung selbst den Wert `oklch(0 0 0 / 0.48)` für `--color-scrim` (Dark) enthält — ein Grep über den ganzen `apps/web/src`-Baum ohne diese Einschränkung würde dort fälschlich anschlagen); Sheets in Light sichtbar weniger hart abgedunkelt.

### F-07: `ScreenHeader` fehlt auf Primär-Screens — Home hat gar kein `<h1>`

**Kategorie:** Screens untereinander, Accessibility
**Evidenz:** `ScreenHeader` wird genutzt von: insights, trends, settings (+Unterseiten), impressum, privacy. **Nicht** genutzt: Home (`src/routes/+page.svelte` — enthält überhaupt kein `<h1>`, nur ein `<h2>` im PWA-Prompt, Zeile 200), `entries/day/[date]` (rohes `<h1>`, Zeile 112), Onboarding (rohe `<h1>`, Zeilen 108/161). `docs/FRONTEND.md` §4.6: „Every primary screen: One screen title via ScreenHeader". Auth-Routen haben bewusst eigenes `auth-page-title`-Layout — das ist als Public-Route-Ausnahme vertretbar, sollte aber in `UI_COMPONENT_SYSTEM.md` als dokumentierte Ausnahme stehen.

**Maßnahme:** Home erhält `ScreenHeader` (ggf. visuell kompakt / `sr-only`-Variante, falls das Daily-Brief-Design keinen sichtbaren Titel will — dann `ScreenHeader` um eine `visuallyHidden`-Prop erweitern). `entries/day` und Onboarding auf `ScreenHeader` migrieren. Auth-Ausnahme dokumentieren.

**Akzeptanz:** Jede navigierbare Primär-Route rendert genau ein `<h1>`; axe/a11y-Check ohne „page has no level-one heading"; bestehende `ScreenHeader.test.ts` erweitert.

### F-08: Theme-Bootstrap ignoriert System-Preference; toter CSS-Fallback-Block

**Kategorie:** Dark/Light, Doku-Drift
**Evidenz:** `docs/FRONTEND.md` §4.1 verspricht „System preference via prefers-color-scheme as default". Tatsächlich: `app.html:2` setzt statisch `data-theme="dark"`; das Inline-Script (app.html:21–35) liest nur `localStorage`, prüft **kein** `matchMedia('(prefers-color-scheme: light)')`. Erstbesucher mit Light-OS bekommen Dark. Dadurch ist der komplette Fallback-Block `@media (prefers-color-scheme: dark) { :root:not([data-theme]) { … } }` (`app.css:220–270`, ~50 duplizierte Token-Zeilen) **toter Code** — `data-theme` ist immer gesetzt. Der Block ist zugleich ein Drift-Risiko (Token-Änderungen müssen dreifach gepflegt werden).

**Maßnahme (Variante A, empfohlen — Doku erfüllen):** Inline-Script erweitern: wenn kein gespeicherter Wert, `matchMedia`-Ergebnis als `data-theme` setzen. Fallback-Block in `app.css` löschen.
**Variante B (Verhalten beibehalten):** Dark-Default als bewusste Entscheidung in `FRONTEND.md` §4.1 + ADR nachziehen und den toten CSS-Block löschen.

**Akzeptanz:** `app.css` enthält Theme-Tokens nur noch **zweimal** (dark + light); Verhalten bei Erstbesuch entspricht der Doku; `mobile-theme-parity.spec.ts` grün.

### F-09: Touch-Targets unter 44 px in Trends-Compare und Symptom-Kalender

**Kategorie:** Mobile vs. Web, Prinzip §1.6 (WCAG 2.5.5)
**Evidenz:**

- `TrendsComparePanel.svelte:380` (`min-height: 32px`), `:402` (`36px`)
- `TrendsCompareQuickFilters.svelte:82, :107, :117` (`36px`)
- `TrendsCompareSettingsSheet.svelte:274` (`32px`)
- `SymptomCalendarHeatmap.svelte:188–196`: klickbare `<button>`-Zellen mit **12 × 12 px**.

**Maßnahme:** Compare-Controls auf `min-height: 44px` bzw. kompaktes Desktop-Layout nur ≥ 768 px erlauben (Mobile: 44 px). Heatmap-Zellen: Hit-Area per transparentem Padding/`::after` auf ≥ 24 px (dichte Matrix-Ausnahme gemäß §1.6) vergrößern, ohne die visuelle Zellgröße zu ändern; alternativ Tap öffnet Tages-Detail über eine Zeilen-/Wochen-Zielfläche.

**Akzeptanz:** Interaktive Elemente mobil ≥ 44 px (Matrix-Zellen ≥ 24 px Hit-Area); Playwright-Touch-Target-Checks (bestehende Sprint-1-Coverage) erweitert um Trends-Compare.

### F-10: Typografie-Skala wird flächig umgangen

**Kategorie:** Screens untereinander
**Evidenz:** Tokens definieren `--text-xs … --text-xl` (app.css:11–15). Im Code: **60+** hartkodierte `font-size`-Werte zwischen `0.6rem` und `2rem` (u. a. `InsightCard.svelte:525` `0.6rem`, `HomeWeekdayOverview.svelte:132` `0.62rem`, `HabitDetailBody.svelte:166` `2rem`, diverse `1.5rem`-Sheet-Titel, Chart-Achsen `10px/11px` in `MetricTimeseries.svelte`). `--text-2xl` wird in `routes/dev/+page.svelte:292` benutzt, existiert aber nicht.

**Maßnahme:**

1. Skala erweitern: `--text-2xs` (≈0.68rem, für Chart-/Legend-Microcopy) und `--text-2xl` (≈1.75–2rem, Display) in `app.css` ergänzen.
2. Mapping-Migration: `0.6–0.72rem → --text-2xs`, `0.75–0.9rem → --text-xs/sm`, `1.1–1.25rem → --text-lg`, `1.4–1.5rem → --text-xl`, `2rem → --text-2xl`. SVG-Achsenlabels (`10px/11px`) dürfen als dokumentierte Ausnahme px behalten (Chart-Präzision), Rest nicht.
3. Sheet-Titel vereinheitlichen (derzeit 5× `1.5rem`, 1× `1.25rem` in `SymptomCooccurrenceDetailSheet.svelte:168`): eine Größe für alle Sheet-Header — erledigt sich großteils über F-05.

**Akzeptanz:** `grep -rnE 'font-size:\s*[0-9.]+rem' apps/web/src --include='*.svelte'` < 10 Rest-Treffer, jeder mit Begründungskommentar; visuelle Prüfung Home/Insights/Trends in beiden Themes.

---

## P2 — Token-Hygiene & Prinzipien

### F-11: Radius-Token-System (GAP-10) nicht durchgezogen

**Evidenz:** Neben `--radius-*` existieren hartkodiert: `999px` (statt `--radius-full`, ~20×), `6px` (Auth-Boxen, `EntryForm.svelte:1181`, `DayDeltaCard.svelte:113`, `SymptomChecker.svelte:479`), `0.45rem` (5×), `0.5rem`, `0.55rem` (`MetricCard.svelte:33`), `0.6rem` (`HomeRecentEntries.svelte:255`, `HomeInsight.svelte:141`), `8px`, `16px` (`routes/auth/+layout.svelte:104`), `2px` (Heatmap-Zellen, `PasswordStrength.svelte:42`).
**Maßnahme:** Mapping: `999px/50% (Pills) → --radius-full`; `6px/0.45rem/0.5rem → --radius-md`; `0.55/0.6rem → --radius-md` (bewusste Vereinheitlichung); `8px → --radius-md`; `16px → --radius-xl`; `2px → --radius-sm` oder als `--radius-2xs`-Mikro-Token, falls optisch nötig.
**Akzeptanz:** `grep -rnE 'border-radius:\s*[0-9]' apps/web/src --include='*.svelte'` ≤ 5 begründete Rest-Treffer.

### F-12: Transition-Wildwuchs

**Evidenz:** Token `--transition-interactive` (180ms) existiert, aber hartkodiert im Code: `120ms ease` (11×), `180ms ease` (8×), `140ms`, `220ms cubic`, `320ms cubic`, `80ms`, `200ms` u. a.
**Maßnahme:** Zwei weitere Tokens: `--transition-fast` (120ms ease) und `--transition-sheet` (220–320ms, für Sheet-Ein-/Ausfahren, respektiert `prefers-reduced-motion` via bestehendem Global-Override). Alle Literale mappen.
**Akzeptanz:** Keine `ms`-Literale in Svelte-`transition:`-Deklarationen außer in Keyframe-Animationen mit Kommentar.

### F-13: Undefinierte, tote und redundante Farb-Tokens

**Evidenz:**

- **Benutzt aber undefiniert** (funktioniert nur via Fallback): `--color-mood-primary` (`SymptomTrendOverlay.svelte:219/223/264`), `--color-surface-muted` (4 Dateien, Fallback `--color-strip-track-bg`), `--color-surface-inverse` (F-06), `--app-header-height` (`InsightsAnalysisToolbar.svelte:79`, `TrendsAnalysisToolbar.svelte:58`), `--text-2xl` (F-10).
- **Definiert aber unbenutzt:** `--color-muted` (0×; Verwechslungsgefahr mit `--color-text-muted`, 153×), `--color-gold` (0×; Duplikat von `--color-warning`).
- **Redundantes Alias:** `--color-primary-soft` = `var(--color-primary-highlight)`; beide werden parallel benutzt (5× vs. 12×).

**Maßnahme:** Undefinierte Verweise durch die real gemeinten Tokens ersetzen (`--color-mood-primary → --color-metric-mood`; `--color-surface-muted → --color-strip-track-bg`); `--app-header-height` entweder in `app.css` definieren (sofern sticky Toolbars unter einem künftigen Header sitzen sollen) oder die `calc()`-Ausdrücke auf `var(--space-2)` vereinfachen. Tote Tokens `--color-muted`, `--color-gold` löschen. Alias auflösen: überall `--color-primary-highlight`, `--color-primary-soft` entfernen.
**Akzeptanz:** Skript-Check „jedes `var(--x)` in Svelte-Dateien ist in `app.css` definiert oder komponentenlokal gesetzt" läuft ohne Treffer (siehe F-21).

### F-14: Symptom-Kalender verletzt Heatmap-Farbprinzip (§1.5)

**Evidenz:** `docs/FRONTEND.md` §1.5: Kalender-/Frequenz-Heatmaps nutzen die neutrale `--color-heatmap-*`-Skala, nie Verdikt-Farben. `SymptomCalendarHeatmap.svelte:185, :199` färbt „Symptom vorhanden"-Zellen mit `--color-warning` (Amber = Warn-Verdikt). `ComparisonHeatmap` und `TagHeatmap` nutzen korrekt `--color-heatmap-*`.
**Maßnahme:** Present-Zellen auf `--color-heatmap-3/4` umstellen (Intensität statt Warnung); Legende mitziehen. Falls Amber eine bewusste Produktentscheidung ist (Symptom ≠ Frequenz), Ausnahme in `FRONTEND.md` §1.5 + `SYMPTOM_VISUALIZATION.md` dokumentieren — Entscheidung nicht implizit lassen.
**Akzeptanz:** Entweder Token-Umstellung oder dokumentierte Ausnahme; Dark/Light geprüft.

### F-15: Legacy-Skeleton-Statusklassen (27 Vorkommen)

**Evidenz:** `text-success-500`, `text-warning-500`, `text-error-500`, `bg-*-500`, `text-surface-600-300-token` — als Shims in `app.css:654–680` definiert, in 20 Dateien benutzt. Das ist eine zweite, parallele Semantik-Ebene neben den Tokens.
**Maßnahme:** Vorkommen auf semantische Klassen/Inline-Token umstellen (`color: var(--color-success)` bzw. Utility `.text-success` benennen ohne Skeleton-`-500`-Suffix); danach Shims aus `app.css` löschen.
**Akzeptanz:** `grep -rn '\-500\b\|600-300-token' apps/web/src --include='*.svelte'` = 0; Shims entfernt.

### F-16: Icon-Größen ignorieren die Icon-Tokens (ISP-9)

**Evidenz:** `--icon-sm` (14px-Cluster) und `--icon-md` (18px-Cluster) sind definiert (app.css:21–22). lucide-Verwendungen: `size={18}` 9×, `size={14}` 7×, `size={16}` 2×, `size={20}`, `size={22}` je 1× — Zahlenliterale statt Token-Bezug; `16/20/22` liegen außerhalb der Cluster.
**Maßnahme:** Icon-Rendering über `IconRender`/`IconButton` kanalisieren; dort `size`-Prop als `'sm' | 'md'` typisieren und auf px-Werte der Tokens mappen (14/18). `16 → 14` oder `18`, `20/22 → 18` vereinheitlichen (Ausnahme: illustrative Icons `40/72` auf Landing/Empty-States bleiben).
**Akzeptanz:** Direkte `size={N}`-Literale nur noch in `IconRender`/dokumentierten Illustrationen.

### F-17: Doku-Drift `FRONTEND.md` §4.2 — Mood-Farbskala existiert nicht im Code

**Evidenz:** §4.2 spezifiziert Mood-Scores `-2…+2` mit Rot-Grün-Ampelskala (`#ef4444 … #22c55e`). Implementiert ist eine `1–5`-Skala (`lib/config/metrics.ts`, `ENTRY_CONTRACT`) mit Metrik-Farben `--color-metric-*` (violett/grün/rot als Linienfarben, nicht als Score-Ampel). Keiner der §4.2-Hexwerte kommt im Frontend-Code vor. Ampelfarben würden zudem §1.5 (kein Verdikt-Farbschema) widersprechen.
**Maßnahme:** Reine Doku-Korrektur: §4.2 auf den realen Stand umschreiben (1–5-Skala, `--color-metric-*`, Verweis auf `metrics.ts` als Source of Truth). Keine Code-Änderung.
**Akzeptanz:** `FRONTEND.md` §4.2 entspricht `metrics.ts`/`ENTRY_CONTRACT`.

### F-18: Vier-Zustände-Kontrakt (§1.7) nur punktuell über `DataState`

**Evidenz:** `DataState.svelte` existiert als Primitive, wird aber außerhalb `common/` nur in 2 Dateien verwendet. Viele Screens bauen Loading/Error/Empty/Offline manuell (Skeleton-Markup in `InsightCard`, `HomeRecentEntries` etc.).
**Maßnahme (Audit-Task):** Pro Primär-Screen prüfen, ob alle vier Zustände existieren und visuell konsistent sind; wo manuell gebaut, auf `DataState`/`EmptyState`/`InlineAlert` umstellen, sofern kein dokumentierter Sondergrund (komponentenspezifische Skeletons sind ok, sollten aber die gleichen Shimmer-/Farb-Tokens nutzen).
**Akzeptanz:** Matrix Screen × Zustand in `UI_COMPONENT_SYSTEM.md` ergänzt; keine „blank div"-Zustände.

---

## P3 — Aufräumen & Guardrails

### F-19: Tote Dependencies

**Evidenz:** `@skeletonlabs/skeleton@^2.10.0` und `@skeletonlabs/tw-plugin@^0.4.0` in `apps/web/package.json:28–29`, nirgends importiert/konfiguriert.
**Maßnahme:** Nach Abschluss von F-01/F-15 entfernen; `pnpm-lock.yaml` aktualisieren.
**Akzeptanz:** Build + Tests grün ohne die Pakete.

### F-20: Einheiten-Mix bei Touch-Target-Höhen

**Evidenz:** `min-height: 44px` (34×) vs. `min-height: 2.75rem` (7×) — gleicher Wert, zwei Schreibweisen.
**Maßnahme:** Token `--tap-target: 44px` in `app.css`, alle Vorkommen darauf umstellen.
**Akzeptanz:** Einheitliche Nutzung; grep auf `min-height: 44px\|2.75rem` = 0 außerhalb `app.css`.

### F-21: Guardrails gegen Rückfall (CI)

**Maßnahme:** Kleines Check-Skript `apps/web/scripts/check-style-tokens.mjs` (Aufruf in `ci-web.yml` neben `check:contrast`), das in `*.svelte` failt bei:

1. Hex-Farbliteralen (`#[0-9a-f]{3,8}`) außerhalb einer Allowlist,
2. `var(--…)`-Verweisen ohne Definition in `app.css` (komponentenlokal via `style=`-Attribut gesetzte Custom Properties per Allowlist: `--bar-*`, `--tag-*`, `--metric-*`, `--day-count`, `--habit-progress`, `--axis-*`, `--*-chart-width`, `--insight-accent` [von `InsightCard.svelte` gesetzt, siehe `INSIGHT_STATEMENT_PATTERN_SPRINT_PLAN.md` Sprint 3/ISP-5]),
3. neuen `@media`-Breakpoints außerhalb des kanonischen Sets (F-04),
4. `font-size`/`border-radius`-Zahlenliteralen ohne `/* token-exempt: <Grund> */`-Kommentar.

**Akzeptanz:** CI-Job rot bei Verstoß; bestehender Code nach Abschluss von F-10/F-11 grün.

---

## Empfohlene Umsetzungsreihenfolge (Work Packages)

| WP                             | Inhalt                                                                           | Findings                                     | Aufwand |
| ------------------------------ | -------------------------------------------------------------------------------- | -------------------------------------------- | ------- |
| WP-1 „Broken Styles"           | Primary-Buttons, Success-Token, Warning-Shim-Bug, Tag-Default                    | F-01, F-02, F-03                             | S       |
| WP-2 „Token-Vervollständigung" | Scrim, text-2xs/2xl, transition-fast/sheet, tap-target, tote/undefinierte Tokens | F-06, F-13, F-20 + Token-Teile aus F-10/F-12 | S       |
| WP-3 „Primitives"              | BottomSheet extrahieren + Sheet-Migration, ScreenHeader-Lücken                   | F-05, F-07                                   | M       |
| WP-4 „Sweep-Migrationen"       | font-size-, radius-, transition-, icon-, Legacy-Klassen-Sweeps                   | F-10, F-11, F-12, F-15, F-16                 | M       |
| WP-5 „Mobile/Web-Härtung"      | Breakpoint-Konsolidierung, Touch-Targets, Theme-Bootstrap                        | F-04, F-08, F-09                             | M       |
| WP-6 „Prinzipien & Doku"       | Heatmap-Farbe, §4.2-Drift, DataState-Audit, Dep-Cleanup, CI-Guardrail            | F-14, F-17, F-18, F-19, F-21                 | S–M     |

Abhängigkeiten: WP-2 vor WP-3/WP-4 (Tokens müssen existieren, bevor migriert wird); F-19 nach F-01+F-15; F-21 als letztes (sonst rot auf Altbestand).

## Verifikation nach jedem WP

```bash
cd apps/web
pnpm lint && pnpm format:check && pnpm typecheck
pnpm test                 # 97 Dateien / 473 Tests Basis-Stand
pnpm check:contrast       # ADR-0027-Paare
pnpm build
pnpm test:e2e:smoke       # bei UI-Verhalten zusätzlich test:e2e:mobile
```

Manuelle Sichtprüfung: Baseline-Viewports aus `surfaceContract.ts` (390/430/768/1280/1440), jeweils Dark **und** Light.

---

## Positiv-Befunde (nicht anfassen)

- Token-Architektur in `app.css` ist solide: 3-stufige Text-Hierarchie, Metrik-/Heatmap-/Divergent-Tokens je Theme, `color-mix`-basierte abgeleitete Farben.
- Shell-Split 768 px (Bottom-Nav ↔ Side-Rail) ist konsistent implementiert und getestet.
- `prefers-reduced-motion`-Global-Override, `:focus-visible`-Standard, Safe-Area-Handling im `page-shell` sind vorbildlich.
- Kaum Hex-Literale in Komponenten (nur F-03) — die Disziplin ist da, es fehlen Vollständigkeit der Tokens und Guardrails.

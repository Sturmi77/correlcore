# [FEATURE] Habit visualization: distinct build vs reduce encoding (Strahl)

> Ready-to-paste GitHub issue body (feature_request template).
> Labels: `enhancement`
> Milestone: Backlog / Trends Habits (W7)

---

## Feature-Beschreibung

Habits so darstellen, dass sofort klar ist, ob ein Habit **aufgebaut** (`build`) oder **reduziert** (`reduce`) werden soll. Den Fortschritts-„Strahl“/Meter typ-spezifisch encodieren.

## Problem / Motivation

[`HabitsPanel`](../../apps/web/src/lib/components/trends/HabitsPanel.svelte) / [`HabitDetailBody`](../../apps/web/src/lib/components/trends/HabitDetailBody.svelte) nutzen denselben Primary-Balken; der Typ erscheint nur als gedämpfter Text. Hoher %-Fill liest sich bei Reduce falsch („mehr = besser“). Es gibt kein radiales Strahl-Widget — Nutzer-„Strahl“ meint den Fortschrittsmeter.

Produktvokabular bleibt `reduce` (nicht „avoid“); keine Rot/Grün-Gamification ([COLOR_SCHEME_CONCEPT](../../docs/frontend/COLOR_SCHEME_CONCEPT.md)).

## Vorgeschlagene Lösung

1. **Typ-aware Meter (MVP):** Build = Füllung L→R (Fortschritt zur Zielhäufigkeit); Reduce = Restkapazität / invertiertes oder hohles Fill (unter Max = „im Rahmen“). Optionales `+`/`−`-Glyph; bestehende Trend-Icons wiederverwenden.
2. **Listenstruktur:** Abschnitte oder Chips „Building“ / „Reducing“.
3. **Strahl (Phase 2, wenn MVP nicht reicht):** net-new SVG — Speichen = Habits, Länge = Adherence; **auswärts = build**, **einwärts/hohl = reduce**; Daten aus [`habitMetrics.ts`](../../apps/web/src/lib/utils/habitMetrics.ts).
4. Insights-Matrix-Habits-Layer optional mit denselben Badges.

### Umsetzungsplan

Meter-Encoding in Panel+Detail → List grouping → i18n → Visual QA; bei Bedarf Phase-2-Strahl als Follow-up-Issue.

## Alternativen

- Nur Copy/Typography — zu schwach für das Finding.
- Rot/Grün zur Typ-Unterscheidung — gegen Design-Regeln.

## Milestone

Backlog / Trends Habits (W7)

## Datenschutz-Impact

Rein präsentational; keine neuen Health-Felder.

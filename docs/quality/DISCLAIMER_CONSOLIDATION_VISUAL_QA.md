# Disclaimer Consolidation — Visual QA & #632 Closeout

Last updated: 2026-08-03 · Milestone: #632 Phase 2 Sprint 3

Closeout for **#632** ("Hinweistexte inventarisieren und Korrelations-Disclaimer
entflechten"). Records the visual QA of the changed surfaces and the final
acceptance mapping. Plan: [`DISCLAIMER_CONSOLIDATION_PHASE2_SPRINT_PLAN.md`](../DISCLAIMER_CONSOLIDATION_PHASE2_SPRINT_PLAN.md).

## QA method

The Browser pane could not composite screenshots in this environment, so visual
QA was done via the DOM / computed styles rather than image capture, at both
breakpoints and both themes:

- **Horizontal overflow:** `documentElement.scrollWidth − clientWidth` (must be 0).
- **Hint presence / count:** `data-testid` queries (guard against duplicate hints).
- **Reachability:** the ⓘ / link resolves to the canonical explanation.
- **Theme + legibility:** `data-theme` + computed `color` on hint text and link.
- **Console:** errors-only, must be empty.

Breakpoints: **375 px** (mobile) and **768 px** (tablet). Themes: **light** + **dark**.

## Results

| Surface                              | 375 light | 375 dark | 768 light | 768 dark | Notes                                                                                                                              |
| ------------------------------------ | --------- | -------- | --------- | -------- | ---------------------------------------------------------------------------------------------------------------------------------- |
| `/insights` (feed / mobile lead)     | ✅        | ✅       | ✅        | ✅       | overflow 0; ⓘ present (mobile-lead pattern keeps its ⓘ; the desktop feed-header hint renders when `showContext=true`)              |
| `/insights/digest` (CorrelationHint) | ✅        | ✅       | ✅        | ✅       | overflow 0; **exactly one** `correlation-hint`; link → `/insights/disclaimer`; text/link legible in dark; hint text fits (no clip) |
| Console (all pages)                  | ✅        | ✅       | ✅        | ✅       | no errors                                                                                                                          |

**Component-tested only — visual QA still PENDING:**

- **Home daily brief** `CorrelationHint` (shown with the lead statement) — **not rendered visually** at any viewport/theme: the mock/dev environment stays in the collecting phase, so `latestInsight` is null and the hint does not appear. DOM/link behaviour is covered by `CorrelationHint.test.ts` + Home component tests, and it reuses the **same component visually verified on `/insights/digest`** (no overflow/clip, legible in dark) — but the Home-with-insight layout has **not** been manually checked. Tracked as the open item below.
- **Onboarding** footer de-dup (concepts / cycle_step removed, maturity_intro kept) — covered by the onboarding component tests + `localeCompleteness`.

## #632 acceptance mapping (final)

- [x] Inventar der Hinweistexte inkl. i18n-Keys + Komponenten — Issue-Kommentar.
- [x] Konzeptentscheid — persistenter Stage-Header/Hint + on-demand ⓘ (kein First-run-Banner).
- [x] Sichtbare Mehrfach-Hinweise reduziert — per-Statement-Tails raus (#639); Onboarding-Footer 3→1 (#643).
- [x] Kanonische Erklärung ≤2 Klicks von jeder Fläche — ⓘ (Feed/Mobile-Lead) + `CorrelationHint`-Link auf Home/Digest (≤1 Klick) (#644).
- [x] Keine Regression Footer/Legal — Auth-Medical entfernt, Impressum/Privacy/FAQ unverändert (#639).
- [~] Light/Dark, Mobile+Desktop geprüft — `/insights` + `/insights/digest` verifiziert (dieses Dokument). **Offen:** Home-`CorrelationHint` mit Insight (Mock/Dev in Collecting-Phase nicht renderbar) — muss auf einem Gerät mit Daten visuell geprüft werden.

## Deliberately kept / not changed

- Rechtliche Pflicht-Disclaimer (Footer/Impressum/Privacy/FAQ) — persistent.
- Cycle-Medizinhinweis am Cycle-Onboarding-Schritt + am Eintrags-Eingabepunkt (Art. 9).
- `/insights/history` Timeline-Hinweis (kontextuell) + Zurück-Link (≤2 Klicks) — kein zusätzlicher `CorrelationHint`, um keine neue Dublette zu erzeugen.
- Symptom-Kalender-Note — navigational, kein Safety-Hedge.

## Merge order

#639 (Kern, gemergt) → #642 (Docs) → #643 (Phase-2 S1) → #644 (Phase-2 S2, enthält diesen Closeout).

**#632 bleibt bewusst offen**, bis die verbleibende Home-`CorrelationHint`-Visual-QA
(mit Insight, 375/768 px, hell/dunkel) auf einem Gerät mit Daten nachgeholt ist.
Deshalb trägt die abschließende PR **kein `Closes #632`** — der Issue wird erst
geschlossen, wenn dieser letzte QA-Punkt erledigt ist.

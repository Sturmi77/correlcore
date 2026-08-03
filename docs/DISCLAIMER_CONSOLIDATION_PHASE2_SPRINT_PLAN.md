# Disclaimer Consolidation — Phase 2 Sprint Plan (#632)

Last updated: 2026-08-03

Follow-up plan for GitHub **#632** ("Hinweistexte inventarisieren und
Korrelations-Disclaimer-Konzept entflechten"). Inventory + concept +
insight-surface core shipped in **PR #639**; this plan covers the remaining
surfaces, the optional first-run banner, and the closing QA.

## Context — what already shipped (#639)

- Per-statement Safety-Tails aus allen 11 `insight_engine.py` Statement-Buildern entfernt → Statements rein deskriptiv.
- **Ein** Feed-Header-Hinweis (`insights.feed.correlation_header`) statt pro-Karte-Wiederholung; kanonische Erklärung via ⓘ → `CorrelationDisclaimer` in ≤2 Klicks.
- Redundanten `disclaimer.medical` im Auth-Layout entfernt; ungenutzte `insights.mobile.correlation_note`/`_link` aufgeräumt; Doc-Beispiel-Statements aktualisiert.

Bewusst offen geblieben (→ dieser Plan): die **Nicht-Insight-Flächen** (Onboarding/Digest/Cycle), der optionale First-run-Banner, und die Cross-Surface-Erreichbarkeits-/Visual-QA.

## Zielbild (Erinnerung)

Zwei getrennte Jobs: **Legal/Pflicht** (persistent, selten, Footer/Legal/Marketing) vs. **Insight-UX-Korrelationshinweis** (einmalig/on-demand, ein kanonischer Ort + ⓘ). Safety-Copy bleibt in ≤2 Klicks erreichbar, nicht redundant sichtbar.

## Sprint 1 — Onboarding / Digest / Cycle konsolidieren

**Ziel:** die „not a diagnosis / no medical advice"-Wiederholungen außerhalb der Insights entflechten.

**Deliverables:**

- **Onboarding:** `ConceptExplainer`, `MaturityExpectationContent`, `CycleFunctionExplainer` — die footer-/disclaimer-Copy (`onboarding.*.footer`, en:1334/1345/1378) auf **eine** Stelle reduzieren; wo die Erklärung schon anderweitig erreichbar ist, den Wiederholungssatz streichen.
- **Cycle:** den „no prediction, no medical advice"-Hinweis am **Cycle-Eingabepunkt einmal** behalten (Art.-9-sensibel), Dubletten in Onboarding/Digest entfernen.
- **Digest (Web + E-Mail):** prüfen, ob der Wochendigest denselben Disclaimer wiederholt; auf einen Hinweis + Link zur kanonischen Erklärung reduzieren. **Wichtig:** E-Mail-Digest muss die Safety-Copy weiter enthalten/erreichbar halten (kein In-App-ⓘ vorhanden).
- i18n DE/EN synchron; `localeCompleteness` grün.

**Tests/QA:** Onboarding-Component-Tests; Digest-Snapshot; Copy-Lint (`noGamificationCopy`).

## Sprint 2 — Reachability-Audit + optionaler First-run-Banner

**Ziel:** sicherstellen, dass **jede** Insight-Fläche die kanonische Erklärung in ≤2 Klicks erreichbar hält; Produktentscheid First-run vs. persistent.

**Deliverables:**

- **Reachability-Audit:** Home Daily Brief, Mobile-Lead, Trends-Cross-Links, Digest — überall ein ⓘ/Link zur `CorrelationDisclaimer`. Lücken schließen (kein Statement-Surface ohne erreichbaren Hinweis).
- **First-run-Banner (nur bei Produktentscheid „einmalig statt persistent"):** dismissbarer Banner „Was bedeuten Korrelationen?" mit „Verstanden", **über bestehende `dismissed_insight_keys`** (kein neues Migration/Preference-Feld), Key z. B. `correlation_intro`. Das persistente ⓘ bleibt immer sichtbar. **Default-Empfehlung:** beim persistenten Stage-Header-Hinweis bleiben (immer sichtbar, kein State) — Banner nur, wenn Produkt es ausdrücklich will.
- **Symptom-Kalender:** `calendar_correlation_note` bewerten — navigational, kann bleiben oder auf ⓘ reduziert werden.

**Tests:** Banner-Dismiss-Roundtrip (falls umgesetzt); Reachability als E2E-Smoke (ⓘ öffnet Sheet).

## Sprint 3 — Visual-QA + #632-Closeout

**Deliverables:**

- Visual-QA 375/768 px, hell + dunkel: Insights-Feed-Header, Onboarding, Cycle, Digest.
- Acceptance-Criteria von #632 final abhaken; Issue schließen oder Rest-Scope explizit dokumentieren.
- CHANGELOG-Ergänzung; ggf. kurzer Doc-Verweis im Insight-Copy-Governance-Abschnitt (`INSIGHT_STATEMENT_PATTERN_SPRINT_PLAN.md`).

## Acceptance-Mapping (#632)

- [x] Inventar (Issue-Kommentar)
- [x] Konzeptentscheid (First-run/Stage-Header + on-demand)
- [x] Insight-Flächen: Mehrfach-Hinweise reduziert (#639)
- [ ] Nicht-Insight-Flächen (Onboarding/Digest/Cycle) konsolidiert (**Sprint 1**)
- [ ] Kanonische Erklärung ≤2 Klicks von **jeder** Fläche (**Sprint 2**)
- [ ] Light/Dark, Mobile+Desktop geprüft (**Sprint 3**)
- [x] Keine Regression Footer/Legal (#639)

## Out of scope

- Rechtliche Pflicht-Disclaimer (Footer/Impressum/Privacy/FAQ) — bleiben persistent, kein Umbau.
- Neue Preference-/Migration-Felder — der optionale Banner nutzt `dismissed_insight_keys`.
- Änderung der kanonischen `CorrelationDisclaimer`-Inhalte (nur Erreichbarkeit/Frequenz, nicht der Text).

## Referenzen

- Issue #632 + [Inventar-Kommentar](https://github.com/Sturmi77/correlcore/issues/632#issuecomment-5159778330)
- PR #639 (Phase-1-Umsetzung, gemerged)
- `docs/PHASE_INSIGHT_MATRIX.md` (Statement-Beispiele, §Sprach-Prinzip)
- `docs/INSIGHT_STATEMENT_PATTERN_SPRINT_PLAN.md` (Disclaimer-Governance)

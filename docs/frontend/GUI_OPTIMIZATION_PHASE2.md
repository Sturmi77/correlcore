# CorrelCore — GUI Optimization Phase 2

**Date:** 2026-06-30 (updated 2026-07-01)  
**Predecessor:** O-01–O-20 ([`OPTIMIZATION_BACKLOG.md`](OPTIMIZATION_BACKLOG.md), PR #281, #284)  
**Source audits:** [`FRICTION_AUDIT.md`](FRICTION_AUDIT.md) · [`USER_WORKFLOWS.md`](USER_WORKFLOWS.md)

Phase 1 removed funnel friction, duplicate maturity UI, and legacy paths. Phase 2 targets **information architecture**, **progressive disclosure placement**, **mobile vertical rhythm**, and **remaining friction-audit findings**.

---

## 1. Erledigt (Stand `main`, Juli 2026)

| ID        | PR         | Titel                                                                         |
| --------- | ---------- | ----------------------------------------------------------------------------- |
| O-01–O-20 | #281, #284 | Phase-1-Backlog (Auth, Onboarding, Home, Trends, PWA, Export, Password reset) |
| O-30      | #288       | Spacing Foundation (`screen-stack`, `--space-5`, Mobile-Dichte)               |
| O-21      | #289       | Entry Flatten — Tags/Symptome/Zeitslots immer sichtbar                        |
| O-23      | Sprint H   | Globales `analysisRange` (Trends + Insights, persistiert)                     |
| O-22      | Sprint H   | Insights: eine Kontrollzeile (Kategorie-Chips + Matrix-Link)                  |
| O-24      | Sprint H   | Symptom-Analytik über Kategorie-Filter statt Checkbox                         |
| O-39      | Sprint I   | Home Brief: Einträge bis Meilenstein inline                                   |
| O-40      | Sprint I   | Cross-link Trends ↔ Insights (Top-Finding)                                    |
| O-36      | Sprint J   | Smart Entry-Defaults (Mood/Energie von gestern)                               |
| O-08      | Sprint J   | Desktop Entry-Surface vereinheitlichen (global EntrySheet)                    |
| O-38      | Sprint J   | Trends/Leer-CTA öffnet EntrySheet inline                                      |

---

## 2. Backlog O-22 – O-42 (offen)

Legende Status: **Offen** · **Teilweise** (Foundation da, Audit-Punkt nicht vollständig) · **Erledigt**

### 2.1 Analyse-IA (höchste Priorität)

| ID   | Impact | Effort | Titel                                                                 | Klasse         | Audit-Quelle                                         | Status       |
| ---- | ------ | ------ | --------------------------------------------------------------------- | -------------- | ---------------------------------------------------- | ------------ |
| O-23 | High   | Medium | Globales `analysisRange` für Trends + Insights                        | Zusammenführen | W6 #157, Cross-cutting „Zeiträume“                   | **Erledigt** |
| O-22 | High   | Medium | Insights: eine Kontrollzeile (Chips + Matrix-Link)                    | Zusammenführen | W5 #113, W6 #147, Cross-cutting „Duplicate maturity“ | **Erledigt** |
| O-24 | Medium | Low    | Symptom-Analytik über Kategorie-Filter statt Checkbox                 | Eliminieren    | W6 Insights controls                                 | **Erledigt** |
| O-40 | Medium | Medium | Cross-link Trends ↔ Insights (Top-Finding)                            | Zusammenführen | W6 #146                                              | **Erledigt** |
| O-41 | Medium | High   | Trends Compare + Health auf gemeinsame Zeitachse / Tab-Konsolidierung | Zusammenführen | W6 Desktop #155, FRONTEND_STREAMLINE                 | Erledigt Sprint M |

### 2.2 Entry & Desktop

| ID   | Impact | Effort | Titel                                                             | Klasse         | Audit-Quelle                                   | Status       |
| ---- | ------ | ------ | ----------------------------------------------------------------- | -------------- | ---------------------------------------------- | ------------ |
| O-08 | Medium | High   | Desktop Entry-Surface vereinheitlichen (Sheet vs. `/entries/new`) | Zusammenführen | W3 Desktop #94, W4, Cross-cutting „Dual entry“ | **Erledigt** |
| O-38 | Medium | Low    | Trends/Leer-CTA → EntrySheet inline statt Route-Wechsel           | Umleiten       | W3 Desktop #96                                 | **Erledigt** |
| O-36 | Medium | Medium | Smart Entry-Defaults (Mood/Energie von gestern)                   | Vereinfachen   | W3 #80                                         | **Erledigt** |
| O-25 | Medium | High   | Entry „Schnell“ vs. „Vollständig“ beim Öffnen                     | Umleiten       | Phase-2-Reserve                                | Erledigt Sprint M |
| O-42 | Low    | Low    | Tageszeit-Slots in Datumszeile integrieren                        | Vereinfachen   | Phase-2 §4                                     | Erledigt Sprint M |

### 2.3 Home & erste Erkenntnis

| ID   | Impact | Effort | Titel                                         | Klasse       | Audit-Quelle                               | Status       |
| ---- | ------ | ------ | --------------------------------------------- | ------------ | ------------------------------------------ | ------------ |
| O-39 | Medium | Low    | Home Brief: „Einträge bis Meilenstein“ inline | Vereinfachen | W5 collecting #110                         | **Erledigt** |
| O-13 | Medium | Medium | Home bridge für wöchentliche Analyse          | Umleiten     | W6 summary, Cross-cutting „Analysis split“ | **Erledigt** |

_Erledigt aus W5:_ O-03 (Empty CTA), O-05 (Sparkline-Gate), O-14 (Matrix/Co-occurrence-Gates).

### 2.4 Onboarding (Rest aus W2)

| ID   | Impact | Effort | Titel                                                                        | Klasse                     | Audit-Quelle | Status              |
| ---- | ------ | ------ | ---------------------------------------------------------------------------- | -------------------------- | ------------ | ------------------- |
| O-37 | Medium | Medium | Onboarding straffen: Intro in ersten Entry; Summary bei ≤3 Tags überspringen | Vorverlagern / Eliminieren | W2 #52, #57  | **Erledigt**        |
| —    | —      | —      | Legacy `/onboarding/retro` + `/profile`                                      | Eliminieren                | W2 legacy    | **Erledigt** (O-04) |

### 2.5 Habits, Settings, Vertrauen

| ID   | Impact | Effort | Titel                                         | Klasse         | Audit-Quelle                         | Status       |
| ---- | ------ | ------ | --------------------------------------------- | -------------- | ------------------------------------ | ------------ |
| O-09 | Medium | Medium | Habit-Hinweis im Onboarding-Tag-Schritt       | Vorverlagern   | W7 #169, Cross-cutting „Habit setup“ | **Erledigt** |
| O-16 | Medium | Medium | Inline Habit-Setup bei leerem Habits-Panel    | Umleiten       | W7 #172                              | **Erledigt** |
| O-27 | Low    | Medium | Settings-Vokabular-Hub (Tags/Symptome/Habits) | Zusammenführen | W8                                   | Erledigt Sprint M |
| O-28 | Medium | High   | Account-Löschung (M9)                         | Vereinfachen   | DSGVO / Vertrauen                    | Erledigt Sprint M |

_Erledigt aus W1:_ O-07 (Verify auto-login), O-11 (Mail deep link), O-20 (Password reset).

### 2.6 Trends Mobile & Spacing

| ID   | Impact | Effort | Titel                                                     | Klasse       | Audit-Quelle           | Status |
| ---- | ------ | ------ | --------------------------------------------------------- | ------------ | ---------------------- | ------ |
| O-26 | Medium | Low    | Trends Mobile: Detail-Toggle vs. Scroll                   | Vereinfachen | Analog O-21            | Erledigt Sprint L |
| O-29 | Low    | Low    | Compare-Filter nur bei geöffnetem Mobile-Detail           | Vereinfachen | Trends control density | Erledigt Sprint L |
| O-31 | Low    | Low    | Settings-Unterrouten auf `screen-stack`                   | Vereinfachen | Spacing-Audit          | Erledigt Sprint L |
| O-32 | Low    | Low    | Heatmap-Mikro-Gaps auf Tokens                             | Vereinfachen | Spacing-Audit          | Erledigt Sprint L |
| O-33 | Low    | Low    | `ScreenHeader` → erster Block: `--screen-header-gap`      | Vereinfachen | Spacing-Audit          | Erledigt Sprint L |
| O-34 | Medium | Low    | InsightStageHeader / MobileInsightLead kompakter (Mobile) | Vereinfachen | W5/W6 + Spacing        | Erledigt Sprint L |
| O-35 | Low    | Low    | Contract-Test: kein Route-Root-Padding in `page-shell`    | Vereinfachen | Spacing-Audit          | Erledigt Sprint L |

---

## 3. Friction Audit — Abdeckungsmatrix

Vollständige Schritt-Inventare: [`FRICTION_AUDIT.md`](FRICTION_AUDIT.md).  
Unten nur **noch offene oder teilweise offene** Audit-Punkte mit Ticket-Zuordnung.

| Workflow | Audit-Punkt                     | Ticket | Priorität           |
| -------- | ------------------------------- | ------ | ------------------- |
| **W1**   | Post-verify Login-Schritt       | —      | **Erledigt** (O-07) |
| **W1**   | Kein Password-Reset             | —      | **Erledigt** (O-20) |
| **W1**   | Check-email Mail-App-Link       | —      | **Erledigt** (O-11) |
| **W2**   | Intro-Panel vor erstem Entry    | —      | **Erledigt** (O-37) |
| **W2**   | Summary bei wenigen Tags        | —      | **Erledigt** (O-37) |
| **W2**   | Post-onboarding leerer Brief    | —      | **Erledigt** (O-02) |
| **W2**   | Legacy retro/profile            | —      | **Erledigt** (O-04) |
| **W3**   | Smart default von gestern       | —      | **Erledigt** (O-36) |
| **W3**   | Dual Entry Desktop              | —      | **Erledigt** (O-08) |
| **W3**   | Entry-Page Chrome (Theme/Nav)   | —      | **Erledigt** (O-08) |
| **W3**   | Trends CTA → Route statt Sheet  | —      | **Erledigt** (O-38) |
| **W3**   | Tags/Symptome hinter Toggle     | —      | **Erledigt** (O-21) |
| **W4**   | Rückdatierung Sheet vs. Page    | —      | **Erledigt** (O-08) |
| **W5**   | Meilenstein inline im Brief     | —      | **Erledigt** (O-39) |
| **W5**   | Duplicate maturity UI           | O-34   | Medium              |
| **W5**   | Matrix/Co-occurrence leer       | —      | **Erledigt** (O-14) |
| **W6**   | Matrix als eigener Tab          | —      | **Erledigt** (O-22) |
| **W6**   | Range pro Widget                | O-23   | High                |
| **W6**   | Trends ↔ Insights getrennt      | O-41   | Medium              |
| **W6**   | Compare + Health Tabs           | O-41   | Medium              |
| **W6**   | Heatmap → Route statt Sheet     | —      | **Erledigt** (O-17) |
| **W7**   | Habit-Setup nicht in Onboarding | —      | **Erledigt** (O-09) |
| **W7**   | Leeres Habits-Panel             | —      | **Erledigt** (O-16) |
| **W8**   | Vokabular-Subnavigation         | O-27   | Low                 |
| **W9**   | Export in Settings versteckt    | —      | **Erledigt** (O-19) |
| **W10**  | PWA-Banner vor erstem Entry     | —      | **Erledigt** (O-18) |

### Cross-cutting themes (aktualisiert)

| Theme                           | Status        | Offene Tickets     |
| ------------------------------- | ------------- | ------------------ |
| Auth-Funnel-Länge               | **Erledigt**  | —                  |
| Onboarding vor erstem Entry     | **Erledigt**  | —                  |
| Dual Entry Surfaces             | **Erledigt**  | —                  |
| Duplicate maturity UI           | **Teilweise** | O-34               |
| Legacy Onboarding               | **Erledigt**  | —                  |
| Analyse auf 2 Nav-Tabs verteilt | **Teilweise** | O-41               |
| Habit-Setup nicht in Onboarding | **Erledigt**  | —                  |
| Kein Password-Reset             | **Erledigt**  | —                  |
| Spacing / Dichte Mobile         | **Teilweise** | O-30 ✅, O-31–O-35 |

---

## 4. Empfohlene Sprint-Reihenfolge

| Sprint                      | Issues                       | Ziel                                     |
| --------------------------- | ---------------------------- | ---------------------------------------- |
| **H — Analyse-Kern**        | O-23, O-22, O-24 ✅          | Ein Zeitfenster; Insights findings-first |
| **I — Home & Verknüpfung**  | O-39, O-40, O-13 ✅          | Wöchentliche Review ohne Tab-Hopping     |
| **J — Entry & Desktop**     | O-36, O-08, O-38 ✅          | W3/W4 Rest; Desktop-Konsistenz           |
| **K — Onboarding & Habits** | O-37, O-09 ✅                | W2/W7 Rest                               |
| **L — Spacing & Polish**    | O-31–O-35, O-26, O-29, O-34  | Mobile-Dichte, Trends/Insights kompakter |
| **M — Strategisch**         | O-41, O-25, O-27, O-28, O-42 ✅ | Größere IA-/Backend-Themen               |

**Nächster konkreter PR:** **Sprint L** (O-31–O-35 Spacing) oder **Sprint M** (O-41).

---

## 5. Spacing (O-30 Foundation)

Siehe §2.6 und [`FRICTION_AUDIT.md`](FRICTION_AUDIT.md) (keine Änderung am technischen Inhalt von O-30).

**Prinzipien:** Horizontal nur `.page-shell`; vertikal `.screen-stack` + `--screen-gap*`.

---

## 6. Erfolgskriterien Phase 2

- Erster sichtbarer Inhalt auf Insights/Trends/Home **≥ 1 Viewport-Block höher** auf 390×844
- Kein Route-Root mit horizontalem Padding innerhalb `page-shell`
- Alle `--space-*` Tokens definiert und verwendet
- Nutzer mit täglichen Symptom-Logs: **0 Extra-Taps** für Symptom-Erfassung ✅ (O-21)
- **Jeder offene Friction-Audit-Punkt** ist einem O-Ticket zugeordnet (§3)

---

## 7. Governance (unverändert)

- Kein 6. Nav-Tab (ADR-0017)
- Keine Gamification
- Insight-Phasenmodell inhaltlich unverändert (ADR-0021)
- ADR vor: O-41 (Trends-Tabs), O-28 (Account deletion)

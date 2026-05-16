# Insight Maturity — Frontend Specification

> **Status:** Accepted · **ADR:** [0021](../adr/0021-insight-maturity-phases.md) · **Last updated:** 2026-05-16

This document is the single source of truth for how insight maturity phases are displayed, communicated,
and enforced across all frontend surfaces in CorrelCore.

---

## 1. Phase Definitions

| Phase Key        | Entries | Badge Label     | Color Token          | Icon            |
| ---------------- | ------- | --------------- | -------------------- | --------------- |
| `collecting`     | 1–6     | Collecting Data | `--color-text-muted` | `loader-circle` |
| `early_patterns` | 7–13    | First Patterns  | `--color-gold`       | `sparkles`      |
| `provisional`    | 14–29   | Provisional     | `--color-warning`    | `flask-conical` |
| `robust`         | 30+     | Robust Insights | `--color-success`    | `shield-check`  |

---

## 2. Components

### 2.1 `InsightJourneyBanner`

Displayed at the top of the **Insights page** and as a collapsible card on the **Dashboard**.

**Structure:**

```
┌────────────────────────────────────────────────────┐
│  [Phase Icon]  Phase 2 of 4: First Patterns         │
│  ──────────────────────────────── (progress bar)   │
│  9 entries tracked · 5 more until Provisional       │
│  [?] How do insights work?               [collapse] │
└────────────────────────────────────────────────────┘
```

**Props:**

```typescript
interface InsightJourneyBannerProps {
  phase: 'collecting' | 'early_patterns' | 'provisional' | 'robust';
  phaseIndex: number; // 1–4
  currentEntries: number;
  nextPhaseAt: number | null; // null when robust
  nextPhaseLabel: string | null;
}
```

**Behaviour:**

- Progress bar fills proportionally within the current phase range.
- In `robust` phase: shows a completed state with a celebration micro-animation (confetti, once only).
- The `[?]` button opens an inline explainer Bottom Sheet: `InsightJourneyExplainer`.
- Collapsible on Dashboard; always expanded on Insights page.

---

### 2.2 `InsightMaturityBadge`

Replaces the raw confidence score in all insight cards. Combines phase + statistical confidence.

**Variants by phase:**

| Phase            | Badge text example             | Tooltip                                                    |
| ---------------- | ------------------------------ | ---------------------------------------------------------- |
| `collecting`     | — (no insight cards shown yet) | —                                                          |
| `early_patterns` | "First hint · 7 entries"       | "Based on limited data — patterns may change."             |
| `provisional`    | "Provisional · 21 entries"     | "Early correlation detected. Needs more data to confirm."  |
| `robust`         | "Confirmed · 45 entries"       | "Stable correlation based on sufficient tracking history." |

**Rules:**

- Never show a raw p-value or numeric confidence score to the user.
- Badge is always accompanied by a plain-language tooltip.
- In `early_patterns` and `provisional`: show a subtle warning icon next to the badge.

---

### 2.3 `InsightJourneyExplainer`

A Bottom Sheet / Modal explaining the maturity model in plain language.

**Content structure:**

```
How insights are built

CorrelCore finds patterns in your data over time.
The more you track, the more reliable the insights become.

  ① Collecting Data (Days 1–6)
     We're building your foundation. No patterns yet.

  ② First Patterns (Days 7–13)
     Early signals visible. Treat as hints, not conclusions.

  ③ Provisional Insights (Days 14–29)
     Correlations emerging. More data will confirm or revise them.

  ④ Robust Insights (Day 30+)
     Stable patterns. Insights are now reliable enough to act on.

[Close]
```

---

### 2.4 Phase Milestone Notification

Triggered when the user enters a new phase. This is NOT a toast — it is a **dedicated card** that appears
at the top of the Dashboard and Insights page on the user's next visit after the phase transition.

**Example (entering `early_patterns`):**

```
🔍 New: First Patterns unlocked!
You've tracked 7 days. Trend charts and early signals are now available.
[Explore Insights →]
```

**Rules:**

- Shown maximum once per phase transition.
- Dismissed on explicit user action (tap/click), not auto-dismissed.
- Stored in user preferences via API (`milestone_notifications_seen[]`).

---

## 3. Affected UI Elements — Full Map

Every element listed here MUST be aware of the current maturity phase and adapt its content or visibility.

| Element                    | Location                    | Adaptation                                                   |
| -------------------------- | --------------------------- | ------------------------------------------------------------ |
| `InsightJourneyBanner`     | Insights page, Dashboard    | Always visible; shows phase progress                         |
| `InsightMaturityBadge`     | All insight cards           | Phase-appropriate label + tooltip                            |
| Insight card headline      | Insights page               | Tone: cautious in early phases, confident in robust          |
| Insight card CTA           | Insights page               | Hidden in `collecting`; contextual in later phases           |
| Chart annotations          | All charts with correlation | Uncertainty ribbon shown in `early_patterns` + `provisional` |
| Dashboard summary module   | Dashboard                   | Only renders correlations in `provisional`+                  |
| Weekly Reflection          | Dashboard / Insights        | Distinguishes observation vs. pattern vs. correlation        |
| Empty state (Insights)     | Insights page               | Phase-aware: explains what's missing and why                 |
| Locked state               | Insights sub-sections       | Shows phase gate reason, not a generic lock icon             |
| Phase Milestone Card       | Dashboard, Insights         | One-time card on phase transition                            |
| Notification (push/in-app) | System                      | Milestone alert on phase transition                          |
| API response               | All `/insights/*` endpoints | `insight_maturity` object required (see ADR-0021)            |

---

## 4. Copy Guidelines

### Tone per phase

| Phase            | Tone              | Avoid                         | Use instead                                        |
| ---------------- | ----------------- | ----------------------------- | -------------------------------------------------- |
| `collecting`     | Encouraging       | "No data yet"                 | "We're building your foundation."                  |
| `early_patterns` | Curious, cautious | "Strong pattern found"        | "First hints are emerging."                        |
| `provisional`    | Informative       | "This is a confirmed insight" | "Early correlation — more data will clarify this." |
| `robust`         | Confident         | "You must..." (prescriptive)  | "Your data shows a consistent pattern."            |

### Translation keys (`i18n`)

```
maturity.collecting.label
maturity.collecting.description
maturity.collecting.hint
maturity.early_patterns.label
maturity.early_patterns.description
maturity.early_patterns.hint
maturity.provisional.label
maturity.provisional.description
maturity.provisional.hint
maturity.robust.label
maturity.robust.description
maturity.robust.hint
maturity.milestone.collecting_to_early_patterns
maturity.milestone.early_patterns_to_provisional
maturity.milestone.provisional_to_robust
```

---

## 5. API Contract (Frontend Perspective)

All insight-related API responses include:

```typescript
interface InsightMaturity {
  phase: 'collecting' | 'early_patterns' | 'provisional' | 'robust';
  phase_index: 1 | 2 | 3 | 4;
  current_entries: number;
  next_phase_at: number | null; // null in robust
  next_phase_label: string | null; // null in robust
  entries_until_next: number | null;
  user_message_key: string; // i18n key
}
```

The frontend MUST NOT compute the phase independently from entry count — it always reads from the API response.

---

## 6. Acceptance Criteria

- [ ] `InsightJourneyBanner` renders correctly for all 4 phases
- [ ] `InsightMaturityBadge` shows phase-appropriate label and tooltip on every insight card
- [ ] No raw p-value or numeric confidence score is visible to the user anywhere
- [ ] Empty state on Insights page shows phase-aware explanation
- [ ] Phase milestone card appears once on phase transition, never again
- [ ] All chart annotations with correlation show uncertainty ribbon in `early_patterns` and `provisional`
- [ ] Dashboard summary module does not render correlation content in `collecting` phase
- [ ] All copy follows tone guidelines per phase
- [ ] All `maturity.*` i18n keys are defined
- [ ] API `insight_maturity` object is present in all insight endpoint responses

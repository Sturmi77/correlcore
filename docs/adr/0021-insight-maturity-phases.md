# ADR-0021: Insight Maturity Phases as a First-Class Frontend Concept

| Field        | Value                     |
| ------------ | ------------------------- |
| **ID**       | 0021                      |
| **Date**     | 2026-05-16                |
| **Status**   | Accepted                  |
| **Deciders** | @Sturmi77                 |
| **Area**     | Frontend / Insights / API |

---

## Context

CorrelCore's core value proposition is "correlations instead of raw data". However, meaningful correlations
require a minimum amount of tracking data. Previously, the design document mentioned a 30-entry threshold
for insight activation with a disclaimer, but this threshold was purely a backend gate — the frontend had
no concept of _insight maturity_ at all.

This led to two UX problems:

1. Users see an empty or locked insights section without understanding why.
2. The wait feels like a bug, not a guided journey.

Discussions also revealed that the **Insight Quality Indicator** (ADR-0018) is directly affected:
it must reflect maturity phase, not just statistical confidence of an individual insight.

Furthermore, a systematic analysis identified **all frontend elements affected** by maturity logic:

- Insight cards (headline, tone, CTA)
- Quality indicator / confidence badge
- Chart annotations and uncertainty hints
- Dashboard summary module
- Weekly reflection component
- Empty states and locked states
- Notification and milestone messages
- API response contract (new fields required)

---

## Decision

Insight maturity is promoted to a **first-class domain concept** shared by backend and frontend.

### Phase Model

| Phase | Key              | Entry Range | Label (UI)           | What is available                                         |
| ----- | ---------------- | ----------- | -------------------- | --------------------------------------------------------- |
| 1     | `collecting`     | 1–6         | Collecting Data      | Streaks, raw counts, entry history                        |
| 2     | `early_patterns` | 7–13        | First Patterns       | Trends, frequency charts, simple comparisons              |
| 3     | `provisional`    | 14–29       | Provisional Insights | Correlations with explicit uncertainty disclaimer         |
| 4     | `robust`         | 30+         | Robust Insights      | Full insight engine, template statements, recommendations |

### API Contract Extension

Every `/api/v1/insights/*` response MUST include:

```json
{
  "insight_maturity": {
    "phase": "early_patterns",
    "phase_index": 2,
    "current_entries": 9,
    "next_phase_at": 14,
    "next_phase_label": "Provisional Insights",
    "entries_until_next": 5,
    "user_message_key": "maturity.early_patterns.description"
  }
}
```

The `user_message_key` references a translation/copy key — the backend never generates user-facing text directly.

### Frontend Rules

1. **InsightJourneyBanner** — always visible on the Insights page; shows current phase, progress bar, and next milestone.
2. **InsightMaturityBadge** — replaces the raw confidence score in all insight cards; combines phase + confidence into one human-readable label.
3. **Phase-gated content**: Insight cards, chart annotations, and dashboard summaries MUST use phase-appropriate language (see `docs/frontend/INSIGHT_MATURITY.md`).
4. **Empty and locked states** MUST explain the phase reason, not just show an empty UI.
5. **Phase transitions** trigger an in-app notification (not a toast — a dedicated milestone card).
6. The Insight Quality Indicator (ADR-0018) is superseded by the combined phase + confidence model defined here.

---

## Consequences

### Positive

- Users understand the journey; waiting feels purposeful.
- Consistent maturity signal across all UI elements prevents contradictory messages.
- Backend and frontend share a single source of truth via API fields.
- Enables future gamification (streaks toward next phase milestone).

### Negative / Trade-offs

- Additional fields in every insight API response (minor payload increase).
- All existing insight UI components need a maturity-awareness refactor (tracked in GitHub Issues).
- Copy/translation layer requires `maturity.*` keys for all 4 phases.

---

## Alternatives Considered

| Alternative                           | Reason Rejected                                                          |
| ------------------------------------- | ------------------------------------------------------------------------ |
| Keep threshold as pure backend gate   | Leaves users without UX context; contradicts "guided journey" philosophy |
| Compute maturity only on the frontend | Duplicates logic; risks divergence from backend insight engine           |
| Use raw entry count in UI             | Too technical; doesn't communicate meaning or progress                   |

---

## Related

- ADR-0018: Insight Confidence Visualisation (superseded in part)
- ADR-0016: Timeseries Split for ML Models
- ADR-0017: Frontend Screen Architecture
- ADR-0037: Tag-cluster `cluster_maturity` (`early` / `provisional` / `robust`) complements insight phases for descriptive tag groups
- `docs/frontend/INSIGHT_MATURITY.md` — detailed component spec
- GitHub Issues: #insight-maturity (see issue tracker)

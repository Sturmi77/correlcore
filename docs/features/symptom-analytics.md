# Feature Spec: Symptom Analytics

**Status:** Proposed
**Version:** 1.0.0
**Created:** 2026-05-19
**Updated:** 2026-05-19
**Owner:** @Sturmi77
**Milestone Coverage:** Sprint-free (foundational bugfix) → M7 (main implementation) → M8 (sleep×symptom) → M9 (beta hardening)

---

## Overview

This document specifies the **Symptom Analytics** feature for CorrelCore. The goal is to elevate
symptoms from a tracked-but-unanalysed signal into a first-class analytical entity, producing insights
across three complementary statistical levels: univariate (symptom vs. mood/energy/stress), co-occurrence
(symptom vs. tag), and multivariate (symptoms as features in regression, lag, and clustering pipelines).

The architectural decision driving this spec is [ADR-0025](../adr/0025-symptom-analytics.md). The data
model foundation is [ADR-0008](../adr/0008-symptom-master-tabelle.md). Phase gating follows
[ADR-0021](../adr/0021-insight-maturity-phases.md). Frontend rendering is specified in
[`../frontend/SYMPTOM_VISUALIZATION.md`](../frontend/SYMPTOM_VISUALIZATION.md).

---

## Motivation

Symptoms are positioned as a **core USP** of CorrelCore's correlation analysis (see
`DESIGN_DOCUMENT.md` §2.4): they are more objective markers than self-reported mood and therefore carry
high analytical value. However, since the M1 introduction of the symptom master table
([ADR-0008](../adr/0008-symptom-master-tabelle.md)), no analytical pipeline has consumed them. The
Insight Engine correlates only tags against mood plus weekday patterns. Symptoms have remained
write-only data.

Three concrete problems result from this gap:

1. **Users cannot see whether symptoms relate to their mood.** A user logging headaches for three weeks
   receives no insight, even though the data is sufficient for analysis.
2. **Symptom-tag co-occurrence is invisible.** Whether headaches cluster with stress-tags or sleep-tags
   is currently unknowable through the UI.
3. **Planned M7 multivariate models would permanently exclude symptoms** unless this is addressed at
   architecture level — Lasso (#144), lag analysis (#145), and hierarchical clustering (#150) all
   currently scope to tags only.

This spec defines the engineering and product work required to close all three gaps coherently.

---

## Non-Goals

- **No symptom-intensity-aware analysis in this scope.** The `entry_symptoms.intensity` field (0–3)
  is treated as binary (present/absent) for all analyses. Intensity-aware methods are deferred to
  Future Work — see §Future Work.
- **No medical claims.** Symptom insights are statistical associations, never diagnoses or
  recommendations to seek treatment.
- **No external API calls.** All analysis runs locally in the existing nightly worker.
- **No new database schema.** Existing `entry_symptoms` and `symptoms` tables are sufficient.
- **No symptom-prediction models.** This is descriptive/associational analytics, not prognostic.
- **No symptom-LLM integration in this scope.** Ollama statement formulation (Issue #148) covers
  symptom insights through the same templating layer as tag insights; no symptom-specific LLM logic.

---

## Product Principles

| #   | Principle                                            | Rationale                                                                                |
| --- | ---------------------------------------------------- | ---------------------------------------------------------------------------------------- |
| 1   | Association, never causation                         | All user-facing language is neutral; causal framing is forbidden                         |
| 2   | Methodology guardrails are non-negotiable            | FDR correction, min-frequency, and confounder checks are not optional                    |
| 3   | Phase gating is shared with tag analytics            | Symptom insights follow ADR-0021 exactly — no separate gating logic                      |
| 4   | Multivariate inclusion is structural                 | Symptoms are inputs to Lasso/lag/clustering by architectural decision, not sprint choice |
| 5   | Visibility before sophistication                     | Descriptive heatmaps in `early_patterns` precede inferential insights in `provisional`   |
| 6   | Symptom insights live in the existing /insights feed | No separate route; the feed is the canonical insight surface                             |

---

## Three Analytical Levels

### Level 1 — Univariate (Symptom × Continuous Metric)

**Question answered:** "Do days with symptom X show different mood/energy/stress than days without?"

#### Methods

| Method         | When applied                                                 | Output                              |
| -------------- | ------------------------------------------------------------ | ----------------------------------- |
| Pointbiserial  | Default; mirror of existing Tag↔Mood code path               | Correlation coefficient `r_pb`      |
| Mann-Whitney-U | When mood distribution is non-normal (Shapiro-Wilk p < 0.05) | U statistic, effect size `r = Z/√N` |
| Cliff's Delta  | Always computed alongside U for interpretability             | `δ ∈ [-1, +1]`                      |

The Mann-Whitney/Cliff's Delta pair is the **robust track**; pointbiserial is reported for parity with
the tag pipeline but downweighted if the normality test fails. The engine reports both, the frontend
displays only the robust one when they diverge.

#### Eligibility

- `current_entries ≥ 15` (maturity phase ≥ `provisional`)
- Symptom must occur in **≥ 5 entries** (base-rate guard)
- Symptom must occur in **< (n − 5)** entries (never analyse a symptom that is present every day)

#### FDR

Benjamini-Hochberg correction is applied **per metric** across all symptoms tested. For three metrics
(mood, energy, stress), this means three independent BH families. Adjusted p-value threshold:
**α = 0.10** for insight surfacing, **α = 0.05** for strong-claim language in copy.

#### Insight Type

`symptom_mood_association` (single type, with `metric` field distinguishing mood/energy/stress)

---

### Level 2 — Co-Occurrence (Symptom × Tag)

**Question answered:** "Do symptom X and tag Y tend to occur on the same days?"

#### Methods

| Method              | Role                                                              | Range      |
| ------------------- | ----------------------------------------------------------------- | ---------- |
| Phi coefficient (φ) | Primary effect size; equivalent to Pearson on two binaries        | `[-1, +1]` |
| Jaccard index (J)   | Asymmetric interpretability: "given symptom X, how often tag Y?"  | `[0, 1]`   |
| Lift / PMI          | Compares observed vs. expected co-occurrence under independence   | `(0, +∞)`  |
| Fisher Exact Test   | Significance test; preferred over chi-square at small cell counts | p-value    |

**Display rule:** the heatmap colours by Lift (divergent scale, neutral at Lift = 1). Phi is shown in
the card detail view. Jaccard is shown as natural-language phrasing in copy. Fisher Exact drives the
significance gate but is not surfaced numerically to users.

#### Eligibility

- `current_entries ≥ 15`
- Both the symptom and the tag must individually occur in **≥ 5 entries**
- The pair must have **≥ 5 co-occurrences** OR Fisher Exact p < 0.05 with ≥ 3 co-occurrences
  (allows detection of strong but rare patterns without inflating the FDR family)

#### Display Filtering

- Heatmap rendering threshold: `|Lift − 1| > 0.5` OR `Fisher Exact p_adj < 0.10`
- Insight card surfacing threshold: `|Lift − 1| > 0.67` AND `Fisher Exact p_adj < 0.10`

The lower threshold for heatmap rendering allows visual exploration while the higher threshold for
explicit insight cards prevents weak signals from generating premature claims.

#### FDR

One BH family across **all symptom × tag pairs computed**. For a user with 8 symptoms and 15 tags above
the eligibility floor, this is up to 120 tests. Without correction, ~6 false positives at α = 0.05 are
expected.

#### Insight Type

`symptom_tag_cooccurrence`

#### Weekday Confounder

The existing chi-square weekday check (used for tag↔mood) is reused verbatim. A symptom-tag pair that
is fully explained by a shared weekday pattern (e.g. both peaking on Sundays) is downgraded with a
`confounder: "weekday"` field in the payload, and the frontend renders a muted variant.

---

### Level 3 — Multivariate (Symptoms in M7 Models)

**Question answered:** "Considering all signals together, which symptoms contribute meaningfully to
mood variation, and on what timescale?"

This level **extends three existing M7 issues** rather than introducing new pipelines:

| Existing Issue                                            | Title                           | Extension                                                                                   |
| --------------------------------------------------------- | ------------------------------- | ------------------------------------------------------------------------------------------- |
| [#144](https://github.com/Sturmi77/correlcore/issues/144) | Lasso Multi-Variable Regression | Include `entry_symptoms` as binary features in the design matrix alongside tags and metrics |
| [#145](https://github.com/Sturmi77/correlcore/issues/145) | Lag Analysis 1–7 days           | Treat symptoms as both input and target variables: `symptom_t → mood_{t+1..7}` and reverse  |
| [#150](https://github.com/Sturmi77/correlcore/issues/150) | Hierarchical Tag Clustering     | Use combined symptom+tag Jaccard distance matrix; clusters may mix symptoms and tags        |

#### Eligibility

- All Level 3 work requires `current_entries ≥ 30` (`robust` phase)
- Symptom features in Lasso: same min-frequency rule (≥ 5 occurrences) applies; symptoms not meeting
  the threshold are dropped from the design matrix
- Lag analysis: minimum 10 observations per lag bucket required to compute

#### Insight Type

`symptom_cluster` (covers multivariate findings; specific sub-type via `payload.method` field:
`lasso` | `lag` | `cluster`)

#### Output

Multivariate findings are surfaced as **higher-tier insight cards** with explicit "robust" maturity
badging. Lasso coefficients and cluster membership are revealed in the expanded card state only
(progressive disclosure rule from [ADR-0017](../adr/0017-frontend-screen-architecture.md)).

---

## Methodological Guardrails

These rules apply across all three levels and are not negotiable per-sprint.

### FDR Correction (Benjamini-Hochberg)

- Mandatory for any analysis producing more than one p-value
- Family definition:
  - Level 1: one family per metric (mood/energy/stress) = 3 families
  - Level 2: one family across all symptom×tag pairs
  - Level 3: Lasso uses regularisation in place of FDR; lag analysis applies BH per (variable, lag)
    pair across the full lag matrix
- α = 0.10 for insight surfacing, α = 0.05 for "strong finding" copy upgrade

### Minimum Frequency

- A symptom must occur in **≥ 5 entries** to be eligible for any analysis
- Symbol: `min_freq_symptom = 5`
- For Level 2, both the symptom and the tag must independently meet this threshold

### Weekday Confounder Check

- Reuses `_check_weekday_confounder()` from existing `insight_engine.py`
- Applied to all Level 1 and Level 2 insights post-significance
- Confounded findings are stored but rendered with a muted/downgraded UI variant

### Base-Rate Protection

- A symptom occurring in `> (n − 5)` entries (i.e. present nearly every day) is excluded from analysis
  because the contrast group is too small for stable estimates
- Documented as `base_rate_excluded: true` in the engine log for traceability

### Causation Language Rule

- Templates must use neutral framing:
  - ✅ "Days with X often coincide with Y"
  - ✅ "Mood tends to be lower on X-days"
  - ❌ "X causes Y"
  - ❌ "Avoiding X will improve Y"
- The `CorrelationDisclaimer` component carries the methodology explanation, especially for the Lift
  metric (Lift = 2.0 ≠ "twice as likely overall"; needs careful copy)

---

## Phase Gating

Following [ADR-0021](../adr/0021-insight-maturity-phases.md), symptom analytics visibility by maturity
phase:

| Phase            | Entries | Symptom Analytics Visible                                                                                                             |
| ---------------- | ------- | ------------------------------------------------------------------------------------------------------------------------------------- |
| `collecting`     | 1–6     | **None.** No symptom insights computed, no symptom views in `/insights`.                                                              |
| `early_patterns` | 7–13    | Descriptive only: SymptomCalendarHeatmap (counts), Co-occurrence heatmap shows raw counts (no Lift). No correlation claims.           |
| `provisional`    | 14–29   | Level 1 (univariate) and Level 2 (co-occurrence) insights with FDR + uncertainty disclaimer. Heatmap switches to Lift colouring.      |
| `robust`         | 30+     | All three levels including multivariate symptom inclusion. Full copy without explicit uncertainty disclaimer in collapsed card state. |

**The frontend never computes the phase.** It always reads `insight_maturity.phase` from the API
response (ADR-0021 single source of truth).

---

## Engine Architecture

### Module Layout

```
backend/app/services/
├── insight_engine.py           # existing — orchestrator
├── symptom_analytics.py        # NEW — all three levels for symptoms
└── analytics_common.py         # existing — FDR, weekday confounder (reused)
```

### Integration with Nightly Worker

`insight_engine.py` already runs nightly, computes all current insight types, and stores results
idempotently. Symptom analytics integrates as a new block:

```python
# pseudocode — inside the nightly run loop
if maturity_phase in ("provisional", "robust"):
    symptom_insights = symptom_analytics.compute_univariate(user_entries)
    symptom_insights += symptom_analytics.compute_cooccurrence(user_entries)
if maturity_phase == "robust":
    symptom_insights += symptom_analytics.compute_multivariate(user_entries)  # M7 only
store_insights(symptom_insights)  # reuses existing storage with date-based dedup
```

### No Database Schema Changes

- Reads from existing `entry_symptoms` and `symptoms` tables
- Writes to existing `insights` table via existing storage helper
- New insight type strings are registered in the engine's type enum extension mechanism (already used
  for adding `weekday_pattern`)

### Caching

- Co-occurrence matrix is computed once per nightly run per user, not per insight
- Lasso/lag models are checkpointed to disk (already in scope for #144 / #145)

---

## API Contract

### Endpoint Changes

No new endpoints. The existing `/api/v1/insights` and `/api/v1/insights/latest` endpoints return the
new insight types alongside existing types.

### New Insight Type Strings

| Type string                | Level | Introduced in      |
| -------------------------- | ----- | ------------------ |
| `symptom_mood_association` | 1     | Sprint-free bugfix |
| `symptom_tag_cooccurrence` | 2     | M7                 |
| `symptom_cluster`          | 3     | M7                 |

### Payload Schemas

All payloads follow the existing insight envelope and add a type-specific `payload` object.

#### `symptom_mood_association`

```json
{
  "type": "symptom_mood_association",
  "payload": {
    "symptom_id": "uuid",
    "symptom_name": "Headache",
    "metric": "mood",
    "method": "pointbiserial",
    "effect_size": -0.42,
    "robust_effect_size": -0.38,
    "robust_method": "cliffs_delta",
    "p_value_corrected": 0.018,
    "sample_n": 47,
    "symptom_n": 12,
    "confounder": null,
    "tier": "preliminary"
  }
}
```

#### `symptom_tag_cooccurrence`

```json
{
  "type": "symptom_tag_cooccurrence",
  "payload": {
    "symptom_id": "uuid",
    "symptom_name": "Headache",
    "tag_id": "uuid",
    "tag_name": "high-stress",
    "phi": 0.34,
    "jaccard": 0.41,
    "lift": 2.1,
    "co_count": 9,
    "symptom_count": 12,
    "tag_count": 18,
    "total_count": 47,
    "p_value_corrected": 0.024,
    "confounder": null,
    "tier": "preliminary"
  }
}
```

#### `symptom_cluster`

```json
{
  "type": "symptom_cluster",
  "payload": {
    "method": "lasso",
    "model_id": "lasso_v1_2026-08-15",
    "target": "mood",
    "features": [
      { "kind": "symptom", "id": "uuid", "name": "Headache", "coefficient": -0.21 },
      { "kind": "tag", "id": "uuid", "name": "high-stress", "coefficient": -0.15 },
      { "kind": "metric", "name": "sleep_minutes", "coefficient": 0.08 }
    ],
    "r_squared": 0.34,
    "sample_n": 92,
    "tier": "robust"
  }
}
```

### Backward Compatibility

- All existing insight types remain unchanged
- The `insight_maturity` object (ADR-0021) is unchanged
- New clients reading unknown insight types must ignore them gracefully (already the contract)

---

## Frontend Integration (Summary)

Full specification: [`../frontend/SYMPTOM_VISUALIZATION.md`](../frontend/SYMPTOM_VISUALIZATION.md).

Summary:

- Symptom insights appear inline in the existing `/insights` feed as `SymptomInsightCard` variants
- Three new visualisation components rendered as sections within the existing route:
  - `SymptomCooccurrenceHeatmap` — Lift-coloured symptom × tag grid
  - `SymptomCalendarHeatmap` — year grid per symptom (M2 component variant)
  - `SymptomTrendOverlay` — DualAxisChart with symptom frequency + mood
- `CorrelationDisclaimer` extended with symptom-specific methodology copy
- No separate `/insights/symptoms` route is created

---

## Milestone Mapping

| Milestone   | Symptom Analytics Scope                                                                                                                                                           |
| ----------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Sprint-free | **Pointbiserial Symptom↔Mood bugfix** (Level 1 foundation). Standalone issue, no milestone label.                                                                                 |
| M4          | None. Mobile/Offline-focused; including symptom work would break sprint scope.                                                                                                    |
| M5          | **Symptom data quality audit** — descriptive statistics over beta data to identify which symptoms meet eligibility thresholds. Preparation only.                                  |
| M7          | **Main implementation.** Epic with sub-issues covering Level 2 engine, all frontend components, API extensions, multivariate extensions via existing #144 / #145 / #150 comments. |
| M8          | **Sleep × Symptom association** (Level 1 extension) as a side effect of sleep-metric integration.                                                                                 |
| M9          | **Beta usability review.** Potential reconsideration of intensity scope based on user feedback.                                                                                   |

---

## Acceptance Criteria

### Sprint-Free (Pointbiserial Bugfix)

- [ ] Pointbiserial Symptom↔Mood implemented analogous to existing Tag↔Mood
- [ ] Symptom-mood insights appear in `/insights` feed from `provisional` phase onward
- [ ] Min-frequency filter (≥ 5 occurrences) enforced
- [ ] FDR correction applied across symptoms within mood family
- [ ] Weekday confounder check runs against symptom-mood insights
- [ ] Existing tag insight behaviour unchanged (regression test passes)
- [ ] No new API field or breaking change

### M7

- [ ] Level 2 engine produces Phi, Jaccard, Lift, Fisher Exact for all eligible symptom×tag pairs
- [ ] FDR correction (BH) applied across the full symptom×tag family
- [ ] Lasso (#144) includes symptoms as binary features in the design matrix
- [ ] Lag analysis (#145) includes symptoms as both input and target variables
- [ ] Hierarchical clustering (#150) uses combined symptom+tag Jaccard distance matrix
- [ ] `SymptomCooccurrenceHeatmap` renders in `/insights` route with Lift-based colouring from `provisional`
- [ ] `SymptomCalendarHeatmap` renders from `early_patterns` (descriptive only)
- [ ] `SymptomTrendOverlay` renders DualAxisChart from `early_patterns`
- [ ] `SymptomInsightCard` integrates with progressive disclosure (3 levels per ADR-0017)
- [ ] `CorrelationDisclaimer` extended with symptom-specific copy (especially Lift methodology)
- [ ] Translation keys (de/en) cover all symptom insight types
- [ ] Weekday confounder check applies to all symptom insights with `confounder` field surfaced
- [ ] Base-rate exclusion logged when applicable

### M8

- [ ] Sleep×Symptom Spearman correlation computed when sleep data is available
- [ ] Sleep-related symptom insights surfaced as `symptom_mood_association` with `metric: "sleep_minutes"`
- [ ] Acceptance criteria for sleep metrics from M8 spec remain satisfied

### M9

- [ ] Beta feedback on symptom analytics usability collected and reviewed
- [ ] Decision on intensity scope (keep as Future Work / promote to next milestone) recorded as ADR addendum or new ADR

---

## Future Work

### Symptom Intensity (0–3)

The `entry_symptoms.intensity` field is captured since M1 but intentionally unused in this scope. All
analyses treat symptom presence as binary (`intensity ≥ 1` = present).

**Rationale for deferral:**

- Ordinal methods (Kendall's Tau, Spearman on intensity) materially increase model complexity
- Sample sizes per intensity level become small quickly → high-variance estimates dominate
- The user value of intensity-aware insights is unclear without prior evidence from binary findings

**Reconsidered:** post-M9 based on beta feedback, or earlier if data shows intensity carries strong
signal independent of presence.

### Cycle-Aware Symptom Analysis

Menstrual cycle is mentioned in `DESIGN_DOCUMENT.md` §2.4 as an optional module. Cycle-aware symptom
analytics (e.g. controlling for cycle phase in symptom×mood regressions) is out of scope here and would
warrant its own ADR if pursued.

### Symptom Sequence Patterns

Detecting symptom sequences (e.g. "fatigue typically precedes headache by 1–2 days") is a special case
of lag analysis but with symptoms on both sides. Could be added to #145 in a later iteration if data
volumes support it.

---

## Open Questions / ADR Triggers

- **Intensity scope reconsideration**: if beta feedback strongly demands intensity-aware insights, a
  follow-up ADR (ADR-0026 or later) will define the ordinal methodology. Not blocking M7.
- **Custom symptom moderation**: users can create custom symptoms (ADR-0008). Should the engine treat
  custom symptoms identically to curated defaults? Current spec assumption: yes. If false-positive
  noise from low-quality custom symptoms becomes a problem in beta, a `min_data_quality` flag could be
  added. Not blocking M7.
- **Cross-user pooling for very rare symptoms**: ruled out for privacy (Art. 9 data). Documented here
  to close the discussion.

---

## Related Documents

- [ADR-0008](../adr/0008-symptom-master-tabelle.md) — Symptom master data model
- [ADR-0016](../adr/0016-timeseries-split-ml-models.md) — Timeseries split for ML models
- [ADR-0018](../adr/0018-insight-confidence-visualisation.md) — Confidence visualisation conventions
- [ADR-0021](../adr/0021-insight-maturity-phases.md) — Insight maturity phases
- [ADR-0025](../adr/0025-symptom-analytics.md) — Symptom analytics architectural decision (parent ADR for this spec)
- [`DESIGN_DOCUMENT.md`](../DESIGN_DOCUMENT.md) §2.4, §2.9, §2.10, §6 — Symptom and insight anchoring
- [`../frontend/SYMPTOM_VISUALIZATION.md`](../frontend/SYMPTOM_VISUALIZATION.md) — Frontend specification (follow-up)
- [`../frontend/INSIGHT_MATURITY.md`](../frontend/INSIGHT_MATURITY.md) — Maturity rendering conventions

---

## Related Issues

- **Sprint-free bugfix:** Pointbiserial Symptom↔Mood (to be created; no milestone label)
- **M7 Epic:** Symptom Analytics — Full Implementation (to be created with sub-issues)
- **M8:** Sleep×Symptom association (to be created)
- **Existing issues to extend via comment:**
  - [#144](https://github.com/Sturmi77/correlcore/issues/144) — Lasso multi-variable regression
  - [#145](https://github.com/Sturmi77/correlcore/issues/145) — Lag analysis
  - [#150](https://github.com/Sturmi77/correlcore/issues/150) — Hierarchical tag clustering
- **M9:** Beta feedback review (to be created)

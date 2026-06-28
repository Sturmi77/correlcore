# ADR-0025: Symptom Analytics — Univariate, Co-Occurrence, Multivariate

| Field        | Value                                                   |
| ------------ | ------------------------------------------------------- |
| **ID**       | 0025                                                    |
| **Date**     | 2026-05-19                                              |
| **Status**   | Accepted (2026-06-28; M7 Sprints 1–2 shipped on `main`) |
| **Deciders** | @Sturmi77                                               |
| **Area**     | Insights / Engine / Frontend / API                      |

---

## Context

Symptoms have been a first-class entity in CorrelCore since M1 (see [ADR-0008](0008-symptom-master-tabelle.md)).
The schema mirrors the tag model: curated defaults plus user-owned custom symptoms, joined to entries via
`entry_symptoms`. The design document positions symptoms as a **core USP** of the correlation analysis
(`DESIGN_DOCUMENT.md` §2.4): symptoms are more objective markers than self-reported mood and therefore
carry high analytical value.

However, the implemented Insight Engine (M3, M3.1, M3.6) only correlates **tags against mood** via
pointbiserial correlation, plus weekday patterns and metric-to-metric Spearman. **Symptoms are not analysed
at all** — neither against mood, energy, or stress, nor in relation to tags, nor as features in the planned
multivariate models (Issues #144 Lasso, #145 Lag analysis, #150 Hierarchical clustering).

This is a structural gap, not just a missing feature:

1. The Insight Engine has no notion of _association_ between two categorical/binary variables. Tag↔Mood
   uses pointbiserial because mood is continuous; Tag↔Symptom (both binary) requires a different statistical
   family (co-occurrence measures).
2. The planned multivariate models in M7 implicitly assume tags as the only categorical input, which would
   permanently exclude symptoms from Lasso and lag analysis unless this is addressed at the architecture level.
3. There is no shared convention for how symptom-derived insights are phase-gated under [ADR-0021](0021-insight-maturity-phases.md),
   how their effect sizes are visualised under [ADR-0018](0018-insight-confidence-visualisation.md), or how
   methodological guardrails (multiple testing, weekday confounders, base-rate filtering) apply.

A discussion in May 2026 surfaced three distinct analytical levels that must be addressed together to avoid
inconsistent partial solutions across milestones:

- **Univariate**: symptom presence vs. continuous metrics (mood, energy, stress)
- **Co-occurrence**: symptom presence vs. tag presence (both binary/categorical)
- **Multivariate**: symptoms as features in regression, lag analysis, and clustering pipelines

The frontend implications are equally cross-cutting: new co-occurrence visualisations, symptom-specific
insight cards, methodology disclaimers, and integration into the existing `/insights` route.

---

## Decision

Symptom analytics is promoted to a **three-level analytical framework**, anchored in this ADR, fully
specified in [`docs/features/symptom-analytics.md`](../features/symptom-analytics.md), with frontend
behaviour specified in [`docs/frontend/SYMPTOM_VISUALIZATION.md`](../frontend/SYMPTOM_VISUALIZATION.md).

### Three Analytical Levels

| Level | Name          | Methods                                                                               | Phase Gate          | Insight Type(s)            |
| ----- | ------------- | ------------------------------------------------------------------------------------- | ------------------- | -------------------------- |
| 1     | Univariate    | Pointbiserial, Mann-Whitney-U, Cliff's Delta                                          | ≥15 (`provisional`) | `symptom_mood_association` |
| 2     | Co-Occurrence | Phi coefficient, Jaccard index, Lift/PMI, Fisher Exact                                | ≥15 (`provisional`) | `symptom_tag_cooccurrence` |
| 3     | Multivariate  | Lasso (Issue #144 extended), Lag analysis (#145 extended), Clustering (#150 extended) | ≥30 (`robust`)      | `symptom_cluster`          |

The three levels are **complementary, not alternative**. An insight at level 1 (symptom↔mood) does not
replace a finding at level 2 (symptom↔tag) — they answer different questions.

### Methodological Guardrails

The following rules are non-negotiable and apply to all three levels:

1. **FDR correction (Benjamini-Hochberg)** is mandatory across all symptom-related test families. Without
   it, 200+ symptom×tag pairs guarantee spurious "significant" results.
2. **Minimum frequency**: a symptom must occur in at least **5 entries** to be eligible for any analysis.
   This protects against base-rate inflation in Lift/PMI calculations.
3. **Weekday confounder check**: the existing chi-square weekday gate (used for tag insights) is reused
   verbatim for symptom insights. A symptom-mood association that is fully explained by weekday is
   downgraded.
4. **Association is not causation**: all user-facing language must use neutral framing
   ("X frequently co-occurs with Y", "X-days show lower mood on average"). The CorrelationDisclaimer
   component is extended for symptom-specific methodology explanation, especially for the Lift metric
   which is not intuitive for laypeople.
5. **Multivariate inclusion is mandatory, not optional**: when Lasso, lag analysis, or hierarchical
   clustering are implemented, symptoms must be included as features in the same pipeline — not as a
   separate parallel system. This is a structural requirement to prevent two divergent analytical paths.

### Phase Gating

Following [ADR-0021](0021-insight-maturity-phases.md):

| Phase            | Entry Range | Symptom Analytics Visibility                                                          |
| ---------------- | ----------- | ------------------------------------------------------------------------------------- |
| `collecting`     | 1–6         | None. No symptom insights computed or shown.                                          |
| `early_patterns` | 7–13        | Descriptive only: symptom frequency, calendar heatmap. No correlation claims.         |
| `provisional`    | 14–29       | Level 1 and Level 2 insights with FDR correction and explicit uncertainty disclaimer. |
| `robust`         | 30+         | All three levels, including multivariate symptom inclusion in M7 models.              |

The symptom-tag co-occurrence heatmap is rendered in `early_patterns` only as raw counts (no Lift values),
and switches to Lift-based colouring from `provisional` onward.

### Engine Architecture

- New module: `backend/app/services/symptom_analytics.py`
- Integrated into the existing nightly insight worker (`insight_engine.py`), not a separate worker
- Reuses existing FDR infrastructure (Benjamini-Hochberg), weekday confounder check, and idempotent
  storage
- No database schema changes required — uses existing `entry_symptoms` and `symptoms` tables
- New insight type strings registered in the existing `insights.insight_type` enum extension mechanism

### API Contract

- Insight type strings extend the existing `/api/v1/insights` and `/api/v1/insights/latest` payloads
  without breaking changes
- Each new insight type defines its own `payload` schema for UI rendering (e.g. `symptom_tag_cooccurrence`
  carries `symptom_id`, `tag_id`, `lift`, `co_count`, `total_count`, `p_value_corrected`)
- The `insight_maturity` object from ADR-0021 remains the single source of truth — symptom analytics does
  not introduce its own phase computation

### Frontend Integration

- Symptom insights appear **inline in the existing `/insights` feed** as a new `SymptomInsightCard`
  variant. No separate `/insights/symptoms` route is created.
- Three new visualisation components are added (specified in `docs/frontend/SYMPTOM_VISUALIZATION.md`):
  - `SymptomCooccurrenceHeatmap` — symptoms × tags grid with Lift-based colouring (divergent blue/red)
  - `SymptomCalendarHeatmap` — year-grid frequency view per symptom (M2 component variant)
  - `SymptomTrendOverlay` — rolling-7-day symptom frequency with mood overlay (DualAxisChart)
- `CorrelationDisclaimer` is extended with symptom-specific methodology copy
- All language follows ADR-0021 phase-appropriate tone rules; "association" never "cause"

### Scope Boundary: Symptom Intensity

The `entry_symptoms.intensity` field (0–3, captured since M1) is **intentionally excluded** from this ADR.
All analyses treat symptom presence as binary (intensity ≥ 1 = present). Rationale:

- Ordinal methods (Kendall's Tau, Spearman on intensity) materially increase model complexity
- Sample sizes per intensity level become small quickly → high-variance estimates dominate
- The user value of intensity-aware insights is unclear without prior evidence from binary findings

Intensity-aware analytics is documented as **Future Work** in
[`docs/features/symptom-analytics.md`](../features/symptom-analytics.md) §8.1 and may be reconsidered
post-M9 based on beta feedback, or earlier if binary findings reveal strong intensity-dependent signals.

---

## Consequences

### Positive

- Symptoms become a first-class analytical signal, fulfilling the M1 design intent (`DESIGN_DOCUMENT.md`
  §2.4) that was structurally unrealised since M3.
- The Insight Engine gains a new statistical family (co-occurrence) that is reusable beyond symptoms —
  e.g. tag×tag co-occurrence becomes trivially possible later.
- Multivariate symptom inclusion in M7 models (Lasso, lag, clustering) is guaranteed by architectural
  decision, not by individual sprint discretion.
- Phase gating, FDR correction, and confounder checks are shared with existing tag analytics → no
  divergent methodology between symptom and tag insights.
- One ADR covers all three levels → no fragmented decision trail across follow-up ADRs.

### Negative / Trade-offs

- Multiple-testing burden grows substantially (e.g. 10 symptoms × 20 tags = 200 pairs). Mitigated by
  mandatory BH correction and minimum-frequency filter, but the false discovery rate must be monitored
  during beta.
- Lift values are not intuitive for laypeople. Requires careful copy work in `CorrelationDisclaimer` and
  symptom insight cards.
- Frontend gains three new components plus disclaimer extensions → increased UI surface area and
  translation key inventory (de/en).
- Symptom intensity remains unused for now, which is a known information loss. Documented as Future Work
  rather than silently ignored.

---

## Alternatives Considered

| Alternative                                                | Reason Rejected                                                                                                                                                   |
| ---------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Three separate ADRs (one per analytical level)             | The three levels share statistical guardrails, phase gating, and frontend infrastructure. Splitting fragments the decision trail without clarifying anything.     |
| Symptom analytics as a separate worker / pipeline          | Would duplicate the FDR, weekday-confounder, and storage infrastructure already in `insight_engine.py`. Integration is cheaper and prevents methodological drift. |
| Build a dedicated `/insights/symptoms` route               | The heatmap is the only oversized component. Integrating it as a section above the feed avoids navigation fragmentation and keeps symptom findings in context.    |
| Include symptom intensity in M7 scope                      | Adds material complexity (ordinal methods, smaller per-level sample sizes) before binary findings have demonstrated user value. Deferred as Future Work.          |
| Use chi-square for symptom×tag co-occurrence               | Small cell counts in typical homelab datasets (50–200 entries) violate chi-square assumptions. Fisher Exact is more reliable; Lift adds interpretability.         |
| Use pointwise correlation only (no co-occurrence measures) | Cannot quantify the association between two binary variables. Would force symptom-tag analysis into a less informative metric-mood frame.                         |

---

## Implementation Roadmap

This ADR does not commit a specific milestone for the foundational univariate step. The implementation is
sequenced as follows:

1. **Sprint-free**: Engine parity bugfix — pointbiserial Symptom↔Mood (analogous to existing Tag↔Mood).
   This closes the most basic gap and is a prerequisite for all M7 symptom work. Tracked as a standalone
   issue with no milestone label, picked up opportunistically.
2. **M7** (Insights v2): Main implementation — co-occurrence (Level 2), multivariate inclusion (Level 3),
   all frontend components, methodology copy. Tracked as an Epic with sub-issues. Issues #144, #145, #150
   are extended via comment (not modified) to include symptoms as inputs.
3. **M8** (Sleep & Health Connect): Sleep×Symptom association as a side effect of sleep-metric integration.
4. **M9** (Beta hardening): Review usability of symptom analytics based on beta feedback. Potential
   reconsideration of intensity scope.

---

## Related

- [ADR-0008](0008-symptom-master-tabelle.md) — Symptom master table and `entry_symptoms` data model
- [ADR-0016](0016-timeseries-split-ml-models.md) — Timeseries split, applies to multivariate symptom models
- [ADR-0018](0018-insight-confidence-visualisation.md) — Confidence rendering conventions, reused for symptom insights
- [ADR-0021](0021-insight-maturity-phases.md) — Insight maturity phases, drives phase gating in this ADR
- [`docs/features/symptom-analytics.md`](../features/symptom-analytics.md) — Full feature specification (follow-up)
- [`docs/frontend/SYMPTOM_VISUALIZATION.md`](../frontend/SYMPTOM_VISUALIZATION.md) — Frontend component specification (follow-up)
- `DESIGN_DOCUMENT.md` §2.4, §2.9, §2.10, §6 — Anchoring patches landed in PR #203
- GitHub Issues: #144 (Lasso), #145 (Lag analysis), #150 (Hierarchical clustering) — to be extended via comment

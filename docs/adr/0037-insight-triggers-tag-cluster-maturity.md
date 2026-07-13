# ADR-0037 — Insight-Trigger, deskriptive Wochentage & Tag-Cluster-Reifegrad

| Field | Value |
| ----- | ----- |
| **ID** | 0037 |
| **Date** | 2026-07-13 |
| **Status** | Vorgeschlagen |
| **Deciders** | @Sturmi77 |
| **Area** | Backend / Analytics / API / Frontend |
| **Related** | ADR-0016, ADR-0017, ADR-0021, [Freigabe-Vorschlag](../proposals/INSIGHT_PIPELINE_TAG_GROUPS_PROPOSAL.md) |

---

## Context

CorrelCore separates **data maturity** (entry count phases per ADR-0021) from **feature visibility**. Users with 30–89 tracking days can be in phase `provisional` or `robust` while several UI surfaces remain empty:

1. **Insights** are persisted only after the analytics worker runs (`generate_and_store_insights`). The nightly cron is the sole production trigger today. Local dev and bulk import do not regenerate insights, which feels like a bug when maturity UI already shows progress.

2. **Home weekday overview** reads `weekday_pattern` insight payloads only. That insight requires `|weekday_delta| ≥ 0.5`. Users with even weekday coverage but flat mood (e.g. max Δ ≈ 0.29 over 67 days) see an empty chart despite descriptive data existing.

3. **Tag groups** (`GET /insights/tag-clusters`) require `MIN_TAG_CLUSTER_ENTRIES = 90`. This threshold was introduced alongside M7 ML features but tag clustering uses Jaccard co-occurrence + k-means **without** cross-validation. ADR-0016's n≥90 rule applies to Lasso/Lag (`TimeSeriesSplit`), not to descriptive clustering. Tag groups are treated as an essential product feature; blocking them until day 90 is disproportionate.

M9 explicitly kept inferential thresholds strict (`MIN_WEEKDAY_DELTA`, `ANALYTICS_MIN_TAG_USAGES`) and scheduled heavy analytics in the nightly worker. This ADR does **not** relax those inferential gates.

---

## Decision

### 1. Multi-trigger insight pipeline (single engine path)

Insight generation and tag-vector recomputation share one code path (`insight_worker_service.generate_insights_for_job`). In addition to the existing nightly worker (03:00 UTC), the following triggers are added:

| Trigger | Event | Scope |
| ------- | ----- | ----- |
| Nightly worker | Scheduled | All eligible users |
| Post-import | Successful `POST /entries/batch` | Importing user only |
| User on-demand | `POST /api/v1/insights/regenerate` | Owner, rate-limited |
| Admin | `POST /api/v1/insights/trigger` | Admin role |

**Rules (all triggers):**

- Respect `user_preferences.analytics_enabled` (skip when `false`)
- Bind user DEK before writing `insights.statement_enc`
- Idempotent per `(user_id, generated_for_date)`
- Per-user transaction isolation on failure
- **No** synchronous full regeneration on every entry save (M9: heavy analytics stay off the hot path)

`GET /insights/tag-clusters` continues to recompute on read for freshness; triggers also persist tag vectors for consistency.

### 2. Descriptive weekday summary (dashboard)

`GET /api/v1/dashboard/summary` includes `weekday_summary[]` with per-weekday `entry_count` and `mood_avg`, computed server-side from deduplicated daily entries.

- Available when ≥ 7 calendar days with entries span at least one weekday bucket with data
- **Not** an insight; no inferential claim
- `weekday_pattern` insight unchanged (`MIN_WEEKDAY_DELTA = 0.5`)

Frontend `HomeWeekdayOverview` uses `weekday_summary` for bars; insight-derived labels remain optional overlays.

### 3. Tiered tag-cluster maturity (decoupled from ML n≥90)

Replace the single `MIN_TAG_CLUSTER_ENTRIES = 90` gate with:

| Constant | Value | Mode |
| -------- | ----- | ---- |
| `MIN_TAG_CLUSTER_PAIR_ENTRIES` | 30 | Top Jaccard pairs → micro-groups (2–3 tags) |
| `MIN_TAG_CLUSTER_PROVISIONAL_ENTRIES` | 45 | k-means, `k ≤ 3`, silhouette ≥ 0.08 |
| `MIN_TAG_CLUSTER_ROBUST_ENTRIES` | 90 | Full k-means (`k` 3–6), mixed tag/symptom nodes |

`TagClustersResponse` gains additive fields:

- `cluster_maturity`: `"early"` | `"provisional"` | `"robust"`
- `cluster_mode`: `"pair"` | `"kmeans"`
- `entries_until_robust`: int | null
- `silhouette_score`: float | null

Provisional clusters are **descriptive**, not inferential insight cards. UI shows ADR-0021-aligned copy (“vorläufig” / `emerging_pattern`).

**Unchanged:**

- `MIN_ML_ENTRIES = 90` for Lasso and lag analysis (ADR-0016)
- `ANALYTICS_MIN_TAG_USAGES = 10` for point-biserial tag insights (M9)
- `MIN_WEEKDAY_DELTA = 0.5` for `weekday_pattern`

### 4. Rolling window semantics

`TAG_CLUSTER_WINDOW_DAYS = 90` remains the maximum lookback. When fewer than 90 days exist, the engine uses **all available days** down to the tier minimum (30 for pair mode). `window_days` in the API reflects the actual days used.

---

## Consequences

### Positive

- Users with 30–89 days see tag groups and weekday bars without weakening inferential statistics
- Bulk import and on-demand regeneration close the “mature data, empty UI” gap
- Clear separation: ADR-0016 ML validity vs. descriptive clustering
- ADR-0021 maturity phases extend naturally to `cluster_maturity`

### Negative / Trade-offs

- Additional API surface (`regenerate`, extended schemas)
- Provisional clusters may shift as data grows — requires explicit UI disclaimer
- Documentation must stay synchronized across ~20 markdown files (see proposal impact matrix)
- Slightly higher CPU on import/regenerate (acceptable with rate limits)

### Neutral

- Nightly worker remains the primary batch path for all users
- Tag-cluster GET-on-read behaviour unchanged; only response gates and fields evolve

---

## Alternatives Considered

| Alternative | Reason Rejected |
| ----------- | --------------- |
| Lower `MIN_TAG_CLUSTER_ENTRIES` to 60 only | Still arbitrary; no pair fallback; higher instability |
| Lower `MIN_WEEKDAY_DELTA` to 0.25 | Contradicts M9 threshold review; conflates descriptive + inferential |
| Frontend-computed weekday averages | Contradicts server-authoritative analytics (ADR-0017, M4.1) |
| Trigger insight gen on every entry save | M9: heavy analytics off hot path; DEK + FDR cost |
| Keep 90-day gate until ADR-0016 amended | ADR-0016 targets CV-ML only; misapplied to clustering |

---

## Implementation Checklist

- [ ] `POST /api/v1/insights/regenerate` (owner, rate-limited)
- [ ] `POST /api/v1/insights/trigger` (admin)
- [ ] Hook after `POST /entries/batch`
- [ ] `weekday_summary` in dashboard schema + service
- [ ] Tag-cluster tiers in `tag_cluster_service.py`
- [ ] `TagGroupsSection` + `HomeWeekdayOverview` UI
- [ ] i18n DE/EN
- [ ] Tests + API contract
- [ ] Documentation per [impact matrix](../proposals/INSIGHT_PIPELINE_TAG_GROUPS_PROPOSAL.md#7-dokumentations-impact-matrix)

---

## References

- [INSIGHT_PIPELINE_TAG_GROUPS_PROPOSAL.md](../proposals/INSIGHT_PIPELINE_TAG_GROUPS_PROPOSAL.md)
- [M10_1_INSIGHT_PIPELINE_SPRINT_PLAN.md](../M10_1_INSIGHT_PIPELINE_SPRINT_PLAN.md)
- ADR-0016 — Time-Series Split (ML n≥90)
- ADR-0017 — Frontend screen architecture (server-authoritative insights)
- ADR-0021 — Insight maturity phases
- M9 Sprint Plan — heavy analytics in nightly worker
- M9 Analytics Threshold Review — inferential thresholds unchanged

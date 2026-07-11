# M9 Analytics Threshold Review

Last updated: 2026-07-11 (M9 Sprint 5)  
Context: [`notes-in-analysis.md`](../features/notes-in-analysis.md) §M9 · Worker: [`backend/app/workers/analytics.py`](../../backend/app/workers/analytics.py)

## Objective

Review analytics worker and insight-engine thresholds before beta. **M9 scope: configuration
review only** — no per-entry notes opt-out API (deferred to M10 per sprint plan).

---

## Scope boundary

| In M9 Sprint 5 | Deferred |
| -------------- | -------- |
| Document and validate existing thresholds | Per-entry `note_visibility` API |
| Confirm defaults suitable for 5–10 beta users | Note signal extraction (M7 spec) |
| Env override via `ANALYTICS_MIN_TAG_USAGES` | LLM / Ollama note analysis |

**Notes-in-analysis:** Feature spec lists M9 as "threshold validation, false-positive review,
opt-out privacy setting per entry". Implementation status:

- `note_raw` / `entry_note_markers` — **not in codebase** (spec is forward-looking)
- M9 delivers **threshold review for live analytics engine** that powers insights today
- Per-entry opt-out → **M10** (explicit in [`M9_SPRINT_PLAN.md`](../M9_SPRINT_PLAN.md))

---

## Configurable thresholds (operator)

| Variable | Default | File | Purpose |
| -------- | ------- | ---- | ------- |
| `ANALYTICS_MIN_TAG_USAGES` | `10` | `config.py`, `.env.example` | Min tagged days before tag→mood insight |
| `analytics_enabled` | user pref | `user.preferences` | DSGVO M3 opt-out — worker skips user |

Documented in:

- [`infra/docker/.env.example`](../../infra/docker/.env.example)
- [`PHASE_INSIGHT_MATRIX.md`](../PHASE_INSIGHT_MATRIX.md) §Konstanten

**Beta recommendation:** Keep defaults. Lowering `ANALYTICS_MIN_TAG_USAGES` increases false-positive
insights for rare tags; raising it delays first insights for sparse taggers.

---

## Engine constants (code — not env)

### Core insight engine — `insight_engine.py`

| Constant | Value | Role |
| -------- | ----- | ---- |
| `EARLY_ENTRY_COUNT` | 3 | Maturity: collecting → early_patterns |
| `PRELIMINARY_ENTRY_COUNT` | 8 | Maturity tier |
| `DEVELOPING_ENTRY_COUNT` | 15 | Min entries for bivariate insights |
| `ROBUST_ENTRY_COUNT` | 30 | Robust tier |
| `MIN_BIVARIATE_ENTRIES` | 15 | Spearman / point-biserial floor |
| `MIN_TAG_GROUP_SIZE` | 2 | Untagged comparison group |
| `MIN_ABS_EFFECT_SIZE` | 0.25 | Effect size gate |
| `FDR_ALPHA` | 0.05 | BH-FDR for tag/metric family |
| `MIN_WEEKDAY_ENTRIES` | 7 | Weekday pattern floor |
| `MIN_WEEKDAY_DELTA` | 0.5 | Weekday effect gate |

### Symptom analytics — `symptom_analytics.py`

| Constant | Value | Role |
| -------- | ----- | ---- |
| `MIN_SYMPTOM_ANALYTICS_ENTRIES` | 15 | Symptom engine entry floor |
| `MIN_SYMPTOM_USAGES` | 5 | Per-symptom occurrence floor |
| `MIN_TAG_USAGES_FOR_SYMPTOM_COOCCURRENCE` | 5 | Tag leg in co-occurrence |
| `SYMPTOM_FDR_ALPHA` | 0.10 | Symptom family FDR (looser than tags) |
| `MIN_CARD_LIFT_DELTA` | 0.67 | Insight card lift gate |
| `MIN_HEATMAP_LIFT_DELTA` | 0.50 | Heatmap cell gate |

### Tag clusters — `tag_cluster_service.py`

| Constant | Value | Role |
| -------- | ----- | ---- |
| `MIN_TAG_CLUSTER_ENTRIES` | 90 | Clustering only at robust history |
| `MIN_TAG_CLUSTER_ACTIVE_TAGS` | 5 | Active tag diversity |

### Multivariate / ML — `multivariate_analytics.py`

| Constant | Value | Role |
| -------- | ----- | ---- |
| `MIN_ML_ENTRIES` | 90 | Lasso / lag eligibility |
| `MIN_LAG_OBSERVATIONS` | 10 | Lag correlation floor |

---

## Worker behaviour — `analytics.py`

| Job | Schedule | Threshold interaction |
| --- | -------- | --------------------- |
| Insight generation | Daily (~03:00 UTC slot) | Respects `analytics_enabled`; uses engine constants |
| Unverified cleanup | Daily | `UNVERIFIED_CLEANUP_DAYS` (default 7) |
| Sync conflict cleanup | Daily | `SYNC_CONFLICT_RETENTION_DAYS` (default 90) |

Insight generation calls `insight_worker_service.generate_insights_for_job` — no separate
notes-in-analysis path exists yet.

---

## Review decisions (M9)

| Question | Decision | Rationale |
| -------- | -------- | --------- |
| Lower `ANALYTICS_MIN_TAG_USAGES` for beta? | **No** (keep 10) | PHASE_INSIGHT_MATRIX documents intentional strictness; beta testers need realistic signal |
| Lower `MIN_SYMPTOM_USAGES` (5)? | **No** | Matches spec §min-frequency; avoids noisy symptom cards |
| Change `SYMPTOM_FDR_ALPHA` (0.10)? | **No** | Already looser than tag FDR; appropriate for sparse symptom matrix |
| Add env for symptom floors? | **Defer M10** | No operator demand yet; avoids config surface creep |
| Per-entry note opt-out? | **Defer M10** | No note analysis pipeline in production code |

---

## False-positive review (static)

| Risk | Mitigation in code | Beta watch |
| ---- | ------------------ | ---------- |
| Rare tag insights | `ANALYTICS_MIN_TAG_USAGES=10` | Testers with hobby tags — collect feedback |
| Weekday confounding | `weekday_confounder.py` flags `weekday_confounded` | Ask if confounded badge is understood |
| Symptom×tag lift false positives | FDR + `MIN_HEATMAP_LIFT_DELTA` | Heatmap week-2 review |
| ML overfit (lasso/lag) | `MIN_ML_ENTRIES=90` | Unlikely in beta window |

---

## Operator override (if needed mid-beta)

Only if round-1 feedback shows **systematic** "no insights yet" complaints from engaged testers:

```env
# Last resort — document change in beta round summary
ANALYTICS_MIN_TAG_USAGES=8
```

Requires API/worker container restart. **Do not go below 8** without engineering review (statistical
power). Symptom floors are not env-configurable — code change required.

---

## Verification

```bash
# Confirm default in settings
cd backend && uv run --python 3.12 python -c \
  "from app.core.config import settings; print(settings.ANALYTICS_MIN_TAG_USAGES)"

# Regression
cd backend && uv run --python 3.12 pytest tests/test_insight_engine.py tests/test_symptom_analytics.py -q
```

---

## Sign-off

| Review | Date | Outcome |
| ------ | ---- | ------- |
| M9 threshold review | 2026-07-11 | **Defaults retained**; per-entry notes → M10 |

---

## Related

- [`M9_SYMPTOM_ANALYTICS_BETA_REVIEW.md`](M9_SYMPTOM_ANALYTICS_BETA_REVIEW.md)
- [`notes-in-analysis.md`](../features/notes-in-analysis.md)
- [`M9_SPRINT_PLAN.md`](../M9_SPRINT_PLAN.md) — API minimization

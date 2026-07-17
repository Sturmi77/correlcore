# Open decisions & hygiene backlog — 2026-07-16

Living tracker. Update when a decision lands.

---

## Closed in follow-up PR (2026-07-16)

| Topic              | Resolution                                                                                                                      |
| ------------------ | ------------------------------------------------------------------------------------------------------------------------------- |
| Digest D-D1–D-D4   | In-app only; profile `digest`; default `digest_enabled=false`; Settings preview link                                            |
| LayerChart D-L1    | **Defer** — spike [`LAYER_CHART_SPIKE_2026-07-16.md`](../frontend/LAYER_CHART_SPIKE_2026-07-16.md); custom SVG stays production |
| Access JWT in JSON | Omitted by default; opt-in `?include_access_token=true`                                                                         |
| Password policy    | Min **12** + letter/digit + common-password denylist                                                                            |
| SlowAPI Redis blip | `in_memory_fallback_enabled=True` (limits kept; not swallow_errors)                                                             |
| Dependabot         | `.github/dependabot.yml` (npm, pip/backend, github-actions)                                                                     |
| Canonical API docs | OpenAPI + docs-site; `docs/API.md` marked Historical                                                                            |
| Compose matrix     | [`COMPOSE_STACKS.md`](../selfhost/COMPOSE_STACKS.md)                                                                            |

---

## Still open

| ID                 | Topic                                              | Notes                              |
| ------------------ | -------------------------------------------------- | ---------------------------------- |
| D-I1               | Generate secondary compose stacks from one source  | Matrix documented; codegen not yet |
| D-I4               | Stamp older GUI/quality audits as Historical       | Opportunistic                      |
| Digest WP1         | Prefer stored digest on GET                        | See completion plan                |
| LayerChart revisit | When Trends lasagna is scheduled + bundle measured | Spike criteria                     |
| Media / HC         | Deferred M13 / M8+M11                              | Not reopened here                  |
| External pentest   | Still pending (`M9_PENTEST.md`)                    |                                    |

---

## Active plans

- [`WEEKLY_DIGEST_COMPLETION_PLAN.md`](../features/WEEKLY_DIGEST_COMPLETION_PLAN.md)
- [`LAYER_CHART_COMPLETION_PLAN.md`](../frontend/LAYER_CHART_COMPLETION_PLAN.md)
- [`LAYER_CHART_SPIKE_2026-07-16.md`](../frontend/LAYER_CHART_SPIKE_2026-07-16.md)

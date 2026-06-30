# M7 Quality Gate — Code-Quality-Review + Security-Audit

**Milestone:** M7 — Insights v2 (Lasso, lag, symptom analytics, tag clustering)
**Stand:** 2026-06-30 (Sprint M7-C milestone closeout)
**Audit-Basis-Commit:** `main` post M7 Sprint 9 merge (#238)
**Referenz:** [`docs/DESIGN_DOCUMENT.md` §9](../DESIGN_DOCUMENT.md) — Quality-Gate-Definition

Dieses Dokument bündelt den vollständigen M7-Quality-Gate über Sprints 1–9 und den
formalen Meilenstein-Abschluss (Sprint M7-C). Optionale Sprint-8-Arbeit (Ollama, Digest)
und Changepoint (#149) sind **nicht** Teil des M7-Exit.

---

## 1. Scope

| Bereich | Issues / PRs | Status |
| ------- | ------------ | ------ |
| Lasso + TimeSeriesSplit | #144, PR #223 | shipped |
| Lag analysis 1–7d | #145, PR #223 | shipped |
| Symptom analytics L1/L2 | ADR-0025, PR #223 | shipped |
| Tag clustering (pgvector) | Sprint 3, PR #223/#224 | shipped |
| Combined tag+symptom clusters | #150, Sprint 9, PR #238 | shipped |
| Weekday OLS confounder | #146, Sprint 7 | shipped |
| Symptom visualisation (calendar, trend) | Sprint 6 | shipped |
| Sprint 9 interaction + feed UX | PR #238 | shipped |
| M7 mobile insights hardening | PR #234, #239 | shipped |
| M7 QA seed (full-stack path) | `seed_m7_qa.py` | shipped |
| Ollama / Digest | #148, #147 | deferred → M7-S8 |
| Changepoint | #149 | deferred → post-M7 |

Ausserhalb M7-Scope: Cycle×Lifestyle (M7.1), Sleep×Symptom (M8), Notes signals (#201/#202).

---

## 2. Code-Quality-Review (CQR)

### 2.1 Statische Analyse

| Tool | Ergebnis |
| ---- | -------- |
| `uv run --python 3.12 ruff check .` | Pass |
| `uv run --python 3.12 ruff format --check .` | Pass |
| `uv run --python 3.12 mypy app` | Pass |
| `pnpm lint` | Pass |
| `pnpm typecheck` | Pass |
| `pnpm check:contrast` | Pass |

### 2.2 Testabdeckung

| Suite | Ergebnis |
| ----- | -------- |
| `uv run --python 3.12 pytest` | Pass (M7 modules + `test_m7_qa_seed_service.py`) |
| `pnpm test` | Pass |
| `pnpm --filter @correlcore/web test:e2e:smoke` | Pass |
| `m7-insights-mobile.spec.ts` | Pass |

M7-relevante Backend-Module: `multivariate_analytics.py`, `symptom_analytics.py`,
`tag_cluster_service.py`, `weekday_confounder.py`, `insight_engine.py`, `m7_qa_seed_service.py`.

---

## 3. Security-Audit (SA) — M7-spezifisch

| Prüfpunkt | Ergebnis |
| --------- | -------- |
| Analytics opt-out respektiert (`analytics_enabled`) | Pass |
| Tag-cluster endpoint skippt Recompute bei opt-out | Pass |
| Insight statements neutral / non-causal | Pass |
| M7 seed script nur für Dev/QA dokumentiert | Pass |
| Kein Cloud-LLM in M7-Kern | N/A (Ollama deferred M7-S8) |
| pgvector RLS auf `tag_vectors` | Pass |

Keine SA-Blocker für M7-Exit.

---

## 4. Full-Stack QA

### Mock-Pfad

[`M7_VISUAL_QA.md`](M7_VISUAL_QA.md) — bestanden 2026-05-31 (Developer Mode mocks).

### Real-Data-Pfad

```bash
cd backend
uv run --python 3.12 --extra dev --extra analytics python scripts/seed_m7_qa.py --reset
uv run --python 3.12 python scripts/verify_m7_qa_api.py
# Login: m7-qa@localhost.dev / M7qaSeed1
```

Sign-off: [`M7_SPRINT5_FULLSTACK_QA.md`](M7_SPRINT5_FULLSTACK_QA.md).

### Sprint 9 rendered QA

Sign-off: [`M7_SPRINT9_VISUAL_QA.md`](M7_SPRINT9_VISUAL_QA.md) — 2026-06-30.

---

## 5. Verdikt

| Gate | Status |
| ---- | ------ |
| CQR (lint, types, tests) | **Bestanden** |
| SA (M7 privacy/analytics) | **Bestanden** |
| Visual QA mock path | **Bestanden** (2026-05-31) |
| Visual QA seeded path | **Bestanden** (2026-06-28) |
| Visual QA Sprint 9 | **Bestanden** (2026-06-30) |
| GitHub #144/#145 | **Geschlossen** |
| GitHub #146/#150 | **Geschlossen** (M7-C 2026-06-30) |
| M7 core shipped (Sprints 1–7) | **Ja** |
| M7 spec complete (Sprint 9) | **Ja** |
| **M7 milestone complete** | **Ja** (2026-06-30) |

**M7-Exit:** Complete. Optional LLM/Digest → M7-S8. Changepoint → post-M7.
See [`CLOSEOUT_SPRINT_PLAN.md`](../CLOSEOUT_SPRINT_PLAN.md) for M4/M5 closeout sequence.

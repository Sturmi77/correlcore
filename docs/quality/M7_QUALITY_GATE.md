# M7 Quality Gate — Code-Quality-Review + Security-Audit

**Milestone:** M7 — Insights v2 (Lasso, lag, symptom analytics, tag clustering)
**Stand:** 2026-06-28 (Sprint 5 closeout core)
**Audit-Basis-Commit:** `main` post M7 Sprints 1–3 merge (#223, #225, #224)
**Referenz:** [`docs/DESIGN_DOCUMENT.md` §9](../DESIGN_DOCUMENT.md) — Quality-Gate-Definition

Dieses Dokument bündelt den Sprint-5-Quality-Gate für den auf `main` gelieferten
M7-Kern (Sprints 1–3). Optionale Sprint-4/8-Arbeit (Ollama, Digest) und
Frontend-Lücken (Sprint 6) sind **nicht** Teil dieses Gates.

---

## 1. Scope

| Bereich                               | Issues / PRs             | Status            |
| ------------------------------------- | ------------------------ | ----------------- |
| Lasso + TimeSeriesSplit               | #144, PR #223            | shipped           |
| Lag analysis 1–7d                     | #145, PR #223            | shipped           |
| Symptom analytics L1/L2               | ADR-0025, PR #223        | shipped           |
| Tag clustering (pgvector)             | Sprint 3, PR #223/#224   | shipped           |
| M7 mobile insights hardening          | PR #234                  | shipped           |
| M7 QA seed (full-stack path)          | Sprint 5 `seed_m7_qa.py` | shipped           |
| Ollama / Digest                       | #148, #147               | deferred Sprint 8 |
| SymptomCalendarHeatmap / TrendOverlay | Sprint 6                 | open              |

Ausserhalb M7-Scope: Cycle×Lifestyle (# cycle-tracking M7.1), Notes signals (#201/#202).

---

## 2. Code-Quality-Review (CQR)

### 2.1 Statische Analyse (Sprint 5)

| Tool                                         | Ergebnis |
| -------------------------------------------- | -------- |
| `uv run --python 3.12 ruff check .`          | Pass     |
| `uv run --python 3.12 ruff format --check .` | Pass     |
| `uv run --python 3.12 mypy app`              | Pass     |
| `pnpm lint`                                  | Pass     |
| `pnpm typecheck`                             | Pass     |
| `pnpm check:contrast`                        | Pass     |

### 2.2 Testabdeckung

| Suite                                          | Ergebnis                                                 |
| ---------------------------------------------- | -------------------------------------------------------- |
| `uv run --python 3.12 pytest`                  | Pass (includes M7 subset + `test_m7_qa_seed_service.py`) |
| `pnpm test`                                    | Pass                                                     |
| `pnpm --filter @correlcore/web test:e2e:smoke` | Pass (baseline `/insights` smoke)                        |
| `m7-insights-mobile.spec.ts`                   | Pass (mobile M7 touch flow)                              |

M7-relevante Backend-Module: `multivariate_analytics.py`, `symptom_analytics.py`,
`tag_cluster_service.py`, `insight_engine.py` (M7 branches), `m7_qa_seed_service.py`.

---

## 3. Security-Audit (SA) — M7-spezifisch

| Prüfpunkt                                           | Ergebnis                                 |
| --------------------------------------------------- | ---------------------------------------- |
| Analytics opt-out respektiert (`analytics_enabled`) | Pass (#224, #227)                        |
| Tag-cluster endpoint skippt Recompute bei opt-out   | Pass (#224)                              |
| Insight statements neutral / non-causal             | Pass (copy + flags)                      |
| M7 seed script nur für Dev/QA dokumentiert          | Pass (`m7_qa_seed_service.py` docstring) |
| Kein Cloud-LLM in M7-Kern                           | N/A (Ollama deferred)                    |
| pgvector RLS auf `tag_vectors`                      | Pass (Migration + Tests)                 |

Keine neuen SA-Blocker für den M7-Kern identifiziert.

---

## 4. Full-Stack QA (Sprint 5)

### Mock-Pfad (bereits dokumentiert)

Siehe [`M7_VISUAL_QA.md`](M7_VISUAL_QA.md) — bestanden 2026-05-31 mit Developer
Mode „Force visualizations with mock data“.

### Real-Data-Pfad (neu)

```bash
# Postgres + Redis laufen; Migrationen applied
cd backend
uv run --python 3.12 --extra dev --extra analytics python scripts/seed_m7_qa.py --reset

# Login: m7-qa@localhost.dev / M7qaSeed1
# /insights ohne Mock-Mode — Lasso/Lag/Symptom/Tag-Groups aus echten Insights
```

Erwartung nach Seed:

- `entry_count` ≥ 90
- `symptom_cluster` insights (lasso und/oder lag) vorhanden
- `symptom_mood_association` und `symptom_tag_cooccurrence` vorhanden
- `GET /api/v1/insights/tag-clusters` liefert Gruppen oder `insufficient_data` nur bei
  absichtlich reduziertem Seed

---

## 5. Verdikt

| Gate                            | Sprint 5                                                                                                                  |
| ------------------------------- | ------------------------------------------------------------------------------------------------------------------------- |
| CQR (lint, types, tests)        | **Bestanden**                                                                                                             |
| SA (M7 privacy/analytics)       | **Bestanden**                                                                                                             |
| Visual QA mock path             | **Bestanden** (2026-05-31)                                                                                                |
| Visual QA seeded path           | **Bestanden** (integration tests + `verify_m7_qa_api.py`; see [`M7_SPRINT5_FULLSTACK_QA.md`](M7_SPRINT5_FULLSTACK_QA.md)) |
| GitHub issue closeout #144/#145 | **Erledigt** (2026-06-28)                                                                                                 |
| Sprint 5 closeout               | **Done** (2026-06-28)                                                                                                     |
| M7 core shipped (Sprints 1–7)   | **Ja** (2026-06-28)                                                                                                       |
| M7 spec complete (Sprint 9)     | **Ja** (2026-06-28)                                                                                                       |

**Sprint-5-Exit:** Done (2026-06-28). M7-Kern ist quality-gated und full-stack-validiert.

**Sprint-9-Exit (geplant):** Spec-complete laut ADR-0025 + SYMPTOM_VISUALIZATION ohne Sleep/Cycle/LLM.

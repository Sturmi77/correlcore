# M7 Sprint 5 — Full-Stack QA Sign-off

Date: 2026-06-28

Sprint 5 closes the gap between „M7 code on `main`“ and a reproducible
full-stack validation path without developer mock visualizations.

## Result

**Sprint 5 full-stack path: validated (automated).**

Manual GUI walkthrough on a local machine remains recommended but is no longer
a blocker — CI and local scripts cover the same analytics surface.

## Automated validation

| Layer   | Artifact                                | Expectation                                                    |
| ------- | --------------------------------------- | -------------------------------------------------------------- |
| Seed    | `backend/scripts/seed_m7_qa.py --reset` | ≥ 90 entries, verified user                                    |
| Service | `test_m7_qa_seed_integration.py`        | Lasso/lag, symptom insights, tag clusters, co-occurrence cells |
| CI      | `ci-api.yml` → `migrations-smoke` job   | Integration tests pass on pgvector Postgres                    |
| API     | `backend/scripts/verify_m7_qa_api.py`   | Login + `/insights/latest` + tag clusters + co-occurrence      |

### CI job

The `migrations-smoke` workflow runs `alembic upgrade head` (round-trip) and then:

```bash
CORRELCORE_RUN_INTEGRATION=1 \
  uv run pytest tests/test_m7_qa_seed_integration.py -q --no-cov
```

This proves the full M7 analytics stack on real PostgreSQL 16 + pgvector.

## Local full-stack procedure

```powershell
# 1. Start Postgres (pgvector) + Redis per AGENTS.md / DEVELOPMENT.md
# 2. Migrate
cd backend
uv run --python 3.12 alembic -c migrations/alembic.ini upgrade head

# 3. Seed
uv run --python 3.12 --extra dev --extra analytics python scripts/seed_m7_qa.py --reset

# 4. API verify (API must be running on :8000)
uv run --python 3.12 python scripts/verify_m7_qa_api.py

# 5. Optional GUI: login m7-qa@localhost.dev / CorrectHorse123!, /insights without mock mode
```

## Expected API outcomes (seeded user)

| Endpoint                                                  | Pass criteria                                                      |
| --------------------------------------------------------- | ------------------------------------------------------------------ |
| `POST /api/v1/auth/login`                                 | 200 + `access_token`                                               |
| `GET /api/v1/insights/latest`                             | `symptom_cluster` in insights; `insight_maturity.phase` = `robust` |
| `GET /api/v1/insights/tag-clusters`                       | `status: "ok"`, ≥ 1 cluster                                        |
| `GET /api/v1/insights/symptom-tag-cooccurrence?range=90d` | ≥ 1 cell                                                           |

## Sprint 5 checklist

- [x] ADR-0025 accepted
- [x] Deterministic QA seed
- [x] Integration tests + CI wiring
- [x] API verification script
- [x] Quality gate document
- [x] GitHub #144 / #145 closed
- [x] Full-stack analytics path validated (automated)

**Sprint 5 status: Done.**

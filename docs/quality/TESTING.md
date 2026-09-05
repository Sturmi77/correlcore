# CorrelCore — Testing Strategy

**Living document.** Last updated: 2026-09-05.

Canonical test / CI strategy for CorrelCore. Operational commands live in
[`docs/DEVELOPMENT.md`](../DEVELOPMENT.md) and [`AGENTS.md`](../../AGENTS.md).
Product Definition of Done: [`DESIGN_DOCUMENT.md` §9](../DESIGN_DOCUMENT.md).

Milestone `*_QUALITY_GATE.md` files under this folder are **Historical**
closeout records, not the living strategy.

---

## Pyramid

| Layer                | What                                                                                                                       | When                                        |
| -------------------- | -------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------- |
| **Unit**             | Backend `pytest` (mocked DB/Redis); Web Vitest                                                                             | Every PR (path-filtered)                    |
| **Contract / style** | OpenAPI→TS (`ci-contract.yml`), `apiContract.ts`, contrast/style/token guards                                              | Every PR touching those paths               |
| **Integration**      | `pytest -m integration` against real Postgres (pgvector) + Redis                                                           | Every API PR (`ci-api.yml` integration job) |
| **E2E (Playwright)** | Mocked API smoke (+ a11y) on PR; mobile / journeys / GDPR nightly                                                          | PR smoke; nightly expanded                  |
| **Security**         | gitleaks, pip-audit, pnpm audit (gating); CodeQL / Trivy / ZAP (report; CRITICAL gate deferred until image baseline clean) | Push/PR / schedule                          |
| **Manual / device**  | Capacitor, Health Connect, widgets, FCM, Play Pre-Launch                                                                   | Milestone / device QA — not CI              |

---

## Coverage floors

| Surface                               | Gate                                                           | Location                                |
| ------------------------------------- | -------------------------------------------------------------- | --------------------------------------- |
| Backend `app`                         | `--cov-fail-under=70`                                          | `backend/pyproject.toml`, `ci-api.yml`  |
| Critical paths (auth / crypto / sync) | Target ≥85 % (report in CQR; not a separate CI fail-under yet) | Design-Doc §9 CQR                       |
| Web `src/lib/api` + `src/lib/offline` | Vitest thresholds                                              | `apps/web/vite.config.ts`, coverage job |

Raise floors as coverage grows; do not lower them to land a change.

---

## What CI must green on a PR

- Lint / format / typecheck (web + API as touched)
- Unit tests + coverage floors
- Contract drift check when backend / `packages/api-types` / FE contracts / `lib/api` change
- Integration job when `backend/**` changes (`CORRELCORE_RUN_INTEGRATION=1`)
- Playwright smoke (mocked API) when web changes
- Security: gitleaks + dependency audit

**Not required on every PR:** staging manual verify, full mobile/journeys/GDPR Playwright, real-API browser happy path, authenticated DAST, external pentest, device QA.

Recommended required status checks:

- `CI — Web`, `CI — API`, `CI — API contract`, `CI - Security`, `CI — Docs Site` (as applicable)

---

## Real-API browser E2E — deferred

Compensating layers: Playwright smoke (mocked API) + API health/migrations/integration against real Postgres/Redis. Nightly expands mobile/journeys/GDPR. Revisit with a shared multi-service harness.

---

## Out of CI (explicit)

- Play Store Pre-Launch / device lab, Health Connect, widgets, FCM
- Independent external pentest (#782)
- Lighthouse / Web Vitals — **target**, not an existing CI job
- `apps/web-react` until package scaffold exists
- Mutation testing, property-based suites, load tests (pre-SaaS)

---

## Local commands

```powershell
.\scripts\local-quality.ps1
```

```bash
cd backend && uv run --python 3.12 pytest
export CORRELCORE_RUN_INTEGRATION=1
uv run --python 3.12 pytest -m integration -q --no-cov

pnpm --filter @correlcore/web test
pnpm --filter @correlcore/web test:coverage
pnpm --filter @correlcore/web test:e2e:smoke
```

Backend notes: [`backend/tests/README.md`](../../backend/tests/README.md).

---

## Related

- [`DEVELOPMENT.md`](../DEVELOPMENT.md) · [`M9_PENTEST.md`](M9_PENTEST.md) ·
  [`SECURITY_MAINTAINABILITY_AUDIT_2026-07-16.md`](SECURITY_MAINTAINABILITY_AUDIT_2026-07-16.md)

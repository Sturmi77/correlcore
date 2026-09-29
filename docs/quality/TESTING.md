# CorrelCore — Testing Strategy

**Living document.** Last updated: 2026-09-23.

Canonical test / CI strategy for CorrelCore. Operational commands live in
[`docs/DEVELOPMENT.md`](../DEVELOPMENT.md) and [`AGENTS.md`](../../AGENTS.md).
Product Definition of Done: [`DESIGN_DOCUMENT.md` §9](../DESIGN_DOCUMENT.md).

Milestone `*_QUALITY_GATE.md` files under this folder are **Historical**
closeout records, not the living strategy.

---

## Pyramid

| Layer                | What                                                                                                                                | When                                        |
| -------------------- | ----------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------- |
| **Unit**             | Backend `pytest` (mocked DB/Redis); Web Vitest                                                                                      | Every PR (path-filtered)                    |
| **Contract / style** | OpenAPI→TS (`ci-contract.yml`), `apiContract.ts`, contrast/style/token guards                                                       | Every PR touching those paths               |
| **Integration**      | `pytest -m integration` against real Postgres (pgvector) + Redis                                                                    | Every API PR (`ci-api.yml` integration job) |
| **E2E (Playwright)** | Mocked API smoke (+ a11y) on PR; mobile / journeys / GDPR nightly                                                                   | PR smoke; nightly expanded                  |
| **Security**         | gitleaks, dependency audits, CRITICAL image gate, ZAP findings gate; A10 also scans exact release digests and authenticated staging | Push/PR/schedule; release candidate         |
| **Manual / device**  | Capacitor, Health Connect, widgets, FCM, Play Pre-Launch                                                                            | Milestone / device QA — not CI              |

---

## Coverage floors

| Surface                                              | Gate                                                                 | Location                                |
| ---------------------------------------------------- | -------------------------------------------------------------------- | --------------------------------------- |
| Backend `app`                                        | `--cov-fail-under=70`                                                | `backend/pyproject.toml`, `ci-api.yml`  |
| Critical paths (auth / scoped DEK / insight compute) | ≥85% in the A10 release gate; sync uses the real-DB integration gate | `audit-a10-release-evidence.yml`        |
| Web `src/lib/api` + `src/lib/offline`                | Vitest thresholds                                                    | `apps/web/vite.config.ts`, coverage job |

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

## Real-API release-candidate E2E

PR Playwright remains a fast mocked-API gate. Before release, the A10 workflow
runs a two-user journey against an isolated, proxy-fronted staging stack and
binds its result to the exact commit and API/web image digests. See
[`A10_RELEASE_EVIDENCE.md`](audit-2026-09-22/A10_RELEASE_EVIDENCE.md).

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

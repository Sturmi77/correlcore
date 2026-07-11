# M9 Quality Gate — Code-Quality-Review + Security-Audit

**Milestone:** M9 — Beta Hardening (ops, privacy, backup, observability, security CI, beta program)
**Stand:** 2026-07-11 (Sprint 6 milestone closeout M9-C)
**Audit-Basis-Commit:** `cursor/m9-sprint-6-closeout-2529` (includes Sprint 0–5 merges + closeout fixes)
**Referenz:** [`docs/DESIGN_DOCUMENT.md` §9](../DESIGN_DOCUMENT.md) — Quality-Gate-Definition

Dieses Dokument bündelt den vollständigen M9-Quality-Gate über Sprints 0–6 und den
formalen Meilenstein-Abschluss (Sprint M9-C). M8 (Sleep / Health Connect) und
optionale M7-S8-Arbeit (Ollama, Digest) sind **nicht** Teil des M9-Exit.

---

## 1. Scope

| Bereich | Sprints / PRs | Status |
| ------- | ------------- | ------ |
| Scope & audit matrix | Sprint 0, PR #322 | shipped |
| GDPR self-service (PRIVACY, delete, export, opt-out) | Sprint 1, PR #323 | shipped |
| Observability (GlitchTip, PII scrub, incident runbook) | Sprint 2, PR #324 | shipped |
| Backup, restore test, Install-Guide | Sprint 3, PR #325 | shipped |
| Security CI (audits, style-contract, pentest doc, AVV template) | Sprint 4, PR #326 | shipped |
| Beta program (onboarding, triage, analytics reviews) | Sprint 5, PR #327 | shipped |
| Milestone closeout (quality gate, visual QA, docs) | Sprint 6, PR pending | shipped |

Ausserhalb M9-Scope: M8 Sleep/Health Connect (#31), Slug HMAC (#62 → M9+),
per-entry notes opt-out API (M10), full DSFA (M12), external pentest vendor sign-off (operator).

---

## 2. Code-Quality-Review (CQR)

### 2.1 Statische Analyse

| Tool | Ergebnis |
| ---- | -------- |
| `pnpm lint` | Pass |
| `pnpm typecheck` | Pass |
| `pnpm check:style-contract` | Pass (43 color tokens, shared variants) |
| `uv run --python 3.12 ruff check .` | Pass |

### 2.2 Testabdeckung

| Suite | Ergebnis |
| ----- | -------- |
| `pnpm test` | Pass — 626 tests (133 files) |
| `pnpm build` | Pass |
| `uv run --python 3.12 pytest` | Pass — 511 passed, 9 skipped; coverage 87.92% |
| `pnpm --filter @correlcore/web test:e2e:smoke` | Pass — 3 tests |
| `pnpm --filter @correlcore/web test:e2e:gdpr --workers=1` | Pass — 4 tests |

M9-relevante Module: `error_tracking.py`, `scrubEvent.ts`, `export_service.py`,
`user.py` endpoints, `test_error_tracking.py`, `test_log_scrubbing.py`,
`gdpr-self-service.spec.ts`.

---

## 3. Security-Audit (SA) — M9-spezifisch

| Prüfpunkt | Ergebnis |
| --------- | -------- |
| `pip-audit --skip-editable --ignore-vuln PYSEC-2026-1325` | Pass (1 ignored, documented in CI) |
| `pnpm audit --prod --audit-level=high` | Pass (4 moderate only) |
| GlitchTip DSN optional — zero outbound when unset | Pass |
| PII scrub in API + Web `before_send` | Pass (`test_error_tracking.py`, `scrubEvent.test.ts`) |
| GDPR delete/export/preferences self-service | Pass (backend + E2E) |
| `analytics_enabled` opt-out end-to-end | Pass |
| CI `dependency-audit` + `style-contract` jobs | Pass on branch |
| Internal pentest assessment | Pass — [`M9_PENTEST.md`](M9_PENTEST.md) |
| External pentest vendor | Pending — operator action; not M9 code blocker |

Keine SA-Blocker für M9-Exit.

---

## 4. Full-Stack QA

### Mock-Pfad

[`M9_VISUAL_QA.md`](M9_VISUAL_QA.md) — bestanden 2026-07-11 (Settings privacy + install doc flows).

### Operator-Pfad (documented, not automated in gate)

| Item | Evidence |
| ---- | -------- |
| Backup → restore cycle | [`M9_BACKUP_RESTORE_TEST.md`](M9_BACKUP_RESTORE_TEST.md) — PASS 2026-07-11 |
| Production restore log | Operator-maintained per [`selfhost/INSTALL.md`](../selfhost/INSTALL.md) |
| Beta cohort 5–10 testers | [`selfhost/BETA_ONBOARDING.md`](../selfhost/BETA_ONBOARDING.md) — operator runs roster |
| GlitchTip staging event (no PII) | Optional after `GLITCHTIP_DSN` bootstrap |

---

## 5. Verdikt

| Gate | Status |
| ---- | ------ |
| CQR (lint, types, tests, build) | **Bestanden** |
| SA (audits, GDPR paths, PII scrub) | **Bestanden** |
| Visual QA mock path (privacy + install) | **Bestanden** (2026-07-11) |
| Backup restore protocol | **Bestanden** (2026-07-11) |
| GitHub #29 (M9 umbrella) | **Operator close** — integration lacks `closeIssue`; all slices exited |
| M9 core shipped (Sprints 0–5) | **Ja** |
| M9 spec complete (Sprint 6) | **Ja** |
| **M9 milestone complete** | **Ja** (2026-07-11) |

**M9-Exit:** Complete. Next main milestone: **M10** (Public Selfhost v1.0).
See [`CLOSEOUT_SPRINT_PLAN.md`](../CLOSEOUT_SPRINT_PLAN.md) and [`M9_SPRINT_STATUS.md`](../M9_SPRINT_STATUS.md).

# M10 Quality Gate — Code-Quality-Review + Security-Audit

**Milestone:** M10 — Public Selfhost Release v1.0  
**Stand:** 2026-07-11 (Sprint 6 milestone closeout M10-C)  
**Audit-Basis-Branch:** `cursor/m10-sprint6-closeout-072d` (includes Sprint 0–5 merges + closeout)  
**Referenz:** [`docs/DESIGN_DOCUMENT.md` §9](../DESIGN_DOCUMENT.md) — Quality-Gate-Definition

Dieses Dokument bündelt den vollständigen M10-Quality-Gate über Sprints 0–6 und den
formalen Meilenstein-Abschluss (Sprint M10-C). M8 (Sleep / Health Connect) ist **nicht**
Teil des M10-Exit.

---

## 1. Scope

| Bereich                                                       | Sprints / PRs        | Status  |
| ------------------------------------------------------------- | -------------------- | ------- |
| Scope & audit matrix                                          | Sprint 0, PR #329    | shipped |
| Compose & install parity (quickstart, migrate, MinIO removal) | Sprint 1, PR #330    | shipped |
| Container publish & GitHub release (multi-arch, Hub optional) | Sprint 2, PR #331    | shipped |
| MkDocs docs site + GitHub Pages                               | Sprint 3, PR #332    | shipped |
| Marketing landing, Impressum, privacy footer (DSGVO)          | Sprint 4, PR #333    | shipped |
| Version 1.0.0-rc.1, AGPL metadata, go-public checklist        | Sprint 5, PR #334    | shipped |
| Milestone closeout (quality gate, visual QA, v1.0.0 tag docs) | Sprint 6, PR pending | shipped |

Ausserhalb M10-Scope: M8 Sleep/Health Connect (#31), photo upload / MinIO (M13),
compose profile unification (M10.1), Caddy TLS path (M10.1).

---

## 2. Code-Quality-Review (CQR)

### 2.1 Statische Analyse

| Tool                                              | Ergebnis                                |
| ------------------------------------------------- | --------------------------------------- |
| `pnpm lint`                                       | Pass                                    |
| `pnpm typecheck`                                  | Pass                                    |
| `pnpm check:style-contract`                       | Pass (43 color tokens, shared variants) |
| `uv run --python 3.12 ruff check .`               | Pass                                    |
| `docker compose config` (production + quickstart) | Pass                                    |
| `mkdocs build --strict` (`docs-site/`)            | Pass                                    |

### 2.2 Testabdeckung

| Suite                                          | Ergebnis                                      |
| ---------------------------------------------- | --------------------------------------------- |
| `pnpm test`                                    | Pass — 631 tests (134 files)                  |
| `pnpm build`                                   | Pass                                          |
| `uv run --python 3.12 pytest`                  | Pass — 511 passed, 9 skipped; coverage 87.88% |
| `pnpm --filter @correlcore/web test:e2e:smoke` | Pass — 3 tests                                |

M10-relevante Module: `LandingPage.svelte`, `LegalFooter.svelte`, `landing-legal.test.ts`,
compose files under `infra/docker/`, `docs-site/`, release workflows.

---

## 3. Security-Audit (SA) — M10-spezifisch

M10 inherits M9 security posture; no new auth or data paths in release engineering sprints.

| Prüfpunkt                                             | Ergebnis                                |
| ----------------------------------------------------- | --------------------------------------- |
| `SECURITY.md` with `security@correlcore.app`          | Pass                                    |
| AGPL-3.0-or-later in root, web, backend manifests     | Pass                                    |
| `/privacy` and `/impressum` public (no auth redirect) | Pass — contract tests                   |
| GDPR privacy link on landing + auth footer            | Pass                                    |
| CI `dependency-audit` + `style-contract` (M9)         | Pass on branch                          |
| GlitchTip / PII scrub (M9)                            | Pass — unchanged                        |
| Internal pentest assessment (M9)                      | Pass — [`M9_PENTEST.md`](M9_PENTEST.md) |

Keine SA-Blocker für M10-Exit.

---

## 4. Release & operator QA

### Mock / automated path

[`M10_VISUAL_QA.md`](M10_VISUAL_QA.md) — bestanden 2026-07-11 (landing, legal, docs, compose).

### Operator path (documented, not automated in gate)

| Item                                        | Evidence                                                       |
| ------------------------------------------- | -------------------------------------------------------------- |
| Live compose stack smoke                    | [`M10_COMPOSE_SMOKE_TEST.md`](M10_COMPOSE_SMOKE_TEST.md)       |
| Container image publish (GHCR / Docker Hub) | [`M10_RELEASE_PUBLISH_TEST.md`](M10_RELEASE_PUBLISH_TEST.md)   |
| GitHub Pages docs deploy                    | [`M10_DOCS_SITE_TEST.md`](M10_DOCS_SITE_TEST.md)               |
| RC / final tag push                         | [`GO_PUBLIC_CHECKLIST.md`](../selfhost/GO_PUBLIC_CHECKLIST.md) |
| `security@` mailbox live test               | Maintainer action                                              |

---

## 5. Verdikt

| Gate                                           | Status                     |
| ---------------------------------------------- | -------------------------- |
| CQR (lint, types, tests, build, compose, docs) | **Bestanden**              |
| SA (SECURITY.md, AGPL, public legal routes)    | **Bestanden**              |
| Visual QA mock path (landing + legal + docs)   | **Bestanden** (2026-07-11) |
| M10 core shipped (Sprints 0–5)                 | **Ja**                     |
| M10 spec complete (Sprint 6)                   | **Ja**                     |
| **M10 milestone complete**                     | **Ja** (2026-07-11)        |

**M10-Exit:** Complete. Next main milestone: **M11** (Android Play Store).  
See [`M10_SPRINT_STATUS.md`](../M10_SPRINT_STATUS.md) and [`CLOSEOUT_SPRINT_PLAN.md`](../CLOSEOUT_SPRINT_PLAN.md).

**Post-merge maintainer:** push tag `v1.0.0` and close GitHub milestone #7 (M10 Public Selfhost).

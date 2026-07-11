# M10 Sprint Status — Public Selfhost Release v1.0

Last updated: 2026-07-11

Tracking document for [`docs/M10_SPRINT_PLAN.md`](M10_SPRINT_PLAN.md).

**Milestone completeness:** Sprints 0–6 complete (M10-C closeout 2026-07-11).

**Prerequisite:** M9 complete (2026-07-11) — [`docs/M9_SPRINT_STATUS.md`](M9_SPRINT_STATUS.md).

## Overview

| Sprint | Title                       | Status   |
| ------ | --------------------------- | -------- |
| 0      | Scope & audit               | Complete |
| 1      | Compose & install parity    | Complete |
| 2      | Container publish & release | Complete |
| 3      | Docs site                   | Complete |
| 4      | Landing & legal             | Complete |
| 5      | Version, AGPL & go-public   | Complete |
| 6      | Milestone closeout (M10-C)  | Complete |

## Acceptance-criteria audit matrix

Audit date: 2026-07-11. Method: codebase review, DESIGN_DOCUMENT § M10, gap
analysis vs M9 exit state.

| Criterion                         | Sprint | Code anchor                                                                       | Test / doc evidence                                                         | Gap                                      |
| --------------------------------- | ------ | --------------------------------------------------------------------------------- | --------------------------------------------------------------------------- | ---------------------------------------- |
| Docker Hub amd64 + arm64          | 2      | [`.github/workflows/release-images.yml`](../.github/workflows/release-images.yml) | Multi-arch CI + [`CONTAINER_IMAGES.md`](selfhost/CONTAINER_IMAGES.md)       | Live Hub push after secrets configured   |
| `docker compose up` minimal setup | 1      | [`infra/docker/`](../infra/docker/)                                               | Quickstart + bootstrap shipped                                              | Live stack smoke (operator)              |
| SECURITY.md                       | —      | [`SECURITY.md`](../SECURITY.md)                                                   | Present + security@ contact                                                 | Mailbox live test (maintainer)           |
| CHANGELOG v1.0.0                  | 5, 6   | [`CHANGELOG.md`](../CHANGELOG.md)                                                 | `[1.0.0]` section + Sprint 6 closeout                                       | Tag `v1.0.0` post-merge                  |
| Docs site live                    | 3      | [`docs-site/`](../docs-site/)                                                     | MkDocs + GitHub Pages workflow                                              | Live deploy post-merge                   |
| Landing + install/user docs       | 4      | [`LandingPage.svelte`](../apps/web/src/lib/components/landing/LandingPage.svelte) | Marketing landing + docs site install                                       | —                                        |
| Quality gate §9                   | 6      | [`M10_QUALITY_GATE.md`](quality/M10_QUALITY_GATE.md)                              | CQR + SA PASS 2026-07-11                                                    | —                                        |
| Privacy link on landing (DSGVO)   | 4      | [`LegalFooter.svelte`](../apps/web/src/lib/components/common/LegalFooter.svelte)  | Landing + auth footer                                                       | —                                        |
| Impressum (AT/DE)                 | 4      | [`impressum/+page.svelte`](../apps/web/src/routes/impressum/+page.svelte)         | TMG/ECG template page                                                       | Operator-specific details                |
| GitHub release v1.0.0             | 2, 6   | [`.github/workflows/github-release.yml`](../.github/workflows/github-release.yml) | Final tag documented in GO_PUBLIC_CHECKLIST                                 | Tag `v1.0.0` post-merge                  |

## Compose decisions (Sprint 0)

Planning outcome: **D + E + F + B** for M10 Sprint 1; **A, C, G-compose → M10.1**.

### Nutzen vs. Risiko

| ID  | Proposal              | Breaks running deploys?   | M10 fit |
| --- | --------------------- | ------------------------- | ------- |
| A   | Profile single stack  | Yes (worker/tls implicit) | M10.1   |
| B   | Remove MinIO          | No (functional)           | **M10** |
| C   | Traefik → Caddy       | Yes                       | M10.1   |
| D   | Two compose paths     | No                        | **M10** |
| E   | Bootstrap + quick env | No                        | **M10** |
| F   | YAML-DRY + migrate    | No                        | **M10** |
| G   | External proxy        | No (docs only)            | Partial |

### MinIO removal analysis (approved for M10)

| Check                    | Result                                                     |
| ------------------------ | ---------------------------------------------------------- |
| Photo upload             | Not implemented — **M13** ([`M13_NOTES.md`](M13_NOTES.md)) |
| `/health/ready`          | Postgres, Redis, encryption only — **no MinIO**            |
| Quickstart without MinIO | Running since M9 (user-test / dockhand compose)            |
| App code                 | Dev-View probe only (`DEV_VIEW_ENABLED`)                   |
| Production blocker       | `api.depends_on.minio` removed in Sprint 1                 |
| User-visible impact      | None (Dev-View shows `minio_connected: false` if enabled)  |
| M13 re-add               | `--profile storage` or compose overlay                     |

### COMPOSE_PROFILES matrix

See [`M10_SPRINT_PLAN.md`](M10_SPRINT_PLAN.md) § COMPOSE_PROFILES matrix and
[`selfhost/M10_COMPOSE_UPGRADE.md`](selfhost/M10_COMPOSE_UPGRADE.md).

## Sprint 0 — Completed checklist

- [x] [`M10_SPRINT_PLAN.md`](M10_SPRINT_PLAN.md) created.
- [x] [`M10_SPRINT_STATUS.md`](M10_SPRINT_STATUS.md) created with audit matrix.
- [x] Compose simplification options A–G evaluated; M10 vs M10.1 decision recorded.
- [x] MinIO removal approved (M13 deferral).
- [x] Non-breaking premise documented (worker + traefik always-on in M10).
- [x] Operator upgrade guide [`selfhost/M10_COMPOSE_UPGRADE.md`](selfhost/M10_COMPOSE_UPGRADE.md).
- [ ] GitHub milestone #7 populated with issues.
- [ ] Beta P2 backlog triaged to `m10` label.

## Sprint 1 — Completed checklist

- [x] Production compose: `migrate`, YAML anchors, `FRONTEND_BASE_URL`, MinIO removed.
- [x] [`docker-compose.quickstart.yml`](../infra/docker/docker-compose.quickstart.yml).
- [x] [`scripts/bootstrap-selfhost-env.sh`](../scripts/bootstrap-selfhost-env.sh) + `.env.quickstart.example`.
- [x] [`INSTALL.md`](selfhost/INSTALL.md) restructured (Path B first, external proxy section).
- [x] [`.env.example`](../infra/docker/.env.example) MinIO section commented (M13 note).
- [x] [`quality/M10_COMPOSE_SMOKE_TEST.md`](quality/M10_COMPOSE_SMOKE_TEST.md).
- [x] `docker compose config` validated for both compose files.

## Sprint 2 — Completed checklist

- [x] Multi-arch (`linux/amd64`, `linux/arm64`) in [`release-images.yml`](../.github/workflows/release-images.yml).
- [x] Docker Hub publish (conditional on `DOCKERHUB_USERNAME` / `DOCKERHUB_TOKEN` secrets).
- [x] [`github-release.yml`](../.github/workflows/github-release.yml) on `v*` tags with CHANGELOG extraction.
- [x] `IMAGE_REGISTRY` in production, quickstart, user-test, dockhand, dockge compose.
- [x] [`selfhost/CONTAINER_IMAGES.md`](selfhost/CONTAINER_IMAGES.md) operator/maintainer guide.
- [x] [`quality/M10_RELEASE_PUBLISH_TEST.md`](quality/M10_RELEASE_PUBLISH_TEST.md).

## Sprint 3 — Completed checklist

- [x] MkDocs Material site under [`docs-site/`](../docs-site/).
- [x] Pages: install, container images, upgrade, user guide, API overview, privacy.
- [x] CI: [`ci-docs-site.yml`](../.github/workflows/ci-docs-site.yml) (`mkdocs build --strict`).
- [x] Deploy: [`deploy-docs-site.yml`](../.github/workflows/deploy-docs-site.yml) (GitHub Pages).
- [x] [`quality/M10_DOCS_SITE_TEST.md`](quality/M10_DOCS_SITE_TEST.md).

## Sprint 4 — Completed checklist

- [x] Marketing [`LandingPage.svelte`](../apps/web/src/lib/components/landing/LandingPage.svelte) replaces pre-alpha anonymous home.
- [x] [`/impressum`](../apps/web/src/routes/impressum/+page.svelte) with AT/DE legal template (i18n EN/DE).
- [x] [`LegalFooter.svelte`](../apps/web/src/lib/components/common/LegalFooter.svelte) on landing, privacy, impressum.
- [x] `/privacy` and `/impressum` public routes (no auth redirect).
- [x] Privacy + Impressum links on auth layout footer.
- [x] [`quality/M10_LANDING_LEGAL_TEST.md`](quality/M10_LANDING_LEGAL_TEST.md).

## Sprint 5 — Completed checklist

- [x] CHANGELOG [`[1.0.0]`](../CHANGELOG.md) section (since `0.6.0` + M10 highlights).
- [x] AGPL-3.0-or-later in root, web, and backend package manifests.
- [x] Version `1.0.0-rc.1` in manifests and i18n `app.version`.
- [x] [`selfhost/GO_PUBLIC_CHECKLIST.md`](selfhost/GO_PUBLIC_CHECKLIST.md) (branch protection, visibility, rc tag).
- [x] [`SECURITY.md`](../SECURITY.md) updated with `1.0.x` support + security@ contact.
- [x] [`quality/M10_VERSION_RC_TEST.md`](quality/M10_VERSION_RC_TEST.md).
- [ ] Tag `v1.0.0-rc.1` pushed (post-merge to `main`; optional if skipping rc).

## Sprint 6 — Completed checklist (M10-C)

- [x] [`quality/M10_QUALITY_GATE.md`](quality/M10_QUALITY_GATE.md) — CQR + SA PASS (2026-07-11).
- [x] [`quality/M10_VISUAL_QA.md`](quality/M10_VISUAL_QA.md) — landing, legal, docs, compose.
- [x] Version **`1.0.0`** in root, web, backend manifests and i18n `app.version`.
- [x] Landing i18n copy fix — no-gamification guard (`noGamificationCopy.test.ts`).
- [x] `CHANGELOG.md`, `README.md`, `DESIGN_DOCUMENT.md` M10 exit checkboxes updated.
- [ ] Tag **`v1.0.0`** pushed (post-merge to `main`).
- [ ] GitHub milestone #7 (M10 Public Selfhost) closed (maintainer).

## Next milestone

**M11** — Android Play Store (Capacitor). See [`DESIGN_DOCUMENT.md`](DESIGN_DOCUMENT.md) § M11.

## API usage note

Same constraints as M9: no new cloud APIs, no new REST endpoints unless audit
proves a gap. Release engineering (Docker Hub, GitHub releases) only.

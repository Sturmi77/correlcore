# M10 Sprint Status — Public Selfhost Release v1.0

Last updated: 2026-07-11

Tracking document for [`docs/M10_SPRINT_PLAN.md`](M10_SPRINT_PLAN.md).

**Milestone completeness:** Sprints 0–2 implemented; Sprint 3 (docs site) next.

**Prerequisite:** M9 complete (2026-07-11) — [`docs/M9_SPRINT_STATUS.md`](M9_SPRINT_STATUS.md).

## Overview

| Sprint | Title                       | Status   |
| ------ | --------------------------- | -------- |
| 0      | Scope & audit               | Complete |
| 1      | Compose & install parity    | Complete |
| 2      | Container publish & release | Complete |
| 3      | Docs site                   | Pending  |
| 4      | Landing & legal             | Pending  |
| 5      | Version, AGPL & go-public   | Pending  |
| 6      | Milestone closeout (M10-C)  | Pending  |

## Acceptance-criteria audit matrix

Audit date: 2026-07-11. Method: codebase review, DESIGN_DOCUMENT § M10, gap
analysis vs M9 exit state.

| Criterion                         | Sprint | Code anchor                                                                       | Test / doc evidence                                                   | Gap                                    |
| --------------------------------- | ------ | --------------------------------------------------------------------------------- | --------------------------------------------------------------------- | -------------------------------------- |
| Docker Hub amd64 + arm64          | 2      | [`.github/workflows/release-images.yml`](../.github/workflows/release-images.yml) | Multi-arch CI + [`CONTAINER_IMAGES.md`](selfhost/CONTAINER_IMAGES.md) | Live Hub push after secrets configured |
| `docker compose up` minimal setup | 1      | [`infra/docker/`](../infra/docker/)                                               | Quickstart + bootstrap shipped                                        | Live stack smoke (operator)            |
| SECURITY.md                       | —      | [`SECURITY.md`](../SECURITY.md)                                                   | Present                                                               | —                                      |
| CHANGELOG v1.0.0                  | 5      | [`CHANGELOG.md`](../CHANGELOG.md)                                                 | `[Unreleased]` only; last tag `[0.6.0]`                               | Cut `[1.0.0]` at release               |
| Docs site live                    | 3      | —                                                                                 | Repo markdown only                                                    | MkDocs site                            |
| Landing + install/user docs       | 3–4    | [`apps/web/src/routes/+page.svelte`](../apps/web/src/routes/+page.svelte)         | Pre-alpha badge; `/privacy` in-app only                               | Landing, Impressum                     |
| Quality gate §9                   | 6      | —                                                                                 | M9 gate as template                                                   | `M10_QUALITY_GATE.md`                  |
| Privacy link on landing (DSGVO)   | 4      | [`privacy/+page.svelte`](../apps/web/src/routes/privacy/+page.svelte)             | In-app only                                                           | Landing footer                         |
| Impressum (AT/DE)                 | 4      | —                                                                                 | Missing                                                               | `/impressum` route                     |
| GitHub release v1.0.0             | 2, 6   | [`.github/workflows/github-release.yml`](../.github/workflows/github-release.yml) | Workflow on `v*` tags; needs first tag post-merge                     | Tag `v1.0.0` at Sprint 6               |

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

## Next milestone

**M10 Sprint 3** — MkDocs docs site (install + user guide + API overview).

## API usage note

Same constraints as M9: no new cloud APIs, no new REST endpoints unless audit
proves a gap. Release engineering (Docker Hub, GitHub releases) only.

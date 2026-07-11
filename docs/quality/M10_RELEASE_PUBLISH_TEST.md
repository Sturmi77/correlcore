# M10 Release Publish Test Protocol

Last updated: 2026-07-11  
Sprint: M10-S2 (Container publish & release)  
Reference: [`docs/selfhost/CONTAINER_IMAGES.md`](../selfhost/CONTAINER_IMAGES.md)

## Objective

Verify Sprint 2 release engineering: multi-arch image builds, optional Docker Hub
mirror, GitHub Release on version tags, and `IMAGE_REGISTRY` compose override.

## Scope

| In scope                         | Out of scope                    |
| -------------------------------- | ------------------------------- |
| Workflow YAML review             | Live Docker Hub account setup   |
| Multi-arch `platforms` in CI     | Sprint 5 CHANGELOG `[1.0.0]` cut |
| GitHub Release workflow on `v*`  | MkDocs site (Sprint 3)          |
| Compose `IMAGE_REGISTRY` default | Full VPS deploy regression      |

## Static checks (CI / maintainer)

### release-images.yml

- [x] `platforms: linux/amd64,linux/arm64` on build-push steps
- [x] GHCR login + push (existing behaviour)
- [x] Docker Hub login conditional on `DOCKERHUB_*` secrets
- [x] Same tag set applied to both registries when Hub secrets present
- [x] Matrix build for `correlcore-api` and `correlcore-web`

### github-release.yml

- [x] Triggers on `push.tags: v*`
- [x] Extracts matching `CHANGELOG.md` section when present
- [x] Marks pre-releases when tag contains `-` (e.g. `v1.0.0-rc.1`)

### Compose

- [x] `${IMAGE_REGISTRY:-ghcr.io/sturmi77}` in production + quickstart compose
- [x] `.env.example` documents `IMAGE_REGISTRY`

## Post-merge verification (maintainer)

After merging to `main`:

```bash
# 1. Confirm workflow ran on main push (Actions tab)
# 2. Inspect multi-arch manifest
docker buildx imagetools inspect ghcr.io/sturmi77/correlcore-api:latest
docker buildx imagetools inspect ghcr.io/sturmi77/correlcore-web:latest
# Expected platforms: linux/amd64, linux/arm64
```

After configuring `DOCKERHUB_USERNAME` + `DOCKERHUB_TOKEN` and re-running workflow:

```bash
docker buildx imagetools inspect docker.io/<username>/correlcore-api:latest
```

After pushing a test tag (e.g. `v0.6.1-test` on a fork or pre-release):

```bash
git tag v0.6.1-test && git push origin v0.6.1-test
# Verify: GitHub Release created, release-images.yml ran, images tagged v0.6.1-test
```

## Compose registry override smoke

```bash
cd infra/docker
export IMAGE_REGISTRY=docker.io/sturmi77 IMAGE_TAG=latest
docker compose -f docker-compose.quickstart.yml config | grep 'image:'
# Expected: docker.io/sturmi77/correlcore-api:latest and correlcore-web:latest
```

Default (no override):

```bash
docker compose -f docker-compose.quickstart.yml config | grep 'image:'
# Expected: ghcr.io/sturmi77/correlcore-api:latest
```

## Sign-off

| Check                    | Status  | Date       |
| ------------------------ | ------- | ---------- |
| Workflow static review   | PASS    | 2026-07-11 |
| Compose config override  | PASS    | 2026-07-11 |
| Live GHCR multi-arch     | Pending | post-merge |
| Live Docker Hub push     | Pending | secrets + re-run |
| Live GitHub Release      | Pending | first `v*` tag after merge |

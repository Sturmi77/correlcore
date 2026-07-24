# Container Images

Last updated: 2026-07-19 (M10 Sprint 2; 1.0.x patch line)

Published images for selfhost deployments. Both **api** and **web** ship as
multi-arch manifests (`linux/amd64`, `linux/arm64`).

**Related:** [Install overview](index.md)

---

## Registries

| Registry       | Image names                                             | Default in compose     |
| -------------- | ------------------------------------------------------- | ---------------------- |
| **GHCR**       | `ghcr.io/sturmi77/correlcore-api`, `correlcore-web`     | Yes (`IMAGE_REGISTRY`) |
| **Docker Hub** | `docker.io/<username>/correlcore-api`, `correlcore-web` | Opt-in via `.env`      |

Replace `<username>` with the maintainer Docker Hub account configured in CI
(`DOCKERHUB_USERNAME` secret).

---

## Tags

Built by
[`release-images.yml`](https://github.com/Sturmi77/correlcore/blob/main/.github/workflows/release-images.yml):

| Trigger                   | Tags applied (both images)              |
| ------------------------- | --------------------------------------- |
| Push to `main`            | `:latest`, `:main`, `:sha-<short>`      |
| Tag `v1.0.0`              | `:v1.0.0`, `:v1.0`, `:latest`           |
| Tag `v1.1.1` (any `v1.x`) | `:v1.1.1`, `:v1.1` (semver minor alias) |
| `workflow_dispatch`       | Same rules for current ref context      |

Pin production deploys to an immutable tag (any **`v1.0.x`** pin works on the 1.0 line):

```env
IMAGE_TAG=v1.1.1
# or another patch, e.g. IMAGE_TAG=v1.0.3
# or
IMAGE_TAG=sha-abc1234
```

Optional digest pin (dev view / audit):

```bash
docker inspect "${IMAGE_REGISTRY:-ghcr.io/sturmi77}/correlcore-api:${IMAGE_TAG}" \
  --format='{{index .RepoDigests 0}}'
```

Set `IMAGE_DIGEST` in `.env` for the API container.

---

## Compose registry override

All official compose files support `IMAGE_REGISTRY`:

```env
# Default (GHCR)
IMAGE_REGISTRY=ghcr.io/sturmi77

# Docker Hub alternative
IMAGE_REGISTRY=docker.io/sturmi77
```

Images resolve as `${IMAGE_REGISTRY}/correlcore-api:${IMAGE_TAG}` and
`${IMAGE_REGISTRY}/correlcore-web:${IMAGE_TAG}`.

---

## Maintainer setup (CI)

### GHCR

Enabled by default with `GITHUB_TOKEN` (`packages: write` permission in workflow).

Make packages public: GitHub → Packages → correlcore-api / correlcore-web →
Package settings → Change visibility.

### Docker Hub

1. Create repositories `correlcore-api` and `correlcore-web` on Docker Hub.
2. Generate a read/write access token.
3. Add repository secrets:
   - `DOCKERHUB_USERNAME`
   - `DOCKERHUB_TOKEN`

When secrets are set, `release-images.yml` pushes the same tags to Docker Hub
on every main/tag build. When unset, GHCR-only publish continues.

### GitHub Release

[`github-release.yml`](https://github.com/Sturmi77/correlcore/blob/main/.github/workflows/github-release.yml)
creates a GitHub Release on every `v*` tag push. Release notes are taken from
the matching `## [x.y.z]` section in
[`CHANGELOG.md`](https://github.com/Sturmi77/correlcore/blob/main/CHANGELOG.md).

Pre-release tags (e.g. `v1.0.0-rc.1`) are marked as pre-releases automatically.

---

## Pull examples

```bash
# GHCR (default)
docker pull ghcr.io/sturmi77/correlcore-api:latest
docker pull ghcr.io/sturmi77/correlcore-web:latest

# Docker Hub (after Sprint 2 publish)
docker pull sturmi77/correlcore-api:latest
docker pull sturmi77/correlcore-web:latest

# Verify multi-arch manifest
docker buildx imagetools inspect ghcr.io/sturmi77/correlcore-api:latest
```

Expected platforms: `linux/amd64`, `linux/arm64`.

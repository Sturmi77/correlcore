# CorrelCore — Container Images

Last updated: 2026-07-19 (M10 Sprint 2; 1.0.x patch line)

Published images for selfhost deployments. Both **api** and **web** ship as
multi-arch manifests (`linux/amd64`, `linux/arm64`).

**Related:** [`INSTALL.md`](INSTALL.md) · [`M10_SPRINT_PLAN.md`](../M10_SPRINT_PLAN.md)

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

Built by [`.github/workflows/release-images.yml`](../../.github/workflows/release-images.yml):

| Trigger                   | Tags applied (both images)              |
| ------------------------- | --------------------------------------- |
| Push to `main`            | `:latest`, `:main`, `:sha-<short>`      |
| Tag `v1.0.0`              | `:v1.0.0`, `:v1.0`, `:latest`           |
| Tag `v1.7.1` (any `v1.x`) | `:v1.7.1`, `:v1.7` (semver minor alias) |
| `workflow_dispatch`       | Same rules for current ref context      |

Pin production deploys to an immutable tag (any **`v1.x`** pin works on the 1.x line):

```env
IMAGE_TAG=v1.7.1
# or another patch, e.g. IMAGE_TAG=v1.4.0
# or
IMAGE_TAG=sha-abc1234
```

Optional digest pin (dev view / audit):

```bash
docker inspect "${IMAGE_REGISTRY:-ghcr.io/sturmi77}/correlcore-api:${IMAGE_TAG}" \
  --format='{{index .RepoDigests 0}}'
```

Set `IMAGE_DIGEST` in `.env` for the API container.

### Verify what is actually running

`APP_VERSION` in JSON alone is not enough (often stays `1.0.0` across
patches). After deploy, check build identity via the web proxy:

```bash
curl -sS http://127.0.0.1:${WEB_HOST_PORT:-3010}/api/v1/health/live | jq .
# expect: image_tag, git_commit, cookie_secure, app_env
docker ps --format '{{.Names}} {{.Image}}' | grep correlcore
```

If testers report a bug that is already fixed on `main`, compare
`image_tag` / `git_commit` to the fixing commit before re-debugging code.

### Auth 401 checklist (`Could not validate credentials`)

Applies to **any** protected route (Trends, Settings → Consent /
`/api/v1/user/me/consents`, Entries, …) — not only the old Trends path bug.

1. **Running image** — `docker ps | grep correlcore` and
   `curl -sS http://127.0.0.1:${WEB_HOST_PORT:-3010}/api/v1/health/live`.
2. **Browser cookies after login** (DevTools → Application → Cookies for the
   web origin): `access_token` (`Path=/api`) and `refresh_token`
   (`Path=/api/v1/auth/refresh`). If missing → session never stuck (proxy /
   Secure). Login JSON alone is not enough.
3. **Network tab on the failing call** — Request must send `Cookie:
access_token=…`. Response header `X-Auth-Fail-Reason` (staging/homelab):
   `missing_access_token` | `jwt_invalid_or_expired` | `dek_unwrap_failed` | …
4. **`COOKIE_SECURE` in the API container** — must be `false` on plain HTTP:
   `docker exec correlcore-api env | grep COOKIE_SECURE`.
5. **`dek_unwrap_failed`** — `ENCRYPTION_KEY` no longer matches keys that
   wrapped user DEKs (key rotated without `ENCRYPTION_KEYS`). Restore the
   previous key or list both: `ENCRYPTION_KEYS=<new>,<old>`.
6. **Capacitor** — absolute `VITE_API_BASE_URL`, mixed content on `http://` API,
   Bearer refresh with `?include_access_token=true`.

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

[`.github/workflows/github-release.yml`](../../.github/workflows/github-release.yml)
creates a GitHub Release on every `v*` tag push. Release notes are taken from
the matching `## [x.y.z]` section in [`CHANGELOG.md`](../../CHANGELOG.md).

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

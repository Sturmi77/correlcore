# Renaming to CorrelCore

MoodSync has been renamed to CorrelCore. The rename is intentionally broad and touches product branding, package names, container images, Compose resources, export filenames and collaboration documentation.

## New Canonical Names

| Area                    | New Name                          |
| ----------------------- | --------------------------------- |
| Product display name    | `CorrelCore`                      |
| Technical slug          | `correlcore`                      |
| Web package             | `@correlcore/web`                 |
| Backend package         | `correlcore-backend`              |
| API image               | `ghcr.io/sturmi77/correlcore-api` |
| Web image               | `ghcr.io/sturmi77/correlcore-web` |
| Default stack name      | `correlcore`                      |
| Default export filename | `correlcore-export-YYYY-MM-DD.*`  |

## Compatibility Notes

- The old deterministic symptom UUID namespace is preserved as `moodsync.symptom.<slug>`. Changing it would alter seeded default IDs and could break existing entry-symptom references.
- The web theme preference migrates from `moodsync-theme` to `correlcore-theme` on first load.
- Export JSON uses the neutral `app_version` field and `format_version: "1.2"`.
- The GitHub repository may still be reachable through old redirects after a repository rename, but documentation now points to the intended `Sturmi77/correlcore` path.

## Existing Deployment Upgrade

The new Compose defaults use `correlcore_*` names for containers, networks and named volumes. If an existing deployment already has data in `moodsync_*` volumes, do not deploy blindly with the new defaults unless you intentionally want a fresh empty database.

Recommended upgrade path:

1. Stop the existing stack.
2. Take a database backup from the old deployment.
3. Deploy the new CorrelCore stack with the new image names.
4. Restore the database into the new Postgres volume.
5. Set `IMAGE_TAG` to a pinned `sha-<short>` tag once the new GHCR images exist.
6. Confirm `/dev` shows the expected Git commit, image tag and optional image digest.

Temporary compatibility option:

- Keep existing database credentials by setting `POSTGRES_DB` and `POSTGRES_USER` explicitly in `.env`.
- Keep old named volumes only if you also keep the old Compose volume names locally. This is a short transition path, not the new default.

## GHCR and Release Workflow

`release-images.yml` publishes multi-arch (`linux/amd64`, `linux/arm64`) images to:

**GHCR (default):**

- `ghcr.io/sturmi77/correlcore-api:latest`
- `ghcr.io/sturmi77/correlcore-api:main`
- `ghcr.io/sturmi77/correlcore-api:sha-<short>`
- `ghcr.io/sturmi77/correlcore-web:latest`
- `ghcr.io/sturmi77/correlcore-web:main`
- `ghcr.io/sturmi77/correlcore-web:sha-<short>`

**Docker Hub (M10 Sprint 2, when CI secrets configured):**

- `docker.io/<username>/correlcore-api` (same tags)
- `docker.io/<username>/correlcore-web` (same tags)

Compose override: `IMAGE_REGISTRY=ghcr.io/sturmi77` (default) or `docker.io/<username>`.
See [`selfhost/CONTAINER_IMAGES.md`](selfhost/CONTAINER_IMAGES.md).

Existing deployments that still reference `moodsync-api` or `moodsync-web` should be updated to the new image names during the same maintenance window.

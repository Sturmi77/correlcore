# CorrelCore — Go-Public Checklist (M10 Sprint 5)

Last updated: 2026-07-20

**Historical M10 go-public checklist.** CorrelCore **v1.0.0** shipped 2026-07-11; the
current release line is **1.0.x** (patch tags through `v1.0.7` with Android sideload APKs).
Use the [Post-1.0.x patch releases](#post-10x-patch-releases) section below for new patch tags.

Operator and maintainer checklist before making the repository **public** and
announcing **v1.0.0** (final tag in M10 Sprint 6).

**Related:** [`M10_SPRINT_PLAN.md`](../M10_SPRINT_PLAN.md) · [`SECURITY.md`](../SECURITY.md) ·
[`INSTALL.md`](INSTALL.md)

---

## Pre-flight (before `git push --tags` for rc/final)

| Step | Action                                                                           | Owner      |
| ---- | -------------------------------------------------------------------------------- | ---------- |
| 1    | CHANGELOG `[1.0.0]` section complete                                             | Maintainer |
| 2    | Package manifests show `1.0.0-rc.1` (rc) / `1.0.0` (final) + `AGPL-3.0-or-later` | Maintainer |
| 3    | `security@correlcore.app` mailbox monitored (72h SLA per SECURITY.md)            | Maintainer |
| 4    | GitHub Pages docs site live                                                      | CI         |
| 5    | Container images published (GHCR public; Docker Hub optional)                    | CI         |

---

## GitHub repository settings

When switching from private → **public**:

### Visibility

1. Settings → General → Danger Zone → **Change visibility** → Public
2. Confirm package visibility: Packages → correlcore-api / correlcore-web → **Public**

### Branch protection (`main`)

Recommended rules (Settings → Branches → Add rule for `main`):

| Rule                                | Setting                                                     |
| ----------------------------------- | ----------------------------------------------------------- |
| Require pull request before merging | ✅                                                          |
| Required approvals                  | ≥ 1                                                         |
| Require status checks               | ✅ `CI — Web`, `CI — API`, `CI — Docs Site` (as applicable) |
| Require branches up to date         | ✅                                                          |
| Include administrators              | optional (team preference)                                  |
| Restrict force pushes               | ✅                                                          |
| Restrict deletions                  | ✅                                                          |

Document any repo-specific exceptions in your team runbook.

### Security

- Settings → Security → **Private vulnerability reporting** enabled
- Dependabot alerts enabled (already in `ci-security.yml` scope)
- Secret scanning if available on your GitHub plan

---

## Package metadata

After go-public, remove `"private": true` from root [`package.json`](../../package.json) if the
monorepo should be npm-discoverable (optional — web package remains `@correlcore/web` private scope).

License field (Sprint 5):

```json
"license": "AGPL-3.0-or-later"
```

Backend: `license = { text = "AGPL-3.0-or-later" }` in `backend/pyproject.toml`.

---

## Release candidate tag (Sprint 5)

```bash
git tag -a v1.0.0-rc.1 -m "CorrelCore v1.0.0-rc.1 — public selfhost release candidate"
git push origin v1.0.0-rc.1
```

This triggers:

- [`release-images.yml`](../.github/workflows/release-images.yml) — image tags `v1.0.0-rc.1`, `v1.0.0`, `latest`
- [`github-release.yml`](../.github/workflows/github-release.yml) — GitHub Release (pre-release)

Verify images:

```bash
docker buildx imagetools inspect ghcr.io/sturmi77/correlcore-api:v1.0.0-rc.1
```

---

## Final release (Sprint 6)

After quality gate and visual QA PASS on `main`:

```bash
git pull origin main
git tag -a v1.0.0 -m "CorrelCore v1.0.0 — public selfhost release"
git push origin v1.0.0
```

This triggers:

- [`release-images.yml`](../.github/workflows/release-images.yml) — image tags `v1.0.0`, `latest`
- [`github-release.yml`](../.github/workflows/github-release.yml) — GitHub Release (non-prerelease)

Then close GitHub milestone #7 (M10 Public Selfhost).

Verify images:

```bash
docker buildx imagetools inspect ghcr.io/sturmi77/correlcore-api:v1.0.0
```

---

## Final release checklist (Sprint 6)

- ✅ Quality gate [`M10_QUALITY_GATE.md`](../quality/M10_QUALITY_GATE.md) — PASS (2026-07-11)
- ✅ Visual QA [`M10_VISUAL_QA.md`](../quality/M10_VISUAL_QA.md) — PASS (2026-07-11)
- ✅ Tag **`v1.0.0`** (non-prerelease) — published
- ✅ Close GitHub milestone #7 (M10 Public Selfhost) — closed with `v1.0.0` release

---

## Security contact verification

[`SECURITY.md`](../../SECURITY.md) lists **security@correlcore.app**.

Before announcing v1.0.0:

1. Send a test message to `security@correlcore.app` from an external mailbox
2. Confirm delivery and 72h response process
3. Update Impressum/operator contact if forwarding differs per instance

Selfhost operators use their own security contact for instance-specific issues; the project address is for **software vulnerabilities** in CorrelCore itself.

---

## Post-1.0.x patch releases

Checklist for tagging **`v1.0.N`** (e.g. `v1.0.7`) after the initial M10 go-public:

| Step | Action                                                                                                                                                       |
| ---- | ------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| 1    | Add `[1.0.N]` section to [`CHANGELOG.md`](../../CHANGELOG.md)                                                                                                |
| 2    | Bump manifests if project policy requires (root/web/backend `package.json`, i18n `app.version`)                                                              |
| 3    | Set operator pin: `IMAGE_TAG=v1.0.N` in `.env` (any `v1.0.x` pin works)                                                                                      |
| 4    | Tag and push: `git tag -a v1.0.N -m "CorrelCore v1.0.N"` → `git push origin v1.0.N`                                                                          |
| 5    | Verify CI: [`release-images.yml`](../../.github/workflows/release-images.yml) publishes `:v1.0.N`, `:v1.0`                                                   |
| 6    | Android sideload (if applicable): [`release-android.yml`](../../.github/workflows/release-android.yml) attaches `correlcore-1.0.N.apk` to the GitHub Release |
| 7    | Verify GHCR: `docker buildx imagetools inspect ghcr.io/sturmi77/correlcore-api:v1.0.N`                                                                       |

See [`CONTAINER_IMAGES.md`](CONTAINER_IMAGES.md) and [`ANDROID_SIDELOAD.md`](ANDROID_SIDELOAD.md) for operator and tester notes.

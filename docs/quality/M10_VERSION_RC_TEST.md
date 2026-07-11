# M10 Version & RC Tag Test Protocol

Last updated: 2026-07-11  
Sprint: M10-S5 (Version, AGPL & go-public)

## Objective

Verify Sprint 5 deliverables: CHANGELOG `[1.0.0]`, AGPL metadata, version alignment,
and release candidate tag readiness.

## Static checks

| Check | Expected | Status |
| ----- | -------- | ------ |
| CHANGELOG has `## [1.0.0]` | Yes | PASS |
| `[Unreleased]` empty or minimal | Yes | PASS |
| Root `package.json` `license` | `AGPL-3.0-or-later` | PASS |
| Root `package.json` `version` | `1.0.0-rc.1` | PASS |
| `@correlcore/web` version | `1.0.0-rc.1` | PASS |
| Backend `pyproject.toml` version | `1.0.0-rc.1` | PASS |
| `SECURITY.md` contact | `security@correlcore.app` | PASS |
| Go-public checklist doc | `docs/selfhost/GO_PUBLIC_CHECKLIST.md` | PASS |

## Tag procedure (maintainer)

After merge to `main`:

```bash
git pull origin main
git tag -a v1.0.0-rc.1 -m "CorrelCore v1.0.0-rc.1 — public selfhost release candidate"
git push origin v1.0.0-rc.1
```

Verify GitHub Release created (pre-release) and `release-images` workflow succeeded.

## Sign-off

| Step | Status | Date |
| ---- | ------ | ---- |
| Manifest / CHANGELOG review | PASS | 2026-07-11 |
| Tag `v1.0.0-rc.1` pushed | Pending | post-merge |
| security@ mailbox test | Pending | maintainer |

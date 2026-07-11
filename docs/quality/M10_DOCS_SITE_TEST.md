# M10 Docs Site Test Protocol

Last updated: 2026-07-11  
Sprint: M10-S3 (Docs site)  
Site URL: https://sturmi77.github.io/correlcore/

## Objective

Verify MkDocs Material site builds with `--strict` and covers M10 Sprint 3 scope:
install guide, user guide, API overview, privacy.

## Scope

| In scope                | Out of scope             |
| ----------------------- | ------------------------ |
| `mkdocs build --strict` | Live GitHub Pages deploy |
| Nav + search            | Custom domain CNAME      |
| Content pages listed    | Full API.md mirror       |

## Required pages

- [x] Home (`index.md`)
- [x] Install overview (`install/index.md`)
- [x] Container images (`install/container-images.md`)
- [x] Upgrade guide (`install/upgrade.md`)
- [x] User guide (`user-guide/index.md`)
- [x] API overview (`api/overview.md`)
- [x] Privacy (`privacy/index.md`)

## Static checks

```bash
cd docs-site
pip install -r requirements.txt
mkdocs build --strict
```

**Result (2026-07-11):** PASS

## CI workflows

- [`.github/workflows/ci-docs-site.yml`](../../.github/workflows/ci-docs-site.yml) — PR + main build
- [`.github/workflows/deploy-docs-site.yml`](../../.github/workflows/deploy-docs-site.yml) — GitHub Pages deploy on main

## Post-merge verification (maintainer)

1. Enable GitHub Pages: Settings → Pages → Source: **GitHub Actions**
2. Merge to `main` and confirm `Deploy — Docs Site` workflow succeeds
3. Open https://sturmi77.github.io/correlcore/
4. Optional: configure custom domain `docs.correlcore.app` in Pages settings

## Sign-off

| Check                 | Status  | Date       |
| --------------------- | ------- | ---------- |
| mkdocs build --strict | PASS    | 2026-07-11 |
| CI workflow added     | PASS    | 2026-07-11 |
| Deploy workflow added | PASS    | 2026-07-11 |
| Live GitHub Pages     | Pending | post-merge |

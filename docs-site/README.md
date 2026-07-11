# CorrelCore Docs Site (MkDocs Material)

Public documentation published to GitHub Pages.

## Local preview

```bash
cd docs-site
pip install -r requirements.txt
mkdocs serve
```

Open http://127.0.0.1:8000/

## Build (strict)

```bash
mkdocs build --strict
```

Output: `docs-site/site/`

## Deploy

Automatic on push to `main` via [`.github/workflows/deploy-docs-site.yml`](../.github/workflows/deploy-docs-site.yml).

Live URL: https://sturmi77.github.io/correlcore/

Optional custom domain: `docs.correlcore.app` (configure in GitHub Pages settings).

## Source layout

| Path | Purpose |
| ---- | ------- |
| `mkdocs.yml` | Site config, nav, theme |
| `docs/index.md` | Home |
| `docs/install/` | Selfhost install, images, upgrade |
| `docs/user-guide/` | End-user workflows |
| `docs/api/` | API overview |
| `docs/privacy/` | Privacy notice (GDPR) |

Canonical operator docs remain in [`docs/selfhost/`](../docs/selfhost/) in the repository.

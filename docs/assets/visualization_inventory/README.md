# Visualization inventory mockups

Schematic mockups for
[`docs/frontend/VISUALIZATION_INVENTORY_2026-09-17.md`](../../frontend/VISUALIZATION_INVENTORY_2026-09-17.md).

These are **not** screenshots of the running app. They are hand-built schematics rendered from
`src/`, using the real design tokens from `apps/web/src/app.css` and the real German UI strings
from `apps/web/src/lib/i18n/locales/de.json`, with synthetic data.

| Prefix | Meaning                                                    |
| ------ | ---------------------------------------------------------- |
| `mNN_` | An existing representation in the product.                 |
| `gN_`  | A **proposal** covering a gap — nothing of this ships yet. |

## Regenerating

Requires Python 3 with Pillow and a Chromium binary. In the Claude Code web environment
Chromium is pre-installed at `/opt/pw-browsers/chromium-1194/chrome-linux/chrome`; adjust
`CHROME` in `src/build.py` for a local run.

```bash
pip install pillow
cd docs/assets/visualization_inventory/src
python3 build.py ..            # all modules
python3 build.py .. mocks_b    # one module
```

`build.py` renders each mockup to a standalone HTML page, screenshots it at 2× device scale and
crops the trailing background. Keep individual mockups under ~880 CSS px tall — headless
Chromium returns a blank frame above roughly 1800 output pixels.

Module layout:

- `lib.py` — colour helpers (mirrors `StripCellMapper`), series/geometry helpers, page shell
- `shared.css` — dark-theme tokens copied from `app.css`
- `mocks_a.py` — Compare family (M01–M04)
- `mocks_b.py` — Insights family (M05–M08)
- `mocks_c.py` — Symptoms and event alignment (M09–M12)
- `mocks_d.py` — Home, habits, maturity (M13–M15) and the gap proposals (G1–G4)

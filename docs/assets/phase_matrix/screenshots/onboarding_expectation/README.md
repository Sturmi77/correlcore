# Onboarding Maturity Expectation Card — Visual Assets

Concept visuals for [`ONBOARDING_MATURITY_EXPECTATION_CARD.md`](../../../../frontend/ONBOARDING_MATURITY_EXPECTATION_CARD.md).

## Files

| File | Purpose |
| ---- | ------- |
| `expectation_card_mock.png` | Full card mock @2x (780×1688) — placement + layout reference |
| `expectation_card_mock_390.png` | Same mock at logical mobile width (390×844) |
| `thumb_phase{1-4}_*.png` | 144×144 square thumbs for each maturity phase |
| `strip_phase{1-4}_*.png` | Wider reference crops from source screenshots |

## Source screenshots

Thumbs are cropped from Dev Mode fixtures in the parent folder:

| Phase | Source |
| ----- | ------ |
| 1 | `../mobile__InsightsPage__collecting.png` |
| 2 | `../mobile__InsightsPage__early_patterns.png` |
| 3 | `../mobile__InsightsPage__provisional.png` |
| 4 | `../mobile__MobileInsightLead__robust.png` |

Regen parent screenshots first (see [`../README.md`](../README.md)), then re-crop thumbs with the same regions documented in the concept (square crop of the characteristic empty state / insight lead, ~20% desaturation).

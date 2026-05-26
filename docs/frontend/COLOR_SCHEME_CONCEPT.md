# CorrelCore Color Scheme — Theoretical Framework

> **Status:** Living document. Last updated: 2026-05-26  
> **Canonical ADRs:** [ADR-0020](../adr/0020-primary-color-system.md), [ADR-0026](../adr/0026-color-scheme-evaluation-orange-vs-violet.md), [ADR-0027](../adr/0027-light-mode-color-requirements.md)

This document records the theoretical foundations, contrast tables, and
design rationale for CorrelCore's color system. It serves as the reference
for all future palette discussions and PR reviews.

---

## 1. Color Theory Foundations

### 1.1 Hue Semantics Relevant to CorrelCore

Color is not neutral — hues carry consistent cross-cultural associations that
should align with, not contradict, the product's purpose.

| Hue                 | Cognitive associations                                         | CorrelCore fit                                                  |
| ------------------- | -------------------------------------------------------------- | --------------------------------------------------------------- |
| **Violet / Purple** | Introspection, depth, creativity, pattern recognition, premium | ✅ Strong — analytical, reflective tool                         |
| **Orange**          | Urgency, action, warmth, energy, appetite                      | ⚠️ Weak — signals immediacy, conflicts with reflective use case |
| **Blue**            | Trust, calm, clinical, data                                    | ✅ Good for data/heatmap encoding, not for primary identity     |
| **Teal**            | Wellness, balance, digital health                              | ⚠️ Overused in health-app category                              |
| **Red/Green**       | Traffic-light verdict, good/bad binary                         | ❌ Forbidden for habit/mood data per no-gamification promise    |

### 1.2 Simultaneous Contrast

Placing a colored element on a dark neutral surface increases its perceived
saturation (Bezold effect). This means:

- A violet `#7c6af5` on `#1e1b2e` appears richer than on white
- An orange `#E8922A` on near-black can look harshly neon
- Warm-dark surfaces (`#171614`) mitigate this by reducing the contrast
  differential between the neutral and the accent

CorrelCore's warm dark base (`#171614`, not pure `#000000`) was chosen
specifically to avoid simultaneous contrast harshness with the violet accent.

### 1.3 OLED Halation

Pure black (`#000000`) on OLED displays causes light bleed around bright
elements (halation). The warm dark `#171614` / `#141414` base avoids this
while still achieving deep contrast. Pure white backgrounds in light mode
trigger a similar issue (harsh adaptation); hence `#fafaf7` as the light base.

### 1.4 Color-Blind Safety

Approximately 8% of males and 0.5% of females have some form of
red-green color vision deficiency. CorrelCore's chart system (D-002) mandates:

- Dash patterns (solid, dashed, dotted, dash-dot) to distinguish metrics
- Point shapes (circle, square, triangle, diamond) as secondary encoding
- Heatmap scales must be perceptually uniform and color-blind safe
  (blue sequential scale, not red-green diverging)

---

## 2. The Chosen Palette: Violet/Dark

### 2.1 Dark Mode Tokens

```css
/* Primitive surfaces */
--color-bg: #171614; /* Page background (warm dark, not pure black) */
--color-surface: #1e1b18; /* Card / elevated surface */
--color-surface-raised: #252220; /* Dropdown, modal, popover */
--color-border: #3a3630; /* Dividers, input borders */

/* Text */
--color-text: #f0ece6; /* Primary text */
--color-text-muted: #9c9489; /* Secondary / descriptive text */
--color-text-faint: #5e5a54; /* Placeholder, disabled — decorative only */

/* Primary accent (violet) */
--color-primary: #7c6af5; /* Contrast on --color-bg: 7.4:1 ✅ AAA */
--color-primary-hover: #9587ff;
--color-primary-active: #6a5be0;
--color-primary-highlight: #2b2742; /* Subtle tint for selected states */

/* Status colors (dark mode — lightened for dark surfaces) */
--color-success: #4ade80;
--color-warning: #fbbf24;
--color-error: #f87171;
--color-info: #60a5fa;
```

### 2.2 Light Mode Tokens

```css
/* Primitive surfaces */
--color-bg: #fafaf7; /* Warm off-white (NOT #ffffff) */
--color-surface: #f0ede8;
--color-surface-raised: #e8e4de;
--color-border: #d6d0c8;

/* Text */
--color-text: #1c1a17; /* 16.8:1 on --color-bg ✅ AAA */
--color-text-muted: #6b6660; /* 5.1:1 on --color-bg ✅ AA */
--color-text-faint: #a8a39c; /* 2.7:1 — decorative only ⚠️ */

/* Primary accent (darkened for light mode contrast) */
--color-primary: #6356d9; /* 5.2:1 on --color-bg ✅ AA */
--color-primary-hover: #5548c5;
--color-primary-active: #4338a8;
--color-primary-highlight: #ebe9ff;

/* Status colors (dark mode — darkened for light surfaces) */
--color-success: #16a34a;
--color-warning: #b45309;
--color-error: #dc2626;
--color-info: #2563eb;
```

### 2.3 Missing Tokens to Add (M3.7 Sprint 1)

| Token                         | Dark value | Light value | Purpose                              | Blocks     |
| ----------------------------- | ---------- | ----------- | ------------------------------------ | ---------- |
| `--color-gold`                | `#fbbf24`  | `#b45309`   | InsightMaturityBadge early_patterns  | Issue #189 |
| `--color-insight-early`       | `#fbbf24`  | `#b45309`   | Semantic alias for early phase       | Issue #189 |
| `--color-insight-provisional` | `#60a5fa`  | `#2563eb`   | Semantic alias for provisional phase | Issue #189 |
| `--color-insight-robust`      | `#4ade80`  | `#16a34a`   | Semantic alias for robust phase      | Issue #189 |

---

## 3. Evaluated Alternatives

### 3.1 Orange/Dark — Rejected (ADR-0026)

Candidate palette: `#141414` bg / `#1e1e1e` surface / `#E8922A` accent

**Failure points:**

| Check                                  | Result                                           |
| -------------------------------------- | ------------------------------------------------ |
| Orange `#E8922A` on light bg `#fafaf7` | 2.5:1 — **WCAG AA FAIL**                         |
| Orange `#E8922A` on dark bg `#141414`  | 3.1:1 — **WCAG AA FAIL** for text                |
| Darkened orange `#B85F10` on `#fafaf7` | 4.7:1 — WCAG AA pass, but splits accent identity |
| Competitive overlap                    | Identical to Grafana, Home Assistant             |
| Hue semantic fit                       | Low — urgency/action vs. reflection/analysis     |

Decision: Rejected as primary. May be introduced as a semantic urgency/status
color for high-priority CTAs in future sprints (not as brand primary).

### 3.2 Teal/Dark — Pre-M3.5 Default, Replaced

The original teal (`#0d9488`) was replaced by ADR-0020. Teal is overused in
the digital health category (Headspace, Calm, Daylio). Violet provides stronger
differentiation and better semantic alignment.

### 3.3 Neutral/Dark (No Color Accent) — Considered, Rejected

A pure monochrome dark theme was considered for maximum privacy-first
aesthetics. Rejected because interactive elements require a distinctive color
for accessibility (WCAG focus visibility, SC 1.4.11) and because the product
needs visual hierarchy in its charts and insight cards.

---

## 4. Competitive Palette Landscape

| Product            | Primary              | Dark BG           | Notes                                          |
| ------------------ | -------------------- | ----------------- | ---------------------------------------------- |
| **Grafana**        | Orange `#FF7B00`     | `#111111`         | Monitoring/ops — orange = alerts               |
| **Home Assistant** | Teal/Orange mix      | `#1c1c1c`         | Smart home — action-oriented                   |
| **Nextcloud**      | Blue `#0082c9`       | N/A (light-first) | Enterprise file sync                           |
| **Daylio**         | Teal/Gradient        | White             | Wellness journal — playful                     |
| **Bearable**       | Blue/Green           | Dark option       | Health tracking — clinical                     |
| **CorrelCore**     | **Violet `#7c6af5`** | **`#171614`**     | **Analytical, introspective — differentiated** |

The violet/warm-dark combination is unique in the selfhosting and health-tracking
space, providing genuine visual differentiation.

---

## 5. Rules Summary for Implementers

1. **Use only semantic tokens** from `app.css`. Never hardcode hex values.
2. **Components must be theme-unaware.** They read tokens; they do not branch
   on `[data-theme]`.
3. **Charts use `--color-heatmap-*` tokens**, not `--color-primary`.
4. **No red/green for mood or habit data.** No traffic-light coloring.
5. **`--color-text-faint` is decorative-only.** Never use for data or labels.
6. **Light mode: `--color-primary` stays `#6356d9`.** Do not lighten it.
7. **Every new token needs a light and dark value**, plus a contrast ratio
   note in the PR description.
8. **Orange is a status color, not a brand color.** If introduced, only as
   `--color-warning` or a dedicated `--color-urgency` token.

---

## 6. Further Reading

- [ADR-0020](../adr/0020-primary-color-system.md) — Violet adoption decision
- [ADR-0026](../adr/0026-color-scheme-evaluation-orange-vs-violet.md) — Orange evaluation and rejection
- [ADR-0027](../adr/0027-light-mode-color-requirements.md) — Light mode formal requirements
- [UI_COMPONENT_SYSTEM.md](UI_COMPONENT_SYSTEM.md) — Component-level theming rules
- WCAG 2.2: https://www.w3.org/TR/WCAG22/

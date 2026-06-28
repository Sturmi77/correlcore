# CorrelCore Figma Handoff

This folder contains prepared Code Connect templates and the node map for the
CorrelCore Figma design system file:

https://www.figma.com/design/XjijHnzMJubA1iuPQxHOwS

Code Connect activation requires the Figma components to be published as a team
library and a Dev or Full seat on an Organization or Enterprise plan.

## Created component sets

- Button: https://www.figma.com/design/XjijHnzMJubA1iuPQxHOwS?node-id=6-64
- Panel: https://www.figma.com/design/XjijHnzMJubA1iuPQxHOwS?node-id=9-27
- InlineAlert: https://www.figma.com/design/XjijHnzMJubA1iuPQxHOwS?node-id=10-43
- ScreenHeader: https://www.figma.com/design/XjijHnzMJubA1iuPQxHOwS?node-id=11-33
- SegmentedControl: https://www.figma.com/design/XjijHnzMJubA1iuPQxHOwS?node-id=12-45
- TabBar: https://www.figma.com/design/XjijHnzMJubA1iuPQxHOwS?node-id=13-45
- AppNav: https://www.figma.com/design/XjijHnzMJubA1iuPQxHOwS?node-id=14-179
- ScaleSlider: https://www.figma.com/design/XjijHnzMJubA1iuPQxHOwS?node-id=16-107
- TagChip: https://www.figma.com/design/XjijHnzMJubA1iuPQxHOwS?node-id=17-18
- FormField: https://www.figma.com/design/XjijHnzMJubA1iuPQxHOwS?node-id=17-58
- MetricCard: https://www.figma.com/design/XjijHnzMJubA1iuPQxHOwS?node-id=19-53
- HomeSummary: https://www.figma.com/design/XjijHnzMJubA1iuPQxHOwS?node-id=19-113
- MetricTimeseries: https://www.figma.com/design/XjijHnzMJubA1iuPQxHOwS?node-id=20-102
- ComparisonHeatmap: https://www.figma.com/design/XjijHnzMJubA1iuPQxHOwS?node-id=20-268
- InsightCard: https://www.figma.com/design/XjijHnzMJubA1iuPQxHOwS?node-id=79-55
- InsightQualityMeter: https://www.figma.com/design/XjijHnzMJubA1iuPQxHOwS?node-id=79-83
- InsightStageHeader: https://www.figma.com/design/XjijHnzMJubA1iuPQxHOwS?node-id=79-111
- MobileInsightLead: https://www.figma.com/design/XjijHnzMJubA1iuPQxHOwS?node-id=98-1541
- MobileTrendsSummary: https://www.figma.com/design/XjijHnzMJubA1iuPQxHOwS?node-id=131-31
- InsightMatrix: https://www.figma.com/design/XjijHnzMJubA1iuPQxHOwS?node-id=131-62
- SymptomChecker: https://www.figma.com/design/XjijHnzMJubA1iuPQxHOwS?node-id=131-3914

## Code Connect templates

Local templates in [`components/`](./components/) (26 files).

### Publish (Sprint H)

Prerequisites: Figma **Organization/Enterprise** plan, **Dev or Full** seat on the
token owner, component library published.

```bash
# From repo root — dry-run (no token required for parse validation)
npx @figma/code-connect@latest connect publish --dry-run

# Publish (set token once in shell or CI secret)
$env:FIGMA_ACCESS_TOKEN = "<personal-access-token>"   # PowerShell
npx @figma/code-connect@latest connect publish
```

Token scopes: **Code Connect → Write**, **File content → Read**.
Generate at: Figma → Settings → Security → Personal access tokens.

Verify after publish: Dev Mode on Button `6:64` shows Svelte snippet; or MCP
`get_code_connect_map` for node `6:64`.

| Template            | Figma node | Code source                         |
| ------------------- | ---------- | ----------------------------------- |
| AppNav              | 14-179     | AppNav.svelte                       |
| Button              | 6-64       | Button.svelte                       |
| ComparisonHeatmap   | 20-268     | ComparisonHeatmap.svelte            |
| FormField           | 17-58      | TagPicker.svelte (field pattern)    |
| HomeSummary         | 19-113     | HomeSummary.svelte                  |
| InlineAlert         | 10-43      | InlineAlert.svelte                  |
| InsightCard         | 79-55      | InsightCard.svelte                  |
| InsightMatrix       | 131-62     | InsightMatrix.svelte                |
| InsightQualityMeter | 79-83      | InsightQualityMeter.svelte (legacy) |
| InsightStageHeader  | 79-111     | InsightStageHeader.svelte           |
| MetricCard          | 19-53      | MetricCard.svelte                   |
| MetricTimeseries    | 20-102     | MetricTimeseries.svelte             |
| MobileInsightLead   | 98-1541    | MobileInsightLead.svelte            |
| MobileTrendsSummary | 131-31     | MobileTrendsSummary.svelte          |
| Panel               | 9-27       | Panel.svelte                        |
| ScaleSlider         | 16-107     | ScaleSlider.svelte                  |
| ScreenHeader        | 11-33      | ScreenHeader.svelte                 |
| SegmentedControl    | 12-45      | SegmentedControl.svelte             |
| TabBar              | 13-45      | TabBar.svelte                       |
| TagChip             | 17-18      | TagPicker.svelte (chip pattern)     |

## Sprint G variant documentation

Board: https://www.figma.com/design/XjijHnzMJubA1iuPQxHOwS?node-id=131-3864

Extracts TagPicker chip states and SymptomChecker intensity grid from Sprint 1
Entry / Details Expanded (`50:1153`).

## Componentized screens

- Home / Componentized: https://www.figma.com/design/XjijHnzMJubA1iuPQxHOwS?node-id=21-3
- Entry Form / Componentized: https://www.figma.com/design/XjijHnzMJubA1iuPQxHOwS?node-id=21-69
- Trends / Componentized: https://www.figma.com/design/XjijHnzMJubA1iuPQxHOwS?node-id=21-151
- Insights / Componentized: https://www.figma.com/design/XjijHnzMJubA1iuPQxHOwS?node-id=21-282

## Mobile / Web split

- Mobile / App Flow: https://www.figma.com/design/XjijHnzMJubA1iuPQxHOwS?node-id=28-328
- Mobile / Today: https://www.figma.com/design/XjijHnzMJubA1iuPQxHOwS?node-id=28-331
- Mobile / Entry: https://www.figma.com/design/XjijHnzMJubA1iuPQxHOwS?node-id=28-397
- Mobile / Trends: https://www.figma.com/design/XjijHnzMJubA1iuPQxHOwS?node-id=28-484
- Mobile / Insights (legacy — do not use for Sprint 3): https://www.figma.com/design/XjijHnzMJubA1iuPQxHOwS?node-id=28-615
- Web / Desktop Flow: https://www.figma.com/design/XjijHnzMJubA1iuPQxHOwS?node-id=28-694
- Web / Today Dashboard: https://www.figma.com/design/XjijHnzMJubA1iuPQxHOwS?node-id=28-698
- Web / Entry Workspace: https://www.figma.com/design/XjijHnzMJubA1iuPQxHOwS?node-id=28-823
- Web / Trends Dashboard: https://www.figma.com/design/XjijHnzMJubA1iuPQxHOwS?node-id=28-908
- Web / Insights Dashboard: https://www.figma.com/design/XjijHnzMJubA1iuPQxHOwS?node-id=28-1080

## Mobile / Web audit

- Figma audit overview: https://www.figma.com/design/XjijHnzMJubA1iuPQxHOwS?node-id=31-1089
- Sprint 0 foundation contracts: https://www.figma.com/design/XjijHnzMJubA1iuPQxHOwS?node-id=36-1089
- Sprint 1 Mobile Entry flow: https://www.figma.com/design/XjijHnzMJubA1iuPQxHOwS?node-id=48-1089
- Mobile Entry / Quick Capture: https://www.figma.com/design/XjijHnzMJubA1iuPQxHOwS?node-id=49-1091
- Mobile Entry / Details Expanded: https://www.figma.com/design/XjijHnzMJubA1iuPQxHOwS?node-id=50-1153
- Mobile Entry / Saving and Saved: https://www.figma.com/design/XjijHnzMJubA1iuPQxHOwS?node-id=52-1153
- Mobile Entry / Offline Retry: https://www.figma.com/design/XjijHnzMJubA1iuPQxHOwS?node-id=54-1153
- Mobile Entry / Read-only History: https://www.figma.com/design/XjijHnzMJubA1iuPQxHOwS?node-id=55-1153
- Sprint 2 Mobile Trends flow: https://www.figma.com/design/XjijHnzMJubA1iuPQxHOwS?node-id=59-1285
- Mobile Trends / Summary: https://www.figma.com/design/XjijHnzMJubA1iuPQxHOwS?node-id=59-1293
- Mobile Trends / Detail Open: https://www.figma.com/design/XjijHnzMJubA1iuPQxHOwS?node-id=59-1296
- Mobile Trends / Empty: https://www.figma.com/design/XjijHnzMJubA1iuPQxHOwS?node-id=59-1299
- Sprint 3 Mobile Insights flow: https://www.figma.com/design/XjijHnzMJubA1iuPQxHOwS?node-id=98-1573
- Mobile Insights / Default: https://www.figma.com/design/XjijHnzMJubA1iuPQxHOwS?node-id=98-1579
- Mobile Insights / Empty: https://www.figma.com/design/XjijHnzMJubA1iuPQxHOwS?node-id=99-1505
- Mobile Insights / Loading: https://www.figma.com/design/XjijHnzMJubA1iuPQxHOwS?node-id=99-1554
- Mobile Insights / Matrix: https://www.figma.com/design/XjijHnzMJubA1iuPQxHOwS?node-id=99-1607
- Audit narrative: ./mobile-web-audit.md
- Audit data: ./mobile-web-audit.json

The Sprint 1 flow documents the implemented mobile composition, autosave and
validation feedback, explicit offline retry, tag and symptom limits, custom tag
entry, and the seven-day read-only boundary. Offline changes are not silently
queued; this remains consistent with ADR-0009 and ADR-0013.

The Sprint 2 flow uses the existing timeseries, tag heatmap, and symptom heatmap
responses. Mobile changes presentation hierarchy only: a readable summary is
shown first, while the complete desktop comparison canvas remains available
through an explicit detail action.

## Mobile Insights Sprint 3

Production-aligned Sprint 3 frames (2026-06-26):

- Strongest signal first via `MobileInsightLead`
- Maturity context via `InsightStageHeader`
- TabBar: Findings vs Matrix; analytics remain explicit detail surfaces
- Empty, loading, and matrix states match code contracts

Do not treat legacy `Mobile / Insights` (`28:615`) as the implementation
reference.

Closeout tracking: [`docs/MOBILE_INSIGHTS_PHASE3_SPRINT_PLAN.md`](../../docs/MOBILE_INSIGHTS_PHASE3_SPRINT_PLAN.md)

## Web Insights Sprint 9 (M7 spec complete)

Analytics interaction frames (2026-06-28). Sprint 9 component sets live on **Foundations**
(`correlcore-sprint9-component-sets-2026-06-28-v1`):

- **Flow board:** https://www.figma.com/design/XjijHnzMJubA1iuPQxHOwS?node-id=141-3841
- **Desktop analytics expanded:** https://www.figma.com/design/XjijHnzMJubA1iuPQxHOwS?node-id=141-3915
- **Desktop symptom analytics:** https://www.figma.com/design/XjijHnzMJubA1iuPQxHOwS?node-id=146-4289
- **Mobile detail sheet:** https://www.figma.com/design/XjijHnzMJubA1iuPQxHOwS?node-id=141-3968
- **Mobile entry history:** https://www.figma.com/design/XjijHnzMJubA1iuPQxHOwS?node-id=141-3990
- **Dark mode previews:** https://www.figma.com/design/XjijHnzMJubA1iuPQxHOwS?node-id=146-3983 (4 screens)

Component sets + Code Connect templates (local; publish still needs Dev/Full seat):

| Component                        | Figma set  | Variant axes               | Template                                             |
| -------------------------------- | ---------- | -------------------------- | ---------------------------------------------------- |
| `InsightCard`                    | `79:55`    | `State` incl. `Confounded` | `components/InsightCard.figma.ts`                    |
| `TagGroupsSection`               | `144:59`   | `Kind` × `State`           | `components/TagGroupsSection.figma.ts`               |
| `SymptomCooccurrenceDetailSheet` | `144:97`   | `Confounder`               | `components/SymptomCooccurrenceDetailSheet.figma.ts` |
| `SymptomCooccurrenceHeatmap`     | `144:3995` | `Phase` × `Sort`           | `components/SymptomCooccurrenceHeatmap.figma.ts`     |
| `TagCooccurrenceHeatmap`         | `144:4086` | `Range` × `Sort`           | `components/TagCooccurrenceHeatmap.figma.ts`         |
| `SymptomCalendarHeatmap`         | `144:4120` | `Phase`                    | `components/SymptomCalendarHeatmap.figma.ts`         |
| `EntryHistorySheet`              | `144:4145` | `State`                    | `components/EntryHistorySheet.figma.ts`              |
| `CooccurrenceEntrySheet`         | `144:4169` | `State`                    | `components/CooccurrenceEntrySheet.figma.ts`         |
| `SymptomTrendOverlay`            | `144:4189` | `Phase`                    | `components/SymptomTrendOverlay.figma.ts`            |
| `SymptomAnalyticsSection`        | `146:4151` | `State`                    | `components/SymptomAnalyticsSection.figma.ts`        |

Flow-board screens use component-set **instances**. Remaining gap: Code Connect publish (Dev/Full seat).

## Mobile Supporting Flows Sprint 4

Production-aligned Sprint 4 frames (2026-06-26). Code reference: `main` @ PR #234.

- **Flow board:** https://www.figma.com/design/XjijHnzMJubA1iuPQxHOwS?node-id=105-1626
- **Layout:** 1680 px board width (aligned with Sprint 3); 22 screens at 390×844;
  B2 and B4 use continuation rows (`111:2120`, `111:2123`) after auto-layout cleanup.

### B1 — Settings essentials

- Settings / Default: https://www.figma.com/design/XjijHnzMJubA1iuPQxHOwS?node-id=105-1634

### B2 — Symptom management

- Default: https://www.figma.com/design/XjijHnzMJubA1iuPQxHOwS?node-id=105-1679
- Delete confirm: https://www.figma.com/design/XjijHnzMJubA1iuPQxHOwS?node-id=105-1718
- Empty: https://www.figma.com/design/XjijHnzMJubA1iuPQxHOwS?node-id=105-1755
- Loading: https://www.figma.com/design/XjijHnzMJubA1iuPQxHOwS?node-id=105-1787
- Error: https://www.figma.com/design/XjijHnzMJubA1iuPQxHOwS?node-id=105-1819

### B3 — App & Offline / PWA

- Online: https://www.figma.com/design/XjijHnzMJubA1iuPQxHOwS?node-id=105-1855
- Offline: https://www.figma.com/design/XjijHnzMJubA1iuPQxHOwS?node-id=105-1899
- Install unavailable: https://www.figma.com/design/XjijHnzMJubA1iuPQxHOwS?node-id=105-1939

### B4 — Auth recovery

- Verify idle: https://www.figma.com/design/XjijHnzMJubA1iuPQxHOwS?node-id=105-1978
- Verify busy: https://www.figma.com/design/XjijHnzMJubA1iuPQxHOwS?node-id=105-2006
- Verify success: https://www.figma.com/design/XjijHnzMJubA1iuPQxHOwS?node-id=105-2032
- Verify error: https://www.figma.com/design/XjijHnzMJubA1iuPQxHOwS?node-id=105-2060
- Missing token: https://www.figma.com/design/XjijHnzMJubA1iuPQxHOwS?node-id=105-2088
- Resend success: https://www.figma.com/design/XjijHnzMJubA1iuPQxHOwS?node-id=105-2119
- Resend error: https://www.figma.com/design/XjijHnzMJubA1iuPQxHOwS?node-id=105-2127

### B5 — Onboarding touch states

- Guided tags: https://www.figma.com/design/XjijHnzMJubA1iuPQxHOwS?node-id=105-2176
- Retrospective: https://www.figma.com/design/XjijHnzMJubA1iuPQxHOwS?node-id=105-2140
- Profile: https://www.figma.com/design/XjijHnzMJubA1iuPQxHOwS?node-id=105-2152
- Submission error: https://www.figma.com/design/XjijHnzMJubA1iuPQxHOwS?node-id=105-2164

### B6 — Global recovery overlays

- Offline banner: https://www.figma.com/design/XjijHnzMJubA1iuPQxHOwS?node-id=105-2190
- Update banner: https://www.figma.com/design/XjijHnzMJubA1iuPQxHOwS?node-id=105-2228

Unsaved Entry data stays on Entry with explicit retry; no silent background sync
queue (ADR-0009).

Closeout tracking: [`docs/MOBILE_CLOSEOUT_SPRINT_PLAN.md`](../../docs/MOBILE_CLOSEOUT_SPRINT_PLAN.md)

## Theme modes (Sprint E)

Semantic colors live in the **CorrelCore / Color** variable collection with
**Light** and **Dark** modes, aligned to `apps/web/src/app.css` and ADR-0027
contrast pairs. Foundation components (`Button`, `Panel`, `InlineAlert`,
`ScreenHeader`, `AppNav`) bind to `color/*` tokens and respond to mode toggles.

**Surface rule:** Card/screen backgrounds use `color/surface`, `color/surface-2`,
or `color/bg` — not hardcoded white. Required for Dark reference frames
(`120:2096`) and mode toggles on sprint boards.

**Dark mode on instances:** Toggling **CorrelCore / Color → Dark** on a parent
frame does **not** always propagate into nested component instances (e.g.
`AppNav`). Dark reference clones set explicit Dark mode recursively on every
node. Do not judge dark parity from light sprint frames alone.

**AppNav:** Mobile variants use `color/surface` at 92% opacity + `color/border`
top stroke (matches `app.css` `color-mix` + border).

Dark reference screens (minimum parity matrix):

- Board: https://www.figma.com/design/XjijHnzMJubA1iuPQxHOwS?node-id=120-2096
- Entry · Dark: https://www.figma.com/design/XjijHnzMJubA1iuPQxHOwS?node-id=126-6
- Trends · Dark: https://www.figma.com/design/XjijHnzMJubA1iuPQxHOwS?node-id=126-84
- Insights · Dark: https://www.figma.com/design/XjijHnzMJubA1iuPQxHOwS?node-id=126-144
- Settings · Dark: https://www.figma.com/design/XjijHnzMJubA1iuPQxHOwS?node-id=126-221

Each sprint board (1–5) includes a **Dark mode previews** row below the light
states. Clones use explicit Dark mode on every node (required for `AppNav` and
other component instances).

| Sprint       | Board                                                                            | Dark previews row                                                                             |
| ------------ | -------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------- |
| 1 Entry      | [48:1089](https://www.figma.com/design/XjijHnzMJubA1iuPQxHOwS?node-id=48-1089)   | [129:6](https://www.figma.com/design/XjijHnzMJubA1iuPQxHOwS?node-id=129-6) · 5 screens        |
| 2 Trends     | [59:1285](https://www.figma.com/design/XjijHnzMJubA1iuPQxHOwS?node-id=59-1285)   | [129:147](https://www.figma.com/design/XjijHnzMJubA1iuPQxHOwS?node-id=129-147) · 3 screens    |
| 3 Insights   | [98:1573](https://www.figma.com/design/XjijHnzMJubA1iuPQxHOwS?node-id=98-1573)   | [129:453](https://www.figma.com/design/XjijHnzMJubA1iuPQxHOwS?node-id=129-453) · 5 screens    |
| 4 Supporting | [105:1626](https://www.figma.com/design/XjijHnzMJubA1iuPQxHOwS?node-id=105-1626) | [129:3739](https://www.figma.com/design/XjijHnzMJubA1iuPQxHOwS?node-id=129-3739) · 29 screens |
| 5 Home       | [121:2292](https://www.figma.com/design/XjijHnzMJubA1iuPQxHOwS?node-id=121-2292) | [127:2586](https://www.figma.com/design/XjijHnzMJubA1iuPQxHOwS?node-id=127-2586) · 3 screens  |
| 9 Analytics  | [141:3841](https://www.figma.com/design/XjijHnzMJubA1iuPQxHOwS?node-id=141-3841) | [146:3983](https://www.figma.com/design/XjijHnzMJubA1iuPQxHOwS?node-id=146-3983) · 4 screens  |

Cross-sprint minimum parity matrix (Theme Reference / Dark):

## Deprecated / reference-only frames

| Frame                      | Node     | Status         | Use instead             |
| -------------------------- | -------- | -------------- | ----------------------- |
| Mobile / App Flow          | `28:328` | DEPRECATED     | Sprint 1–4 flows        |
| Mobile / Insights (legacy) | `28:615` | DEPRECATED     | Sprint 3 `98:1573`      |
| Home / Componentized       | `21:3`   | Reference only | Sprint 5 Home (planned) |
| Entry Form / Componentized | `21:69`  | Reference only | Sprint 1 `48:1089`      |
| Trends / Componentized     | `21:151` | Reference only | Sprint 2 `59:1285`      |
| Insights / Componentized   | `21:282` | Reference only | Sprint 3 `98:1573`      |

Badges are visible on canvas (Sprint E, 2026-06-27).

## Pending Figma work

Production-grade closeout — **Sprint E–F complete**; remaining Sprints G–I:
[`docs/FIGMA_PRODUCTION_GRADE_SPRINT_PLAN.md`](../../docs/FIGMA_PRODUCTION_GRADE_SPRINT_PLAN.md)

## Mobile Home Sprint 5

- Flow board: https://www.figma.com/design/XjijHnzMJubA1iuPQxHOwS?node-id=121-2292
- Default: https://www.figma.com/design/XjijHnzMJubA1iuPQxHOwS?node-id=121-2296
- Loading: https://www.figma.com/design/XjijHnzMJubA1iuPQxHOwS?node-id=121-2361
- Empty: https://www.figma.com/design/XjijHnzMJubA1iuPQxHOwS?node-id=121-2425

Three zones per ADR-0017: today context (`ScreenHeader`), daily brief (`HomeSummary` +
panel), entry CTA + `AppNav · Today`.

### Sprint 4 extensions (Sprint F)

**B1b — Tag management**

- Default: https://www.figma.com/design/XjijHnzMJubA1iuPQxHOwS?node-id=121-2662
- Create tag: https://www.figma.com/design/XjijHnzMJubA1iuPQxHOwS?node-id=121-2703
- Empty: https://www.figma.com/design/XjijHnzMJubA1iuPQxHOwS?node-id=121-2741

**B4b — Auth entry**

- Login default: https://www.figma.com/design/XjijHnzMJubA1iuPQxHOwS?node-id=121-2585
- Login error: https://www.figma.com/design/XjijHnzMJubA1iuPQxHOwS?node-id=121-2600
- Register default: https://www.figma.com/design/XjijHnzMJubA1iuPQxHOwS?node-id=121-2619
- Register strength: https://www.figma.com/design/XjijHnzMJubA1iuPQxHOwS?node-id=121-2638

**Sprint 3 — Matrix @ 430 px**

- https://www.figma.com/design/XjijHnzMJubA1iuPQxHOwS?node-id=121-2781

### Out of scope here

- Phase 5 desktop consolidation
- Native mobile app split decision after product and platform scope is clear

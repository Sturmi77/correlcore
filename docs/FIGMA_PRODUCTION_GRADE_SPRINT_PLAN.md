# Figma Production-Grade Sprint Plan

Last updated: 2026-06-27

**Scope:** Close the gaps between **mobile closeout complete** (Phases 0–4) and a
**production-grade design system**: dark/light parity in Figma, full screen coverage,
complete Code Connect, live library publish, and legacy hygiene.

**Out of scope here:** Phase 5 desktop consolidation, password-recovery backend,
Dexie sync queue, Capacitor/native split.

Canonical references:

- Figma audit (2026-06-27): conversation closeout + [`docs/frontend/MOBILE_WEB_AUDIT.md`](frontend/MOBILE_WEB_AUDIT.md)
- Prior track: [`docs/MOBILE_CLOSEOUT_SPRINT_PLAN.md`](MOBILE_CLOSEOUT_SPRINT_PLAN.md) (Sprints A–D ✅)
- Figma file: [CorrelCore Design System](https://www.figma.com/design/XjijHnzMJubA1iuPQxHOwS)
- Node ledger: [`apps/web/figma/correlcore-figma-map.json`](../apps/web/figma/correlcore-figma-map.json)
- Code Connect templates: [`apps/web/figma/components/`](../apps/web/figma/components/)

---

## Executive summary

Mobile closeout delivered **34 canonical sprint screens** (S1–S4) with strong
light-mode token parity and E2E coverage at 390/430 px. Production-grade still
requires:

| Gap               | Current                                                  | Target                                              |
| ----------------- | -------------------------------------------------------- | --------------------------------------------------- |
| Theme in Figma    | Light frames only                                        | Variable modes or dark reference screens            |
| Code Connect live | 13 local templates; publish blocked                      | All mapped components + live `get_code_connect_map` |
| Screen flows      | Home, Login/Register, Tags missing                       | Dedicated sprint boards                             |
| Component sets    | InsightCard/StageHeader/QualityMeter undocumented in map | Component sets + `.figma.ts`                        |
| Legacy frames     | `28:*`, `21:*` still visible                             | Archived / deprecated in Figma + map                |
| Viewport matrix   | 430 px only on Trends Detail                             | Spot references + QA matrix                         |

**Recommended order:** E → F → G → H → I (H may start in parallel with G once
templates exist; publish depends on Figma org seat).

---

## Phase ledger (production-grade)

| Phase | Title                          | Figma                                        | Repo                    | QA / Docs       | Gate                         |
| ----- | ------------------------------ | -------------------------------------------- | ----------------------- | --------------- | ---------------------------- |
| E     | Token & hygiene foundation     | Variable modes, legacy archive, layout fixes | Map flags               | —               | Sprint E DoD ✅              |
| F     | Missing mobile screen flows    | Home, Auth entry, Tags                       | —                       | E2E optional    | Sprint F DoD ✅              |
| G     | Component library completeness | New component sets                           | 7 `.figma.ts` templates | Contract tests  | Sprint G DoD ✅              |
| H     | Code Connect publish           | Library publish                              | `figma connect publish` | Live map verify | **Deferred** — Dev/Full seat |
| I     | Production sign-off            | Dark QA board                                | Audit JSON refresh      | QA matrix doc   | Sprint I DoD ✅              |

---

## Sprint E — Design tokens & Figma hygiene

**Depends on:** Mobile closeout Sprints A–D ✅

**Goal:** Establish **dark/light as a first-class Figma contract** on foundation
components and remove confusion from legacy boards — without duplicating all 34
screens by hand.

### E1 — Figma variable collection (Light / Dark)

Create or extend a **CorrelCore Tokens** collection with modes aligned to
`apps/web/src/app.css`:

| Token group      | Light source                              | Dark source                    |
| ---------------- | ----------------------------------------- | ------------------------------ |
| Surfaces         | `[data-theme='light']`                    | `:root`, `[data-theme='dark']` |
| Text hierarchy   | `--color-text*`                           | same                           |
| Primary / status | `--color-primary*`, success/warning/error | same                           |
| Charts / heatmap | light heatmap + divergent tokens          | dark equivalents               |

Bind modes to these **foundation component sets** first (highest reuse):

- `Button` (`6:64`)
- `Panel` (`9:27`)
- `InlineAlert` (`10:43`)
- `ScreenHeader` (`11:33`)
- `AppNav` (`14:179`)

**Exit:** Toggling Figma mode Light ↔ Dark updates all five component sets;
spot-check against `pnpm check:contrast` token pairs (ADR-0027).

### E2 — Dark reference screens (minimum matrix)

Add **one dark frame per sprint flow** (duplicate from light, apply Dark mode —
do not redraw):

| Flow        | Reference light node    | New dark frame label                  |
| ----------- | ----------------------- | ------------------------------------- |
| S1 Entry    | `49:1091` Quick Capture | `Mobile Entry / Quick Capture · Dark` |
| S2 Trends   | `59:1293` Summary       | `Mobile Trends / Summary · Dark`      |
| S3 Insights | `98:1579` Default       | `Mobile Insights / Default · Dark`    |
| S4 Settings | `105:1634` Default      | `Mobile Settings / Default · Dark`    |

Place on a **Theme parity row** under each sprint header or a shared
`Theme Reference / Dark` board (`new node` — record in map).

**Exit:** Four dark reference frames; screenshot parity checklist vs rendered app
with `data-theme='dark'`.

### E3 — Layout fix: Sprint 3 Default overflow

Fix `98:1579` (`Mobile / Insights / Sprint 3 / Default`): `AppNav` must sit
inside the 844 px frame (currently y=882). Use auto-layout spacer / clip fix
consistent with Empty/Loading frames (`99:1505`, `99:1554`).

**Exit:** Frame height 844; no clipped or overflowing nav.

### E4 — Legacy deprecation in Figma + map

| Asset                         | Action                                                              |
| ----------------------------- | ------------------------------------------------------------------- |
| `28:615` Mobile Insights      | Keep README warning; add Figma badge **DEPRECATED → use 98:1573**   |
| `28:328` Mobile App Flow      | Badge **DEPRECATED → use Sprint 1–4 flows**                         |
| `21:3`–`21:282` Componentized | Move to page **Archive / Pre-Sprint** or badge **Reference only**   |
| `correlcore-figma-map.json`   | Add `"status": "deprecated"` on `28:328`, `28:615`, optional `21:*` |

**Exit:** No open mobile implementation doc points to legacy without deprecation
label; map reflects status.

### Sprint E definition of done

- [x] Variable collection with Light/Dark modes on 5 foundation components
- [x] 4 dark reference screens
- [x] Sprint 3 Default layout fixed
- [x] Legacy frames labeled; map updated
- [x] `apps/web/figma/README.md` — new § Theme modes + deprecation table

**Completed 2026-06-27.** Run id: `correlcore-production-grade-sprint-e-2026-06-27-v1`.

| Task | Result                                                                                                            |
| ---- | ----------------------------------------------------------------------------------------------------------------- |
| E1   | **CorrelCore / Color** collection extended with **Dark** mode (`120:0`); 20 semantic tokens alias dark primitives |
| E2   | **Theme Reference / Dark** board `120:2096` with 4 dark clones (`120:2099`, `120:2115`, `120:2141`, `120:2148`)   |
| E3   | Sprint 3 Default `98:1579`: removed overflow block; AppNav at y=760 within 844 px                                 |
| E4   | Deprecation badges on `28:328`, `28:615`, `21:3`–`21:282`; map `deprecated` flags                                 |

---

## Sprint F — Missing mobile screen flows

**Depends on:** Sprint E (tokens available for new frames)

**Goal:** Close **yellow** items from the production audit: screens that exist in
code and E2E but lack canonical Figma sprint boards.

### F1 — Sprint 5 / Home · Today (Mobile Primary)

**New flow board:** `Mobile Home / Sprint 5 Flow` (suggested placement: after
Sprint 4 board, 1680 px width, 390×844 frames).

| #   | State               | Content (match code)                                                |
| --- | ------------------- | ------------------------------------------------------------------- |
| 1   | Default             | `ScreenHeader`, `HomeSummary`, Daily Brief teaser, `AppNav · Today` |
| 2   | Partial / loading   | Skeleton or `DataState` partial — match `HomeDailyBrief` loading    |
| 3   | Empty / first visit | No entries yet CTA toward Entry                                     |

Code references:

- `apps/web/src/routes/+page.svelte`
- `HomeSummary`, `HomeDailyBrief`, `HomeTodayContext`, `HomeInsight`

**Exit:** 3 frames; nodes in `correlcore-figma-map.json` under
`implementationFlows`; audit Home row → **green**.

### F2 — Auth entry screens (Login + Register)

Extend Sprint 4 **B4 — Auth recovery** or add **B4b — Auth entry** row:

| Screen   | Route            | States                             |
| -------- | ---------------- | ---------------------------------- |
| Login    | `/auth/login`    | Default, inline error              |
| Register | `/auth/register` | Default, password strength visible |

Reuse: `Panel`, `FormField`, `Button`, `InlineAlert`, `PasswordStrength` (if
component exists in Figma; else add in Sprint G).

**Exit:** 4 frames minimum; README B4 section updated.

### F3 — Tags settings

Add **B1b — Tag management** under Sprint 4 or Sprint 5:

| State        | Route            | Notes                            |
| ------------ | ---------------- | -------------------------------- |
| Default list | `/settings/tags` | Existing tags, create affordance |
| Create tag   | same             | Inline create (WIP-214 parity)   |
| Empty        | same             | No custom tags yet               |

**Exit:** 3 frames; aligns with Settings Tags Playwright coverage.

### F4 — Optional: Insights disclaimer

If product requires design sign-off: single frame `/insights/disclaimer` with
`ScreenHeader` + legal copy panel. **Defer** if copy is static and low churn.

### F5 — 430 px reference (Insights matrix)

Add one **430×932** frame: `Mobile / Insights / Sprint 3 / Matrix · 430` —
mirrors E2E assertion _“430px keeps matrices behind explicit detail”_
(`mobile-insights-foundation.spec.ts`).

**Exit:** Frame exists; cross-linked in QA doc.

### Sprint F definition of done

- [x] Sprint 5 Home flow (3 screens) in Figma + map
- [x] Login + Register frames (4+ screens)
- [x] Tags settings frames (3 screens)
- [x] Insights disclaimer — **deferred** (static copy; no design churn)
- [x] 430 px Insights matrix reference frame
- [x] `mobile-web-audit.json` Home + Auth entry → green where applicable

**Completed 2026-06-27.** Run id: `correlcore-production-grade-sprint-f-2026-06-27-v1`.

| Task | Result                                                                                      |
| ---- | ------------------------------------------------------------------------------------------- |
| F1   | **Mobile Home / Sprint 5 Flow** `121:2292` — Default, Loading, Empty                        |
| F2   | **B4b Auth entry** — Login default/error, Register default/strength (`121:2585`–`121:2638`) |
| F3   | **B1b Tag management** — Default, Create, Empty (`121:2662`–`121:2741`)                     |
| F4   | Disclaimer deferred (documented)                                                            |
| F5   | **Matrix · 430** `121:2781` in Sprint 3 flow                                                |

---

## Sprint G — Component library & Code Connect templates

**Depends on:** Sprint E tokens (for new component variants)

**Goal:** Every **README-listed component set** has a map entry and a local
`.figma.ts` template; high-risk gaps from audit matrix closed.

### G1 — Missing Code Connect templates (repo)

Create templates following existing pattern (`// url=`, `// source=`):

| Component             | Figma node | Code source                                       |
| --------------------- | ---------- | ------------------------------------------------- |
| `InsightCard`         | `79:55`    | `InsightCard.svelte`                              |
| `InsightStageHeader`  | `79:111`   | `InsightStageHeader.svelte`                       |
| `InsightQualityMeter` | `79:83`    | (map to meter subcomponent or doc-only if inline) |
| `TagChip`             | `17:18`    | `TagPicker.svelte` (chip variant)                 |
| `FormField`           | `17:58`    | shared form field or TagPicker field              |

Extend [`code-connect-contract.test.ts`](../apps/web/src/routes/code-connect-contract.test.ts)
with import-path assertions for each new template (mirror `MobileInsightLead` test).

### G2 — Figma component sets (if not publish-ready)

Promote screen-local instances to **library component sets** where Sprint boards
already use them:

| Instance in screens               | Promote to set        | Variants                  |
| --------------------------------- | --------------------- | ------------------------- |
| `InsightStageHeader / Maturity`   | `InsightStageHeader`  | Collecting, Maturity, …   |
| `InsightCard / Loading`           | `InsightCard`         | Default, Loading, Compact |
| `MobileTrendsSummary` (S2 frames) | `MobileTrendsSummary` | Ready, Empty              |

Add **`InsightMatrix`** component set (`99:1620` reference) with mobile-simplified
variant documented in map.

### G3 — SymptomChecker & TagPicker documentation

Audit matrix flagged high mobile risk. Minimum deliverable:

- **TagPicker:** variant sheet — selected, limit reached, create custom (S1
  `50:1153` already shows states; extract to component set doc page)
- **SymptomChecker:** 1 component set + intensity grid variant (align S1
  `50:1178`)

No code changes required unless Figma discovery reveals drift.

### G4 — Map & README sync

Update:

- [`correlcore-figma-map.json`](../apps/web/figma/correlcore-figma-map.json) —
  `componentSets` for all G1/G2 items
- [`apps/web/figma/README.md`](../apps/web/figma/README.md) — template links
- Run id: `correlcore-production-grade-sprint-g-2026-06-XX-v1`

### Sprint G definition of done

- [x] 7 new `.figma.ts` files (20 total); contract tests green
- [x] Map lists 21 component sets matching README
- [x] InsightCard / StageHeader / Matrix as publishable Figma components
- [x] TagPicker + SymptomChecker variant documentation in Figma

**Completed 2026-06-27.** Run id: `correlcore-production-grade-sprint-g-2026-06-27-v1`.

| Task | Result                                                                                                                   |
| ---- | ------------------------------------------------------------------------------------------------------------------------ |
| G1   | Templates: InsightCard, InsightStageHeader, InsightQualityMeter, TagChip, FormField, MobileTrendsSummary, InsightMatrix  |
| G2   | Component sets: MobileTrendsSummary `131:31`, InsightMatrix `131:62`, SymptomChecker `131:3914`; Insight\* sets verified |
| G3   | Variant doc board `131:3864` (TagPicker chips, SymptomChecker intensity)                                                 |
| G4   | Map, README, contract tests updated                                                                                      |

---

## Sprint H — Code Connect publish & live sync

**Depends on:** Sprint G templates merged; **Figma org Dev or Full seat**

**Goal:** GitHub and Figma **live-linked** via Code Connect — not just local
templates.

### H1 — Unblock Figma seat / plan

| Blocker                                       | Owner          | Action                               |
| --------------------------------------------- | -------------- | ------------------------------------ |
| Code Connect API: _Dev or Full seat required_ | Design / Admin | Upgrade seat or assign to publisher  |
| Library not published                         | Design         | Publish CorrelCore component library |

Document outcome in README § Code Connect activation.

### H2 — Publish pipeline

1. From `apps/web`: run Figma Code Connect CLI publish (project convention —
   document exact command in README when verified).
2. Verify with MCP/API: `get_code_connect_map` for `6:64`, `98:1541`, `79:55`
   returns `codeConnectSrc` pointing at repo paths.
3. Spot-check Dev Mode in Figma: Button, MobileInsightLead, InsightCard show
   Svelte snippets.

### H3 — CI guard (optional but recommended)

Add a **manual or scheduled** workflow job (non-blocking until seat stable):

- Script fails if local template count ≠ map `componentSets` with `status: created`
- On publish success: optional smoke calling Code Connect API with repo token

### Sprint H definition of done

- [ ] `get_code_connect_map` succeeds for all mapped nodes
- [ ] Dev Mode shows snippets for core + insight components
- [ ] README documents publish command + last publish run id
- [ ] `MOBILE_WEB_AUDIT.md` — Code Connect row → green

---

## Sprint I — Production QA & sign-off

**Depends on:** Sprints E–H (H may be partial if seat delayed — sign off E+G+F
with H tracked)

**Goal:** Single **production-grade acceptance** record for design system parity.

### I1 — Rendered QA matrix (Figma ↔ browser)

Extend [`docs/quality/MOBILE_WEB_CLOSEOUT_QA.md`](quality/MOBILE_WEB_CLOSEOUT_QA.md)
or add `docs/quality/FIGMA_PRODUCTION_GRADE_QA.md`:

| Dimension | Coverage                                    |
| --------- | ------------------------------------------- |
| Viewports | 390, 430 (mandatory); 1280 sanity           |
| Themes    | Light + Dark (rendered + Figma mode toggle) |
| Flows     | S1–S5, S4 auth entry, tags                  |
| Checks    | H-scroll, 44 px touch, token contrast       |

Run:

```bash
cd apps/web && npm run test:e2e:mobile
pnpm check:contrast
```

Dark browser pass: manual or Playwright `data-theme` injection per flow (add
spec if missing).

### I2 — Audit refresh

Update:

- [`docs/frontend/MOBILE_WEB_AUDIT.md`](frontend/MOBILE_WEB_AUDIT.md) — remove
  “Remaining gaps” items closed by this plan
- [`apps/web/figma/mobile-web-audit.json`](../apps/web/figma/mobile-web-audit.json) —
  Home green, theme parity note, Code Connect status
- [`docs/frontend/MOBILE_WEB_IMPLEMENTATION_PLAN.md`](frontend/MOBILE_WEB_IMPLEMENTATION_PLAN.md) —
  pointer to this plan + status line

### I3 — GitHub closure

| Issue theme                             | Action                        |
| --------------------------------------- | ----------------------------- |
| Figma production-grade                  | Close with link to QA doc     |
| Open `mobile` / `design-system` backlog | Triage; link sub-tasks to E–I |

### I4 — Figma audit overview board

Refresh [`31:1089`](https://www.figma.com/design/XjijHnzMJubA1iuPQxHOwS?node-id=31-1089)
badge counts: screen rows + component cards + **theme parity** row.

### Sprint I definition of done

- [x] QA doc signed with light + dark matrix — [`FIGMA_PRODUCTION_GRADE_QA.md`](quality/FIGMA_PRODUCTION_GRADE_QA.md)
- [x] Audit JSON + MOBILE_WEB_AUDIT updated
- [x] Figma overview board reflects production-grade status (`31:1089` theme parity row)
- [x] Phase ledger: H explicitly deferred (Figma org admin / Dev or Full seat)

**Completed 2026-06-27.** Run id: `correlcore-production-grade-sprint-i-2026-06-27-v1`.

| Task | Result                                                                    |
| ---- | ------------------------------------------------------------------------- |
| I1   | QA matrix doc; `mobile-theme-parity.spec.ts` dark @390 smoke              |
| I2   | Audit + implementation plan refresh                                       |
| I3   | GitHub triage — manual (link QA doc when closing production-grade issues) |
| I4   | Overview board subtitle + theme parity row `134:3827`                     |

---

## Recommended execution order

```text
Sprint E (tokens + hygiene)
    ↓
Sprint F (missing screens)     ──┐
    ↓                            ├── can overlap after E1 complete
Sprint G (components + templates)┘
    ↓
Sprint H (publish — seat gate)
    ↓
Sprint I (sign-off)
```

**Parallel allowed:**

- G1 templates in repo while E1 variable modes are in progress (different owners)
- F1 Home frames while G2 InsightCard set is built
- H blocked on org seat — **do not block** E, F, G, I (partial)

---

## Effort estimate

| Sprint | Focus                            | Estimate                      |
| ------ | -------------------------------- | ----------------------------- |
| E      | Variables + 4 dark refs + legacy | 1–2 days design               |
| F      | ~10 new screens                  | 2–3 days design               |
| G      | 5 templates + 3 component sets   | 1–2 days design + 0.5 day eng |
| H      | Publish + verify                 | 0.5 day (after seat)          |
| I      | QA + docs                        | 1 day eng + QA                |

**Total:** ~1.5–2 weeks calendar with design + frontend pairing; Sprint H
calendar depends on Figma admin.

---

## Risk register

| Risk                                         | Impact                  | Mitigation                                               |
| -------------------------------------------- | ----------------------- | -------------------------------------------------------- |
| Figma seat gate persists                     | No live Code Connect    | Ship G locally; H deferred; I sign-off notes partial     |
| Dark mode via variables breaks legacy frames | Visual regressions      | Bind modes only on component sets; screens use instances |
| Scope creep into Phase 5 desktop             | Delays production-grade | Explicit out-of-scope; desktop wide frames unchanged     |
| Home composition churn (M5)                  | F5 frames stale         | Lock to current `+page.svelte`; refresh in Phase 5       |
| Inter in Figma vs system UI in code          | Typography drift        | Document as accepted; no webfont in product (DSGVO)      |

---

## Acceptance criteria (production-grade)

The design system is **production-grade** when all are true:

1. **Theme:** Foundation components support Light/Dark in Figma; minimum dark
   reference screens exist; code `check:contrast` passes.
2. **Coverage:** Every primary mobile route in
   [`MOBILE_WEB_CLOSEOUT_QA.md`](quality/MOBILE_WEB_CLOSEOUT_QA.md) has a
   canonical Figma sprint frame (including Home, Login, Register, Tags).
3. **Components:** README component list = map componentSets = `.figma.ts` count
   (except explicitly doc-only nodes).
4. **Connect:** Live Code Connect map verified OR seat deferral documented with
   date and owner.
5. **Hygiene:** Legacy mobile/desktop preview frames deprecated and not referenced
   by implementation docs.
6. **Evidence:** QA matrix + audit JSON updated; Figma overview board current.

---

## Explicitly out of scope

- Phase 5 desktop consolidation (split views, wide Home dashboard)
- Password recovery UI (backend contract pending)
- Account deletion, reminders, health import consent screens
- Dexie background sync queue UI
- Native app / Capacitor shell
- Full duplication of all 34+ screens in both themes (variable modes + 4 refs
  suffice)

---

## Quick links after completion

| Artifact               | Path                                                              |
| ---------------------- | ----------------------------------------------------------------- |
| Sprint plan (this doc) | `docs/FIGMA_PRODUCTION_GRADE_SPRINT_PLAN.md`                      |
| Node map               | `apps/web/figma/correlcore-figma-map.json`                        |
| Code Connect           | `apps/web/figma/components/*.figma.ts`                            |
| QA sign-off            | `docs/quality/FIGMA_PRODUCTION_GRADE_QA.md` (created in Sprint I) |
| Prior mobile closeout  | `docs/MOBILE_CLOSEOUT_SPRINT_PLAN.md`                             |

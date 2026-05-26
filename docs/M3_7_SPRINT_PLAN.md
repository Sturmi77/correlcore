# M3.7 Sprint Plan – Color System Hardening

Last updated: 2026-05-26

M3.7 consolidates the findings of the structured color scheme evaluation
(ADR-0026, ADR-0027) into a focused token hardening and QA milestone.

**Prerequisite:** M3.6 CI blockers (typecheck/lint) must be resolved and
Sprint 4 closeout completed before M3.7 begins. Notes Epic (#194–#202) and
remaining M3.5 issues (#182–#186) may proceed in parallel once M3.6 is
unblocked.

---

## Goal

Formalize and complete the color token architecture. No palette change.
No rebrand. The deliverables are:

- ADRs filed and merged: ADR-0026, ADR-0027 ✅ (completed 2026-05-26)
- `docs/frontend/COLOR_SCHEME_CONCEPT.md` written ✅ (completed 2026-05-26)
- Missing tokens added (`--color-gold`, insight maturity semantic tokens)
- Legacy aliases removed (`--color-ms-primary*`)
- System-preference fallback block completed (`--color-metric-*` gap)
- Light mode formally QA'd against ADR-0027 requirements
- `pnpm check:contrast` CI gate added
- `docs/FRONTEND.md` updated to reference ADR-0027

---

## Sources of Truth

- [ADR-0026](adr/0026-color-scheme-evaluation-orange-vs-violet.md) — color scheme evaluation
- [ADR-0027](adr/0027-light-mode-color-requirements.md) — light mode requirements
- `apps/web/src/app.css` — runtime token source
- `docs/frontend/COLOR_SCHEME_CONCEPT.md` — theoretical framework
- `docs/FRONTEND.md` — screen-level implementation rules

---

## Sprint 0 — ADR Documentation ✅ COMPLETED (2026-05-26)

**Goal:** All color-related architectural decisions are formally recorded.

### Completed deliverables

- [x] `docs/adr/0026-color-scheme-evaluation-orange-vs-violet.md` — merged
- [x] `docs/adr/0027-light-mode-color-requirements.md` — merged
- [x] `docs/frontend/COLOR_SCHEME_CONCEPT.md` — merged
- [x] ADR README index updated with ADR-0026 and ADR-0027

### Exit criteria — all met

- [x] Both ADRs present in `docs/adr/`
- [x] `COLOR_SCHEME_CONCEPT.md` exists in `docs/frontend/`
- [x] ADR README index updated
- [x] No code changes in this sprint

---

## Sprint 1 — Token Completion and Legacy Cleanup

**Goal:** `app.css` is the single, complete, gap-free token source.

### Issues to create and close

| Issue title | Labels | Notes |
|-------------|--------|-------|
| `[M3.7] Token: add --color-gold and insight maturity semantic tokens` | `frontend`, `tokens` | Blocks #189 |
| `[M3.7] Cleanup: remove legacy --color-ms-primary* aliases` | `frontend`, `cleanup` | — |
| `[M3.7] Fix: system-preference fallback block missing --color-metric-*` | `frontend`, `bug` | — |

### Tasks

1. **Add `--color-gold`** to `app.css`
   - Dark: `#fbbf24`
   - Light: `#b45309` (contrast on `#fafaf7`: 4.9:1 ✅ AA)
   - Document contrast ratio in PR description

2. **Add insight maturity semantic tokens** to `app.css`
   ```css
   /* dark */
   --color-insight-early:       #fbbf24;
   --color-insight-provisional: #60a5fa;
   --color-insight-robust:      #4ade80;

   /* light */
   --color-insight-early:       #b45309;
   --color-insight-provisional: #2563eb;
   --color-insight-robust:      #16a34a;
   ```

3. **Remove legacy aliases** — verify no component references them first:
   ```bash
   grep -r 'color-ms-primary' apps/web/src/
   ```
   Then remove from `app.css`:
   ```css
   /* DELETE these three aliases */
   --color-ms-primary: ...;
   --color-ms-primary-hover: ...;
   --color-ms-primary-active: ...;
   ```

4. **Fix system-preference fallback block** — ensure
   `@media (prefers-color-scheme: dark)` block is 1:1 with
   `[data-theme='dark']` block, including `--color-metric-*` tokens.

### Exit criteria

- [ ] `--color-gold` exists with verified dark and light values (contrast noted in PR)
- [ ] `--color-insight-early/provisional/robust` exist in both modes
- [ ] No `--color-ms-primary*` token references remain in the codebase
      (`grep -r 'color-ms-primary' apps/` returns empty)
- [ ] System-preference fallback block is 1:1 with `[data-theme='dark']` block
- [ ] CI: `svelte-check`, `eslint`, `prettier` pass
- [ ] Issue #189 can proceed (dependency unblocked)

---

## Sprint 2 — Light Mode QA Gate

**Goal:** Light mode is verified against ADR-0027 and QA is systematized in CI.

### Issues to create and close

| Issue title | Labels | Notes |
|-------------|--------|-------|
| `[M3.7] CI: add pnpm check:contrast WCAG AA gate` | `frontend`, `ci`, `a11y` | — |
| `[M3.7] QA: Light mode contrast audit against ADR-0027` | `frontend`, `a11y`, `qa` | — |
| `[M3.7] docs: update FRONTEND.md to reference ADR-0027` | `documentation` | — |

### Tasks

1. **Add `pnpm check:contrast` script**

   Install: `pnpm add -D wcag-contrast` (or equivalent)

   Create `scripts/check-contrast.ts`:
   - Parse `--color-*` tokens from `app.css`
   - Assert all informational text pairs meet 4.5:1
   - Assert all UI component pairs meet 3:1 (SC 1.4.11)
   - Assert `--color-text-faint` is NOT used in pair assertions
     (document it as decorative-only)
   - Exit code 1 on any failure

   Add to `package.json`:
   ```json
   "check:contrast": "tsx scripts/check-contrast.ts"
   ```

   Add step to `ci-web.yml`:
   ```yaml
   - name: Contrast check
     run: pnpm check:contrast
   ```

2. **Manual QA pass — all screens in light mode**

   Screens to verify (per ADR-0017 — 5 primary screens):
   - `/` (Home / Dashboard)
   - `/entries/new` (Entry Sheet)
   - `/insights` (Insights Feed)
   - `/trends` (Trends)
   - `/settings` (Settings)
   - `/dev` (Developer View — non-user-facing but must not break)

   For each screen verify at 375px and 1280px viewport:
   - [ ] All text is legible (no WCAG AA violation visible)
   - [ ] Interactive elements have visible focus rings
   - [ ] Charts use dash patterns / point shapes (not color alone)
   - [ ] No hardcoded non-token colors visible in DevTools
   - [ ] `--color-text-faint` not used for data labels

   Document QA results in `docs/M3_7_SPRINT_STATUS.md`.

3. **Update `docs/FRONTEND.md`** — add theming section:
   ```markdown
   ## Theming

   Color tokens are defined in `apps/web/src/app.css`.
   Light mode requirements are formally specified in [ADR-0027](adr/0027-light-mode-color-requirements.md).
   Theoretical framework and contrast tables: [COLOR_SCHEME_CONCEPT.md](frontend/COLOR_SCHEME_CONCEPT.md).
   ```

### Exit criteria

- [ ] `pnpm check:contrast` script exists and passes
- [ ] `check:contrast` step added to `ci-web.yml` and passes in CI
- [ ] All 5 primary screens QA'd in light mode at 375px and 1280px
- [ ] No WCAG AA violations found for informational text in light mode
- [ ] QA results documented in `docs/M3_7_SPRINT_STATUS.md`
- [ ] `docs/FRONTEND.md` references ADR-0027 and `COLOR_SCHEME_CONCEPT.md`
- [ ] CI: full pipeline green (`svelte-check`, `eslint`, `prettier`,
      `check:contrast`)

---

## GitHub Issues Overview

Create the following issues before Sprint 1 begins:

| # | Title | Sprint | Labels | Dependency |
|---|-------|--------|--------|------------|
| — | [M3.7] Token: add `--color-gold` and insight maturity semantic tokens | S1 | `frontend`, `tokens` | Blocks #189 |
| — | [M3.7] Cleanup: remove legacy `--color-ms-primary*` aliases | S1 | `frontend`, `cleanup` | — |
| — | [M3.7] Fix: system-preference fallback block missing `--color-metric-*` | S1 | `frontend`, `bug` | — |
| — | [M3.7] CI: add `pnpm check:contrast` WCAG AA gate | S2 | `frontend`, `ci`, `a11y` | — |
| — | [M3.7] QA: Light mode contrast audit against ADR-0027 | S2 | `frontend`, `a11y`, `qa` | — |
| — | [M3.7] docs: update FRONTEND.md to reference ADR-0027 | S2 | `documentation` | — |

---

## Dependency Map

```
M3.6 CI Blocker Resolution  (prerequisite — not in M3.7 scope)
    └─► M3.7 Sprint 0: ADR Documentation ✅ DONE
          └─► M3.7 Sprint 1: Token Completion + Legacy Cleanup
                └─► M3.7 Sprint 2: Light Mode QA Gate
                      └─► M3.8+ (next milestone)

Parallel (no M3.7 dependency):
    Notes Epic (#194–#202)
    M3.5 remaining issues (#182–#186)
```

---

## Milestone Acceptance Criteria

M3.7 is complete when ALL of the following are true:

- [ ] ADR-0026 and ADR-0027 merged to `main` ✅
- [ ] `docs/frontend/COLOR_SCHEME_CONCEPT.md` exists ✅
- [ ] `--color-gold` token present with verified contrast in both modes
- [ ] `--color-insight-early/provisional/robust` present in both modes
- [ ] No `--color-ms-primary*` tokens remain in codebase
- [ ] System-preference fallback block is complete (no missing tokens)
- [ ] `pnpm check:contrast` script passes in CI
- [ ] All 5 primary screens QA'd in light mode (375px + 1280px)
- [ ] No WCAG AA violations for informational text in light mode
- [ ] `docs/FRONTEND.md` references ADR-0027
- [ ] `docs/M3_7_SPRINT_STATUS.md` shows all sprints complete
- [ ] CI: `svelte-check` + `eslint` + `prettier` + `check:contrast` green on `main`
- [ ] `CHANGELOG.md` updated

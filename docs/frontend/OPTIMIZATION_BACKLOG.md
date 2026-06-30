# CorrelCore — GUI Optimization Backlog

**Date:** 2026-06-30  
**Source:** [`FRICTION_AUDIT.md`](FRICTION_AUDIT.md)  
**Labels:** `workflow`, `friction`, `quick-win`, `needs-adr`, `ux`

Prioritized implementation items derived from workflow walkthrough. Create GitHub issues from these templates.

---

## Quick wins (implement first)

### O-01 — Consolidate Insights maturity UI on mobile

| Field | Value |
|-------|-------|
| **GitHub** | [#250](https://github.com/Sturmi77/correlcore/issues/250) |
| **Labels** | `friction`, `quick-win`, `workflow`, `ux` |
| **Workflows** | W5, W6 |
| **Class** | Eliminieren |
| **Friction score** | 4 (duplicate lead + stage header) |
| **ADR conflict** | No — ADR-0021 phases remain visible |

**Problem:** On mobile Insights (`/insights`), `MobileInsightLead` and `InsightStageHeader` both communicate maturity and top finding, wasting first-viewport space (see [`FRONTEND_STREAMLINE_CONCEPT.md`](../FRONTEND_STREAMLINE_CONCEPT.md)).

**Proposal:** Show exactly one status block per screen. Keep `MobileInsightLead` OR compact `InsightStageHeader`, not both.

**Acceptance criteria:**
- [ ] Mobile 390px: single maturity/status region above view tabs
- [ ] Desktop 1280px: unchanged analysis-first layout
- [ ] `mobile-insights-foundation.spec.ts` and `user-journeys.spec.ts` pass

**Files:** `apps/web/src/routes/insights/+page.svelte`, `MobileInsightLead.svelte`, `InsightStageHeader.svelte`

---

### O-02 — Open EntrySheet after onboarding complete

| Field | Value |
|-------|-------|
| **GitHub** | [#251](https://github.com/Sturmi77/correlcore/issues/251) |
| **Labels** | `friction`, `quick-win`, `workflow`, `ux` |
| **Workflows** | W2, W3 |
| **Class** | Vorverlagern |
| **Friction score** | 3 (extra home stop before first entry) |
| **ADR conflict** | No |

**Problem:** After onboarding "Start tracking", user lands on Home and must tap CTA again to log first entry (FRICTION_AUDIT W2 step 9).

**Proposal:** On `completeOnboarding` success, navigate to `/` with query `?openEntry=1` or dispatch open EntrySheet from Home mount when `entry_count === 0` post-onboarding.

**Acceptance criteria:**
- [ ] Completing onboarding opens EntrySheet automatically once
- [ ] Skip path also offers optional immediate entry
- [ ] `user-journeys.spec.ts` onboarding tests updated

**Files:** `apps/web/src/routes/onboarding/+page.svelte`, `apps/web/src/routes/+page.svelte`

---

### O-03 — Insights empty-state CTA opens entry directly

| Field | Value |
|-------|-------|
| **GitHub** | [#252](https://github.com/Sturmi77/correlcore/issues/252) |
| **Labels** | `friction`, `quick-win`, `workflow`, `ux` |
| **Workflows** | W5 |
| **Class** | Umleiten |
| **Friction score** | 2 |
| **ADR conflict** | No |

**Problem:** Collecting-phase Insights empty state links to Home, requiring another tap for entry.

**Proposal:** CTA triggers `goto('/?openEntry=1')` or uses shared entry-open event.

**Acceptance criteria:**
- [ ] Empty state CTA reaches entry capture in one tap from Insights
- [ ] Works on mobile and desktop

**Files:** `apps/web/src/lib/components/insights/InsightFeed.svelte`

---

### O-04 — Redirect legacy onboarding routes

| Field | Value |
|-------|-------|
| **GitHub** | [#253](https://github.com/Sturmi77/correlcore/issues/253) |
| **Labels** | `friction`, `quick-win`, `workflow`, `ux` |
| **Workflows** | W2 |
| **Class** | Eliminieren |
| **Friction score** | 8 (legacy retro + profile path) |
| **ADR conflict** | No — ADR-0030 supersedes |

**Problem:** `/onboarding/retro` and `/onboarding/profile` remain reachable via deep link but are bypassed by guided onboarding, causing confusion.

**Proposal:** Replace pages with `goto('/onboarding', { replaceState: true })` or show deprecation notice + redirect.

**Acceptance criteria:**
- [ ] Direct navigation to legacy routes redirects to `/onboarding`
- [ ] No broken links in docs or Settings dev preview

**Files:** `apps/web/src/routes/onboarding/retro/+page.svelte`, `apps/web/src/routes/onboarding/profile/+page.svelte`

---

### O-05 — Hide Home sparkline until sufficient data

| Field | Value |
|-------|-------|
| **GitHub** | [#254](https://github.com/Sturmi77/correlcore/issues/254) |
| **Labels** | `friction`, `quick-win`, `workflow`, `ux` |
| **Workflows** | W5 |
| **Class** | Vereinfachen |
| **Friction score** | 2 |
| **ADR conflict** | No |

**Problem:** Sparkline with 1–2 points adds visual noise without insight (FRICTION_AUDIT W5 collecting).

**Proposal:** Render `HomeSparkline` only when `recentEntries.length >= 3`.

**Acceptance criteria:**
- [ ] 0–2 entries: sparkline hidden, CTA remains
- [ ] 3+ entries: sparkline visible as today

**Files:** `apps/web/src/routes/+page.svelte`, `HomeSparkline.svelte`

---

## Strategic items (higher effort)

### O-06 — Integrate tag selection into first entry

| Field | Value |
|-------|-------|
| **Labels** | `friction`, `workflow`, `ux`, `needs-adr` |
| **Workflows** | W2, W3 |
| **Class** | Vorverlagern |
| **Friction score** | 6+ |
| **ADR conflict** | Yes — ADR-0030 update required |

**Problem:** Separate 3-step onboarding delays time-to-first-entry by ~2 minutes.

**Proposal:** Collapse tag onboarding into first `EntrySheet` session with inline suggestions; keep `POST /onboarding/complete` on first save or skip.

**Acceptance criteria:**
- [ ] New user can log first entry without separate onboarding wizard
- [ ] Tag suggestions still offered inline
- [ ] ADR documents scope change

---

### O-07 — Auto-login after email verification

| Field | Value |
|-------|-------|
| **Labels** | `friction`, `workflow`, `ux`, `needs-adr` |
| **Workflows** | W1 |
| **Class** | Zusammenführen |
| **Friction score** | 4 |
| **ADR conflict** | Yes — ADR-0004 |

**Problem:** Register → check-email → verify → login is four screens before first app use.

**Proposal:** Issue short-lived session cookie on successful verify; redirect to `/` or onboarding.

**Acceptance criteria:**
- [ ] Verified user reaches app without manual login step
- [ ] Security review: token burn, session fixation
- [ ] ADR-0004 amendment

---

### O-08 — Unify desktop entry surface

| Field | Value |
|-------|-------|
| **Labels** | `friction`, `workflow`, `ux` |
| **Workflows** | W3, W4 |
| **Class** | Zusammenführen |
| **Friction score** | 4 |
| **ADR conflict** | No |

**Problem:** Desktop users encounter both `EntrySheet` (Home) and `/entries/new` (deep links) with different chrome.

**Proposal:** Phase 5 — standardize on one desktop capture pattern; align Trends empty-state CTAs.

**Acceptance criteria:**
- [ ] Single documented desktop entry path
- [ ] `FRONTEND_STATUS.md` Entry web status → green

---

### O-09 — Habit hint in onboarding tag step

| Field | Value |
|-------|-------|
| **Labels** | `friction`, `workflow`, `ux` |
| **Workflows** | W2, W7 |
| **Class** | Vorverlagern |
| **Friction score** | 3 |
| **ADR conflict** | Related to ADR-0034 (cycle toggle) |

**Problem:** Habit configuration only discoverable in Settings; Habits tab empty without prior setup.

**Proposal:** Optional "Track as habit" toggle on selected tags during onboarding; link to ADR-0034 cycle opt-in.

---

## Deferred / out of scope (document only)

| ID | Item | Reason |
|----|------|--------|
| O-10 | Password reset UI | Backend not implemented |
| O-11 | Phase 5 desktop entry workspace | Separate track |
| O-12 | Figma Code Connect publish | Design tooling, not user flow |

---

## Priority matrix

| ID | Impact | Effort | Quadrant |
|----|--------|--------|----------|
| O-01 | High | Low | Quick win |
| O-02 | High | Low | Quick win |
| O-03 | Medium | Low | Quick win |
| O-04 | Medium | Low | Quick win |
| O-05 | Low | Low | Quick win |
| O-06 | High | High | Strategic |
| O-07 | High | Medium | Strategic |
| O-08 | Medium | High | Strategic |
| O-09 | Medium | Medium | Strategic |

---

## Suggested sprint grouping

**Sprint A (quick wins):** O-01, O-02, O-03, O-05  
**Sprint B (cleanup):** O-04, O-09  
**Sprint C (strategic):** O-06, O-07, O-08 (each needs design + ADR review)

---

## Issue creation command template

```bash
gh issue create \
  --title "ux: O-01 Consolidate Insights maturity UI on mobile" \
  --label "friction,quick-win,workflow,ux" \
  --body-file docs/frontend/issues/O-01.md
```

Copy acceptance criteria from sections above into per-issue files when creating tickets.

# CorrelCore — GUI Friction Audit

**Date:** 2026-06-30 (status updated 2026-07-01)  
**Method:** Code-based step inventory + viewport walkthrough (390×844 mobile, 1280×900 desktop)  
**Workflow reference:** [`USER_WORKFLOWS.md`](USER_WORKFLOWS.md)  
**Backlog / planning:** [`OPTIMIZATION_BACKLOG.md`](OPTIMIZATION_BACKLOG.md) · [`GUI_OPTIMIZATION_PHASE2.md`](GUI_OPTIMIZATION_PHASE2.md)

### Resolution status (summary)

| Phase         | Scope                    | Status                                      |
| ------------- | ------------------------ | ------------------------------------------- |
| Phase 1       | O-01–O-20                | **Complete** on `main`                      |
| Phase 2 early | O-30 (#288), O-21 (#289) | **Complete** on `main`                      |
| Phase 2 open  | —                        | **Complete** (O-21–O-42 + O-01/O-14 polish) |

**Open audit themes:** Insights control density (W5/W6), spacing hardening (O-31–O-35), Trends tab consolidation (W6).

**Scoring:** 0 = no friction, 3 = high friction (per criterion); **Total** = sum of 6 criteria (max 18)

### Scoring criteria

| Criterion             | 0                  | 3                            |
| --------------------- | ------------------ | ---------------------------- |
| **Notwendigkeit**     | Required for goal  | Could be removed             |
| **Redundanz**         | Unique             | Duplicated elsewhere         |
| **Kognitive Last**    | Obvious next step  | User must guess              |
| **Kontextbruch**      | Same context       | Route/sheet/tab switch       |
| **Leerzustand**       | Clear CTA          | Dead end                     |
| **Maturity-Mismatch** | Matches user state | Feature shown too early/late |

### Optimization classes

`Eliminieren` | `Vorverlagern` | `Zusammenführen` | `Vereinfachen` | `Umleiten` | `Nicht ändern`

---

## W1: Account & Vertrauen

**Viewport:** Mobile + Desktop (identical auth layout)

| #   | Route                | UI element                           | User action                   | System reaction                     | Required | Taps | Est. time | N   | R   | K   | C   | L   | M   | Total | Class          | Proposal                                   | ADR conflict |
| --- | -------------------- | ------------------------------------ | ----------------------------- | ----------------------------------- | -------- | ---- | --------- | --- | --- | --- | --- | --- | --- | ----- | -------------- | ------------------------------------------ | ------------ |
| 1   | `/auth/register`     | Email, display name, password fields | Fill form                     | Password strength indicator updates | yes      | 0    | 30s       | 0   | 0   | 0   | 0   | 0   | 0   | 0     | Nicht ändern   | —                                          | no           |
| 2   | `/auth/register`     | Submit button                        | Tap submit                    | Redirect to check-email             | yes      | 1    | 2s        | 0   | 0   | 0   | 1   | 0   | 0   | 1     | Nicht ändern   | —                                          | no           |
| 3   | `/auth/check-email`  | Static message                       | Read inbox instruction        | None                                | yes      | 0    | 10s       | 0   | 0   | 1   | 1   | 0   | 0   | 2     | Vereinfachen   | Inline "open mail app" deep link on mobile | no           |
| 4   | Email client         | Verification link                    | Tap link                      | Opens `/auth/verify-email?token=`   | yes      | 1    | 5s        | 0   | 0   | 0   | 2   | 0   | 0   | 2     | Nicht ändern   | Context switch unavoidable                 | no           |
| 5   | `/auth/verify-email` | Confirm button                       | **Manual** tap (anti-scanner) | Token verified                      | yes      | 1    | 3s        | 1   | 0   | 1   | 0   | 0   | 0   | 2     | Nicht ändern   | Deliberate ADR-0004 / DSGVO pattern        | no           |
| 6   | `/auth/verify-email` | "Go to login" link                   | Tap                           | Navigate to login                   | yes      | 1    | 2s        | 1   | 0   | 0   | 1   | 0   | 0   | 2     | Zusammenführen | Auto-login after verify (if session safe)  | needs ADR    |
| 7   | `/auth/login`        | Email + password                     | Fill + submit                 | Cookie session, redirect `?next=`   | yes      | 1    | 15s       | 0   | 0   | 0   | 1   | 0   | 0   | 1     | Nicht ändern   | —                                          | no           |

**W1 summary:** 7 GUI steps, ~4 screens, **12 friction points**. Highest impact: post-verify login is a separate step (class `Zusammenführen`).

**Quick wins:** Mobile mail-app deep link on check-email (score reduction ~2).

---

## W2: Cold Start / Onboarding

**Viewport:** Mobile-primary (no AppNav)

| #   | Route                | UI element             | User action           | System reaction                                | Required | Taps | Est. time | N   | R   | K   | C   | L   | M   | Total | Class        | Proposal                                 | ADR conflict |
| --- | -------------------- | ---------------------- | --------------------- | ---------------------------------------------- | -------- | ---- | --------- | --- | --- | --- | --- | --- | --- | ----- | ------------ | ---------------------------------------- | ------------ |
| 1   | `/`                  | Dashboard load         | Wait                  | Auto-redirect to `/onboarding` if 0 entries    | yes      | 0    | 2s        | 0   | 0   | 1   | 1   | 0   | 0   | 2     | Umleiten     | Deep-link new users directly post-login  | no           |
| 2   | `/onboarding` step 0 | Intro panel            | Read                  | —                                              | optional | 0    | 15s       | 1   | 0   | 1   | 0   | 0   | 0   | 2     | Vorverlagern | Merge intro into first entry CTA on Home | no           |
| 3   | `/onboarding` step 0 | Skip / Continue        | Tap                   | Skip → complete with 0 tags; Continue → step 1 | yes      | 1    | 2s        | 0   | 0   | 0   | 0   | 0   | 0   | 0     | Nicht ändern | —                                        | no           |
| 4   | `/onboarding` step 1 | Tag suggestion groups  | Scroll + select chips | Selection map updates                          | optional | 3–8  | 45s       | 1   | 0   | 1   | 0   | 0   | 0   | 2     | Vorverlagern | Tag picker in first EntrySheet instead   | no           |
| 5   | `/onboarding` step 1 | Custom tag input       | Type + add            | Chip added                                     | optional | 2    | 20s       | 1   | 0   | 1   | 0   | 0   | 0   | 2     | Vorverlagern | Same as above                            | no           |
| 6   | `/onboarding` step 1 | Skip / Continue        | Tap                   | → step 2 or skip                               | yes      | 1    | 2s        | 0   | 0   | 0   | 0   | 0   | 0   | 0     | Nicht ändern | —                                        | no           |
| 7   | `/onboarding` step 2 | Summary chips          | Review                | —                                              | optional | 0    | 10s       | 1   | 0   | 1   | 0   | 0   | 0   | 2     | Eliminieren  | Skip summary if ≤3 tags selected         | no           |
| 8   | `/onboarding` step 2 | "Start tracking"       | Tap                   | `POST /onboarding/complete` → `/`              | yes      | 1    | 2s        | 0   | 0   | 0   | 1   | 0   | 0   | 1     | Nicht ändern | —                                        | no           |
| 9   | `/`                  | Home (post-onboarding) | See empty brief       | No entry yet — must tap CTA                    | yes      | 0    | 3s        | 0   | 0   | 2   | 0   | 1   | 0   | 3     | Vorverlagern | Land on open EntrySheet after onboarding | no           |

**Legacy path friction (if user hits deep link):**

| Route                 | Issue                                                                    | Total | Class                    |
| --------------------- | ------------------------------------------------------------------------ | ----- | ------------------------ |
| `/onboarding/retro`   | 7-day mood grid before profile; bypassed by ADR-0030 but still reachable | 8     | Eliminieren or redirect  |
| `/onboarding/profile` | Optional questionnaire after retro; sets profile flag separately         | 6     | Eliminieren (deprecated) |

**W2 summary:** 9 primary steps before first entry, **~2 min** if user selects tags. **Time-to-first-entry** is the main optimization target.

---

## W3: Tägliche Eingabe

### Mobile (390×844) — EntrySheet path

| #   | Route | UI element              | User action                  | System reaction                        | Required | Taps | Est. time | N   | R   | K   | C   | L   | M   | Total | Class        | Proposal                             | ADR conflict |
| --- | ----- | ----------------------- | ---------------------------- | -------------------------------------- | -------- | ---- | --------- | --- | --- | --- | --- | --- | --- | ----- | ------------ | ------------------------------------ | ------------ |
| 1   | `/`   | App load + dashboard    | Wait                         | Today context, brief, sparkline render | yes      | 0    | 2s        | 0   | 0   | 0   | 0   | 0   | 0   | 0     | Nicht ändern | —                                    | no           |
| 2   | `/`   | "Log today" CTA         | Tap                          | `EntrySheet` opens (bottom sheet)      | yes      | 1    | 1s        | 0   | 0   | 0   | 0   | 0   | 0   | 0     | Nicht ändern | Primary mobile path                  | no           |
| 3   | Sheet | Mood slider (default 3) | Adjust or accept default     | Auto-save scheduled (800ms)            | yes      | 0–2  | 5s        | 0   | 0   | 0   | 0   | 0   | 0   | 0     | Vereinfachen | Smart default from yesterday         | no           |
| 4   | Sheet | Energy / stress sliders | Optional adjust              | Debounced save                         | optional | 0–4  | 10s       | 0   | 0   | 0   | 0   | 0   | 0   | 0     | Nicht ändern | Defaults OK for 60s rule             | no           |
| 5   | Sheet | Work context chips      | Optional tap                 | Field updates                          | optional | 0–1  | 3s        | 0   | 0   | 0   | 0   | 0   | 0   | 0     | Nicht ändern | Auto-default by weekday              | no           |
| 6   | Sheet | Tags + symptoms         | Select without expand (O-21) | Tags/symptoms auto-save                | optional | 0–3  | 15s       | 0   | 0   | 0   | 0   | 0   | 0   | 0     | Nicht ändern | Core fields always visible on mobile | no           |
| 7   | Sheet | Note/cycle toggle       | Tap (compact mode only)      | Note + cycle fields visible            | optional | 0–1  | 2s        | 0   | 0   | 0   | 0   | 0   | 0   | 0     | Nicht ändern | Rare fields stay behind disclosure   | no           |
| 8   | Sheet | SaveStatusBadge         | Observe                      | "Saved" confirmation                   | yes      | 0    | 1s        | 0   | 0   | 0   | 0   | 0   | 0   | 0     | Nicht ändern | ADR-0013                             | no           |
| 9   | Sheet | Close (swipe/down)      | Dismiss sheet                | Returns to Home; dashboard refreshes   | yes      | 1    | 1s        | 0   | 0   | 0   | 0   | 0   | 0   | 0     | Nicht ändern | —                                    | no           |

**Mobile minimum path:** 2 taps (open sheet, close), ~10s with defaults — **within 60s rule**.

### Desktop (1280×900) — same EntrySheet OR `/entries/new`

| #                                       | Issue                                                | Total | Class          | Proposal                                                    |
| --------------------------------------- | ---------------------------------------------------- | ----- | -------------- | ----------------------------------------------------------- |
| Dual entry surfaces                     | Sheet vs full page causes inconsistent muscle memory | 4     | Zusammenführen | Default desktop to `/entries/new` workspace or always sheet |
| Page mode shows theme toggle + back nav | Extra chrome vs sheet                                | 2     | Vereinfachen   | Phase 5 desktop workspace polish                            |
| Empty Trends CTA → `/entries/new`       | Context break from Trends                            | 3     | Umleiten       | Open EntrySheet inline where possible                       |

**W3 summary:** Mobile path is lean (no extra tap for tags/symptoms since O-21). Desktop dual-surface is main friction.

---

## W5: Erste Erkenntnis

**Simulated phases:** `collecting` (3 entries), `early_patterns` (9 entries), `provisional` (21 entries)

### Phase: `collecting` (1–6 entries)

| #   | Route       | UI element              | User action              | System reaction    | N   | R   | K   | C   | L   | M   | Total | Class        | Proposal                            |
| --- | ----------- | ----------------------- | ------------------------ | ------------------ | --- | --- | --- | --- | --- | --- | ----- | ------------ | ----------------------------------- |
| 1   | `/`         | HomeDailyBrief          | Read phase fallback copy | No insight card    | 0   | 0   | 1   | 0   | 0   | 0   | 1     | Vereinfachen | Show entries-until-milestone inline |
| 2   | `/`         | Sparkline (sparse)      | Glance                   | May show flat line | 0   | 0   | 1   | 0   | 1   | 0   | 2     | Vereinfachen | Hide sparkline until ≥3 points      |
| 3   | `/insights` | InsightStageHeader      | Read maturity meter      | Phase 1 badge      | 0   | 2   | 1   | 0   | 0   | 0   | 3     | Eliminieren  | Single maturity block (see W6)      |
| 4   | `/insights` | InsightFeed empty state | Read CTA                 | Links back to Home | 0   | 1   | 0   | 1   | 0   | 0   | 2     | Umleiten     | CTA opens EntrySheet directly       |

### Phase: `early_patterns` (7–13 entries)

| #   | Route       | UI element                       | Total | Class        | Proposal                                      |
| --- | ----------- | -------------------------------- | ----- | ------------ | --------------------------------------------- |
| 1   | `/`         | FirstWeekInsightBanner           | 2     | Vereinfachen | Dismissible; OK                               |
| 2   | `/`         | HomeDailyBrief with insight      | 0     | Nicht ändern | —                                             |
| 3   | `/insights` | MobileInsightLead + stage header | 4     | Eliminieren  | Redundant lead + header (FRONTEND_STREAMLINE) |
| 4   | `/insights` | First insight card               | 0     | Nicht ändern | —                                             |
| 5   | `/insights` | Disclaimer link                  | 1     | Nicht ändern | Trust requirement                             |

### Phase: `provisional` (14–29 entries)

| #                             | Issue | Total             | Class                                       | Proposal |
| ----------------------------- | ----- | ----------------- | ------------------------------------------- | -------- |
| Matrix tab visible but sparse | 3     | Maturity-Mismatch | Hide matrix until ≥2 pointbiserial insights |
| Co-occurrence section empty   | 2     | Leerzustand       | Collapse until data exists                  |

**W5 summary:** Main friction is **duplicate maturity UI** on Insights (scores 3–4 per visit).

---

## W6: Wöchentliche Analyse

### Mobile (390×844)

| #   | Route       | Tab/view          | User action                 | Total                                | Class        | Proposal       |
| --- | ----------- | ----------------- | --------------------------- | ------------------------------------ | ------------ | -------------- | ------------------------------------------------------ |
| 1   | `/trends`   | Compare (default) | MobileTrendsSummary loads   | 0                                    | Nicht ändern | —              |
| 2   | `/trends`   | Summary card      | Tap detail                  | Opens detail canvas                  | 1            | Nicht ändern   | Expected drill-down                                    |
| 3   | `/trends`   | Health tab        | Switch tab                  | Tag + symptom heatmaps               | 1            | Nicht ändern   | —                                                      |
| 4   | `/trends`   | Heatmap cell      | Tap date                    | EntryHistorySheet or `/entries/day/` | 2            | Umleiten       | Prefer sheet to avoid route break                      |
| 5   | `/insights` | Findings tab      | Switch nav tab              | New page load                        | 2            | Zusammenführen | Cross-link Trends ↔ Insights top finding               |
| 6   | `/insights` | Matrix tab        | Toggle view                 | Second maturity context              | 3            | Eliminieren    | Matrix behind single "Details" per FRONTEND_STREAMLINE |
| 7   | `/insights` | Category filter   | Tap All/Mood/Symptoms/Sleep | Feed filters                         | 0            | Nicht ändern   | —                                                      |
| 8   | `/insights` | Symptom analytics | Scroll + expand             | Co-occurrence sheets                 | 1            | Nicht ändern   | Progressive disclosure                                 |

### Desktop (1280×900)

| #                                        | Issue | Total          | Class                                      | Proposal                  |
| ---------------------------------------- | ----- | -------------- | ------------------------------------------ | ------------------------- |
| Trends Compare + Health on separate tabs | 2     | Zusammenführen | Shared time axis (partially done ADR-0035) |
| Insights analysis-first layout           | 0     | Nicht ändern   | —                                          |
| Range selector repeated per tab          | 2     | Vereinfachen   | Global range control sticky in header      | **Erledigt** (O-15, O-23) |

**W6 summary:** Mobile requires **2 nav tabs** (Trends + Insights) for full weekly review — consider Home brief as bridge.

---

## W7: Habit-Review

**Prerequisite:** Tag with `habit_type: build|reduce` in `/settings/tags`

| #   | Route            | UI element                    | User action             | Total                | Class        | Proposal                                       |
| --- | ---------------- | ----------------------------- | ----------------------- | -------------------- | ------------ | ---------------------------------------------- | --- |
| 1   | `/settings/tags` | Habit type + target frequency | Configure (first time)  | 2                    | Vorverlagern | Suggest habit setup during onboarding tag step |
| 2   | `/trends`        | Habits tab                    | Switch from Compare     | 1                    | Nicht ändern | —                                              |
| 3   | `/trends`        | HabitsPanel empty             | Read CTA → settings     | 3                    | Umleiten     | Inline "add habit" mini-flow                   |
| 4   | `/trends`        | Habit adherence %             | Review calendar heatmap | 0                    | Nicht ändern | No streak — ADR compliant                      |
| 5   | `/trends`        | Habit detail expand           | Tap habit row           | Stats for 28d window | 0            | Nicht ändern                                   | —   |

**W7 summary:** Setup friction (step 1) dominates; review path is clean once habits exist.

---

## W4, W8, W9, W10 — Summary scores

| Workflow                | Steps | Total friction | Top issue                            | Priority |
| ----------------------- | ----- | -------------- | ------------------------------------ | -------- |
| W4 Rückdatierte Eingabe | 5     | 4              | Full page vs sheet inconsistency     | medium   |
| W8 Vokabular            | 6     | 3              | Settings → sub-page navigation       | low      |
| W9 Export               | 4     | 2              | Export buried in Settings scroll     | low      |
| W10 PWA                 | 5     | 5              | Install prompt timing vs first entry | medium   |

---

## Cross-cutting friction themes

| Theme                         | Affected workflows | Aggregate score | Recommended class                    | Status (2026-07-01) | Tickets                      |
| ----------------------------- | ------------------ | --------------- | ------------------------------------ | ------------------- | ---------------------------- |
| Auth funnel length            | W1                 | high            | Zusammenführen (verify → auto-login) | **Erledigt**        | O-07, O-11, O-20             |
| Onboarding before first entry | W2                 | high            | Vorverlagern                         | **Erledigt**        | O-02, O-04, O-06, O-37 ✅    |
| Dual entry surfaces           | W3, W4             | medium          | Zusammenführen                       | **Erledigt**        | O-08 ✅, O-38 ✅             |
| Duplicate maturity UI         | W5, W6             | high            | Eliminieren                          | **Erledigt**        | O-01, O-14, O-22 ✅, O-34 ✅ |
| Legacy onboarding routes      | W2                 | medium          | Eliminieren                          | **Erledigt**        | O-04                         |
| Analysis split across 2 tabs  | W6                 | medium          | Umleiten (Home brief bridge)         | **Erledigt**        | O-41 ✅                      |
| Habit setup not in onboarding | W7                 | medium          | Vorverlagern                         | **Erledigt**        | O-09 ✅ (O-16 done)          |
| No password reset             | W1                 | medium          | Backend scope                        | **Erledigt**        | O-20                         |
| Mobile spacing / density      | W3–W6              | medium          | Vereinfachen                         | **Erledigt**        | O-30 ✅, O-31–O-35 ✅        |
| Entry core fields hidden      | W3                 | medium          | Vereinfachen                         | **Erledigt**        | O-21                         |

---

## Prioritized optimization backlog

**Phase 1 (O-01–O-20):** complete — see [`OPTIMIZATION_BACKLOG.md`](OPTIMIZATION_BACKLOG.md).

**Phase 2 (O-21–O-42):** complete — see [`GUI_OPTIMIZATION_PHASE2.md`](GUI_OPTIMIZATION_PHASE2.md).

### Phase 2 closure (July 2026)

1. **O-01** — Page-level maturity chrome OR per-card badge on Insights, never both
2. **O-14** — Matrix tab and co-occurrence panels gated by maturity and data presence

### Phase 1 quick wins (historical — all shipped)

1. **O-02** Vorverlagern open EntrySheet after onboarding complete
2. **O-03** Umleiten Insights empty-state CTA → EntrySheet
3. **O-04** Eliminieren legacy onboarding routes
4. **O-05** Vereinfachen hide Home sparkline until ≥3 entry points

---

## ADR compliance check

| Proposal                     | ADR / rule                            | Conflict?                                    |
| ---------------------------- | ------------------------------------- | -------------------------------------------- |
| O-01 single maturity block   | ADR-0021 (phases must remain visible) | No — consolidate display, keep phase model   |
| O-06 tags in first entry     | ADR-0030                              | Needs ADR update if onboarding route removed |
| O-07 auto-login after verify | ADR-0004                              | Yes — requires ADR amendment                 |
| O-08 unified entry surface   | ADR-0017 (entry not a tab)            | No                                           |
| Streak counters              | DESIGN_DOCUMENT §1.4                  | **Never** — adherence % only                 |

---

## Evidence

| Workflow | Code audit                                     | E2E coverage                                               |
| -------- | ---------------------------------------------- | ---------------------------------------------------------- |
| W1       | `routes/auth/*`                                | `user-journeys.spec.ts` (new)                              |
| W2       | `routes/onboarding/+page.svelte`               | `user-journeys.spec.ts` (new)                              |
| W3       | `EntryForm.svelte`, `+page.svelte`             | `mobile-entry-foundation.spec.ts`, `user-journeys.spec.ts` |
| W5–W7    | `insights/+page.svelte`, `trends/+page.svelte` | `user-journeys.spec.ts` (maturity fixtures)                |

**Automated regression:** `pnpm --filter @correlcore/web exec playwright test tests/e2e/user-journeys.spec.ts`

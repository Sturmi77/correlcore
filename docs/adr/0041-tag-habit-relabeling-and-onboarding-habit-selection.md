# ADR-0041: Tag/Habit Relabeling and Habit Selection in Onboarding

Date: 2026-07-27

## Status

Proposed

Immediate mitigation shipped separately: the onboarding `ConceptExplainer` copy
now states that a habit is a tag with a goal (#552, Option 2). This ADR captures
the target design for the actual relabeling/flow work (#552, Option 3), to be
implemented later under its own follow-up issue.

## Context

The three core tracking concepts are **not equal-ranked** in the data model, yet
the UI presents them as parallel:

- **Tag** and **Habit** are **not separate objects.** A habit is a **tag with
  `habit_type` = build/reduce + `target_frequency`** (ADR-0012), created by
  marking an existing tag in Settings → Tags
  ([`settings/tags/+page.svelte`](../../apps/web/src/routes/settings/tags/+page.svelte)).
  In onboarding the user picks **only tags**.
- **Symptom** is a **separate object** (symptom master table, ADR-0008), captured
  per entry via `SymptomChecker`.
- The onboarding `ConceptExplainer`
  ([`ConceptExplainer.svelte`](../../apps/web/src/lib/components/onboarding/ConceptExplainer.svelte))
  lists Tag / Habit / Symptom as parallel terms — good for first-time teaching,
  but it can imply that "Habit" is a separately selectable type, which it is not.

The copy clarification (#552 Option 2) reduces confusion but does not make the
hierarchy (Tag ⊃ Habit) visible in the flow, and onboarding still offers no way
to set a goal.

## Decision (target design)

1. **Surface Habit as a Tag property, not a peer type.** In the UI, a habit is
   reached via a tag ("Tag → track as a habit / set a goal"), making the
   hierarchy Tag ⊃ Habit explicit. Terminology across onboarding, Settings →
   Tags, Trends, and Insights must be consistent with this.
2. **Onboarding must let users select/mark Habits, not only Tags.** The onboarding
   sequence gains an optional affordance to turn a picked tag into a habit
   (set `habit_type` build/reduce + `target_frequency`) — either an inline
   "set a goal" control on the tag step or a dedicated optional step after tag
   selection. It reuses the existing `habit_type` / `target_frequency` model and
   endpoints already used by Settings → Tags; it does not introduce a new object.
3. **No new data model.** Habits remain tags with habit fields (ADR-0012). This
   ADR is terminology + flow only.

## Constraints

- Non-gamification (no streak/reward/badge/fire framing; the
  `noGamificationCopy` test guards locale strings) and non-medical tone.
- Keep the mandatory onboarding sequence lean (see the onboarding-sequence work,
  #560) — the habit affordance is **optional** and must not block reaching the
  first entry.
- DE/EN locale parity for any new copy.

## Acceptance criteria (for the follow-up implementation)

- [ ] `ConceptExplainer` / onboarding copy present Habit as a facet of Tag.
- [ ] Onboarding offers an optional "track as habit / set a goal" affordance that
      writes `habit_type` + `target_frequency` via the existing tag endpoints.
- [ ] Terminology aligned across onboarding, Settings → Tags, Trends, Insights.
- [ ] i18n DE/EN; `noGamificationCopy` + locale-parity tests green.
- [ ] UX copy review (no gamification, non-medical).

## Consequences

- Clearer mental model (Tag ⊃ Habit) and habit setup reachable during onboarding.
- More onboarding surface area and copy to maintain; mitigated by keeping the
  habit affordance optional and reusing existing habit endpoints.

## Status update — onboarding habit selection shipped (2026-07-27)

The onboarding side of this ADR is implemented (#564): an optional **Goals** step
after tag selection lets users mark a picked tag as a build/reduce habit with a
weekly target, sent atomically via the extended `/onboarding/complete` contract
(reusing `TagCreate`/`update_custom_tag`). The remaining "terminology sweep" was
audited but deliberately **not** bundled here (kept focused).

### Terminology audit (for the future sweep)

- **Settings → Tags** copy is already tag-property-aware: `settings.tags.habits_body`
  = "Mark tags as build or reduce habits…", `habit_hint` = "Tags … can later be
  marked as … habits". No change needed.
- **Trends** exposes a first-class **"Habits" tab** (`trends.tabs.habits`,
  `HabitsPanel`) — a legitimate analytics grouping of habit-tags, but the bare
  label reads as a peer type. Candidate: a subtitle/tooltip clarifying "tags you
  track as habits".
- **ConceptExplainer** still lists Tag/Habit/Symptom as parallel terms
  (teaching), mitigated by the #552 copy ("a habit is a tag with a goal").
- **Nav / Insights**: no standalone "Habit" object framing found.

**Verdict:** residual peer-type framing is light (Trends tab + concept ordering);
a small consistency pass is worthwhile but low-priority → tracked as a separate
follow-up issue rather than blocking #564.

## References

ADR-0012 (tracking semantics + habit adherence), ADR-0008 (symptom master table),
ADR-0025 (symptom analytics) · #541 (definitions, done), #552 (relabeling, done),
#564 (onboarding habit selection) · #547 (cycle feature) · M10.2 onboarding plan
(Phase 3, O5 analysis).

# ADR-0043 Addendum A (DRAFT) — Personal questions, answer states and evidence language

## Status

**Draft for #1023 (Z1.4).** Not accepted. Amends [ADR-0043](../adr/0043-insight-surface-layers.md) (keeps the four layers) and prepares the sync of the documents listed in the [target picture §8](INSIGHT_USER_VALUE_TARGET_2026-09-29.md). Nothing here has been user-tested yet; the early tests in Z1.4 are the gate. The UI decisions below come from six prototype rounds with synthetic data (`docs/assets/insight_value_mockups/`); those are design choices, not evidence of user value.

## Context

The four layers (answer → check → deeper analysis → report) answer _where_ density belongs. They do not say what a user can ask, what an answer to a personal question consists of, or how a non-result and a data gap are told apart from an error. The user-value plan adds a personal question as an optional entry point. Two constraints from the engine shape the design ([capability matrix draft](INSIGHT_Z1_1_CAPABILITY_MATRIX_DRAFT.md), [lag evidence gap](INSIGHT_LAG_EVIDENCE_GAP_993.md)):

- The engine supports a fixed set of signal pairs and methods; free text cannot be analysed.
- Lagged analysis exists only for 1–7 days, needs ≥ 90 entries, and its evidence contract lacks group frequencies, pair counts and the profile.

## Decision

### 1. A personal question links two signals

A question connects two of: **tag** (incl. custom), **symptom**, **value** (mood, energy, stress), sleep, weekday. One grammar covers all pair types. The sentence shown to the user is generated from a per-type template in natural language ("How is my energy 2 days after sport?", "Does headache occur more often on days with coffee?"). There is **no free-text analysis**; an optional private title never changes analysis parameters.

### 2. Roles are derived, order is irrelevant

Users pick two things in any order; the app assigns reference and target. Values are targets; sleep and weekday are references; a symptom is the target when paired with a tag and the reference when paired with a value. Only tag↔tag and symptom↔symptom are symmetric (a duplicate in reverse order is the same question).

### 3. Time is a second, equal choice

Same day, a fixed lag of 1–7 days, or **open lag** (compare seven distances, report the most distinct). Open lag ships in the first release with a mandatory disclosure: the profile of all seven distances is shown, the winner is marked, and the card states that seven distances were compared. It is never started automatically for a saved question. Lag requires ≥ 90 entries; below that the state is "not enough entries for lag", with a reason, before saving.

### 4. Excluded in the first release

Value↔value (use the correlation matrix), a value as the lag starting point (direction high/low unresolved), tags as the later signal, tag↔tag with lag, free-text analysis, causal wording.

### 5. Three entrances, one confirmation

"Choose a suggestion" and "Create a question" are **equal peers** on the same level (empty state, next to the question list, tabs in the sheet). "Remember this question" on an observation is the third entrance. All three end in the same confirmation: generated sentence, support status, optional title, focus decision.

### 6. Several questions, one focus, never a silent change

Users may save several questions and set one as focus. Saving pre-selects "set as focus" only for the first question. Any focus change shows a message with undo. Unsupported questions are not saved and offer the nearest supported variant; questions with a data gap can be saved with a visible data status.

### 7. The answer card is one pattern for all question types

Question → state → sentence → frequency bars ("7 of 10 vs. 7 of 18") → caveat → reasoned next step. Events use the engine's definition ("good day": mood/energy ≥ 4, stress ≤ 2; or "symptom present"); the card says "days with good energy" / "days with little stress". Days, not entries, are counted. A correlation coefficient is never presented as a difference in scale points.

### 8. Four states plus independent technical states

Data basis insufficient · still unclear · pattern observed · no clear pattern, as in the target picture. Technical states (loading, stale, unsupported, budget, unavailable) stay independent; a timeout is never "no pattern". A data gap shows counts (bars in days) and no promise of certainty after N more days. A non-result offers three equal paths (keep observing, choose another question, add to report).

### 9. Detail view in five steps

What was observed → how large is the difference → what is it based on → what else could play a role → what helps next. A context sentence appears only when a context check was computed; otherwise the view says none is available and that this does not rule out other influences.

### 10. Report is its own tab

Selection is explicit; "add to report" does not navigate. Non-results and data status are selectable but labelled as such; an error is never exported as a non-result; an empty or invalid selection selects nothing else. Question, state, period, answer, caveat and the group table appear in PDF/PNG; CSV/JSON carry the same values.

### 11. Continuous signals: the threshold is part of the contract

For sleep the engine splits at the **median of the user's own values**. The UI says "shorter than your median of 7 h 10 min"; value, unit, feature (duration or quality) and as-of date are contract fields (`event.split`), not UI constants.

## Consequences

- Z1.1 becomes a matrix over signal kind × signal kind × time × method, with classes U / UV / D / N / P.
- The evidence contract needs a lag v2 and evidence families for co-occurrence, weekday and sleep (gap G1–G11). Until then, cards for those question types cannot be filled from the contract.
- Analysis per saved question needs its own budget; the Top-10 finding feed cannot back saved questions (G5, Z3.2).
- Symptom questions need a wording rule: "recorded more often", never a diagnosis; symptom names are encrypted at rest (ADR-0005), so saved questions store IDs.
- The first release deliberately offers fewer combinations than the engine holds internally.

## Alternatives considered

- **Free-text question box:** rejected; it promises analysis that does not exist.
- **Only suggestions or only a builder:** each fails one group (no prior knowledge vs. custom tags); equal peers cover both.
- **Question only from an observation:** no entry when nothing was found, contradicting "a question without a hit".
- **One focused question only:** rejected after user feedback; several saved questions, one focus.
- **Automatic open-lag search for every saved question:** rejected (multiple testing, budget, hunting for a hit).
- **Fixed sleep guideline (e.g. 6 h):** possible, but the engine does not compute it; would need a new method.

## Open questions

1. "What came first?" prompt only for symptom↔symptom, or always visible.
2. Sleep duration vs. quality as the meaning of "little sleep".
3. Which values the weekday pattern actually covers.
4. Whether the sleep median or a fixed guideline reads better in the early user tests.
5. Family of multiple tests for a personal question (matrix-wide today).

## References

Target picture, findings U01–U18, capability matrix draft, lag evidence gap, prototypes `runde2`–`runde6`, issues #1017, #1020, #1021, #1023, #1024, #1028.

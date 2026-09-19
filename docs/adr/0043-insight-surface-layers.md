# ADR-0043 — Insight Surface Layers (depth on demand)

## Status

Accepted (2026-09-19)

Amends and supersedes parts of [ADR-0017](0017-frontend-screen-architecture.md)
(see "Relationship to ADR-0017" below). Context: analysis issues
[#928](https://github.com/Sturmi77/correlcore/issues/928),
[#930](https://github.com/Sturmi77/correlcore/issues/930),
[#931](https://github.com/Sturmi77/correlcore/issues/931).

## Context

The visualization inventory in
[`../frontend/VISUALIZATION_INVENTORY_2026-09-17.md`](../frontend/VISUALIZATION_INVENTORY_2026-09-17.md)
catalogued 19 visualization forms across the product and compared them against the six
questions users actually ask. It found seven overlaps and nine gaps. The overlaps and gaps
share one cause, and it is not a missing chart type:

**Analytical seriousness is currently signalled through density in the entry surface.**

Evidence in the code at the time of writing:

- `DEFAULT_INSIGHT_SECTIONS` (`apps/web/src/lib/utils/insightSections.ts`) enables **eight**
  sections by default, with `correlation_matrix` ordered **before** `insight_feed`.
- No surface answers the question "is this claim actually true?". The most common insight
  type (`pointbiserial`) has no visual counterpart: there is no scatter plot anywhere in
  `apps/web/src`, and no with/without distribution comparison.
- A non-result ("X changed nothing") cannot be expressed at all, so the product can only
  ever show findings — which structurally biases it towards the accidental finding.
- `pdf` appears in neither `apps/web/src` nor `backend/app`. CSV/JSON/ZIP export lives in
  `/settings/data` (a GDPR surface); PNG export lives _inside_ `InsightMatrix.svelte`
  (`exportPng()`). The "export for a doctor's appointment" job named as _critical_ in
  DESIGN_DOCUMENT §2.10 has no home.

Adding or removing individual components cannot resolve this, because each of the 19 forms
has a defensible technical strength. What is missing is a rule that decides **where**
density is allowed. Without such a rule, every new analytical feature lands as another
default section in `/insights`, and ADR-0017's instruction to make the matrix a secondary
drilldown stayed unimplemented for two sprints because no surface existed to receive it.

## Decision

### 1. Four surface layers, density bound to intent

CorrelCore organises analytical surfaces into four layers. The guiding principle is
**depth on demand instead of density at the entrance**.

| Layer | Name             | Job                                                                | Density                                                        | Today                         |
| ----- | ---------------- | ------------------------------------------------------------------ | -------------------------------------------------------------- | ----------------------------- |
| 1     | **Answer**       | State what was found, in one sentence, in natural language         | Minimal — one statement, one window, one confidence vocabulary | `/` and `/insights` exist     |
| 2     | **Verification** | Make a single hypothesis checkable: with/without, course, raw data | Medium, progressive disclosure                                 | **Does not exist**            |
| 3     | **Laboratory**   | Let the user dig: compare metrics, tags, windows                   | High — density is correct here, because the user chose it      | `/trends` exists              |
| 4     | **Report**       | Produce something to take away (doctor, therapist, own records)    | High — a printout is supposed to be a table                    | **Two fragments, no surface** |

Rules:

- A component's technical strength is an argument against **deleting** it. It is never an
  argument for **default presence** in layer 1.
- Every layer-1 statement must offer exactly one forward path into layer 2. Layer 1 does
  not offer a choice between multiple charts of the same fact.
- Layer 3 must always show which time window is active. Two arrows on two surfaces must
  never silently mean different windows.
- Layer 4 is the only place where export lives. Export controls must not be embedded in
  analytical components.

### 2. Layers are secondary surfaces, not new primary screens

ADR-0017 fixes **five primary screens** and requires an ADR for any addition. This ADR does
not add a primary screen. Layers 2 and 4 are drilldowns inside the existing insights route:

- Layer 2: a signal detail surface reached from an insight card (e.g.
  `/insights/signal/[id]`), and reachable from `/trends` compare via a "check this
  question" affordance.
- Layer 4: a report surface (e.g. `/insights/report`) that unifies PDF, PNG, CSV and JSON.

Bottom navigation stays at Home, Insights, Trends, Settings.

### 3. Layers form one stack per account, not one home per segment

The four layers are **not** mapped 1:1 onto user segments. The same person uses layer 1 on
a weekday morning and layer 4 before a doctor's appointment. The relation between segments
and layers is n:n. A segment must therefore never be used to justify hiding a layer, and a
layer must never be described as belonging to a persona (see #930 G6).

### 4. Evidence language

Across all four layers, effects are expressed as **natural frequencies with two
denominators** ("good on 24 of 34 days with sport · good on 29 of 56 days without"). Lift,
p-values and FDR remain internal gating criteria and expert detail behind disclosure; they
are not the primary statement. Correlation-with-offset ("time offset") and presence
sequence ("sequence") are named as two distinct things and never merged into one label.

### 5. A non-result is a result

Layer 2 must be able to state that a hypothesis did not hold, with the same visual weight
as a finding, plus a next action. This is a positioning decision, not a chart: a product
that can only show findings has to manufacture them.

**Consequence for the success metrics:** DESIGN_DOCUMENT §1.6
"Time-to-First-Insight < 14 days" becomes counter-productive under this rule, because it
rewards producing a finding. It is redefined as **Time-to-First-Answer** — the first
defensible statement, finding _or_ non-finding.

### 6. Reducing layer 1 requires a landing place and a migration

Removing a section from the layer-1 default is only permitted when the component has a
surface to move to. Specifically, `correlation_matrix` may only be removed from the default
once the layer-4 report surface exists, because `exportPng()` lives inside that component
and would otherwise disappear with it.

Furthermore, changing `DEFAULT_INSIGHT_SECTIONS` does **not** reach existing users:
`merge()` in `apps/web/src/lib/utils/sectionPreferences.ts` treats stored preferences as
authoritative and only appends missing keys. The only effective lever — removing the key
from `validKeys` so `coerce()` drops it — discards the key for _everyone_, including users
who deliberately enabled and reordered the section. Any reduction of layer 1 is therefore a
**versioned preference migration** with an explicit acceptance criterion, not a default
flip.

## Alternatives considered

| Option                                                    | Pros                                                                                                     | Cons                                                                                                                                     |
| --------------------------------------------------------- | -------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------- |
| **Keep the status quo** (add charts per feature)          | No architectural work                                                                                    | Entry surface keeps growing; density signals seriousness; overlaps recur with every feature                                              |
| **Delete redundant components**                           | Immediately less clutter                                                                                 | Destroys real analytical capability; each of the 19 forms has a defensible strength; does not answer "where is density allowed"          |
| **Configurable dashboard** (user assembles their own hub) | Maximum flexibility                                                                                      | Shifts the editorial decision onto the user; contradicts the 60-second principle; ADR-0017 already rejected the mini-dashboard direction |
| **Dual strength × confidence metric** (Exist.io model)    | State of the art, compact                                                                                | Too abstract for the target audience — already rejected in ADR-0017; natural frequencies communicate the same thing concretely           |
| **Four layers, density bound to intent** ✅               | Retains capability, gives every component a correct home, makes claims checkable, gives export a surface | Requires two new secondary surfaces (layers 2 and 4) before layer 1 can be reduced                                                       |

## Consequences

- **Layer 2 is the one genuine new build.** It closes the checkability gap and is the
  precondition for the non-result state.
- **Layer 4 must exist before layer 1 is reduced.** It also finally provides a home for the
  §2.10 export job (PDF is still missing everywhere).
- **DESIGN_DOCUMENT §1.6 changes** to Time-to-First-Answer. §2.10 must be corrected
  independently (PNG is implemented; PDF exists in no layer) — see #931.
- **ADR-0017 line "evaluate `InsightMatrix.svelte` … removed or repurposed if redundant"
  is retired by this ADR**: the component is not redundant, it is misplaced. It moves to
  layer 4 as a report table.
- **ADR-0017's M5 amendment** ("the matrix remains a secondary drilldown inside
  `/insights`") is confirmed in intent and made implementable: a drilldown needs a surface,
  and the section model has no "present but not in the entry surface" state.
- Any future analytical feature must name its layer in its issue. A feature without a layer
  defaults to layer 3 (laboratory), never layer 1.
- The five-primary-screen contract of ADR-0017 remains intact.
- Sequencing, gaps and the accompanying mockups (E1–E6) are documented in #928; the
  mockup sources live in
  [`../assets/visualization_inventory/src/mocks_e.py`](../assets/visualization_inventory/src/mocks_e.py),
  the renders in `../assets/visualization_inventory/proposals/`.

## Open questions

- Whether strain/recovery becomes a category anchor (#930 G3) is explicitly **not** decided
  here. It is gated behind layers 1–2 shipping and requires a neutral `work_context` value,
  which the enum currently lacks (#875, #930).
- Exact route names for layers 2 and 4 are set in the implementation issues; this ADR fixes
  only that they are secondary surfaces inside the insights route.
- The interview validation asked for in #930 H.4 remains a gate for the layer-2 build. This
  ADR records the structural decision, not the user research.

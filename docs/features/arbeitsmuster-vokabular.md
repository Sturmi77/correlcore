# Arbeitsmuster-Vokabular — Copy-Register (#930 G3)

> **2026-09-19 (Phase 9):** Activated after Layer 2 (signal detail / non-results)
> and honest time windows shipped, plus `work_context.other` and the opt-in
> Belastung overlay (Phase 7–8). This is a **copy register with a gate**, not a
> category pivot.
>
> **Status**: Canonical wording for product, store listing, and UI
> **Relevant issues**: [#930](https://github.com/Sturmi77/correlcore/issues/930) · [#720](https://github.com/Sturmi77/correlcore/issues/720) · [#721](https://github.com/Sturmi77/correlcore/issues/721) · [#875](https://github.com/Sturmi77/correlcore/issues/875)
> **Relevant ADR**: [ADR-0043](../adr/0043-insight-surface-layers.md)

## Decision (G3)

CorrelCore does **not** rebrand as a burnout or occupational-health product.
When store or marketing copy needs a stronger work-day angle, use this
**Arbeitsmuster** register — patterns in the user’s own entries around load,
recovery, and situation — never clinical inventories or employer framing.

| Keep                                                                   | Do not                                              |
| ---------------------------------------------------------------------- | --------------------------------------------------- |
| Mood / Habit as everyday jobs (W3 / W7)                                | Drop Mood/Habit from listing or IA                  |
| `work_context` as a **field** (label: Arbeitssituation / Work context) | Make `work_context` the Play category or hero title |
| Optional Layer-1 “load & recovery” overlay                             | Parallel burnout information architecture           |
| Patterns, hints, associations                                          | Diagnosis, prevention claims, MBI/CBI               |

## Preferred (use)

| DE                            | EN                            | Where                                                               |
| ----------------------------- | ----------------------------- | ------------------------------------------------------------------- |
| Arbeitsmuster                 | work patterns                 | Positioning / listing prose (not a nav label)                       |
| Belastung / Erholung          | load / recovery               | Overlay + Settings (`insights.belastung.*`, `settings.belastung.*`) |
| Muster / Hinweis              | pattern / hint                | Confidence-light Layer-1 copy                                       |
| Arbeitssituation              | work situation / work context | Entry field + trends (`entry.work_context_*`)                       |
| Zusammenhänge / Assoziationen | associations / correlations   | Insights / store USP                                                |
| Wohlbefinden                  | wellbeing                     | Landing / README / listing                                          |
| Stimmung / Energie / Stress   | mood / energy / stress        | Daily check-in (unchanged)                                          |
| Gewohnheiten                  | habits                        | Trends / Settings (unchanged)                                       |

## Avoid (do not use as product claim)

| Term                                       | Why                                              |
| ------------------------------------------ | ------------------------------------------------ |
| Burnout-Prävention / burnout prevention    | Health-claim + Play-rejection risk (SWOT / #721) |
| Burnout-Score / burnout risk score         | Implies clinical assessment                      |
| Occupational health / B2B wellness         | Product excludes employer views (G5)             |
| “Arbeit” / “Work” as **category title**    | `work_context` is a differentiation field only   |
| Replacing Mood/Habit with Arbeitssituation | W3/W7 remain the daily jobs                      |

### Causal verbs (#928 D4)

An insight is a correlation, so its copy may not name a cause. Use the
Preferred row above — `Zusammenhang mit` / `Associated with` — wherever a
finding relates two things.

| Do not write (as a finding)                                 | Write instead                         |
| ----------------------------------------------------------- | ------------------------------------- |
| wirkt auf · beeinflusst · verursacht · führt zu · sorgt für | Zusammenhang mit · hängt zusammen mit |
| Affects · influences · causes · leads to · results in       | Associated with · linked to           |

Negated disclaimers (“eine Korrelation bedeutet nicht, dass …”, “an
association in your entries, not a cause”) are the point of the surface and
stay required.

## Never (forbidden in UI + store copy)

| Term                                                  | Notes                                                                 |
| ----------------------------------------------------- | --------------------------------------------------------------------- |
| Burnout (as label, score, or diagnosis)               | Allowed only in internal docs / issue titles                          |
| MBI, CBI, ICD burnout codes                           | No clinical inventories                                               |
| Diagnose / diagnosis **as a product capability**      | Negated disclaimers (“keine Diagnose”) stay required                  |
| Arbeitgeber-Auswertung / team dashboard               | G5 exclusion; overlay disclaimer already states never for an employer |
| Medical prediction / fertility / contraception claims | ADR-0033 §9 / Play listing guardrails                                 |

## Field vs register

- **Register name:** Arbeitsmuster-Vokabular — how we talk about load/recovery in
  marketing and Layer-1 overlay copy.
- **Field label:** `Arbeitssituation` / `Work context` — UI for
  `entries.work_context` (including `other`). Do not rename the field to
  “Arbeitsmuster”.
- **Overlay title:** Belastung / Load & recovery — opt-in; heuristic; not a
  store category.

## Store listing (#720) + Data Safety (#721)

- Listing may mention optional load/recovery **patterns from your own entries**
  and work-day context alongside mood, energy, stress, tags, and habits.
- Listing must keep the non-medical note and must **not** use never-terms above.
- Data Safety declares the same Health-info surface as before; the Belastung
  overlay adds **no new Play data types** — it reuses stress, energy, symptoms,
  tags, and `work_context`. See
  [`docs/legal/PLAY_DATA_SAFETY_MAPPING.md`](../legal/PLAY_DATA_SAFETY_MAPPING.md).

## Lint

UI locales are guarded by two tests, both of which allow negated disclaimers:

- [`noClinicalProductCopy.test.ts`](../../apps/web/src/lib/i18n/noClinicalProductCopy.test.ts)
  — burnout / MBI / CBI as product framing.
- [`noCausalInsightCopy.test.ts`](../../apps/web/src/lib/i18n/noCausalInsightCopy.test.ts)
  — affirmative causal verbs (#928 D4). It reports the offending locale path,
  so a new string that claims a cause names itself in the failure.

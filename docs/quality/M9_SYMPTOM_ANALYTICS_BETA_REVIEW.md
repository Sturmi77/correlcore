# M9 Symptom Analytics — Beta Usability Review

Last updated: 2026-07-11 (M9 Sprint 5)  
Spec: [`features/symptom-analytics.md`](../features/symptom-analytics.md) · ADR: [`adr/0025-symptom-analytics.md`](../adr/0025-symptom-analytics.md)

## Objective

Review symptom analytics surfaces before / during closed beta. Collect usability signal without
new APIs or third-party analytics.

**M9 acceptance (spec §M9):**

- Beta feedback on symptom analytics usability collected and reviewed
- Decision on intensity scope recorded

---

## Surfaces in scope

| Surface | Route / component | Maturity gate | Code anchor |
| ------- | ----------------- | ------------- | ----------- |
| Symptom mood insights | Insights feed tab **Symptoms** | `provisional`+ for associations | `InsightCard`, `insightFeedFilter.ts` |
| Co-occurrence heatmap | Insights → symptom co-occurrence panel | `provisional`+ | `SymptomCooccurrenceHeatmap.svelte` |
| Detail sheet | Tap heatmap cell | `provisional`+ | `SymptomCooccurrenceDetailSheet.svelte` |
| Calendar heatmap | Trends (symptom overlay) | `early_patterns`+ | Trends symptom panels |
| Correlation disclaimer | Insights disclaimer route/modal | all authenticated | M3.1 polish |
| Matrix tab | Insights matrix | `early_patterns`+ and ≥2 matrix insights | `insightAnalyticsGate.ts` |

---

## Internal review (pre-beta) — 2026-07-11

Method: code + UX contract review against [`SYMPTOM_VISUALIZATION.md`](../frontend/SYMPTOM_VISUALIZATION.md)
and Playwright foundation specs. No live tester cohort yet.

| # | Topic | Finding | Severity | Beta action |
| - | ----- | ------- | -------- | ----------- |
| SA-1 | **Discoverability** | Symptom co-occurrence hidden until `provisional` phase — correct per ADR, but testers with <15 entries may never see it | Info | Tell week-2 testers to log ≥15 days first |
| SA-2 | **Disclaimer** | Lift/Phi methodology explained in correlation disclaimer; symptom-specific copy present | OK | Ask testers: "Is the disclaimer understandable?" |
| SA-3 | **Intensity** | `entry_symptoms.intensity` captured but analysis is binary (presence only) | Info | Explicitly **out of scope** for beta — document in feedback template |
| SA-4 | **Custom symptoms** | Custom symptoms treated same as defaults (spec assumption) | Watch | If testers report noisy insights from typo symptoms, log for `min_data_quality` (post-M9) |
| SA-5 | **Mobile heatmap** | Horizontal scroll with compact labels per mobile hardening rules | OK | Test at 375px in week 2 |
| SA-6 | **Empty states** | `hasSymptomCooccurrenceData` gates rendering — empty panel vs error must be distinct | OK | Verify with sparse symptom data |
| SA-7 | **Tab filtering** | `symptoms` tab includes `symptom_mood_association` and co-occurrence types | OK | — |

**Internal review result:** No P0/P1 usability blockers identified. Beta prompts below.

---

## Beta tester prompts (week 2)

Add to onboarding email or checklist optional section:

1. After **≥15 daily entries** with at least one symptom on ≥5 days:
   - Open **Insights → Symptoms** tab. Do any symptom cards feel surprising or wrong?
2. Open **symptom co-occurrence heatmap** (if visible). Can you explain what a highlighted cell means?
3. Read the **correlation disclaimer**. Is the Lift explanation clear (DE/EN)?
4. Would **symptom intensity** (0–3) change how you trust insights? (yes/no + comment)

Record answers in GitHub issues with label `beta` + `symptom-analytics`.

---

## Intensity scope decision (M9)

Per [`symptom-analytics.md`](../features/symptom-analytics.md) §Future Work:

| Option | Decision | Rationale |
| ------ | -------- | --------- |
| Promote intensity to M9 | **Rejected** | No pre-beta evidence; ordinal methods need larger N per level |
| Keep binary for beta | **Accepted** | Matches current engine; avoids misleading sparse intensity splits |
| Revisit post-beta | **Accepted** | If ≥3 testers independently request intensity in feedback round 1 → M10 ADR trigger |

**Recorded:** Intensity remains **Future Work** through M9 beta. Re-evaluation trigger: ≥3 independent
tester requests **or** internal data show intensity variance adds signal beyond presence.

---

## Custom symptom quality (watch item)

If beta feedback reports misleading insights driven by custom symptom names:

- **Short term:** Educate testers on symptom naming (Settings → Symptoms)
- **Medium term (M9+):** Evaluate `min_data_quality` flag in engine — not implemented in M9 (no new API)

---

## Feedback log (operator-maintained)

| Date | Tester | Issue # | Theme | Priority | Resolution |
| ---- | ------ | ------- | ----- | -------- | ---------- |
| _pending_ | — | — | — | — | Awaiting round 1 |

---

## Sign-off

| Review | Date | Result |
| ------ | ---- | ------ |
| Internal pre-beta review | 2026-07-11 | PASS — no blockers |
| External beta round 1 | _pending_ | Operator fills after week 2 |

---

## Related

- [`M9_ANALYTICS_THRESHOLDS_REVIEW.md`](M9_ANALYTICS_THRESHOLDS_REVIEW.md) — engine thresholds
- [`BETA_ONBOARDING.md`](../selfhost/BETA_ONBOARDING.md) — recruitment
- [`PHASE_INSIGHT_MATRIX.md`](../PHASE_INSIGHT_MATRIX.md) — threshold reference table

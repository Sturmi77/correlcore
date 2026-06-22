# CorrelCore Mobile/Web Audit

Run ID: `correlcore-mobile-web-audit-2026-06-22-v1`
Figma file: https://www.figma.com/design/XjijHnzMJubA1iuPQxHOwS

## Concept principles

- Mobile = capture, check-in, fast feedback.
- Web = analysis, comparison, management, review.
- Shared design system = one visual language with different density.
- Current default = no separate native mobile frontend; keep SvelteKit shared until native capabilities require a split.
- Code Connect remains blocked until Figma has a Dev or Full seat on an Organization or Enterprise plan.

## Status legend

- Green: Fits with the current component system on this surface.
- Yellow: Needs layout, variant, state, or density refinement.
- Red: Needs conceptual split, new variants, or missing Figma/code parity work.

## Mobile/Web problem matrix

| Screen | Code routes | Main components | Mobile | Web | Problem type | Recommendation |
| --- | --- | --- | --- | --- | --- | --- |
| Home / Today | \`/\` | \`HomeSummary\`<br>\`HomeDailyBrief\`<br>\`HomeTodayContext\`<br>\`HomeInsight\`<br>\`HomeRecentEntries\`<br>\`WeekdayPatternChart\`<br>\`AppNav\`<br>\`ScreenHeader\` | yellow | green | Partial Figma coverage and density split | Keep mobile as quick daily summary; make web a broader dashboard with recent movement and follow-up panels. |
| Entry | \`/entries/new\`<br>\`/entries/day/[date]\` | \`EntryForm\`<br>\`ScaleSlider\`<br>\`TagPicker\`<br>\`SymptomChecker\`<br>\`SaveStatusBadge\`<br>\`DayDeltaCard\` | yellow | yellow | High-frequency form density and state coverage | Mobile gets a compressed capture flow; web gets a workspace layout with context, notes, and review states. |
| Trends | \`/trends\` | \`TrendsComparePanel\`<br>\`MetricTimeseries\`<br>\`ComparisonHeatmap\`<br>\`UnifiedStripChart\`<br>\`TagHeatmap\`<br>\`HabitsPanel\`<br>\`EntryHistorySheet\` | red | green | Dense chart interactions and comparison surface | Web remains the primary analysis surface; mobile needs summary cards plus drill-down sheets instead of full chart parity. |
| Insights | \`/insights\`<br>\`/insights/disclaimer\` | \`InsightFeed\`<br>\`InsightCard\`<br>\`InsightMatrix\`<br>\`InsightQualityMeter\`<br>\`InsightConfidenceScale\`<br>\`TagGroupsSection\`<br>\`TagCooccurrenceHeatmap\`<br>\`SymptomAnalyticsSection\` | red | yellow | Missing Figma coverage for real insight components | Define insight card, feed, quality, and matrix variants before treating the Figma screen as implementation-ready. |
| Settings | \`/settings\`<br>\`/settings/tags\` | \`ScreenHeader\`<br>\`Panel\`<br>\`Button\`<br>\`InlineAlert\`<br>\`ThemeToggle\` | yellow | green | Missing Figma flow | Add settings and tag-management backlog frames; keep mobile simple and web management-oriented. |
| Onboarding/Auth | \`/onboarding\`<br>\`/onboarding/profile\`<br>\`/onboarding/retro\`<br>\`/auth/login\`<br>\`/auth/register\`<br>\`/auth/check-email\`<br>\`/auth/verify-email\`<br>\`/auth/resend-verification\` | \`Button\`<br>\`Panel\`<br>\`InlineAlert\`<br>\`PasswordStrength\` | yellow | yellow | Missing Figma flow and conversion-state coverage | Add a lightweight onboarding/auth backlog flow with form, verification, error, and success states. |
| Offline/PWA | \`/offline\` | \`Panel\`<br>\`Button\` | yellow | yellow | Missing Figma state | Add offline/install/update states because they matter most in mobile daily-use contexts. |

## Component classification

| Component | Classification | Mobile risk | Web risk | Recommendation |
| --- | --- | --- | --- | --- |
| `AppNav` | Needs split | medium | medium | Keep bottom nav and desktop rail variants as first-class shell decisions. |
| `ScreenHeader` | Shared | low | low | Keep compact and action variants; audit long translated text. |
| `Button` | Shared | low | low | Keep current variants; verify icon-only and loading states in Figma. |
| `Panel` | Shared | medium | low | Use as layout primitive, but avoid nested-card density on mobile. |
| `InlineAlert` | Shared | low | low | Keep action and no-action variants; include error/success states in screen specs. |
| `ScaleSlider` | Mobile-specialized | medium | low | Mobile touch target and thumb/value feedback are critical; web can group sliders horizontally. |
| `TagPicker` | Mobile-specialized | high | medium | Promote TagChip/FormField variants into fuller Figma coverage and limit overflow states. |
| `SymptomChecker` | Mobile-specialized | high | medium | Create Figma coverage; likely needs grouped disclosure on mobile. |
| `EntryForm` | Needs split | high | medium | Split screen composition, not data model: mobile capture flow vs web workspace. |
| `HomeSummary` | Shared | low | low | Use shared summary but vary surrounding context density. |
| `MetricTimeseries` | Web-primary | high | low | Create mobile summary/drill-down treatment instead of squeezing full chart parity. |
| `ComparisonHeatmap` | Web-primary | high | low | Use web as primary; mobile should expose top signals and drill-down. |
| `TrendsComparePanel` | Web-primary | high | low | Needs mobile simplification and Figma representation. |
| `UnifiedStripChart` | Web-primary | high | medium | Audit cursor/timeline interaction on mobile before implementation. |
| `TagHeatmap` | Web-primary | high | medium | Prefer compact ranked signal cards on mobile. |
| `HabitsPanel` | Web-primary | medium | low | Keep full panel web-first; mobile can use an insight teaser. |
| `InsightFeed` | Needs variant | medium | medium | Add Figma variants for feed density and tab behavior. |
| `InsightCard` | Shared | medium | medium | Create Figma coverage; card content hierarchy drives both surfaces. |
| `InsightMatrix` | Web-primary | high | medium | Mobile needs a simplified pattern list; web can keep matrix visualization. |
| `Settings screens` | Web-primary | medium | low | Add Figma backlog screens for settings and tag management. |

## Next implementation path

1. Build missing Figma variants for Entry, Insights, Settings, Auth/Onboarding, and Offline/PWA states.
2. Plan the responsive code shell around `AppNav`, route density, and screen-level composition.
3. Run browser responsive QA against mobile and desktop viewports once code changes begin.

## Acceptance status

- Main flows assigned: yes
- Existing Figma screens rated: yes
- Core components classified: yes
- Primary surface decisions resolved: yes

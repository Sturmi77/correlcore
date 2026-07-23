# [FEATURE] Lag correlation visualization (time-offset insights)

> Ready-to-paste GitHub issue body (feature_request template).
> Labels: `enhancement`
> Milestone: Backlog / Insights-UX

---

## Feature-Beschreibung

Lag-Insights (z. B. „2 Tage nach Radfahren wiederkehrend Müdigkeit“) nicht nur als Text, sondern als erkennbare **Zeitversatz-Darstellung**: Feature bei T0, Outcome bei +N Tagen.

## Problem / Motivation

Die Backend-Analyse existiert bereits: [`run_lag_analysis`](../../backend/app/services/multivariate_analytics.py) (M7) liefert `payload.method=lag`, `lag_days`, Feature/Target. Die UI zeigt in [`InsightCard`](../../apps/web/src/lib/components/insights/InsightCard.svelte) nur den Titel-Suffix `(+N days)`. Das Event-Aligned Sheet aligniert auf Subject/Target und **ignoriert** `lag_days`. ADR-0035 nennt Lag-Korrelations-Heatmaps als Zukunftsthema.

Nutzer können den zeitlichen Versatz nicht visuell nachvollziehen.

## Vorgeschlagene Lösung

1. **Explore Events für Lag:** Onset = `payload.feature` (Tag/Symptom); Fenster so, dass Outcome bei `+lag_days` markiert/hervorgehoben wird (`get_insight_event_windows` + Event-Aligned Sheet anpassen).
2. **InsightCard Level 2:** kleines **Lag-Profil** (Bars Tage 1–7), sofern Engine/API die `r[lag]`-Serie mitliefert — sonst mindestens Annotation der gewählten Lag-Position.
3. **Phase 2 (Follow-up, nicht Blocker):** Lag-Korrelations-Heatmap (Paar × Lag) laut ADR-0035.
4. Gates unverändert: `MIN_ML_ENTRIES=90`, FDR, non-causal Copy.

### Umsetzungsplan

Lag-Payload prüfen/erweitern → Event-Window-API lag-aware → Sheet + Card-Profil → Tests (`test_multivariate_analytics` + Web).

```text
run_lag_analysis → Insight payload (lag)
  → InsightCard title + lag annotation
  → Event windows on feature → Sheet mark at +lag_days
```

## Alternativen

- Neues DualAxisChart (in Docs spezifiziert, im Code nicht vorhanden) — höherer Aufwand; bestehende Strip/Event-Aligned-Primitives reichen für Phase 1.
- Nur Copy verbessern — löst das Darstellungs-Finding nicht.

## Milestone

Backlog / Insights-UX

## Datenschutz-Impact

Nutzt bestehende Insight-Payloads; ggf. erweiterte aggregierte Statistik in der Payload. Keine neuen Roh-Gesundheitsdaten in der UI.

# [FEATURE] Home weekday overview: show most frequent tag/signal per weekday

> Ready-to-paste GitHub issue body (feature_request template).
> Labels: `enhancement`
> Milestone: Backlog / Post-M10.1

---

## Feature-Beschreibung

Pro Wochentag (Mo–So) im Homescreen-Wochentags-Strip genau **ein** dominantes Signal anzeigen: das Tag, Symptom oder der Work-Context, der an diesem Wochentag am häufigsten vorkommt — unabhängig davon, ob es Habit, Symptom, Work Context o. Ä. ist.

## Problem / Motivation

Die Home-Wochentags-Übersicht ([`HomeWeekdayOverview.svelte`](../../apps/web/src/lib/components/home/HomeWeekdayOverview.svelte)) zeigt aktuell Mood-Durchschnitte und gelegentlich Insight-Confounder-Labels ([`homeWeekdayOverview.ts`](../../apps/web/src/lib/utils/homeWeekdayOverview.ts)). Nutzer sehen nicht, _was_ typischerweise an dem Tag passiert (z. B. „Meeting“ freitags, „Kopfschmerz“ montags).

`GET /dashboard/summary` liefert in `weekday_summary` nur `mood_avg` / `entry_count` — keine Frequenz-Mode über Tags, Symptoms oder Work-Context.

## Vorgeschlagene Lösung

1. **Backend:** `weekday_summary` in [`dashboard_service.py`](../../backend/app/services/dashboard_service.py) / [`schemas/dashboard.py`](../../backend/app/schemas/dashboard.py) erweitern um z. B.:
   - `top_signal: { kind: tag|symptom|work_context, id?, label, count, share }`
   - Aggregation über dasselbe Fenster wie bestehendes `weekday_summary`; leer bei zu wenig Daten.
   - Kandidaten: Tags (`entry_tags`), Symptoms (`entry_symptoms`), Work-Context (`entries.work_context`).
   - Pro Wochentag Mode mit höchster Häufigkeit; Tie-Break: Tag > Symptom > Work-Context, dann Label.
2. **Frontend:** Finding-Slot in `HomeWeekdayOverview` mit `top_signal.label` füllen (Mood-Balken behalten). i18n DE/EN.
3. **Tests:** Backend-Aggregation + Web-Unit für Cell-Mapping; Dashboard-Mocks erweitern.

### Umsetzungsplan

`dashboard` Schema+Service → Web-Typen / `homeWeekdayOverview` → UI Finding-Label → Tests.

## Alternativen

- Clientseitig aus Tag-/Symptom-Heatmap aggregieren — mehr Payload, inkonsistent mit Dashboard-API.
- Nur Tags (ohne Symptoms/Work-Context) — zu eng gegenüber dem Finding.

## Milestone

Backlog / Post-M10.1

## Datenschutz-Impact

Aggregierte Häufigkeiten aus bestehenden Entry-Daten; keine neuen PII-Felder.

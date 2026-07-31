# [FEATURE] Konfigurierbarer Home Screen: Sektionen auswählen & Reihenfolge festlegen

> **Status:** Implementiert in PR [#594](https://github.com/Sturmi77/correlcore/pull/594) (2026-07-31)  
> GitHub issue: [#584](https://github.com/Sturmi77/correlcore/issues/584) (closed)  
> ADR: [`0017-frontend-screen-architecture.md`](../adr/0017-frontend-screen-architecture.md) (2026-07-31 amendment)  
> Migration: `034_home_sections`

---

## Feature-Beschreibung

Der Home Screen wird konfigurierbar: Nutzer wählen, **welche** kompakt
darstellbaren Info-Blöcke angezeigt werden und **in welcher Reihenfolge**.

## Konfigurierbare Sektionen

| key                 | Komponente                      | Beschreibung                       |
| ------------------- | ------------------------------- | ---------------------------------- |
| `first_week_banner` | `FirstWeekInsightBanner.svelte` | Früh-Insight-Banner                |
| `daily_brief`       | `HomeDailyBrief.svelte`         | Top-Insight / Phase + Bridge-Links |
| `work_context`      | `HomeWorkContextSummary.svelte` | Arbeitssituationsmuster            |
| `weekday_overview`  | `HomeWeekdayOverview.svelte`    | Wochentags-Strip                   |

**Fix (nicht konfigurierbar):** `HomeTodayContext`, Primary CTA, PWA-Banner,
Onboarding-Redirect.

## Datenmodell

```json
"home_sections": [
  { "key": "first_week_banner", "enabled": true },
  { "key": "daily_brief", "enabled": true },
  { "key": "work_context", "enabled": true },
  { "key": "weekday_overview", "enabled": true }
]
```

- Spalte `user_preferences.home_sections` (JSONB, nullable)
- `NULL`/leer → Server-Default (`first_week_banner`, `daily_brief`, `work_context`, `weekday_overview` — Banner zuerst)
- Merge-Logik: unbekannte Keys verwerfen, fehlende Default-Keys einfügen

## UI

- Route: `/settings/home`
- Checkbox pro Sektion, Hoch/Runter-Buttons (a11y), Reset auf Standard
- Persistenz via `PATCH /user/preferences`

## Datenschutz

Nur UI-Layout-Präferenzen. Keine Gesundheitsdaten oder neuen PII-Felder.

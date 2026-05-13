# M3 Sprint- und Issue-Status

Stand: 2026-05-13

Dieses Dokument beschreibt den Abschlussstand von M3 im Abschluss-Branch
`m3-completion-plan`. Die ersten sechs Sprints lagen bereits auf `main`; die
Sprints 7 bis 12 werden in einem Abschluss-PR zusammengefuehrt und danach ueber
den `release-images.yml`-Workflow als neue GHCR-Images verifiziert.

## Sprint-Uebersicht

| Sprint | Status      | Kurzinhalt                                                                               |
| ------ | ----------- | ---------------------------------------------------------------------------------------- |
| 1      | geschlossen | No-Gamification-Prep: sichtbare Entry-Run-Copy auf Tracking Consistency umgestellt.      |
| 2      | geschlossen | Insight- und Preference-Foundation: Migration, Modelle, Schemas, Analytics-Dependencies. |
| 3      | geschlossen | Analytics Engine v1: tiered Kandidaten, Spearman, Point-biserial, Weekday Pattern.       |
| 4      | geschlossen | Analytics Worker: nightly Insight-Generation fuer aktive/verifizierte User.              |
| 5      | geschlossen | Read-API: `GET /api/v1/insights` und `/insights/latest`.                                 |
| 6      | geschlossen | Web Home Preview: neuester Insight read-only auf der Home-Seite.                         |
| 7      | geschlossen | Statistik-Haertung: FDR-Korrektur, Mindeststichprobe, Wochentags-Bias, entry-date Guard. |
| 8      | geschlossen | Insight Confidence Scale: Dashboard Summary Endpoint und permanente Home-Skala.          |
| 9      | geschlossen | First-Week UX: WeekdayPatternChart, neutraler Banner, Preference-Dismiss-State.          |
| 10     | geschlossen | Insights-Seite und Korrelations-Matrix fuer Tag-Mood-Muster.                             |
| 11     | geschlossen | Cold-start Onboarding: Retro-Batch, Profilfragen, statische Preview-Library.             |
| 12     | geschlossen | Day-over-Day Delta: direkter Vergleich zu gestern nach Entry-Save.                       |

## Implementierungsstand

- **#151 Tiered Confidence System:** `Insight`-Model/API/Worker liefern `tier`, `confidence` und `sample_n`; Home rendert Tier-Badge, erklaerenden Tooltip/ARIA-Text, sichtbaren Medical Disclaimer und neutrale Copy ohne kausale oder diagnostische Aussagen.
- **#152 Retrospective Entry Import:** `EntrySource`, Migration, `POST /api/v1/entries/batch`, `/onboarding/retro` und persistierter `onboarding_retro_completed`-State sind umgesetzt.
- **#153 Insight Confidence Scale:** `GET /api/v1/dashboard/summary`, logarithmischer `confidence_score` und `InsightConfidenceScale` auf Home sind umgesetzt.
- **#154 Day-over-Day Delta:** neuer `GET /api/v1/entries/delta?entry_date=YYYY-MM-DD&slot=day`, metric-only Response, shared Tags und `DayDeltaCard` auf `/entries/new` nach Auto-Save bzw. beim Laden bestehender Eintraege sind umgesetzt.
- **#155 First-Week Tracking Consistency Insight:** Weekday-Payload, 7-Bar-Chart, neutraler Banner und persistenter `dismissed_insight_keys`-State sind umgesetzt.
- **#156 Onboarding Questionnaire:** `user_profiles`, `PUT /api/v1/user/profile`, Export-Erweiterung, `/onboarding/profile` und `insight_previews.json` mit klar gelabelten allgemeinen Forschungshinweisen sind umgesetzt.
- **#157 und #159:** bleiben bewusst ausserhalb von M3 als M5-Folgearbeit offen.
- **#158:** M2-Follow-up ist umgesetzt und in GitHub bereits geschlossen.

## Verifikation

Zuletzt ausgefuehrte Abschluss-Gates:

- `uv run --python 3.12 ruff check .` gruen.
- `uv run --python 3.12 ruff format --check .` gruen.
- `uv run --python 3.12 mypy app` gruen.
- `$env:ENCRYPTION_KEY='AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA='; uv run --python 3.12 pytest --no-cov` mit 372 Tests gruen.
- `NODE_OPTIONS=--max-old-space-size=4096 pnpm --filter @correlcore/web typecheck` gruen.
- `pnpm --filter @correlcore/web lint` gruen.
- `pnpm --filter @correlcore/web test -- --run` mit 195 Tests gruen.
- `pnpm --filter @correlcore/web build` gruen.

Hinweis: Der gueltige Test-Fernet-Key wird nur fuer lokale Tests gesetzt, weil
die lokale `.env` weiterhin den dokumentierten Platzhalter-Key enthaelt.

## Abschlussfolge

1. Abschluss-Commit auf `m3-completion-plan` erstellen und PR gegen `main` oeffnen.
2. GitHub-Checks im PR abwarten.
3. PR nach `main` mergen, wenn die Checks gruen sind.
4. Issues #151, #152, #154 und #156 mit Abschlusskommentar schliessen.
5. `release-images.yml` auf `main` verifizieren: API- und Web-Job muessen gruen sein und `latest`, `main`, `sha-<merge-short-sha>` nach GHCR pushen.

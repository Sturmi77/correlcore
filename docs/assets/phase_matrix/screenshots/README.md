# UI-Screenshots für die Phase- & Insight-Referenz

Frontend-Screenshots, die in [`../../../PHASE_INSIGHT_MATRIX.md`](../../../PHASE_INSIGHT_MATRIX.md)
(§4.4 Backend ↔ Frontend-Landkarte, Abschnitt 4.4.3) eingebettet werden.

## Dateinamens-Konvention

`<Komponente>__<preset>.png` — z.B. `InsightCard__robust.png`, `InsightStageHeader__collecting.png`.
`<preset>` ist eine der Dev-Phasen (`collecting` / `early_patterns` / `provisional` / `robust`).

## Vorhandene Aufnahmen

Phasen-Progression (Route `/insights`):

- `InsightStageHeader__{collecting,early_patterns,provisional,robust}.png`
- `InsightFeed__{collecting,early_patterns,provisional,robust}.png`

Komponenten-Galerie (Preset `robust`):

- `InsightCard__robust.png` — einzelne Insight-Karte
- `InsightMatrix__robust.png` — Correlation-Matrix-Tab (EFFEKT/KONFIDENZ)
- `TagCooccurrenceHeatmap__robust.png` — Tag×Tag-Co-occurrence (`/trends`)
- `MetricTimeseries__robust.png` — Metrik-Zeitreihe (`/trends`)
- `TrendsComparePanel__robust.png`, `TrendsHealthContext__robust.png` — Trends-Kontext
- `HomeInsightZone__robust.png` — Daily-Brief-Insight-Zone (`/`)

> Alle Bilder stammen aus **Dev Mode + `dev_force_viz`** mit den Phase-Presets — die Insight-Daten
> kommen aus `getDevPhaseFixture` (`apps/web/src/lib/dev/phaseFixtures.ts`), **nicht** aus einer echten
> Nutzer-Datenbank. Sie dienen ausschließlich als Debug-/Doku-Referenz.

## Reproduzierbare Aufnahme (Dev Mode, manuell)

1. Web-App lokal starten (`docs/DEVELOPMENT.md`; Dev-Server auf `http://127.0.0.1:4173`).
2. **Settings → Developer** öffnen, **Dev Mode** und **`dev_force_viz`** aktivieren, dann das gewünschte
   **Phase-Preset** wählen (`DEV_PHASE_PRESETS`). Die Routen `/`, `/insights`, `/trends` lesen die Fixture
   über `getDevPhaseFixture`.
   > Wichtig: Das Preset (`devPhase`-Store) wird **nicht** in `localStorage` persistiert. Nach dem Umschalten
   > per **SPA-Navigation** (In-App-Link) zur Zielroute wechseln — ein voller Reload (`page.goto`) würde den
   > Store auf `collecting` zurücksetzen.
3. Zielkomponente per `data-testid` aufnehmen (z.B. `insight-feed`, `insight-card`, `insight-matrix`,
   `insight-stage-header`, `home-zone-insight`, `trends-compare-panel`).
4. Als `<Komponente>__<preset>.png` hier ablegen.

## Automatisierte Aufnahme (Playwright, empfohlen)

Die vorhandenen Bilder wurden mit Playwright headless (Chromium, Viewport 1440×1600, `deviceScaleFactor: 2`,
Dark-Theme) erzeugt. Kernschritte des Skripts:

- `addInitScript`: `localStorage` setzen — `dev_mode_enabled=true`, `dev_force_viz=true`, `correlcore-locale=de`.
- `page.route('**/api/v1/**', …)`: Auth (`/auth/me` → Mock-User) + Basis-Endpunkte mocken. Die Insights selbst
  liefert bei aktivem `dev_force_viz` die Client-Fixture, kein Backend nötig. Vorlage:
  [`apps/web/tests/e2e/helpers/insightsApiMock.ts`](../../../../apps/web/tests/e2e/helpers/insightsApiMock.ts).
- Pro Preset: `/settings` → `selectOption('[data-testid="developer-phase-select"]', <preset>)` → **SPA-Link**
  zur Zielroute → `locator(<testid>).screenshot({ path: … })`.

> Hinweis: `robust` (42 Einträge) deckt **kein** ML/Lag ab (braucht ≥ 90). Für LASSO/Lag-Screenshots ist eine
> erweiterte Fixture oder ein manueller Datensatz nötig (siehe §9-Hinweis in der Referenz). Die ML/Lag-Zeilen in
> §4.4.1 verweisen daher ersatzweise auf `InsightCard__robust.png`.

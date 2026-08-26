# UI-Screenshots für die Phase- & Insight-Referenz

Frontend-Screenshots, die in [`../../../PHASE_INSIGHT_MATRIX.md`](../../../PHASE_INSIGHT_MATRIX.md)
(§4.4 Backend ↔ Frontend-Landkarte, Abschnitt 4.4.3) eingebettet werden.

**Onboarding expectation card (concept mocks + phase thumbs):**
[`onboarding_expectation/`](onboarding_expectation/) — see
[`ONBOARDING_MATURITY_EXPECTATION_CARD.md`](../../../frontend/ONBOARDING_MATURITY_EXPECTATION_CARD.md).

## Dateinamens-Konvention

`<Komponente>__<preset>.png` — z.B. `InsightCard__robust.png`, `InsightStageHeader__collecting.png`.
`<preset>` ist eine der Dev-Phasen (`collecting` / `early_patterns` / `provisional` / `robust`).

**Mobile-Varianten** tragen zusätzlich das Präfix `mobile__` — z.B. `mobile__InsightsPage__robust.png`.
Sie werden aus der `mobile-daily`-Surface (Viewport **390×844**, DPR 3, Route unterhalb
`DESKTOP_SHELL_BREAKPOINT_PX = 768`) aufgenommen und stehen in der Referenz (§4.4.3 A) **vor** den
Desktop-Varianten, weil CorrelCore mobile-first ist.

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

Mobile-Surface (`mobile-daily`, 390×844, Präfix `mobile__`):

- `mobile__InsightsPage__{collecting,early_patterns,provisional,robust}.png` — Phasen-Progression auf `/insights`
- `mobile__MobileInsightLead__robust.png` — `MobileInsightLead` (`mobile-insight-lead`), priorisiertes Signal
- `mobile__TrendsSummary__robust.png` — „Auf einen Blick" (`mobile-trends-summary`, `/trends`)
- `mobile__TrendsDetail__robust.png` — aufgeklappte Detail-Ansicht (`mobile-trends-detail`, `/trends`)
- `mobile__HomePage__robust.png` — Home (`/`) inkl. Bottom-Tab-Navigation

> Alle Bilder stammen aus **Dev Mode + `dev_force_viz`** mit den Phase-Presets — die Insight-Daten
> kommen aus `getDevPhaseFixture` (`apps/web/src/lib/dev/phaseFixtures.ts`), das wiederum die
> Lifestyle-Persona in `personaDataset.ts` nutzt (**nicht** aus einer echten Nutzer-Datenbank).
> Sie dienen ausschließlich als Debug-/Doku-/Marketing-Referenz.

## Reproduzierbare Aufnahme (Dev Mode, manuell)

1. Web-App lokal starten (`docs/DEVELOPMENT.md`; Dev-Server auf `http://127.0.0.1:4173`).
2. **Settings → Developer** öffnen, **Dev Mode** und **`dev_force_viz`** aktivieren, dann das gewünschte
   **Phase-Preset** wählen (`DEV_PHASE_PRESETS`). Die Routen `/`, `/insights`, `/trends` lesen die Fixture
   über `getDevPhaseFixture`.
   > Wichtig: Das Preset (`devPhase`-Store) wird **nicht** in `localStorage` persistiert. Nach dem Umschalten
   > per **SPA-Navigation** (In-App-Link) zur Zielroute wechseln — ein voller Reload (`page.goto`) würde den
   > Store auf `collecting` zurücksetzen.
3. Zielkomponente per `data-testid` aufnehmen (z.B. `insight-feed`, `insight-card`, `insight-matrix`,
   `insight-stage-header`, `home-zone-sections`, `trends-compare-panel`).
4. Als `<Komponente>__<preset>.png` hier ablegen.

## Automatisierte Aufnahme (Playwright)

```bash
cd apps/web
CAPTURE_SCREENSHOTS=1 pnpm exec playwright test tests/e2e/capture-phase-screenshots.spec.ts
```

Das Skript regeneriert die **Mobile-Phasenprogression**, `mobile__MobileInsightLead__robust`, Onboarding-/Landing-Thumbs
(`static/onboarding/maturity/phase*.png`), README-Marketing-Shots (`docs/assets/screenshots/`) und einen
Landing-Journey-Shot (`landing__Journey__maturity.png`). Desktop-Komponenten-Galerie (Matrix, Feed, …)
weiterhin manuell oder per Erweiterung des Skripts. Für saubere 144×144-Thumbs wird optional `sharp`
als Dev-Dependency genutzt (`pnpm --filter @correlcore/web add -D sharp`).

**Noch nicht automatisiert / Orphans:** `TrendsComparePanel__robust.png`, `TrendsHealthContext__robust.png`,
sowie unreferenzierte `mobile__HomeInsightZone__robust.png`, `mobile__InsightFeed__robust.png`,
`mobile__TrendsPage__robust.png` — bei Bedarf manuell regenerieren oder entfernen.

Weitere Kernschritte (manuell/erweitert):

- `addInitScript`: `localStorage` setzen — `dev_mode_enabled=true`, `dev_force_viz=true`, `correlcore-locale=de`.
- `page.route('**/api/v1/**', …)`: Auth (`/auth/me` → Mock-User) + Basis-Endpunkte mocken. Die Insights selbst
  liefert bei aktivem `dev_force_viz` die Client-Fixture, kein Backend nötig. Vorlage:
  [`apps/web/tests/e2e/helpers/insightsApiMock.ts`](../../../../apps/web/tests/e2e/helpers/insightsApiMock.ts).
- Pro Preset: `/dev` → Tab **Dev-Viz** → `selectOption('[data-testid="developer-phase-select"]', <preset>)` → **SPA-Link**
  zur Zielroute → `locator(...).screenshot({ path: … })`.

> Hinweis: `robust` (42 Einträge) deckt **kein** ML/Lag ab (braucht ≥ 90). Für LASSO/Lag-Screenshots ist eine
> erweiterte Fixture oder ein manueller Datensatz nötig (siehe §9-Hinweis in der Referenz). Die ML/Lag-Zeilen in
> §4.4.1 verweisen daher ersatzweise auf `InsightCard__robust.png`. Landing-Marketing-Mocks nutzen weiterhin
> ~92 Einträge in `landingDemoData.ts` für Lag-Previews.

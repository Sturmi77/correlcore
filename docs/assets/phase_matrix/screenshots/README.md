# UI-Screenshots für die Phase- & Insight-Referenz

Ablage für Frontend-Screenshots, die in [`../../../PHASE_INSIGHT_MATRIX.md`](../../../PHASE_INSIGHT_MATRIX.md)
(§4.4 Backend ↔ Frontend-Landkarte) eingebettet werden.

## Dateinamens-Konvention

`<komponente>__<preset>.png` — z.B. `InsightCard__provisional.png`, `InsightMatrix__provisional.png`.
`<preset>` ist eine der Dev-Phasen (`collecting` / `early_patterns` / `provisional` / `robust`).

## Reproduzierbare Aufnahme (Dev Mode)

1. Web-App lokal starten (`docs/DEVELOPMENT.md`).
2. **Settings → Developer** öffnen, Dev Mode aktivieren und das gewünschte **Phase-Preset**
   wählen (`DEV_PHASE_PRESETS` in `apps/web/src/lib/dev/phaseFixtures.ts`).
   Die Routen `/`, `/insights` und `/trends` lesen die Fixture über `getDevPhaseFixture`.
3. Zielansicht öffnen und Screenshot der jeweiligen Komponente aufnehmen
   (Viewport-Empfehlung: Desktop 1280×800 und Mobile 390×844, wenn eine mobile Variante existiert).
4. Als `<komponente>__<preset>.png` hier ablegen; die Einbettung in §4.4 zeigt das Bild dann automatisch.

> Hinweis: `robust` (42) deckt **kein** ML/Lag ab (braucht ≥ 90). Für LASSO/Lag-Screenshots
> ist ein manueller Datensatz oder eine erweiterte Fixture nötig (siehe §9-Hinweis in der Referenz).

## Status (Platzhalter)

Solange eine Datei fehlt, verweist §4.4 auf diesen Ordner; bitte Screenshots nachreichen.

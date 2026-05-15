# M3.5 Sprint Plan - Frontend Web and Mobile Optimisation

Stand: 2026-05-15

Dieses Dokument definiert den vollstaendigen Umsetzungsplan fuer M3.5. M3.5 ist
kein neuer Daten-Meilenstein, sondern ein Frontend-Polish- und
Mobile-Architecture-Meilenstein auf Basis von M3 und M3.1.

## Zielbild

M3.5 ist abgeschlossen, wenn CorrelCore auf Web und Mobile entlang der
kanonischen Screen-Architektur aus `docs/FRONTEND.md` und ADR-0017 nutzbar,
konsistent, barrierearm und visuell belastbar ist.

Das Ergebnis soll:

- die 5 Primary Screens aus ADR-0017 respektieren,
- den Daily Entry Flow auf Mobile in maximal 60 Sekunden unterstuetzen,
- Insights mit klarer progressiver Offenlegung erklaeren,
- Trends als mobile-tauglichen Analyse-Screen mit Tabs fuehren,
- Settings als strukturierte Verwaltungs- und Datenschutz-Zentrale ausbauen,
- keine Gamification-Muster einfuehren,
- die offenen M3.5-GUI-Findings aus GitHub adressieren.

## Quellen

- `docs/DESIGN_DOCUMENT.md`
- `docs/FRONTEND.md`
- `docs/adr/0017-frontend-screen-architecture.md`
- `docs/adr/0018-insight-confidence-visualisation.md`
- `docs/adr/0019-dev-mode-settings-toggle.md`
- GitHub Issues:
  - `#170` Screen-Bereiche visuell klar trennen
  - `#171` Work-Context Pflichtfeld-Hinweis und Wochenend-Auto-Fill
  - `#172` Sleep Quality Slider
  - `#173` Tags deaktivieren und Umgang mit Korrelationen
  - `#182` Stressskala invertieren
  - `#183` Dev Mode Force Visualizations
  - `#184` Insight Quality Fortschrittsschaetzung
  - `#185` Language Toggle DE/EN
  - `#186` Screen-Definitionen aus FRONTEND.md

## Grundsaetze fuer M3.5

### 1. FRONTEND.md ist fuehrend

`docs/FRONTEND.md` definiert die Screen-Architektur und die UX-Regeln. Wenn die
Implementierung davon abweicht, muss im PR eine bewusste Entscheidung
dokumentiert werden. Groessere Abweichungen brauchen einen ADR.

### 2. Genau 5 Primary Screens

Gemaess ADR-0017 gibt es genau:

| Screen | Route / Trigger       | Rolle                                                                    |
| ------ | --------------------- | ------------------------------------------------------------------------ |
| 1      | `/`                   | Home: taeglicher Einstieg, aktueller Kontext, Insight Preview, Entry CTA |
| 2      | Bottom Sheet von Home | Entry: taeglicher Eintrag in <= 60 Sekunden                              |
| 3      | `/insights`           | Insights Feed mit progressiver Offenlegung                               |
| 4      | `/trends`             | Trends: Mood, Activities, Health, Entry History als Sheet                |
| 5      | `/settings`           | Settings: Tracking, Analyse, Datenschutz, Appearance, Developer          |

`/dev`, Onboarding, Disclaimer und Entry History sind Hilfsrouten oder
Secondary Sheets, keine Primary Screens.

### 3. Mobile first, Web parity

Jeder Sprint wird auf 375 px Mobile, 768 px Tablet und 1280 px Desktop
abgenommen. Mobile ist nicht nur "responsive", sondern der fuehrende
Interaktionsmodus.

### 4. No gamification

Verboten sind Streak-Zaehler, Badges, Punkte, Reward-Animationen,
Fire-Emojis, Dringlichkeits-Copy und "falling behind"-Framing. Tracking wird
als Datenqualitaet erklaert, nicht als Verhaltensdruck.

### 5. Vier Zustandsarten pro datenladender Komponente

Jede datenladende Komponente definiert:

- Loading: Skeleton oder stabiler Platzhalter
- Error: Inline-Fehler mit Retry
- Empty: kontextueller Leerzustand
- Offline: cached data oder graceful hide

Offline-First wird in M4 voll umgesetzt, aber M3.5 darf keine Komponenten
bauen, die spaeter nur schwer offline-faehig werden.

## Bekannte Ausgangslage auf `main`

Stand der Analyse: `main` bei Commit `1bfb231`.

Bereits vorhanden:

- M3 ist abgeschlossen und gemerged.
- M3.1 hat `InsightCard`, `InsightFeed`, `CorrelationDisclaimer`,
  `InsightStore` und ADR-0017 bis ADR-0019 eingefuehrt.
- Tag-Management kann Hidden Tags technisch bereits laden und toggeln.
- `GET /tags?include_hidden=true` existiert.
- Trends hat `MetricTimeseries` und `TagHeatmap`.
- Settings hat 7x Tap Developer Mode.

Offene Abweichungen:

- Root Layout hat noch keine Bottom Navigation.
- Entry ist noch eine Full Page unter `/entries/new`, nicht das definierte
  Bottom Sheet.
- `app.css` nutzt noch ein teal Primary-System, waehrend `FRONTEND.md`
  violette Primary-Tokens definiert.
- `src/lib/config/metrics.ts` existiert noch nicht.
- Stress-Inversion ist noch nicht zentral zwischen Charts, Insights und
  Analytics abgestimmt.
- `sleep_quality` ist im aktuellen `Entry`-Model nicht vorhanden, obwohl
  `#172` von einem vorhandenen Feld ausgeht.
- `FRONTEND.md` nennt `paraglide-js` als kanonisch, die App nutzt aktuell
  `svelte-i18n`.
- Einige Synology-Metadaten (`@eaDir/SYNOINDEX_MEDIA_INFO`) liegen im
  Frontend-Baum und muessen entfernt werden.
- Trends benutzt weiterhin Streak-benannte API- und UI-Konzepte.
- Settings ist noch nicht vollstaendig nach TRACKING / ANALYSIS /
  PRIVACY & DATA / APPEARANCE / DEVELOPER gegliedert.

## Sprint-Uebersicht

| Sprint | Titel                                         | Primaere Issues            | Ziel                                                       |
| ------ | --------------------------------------------- | -------------------------- | ---------------------------------------------------------- |
| 0      | Repo Hygiene und Design-System Alignment      | `#186`                     | saubere Grundlage, Token- und Doc-Konflikte klaeren        |
| 1      | App Shell und Mobile Navigation               | `#186`                     | Bottom Navigation, App Shell, 5-Screen-Kontrakt            |
| 2      | Entry Flow Foundation                         | `#170`, `#171`, `#182`     | klare Entry-Sektionen, Work Context, Stress-Semantik       |
| 3      | Entry Bottom Sheet und Sleep Quality Decision | `#172`, `#186`             | mobiler Entry Flow, Sleep Quality fachlich korrekt klaeren |
| 4      | Home Screen Recomposition                     | `#186`, M3.1 Folgearbeiten | Home auf max. 3 Info-Zonen reduzieren                      |
| 5      | Insights Quality und Progressive Disclosure   | `#184`, `#186`             | InsightQualityMeter, Feed, Disclaimer QA                   |
| 6      | Trends Screen als Tabbed Analysis Surface     | `#182`, `#186`             | Mood/Activities/Health Tabs, Entry History Sheet           |
| 7      | Settings, Language und Developer UX           | `#183`, `#185`, `#186`     | Settings-Struktur, Language Toggle, Force Visualizations   |
| 8      | Tag Lifecycle und Inactive Correlations       | `#173`                     | Hidden Tags, reaktivieren, Insight-Hinweise                |
| 9      | Visual QA, Docs und GitHub Closure            | alle                       | Abschluss, Issues, Doku, PR/Merge                          |

## Sprint 0 - Repo Hygiene und Design-System Alignment

### Ziel

Vor funktionalen UI-Aenderungen wird die technische Grundlage stabilisiert.
Der Sprint verhindert, dass M3.5 auf widerspruechlichen Tokens, falschen
Dokumentannahmen oder versehentlichen Metadateien aufbaut.

### Aufgaben

- Synology-Metadaten aus dem Repo entfernen:
  - `apps/web/src/lib/components/insights/@eaDir/**`
  - `apps/web/src/lib/stores/@eaDir/**`
- `.gitignore` um `@eaDir/` und `SYNOINDEX_MEDIA_INFO` ergaenzen.
- `app.css` mit `FRONTEND.md` abgleichen:
  - `--color-primary` dark: `#7c6af5`
  - `--color-primary` light: `#6356d9`
  - passende `hover`, `active`, `highlight` Tokens definieren
  - `--color-error-highlight` ergaenzen
  - Heatmap-Tokens neutral/blau ausrichten
- ADR fuer Primary-Farbwechsel erstellen oder `FRONTEND.md` an den
  vorhandenen teal Stand zurueckfuehren. Empfehlung: ADR erstellen und
  violett umsetzen, weil `FRONTEND.md` dies bereits als technische
  Brand-Richtung festlegt.
- I18n-Konflikt klaeren:
  - kurzfristig: `svelte-i18n` bleibt technischer Ist-Stand fuer M3.5
  - `FRONTEND.md` wird ergaenzt: Migration zu `paraglide-js` ist separater
    Refactor, wenn nicht in M3.5 enthalten
  - keine parallele Custom-Locale-Store-Struktur einfuehren
- `docs/FRONTEND.md` und `docs/M3.1_SPRINT_STATUS.md` aktualisieren, falls
  der reale Stand bereits von den dortigen TODOs abweicht.

### Dateien

- `.gitignore`
- `apps/web/src/app.css`
- `docs/FRONTEND.md`
- `docs/adr/0020-primary-color-system.md` oder gleichwertiger ADR
- `docs/M3.1_SPRINT_STATUS.md`

### Akzeptanzkriterien

- Keine `@eaDir` oder `SYNOINDEX_MEDIA_INFO` Dateien mehr im Repo.
- Theme-Tokens stimmen mit `FRONTEND.md` oder dem neuen ADR ueberein.
- Dark und Light Mode verwenden dieselben semantischen Token-Namen.
- Kein neuer UI-Code nutzt alte `rgb(var(--color-primary-500...))` Fallbacks.
- Der i18n-Plan ist eindeutig dokumentiert.

### Tests

- `pnpm --filter @correlcore/web typecheck`
- `pnpm --filter @correlcore/web lint`
- `pnpm --filter @correlcore/web test -- --run`
- `pnpm --filter @correlcore/web build`

## Sprint 1 - App Shell und Mobile Navigation

### Ziel

Die App bekommt eine echte Shell gemaess ADR-0017. Authenticated Screens werden
ueber eine mobile Bottom Navigation erreichbar. Damit wird Web und Mobile
erstmals gleichmaessig gefuehrt.

### Aufgaben

- Root `+layout.svelte` erweitern:
  - Skip-Link als erstes fokussierbares Element
  - `id="main-content"` auf dem Main-Container
  - Bottom Navigation fuer authentifizierte, nicht-public Routes
  - Safe-Area Padding fuer Bottom Navigation
  - public/auth/status routes ohne Bottom Nav
- Navigationselemente:
  - Home `/`
  - Insights `/insights`
  - Trends `/trends`
  - Settings `/settings`
- Entry wird nicht als permanenter Tab eingefuehrt, weil Screen 2 ein
  Bottom Sheet Trigger von Home ist.
- Desktop:
  - Bottom Nav optional als kompakte Seitennavigation oder Top-Nav
  - kein `/dev` in Hauptnavigation
- Active-State anhand `$page.url.pathname`.
- Alle Icon-only Buttons mit `aria-label`.
- Locale Keys fuer Nav-Labels DE/EN vervollstaendigen.

### Dateien

- `apps/web/src/routes/+layout.svelte`
- `apps/web/src/app.css`
- `apps/web/src/lib/i18n/locales/de.json`
- `apps/web/src/lib/i18n/locales/en.json`
- optional: `apps/web/src/lib/components/common/AppNav.svelte`
- optional: `apps/web/src/lib/components/common/AppShell.svelte`

### Akzeptanzkriterien

- Bottom Navigation ist auf 375 px sichtbar und bedienbar.
- Jedes Nav-Ziel hat mindestens 44 x 44 px Touch Target.
- Kein horizontaler Scroll bei 375 px.
- `/dev` wird nicht in der Hauptnavigation angezeigt.
- Auth-Seiten und Status-Seite bleiben ohne App-Chrome.
- Keyboard-Fokus ist sichtbar und logisch.

### Tests

- Component-Test fuer `AppNav` Active-State.
- Layout-Test fuer public vs authenticated route rendering, soweit mit
  bestehender Teststruktur sinnvoll.
- Browser QA:
  - 375 x 812
  - 768 x 1024
  - 1280 x 800

## Sprint 2 - Entry Flow Foundation

### Ziel

Der Entry Flow wird semantisch korrekt, schneller scannbar und
mobile-tauglicher. Dieser Sprint bearbeitet die kritischen Datenqualitaets-
Findings vor dem Bottom-Sheet-Umbau.

### Issues

- `#170`
- `#171`
- `#182`

### Aufgaben

#### Sectioning

- Entry-Form in klar abgegrenzte Bereiche aufteilen:
  - Datum
  - Mood
  - Energy
  - Stress
  - Work Context
  - Tags
  - Symptoms
  - Note
  - Day-over-Day Delta
- Visuelle Trennung ueber dezente Surfaces, Dividers oder Panels.
- Keine farbigen Seitenrahmen.
- Keine verschachtelten Cards.

#### Work Context

- Work Context als Pflichtfeld-Hinweis darstellen, aber Auto-Save nicht
  blockieren.
- Hinweis ist informativ:
  - kein aggressiver Error
  - nicht nur Farbe als Signal
  - Kontrast >= 4.5:1
- Wochenende automatisch mit `weekend` vorbelegen.
- Auto-Fill bleibt ueberschreibbar.
- Utility fuer Wochentagsberechnung extrahieren.

#### Stress Inversion

- `apps/web/src/lib/config/metrics.ts` erstellen.
- Zentrale Metric Definition:
  - `mood_score`, `invert=false`
  - `energy`, `invert=false`
  - `stress`, `invert=true`
  - `sleep_quality`, `invert=false`, sobald Feld verfuegbar ist
- `ScaleSlider` fuer Stress so beschriften, dass die Semantik klar ist:
  - links / niedriger Wert: entspannter
  - rechts / hoeherer Rohwert: sehr gestresst
- Fuer Visualisierungen gilt:
  - raw DB bleibt unveraendert
  - display value fuer Stress = `6 - raw`
- Analytics muss dieselbe Semantik verwenden, damit Korrelationen korrekt
  interpretiert werden.

### Dateien

- `apps/web/src/routes/entries/new/+page.svelte`
- `apps/web/src/lib/components/entries/ScaleSlider.svelte`
- `apps/web/src/lib/config/metrics.ts`
- `apps/web/src/lib/utils/workContext.ts`
- `apps/web/src/lib/utils/metrics.ts`
- `apps/web/src/lib/i18n/locales/de.json`
- `apps/web/src/lib/i18n/locales/en.json`
- `backend/app/services/insight_engine.py`
- `backend/app/services/stats_service.py`
- relevante Tests

### Akzeptanzkriterien

- Jede Entry-Sektion ist auf Mobile klar erkennbar.
- Work Context Hinweis erscheint, wenn kein Wert gesetzt ist.
- Wochenende wird automatisch als `weekend` vorbelegt.
- Auto-Save bleibt nicht-blockierend.
- Stress wird in Charts und Insight-Richtung semantisch korrekt behandelt.
- Rohwerte in API, DB und Export bleiben unveraendert.

### Tests

- Unit-Test fuer `defaultWorkContextForDate`.
- Unit-Test fuer `displayMetricValue` bzw. Stress-Inversion.
- Component-Test fuer `ScaleSlider` Stress-Legende.
- Backend-Test fuer Stress-Semantik in Insight Engine, sofern Worker-Logik
  angepasst wird.

## Sprint 3 - Entry Bottom Sheet und Sleep Quality Decision

### Ziel

Screen 2 aus ADR-0017 wird als mobiler Bottom Sheet Flow umgesetzt. Gleichzeitig
wird `#172` fachlich geklaert, weil der aktuelle Backend-Stand kein
`entries.sleep_quality` Feld enthaelt.

### Issues

- `#172`
- `#186`

### Entscheidungspunkt Sleep Quality

Vor Implementation muss eine der beiden Varianten gewaehlt werden:

#### Variante A - M3.5 fuehrt `sleep_quality` ein

- Alembic Migration fuer nullable `entries.sleep_quality`.
- Schema/API `EntryCreate`, `EntryUpdate`, `EntryResponse` ergaenzen.
- Export JSON/CSV um Sleep Quality erweitern.
- Entry UI bekommt optionalen 1-5 Slider.

#### Variante B - `#172` wird korrigiert und auf M7 verschoben

- `#172` wird kommentiert: Annahme "DB-Feld existiert" ist falsch.
- M3.5 baut nur die UI-Erweiterbarkeit in `ScaleSlider`/Metric Config.
- Sleep Quality wird in M7 mit Health Connect Datenmodell eingefuehrt.

Empfehlung: Variante A nur umsetzen, wenn Sleep Quality vor M7 wirklich fuer
M3.5 notwendig ist. Sonst Variante B, um Scope und Datenmodell klein zu halten.

### Bottom Sheet Aufgaben

- `EntrySheet.svelte` erstellen.
- Home CTA oeffnet Entry Sheet auf Mobile.
- Desktop kann Sheet als centered modal oder breite Side Sheet rendern.
- `/entries/new` bleibt als Deep-Link/Fallback erhalten und nutzt dieselbe
  Form-Komponente.
- Form-Logik aus Route in wiederverwendbare EntryForm-Komponente extrahieren.
- Optionalbereiche hinter "+ More":
  - Tags vollstaendig
  - Symptoms
  - Note
  - Sleep Quality, falls Variante A
- Day-over-Day Delta nach Auto-Save weiter anzeigen.
- Escape / Backdrop / Close Button schliessen Sheet.
- Dirty/Saving Zustand darf nicht still verloren gehen.

### Dateien

- `apps/web/src/lib/components/entries/EntryForm.svelte`
- `apps/web/src/lib/components/entries/EntrySheet.svelte`
- `apps/web/src/routes/+page.svelte`
- `apps/web/src/routes/entries/new/+page.svelte`
- optional Backend-Migration und Schemas fuer Sleep Quality

### Akzeptanzkriterien

- Auf 375 px oeffnet Entry als Bottom Sheet.
- Primary CTA auf Home bleibt immer sichtbar.
- Entry ist per Keyboard bedienbar.
- Fokus wird beim Oeffnen ins Sheet gesetzt und beim Schliessen zurueckgegeben.
- Existing Entry fuer heute wird im Sheet geladen.
- Deep Link `/entries/new` funktioniert weiterhin.
- Sleep Quality Entscheidung ist dokumentiert und umgesetzt.

### Tests

- Component-Test fuer Entry Sheet Open/Close.
- Auto-Save Smoke-Test bleibt gruen.
- Falls Variante A:
  - Backend Migration-Test
  - Entry API Tests
  - Export Tests
  - Web API Tests

## Sprint 4 - Home Screen Recomposition

### Ziel

Home wird auf die Rolle "daily touch point" zurueckgefuehrt. Keine Dashboard-
Ueberladung, maximal drei Informationsbereiche.

### Aufgaben

- Home Layout gemaess `FRONTEND.md` neu ordnen:
  1. Datum + heutiger Work Context / Entry Status
  2. Latest Insight oder FirstWeekInsightBanner
  3. Last 7 days Sparkline + Log Today CTA
- CTA prominent und jederzeit sichtbar.
- Insight-Load bleibt best-effort und blockiert nichts.
- `InsightMatrix` von Home entfernen oder nur hinter "Explore insights" in
  `/insights`/`/trends` anbieten. Empfehlung: nicht dauerhaft auf Home
  anzeigen, weil es der 3-Zonen-Regel widerspricht.
- `HomeRecentEntries` pruefen:
  - wenn beibehalten, als kompakter Verlauf oder Trends-Einstieg
  - nicht den First Viewport dominieren lassen
- Tracking Consistency nur neutral und nur bei echter Relevanz anzeigen.
- Keine `streak` Copy im sichtbaren Home UI.

### Dateien

- `apps/web/src/routes/+page.svelte`
- `apps/web/src/lib/components/home/HomeSummary.svelte`
- `apps/web/src/lib/components/home/HomeSparkline.svelte`
- `apps/web/src/lib/components/home/HomeRecentEntries.svelte`
- `apps/web/src/lib/components/insights/InsightCard.svelte`

### Akzeptanzkriterien

- First viewport auf 375 px zeigt CTA ohne langes Scrollen.
- Home enthaelt maximal 3 Informationsbereiche.
- Keine Matrix auf Home, ausser per dokumentierter Abweichung.
- Insight-Fehler erzeugt keinen Home-Fehlerzustand.
- CTA funktioniert auch bei leerem InsightStore.

### Tests

- Home Component/Route Tests fuer:
  - kein Insight
  - loading Insight
  - Insight Fehler
  - heutiger Entry vorhanden/nicht vorhanden
- Browser Screenshot QA Mobile/Desktop.

## Sprint 5 - Insights Quality und Progressive Disclosure

### Ziel

Insights werden als vertrauensbildender, erklaerbarer Feed finalisiert.
`#184` wird umgesetzt, ohne Gamification oder Pseudo-Praezision.

### Issues

- `#184`
- relevante Teile aus `#186`

### Aufgaben

- `InsightQualityMeter` in `components/insights` finalisieren.
- Fortschrittsschaetzung fuer < 30 Eintraege:
  - 0-3: neutraler Einstiegstext ohne Schaetzung
  - 4-29: `X/30` plus Schaetzung anhand der letzten 14 Tage
  - keine aktuellen Eintraege: keine Schaetzung
- Copy nach `FRONTEND.md`:
  - beschreibend
  - keine Imperative
  - keine Emojis
  - keine Dringlichkeit
- Feed bleibt sortiert nach `confidence * abs(effect_size)`.
- Filtertabs pruefen:
  - All
  - Mood
  - Symptoms
  - Sleep
- Disclaimer Button in Header und Cards pruefen.
- Expanded Insight View vorbereiten:
  - falls DualAxisChart noch nicht vorhanden, als eigenes Folge-Issue
    ausgliedern oder Minimal-Stub vermeiden
  - keine unfertige Placeholder-UI ausliefern

### Dateien

- `apps/web/src/lib/components/insights/InsightConfidenceScale.svelte`
- `apps/web/src/lib/components/insights/InsightFeed.svelte`
- `apps/web/src/lib/components/insights/InsightCard.svelte`
- `apps/web/src/lib/utils/insightQuality.ts`
- i18n Dateien

### Akzeptanzkriterien

- `#184` komplett abgehakt.
- Zeitschaetzung basiert auf realer Tracking-Frequenz der letzten 14 Tage.
- Kein zusaetzlicher API-Call nur fuer die Schaetzung.
- Empty State ist neutral und hilfreich.
- Disclaimer ist per Maus, Touch und Keyboard erreichbar.

### Tests

- Unit-Test `estimateInsightReadiness`.
- Component-Test fuer `InsightQualityMeter`:
  - 0-3
  - 4-29 mit Pace
  - 4-29 ohne recent data
  - > = 30
- Existing InsightFeed Tests erweitern.

## Sprint 6 - Trends Screen als Tabbed Analysis Surface

### Ziel

`/trends` wird zum kanonischen Screen 4. History, Calendar und Entry Detail
werden nicht als neue Screens gebaut, sondern als Tabs und Secondary Sheet.

### Issues

- `#186`
- `#182`
- Referenz: `#166`

### Aufgaben

- Tabs einfuehren:
  - Mood
  - Activities
  - Health
- Time Range Controls vereinheitlichen:
  - 7D
  - 30D
  - 90D
  - 1Y
- Mood Tab:
  - `MetricTimeseries`
  - zentrale Metric Config inklusive Stress-Inversion
  - Tap auf Datenpunkt -> Entry History Sheet
- Activities Tab:
  - `TagHeatmap`
  - Kategorie-/Tagfilter
  - neutrale blaue Heatmap
  - Tap auf Zelle -> Entry History Sheet
- Health Tab:
  - aktuell Symptoms/Sleep readiness
  - keine leeren, unfertigen Charts zeigen
  - falls Daten fehlen: Empty State
- Entry History Sheet:
  - read-only
  - zeigt Datum, Mood/Energy/Stress, Work Context, Tags, Symptome, Note
  - keine neue Primary Route
- Streak-Anzeigen entfernen oder neutral in Tracking Consistency umbenennen.
- API-Typen koennen intern noch `fetchEntryStreak` heissen, sichtbare UI aber
  nicht.

### Dateien

- `apps/web/src/routes/trends/+page.svelte`
- `apps/web/src/lib/components/trends/MetricTimeseries.svelte`
- `apps/web/src/lib/components/trends/TagHeatmap.svelte`
- `apps/web/src/lib/components/trends/EntryHistorySheet.svelte`
- `apps/web/src/lib/config/metrics.ts`
- `apps/web/src/lib/utils/charts.ts`

### Akzeptanzkriterien

- `/trends` hat Tabs, kein eigener History Screen.
- Entry Detail ist ein Sheet/Overlay.
- Kein horizontaler Scroll bei 375 px ausser bewusstem Chart-Innenbereich mit
  klarer Bedienung.
- Stress ist korrekt invertiert.
- Heatmap bleibt neutral und nicht wertend.
- Keine sichtbare Streak-Copy.

### Tests

- Component-Tests fuer Tabs und EntryHistorySheet.
- Chart-Tests fuer Stress-Inversion.
- Browser QA fuer 375/768/1280 px.

## Sprint 7 - Settings, Language und Developer UX

### Ziel

Settings wird zur vollstaendigen Verwaltungszentrale gemaess Screen 5.
Language Toggle und Force Visualizations werden sauber eingebaut.

### Issues

- `#183`
- `#185`
- Settings-Teile aus `#186`

### Aufgaben

#### Settings Struktur

Abschnitte:

- TRACKING
  - Manage tags
  - Manage symptoms
  - Reminders placeholder, falls noch nicht implementiert
- ANALYSIS
  - Analytics enabled Toggle
  - Explore insights Link
- PRIVACY & DATA
  - Export all data
  - Delete account placeholder oder verlinktes M9-Issue, solange nicht gebaut
- APPEARANCE
  - Theme Toggle
  - Language DE/EN
- DEVELOPER
  - nur nach Unlock sichtbar
  - Developer View Link
  - Force Visualizations Toggle

#### Language Toggle

- Kurzfristig mit aktuellem `svelte-i18n` integrieren oder zuerst i18n-ADR
  klaeren.
- Header Toggle kompakt: `DE | EN`.
- Settings Toggle als Segmented Control.
- Persistenz:
  - LocalStorage als Fallback
  - Server-Persistenz nur wenn Backend Preferences ein `locale` Feld bietet
  - falls Backend fehlt: eigenes Folge-Issue/Migration anlegen

#### Dev Mode / Force Visualizations

- `devMode` Store erweitern:
  - `devModeEnabled`
  - `devForceVisualizations`
  - localStorage keys `dev_mode_enabled`, `dev_force_viz`
  - Deaktivieren von Dev Mode setzt Force Viz false
- Force Visualizations nicht an `import.meta.env.DEV` koppeln, weil
  selfhosted Produktion laut `FRONTEND.md` davon profitieren soll.
- Mock-Daten zentralisieren:
  - `apps/web/src/lib/dev/mockInsights.ts`
  - `apps/web/src/lib/dev/mockEntries.ts`
  - `apps/web/src/lib/dev/mockTrends.ts`
- Keine echten API-Writes oder Auto-Save Nebenwirkungen.

### Dateien

- `apps/web/src/routes/settings/+page.svelte`
- `apps/web/src/lib/stores/devMode.ts`
- `apps/web/src/lib/dev/mockInsights.ts`
- `apps/web/src/lib/dev/mockEntries.ts`
- `apps/web/src/lib/dev/mockTrends.ts`
- `apps/web/src/lib/i18n/locales/de.json`
- `apps/web/src/lib/i18n/locales/en.json`
- optional Backend Preferences fuer `locale`

### Akzeptanzkriterien

- `#185` ist erfuellt oder Backend-Abhaengigkeit ist als eigenes Issue
  dokumentiert.
- Language Toggle wirkt ohne Reload.
- Settings enthaelt alle definierten Bereiche.
- Dev Mode wird per 7x Tap aktiviert.
- Force Visualizations ist nur bei aktivem Dev Mode sichtbar.
- Force Visualizations befuellt Insights, Trends und Home mit Mock-Daten,
  ohne echte Daten zu schreiben.

### Tests

- Store-Tests fuer Dev Mode und Force Viz.
- Settings Component-Test:
  - Developer versteckt
  - 7x Tap zeigt Developer
  - Force Viz Toggle sichtbar
- i18n Tests fuer DE/EN Vollstaendigkeit.

## Sprint 8 - Tag Lifecycle und Inactive Correlations

### Ziel

`#173` wird vollstaendig abgeschlossen: Tags koennen deaktiviert und
reaktiviert werden, ohne historische Daten zu verlieren. Insights auf
inaktive Tags bleiben transparent.

### Issues

- `#173`

### Aufgaben

- Tag Settings UI ueberarbeiten:
  - aktive Tags
  - inaktive Tags
  - Reaktivieren
  - Deaktivieren mit neutraler Copy
- Entry Tag Picker zeigt keine hidden Tags.
- Default Tags: Copy-on-Write Verhalten pruefen.
- Analytics:
  - `is_hidden=true` Tags bei neuen Berechnungen ueberspringen
  - bestehende Insights nicht loeschen
- Insights:
  - inaktive Tags mit Hinweis markieren
  - `"(Tag inactive)"` bzw. lokalisierte Copy
- M5 Anschluss:
  - Habit Detail spaeter zeigt Correlation Contribution Score als inactive,
    wenn Tag hidden ist

### Dateien

- `apps/web/src/routes/settings/tags/+page.svelte`
- `apps/web/src/lib/components/entries/TagPicker.svelte`
- `apps/web/src/lib/api/tags.ts`
- `apps/web/src/lib/stores/tags.ts`
- `apps/web/src/lib/components/insights/InsightCard.svelte`
- `backend/app/services/tag_service.py`
- `backend/app/services/insight_engine.py`
- `docs/API.md`

### Akzeptanzkriterien

- Hidden Tags erscheinen nicht im Entry Picker.
- Hidden Tags sind in Settings reaktivierbar.
- Historische Entries behalten ihre Tag-Beziehungen.
- Analytics erzeugt keine neuen Insights fuer hidden Tags.
- Bestehende Insights werden nicht geloescht.
- Insight UI kennzeichnet inaktive Tags klar, aber nicht alarmistisch.
- API-Dokumentation beschreibt `include_hidden`.

### Tests

- Backend Tests fuer `include_hidden`.
- Backend Tests fuer Analytics Skip hidden Tags.
- Web Tests fuer Tag Settings aktive/inaktive Gruppen.
- Web Tests fuer Tag Picker ohne hidden Tags.

## Sprint 9 - Visual QA, Docs und GitHub Closure

### Ziel

M3.5 wird nicht abgeschlossen, bevor Desktop, Mobile, Light/Dark, Accessibility
und Docs geprueft sind.

### Aufgaben

- Vollstaendige visuelle QA:
  - Home
  - Entry Sheet
  - Insights
  - Trends
  - Settings
- Viewports:
  - 375 x 812
  - 768 x 1024
  - 1280 x 800
- Themes:
  - light
  - dark
- States:
  - loading
  - error
  - empty
  - populated
  - forced visualizations
- Accessibility:
  - Keyboard navigation
  - Focus visible
  - Dialog focus restore
  - `aria-label` fuer icon-only buttons
  - contrast spot checks
- Doku aktualisieren:
  - `docs/FRONTEND.md`
  - `docs/M3_5_SPRINT_STATUS.md`
  - `CHANGELOG.md`
  - ADRs, falls neue Architekturentscheidungen entstanden sind
- GitHub Issues kommentieren und schliessen:
  - `#170`
  - `#171`
  - `#172`, wenn fachlich erledigt oder bewusst verschoben/korrigiert
  - `#173`
  - `#182`
  - `#183`
  - `#184`
  - `#185`
  - `#186`

### Quality Gate

Backend, falls Backend geaendert:

```powershell
uv run --python 3.12 ruff check .
uv run --python 3.12 ruff format --check .
uv run --python 3.12 mypy app
$env:ENCRYPTION_KEY='AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA='; uv run --python 3.12 pytest --no-cov
```

Frontend:

```powershell
pnpm --filter @correlcore/web typecheck
pnpm --filter @correlcore/web lint
pnpm --filter @correlcore/web test -- --run
pnpm --filter @correlcore/web build
```

Rendered QA:

- Browser/IAB oder Playwright Screenshot QA.
- Desktop und Mobile Screenshots.
- Keine Framework Error Overlays.
- Keine relevanten Console Errors.
- Core Interactions:
  - Home -> Entry Sheet -> Auto-Save -> Day Delta
  - Insights -> Filter -> Disclaimer -> Details
  - Trends -> Tab -> Data point -> Entry History Sheet
  - Settings -> Language -> Theme -> Dev Unlock -> Force Viz

## Cross-Sprint Abhaengigkeiten

| Thema                                | Blockiert      | Klaerung                                          |
| ------------------------------------ | -------------- | ------------------------------------------------- |
| `sleep_quality` fehlt im Entry Model | Sprint 3       | Migration in M3.5 oder Issue auf M7 korrigieren   |
| `svelte-i18n` vs `paraglide-js`      | Sprint 7       | Kein paralleler Store; Entscheidung dokumentieren |
| Primary Farbe teal vs violett        | Sprint 0       | ADR oder FRONTEND.md Korrektur                    |
| Stress-Inversion                     | Sprint 2, 6, 8 | zentrale Metric Config plus Backend-Semantik      |
| Bottom Sheet Entry                   | Sprint 1, 3, 4 | Shell zuerst, Sheet danach                        |
| Force Visualizations                 | Sprint 5, 6, 7 | Mock-Daten muessen alle Visualisierungen bedienen |

## Empfohlene PR-Struktur

Um Review-Risiko klein zu halten, sollte M3.5 nicht als ein einzelner Riesen-PR
umgesetzt werden.

1. `m3.5-00-foundation`
2. `m3.5-01-app-shell`
3. `m3.5-02-entry-foundation`
4. `m3.5-03-entry-sheet`
5. `m3.5-04-home-recomposition`
6. `m3.5-05-insight-quality`
7. `m3.5-06-trends-tabs`
8. `m3.5-07-settings-language-dev`
9. `m3.5-08-tag-lifecycle`
10. `m3.5-09-docs-qa-closeout`

Jeder PR muss:

- die betroffenen GitHub Issues referenzieren,
- lokale Tests dokumentieren,
- visuelle QA fuer mindestens 375 px und 1280 px enthalten,
- Light/Dark Mode pruefen,
- Abweichungen von `FRONTEND.md` dokumentieren.

## Definition of Done fuer M3.5

M3.5 ist abgeschlossen, wenn:

- alle Sprint-PRs gemerged sind,
- alle M3.5 Issues geschlossen oder bewusst neu gescoped sind,
- `docs/FRONTEND.md` dem realen UI entspricht,
- `docs/M3_5_SPRINT_STATUS.md` den Abschlussstand dokumentiert,
- `CHANGELOG.md` M3.5 enthaelt,
- lokale und GitHub-CI-Gates gruen sind,
- Web und Mobile QA dokumentiert ist,
- keine bekannten horizontalen Scroll-/Overlap-/Touch-Target-Probleme auf
  375 px bestehen,
- keine No-Gamification-Verstoesse in sichtbarer Copy oder UI verbleiben,
- GitHub nach Merge neue Container Images fuer API und Web gebaut hat.

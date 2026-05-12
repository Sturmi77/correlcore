# M3 Sprint- und Issue-Status

Stand: 2026-05-12

Dieses Dokument fasst den aktuellen M3-Arbeitsstand auf `main` zusammen. Es
trennt bewusst zwischen lokal implementierten Sprints und dem offiziellen
GitHub-Issue-Status. Die GitHub-Issues #151 bis #159 waren zum Zeitpunkt dieser
Dokumentation remote noch offen.

## Mainline-Stand

`main` enthaelt aktuell diese M3-/No-Gamification-Sprint-Commits:

| Sprint | Commit    | Status      | Kurzinhalt                                                                               |
| ------ | --------- | ----------- | ---------------------------------------------------------------------------------------- |
| 1      | `22553cc` | geschlossen | No-Gamification-Prep: sichtbare Entry-Run-Copy auf Tracking Consistency umgestellt.      |
| 2      | `46b03d3` | geschlossen | Insight- und Preference-Foundation: Migration, Modelle, Schemas, Analytics-Dependencies. |
| 3      | `bf61d65` | geschlossen | Analytics Engine v1: tiered Kandidaten, Spearman, Point-biserial, Weekday Pattern.       |
| 4      | `1e75262` | geschlossen | Analytics Worker: nightly Insight-Generation fuer aktive/verifizierte User.              |
| 5      | `0759f50` | geschlossen | Read-API: `GET /api/v1/insights` und `/insights/latest`.                                 |
| 6      | `1b92ee4` | geschlossen | Web Home Preview: neuester Insight read-only auf der Home-Seite.                         |

## Geschlossene Sprints

### Sprint 1 - No-Gamification Prep

Scope: Web-Copy only. Die sichtbare Streak-Framing-Copy wurde auf Tracking
Consistency umgestellt, inklusive Locale-Regressionscheck gegen
Reward-/Badge-/Fire-/Streak-Wording.

Issue-Bezug: #158 ist lokal erfuellt, aber remote noch offen.

### Sprint 2 - Insight/Preference Foundation

Scope: Backend Foundation. Angelegt wurden `insights` und `user_preferences`
inklusive RLS, verschluesseltem `statement_enc`, Tier-/Confidence-/Sample-Feldern
und `analytics_enabled`.

Issue-Bezug: technische Grundlage fuer #151, #152, #155 und #156.

### Sprint 3 - Analytics Engine v1

Scope: interne Engine ohne API/Worker. Implementiert wurden Tier-Grenzen,
Weekday-Pattern ab 7 Eintraegen, Spearman- und Point-biserial-Kandidaten,
neutrale Statements und Safety-Flags.

Issue-Bezug: wesentliche Backend-Teile von #151 und #155 sind vorhanden.

### Sprint 4 - Worker-Anbindung

Scope: Worker only. Der bestehende Analytics Worker generiert nightly Insights
pro berechtigtem User, bindet den User-DEK und isoliert Fehler pro User.

Issue-Bezug: operationalisiert #151/#155-Grundlagen.

### Sprint 5 - Read-API

Scope: Backend API read-only. Verfuegbar sind:

- `GET /api/v1/insights`
- `GET /api/v1/insights/latest`

Die Endpunkte sind owner-gefiltert, rate-limitiert und geben `tier`,
`confidence`, `sample_n`, Statement und Metadaten aus.

Issue-Bezug: API-Anteil von #151 ist implementiert.

### Sprint 6 - Home Insight Preview

Scope: Web only. Neuer `insights`-Client, neue `HomeInsight`-Komponente und
Home-Anbindung fuer den neuesten worker-generierten Insight. Der Insight-Fetch
ist best-effort und blockiert Recent Entries, Summary oder Sparkline nicht.

Issue-Bezug: UI-Anteil von #151 ist teilweise implementiert; #155 kann bereits
als normaler latest Insight sichtbar werden, aber noch ohne Weekday-Chart und
ohne dismissbare First-Week-Karte.

## Offene Sprints

Empfohlene naechste Reihenfolge:

| Naechster Sprint | Primaeres Issue | Status          | Abhaengigkeiten                             | Scope                                                                                |
| ---------------- | --------------- | --------------- | ------------------------------------------- | ------------------------------------------------------------------------------------ |
| 7                | #153            | offen           | Sprints 2-6                                 | Insight Confidence Scale, Dashboard Summary/Confidence Score, permanente Home-Skala. |
| 8                | #155            | offen/teilweise | #151, #153 empfohlen                        | WeekdayPatternChart, first-week neutral banner, Dismiss-State in Preferences.        |
| 9                | #154            | offen           | Entry API/Tags vorhanden                    | Day-over-Day Delta nach Auto-Save und auf Entry-Form.                                |
| 10               | #152            | offen           | Preferences, Entry Batch/API-Aenderung      | Retrospective 7-day onboarding import.                                               |
| 11               | #156            | offen           | Preferences/Profile API, Onboarding-Routing | Optionales Profil-Onboarding und statische Insight-Previews.                         |

M5-Issues #157 und #159 bleiben ausserhalb des M3-Sprint-Scopes. Sie sind fuer
die spaetere Habit-UI relevant, nutzen aber M3-Insight-Daten als Grundlage.

## GitHub-Issue-Status

| Issue                                        | GitHub-Status | Implementierungsstand                  | Abschlussnotiz                                                                                                                                                                   |
| -------------------------------------------- | ------------- | -------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| #151 Tiered Confidence System                | offen         | teilweise bis weitgehend implementiert | Model/API/Worker/Home enthalten `tier`, `confidence`, `sample_n`; offen bleiben Abnahme der Acceptance Criteria, explizite Review-Checkliste und ggf. Tooltip/Visual-Finetuning. |
| #152 Retrospective Entry Import              | offen         | nicht gestartet                        | Neuer Batch-Endpoint, `EntrySource` und Onboarding-Flow fehlen.                                                                                                                  |
| #153 Insight Confidence Scale                | offen         | nicht gestartet                        | Noch kein Dashboard Summary Endpoint und keine Confidence-Scale-Komponente.                                                                                                      |
| #154 Day-over-Day Delta                      | offen         | nicht gestartet                        | Delta-Endpoint und `DayDeltaCard` fehlen.                                                                                                                                        |
| #155 First-Week Tracking Consistency Insight | offen         | teilweise implementiert                | Backend kann Weekday-Pattern erzeugen und Home kann latest Insight anzeigen; Weekday-Chart, one-time banner und Dismiss-State fehlen.                                            |
| #156 Onboarding Questionnaire                | offen         | nicht gestartet                        | Profil-API, Preview-Library und Onboarding-Route fehlen.                                                                                                                         |
| #157 M5 No-Gamification Habit Redesign       | offen         | nicht M3                               | Architektur-/M5-Folgearbeit; Sprint 1 hat den M2-Followup vorbereitet.                                                                                                           |
| #158 M2 Tracking Consistency Relabel         | offen         | lokal implementiert                    | Kann nach Review/visueller 375px-Pruefung in GitHub geschlossen werden.                                                                                                          |
| #159 M5 Habit Dashboard                      | offen         | nicht M3                               | Wartet auf M5 Habit-Scope und kann spaeter M3-Korrelationen nutzen.                                                                                                              |

## Verifikation

Zuletzt ausgefuehrte Checks:

- Backend bis Sprint 5: `ruff`, `ruff format`, `mypy`, `pytest` mit 351 Tests gruen.
- Web Sprint 6: `pnpm --filter @correlcore/web test` mit 177 Tests gruen.
- Web Sprint 6: `pnpm --filter @correlcore/web typecheck` gruen.
- Web Sprint 6: `pnpm --filter @correlcore/web lint` gruen.
- Web Sprint 6: `pnpm --filter @correlcore/web build` gruen.
- Sprint-Dateien: gezielter Prettier-Check gruen.
- Locale-Copy: No-Gamification-Regressionscheck gruen.

Hinweis: Der globale Web-`format:check` prueft derzeit auch generierte
`.svelte-kit`-/`build`-Artefakte und vorhandene Repo-Format-Warnungen ausserhalb
des Sprint-Scopes. Die angefassten Sprint-Dateien sind Prettier-konform.

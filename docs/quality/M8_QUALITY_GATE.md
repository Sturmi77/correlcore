# M8 Quality Gate — Sleep & Health Connect

> **Historical** — M8 closeout record (2026-08-02). Living strategy:
> [`TESTING.md`](TESTING.md).

**Milestone:** M8 — Schlaf & Health Connect (core: manual sleep, sleep↔mood, HC bridge, sleep import)
**Stand:** 2026-08-02 (Sprint 5 closeout)
**Referenz:** [`DESIGN_DOCUMENT.md` §9](../DESIGN_DOCUMENT.md), [`M8_SPRINT_STATUS.md`](../M8_SPRINT_STATUS.md)

Bündelt den Quality-Gate über M8 Sprints 1–5. Cycle-Health-Connect, Phase-Bands,
Sleep×Symptom, HR-Persistenz und der native Background-Sync sind **nicht** Teil des
M8-Kern-Exit (siehe Deferrals im Sprint-Status).

---

## 1. Scope

| Bereich                                                  | Sprint | Status                          |
| -------------------------------------------------------- | ------ | ------------------------------- |
| Manuelle Schlaffelder (`sleep_minutes`, `sleep_quality`) | 1      | shipped                         |
| Schlaf↔Mood-Spearman + Sleep-Design-Matrix-Spalten       | 2      | shipped                         |
| Nativer Health-Connect-Bridge (Kotlin) + Rationale       | 3      | shipped (nativ nicht CI-gebaut) |
| Consent-gated Sleep-Import + per-Feld-Toggle             | 4      | shipped                         |
| Closeout (Docs, Cascade-Test, Gate)                      | 5      | shipped                         |

## 2. Statische Analyse & Tests

| Tool / Suite                                                                                              | Ergebnis                                |
| --------------------------------------------------------------------------------------------------------- | --------------------------------------- |
| `svelte-check` (Web-Typecheck)                                                                            | 0 errors, 0 warnings                    |
| Web-Unit-Tests (sleep, sleep↔mood, HC-Bridge, Import-Aggregation)                                         | grün                                    |
| `noGamificationCopy` Copy-Lint                                                                            | grün                                    |
| `check:style-contract`                                                                                    | grün (46 Color-Tokens, Shared-Variants) |
| Backend-Tests (entries, export, sync, insight-engine, multivariate, preferences, api-contract, hc-import) | grün                                    |
| i18n Locale-Parität (`localeCompleteness`)                                                                | grün                                    |

Nicht in CI gebaut: der native Kotlin/Gradle-Pfad (kein Android-SDK). Nur der
config-only `pnpm --filter @correlcore/android validate` läuft (OK).

## 3. Sicherheit & Datenschutz (DSGVO)

| Punkt                                    | Bewertung                                                                                       |
| ---------------------------------------- | ----------------------------------------------------------------------------------------------- |
| Art. 9 Consent vor Import                | ✅ Endpoint gibt 403 ohne `consent_log`-Grant                                                   |
| Daten-Minimierung                        | ✅ Native Permission-Menge fix auf `READ_SLEEP` + `READ_HEART_RATE`; Import schreibt nur Schlaf |
| Keine Third-Party-Weitergabe             | ✅ on-device (ADR-0042), keine Cloud-Aggregatoren                                               |
| Health-Daten im Error-Tracking redigiert | ✅ `sleep_minutes`/`sleep_quality` in `_SENSITIVE_KEYS`                                         |
| Löschung bei Account-Delete              | ✅ `entries` ON DELETE CASCADE (Test: `test_imported_sleep_rides_account_delete_cascade`)       |
| Manual wins / keine erfundenen Einträge  | ✅ Import füllt nur NULL-`sleep_minutes`, erzeugt keine mood-losen Zeilen                       |
| Kein medizinischer Claim                 | ✅ Statements „not a diagnosis"; Rationale ohne Diagnose-Sprache                                |

## 4. Offene Punkte (kein M8-Kern-Blocker)

- Manuelle Geräte-QA des HC-Permission-Flows auf Sideload-APK (inkl. gehärtete ROMs) —
  [`features/HEALTH_CONNECT.md`](../features/HEALTH_CONNECT.md).
- Visual-QA 375/768 px hell+dunkel — [`M8_VISUAL_QA.md`](M8_VISUAL_QA.md).
- CI baut den nativen Pfad nicht; ein Release erfordert einen lokalen `cap:assemble`.

## 5. Gate-Ergebnis

**Bestanden für den M8-Kern** (Backend + Web verifiziert). Der native Health-Connect-Pfad
ist **implementiert, aber nicht maschinell verifiziert** — Geräte-QA ist Vorbedingung für
einen Sideload-/Play-Release.

# PR-Review-Fix-Plan (28.07.–31.07.2026)

> **Ziel-PR:** `cursor/pr-review-fixes-a8b8` → `main`  
> **Quelle:** Codex P1/P2 + Cursor Risk-Kommentare auf 26 PRs (inkl. gemergte)  
> **Stand:** 2026-07-31

## Executive Summary

| Kategorie | Gesamt | Bereits behoben (vor Fix-PR) | In Fix-PR | Bewusst deferred |
| --------- | -----: | ---------------------------: | --------: | ---------------: |
| **P1**    |     10 |                            6 |         4 |                0 |
| **P2**    |     36 |                            9 |        24 |                3 |

**Größter Residual-Risk vor Fix-PR:** `lag_profile_backfill` (#596) — RLS, DEK, historischer `as_of`, fehlende Runtime-Scripts im Docker-Image.

**Fix-PR-Strategie:** Ein konsolidierter PR in drei Wellen (Backend-kritisch → UX/Compare/Home → Docs/Runbooks). Kein neues Feature-Scope; nur Review-Follow-ups.

---

## Wave 1 — P1 Backend (Blocker)

### #596 — Lag-Profile-Backfill (4× P1, **offen**)

| # | Finding | Datei | Fix |
| - | ------- | ----- | --- |
| 1 | RLS: `FORCE RLS` ohne `app.current_user_id` → leerer Scan | `lag_profile_backfill_service.py` | Pro User `bind_rls_current_user`; Insight-Query scoped auf `user_id` |
| 2 | DEK nicht gebunden vor `load_analytics_data` / Symptom-Decrypt | `lag_profile_backfill_service.py` | DEK laden wie `workers/digest.py` (`UserEncryptionKey` → `set_current_user_dek`) |
| 3 | Ein globaler `as_of=heute` verfälscht historische Insights | `lag_profile_backfill_service.py` | `LagInsightRow.generated_for_date` + `as_of = generated_for_date + 1 day` pro Row |
| 4 | Script nicht in Production-Container | `Dockerfile`, `scripts/backfill_lag_profile.py` | `scripts/` ins Runtime-Image; Doku: `python scripts/backfill_lag_profile.py` |

**Tests:** `test_lag_profile_backfill.py` — RLS/DEK-Mocks, per-insight `as_of`, Integration smoke optional.

---

## Wave 2 — P2 Produktcode (UX, Sync, Ops)

### #597 — Trends Compare Cluster-Sort (5× P2)

| Finding | Fix |
| ------- | --- |
| Cluster-Focus-Chips in Compact fehlen | Focus-Chips auch bei `compactChrome` (eigene kompakte Zeile) |
| Tag-Gruppen nicht bei Pull-to-Refresh | `loadTagClusters()` aus Trends-Refresh erneut aufrufen (Prop/Event) |
| Compact Settings erlaubt `clustered` ohne Daten | `clustersAvailable` an Settings-Sheet; Option `disabled` |
| Focus bleibt bei leerer Gruppe | `focusedClusterId` auf `null` wenn keine sichtbaren Tags |
| Cluster nicht contig bei Mixed-Layers | Sort: Tag↔Tag cluster order; Cross-kind nach kind + cluster block |

**Dateien:** `TrendsComparePanel.svelte`, `TrendsCompareSettingsSheet.svelte`, `ComparisonHeatmap.svelte`, `routes/trends/+page.svelte`

### #594 — Home Screen (5× P2)

| Finding | Fix |
| ------- | --- |
| Default-Sections flashen vor Prefs-Load | `preferencesLoaded` Gate; Sections erst nach Fetch |
| Editor editierbar vor Load | `loading` initial `true`; Editor `disabled` bis Load |
| Reset-Button Touch-Target | `min-height/min-width: 44px` auf Reset |
| Unbekannte JSONB-Keys crashen Response | `normalize_home_sections` in `to_preferences_response` vor validate |
| SR: Reorder-Buttons ohne Section-Name | `aria-label` mit Section-Label interpolieren |

**Dateien:** `+page.svelte`, `settings/home/+page.svelte`, `HomeSectionsEditor.svelte`, `user_preferences_service.py`

### #598 — Dev-Mode Settings (1× P2)

| Finding | Fix |
| ------- | --- |
| Probe-Fehler = „Backend absichtlich aus" | `devBackendState: 'unknown' \| 'available' \| 'disabled' \| 'error'`; Copy unterscheidet 404 vs Netzwerk |

### #593 — Deploy + Landing (2× P2)

| Finding | Fix |
| ------- | --- |
| `verify-deploy-health.sh` Prefix statt Ancestry | `git merge-base --is-ancestor MIN HEAD` lokal oder semver auf commit date |
| `/?landing=1` + Onboarding-Redirect | Onboarding-Reactive-Block mit `!showLandingPreview` guard |

**Dateien:** `scripts/verify-deploy-health.sh`, `+page.svelte`

### #577 — Insights Viz (2× P2)

| Finding | Fix |
| ------- | --- |
| Landing-Cluster doppelt benannt | `TagGroupsSection`: bei `data.source === 'landing'` kein `card_title`-Prefix |
| Monats-Label bei Monatsanfang | `buildMonthLabels`: Woche dem Monat des **Montags** oder Mehrheit zuordnen |

### #599 — Cycle Settings UI (1× P2, Stage-1-Lücke)

| Finding | Fix |
| ------- | --- |
| `deleteCycleData()` ohne UI | Settings → Cycle: „Zyklusdaten löschen" + Confirm-Dialog (wie Account-Delete light) |

**Dateien:** `settings/+page.svelte`, i18n, `page.test.ts`

---

## Wave 3 — P2 Docs / Specs

### #602 — Dismiss-Archive Draft (3× P2)

| Finding | Fix |
| ------- | --- |
| `_subject_key` existiert nicht | → `_latest_subject_key` + Hinweis auf getrennte Digest-Keys |
| Digest-Filter widersprüchlich | Phase 0: „TBD" explizit; kein hartes AC |
| `generated_for_date` ≠ Occurrence | Abschnitt präzisieren: Analytics-Cutoff vs. Pattern-Occurrence |

### #595 — API/Figma Docs (5× P2)

| Finding | Fix |
| ------- | --- |
| Unknown home-section keys → 422 | In `docs/API.md` dokumentieren |
| Response fields unvollständig | `user_id`, `created_at`, `updated_at` ergänzen |
| `null` PATCH = no-op | Dokumentieren |
| Figma node 19:113 Mapping | README auf `HomeDailyBrief` korrigieren |
| Default section order | `first_week_banner` first in Doku |

---

## Bereits behoben (kein Fix-PR nötig)

| PR | Items | Nachweis |
| -- | ----- | -------- |
| #570 | P1 OOM + P2 DecompressionBomb | Commits `87163db`, Sturmi77 inline replies |
| #581 | P1 analytics exclusion + 2× P2 Explore/dev | Commit `f60fc8c` |
| #580 | 2× P2 strip zoom | Commit `94e5f60` |
| #586 | 3× P2 lag heatmap dedup/a11y/i18n | Commits `23e2e26`, `9e00ce8` |
| #583 | 2× P2 mini-bars | merged, keine offenen Replies |
| #593 P1 | Heatmap pruning threshold | `value > 0` statt `sum >= 1` |
| #599 P1 | Cycle sync/dirty/mypy/sanitise | #606 merged |
| #599 P2 | Dict sanitise | #606 merged |

---

## Bewusst deferred (nicht in Fix-PR)

| PR | Item | Begründung |
| -- | ---- | ---------- |
| #575 | Weekend-Context in Home-Summary | Bewusste Scope-Entscheidung #572; nur Home-Woche |
| #580 | Device QA Strips | Tracking #585; Code grün |
| #602 Option D–F | Archiv-UI | Feature-Scope, nicht Review-Fix |

---

## Commit-Plan (Fix-PR)

```
1. fix(backfill): RLS, DEK, per-insight as_of, Docker scripts (#596 P1)
2. fix(trends): cluster sort P2 batch (#597)
3. fix(home): preferences load gate + editor a11y (#594)
4. fix(settings): dev backend probe states + cycle data delete UI (#598, #599 P2)
5. fix(web): landing onboarding guard + deploy verify ancestry (#593)
6. fix(insights): tag group landing labels + calendar month axis (#577)
7. docs: dismiss draft + API/home figma corrections (#602, #595)
8. test: extend unit/e2e for above
```

---

## Testplan (Fix-PR)

| Layer | Command / Check |
| ----- | ---------------- |
| Backend | `cd backend && uv run mypy app && uv run pytest tests/test_lag_profile_backfill.py tests/test_entries.py -q` |
| Web unit | `pnpm exec vitest run src/lib/components/trends src/lib/components/settings src/routes/settings` |
| Web lint | `pnpm lint && pnpm typecheck` |
| Manual | Settings → Cycle → delete data; Trends Compare clustered compact; Home hidden section no flash |
| Ops | `./scripts/verify-deploy-health.sh` mit neuem/älterem Commit |

---

## Risiko nach Merge

- **Niedrig** für Waves 2–3 (UI/Docs, isolierte Guards).
- **Mittel** für Wave 1: Backfill-Script auf Prod nur nach Dry-Run; DEK/RLS-Pfad muss in Staging verifiziert werden.

---

## Referenzen

- Ursprungs-PRs: #566–#606 (28.07.–31.07.2026)
- ADR SHD: `docs/adr/0033-sensitive-health-data-handling-cycle-signals.md`
- Cycle Stage 2: Settings selective delete war P2 in #599, jetzt in Wave 2 aufgenommen

# [FEATURE] Insight-Dismiss: Wissen erhalten (Archiv / Zeitleiste / Undo)

> GitHub issue: [#601](https://github.com/Sturmi77/correlcore/issues/601)
> Labels: `enhancement`, `frontend`, `backend`, `privacy`, `should`
> Milestone: Backlog / Insights-UX (Post-M10)
>
> **Hinweis:** Dieses Dokument analysiert Ist-Zustand und Umsetzungsoptionen.
> Es ist noch keine Implementierungsentscheidung. Kanonische Spec parallel zum Issue.

---

## Feature-Beschreibung

Wenn Nutzer:innen Insights „wegklicken“ (Dismiss), soll das dahinterliegende Wissen **nicht verloren gehen**. Es braucht einen klaren Lifecycle:

1. **Aktiver Feed** — aktuelle, nicht dismissed Insights (wie heute `/insights`).
2. **Wiederauffindbarkeit** — dismissed / historische Insights später wieder einsehen, idealerweise dem **Zeitpunkt des Auftretens** zuordenbar (Zeitleiste / Archiv).
3. **Stabile Absicht** — Dismiss meint „jetzt nicht zeigen“, nicht „für immer löschen“; Undo und ggf. „dieses Muster dauerhaft ausblenden“ trennen.

Dieses Issue entscheidet **nicht** pauschal eine UI, sondern bewertet Optionen A–F unten und empfiehlt eine gestaffelte Umsetzung.

## Problem / Motivation

### Ist-Zustand (Code, Stand main)

Dismiss ist heute **kein Soft-Delete und kein Archiv**, sondern ein **Client-seitiges Hide** über Preference-Keys:

| Schicht       | Verhalten                                                                                                                                                               |
| ------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| UI            | ✕ auf [`InsightCard`](../../apps/web/src/lib/components/insights/InsightCard.svelte) → `dismiss`                                                                        |
| Store         | [`dismissInsight(id)`](../../apps/web/src/lib/stores/insights.ts) filtert lokal und PATCH’t Preferences                                                                 |
| Persistenz    | `UserPreference.dismissed_insight_keys` (JSONB `string[]`, max **128**) — UUID-Keys und Banner-Keys                                                                     |
| Insight-Zeile | [`Insight`](../../backend/app/models/insight.py) hat **kein** `status` / `dismissed_at` / Soft-Delete                                                                   |
| API           | Kein `DELETE`/`PATCH /insights/{id}`; nur Prefs + `GET /insights`, `GET /insights/latest`, Regenerieren, Digest                                                         |
| Feed          | Frontend filtert dismissed UUIDs; Backend liefert sie weiterhin                                                                                                         |
| Regenerieren  | [`generate_and_store_insights`](../../backend/app/services/insight_engine.py) **hard-deletet** alle Rows für `(user_id, generated_for_date)` und legt **neue UUIDs** an |
| Digest        | Ranking berücksichtigt `dismissed_insight_keys` **nicht**                                                                                                               |
| Export        | Insights im DSGVO-Export aktuell Stub/leer                                                                                                                              |

Historische Rows über mehrere `generated_for_date` existieren in der DB; `list_insights` ist chronologisch (newest-first), die Produkt-UI nutzt aber vor allem `/latest` (Dedup pro semantischem Subject). Es gibt **keine** Archiv-/Zeitleisten-Oberfläche und **kein Undo**.

### Konkrete Wissens- und UX-Lücken

1. **Subjektiv „weg“** — User sieht den Insight nicht mehr; es gibt keinen Weg zurück (kein „Dismissed“-Bereich, kein Undo).
2. **ID-basiertes Dismiss ist fragil** — Same-Day-Regenerate → neue UUID → gleiches Muster kann wieder erscheinen; alte Keys verbleiben und füllen das 128-Cap.
3. **Kein Subject-stabiles „nie wieder“** — man kann nicht dauerhaft „dieses Sport↔Mood-Muster“ ausblenden.
4. **Server ignoriert Dismiss** — Digest / API / künftige Surfaces können dismissed Insights weiter zeigen.
5. **Keine Zeitachse** — Wann trat das Muster erstmals / zuletzt auf? DB hat `generated_for_date` / `generated_at`, UI nicht.
6. **Kein Audit** — kein `dismissed_at`, kein Grund, keine Export-Historie der Dismissals.

Nutzer:innen, die Insights bewusst wegklicken (zu früh, irrelevant, emotional belastend, „weiß ich schon“), verlieren damit faktisch die Möglichkeit, später nachzuschlagen: _„Was hat die App damals erkannt?“_

## Analyse der Optionen

### Option A — Minimal: Undo + „Ausgeblendete Insights“-Liste (Prefs bleiben)

**Idee:** Weiterhin `dismissed_insight_keys`, aber UI zeigt eine Sektion „Ausgeblendet“ (oder Settings) mit Undo (= Key aus Liste entfernen).

| Pro                                    | Contra                                                          |
| -------------------------------------- | --------------------------------------------------------------- |
| Sehr geringer Aufwand (nur FE + Prefs) | Kein echter Zeitbezug; nur aktuelle Rows mit noch gültiger UUID |
| Keine Migration                        | Regenerieren bricht Zuordnung weiterhin                         |
| Schnelles Undo                         | Kein Server-Filter; Digest bleibt inkonsistent                  |

**Umsetzbarkeit:** Hoch. Änderungen: `insights` Store (`undismissInsight`), UI-Sektion auf `/insights` oder Settings, i18n, Tests. Backend optional: Prefs-Merge statt Full-Replace dokumentieren.

**Eignet sich als:** Sofort-Fix gegen „Wissen ist weg“, aber **nicht** als Archiv/Zeitleiste.

---

### Option B — Server-seitiger Insight-Status (Soft-Dismiss auf der Row)

**Idee:** Spalten z. B. `dismissed_at TIMESTAMPTZ NULL`, optional `dismiss_reason`, ggf. `visibility: active|dismissed|archived`. Dismiss = `PATCH /insights/{id}` statt Prefs-UUID-Liste.

| Pro                                         | Contra                                                                           |
| ------------------------------------------- | -------------------------------------------------------------------------------- |
| Querybar, exportierbar, Digest kann filtern | Same-Day-Regenerate löscht die Row → Status geht verloren, sofern nicht migriert |
| `dismissed_at` für Zeitleiste               | Migration + API + FE-Umschreibung                                                |
| Klarer Lifecycle auf dem Insight            | Banner-Keys (`early_context_pattern`) bleiben Prefs                              |

**Umsetzbarkeit:** Mittel. Migration auf `insights`, Endpoints, `list_latest_insights`/`list_insights` mit `include=dismissed|active`, Digest-Filter, Prefs-Deprecation/Migration der UUID-Keys.

**Risiko:** Ohne Anpassung der Engine (Regenerate) bleibt Soft-Dismiss fragil.

---

### Option C — Subject-stabile Dismissals (Muster ausblenden)

**Idee:** Statt UUID einen **semantischen Subject-Key** speichern (gleiche Logik wie `_latest_subject_key` in [`insight_service.py`](../../backend/app/services/insight_service.py): Typ + Metric + Subject/Slug/Lag). Prefs oder eigene Tabelle `insight_dismissals(user_id, subject_key, dismissed_at, mode)`.

| Pro                                | Contra                                                                                    |
| ---------------------------------- | ----------------------------------------------------------------------------------------- |
| Überlebt Regenerieren / neue UUIDs | Subject-Key-Evolution (Legacy Tags, Lag-Payload) muss stabil bleiben                      |
| „Dieses Muster nicht mehr zeigen“  | Historische Instanzen des Musters trotzdem sichtbar machen braucht zusätzliche History-UI |
| Cap sinnvoller als 128 UUIDs       | Banner-Keys weiterhin separat                                                             |

**Umsetzbarkeit:** Mittel. Backend: Subject-Key-Helper teilen; Prefs oder Tabelle; Engine/Digest respektieren Keys; FE: Dismiss sendet Subject-Key (+ optional UUID für Instant-Hide).

**Empfehlung:** Dismiss-Intent sollte mittelfristig **subject-stabil** sein; UUID-only ist technische Schuld.

---

### Option D — Archiv mit Zeitleiste (History-Surface)

**Idee:** Produkt-Surface „Insight-Verlauf“ / Archiv:

- Chronologisch nach `generated_for_date` oder `generated_at` (Tage/Wochen gruppieren).
- Filter: aktiv / dismissed / alle; nach Typ/Tier/Subject.
- Klick öffnet Detail (Statement, Stats, Flags) — Wissen bleibt lesbar.
- Optional: erste vs. letzte Beobachtung pro Subject („seit 12.03. sichtbar“).

Datenbasis: bestehende `insights`-Rows + Digests (`insight_digests.insight_ids`). Lücken: Same-Day-Hard-Delete entfernt Tagesversionen; Retention-Policy fehlt.

| Pro                                            | Contra                                                   |
| ---------------------------------------------- | -------------------------------------------------------- |
| Beantwortet die Kernfrage „wann trat das auf?“ | UI-Aufwand; Mobile-Layout                                |
| Nutzt vorhandene History-Rows + `/insights`    | Engine muss History **nicht** mehr wegwerfen (Retention) |
| Passt zu Weekly Digest als Wochen-Snapshots    | Speicherkosten / Encryption der Statements               |

**Umsetzbarkeit:** Mittel–hoch je nach Scope.

**Voraussetzungen:**

1. Retention: Regenerieren darf History nicht blind zerstören — z. B. nur „aktive“ Tages-Rows ersetzen **oder** Append-only + `superseded_by` **oder** Snapshot vor Delete.
2. API: `GET /insights?from=&to=&status=&group_by=date` (Pagination).
3. FE: Timeline-View; Dismissed opt-in sichtbar.
4. Digest-Hydration: bereits bekannt, dass gelöschte IDs Hydration brechen ([Weekly Digest Plan](../features/WEEKLY_DIGEST_COMPLETION_PLAN.md)).

---

### Option E — Append-only Insight-Events / Snapshot-Archiv

**Idee:** Dismiss und Generierung als Events: `insight_events(kind=generated|dismissed|restored|superseded, insight_id|snapshot, at)`. Oder bei Regenerieren Statement+Metadaten in `insight_archive` kopieren, bevor hard-delete.

| Pro                               | Contra                                     |
| --------------------------------- | ------------------------------------------ |
| Audit-tauglich, DSGVO-Export klar | Höchste Komplexität                        |
| Unabhängig von Live-Row-Lifecycle | Doppelte encrypted Blobs                   |
| Echte Zeitleiste auch nach Delete | Mehr Storage; Retention/Löschkonzept nötig |

**Umsetzbarkeit:** Niedriger Priorität / späteres Hardening. Sinnvoll wenn Insights rechtlich/historisch nachvollziehbar bleiben müssen.

---

### Option F — Nur Digest als „Wochenarchiv“

**Idee:** Weekly Digests ([`insight_digests`](../../backend/app/models/insight_digest.py)) als leichtgewichtiges Archiv; dismissed Insights trotzdem in Digest-Snapshots.

| Pro                     | Contra                                    |
| ----------------------- | ----------------------------------------- |
| Infrastruktur existiert | Nur Wochengranularität; nur Top-N         |
| Wenig neuer Code        | `insight_ids` ohne Row → Hydration bricht |
|                         | Kein täglicher Dismiss-Lifecycle          |

**Umsetzbarkeit:** Hoch als Ergänzung, **unzureichend** als alleinige Lösung.

---

## Vergleich (Kurz)

| Option                      | Wissen erhalten       | Zeitbezug            | Überlebt Regenerate  | Aufwand     | Empfohlen            |
| --------------------------- | --------------------- | -------------------- | -------------------- | ----------- | -------------------- |
| A Undo + Ausgeblendet-Liste | teilweise             | nein                 | nein                 | niedrig     | Phase 0              |
| B Soft-Dismiss auf Row      | ja (solange Row lebt) | `dismissed_at`       | nein ohne Engine-Fix | mittel      | Phase 1 Baustein     |
| C Subject-stabile Keys      | Intent ja             | via Join auf History | **ja**               | mittel      | Phase 1 Kern         |
| D Timeline/Archiv-UI        | ja                    | **ja**               | braucht Retention    | mittel–hoch | Phase 2              |
| E Event/Snapshot-Archiv     | vollständig           | ja                   | ja                   | hoch        | Phase 3 / Compliance |
| F Digest-only               | schwach               | Wochen               | bedingt              | niedrig     | Ergänzung            |

## Vorgeschlagene Lösung (gestaffelt)

### Phase 0 — Sofort-UX (ohne Schema-Bruch)

- Undo + Sektion „Ausgeblendete Insights“ auf `/insights` (oder Settings).
- Server: Digest und `GET /insights/latest` respektieren `dismissed_insight_keys` (Konsistenz) — **TBD:** exakte Digest-Filter-Semantik für dismissed Keys ist noch nicht final spezifiziert; Phase 0 dokumentiert nur die Intent-Richtung.
- Prefs: append/remove Helpers statt blindem Full-Replace; orphaned UUID-Keys beim Load bereinigen.

**Hinweis `generated_for_date` vs. Occurrence:** `generated_for_date` ist der Analytics-Cutoff-Tag (wann der Insight generiert wurde), nicht zwingend der Kalendertag des beobachteten Musters. Für Zeitleisten-Archiv (Phase 2) braucht es zusätzliche Occurrence-Metadaten.

### Phase 1 — Stabiler Dismiss-Intent

- Subject-Key-Dismiss (Option C), parallel UUID für Instant-UI.
- Optional `dismissed_at` / kleine Tabelle `insight_dismissals`.
- API: `POST/DELETE /insights/dismissals` oder PATCH mit Subject-Key.
- Klare Semantik: **Hide** (temporär / dieses Vorkommen) vs. **Mute Muster** (subject-stabil).

### Phase 2 — Archiv mit Zeitleiste

- Retention-Policy in der Engine: History über `generated_for_date` behalten (kein blindes Hard-Delete aller Vergangenheit; Same-Day-Idempotenz anders lösen).
- `GET /insights/history` (Zeitraum, Status, Pagination).
- UI: Zeitleiste (Tag/Woche), Filter aktiv/dismissed, Deep-Link aus Digest.
- Pro Subject optional „Verlauf“ (erste/letzte Beobachtung, Tier-Entwicklung).

### Phase 3 — (Optional) Audit & Export

- Events/Snapshots (Option E) falls nötig für Export/Compliance.
- Insights + Dismissals in DSGVO-Export aufnehmen.

### Nicht-Ziele (dieses Issue)

- Gamification / Streaks um Dismissals.
- Automatisches Re-Surfacing ohne User-Kontrolle (Mute muss Mute bleiben).
- Öffentliches Teilen von Insights.

## Alternativen

- **Nur Copy ändern** („wegklicken = ausblenden, Daten bleiben“) — reduziert Verwirrung, löst Wiederauffindbarkeit nicht.
- **Hard-Delete bei Dismiss** — widerspricht dem Ziel; Wissen geht wirklich verloren.
- **Nur clientseitiges localStorage-Archiv** — nicht multi-device, nicht exportierbar, ungeeignet.

## Offene Produktfragen

1. Bedeutet ✕ eher „später nochmal“ (snooze), „dieses Vorkommen weg“ oder „Muster mute“?
2. Sollen dismissed Insights im Weekly Digest erscheinen?
3. Wie lange History speichern (90 Tage / unendlich / bis User-Löschung)?
4. Darf die Zeitleiste auch **aktive** historische Versionen zeigen (Muster-Evolution), oder nur dismissed?

## Milestone

Backlog / Insights-UX (Post-M10) — Phase 0–1 als `should`, Phase 2 als eigenes Follow-up möglich.

## Datenschutz-Impact

Ja — Insights enthalten verschlüsselte Statements und abgeleitete Gesundheits-/Verhaltenssignale.

- Dismiss-Metadaten (`dismissed_at`, Subject-Keys) sind Nutzerverhalten und gehören in Export/Löschkonzept.
- Längere Retention erhöht Speichermenge verschlüsselter Blobs; Löschung bei Account-Delete (`CASCADE`) muss weiter greifen.
- Keine neuen Third-Party-Transfers; Server-seitiger Filter verhindert unbeabsichtigtes Surfacing in Digest/Push.
- UI „Archiv“ macht historische Ableitungen wieder sichtbar — klare Kennzeichnung als vergangene Auswertung, keine kausalen Claims (bestehende No-Gamification / Non-causal Copy).

## Betroffene Dateien (Orientierung)

| Bereich           | Pfad                                                                                        |
| ----------------- | ------------------------------------------------------------------------------------------- |
| Model Insight     | `backend/app/models/insight.py`                                                             |
| Prefs             | `backend/app/models/user_preference.py`, `schemas/user_preferences.py`                      |
| Engine Regenerate | `backend/app/services/insight_engine.py`                                                    |
| List/Latest       | `backend/app/services/insight_service.py`                                                   |
| Digest            | `backend/app/services/insight_digest.py`                                                    |
| API               | `backend/app/api/v1/endpoints/insights.py`, `user.py`                                       |
| FE Store/UI       | `apps/web/src/lib/stores/insights.ts`, `InsightCard.svelte`, `routes/insights/+page.svelte` |
| Docs              | `docs/API.md`, Weekly-Digest-Plan                                                           |

## Akzeptanzkriterien (für die spätere Umsetzung)

- [ ] Dismiss entfernt Insight aus dem aktiven Feed, löscht aber nicht irreversibel das Wissen.
- [ ] Nutzer:in kann dismissed Insights wiederfinden und optional wieder einblenden (Undo).
- [ ] Dismiss-Intent überlebt Same-Day-Regenerate (Subject-Key oder äquivalent).
- [ ] Digest/API respektieren Dismiss-Intent serverseitig.
- [ ] (Phase 2) Zeitleiste ordnet Insights einem Auftretenszeitpunkt (`generated_for_date` / Äquivalent) zu.
- [ ] Export/Löschung berücksichtigen Dismiss- und History-Daten.
- [ ] Tests: Prefs/Subject-Dismiss, Engine-Retention, FE Undo/Archiv; keine Regression der Maturity-Milestones (`reached_milestone_keys`).

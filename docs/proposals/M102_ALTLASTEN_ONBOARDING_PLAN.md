# M10.2 Altlasten-Abschluss + Onboarding/Landing-Plan

> **Stand:** 2026-07-26 · **Branch:** `claude/m102-altlasten-onboarding`
> **Zweck:** Vor neuen Features die M10.2-Altlasten sauber schließen, dann
> Onboarding + Landing so weit definieren und umsetzen, dass neue User Tag,
> Habit, Symptom **und Zyklus** verstehen.
> **Quellen:** [M10.2 STATUS](../M10_2_PUBLIC_HOSTED_LAUNCH_STATUS.md) ·
> [M10.2 BACKLOG](../M10_2_PUBLIC_HOSTED_LAUNCH_BACKLOG.md) ·
> [Backlog-Triage 2026-07-23](BACKLOG_TRIAGE_2026-07-23.md) ·
> [cycle-tracking.md](../features/cycle-tracking.md) · ADR-0008/0012/0021/0025/0030/0031–0034

---

## Phase 0 — Abschluss der finalisierten Punkte dokumentieren

Der Cutover auf `correlcore.com` ist real erfolgt (belegt durch die Live-Fixes
#526/#527 Auth-Cookie am Proxy, #531/#533 self-contained Nginx-Edge, #540
502-Proxy-Buffer, sowie die live gestellte Landing #510/#512). M10.2 ist damit
**„Repo done" + Cutover done** — offen sind nur noch Verifikation, Doku-Sync und
zwei echte Restarbeiten.

### 0.1 Als abgeschlossen dokumentieren / schließen

| Issue | Was                          | Aktion                                                                                                            |
| ----- | ---------------------------- | ----------------------------------------------------------------------------------------------------------------- |
| #463  | Landing Android-Download-CTA | bereits geschlossen ✅                                                                                            |
| #460  | DNS + Nginx-Edge             | Einmal öffentlichen Smoke `GET /` + `/api/v1/health` ohne VPN belegen (S1-O7), Ergebnis ins Issue → **schließen** |
| #459  | Sprint-Tracking-Doc          | zuletzt schließen, wenn 0.2 + Phase 2 durch sind                                                                  |

### 0.2 Vor dem Schließen erledigen (billige Repo-Bereinigung)

| Punkt                                     | Datei / Stelle                                                                                                                                                             | Aktion                                                                                                                                                |
| ----------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------- |
| Kontakt-Domain `.app`→`.com` (#462 S3-R1) | [SECURITY.md:14](../../SECURITY.md), [GO_PUBLIC_CHECKLIST.md:23,133,137](../selfhost/GO_PUBLIC_CHECKLIST.md), [incident-response.md:125](../runbooks/incident-response.md) | `security@correlcore.app` → `security@correlcore.com`. **Nicht** anfassen: `de.correlcore.app` (Android-Package), `docs.correlcore.app` (Docs-Domain) |
| M10.2 STATUS/BACKLOG stale                | [STATUS.md](../M10_2_PUBLIC_HOSTED_LAUNCH_STATUS.md), [BACKLOG.md](../M10_2_PUBLIC_HOSTED_LAUNCH_BACKLOG.md)                                                               | „Pending topology / Exit criteria not met" auf Ist-Stand (Cutover done) aktualisieren oder archivieren                                                |

### 0.3 Noch offen — echte Restarbeit (kein Altlast-Abschluss)

| Issue | Was                                        | Einordnung                                                                                                                                                                                                               |
| ----- | ------------------------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| #461  | Echtes SMTP + Mailpit aus dem Hosted-Stack | **Prüfen:** `mailpit` in [docker-compose.yml:279](../../infra/docker/docker-compose.yml) hat **kein `profiles:`-Gate** → startet immer. Für Hosted per Profil ausnehmen; SPF/DKIM/DMARC + Verify/Reset E2E bestätigen    |
| #464  | NAS→VPS-Runbook                            | `docs/runbooks/nas-to-vps.md` fehlt noch → schreiben (Traefik Path A **statt** Nginx)                                                                                                                                    |
| #462  | Hosted Impressum/Datenschutz               | Inhalt ist generischer Selfhost-Platzhalter ([de.json:1567](../../apps/web/src/lib/i18n/locales/de.json)). Für öffentliches `correlcore.com` echte Betreiberangaben (Name/Anschrift/Kontakt, §5 TMG/ECG) → siehe Phase 2 |

**Ergebnis Phase 0:** #460, #459 schließbar; #461/#462/#464 als klar umrissene
Restarbeit sichtbar; Doku widerspricht der Realität nicht mehr.

---

## Phase 1 — Definitionen & Entscheidungen (Produkt, wenig/kein Code)

Das ist der **Kern dieses Branches**. Nichts in Phase 3/4/5 kann sauber gebaut
werden, bevor diese Begriffe entschieden sind. Vorschläge unten sind **zu
bestätigen**, nicht gesetzt.

### 1.1 Kanonische Definitionen — Tag / Habit / Symptom (#541) · **FESTGEZURRT**

Wortlaut (entschieden 2026-07-26, E1). Non-medical, kein Gamification-Ton. Diese
Fassung ist für Onboarding-Karte (kurz) und In-App-Info-Sheet (mit Analytik-Zusatz)
verbindlich.

| Begriff     | DE                                                                                                                                                                                        | EN                                                                                 | Analytik-Semantik                                                 | ADR                |
| ----------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------- | ----------------------------------------------------------------- | ------------------ |
| **Tag**     | „Ein Kontext-Etikett für einen Tag — z. B. Spaziergang, Alkohol, Meeting. Kein Ziel, kein Zeitplan. CorrelCore sucht, was gemeinsam auftritt und wie es mit deinen Werten zusammenhängt." | „A context label for a day — e.g. Walk, Alcohol, Meeting. No target, no schedule." | Ko-Vorkommen + Assoziation mit deinen Metriken                    | ADR-0030           |
| **Habit**   | „Ein Verhalten, das du aufbauen oder reduzieren willst — mit einer Zielhäufigkeit. CorrelCore zeigt deine Dranbleib-Quote über Zeit und wie sie mit deinen Werten zusammenhängt."         | „A behavior you want to build or reduce — with a target frequency."                | Adhärenz über Zeit + Wirkung auf Metriken; build-vs-reduce (#490) | ADR-0012           |
| **Symptom** | „Etwas, das du körperlich oder mental erlebst — z. B. Kopfschmerz, Grübeln. CorrelCore sucht Zusammenhänge mit Stimmung und Energie."                                                     | „Something you experience physically or mentally — e.g. headache, rumination."     | Assoziation mit Stimmung/Energie                                  | ADR-0008, ADR-0025 |

**Entschieden:**

- **E1** — Wortlaut oben übernommen. ✅
- **E2** — Erklärung sitzt **vor** dem Tag-Schritt als kurze Karte; Deep-Dive
  jederzeit per „?"-Info-Sheet in-app. ✅
- **E3** — Zusätzlich zum Erklären wird ein **UX-Relabeling geprüft**, um die
  Begriffs-Überlappung zu reduzieren (eigener Scope in Phase 3, siehe O5). ✅

### 1.2 Symptom-Intensität — implementieren oder deaktivieren (#544) · **FESTGEZURRT**

`intensity` (0–3) wird auf Entries gespeichert, aber von der Analytik ignoriert
(ADR-0025: Future Work). Sichtbares, wirkungsloses Control wirkt kaputt.

**E4 — entschieden:** Control **sichtbar deaktivieren** (ausgrauen + Hinweis „noch
nicht verfügbar"), kein stiller No-op. Volle Intensitäts-Analytik bleibt Future
Work. Umsetzung in Phase 4. ✅

### 1.3 Zyklus — aktuelle Form erklären **und** Ausbaustufe definieren

**Ist-Zustand (real geshippt):**

- Nur `cycle_day` (Integer 1–35) pro Entry ([entry.py:134](../../backend/app/models/entry.py), Migration 013).
- Im EntryForm als manuelles Zahlenfeld; als **Metrik** behandelt
  ([metrics.ts:44](../../apps/web/src/lib/config/metrics.ts)) → fließt wie andere
  Metriken in Korrelationen.
- CYCLE-**Tag-Kategorie** (cycle/period/pms) aus den Onboarding-Vorschlägen.
- **Nicht** vorhanden: der in **ADR-0034 spezifizierte Opt-in-Toggle**
  (`cycle_tracking_enabled` existiert nirgends), Blutungsstärke, gemeldete/
  inferierte Phase, Zyklus-Events, Zyklus-Symptom-Taxonomie, CycleSnapshot,
  Phasen-Inferenz, Cross-Domain-Zyklus-Insights, Kalender-Overlay.

→ **Altlast-Befund:** [cycle-tracking.md](../features/cycle-tracking.md) und
ADR-0031/0032/0034 beschreiben deutlich mehr, als gebaut ist. Das muss ehrlich
gemacht werden, bevor wir Usern „Zyklus" erklären.

**Entschieden:**

- **E5 — Erklärung der aktuellen Form (Wortlaut festgezurrt):**
  _DE:_ „Optional: trage deinen Zyklustag (1–35) ein. CorrelCore behandelt ihn wie
  eine Metrik und sucht Zusammenhänge mit Stimmung, Schlaf und mehr. Keine
  Vorhersage, keine medizinische Aussage." · _EN:_ „Optional: log your cycle day
  (1–35). CorrelCore treats it like a metric and looks for links with mood, sleep
  and more. No prediction, no medical advice." Plus Hinweis auf die CYCLE-Tags. ✅
- **E6 — Opt-in-Toggle:** **deferred.** Detailarbeit (Toggle, Schema, UX) auf
  später verschoben (siehe #547). Bis dahin wird die aktuelle Form ehrlich als
  „Metrik" beschrieben; cycle-tracking.md + ADR-0034 werden mit der Ausbaustufe
  (Stage 1) auf den Ist-Stand korrigiert. ✅
- **E7 — Ausbaustufe → eigenes Issue angelegt: [#547](https://github.com/Sturmi77/correlcore/issues/547)**
  („Cycle Tracking v1 — Definition + Umsetzung"). Enthält Ist-Stand +
  Altlast-Befund; Stages als Zielrichtung, Detail-Definition bewusst deferred:
  1. **Stage 1 (klein):** Opt-in-Toggle (ADR-0034) + Blutungsstärke-Enum + Doku-
     Korrektur. Kein Analytik-Ausbau.
  2. **Stage 2:** Zyklus-Symptom-Taxonomie (ADR-0008-Erweiterung) + gemeldete Phase.
  3. **Stage 3:** Phasen-Inferenz (CycleSnapshot) + erste Zyklus×Lifestyle-Insights
     (≥3 Zyklen, ADR-0021-Konfidenz).
     Nicht Teil des Onboarding-Sprints — die Onboarding-Erklärung (E5) referenziert
     nur den Ist-Stand. ✅

**Ergebnis Phase 1:** E1–E7 entschieden; neues Cycle-Issue angelegt; die vier
Begriffe (Tag/Habit/Symptom/Cycle) haben bestätigte Ein-Zeilen-Definitionen.

---

## Phase 2 — Landing-Page-Restarbeit (parallelisierbar, geringes Risiko)

Hängt an **keiner** Entscheidung aus Phase 1 außer der Legal-Content-Frage.

| ID  | Was                                                                                                                                                                   | Issue | Status                                                                                                                                  |
| --- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ----- | --------------------------------------------------------------------------------------------------------------------------------------- |
| L1  | Preview-Diagramme (Insight-Matrix + Tag-Heatmap) nicht mehr geclippt — `preview`-Prop blendet Header/Controls aus, Chart ist der Held; `.landing__shot`-Crop entfernt | #546  | ✅ **erledigt** (dieser PR, E9 = `preview`-Prop)                                                                                        |
| L4  | FAQ unter 480px war ausgeblendet (`display:none`) — jetzt auf Mobil sichtbar                                                                                          | —     | ✅ **erledigt** (dieser PR)                                                                                                             |
| L2  | Kontakt-Domain `.app`→`.com`                                                                                                                                          | #462  | ✅ **erledigt** in Phase 0 (#548)                                                                                                       |
| L3  | Hosted Impressum/Datenschutz: echte Betreiberangaben für `correlcore.com` (Selfhost-Template bleibt generisch)                                                        | #462  | ⏳ **bewusst offen** — braucht E8 (Betreiberidentität). **Blockiert Phase 2 nicht**; kommt als separater PR, sobald die Daten vorliegen |

**Bewusst zurückgestellt (E8):** Das Hosted-Impressum verlangt echte Betreiber­angaben
(Name/Anschrift/Kontakt, §5 TMG/ECG). Solange die Daten nicht vorliegen, bleibt der
generische Selfhost-Platzhalter ([de.json](../../apps/web/src/lib/i18n/locales/de.json),
`impressum.sections.operator`) stehen — er weist Betreiber ausdrücklich an, die Seite
vor dem Go-live zu ersetzen. Der Landing-Preview-Fix (L1) wird davon nicht blockiert.
**E9** ist mit `preview`-Prop umgesetzt.

---

## Phase 3 — Onboarding-Umsetzung (hängt an Phase 1)

Baut auf den bestätigten Definitionen auf. Bestehende Basis bleibt:
`MaturityExpectationSheet` (Phasen-Erwartung) + `InsightJourneyExplainer`.

| ID  | Was                                                                                                                                                 | Abhängig von |
| --- | --------------------------------------------------------------------------------------------------------------------------------------------------- | ------------ |
| O1  | Kurz-Erklärung Tag/Habit/Symptom **vor** dem Tag-Schritt, festgezurrter Wortlaut 1.1 (#541)                                                         | E1, E2       |
| O2  | Zyklus-Erklärung in aktueller Form (E5-Wortlaut) an passender Stelle (Info-Sheet)                                                                   | E5           |
| O3  | In-App-Zugang zu den Definitionen (Info-„?" dort, wo Tags/Habits/Symptome/Zyklus verwaltet werden)                                                  | E1, E5       |
| O4  | i18n DE/EN + UX-Copy-Review (no-gamification)                                                                                                       | O1–O3        |
| O5  | **UX-Relabeling prüfen** (E3): Analyse der Begriffs-Überlappung Tag/Habit/Symptom in der UI, ggf. Benennungs-/Flow-Vorschlag als eigener Folge-Task | E1           |

**Reihenfolge innerhalb Phase 3:** O1 → O2 → O3 → O4; O5 als paralleler
Analyse-Task (Ergebnis kann eigenes Umsetzungs-Issue erzeugen). Platzierungsregel aus der
[Onboarding-Maturity-Karte](../frontend/ONBOARDING_MATURITY_EXPECTATION_CARD.md)
beachten (Erklärung vor der Tag-Auswahl, damit sie die Vokabelwahl informiert).

---

## Phase 4 — Symptom-Intensität auflösen (#544)

Nach E4: entweder inert-Schaltung (klein) oder Analytik-Verdrahtung (groß).
Empfehlung inert → wenige Zeilen Frontend + Hinweis-Copy. Hängt an Phase 1/3.

---

## Phase 5 — Cycle Tracking v1 (neues Issue, eigener Sprint)

Umsetzung der in E7 geschnittenen Stage 1 (Toggle + Blutungsstärke + Doku-
Korrektur). **Bewusst nach** Onboarding/Landing — größerer Umfang, SHD-Sorgfalt
(ADR-0033), nicht nebenbei. Onboarding (O2) erklärt bis dahin nur die aktuelle Form.

---

## Reihenfolge auf einen Blick

```
Phase 0  M10.2-Abschluss dok. + .app→.com + Smoke   → #460, #459 schließen
Phase 1  Definitionen/Entscheide E1–E9 + Cycle-Issue anlegen   ← entsperrt 3+4+5
Phase 2  Landing #546 + Legal/Domain #462            ← parallel zu Phase 1 möglich
Phase 3  Onboarding-Erklärung Tag/Habit/Symptom/Zyklus (#541)  ← braucht Phase 1
Phase 4  Symptom-Intensität #544                      ← braucht E4
Phase 5  Cycle Tracking v1 (neues Issue, Stage 1)     ← eigener Sprint, zuletzt
```

Phase 0 und Phase 2 hängen an nichts Inhaltlichem und können sofort starten.
Phase 1 ist der Flaschenhals für alles Inhaltliche — zuerst entscheiden.

---

## Entscheidungen (Stand 2026-07-26)

| #   | Entscheidung                                       | Status                                                                               |
| --- | -------------------------------------------------- | ------------------------------------------------------------------------------------ |
| E1  | Wortlaute Tag/Habit/Symptom DE/EN                  | ✅ **festgezurrt** — Tabelle 1.1 übernommen                                          |
| E2  | Platzierung der Erklärung im Onboarding            | ✅ **festgezurrt** — vor Tag-Schritt + Info-Sheet                                    |
| E3  | UX-Relabeling gegen Begriffs-Überlappung?          | ✅ **entschieden** — Relabeling **prüfen** (O5)                                      |
| E4  | Symptom-Intensität implementieren vs. deaktivieren | ✅ **festgezurrt** — sichtbar deaktivieren                                           |
| E5  | Wortlaut Zyklus-Erklärung (aktuelle Form)          | ✅ **festgezurrt** — E5-Wortlaut in 1.3                                              |
| E6  | Opt-in-Toggle bauen oder zurückstufen              | ✅ **deferred** — Detail auf #547 verschoben                                         |
| E7  | Cycle-Ausbaustufe + neues Issue                    | ✅ **erledigt** — [#547](https://github.com/Sturmi77/correlcore/issues/547) angelegt |
| E8  | Betreiberidentität fürs Hosted-Impressum           | ⏳ **offen** — braucht Maintainer-Angabe                                             |
| E9  | Landing-Preview-Ansatz (preview-Prop vs. Crop)     | ✅ **umgesetzt** — `preview`-Prop (Phase 2, #546)                                    |

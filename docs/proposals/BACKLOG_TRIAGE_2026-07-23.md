# Backlog-Triage & Plan — 2026-07-23

Stand: 23 offene Issues, 0 offene PRs. Quelle: `gh issue list` + Abgleich gegen
`origin/main` (HEAD `e6c5bb0`).

---

## 1. Befunde

### B1 — Triage-Hygiene fehlt vollständig

Alle 23 offenen Issues haben **kein Label und keinen Milestone**, obwohl das Repo
eine ausgebaute Taxonomie besitzt (`must`/`should`/`could`/`wont`,
`backend`/`frontend`/`infra`/`security`/`privacy`, `milestone:M*`).

Milestone **M10** (#7) ist leer (0 offen / 0 geschlossen), **M10.2** existiert
nicht — obwohl #459 genau das als offenen Maintainer-Schritt führt.

Folge: keine Filterbarkeit, keine belastbare „was ist als Nächstes dran"-Sicht.
Das ist der billigste Hebel im ganzen Backlog.

### B2 — Vier Entscheidungen blockieren 9 Issues

Kein Code, nur Produkt-/Ops-Entscheide — aber sie halten den größten Block auf:

| Entscheidung                          | Blockiert                      | Fundstelle                                   |
| ------------------------------------- | ------------------------------ | -------------------------------------------- |
| Hosted-Topologie **A / B / H**        | #460, #461, #462, #463, #464   | `M10_2_..._STATUS.md` → „Pending maintainer" |
| Android-Keystore + Play-Setup (#429)  | #463                           | #429 Checkliste A                            |
| Digest-Opt-in-Policy (#449)           | #449 selbst (Migration wartet) | #449                                         |
| Z-Score-Aggregation für Strips (#482) | #482 selbst                    | #482                                         |

### B3 — #472 ist fertig, nur nicht geschlossen

CAZ-0 bis CAZ-3 sind gemergt (#479, #480, #481, #483). Die QA-Checkliste sagt
explizit: _„Device rows need a physical or emulator pass before closing #472."_
Automatisierte Abdeckung ist laut Checkliste vollständig grün. Es fehlt **ein
manueller Gerätedurchlauf**, danach schließbar.

### B4 — #450 ist real und noch offen

Verifiziert an `scripts/github-release-android-downloads.sh`: das Skript liest
nur den Release-Body (`gh release view --json body`) und prüft **nie**, ob das
APK-Asset existiert. Jeder `v*`-Tag ohne erfolgreichen Signing-Job erzeugt also
weiterhin einen 404-Link. Relevant, sobald Tester über die Landing-CTA (#463)
kommen.

### B5 — M10.2 ist „Repo done", die Lücke ist reine Ops

Laut Statusdoc sind Sprint 1 (Nginx) und Sprint 2 (SMTP) im Repo erledigt,
Runbooks liegen unter `docs/runbooks/`. Was fehlt, ist DNS/TLS/SMTP-Ausführung
auf der NAS — kein Engineering-Aufwand, sondern ein Wartungsfenster.

---

## 2. Kategorisierung der 23 Issues

| Gruppe              | Issues                       | Art                                    |
| ------------------- | ---------------------------- | -------------------------------------- |
| Tracking / Meta     | #452, #459                   | Sammelklammern, nicht selbst umsetzbar |
| Entscheidungen      | #429, #449, #482 + Topologie | Blocker ohne Code                      |
| M11 Polish Sprint B | #445, #446, #447, #448       | Widget-/Mobile-UX + a11y               |
| M11 Polish Sprint C | #450, #451                   | CI/Release-Korrektheit                 |
| M10.2 Hosted Launch | #460, #461, #462, #463, #464 | Ops-Sequenz                            |
| Auth                | #453                         | Großes Feature, Plan liegt vor         |
| Trends / Compare    | #472, #482                   | #472 abschlussreif                     |
| Feature-Backlog     | #487, #488, #489, #490       | Neu, ungeschätzt                       |
| Ops-Härtung         | #491                         | Selfhost-Verfügbarkeit                 |

---

## 3. Plan

### Welle 0 — Triage-Hygiene (~30 min, keine Code-Änderung)

1. Labels auf alle 23 Issues (Vorschlag je Issue in Abschnitt 4).
2. Milestone **M10.2 — Public Hosted Launch** anlegen, #459–#464 zuordnen.
3. Milestone **M11 — Android / Polish** anlegen, #429, #445–#452 zuordnen.
4. Milestone **M10** (#7) schließen — er ist leer und verwirrt (Schritt aus #459).
5. Neuen Milestone **Backlog** für #487–#491 anlegen oder bewusst milestone-los
   lassen und nur `could` labeln.

Danach ist der Backlog erstmals filterbar. **Zuerst machen** — alles Weitere
wird dadurch billiger.

### Welle 1 — Entscheidungen treffen (Maintainer, kein Code)

Diese vier Entscheidungen in einer Sitzung, sie entsperren 9 Issues:

- **Topologie A/B/H.** Statusdoc empfiehlt **H** (`app.correlcore.com`), wenn
  IONOS-Marketing auf der Apex bleibt. Entscheidung als Kommentar in #459
  festhalten.
- **#449 Digest-Backfill.** Drei Optionen stehen ausformuliert im Issue. Wenn
  „opt-in" die Policy ist, ist Option 1 (Backfill) die konsistente Wahl.
- **#482 Z-Score-Policy.** Nur relevant, wenn Strips überhaupt Zoom bekommen
  sollen — sonst als `wontfix` schließen und das Strip-Gate als Endzustand
  dokumentieren.
- **#429 Keystore.** Rein operativ (Keytool, Secrets, Backup). Blockiert #463.

### Welle 2 — Kleine Korrektheits-Fixes (~1 Tag, sofort machbar)

Unabhängig von allen Entscheidungen, geringes Risiko:

| Issue                                   | Aufwand | Warum jetzt                                         |
| --------------------------------------- | ------- | --------------------------------------------------- |
| #450 APK-Link nur bei vorhandenem Asset | klein   | Verifizierter Bug, wird bei Tester-Rollout sichtbar |
| #451 Tag-Checkout bei `attach_to_tag`   | klein   | Falsche Binaries auf altem Tag = schwer zu bemerken |
| #448 Brand-Link aus `<nav>`             | klein   | a11y + entschärft E2E-Contract                      |

### Welle 3 — #472 abschließen

Manuellen Geräte-Durchlauf nach `docs/quality/COMPARE_AXIS_ZOOM_CAZ3_QA.md`
fahren, Ergebnis im Issue dokumentieren, #472 schließen. Danach #482 gemäß
Welle-1-Entscheid schließen oder umsetzen.

### Welle 4 — Widget-UX (Sprint B, ~3–5 Tage)

Reihenfolge laut #452 und nach Nutzerschmerz:

1. **#445** Timezone — funktionaler Fehler, Widget zeigt falsche Daten.
2. **#447** Deep-Link — dokumentiertes Verhalten stimmt nicht mit Runtime überein.
3. **#446** Polling-Gating — Batterie/Netz, kein Fehlverhalten.

#448 ist bereits in Welle 2 abgeräumt, damit ist Sprint B danach komplett und
#452 zur Hälfte schließbar.

### Welle 5 — Hosted Launch ausführen (Ops-Fenster)

Strikt sequenziell, gated auf die Topologie-Entscheidung:

`#460 DNS/Nginx` → `#461 SMTP + Mailpit raus` → `#462 Landing/Legal` →
`#463 APK-CTA` (braucht #429 **und** #450) → `#464 Closeout-Runbook`

Danach #459 schließen.

### Welle 6 — Große Features

- **#453 Persistent Session** — WP0–WP3 sind im Plan geschnitten
  (`docs/features/PERSISTENT_SESSION_PLAN.md`). Größter Nutzerwert im Backlog:
  Capacitor erzwingt aktuell bei jedem Kaltstart einen Login. Als eigener Sprint
  fahren, nicht nebenbei.
- **#487–#490** — vier Feature-Drafts ohne Schätzung. Vorschlag: erst nach #453
  bewerten, dann höchstens **eins** pro Sprint ziehen. #487 (Weekday Top-Signal)
  ist das kleinste und am klarsten geschnittene, #488 (Lag-Visualisierung) das
  aufwendigste (Engine muss `r[lag]`-Serie liefern).

### Welle 7 — #491 Container-Autostart + Alerts

Kein Nutzer-Feature, aber Selfhost-Verfügbarkeit. Sinnvoll **nach** dem Hosted
Launch, weil der Launch die reale Betriebslast erst erzeugt. ADR-0007 gibt den
schlanken Pfad vor (Uptime Kuma statt Prometheus).

---

## 4. Label-Vorschlag je Issue

| Issue | Labels                                                   |
| ----- | -------------------------------------------------------- |
| #429  | `infra`, `must`, `milestone:M10`                         |
| #445  | `bug`, `frontend`, `should`                              |
| #446  | `enhancement`, `frontend`, `could`                       |
| #447  | `bug`, `frontend`, `should`                              |
| #448  | `bug`, `frontend`, `should`                              |
| #449  | `question`, `backend`, `privacy`, `should`               |
| #450  | `bug`, `infra`, `must`                                   |
| #451  | `bug`, `infra`, `should`                                 |
| #452  | `documentation`, `could`                                 |
| #453  | `enhancement`, `frontend`, `backend`, `security`, `must` |
| #459  | `documentation`, `should`                                |
| #460  | `infra`, `must`                                          |
| #461  | `infra`, `must`                                          |
| #462  | `documentation`, `infra`, `should`                       |
| #463  | `enhancement`, `frontend`, `should`                      |
| #464  | `documentation`, `infra`, `should`                       |
| #472  | `enhancement`, `frontend`, `should`                      |
| #482  | `question`, `frontend`, `could`                          |
| #487  | `enhancement`, `frontend`, `backend`, `could`            |
| #488  | `enhancement`, `frontend`, `could`                       |
| #489  | `enhancement`, `frontend`, `could`                       |
| #490  | `enhancement`, `frontend`, `could`                       |
| #491  | `enhancement`, `infra`, `should`                         |

---

## 5. Reihenfolge auf einen Blick

```
Welle 0  Triage-Hygiene            ← sofort, entsperrt die Sicht
Welle 1  4 Entscheidungen          ← Maintainer, entsperrt 9 Issues
Welle 2  #450 #451 #448            ← parallel möglich, kein Blocker
Welle 3  #472 Device-QA → close
Welle 4  #445 #447 #446            ← Sprint B fertig
Welle 5  #460→#461→#462→#463→#464  ← braucht Welle 1 + #429 + #450
Welle 6  #453, dann 1× aus #487–#490
Welle 7  #491
```

Welle 2 und 3 hängen an nichts und können sofort starten, auch wenn Welle 1
noch offen ist.

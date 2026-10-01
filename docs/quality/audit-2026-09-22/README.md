# Audit-Behebung nach v1.9.1

[Vollständiger Maßnahmenplan](REMEDIATION_PLAN.md) · [Tracking #975](https://github.com/Sturmi77/correlcore/issues/975) · [PR #987](https://github.com/Sturmi77/correlcore/pull/987)

| Paket | GitHub-Issue                                                                                                             |
| ----- | ------------------------------------------------------------------------------------------------------------------------ |
| A00   | [#976 — Ausgangsstand und vollständiges Befundregister](https://github.com/Sturmi77/correlcore/issues/976)               |
| A01   | [#977 — Sicheres Release-Upgrade und Marker-Backfill](https://github.com/Sturmi77/correlcore/issues/977)                 |
| A02   | [#988 — Begrenzte Analytics-Ausführung](https://github.com/Sturmi77/correlcore/issues/988)                               |
| A03   | [#978 — Layout-Einstellungen und persistierte Ausblendungen erhalten](https://github.com/Sturmi77/correlcore/issues/978) |
| A04   | [#979 — Fachliche Datenverträge und Stress-/Belastungssemantik](https://github.com/Sturmi77/correlcore/issues/979)       |
| A05   | [#989 — Einheitliche und sichere Berichtsexporte](https://github.com/Sturmi77/correlcore/issues/989)                     |
| A06   | [#980 — Evidenzdarstellung F1/F2/F4 vervollständigen](https://github.com/Sturmi77/correlcore/issues/980)                 |
| A07   | [#981 — Exakte Analysefenster, Request-State und Leerzustände](https://github.com/Sturmi77/correlcore/issues/981)        |
| A08   | [#982 — Compare-/ESM-Handoffs und Detailnavigation](https://github.com/Sturmi77/correlcore/issues/982)                   |
| A09   | [#983 — Timezone-Robustheit und Übersetzungsqualität](https://github.com/Sturmi77/correlcore/issues/983)                 |
| A10   | [#984 — CI-, Integrations- und Security-Freigabenachweise](https://github.com/Sturmi77/correlcore/issues/984)            |
| A11   | [#985 — Review- und Dokumentationsabschluss](https://github.com/Sturmi77/correlcore/issues/985)                          |
| A12   | [#986 — Geräte-, Betriebs- und Nutzerabnahmen](https://github.com/Sturmi77/correlcore/issues/986)                        |

Alle Arbeitspakete besitzen konkrete Maßnahmen, Regressionstests und Abschlusskriterien. Bestehende externe Aufgaben bleiben verknüpft. Dieser Dokumentationsstand behebt selbst keine Produktfehler.

## A00-Nachweise

[Ausgangsstand und Status](A00_STATUS.md) · [Status 01.10.2026](STATUS_2026-10-01.md) · [Kandidat v1.9.2-rc.1](A10_CANDIDATE_v1.9.2-rc.1.md) · [Desktop-Retest 30.09.2026](QA_RETEST_2026-09-30.md) · [Befundregister](A00_BEFUNDREGISTER.csv) · [Reviewregister](A00_REVIEWREGISTER.csv) · [lokale Fix-Kandidaten](A00_LOKALE_FIXES.csv)

## A12-Nachweise

[Status](A12_STATUS.md) · [Abnahmelaufplan](A12_ACCEPTANCE_RUNBOOK.md) · [maschinenlesbares Gate-Register](A12_ACCEPTANCE_REGISTER.json) · [Evidenzformat](a12-evidence/README.md)
Für A01 beschreibt [der Upgrade- und Wiederanlaufplan](A01_UPGRADE.md) die
Migration aus 046–048 und die erforderliche Backup-/Restore-Probe.

## A11-Nachweise

[Review- und Dokumentationsabschluss](A11_REVIEW_CLOSEOUT.md) · [verlustfreies Abschlussregister](A11_REVIEW_CLOSEOUT.csv)

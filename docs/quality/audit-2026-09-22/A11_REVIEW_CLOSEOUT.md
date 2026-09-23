# A11 – Review- und Dokumentationsabschluss

Stand: 23.09.2026. Audit-Basis: `71d1089ff77388cadf2253ac67d1471dfa99fa40`.

## Geltungsbereich und Status

Dieses Dokument schließt die **Zuordnung** aller im A00-Snapshot erfassten Review-Zeilen
ab. Es erteilt keine Release-Freigabe. Produktfixes, finale CI-/Security-Nachweise und
externe Abnahmen bleiben in ihren Arbeitspaketen offen, bis sie am tatsächlich zu
mergenden Release-SHA belegt sind.

Das verlustfreie [A11-Abschlussregister](A11_REVIEW_CLOSEOUT.csv) basiert auf
`A00_REVIEWREGISTER.csv` aus Commit
[`026a4dff`](https://github.com/Sturmi77/correlcore/commit/026a4dff41f58fb5577726ce21745acf67843620)
und enthält alle **524** Zeilen weiter mit Original-URL, Art, Pfad, Threadzustand,
Audit-Zuordnung und Kurztext. Die ergänzten Felder `abschlussgruppe`,
`abschlussstatus` und `abschlussnachweis` machen die endgültige A11-Behandlung
maschinenlesbar. `isResolved` bezeichnet weiterhin nur den GitHub-Threadzustand.

## Vollständigkeitsbilanz

| Gruppe        |  Zeilen |  Inline | Review/Antwort | Behandlung                                                                                                                 |
| ------------- | ------: | ------: | -------------: | -------------------------------------------------------------------------------------------------------------------------- |
| PRs #888–#963 |     460 |     266 |            194 | Historischer Review-Kontext; jede Zeile ist auf ihren A00-Matrixpunkt und damit auf das zuständige Audit-Paket übertragen. |
| PRs #968–#974 |      64 |      32 |             32 | Aktuelle Review-Runde; Inline-Findings sind unten einem Fix/Test oder einem offenen Audit-/Abnahme-Gate zugeordnet.        |
| **Gesamt**    | **524** | **298** |        **226** | Keine Zeile wurde durch Gruppierung entfernt.                                                                              |

Die 226 Einträge der Art `Review/Antwort` sind Bot-Zusammenfassungen, Risikoberichte
oder Antworten ohne eigenen Inline-Thread. Sie bleiben einzeln im CSV erhalten und
werden pro Quell-PR als `review-summary` gebündelt. Die technischen Inline-Findings
sind separat dispositioniert. Frühere `unresolved`-Flags werden deshalb nicht als
neue, unabhängige A11-Befunde gezählt: Der jeweilige Inhalt ist über `auditZuordnung`
in die aktuelle 40-Punkte-Matrix übertragen und bleibt dort bis zur Paketabnahme offen.

## Review-Runde #968–#974

| Quell-PR                                                | Zeilen | Endgültige Zuordnung                  | Nachweis / verbleibendes Gate                                                                                                                                                                            |
| ------------------------------------------------------- | -----: | ------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| [#968](https://github.com/Sturmi77/correlcore/pull/968) |      3 | A03                                   | Dismissal- und Layoutmigration: [#978](https://github.com/Sturmi77/correlcore/issues/978), Implementierung [PR #992](https://github.com/Sturmi77/correlcore/pull/992).                                   |
| [#969](https://github.com/Sturmi77/correlcore/pull/969) |      6 | A05                                   | Einheitlicher Reportvertrag, sichere Auswahl und CSV-Empfängernachweis: [#989](https://github.com/Sturmi77/correlcore/issues/989). Kein Abschluss behauptet.                                             |
| [#970](https://github.com/Sturmi77/correlcore/pull/970) |      5 | A07                                   | Fenster-/Leerzustandskorrekturen: [#981](https://github.com/Sturmi77/correlcore/issues/981), Implementierung [PR #995](https://github.com/Sturmi77/correlcore/pull/995).                                 |
| [#971](https://github.com/Sturmi77/correlcore/pull/971) |      8 | A06/A08                               | Evidenzdarstellung [PR #994](https://github.com/Sturmi77/correlcore/pull/994) und Handoffs [PR #996](https://github.com/Sturmi77/correlcore/pull/996); finaler Journey-Nachweis bleibt Teil von A10/A12. |
| [#972](https://github.com/Sturmi77/correlcore/pull/972) |     11 | Regression erhalten                   | Alle vier Inline-Threads sind auf GitHub gelöst. Rohminuten >12 h und die Deckkraftlegende sind durch die unten genannten Tests verankert.                                                               |
| [#973](https://github.com/Sturmi77/correlcore/pull/973) |     23 | Regression erhalten, A05 bleibt offen | Alle acht Inline-Threads sind gelöst. Auswahl-, PDF-, Winner-, Fetch-Cap- und Query-Verträge sind durch die unten genannten Tests verankert. A05 erweitert diese Basis.                                  |
| [#974](https://github.com/Sturmi77/correlcore/pull/974) |      8 | A03/A06/A11/A12                       | Technische Fixes: PRs #992/#994. Dokumentstatus: dieser A11-Stand. Interview- und externe Abnahmen: [#986](https://github.com/Sturmi77/correlcore/issues/986).                                           |

## Erhaltene Regressionen aus #972/#973

| Vertrag                                                                                                     | Automatisierter Nachweis auf `main`                                                                                                                                              |
| ----------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Schlaf bleibt als Rohminuten erhalten; 13 h und 16 h kollabieren nicht auf denselben Chartwert              | `apps/web/src/lib/components/trends/UnifiedStripChart.test.ts` – „keeps nights longer than 12 h distinct…“; `EventAlignedSmallMultiplesSheet.test.ts` – gleichnamiger Test       |
| Mehrseitiges PDF behält alle Zeilen, Seitenobjekte, Grenzen und Byte-Offets; WinAnsi/CP1252 wird deklariert | `apps/web/src/lib/utils/insightMatrixExport.test.ts` – Blöcke „pagination (#959)“ und „character set (#960)“                                                                     |
| Bewusst leere Auswahl bleibt bei Refresh/Reload leer                                                        | `apps/web/src/routes/insights/report/page.test.ts` – „does not refill an emptied selection…“, „does not re-seed…“, „keeps a deliberately emptied selection empty…“               |
| Auswahl und letzte geladene Zeilen bleiben bei Refresh-Fehler erhalten                                      | `apps/web/src/routes/insights/report/page.test.ts` – „keeps an untouched selection…“ und „still exports the last loaded rows…“                                                   |
| Neueres `null_association` gewinnt vor älterem positiven Befund                                             | `backend/tests/test_insights.py::test_list_latest_insights_lets_a_null_association_retire_its_subject`                                                                           |
| Familienfilter greift vor beiden Fetch-Caps                                                                 | `backend/tests/test_insights.py::test_list_latest_insights_filters_families_before_the_row_cap` und `::test_newest_insight_per_subject_stmt_filters_families_before_its_own_cap` |
| `/insights` und `/insights/latest` besitzen getrennte Query-Verträge                                        | `apps/web/src/lib/api/insights.test.ts` – Latest-Familienparameter und History-Request; `LatestInsightListQuery` ist nur am Latest-Endpoint verwendbar                           |

Diese Tests schützen die bereits reparierten Fälle. Sie ersetzen die weitergehenden
A05-Anforderungen an identische Daten in allen vier Exportformaten, CSV-Formelschutz
und reale Empfänger-/Rendering-Prüfungen nicht.

## Dokumentations- und Issue-Status

- Der Rolloutplan steht bis zur echten Abnahme auf „Implementierung in
  Audit-Nacharbeit, Abnahme offen“. Seine frühere Fertigmeldung ist als historischer
  Vermerk gekennzeichnet.
- ADR-0043 bleibt als Architekturentscheidung akzeptiert; die Konsequenzen nennen den
  heutigen Implementierungsstand und die offenen A05/A06/A10/A12-Gates.
- DESIGN_DOCUMENT §2.10 unterscheidet Berichtsexporte vom vollständigen
  DSGVO-Datenexport und nennt den offenen A05-Nachweis. Die frühere M13-Medienplanung
  ist historisch; [#715](https://github.com/Sturmi77/correlcore/issues/715) priorisiert
  strukturierte Ernährung für den Korrelationspfad.
- `SECURITY.md` weist `1.9.x` als unterstützte Release-Linie aus.
- #928, #930 und #931 waren durch PR #974 zu früh geschlossen. Sie wurden am
  23.09.2026 wieder geöffnet und jeweils mit ihren konkreten A03/A05/A06/A10/A12-Gates
  verknüpft. #776 blieb offen und verweist nun ebenfalls sichtbar auf A10/A12.

## Abschlussregel

A11 selbst bleibt bis zur finalen Review-Runde auf dem exakten Merge-SHA offen. Ein PR
zu diesem Stand verwendet daher `Relates to #985` und keine Closing-Keywords. Der
Gesamtrollout darf erst abgeschlossen werden, wenn A00–A12 ihre jeweiligen Nachweise
besitzen und A12s externe Sign-offs vorliegen.

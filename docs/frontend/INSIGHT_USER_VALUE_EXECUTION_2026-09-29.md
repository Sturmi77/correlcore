# Arbeitsplan und Merge-Strategie: persönliche Insights

Stand: 29.09.2026, PR-Abfrage etwa 16:10–16:16 UTC. Status: **Plan, keine Merge- oder Release-Freigabe**.

[Zielbild](INSIGHT_USER_VALUE_TARGET_2026-09-29.md) · [Findings](INSIGHT_USER_VALUE_FINDINGS_2026-09-29.md)

## 1. Entscheidung zur Reihenfolge

**Die fachlichen Basis-PRs sollen vor der neuen Produktimplementierung konsolidiert werden. Planung, Fähigkeitsinventar, Copy und Prototypen können jetzt beginnen. Nicht alle offenen PRs sind Voraussetzung.**

Dabei drei Schritte auseinanderhalten:

1. **Integration:** ausgewählte Fixes auf einen gemeinsamen isolierten Stand bringen und Überschneidungen prüfen.
2. **Main-Merge:** geprüfte Änderungen nach den Repository-Regeln übernehmen; nach jedem Merge den verbleibenden Stand neu bewerten.
3. **Release/Deployment:** die gemeinsame Version anhand unveränderlicher SHAs und Image-Digests abnehmen und bewusst ausrollen.

Im aktuellen Repository löst ein Push auf Main bereits die Containerveröffentlichung mit `latest`, `main` und SHA-Tags aus. Eine versionierte GitHub-Release-Veröffentlichung wird separat über `v*` ausgelöst. Das Auslassen eines Versions-Tags verhindert daher nicht die Containerveröffentlichung. Ob ein Betreiber `latest` automatisch übernimmt, ist noch nicht festgestellt.

**Empfohlener Pfad:** Basis-PRs zunächst auf einem Integrationsbranch kombinieren; einen isolierten Kandidaten bauen und die Kernwege prüfen. Vor Main-Merges festhalten, welche Deployments mutable Tags verwenden und wie unbeabsichtigte Zwischenstände vermieden werden. Falls Main absichtlich ein laufender Veröffentlichungskanal bleibt, muss jede Zwischenstufe eigenständig tragfähig und deren Übernahme bewusst sein. Keine automatische Umstellung von Betreiberkonfigurationen im Rahmen dieses Dokumentationsauftrags.

## 2. Aktueller PR-Snapshot

Quelle: `gh pr list --state open --limit 100 --json number,title,isDraft,mergeStateStatus,reviewDecision,headRefOid,statusCheckRollup`. Alle 17 gemeldeten PRs waren `CLEAN`, keine Drafts. Kein gemeldeter Check war laufend oder fehlgeschlagen; `NEUTRAL` und `SKIPPED` werden dabei nicht als erfolgreich ausgeführte Tests gezählt. Welche Statuschecks durch Branch Protection verpflichtend sind und ob alle Review-Threads erledigt sind, wurde hier nicht vollständig geprüft.

Ein leeres Review-Entscheidungsfeld ist kein Beleg für eine Freigabe. Einzelne PR-Beschreibungen sprechen noch von Draft; für den aktuellen Draft-Status gilt die abgefragte Metadatenlage. Bei jeder Änderung an Head oder Base ist dieser Snapshot neu zu bewerten.

| PR                                                        | Head (gekürzt) | Gemeldete Checks | Review-Entscheidung | Rolle                           |
| --------------------------------------------------------- | -------------- | ---------------: | ------------------- | ------------------------------- |
| [#990](https://github.com/Sturmi77/correlcore/pull/990)   | `026a4dff`     |               17 | nicht gesetzt       | Ausgangsregister                |
| [#991](https://github.com/Sturmi77/correlcore/pull/991)   | `b5ae88d7`     |               28 | nicht gesetzt       | Migration                       |
| [#992](https://github.com/Sturmi77/correlcore/pull/992)   | `fd1bd06f`     |               28 | nicht gesetzt       | Layout/Ausblendungen            |
| [#993](https://github.com/Sturmi77/correlcore/pull/993)   | `1b876c2d`     |               28 | nicht gesetzt       | Evidenzverträge                 |
| [#994](https://github.com/Sturmi77/correlcore/pull/994)   | `96022dd3`     |               28 | nicht gesetzt       | Evidenzdarstellung              |
| [#995](https://github.com/Sturmi77/correlcore/pull/995)   | `75285f5a`     |               28 | nicht gesetzt       | Zeitfenster                     |
| [#996](https://github.com/Sturmi77/correlcore/pull/996)   | `7b4a1abb`     |               28 | nicht gesetzt       | Paarübergaben                   |
| [#997](https://github.com/Sturmi77/correlcore/pull/997)   | `03965285`     |               28 | APPROVED            | Zeitzonen/Locales               |
| [#998](https://github.com/Sturmi77/correlcore/pull/998)   | `512332bc`     |               17 | APPROVED            | Review-/Dokuabschluss           |
| [#999](https://github.com/Sturmi77/correlcore/pull/999)   | `c99ef487`     |               28 | APPROVED            | Externe Abnahmeregister         |
| [#1000](https://github.com/Sturmi77/correlcore/pull/1000) | `bc95f82b`     |               28 | nicht gesetzt       | Analysebudget/Laufzeit          |
| [#1001](https://github.com/Sturmi77/correlcore/pull/1001) | `45ec1976`     |               28 | nicht gesetzt       | Berichte/Export                 |
| [#1002](https://github.com/Sturmi77/correlcore/pull/1002) | `0b31ece6`     |               29 | nicht gesetzt       | Release-Evidenz-Gates           |
| [#1008](https://github.com/Sturmi77/correlcore/pull/1008) | `ddffda8c`     |               24 | nicht gesetzt       | Sentry-11-Major, separat prüfen |
| [#1009](https://github.com/Sturmi77/correlcore/pull/1009) | `bb98f2d0`     |               21 | APPROVED            | Parser-Patch, unabhängig        |
| [#1012](https://github.com/Sturmi77/correlcore/pull/1012) | `749d2dba`     |               20 | APPROVED            | Nullable Schlafqualität         |
| [#1013](https://github.com/Sturmi77/correlcore/pull/1013) | `574c443b`     |               29 | nicht gesetzt       | Web-Healthcheck                 |

Dokumentationsbranch basiert auf Main `7e59ba5a1c9b46c89511d6c706a30cf61809122f`. Dieser Main enthält bereits weitere Dependency-Merges; Ergebnisse älterer PR-Läufe sind daher kein gemeinsamer Nachweis auf dieser Basis.

## 3. Empfohlene Integrationswellen

Die Reihenfolge ordnet Risiko und fachliche Verantwortung. Sie behauptet keine vollständige Git-Abhängigkeitsanalyse; konkrete Konflikte und neue Review-Findings werden beim Zusammenführen aufgelöst.

| Welle                        | PRs / Arbeit                                              | Warum jetzt?                                                                           | Ende der Welle                                                                                   |
| ---------------------------- | --------------------------------------------------------- | -------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------ |
| A – Prüfrahmen               | #990, #999, Prüfharness aus #1002                         | Prüfanforderungen und offene externe Gates vor dem Kandidaten sichtbar machen          | Prüfplan, Artefaktidentität, Operator-Aufgaben und Verantwortliche stehen                        |
| B – Daten- und Betriebsbasis | #991, #992, #1012, #1013                                  | Sichere Migration, unverfälschte Eingaben, erhaltene Einstellungen, startfähiger Stack | Upgrade-/Bestandsnutzer-/Nullwert-Regressionen und Healthchecks bestanden                        |
| C – Fachlicher Vertrag       | #993, #995, #1000                                         | Einheitliche Evidenz und Fenster innerhalb begrenzter Berechnung                       | API-Vertrag, Methodenwerte, Fehler-/Limitzustände konsistent                                     |
| D – Nutzerweg                | #994, #996, #997, #1001                                   | Darstellungen und Übergaben auf denselben Vertrag ausrichten                           | Alle fünf Nutzerwege mit echter API und Exportprüfung                                            |
| E – Abschluss                | #998 aktualisieren; #1002/#999-Nachweise vervollständigen | Dokumentation muss den tatsächlich integrierten Kandidaten beschreiben                 | Finale Reviews, CI, Geräte-/Nutzer-/Betriebs-Gates und verbleibende Einschränkungen dokumentiert |

#1008 und #1009 sind keine Voraussetzung für persönliche Fragen. Den Parser-Patch unabhängig nach den üblichen Checks behandeln. Für den Sentry-Major die tatsächlichen Integrationen und Migrationsfolgen separat prüfen; ihn nicht allein wegen der grünen Liste mit dem Produktumbau koppeln. Wenn Dependencies mit in den Kandidaten kommen, müssen die gemeinsamen Nachweise genau diesen Stand abdecken.

### Merge-Checkliste pro Welle

- [ ] Aktuelle Heads, Base, notwendige Reviews, ungelöste Threads und verpflichtende Checks prüfen.
- [ ] Überschneidende Änderungen fachlich zusammenführen; OpenAPI, DE/EN und Migrationen auf denselben Stand bringen.
- [ ] Gezielt betroffene Tests laufen lassen; gemeinsame kritische Wege nach der letzten relevanten Änderung prüfen.
- [ ] Vor Main-Merge Veröffentlichungswirkung und Verbraucher der Image-Tags klären.
- [ ] Änderungen nach Main übernehmen und nachfolgende PRs neu bewerten; keine alte grüne Prüfung als pauschale Freigabe übernehmen.
- [ ] Für den Release einen finalen SHA und Image-Digests fixieren; die Abnahme referenziert genau diese Artefakte.
- [ ] Externe Abnahmen offen lassen, bis sie wirklich vorliegen. Main-Merge allein schließt #984/#986 oder andere externe Gates nicht ab.

Der aktuelle Auftrag veröffentlicht ausschließlich die Planung. Er merged keine dieser Produkt-PRs und löst keinen Release aus.

## 4. Arbeitsplan nach Produktpaketen

Gemeinsame DoD: benannter Nutzerweg, belegte Zustandssemantik, DE/EN, Regressionen und Nachweise am jeweiligen Kandidaten. Ein Ticket ist nicht fertig, wenn nur sein Mock funktioniert. Die Plan-IDs unten sind noch keine GitHub-Issues.

| ID   | Konkretes Ergebnis                                                     | Abhängigkeit                            | Überprüfbare Abnahme                                                                                                  | Rolle                  |
| ---- | ---------------------------------------------------------------------- | --------------------------------------- | --------------------------------------------------------------------------------------------------------------------- | ---------------------- |
| Z0.1 | PR-Inventar und Integrationskandidat nach Wellen A–E                   | Aktuelle Heads                          | Fünf Kernwege; finale SHA-/Image-Zuordnung; offen gebliebene Gates benannt                                            | Entwicklung/QA/Release |
| Z0.2 | Main-/Image-Kanalentscheidung dokumentieren                            | Workflow und Betreiberabgleich          | Keine unbewusste Übernahme ungetesteter Zwischenstände                                                                | Owner/Betrieb          |
| Z1.1 | Fähigkeitsmatrix für Faktor × Ziel × Zeitbezug × Methode               | Z0-Bestand; lesend sofort möglich       | Jede auswählbare Kombination unterstützt, datenarm oder nicht unterstützt klassifiziert; keine erfundenen Methoden    | Analytics/Entwicklung  |
| Z1.2 | Vier fachliche Zustände, Gründe und Datenreife-Abgrenzung definieren   | Z1.1                                    | Testfälle für kleine Gruppen, Nicht-Ergebnis, Unsicherheit, Fehler und historische Payloads                           | Analytics/Produkt      |
| Z1.3 | Vorlagenkatalog und strukturierter Fragebaukasten in DE/EN             | Z1.1–Z1.2                               | Fragen ohne Treffer sowie eigener Tag wählbar; freie Notiz erzeugt keine automatische Analyse                         | Produkt/Design         |
| Z1.4 | Sechs Szenarien prototypisieren, zwei frühe Nutzertests, ADR-Nachtrag  | Z1.2–Z1.3                               | Findings verarbeitet; Kontoreife wird nicht als Bestätigung verstanden                                                | Produkt/Research       |
| Z2.1 | Gemeinsame Antwortprojektion aus Evidenz und begründeten Aktionen      | Z1-Abnahme, #993/#994/#995              | Identische Werte und Aussage über Heute/Karte/Detail; Gründe nur aus berechneten Daten                                | Entwicklung            |
| Z2.2 | Satzhierarchie, progressive Details und Kontextsprache integrieren     | Z2.1                                    | Lange Texte, Stress, Lag, Roh-Keys, DE/EN, Tastatur geprüft                                                           | Frontend/QA            |
| Z2.3 | Verständliche Berichtseinleitung mit gemeinsamer Evidenz               | Z2.1, #1001                             | Frage, Antwort, Zeitraum und Vorbehalt in PDF/PNG; strukturierte Entsprechung in CSV/JSON                             | Frontend/QA            |
| Z3.1 | Mehrere Fragen speichern, eine fokussieren; Lifecycle                  | Z1.1, stabile Paaridentität #996        | Eigener Tag, Umbenennen, Archivieren, Löschen, Konto-/Offline-Wechsel, fehlender Faktor, Datenexport/-löschung        | Backend/Frontend       |
| Z3.2 | Datenstatus ohne Insight und begrenzte Berechnung anbinden             | Z3.1, #1000                             | Gespeicherte Frage ohne Treffer bleibt sichtbar; kein Job-Fan-out pro gespeicherter Frage; Caches konto-/datenbezogen | Backend/Analytics      |
| Z3.3 | Priorisierung, Gruppierung und Erklärung „Warum sehe ich das?“         | Z2.1, Z3.1–Z3.2                         | Aktive Frage inkl. Nicht-Ergebnis zuerst; stabile Gleichstände; automatische Entdeckung ohne Fragewahl                | Entwicklung/Produkt    |
| Z4.1 | Vergleichbare Analysestände und begründete Änderungshinweise           | Z3.3                                    | Zeitstempelwechsel allein erzeugt keine Neuigkeit; Methode/Fenster/Datenbasis werden berücksichtigt                   | Analytics/Entwicklung  |
| Z4.2 | Digest und Bericht auf neue Antworttypen erweitern                     | Z4.1, Z2.3                              | Eine hilfreiche Antwort möglich; kein Muster berichtbar; technische Fehler nicht als Ergebnis exportiert              | Entwicklung/QA         |
| Z5.1 | Gemeinsame Fach-, Browser-, Geräte- und Datei-Abnahme                  | Je Release-Schnitt                      | Fixtures und fünf Nutzerwege aus dem Zielbild bestanden                                                               | QA/Release             |
| Z5.2 | Sechs finale Nutzertests, kritische Befunde korrigieren und nachtesten | Funktionsfähiger Kandidat               | Mindestens 5/6 lösen Aufgaben; 0 ungelöste kritische Missverständnisse                                                | Produkt/Research       |
| Z5.3 | Stufenweise Beta, Rückstellmöglichkeit und breiter Rollout             | Z5.1–Z5.2 plus vorhandene Release-Gates | Neue Priorisierung deaktivierbar ohne Verlust gespeicherter Fragen oder Rücknahme der Evidenzfixes                    | Release/Betrieb        |

## 5. Startpaket und Scope-Grenze

**Jetzt ausführbar:** diesen Plan reviewen, Z1.1–Z1.3 vorbereiten, zwei frühe und sechs finale Testpersonen sowie Gerätezugang organisieren. Voraussetzung dafür ist kein Merge aller offenen PRs.

**Vor neuer Produktimplementierung:** die fachliche Basis konsolidieren und den für das neue Paket benötigten Vertrag abnehmen. Auf einem uneinheitlichen Stapel konkurrierender Insight-/Export-/Fensteränderungen würde dieselbe Arbeit mehrfach erfolgen.

**R1 umfasst:** verständliche Antworten und begründete nächste Schritte, mehrere gespeicherte Fragen mit einem Fokus, unterstützte Fragewahl, stabile persönliche Priorisierung und die relevanten Abnahmen. Die UI verspricht nur die in Z1.1 bestätigten Analysemöglichkeiten. Freie Notizen sind optional; sie werden bei unklarer sicherer Speicherintegration auf einen separaten Folgeschritt verschoben, ohne den strukturierten Fragebaukasten zu blockieren.

**R2 umfasst:** nachvollziehbare Antwortänderungen, Digest-Angleichung und vollständige Mitnahme der neuen Antworttypen.

Ausgenommen: neue beliebige Analyse-Engine, kausale Erklärungen, KI-Chat, Experiment-Coach, weitere Pflichtdaten und zusätzliche Push-Schleifen.

## 6. Aufwand, Entscheidungen und Erfolg

Vorläufige Schätzung aus dem Zielbild: Z0 2–4, Z1 3–5, Z2 4–6, Z3 5–8, Z4 4–7, Z5 3–5 Arbeitstage; insgesamt **21–35 Arbeitstage** für eine repo-erfahrene Person. Die konkretisierte Mehrfragen-Speicherung ist innerhalb Z3 zu schätzen; nach der Fähigkeitsmatrix und dem Prototyp wird die Gesamtschätzung verbindlicher erneuert. Neue Methoden, Konflikte und externe Wartezeiten sind nicht stillschweigend enthalten.

Vor Z2 zu entscheiden: finale unterstützte Fragefamilien, Zustandszuordnung und Wortwahl. Vor Z3: Persistenz-/Datenschutzregeln für Titel/Notizen, Budget für gespeicherte Fragen, Konfliktregel bei Offline-Fokuswechsel. Vor Main-Merges: Kanalwirkung. Vor Release: finale Abnahmematrix und Verantwortliche.

Erfolg wird zunächst in moderierten Sitzungen mit synthetischen Daten gemessen: Antwort in 15 Sekunden finden, Zeitraum und Vorbehalt erklären, passenden nächsten Schritt und Bericht ohne Hilfe erreichen. Mindestens 5 von 6 Personen sollen die jeweiligen Aufgaben schaffen; kein ungelöstes kritisches Missverständnis bleibt. Diese kleine Stichprobe ist eine Produktabnahme, keine repräsentative Wirksamkeitsstudie.

**Abbruch-/Rückstellkriterium:** falsche Kernaussage, unbemerkter Wechsel der Frage oder fremde Berichtsauswahl blockieren den Release. Fehlende Methode führt zu sichtbarer Nicht-Unterstützung statt einer erfundenen Antwort. Offene externe Gates werden nicht durch grüne Einzel-PRs ersetzt.

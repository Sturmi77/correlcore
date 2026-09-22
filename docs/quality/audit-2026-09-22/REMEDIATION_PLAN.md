# Umsetzungsplan: sämtliche Befunde des Release-Audits beheben

Stand: 22.09.2026 · Status: **geplant, noch nicht umgesetzt**  
Referenz: Release-Audit vom 22.09.2026 (vollständige Evidenz lokal beim Maintainer), Audit-Basis `71d1089ff77388cadf2253ac67d1471dfa99fa40`.

## Veröffentlichungsstand

Öffentliche Arbeitsfassung. Security-spezifische Details aus A02/A05 bleiben bis zur ausdrücklichen Freigabe gemäß SECURITY.md lokal. Kein Befund ist dadurch erledigt oder aus dem Umfang entfernt. Tracking: [#975](https://github.com/Sturmi77/correlcore/issues/975).

## Ziel und Abschlussregel

Alle bestätigten Fehler R1–R9 und S1–S2, die Wartbarkeits- und Prozessbefunde sowie die fehlenden Abnahmen erhalten unten eine verantwortliche Rolle, Umsetzung und prüfbare Abschlussbedingung. Die Rollen sind Zuweisungsvorschläge, keine bereits zugesagten Personen.

**Ein Befund gilt erst als behoben, wenn Fix-Commit, geeigneter Regressionstest und erfolgreicher Nachweis auf dem finalen Release-Kandidaten verlinkt sind.** Ein grüner isolierter Komponententest, ein geschlossener Thread oder eine geänderte Dokumentation genügen nicht.

Statische Verdachtsfälle werden zuerst reproduziert. Falls ein Verdacht widerlegt wird, sind Gegenbeleg und geprüfter Commit zu dokumentieren; er darf nicht still verschwinden. Externe Abnahmen bleiben offen, bis reale Evidenz vorliegt.

Dieser Plan autorisiert keine Behauptung einer bereits erfolgten Behebung. Er ändert keinen Produktcode und veröffentlicht keine GitHub-Kommentare.

## Reihenfolge und Aufteilung

| Paket / vorgeschlagener PR | Inhalt | Abhängigkeit | Verantwortliche Rolle |
|---|---|---|---|
| A00 | Ausgangsstand, vorhandene Fixes, Befundregister | zuerst | Release-Verantwortung |
| A01 | Sicheres Upgrade und Backfill | A00 | Backend / Datenbank |
| A02 | Begrenzte Analytics-Ausführung | A00 | Backend |
| A03 | Layout- und Dismissal-Erhalt | A00; Integration nach A01 | Backend + Frontend |
| A04 | Fachliche Datenverträge und Stress-/Belastungssemantik | A00 | Backend + Frontend / Produkt |
| A05 | Einheitlicher, sicherer Berichtsexport | A04 | Frontend |
| A06 | Evidenzdarstellung F1/F2/F4 | A04 | Frontend / Produkt |
| A07 | Exakte Fenster, Request-Races, Leerzustände | A02/A04 für finalen API-Vertrag | Backend + Frontend |
| A08 | Compare-, ESM-, Detail- und Login-Übergaben | A04/A07; Berichtintegration A05 | Frontend |
| A09 | Plattformrobustheit und Übersetzungen | A00; Copy-Abgleich A05/A06 | Backend + Frontend |
| A10 | CI, echte Integration und Security-Verifikation | Infrastruktur früh starten; Abschluss nach A01–A09 | QA / DevOps |
| A11 | Review- und Dokumentationsabschluss | Register ab A00; Abschluss nach A10/A12 | Release-Verantwortung / Produkt |
| A12 | Geräte-, Betriebs- und Nutzerabnahmen | Vorbereitung früh; Ausführung am Kandidaten | QA / Betrieb / Produkt |

Kleine PRs pro Paket; A04 bei Bedarf in Datenvertrag und fachliche Berechnung teilen. A07 und A08 bearbeiten dieselben großen Routen: Änderungen nacheinander integrieren, nicht gleichzeitig dieselben Dateien umbauen. Vorhandene Änderungen aus der Arbeitskopie werden nicht blind überschrieben. Kein Sammel-PR, der alle Tests und Fachentscheidungen zugleich unprüfbar macht.

## A00 — Ausgangsstand und vollständige Nachverfolgung

**Umsetzung**
1. Main, lokalen HEAD und vorhandene Änderungen erfassen. Einen isolierten, benannten Implementierungsstand aus dem gewählten aktuellen Main verwenden. Vorhandene lokale Fixes einzeln zuordnen und mit ihrem Urheber-/Arbeitsstand erhalten.
2. Für jeden Unterpunkt der Abdeckungsmatrix eine Registerzeile anlegen: Befund-ID, Review-URL, Zielverhalten, betroffene Dateien, verantwortliche Rolle, Status, Fix-Commit, Test, CI-/Abnahmenachweis.
3. Die archivierten Review-Kommentare aus `review-evidence.json` mit aktuellen Threads abgleichen. Wenn verfügbar GraphQL-`isResolved` lesen; technische Erledigung separat bewerten.
4. Bereits vorhandene Fixes nicht doppelt implementieren: gegen das Audit-Zielverhalten testen und anschließend als erledigt oder weiterhin offen einstufen.

**Abnahme:** Jeder Audit-Unterpunkt und jeder fachlich relevante Review-Kommentar besitzt eine Zuordnung. Kein bestätigtes Finding ist lediglich „akzeptiertes Risiko“. Widerlegte Verdachtsfälle besitzen konkrete Gegenbeweise.

## A01 — R1: Migration und Datenübernahme

**Betroffene Bereiche:** Alembic-Konfiguration, Revisionen 048/049, Marker-Backfill, Migrations-Integrationstests.

**Umsetzung**
- Den Sperrzyklus mit PostgreSQL 16/pgvector und Ausgangsrevision 046 zuerst reproduzieren; feste Test-Timeouts verhindern hängende CI.
- Bevorzugter Fix: migrationsgeeigneten Backfill über dieselbe DB-Verbindung/Transaktion ausführen. Keine zweite Verbindung, auf deren Abschluss die DDL-Transaktion synchron wartet.
- Backfill von später veränderlichen ORM-Modellen entkoppeln: migrationslokale Tabellen-/Spaltenprojektionen verwenden. Keine Abhängigkeit von Spalten, die erst nach 049 existieren.
- Entschlüsselung, Nutzerzuordnung und Hidden-Note-Regeln explizit erhalten. Daten erst entfernen, wenn alle vorgesehenen Übernahmen erfolgreich und geprüft sind.
- Nicht pauschal globale Autocommit-/Transaktionsregeln ändern, um die Sperre zu verdecken. Falls ein separat committed Backfill unvermeidbar ist, ihn als explizite, wiederanlauffähige Phase vor dem Drop gestalten und Crash-Zustände dokumentieren.
- Bereits angewandte Revision 049 nicht als erneut ausführbar voraussetzen. Falls sie außerhalb des Releasepfads bereits lief, notwendige Reparaturen durch eine neue Forward-Migration ergänzen.
- Test-Fixture wirklich im alten Schema erstellen. Detaillierte Backfill-Tests dürfen nicht wegen bereits entfernter Markertabellen übersprungen werden.

**Regression / Abnahme**
- Frische Installation sowie 046→Head, 047→Head und committed 048→Head laufen ohne Sperrhänger.
- Mehrere Nutzer, eigene/neue Tags, bereits verknüpfte Tags, Kollisionen, versteckte Notizen und leere Bestände abdecken.
- Fehler mitten im Backfill, Neustart und erneuter Aufruf: keine Duplikate, keine verlorenen Ausgangsdaten, keine fremden Nutzerzuordnungen.
- Migration mit vorgesehenem Owner-Zugang; App anschließend mit eingeschränkter Runtime-Rolle funktionsfähig.
- Backup-/Restore-Probe. Ein destruktiver Downgrade wird nicht als Ersatz für getestetes Restore verkauft.

## A02 — Security-Arbeitspaket

Die vollständige Beschreibung, Evidenz und Abnahmekriterien liegen im lokalen Maßnahmenplan. Öffentliche Veröffentlichung gemäß SECURITY.md noch in Klärung. Dieses Paket bleibt verpflichtender Teil der Audit-Behebung.

## A03 — R2/R3: Nutzerentscheidungen erhalten

**Layout**
- Versionierte Legacy-Defaults vollständig vergleichen, einschließlich Reihenfolge und Flags. Nur den exakt unveränderten Default auf die neue reduzierte Vorlage abbilden.
- Bei angepassten Layouts Reihenfolge und explizite Enabled-Flags erhalten; Regeln für neue/unbekannte Schlüssel dokumentieren.
- Eine gemeinsame sprachunabhängige Fixture-Sammlung von Python und TypeScript prüfen lassen. Keine zwei unabhängig definierten Erwartungstabellen.
- Bereits fehlerhaft migrierte v2-Werte sind ohne Historie nicht sicher rekonstruierbar: verfügbare Sicherungen/Provenienz prüfen; keine vermuteten Entscheidungen überschreiben. Gegebenenfalls transparente Wiederherstellungsauswahl anbieten.

**Dismissals**
- Eine kanonische Schlüsselfunktion für Schreiben, Lesen und Migration verwenden; alte Changepoint-, Null-Association- und vorhandene Lag-Formate berücksichtigen.
- Versionsbezogene, idempotente Datenmigration plus Übergangskompatibilität vorsehen. Kollisionen und Unhide behandeln; Ausblendungen nicht unbeabsichtigt auf andere Metriken/Serien ausweiten.

**Regression / Abnahme**
- Exakter Default, nur umsortiert, Flag geändert, teilweise/unbekannte Keys, zweimalige Migration.
- Altes persistiertes Dismissal bleibt nach Upgrade und Regeneration verborgen; gezieltes Aufheben funktioniert; andere Nutzer/Serien bleiben unbeeinflusst.
- Gleiche Layout-Fixtures liefern in Backend und Frontend dieselben Ergebnisse.
- Existierende fehlerhafte Migrationstest-Erwartung durch Produktvertrag ersetzen.

## A04 — R8 und Wartbarkeit: Ein fachlicher Vertrag

**Umsetzung**
- Insight-Payloads nach Familie typisieren/validieren; Gruppenstärken, Null-/Missing-Werte, Rohwerte, Darstellungswerte, adjustierte Koeffizienten, Paaridentität und Evidenzfenster explizit machen.
- Backend-Schema, generierte API-Typen und Frontend-Adapter gemeinsam weiterentwickeln. Historische gespeicherte Payloads über kompatible Adapter lesen; neue Pflichtfelder nicht rückwirkend ungeprüft erzwingen.
- Stress-Rohwerte getrennt von positiv orientierten Anzeigewerten führen. Text beschreibt die tatsächliche Richtung; Achsenticks, Punkte, Effektpfeile und Export verwenden denselben Vertrag.
- Belastungs-Text an die tatsächlich berechnete Aussage binden. Für die vorhandenen marginalen Veränderungen zunächst „im Vergleich zum vorherigen Zeitraum …“ formulieren; „häufiger gemeinsam“ nur bei explizit berechneter gemeinsamer Häufigkeit.
- Gleiche Semantik in Deutsch/Englisch und bei fehlenden/unzureichenden Daten. Keine kausale oder klinische Aussage aus einer beobachteten Assoziation ableiten.

**Regression / Abnahme**
- Stress 2→5 und 5→2, unverändert und fehlend: Text, Pfeil und Skala widerspruchsfrei.
- Nur Stress verändert, nur Energie verändert, nur Fatigue verändert; Signale an getrennten versus gemeinsamen Tagen.
- Gruppen 5/95, fehlende Gruppen, Nullwerte, gleichzeitige und zeitversetzte Beziehungen, historische Payload-Versionen.
- API→Adapter→Darstellung-Vertragstests, nicht allein OpenAPI-Dateivergleich.

## A05 — R4 und ergänzende Security-Abnahme: Berichte und Export

**Umsetzung**
- Aus A04 ein gemeinsames, typisiertes Report-Row-Modell erzeugen. Bildschirm, PDF, PNG, CSV und JSON konsumieren dieselben ausgewählten Zeilen und Evidenzdaten.
- Getrennte Mit-/Ohne-Gruppengrößen, Gesamtzahl, Abdeckung und tatsächlichen Analysezeitraum ausgeben. Fehlende Daten als fehlend kennzeichnen.
- Auswahlzustände unterscheiden: Erstaufruf ohne Signal, gültiges Signal, ungültiges/veraltetes/nicht reportbares Signal, bewusst leere Auswahl, Refresh-Fehler.
- Ungültiges angefordertes Signal wählt keine anderen Zeilen automatisch aus. API-Fehler ist kein fachlicher „nicht reportbar“-Befund; bestehende Auswahl bei Refresh-Fehler erhalten.
- Sicher erlaubten internen Rücksprung samt `signal`-Parameter durch Login erhalten; keine beliebigen externen Redirect-Ziele zulassen.
- Hinweise zu Auswahl und leerem Export in beiden Sprachen auf alle vier Formate aktualisieren.

**Regression / Abnahme**
- 5/95-Gruppen in allen Formaten nachvollziehbar; identische Auswahl; Null-/Sonderzeichen; lange Namen, Umlaute und mehrseitige PDFs.
- Reale Browserwege für Login-Rückkehr, fehlgeschlagenes Laden, Refresh und explizites Deselektieren.
- PDF-/PNG-Rendering visuell prüfen; keine abgeschnittenen Tabellen, fehlende Gruppen oder unlesbare Zeichen.
- Der zusätzliche Security-Abschluss dieses Pakets bleibt verpflichtend; Details werden gemäß SECURITY.md separat behandelt.

## A06 — R5: Evidenzsprache auf allen Oberflächen

**Umsetzung**
- F1: Symptom-Kookkurrenz auch im optionalen Advanced-Bereich auf natürliche Häufigkeiten umstellen. Lift/FDR bleiben nach geltendem ADR internes Gate.
- F2: Richtung aus Beziehungstyp und Lag ableiten: `↔` gleichzeitige Assoziation, `→` tatsächliche zeitliche Richtung; negative Lags eindeutig orientieren. Titel, Karten und Exporte abgleichen.
- F4: vorhandene adjustierte Koeffizienten nur in Ebene 2 hinter Disclosure tatsächlich zeigen, mit Vergleich zum unadjustierten Effekt und verständlicher Beschreibung gehaltener Faktoren.
- Nicht berechnet, nicht unterstützt, zu wenig Daten und tatsächlich Null unterscheiden. Scatter-Steuerung nur bei unterstützter Verifikation anzeigen.

**Regression / Abnahme**
- F1/F2/F4-Matrix über Hub, Detail, optionale Heatmaps und Bericht; mehrere Reifestufen, Desktop/Mobil, Deutsch/Englisch.
- Adjustierter Effekt vorhanden/fehlend/Null; Composite-Insight ohne Scatter; Tastatur-/Screenreader-Erreichbarkeit.
- F3 und F5 bleiben erhalten: sekundäre Detailroute und echtes Nicht-Ergebnis, keine neue Hauptnavigation oder zurückkehrende falsche Positivbefunde.

## A07 — R6/R7: Exakte Analysefenster und verlässlicher Request-State

**Umsetzung**
- API-Vertrag auf exakte Tageszahl bzw. explizites Start-/Enddatum ausrichten. 14→7 und 28→30 als stillen Fallback entfernen.
- Bestehende Range-Clients kompatibel halten; Priorität bei gleichzeitigem Range-/Days-Parameter eindeutig validieren. API-Typen neu generieren.
- Alle betroffenen Abfragen inventarisieren: Timeseries, Tag-/Symptom-Kookkurrenz, Verteilungen, Compare, ESM, Bericht/Detail. Angezeigtes Evidenzfenster muss dem tatsächlich verwendeten entsprechen; historische persistierte Insights nicht nur neu beschriften.
- Datumsgrenzen, inklusive Tage, Nutzer-Zeitzone und Sommerzeit gemeinsam definieren.
- Request-Generation/Abbruch pro Kontext; nur passende Antworten dürfen Daten, Ladezustand und Fehler überschreiben. A→B→A ebenfalls absichern.
- Präferenzänderungen pro Nutzer serialisieren bzw. versionieren; neuester Wunsch gewinnt. Fehlgeschlagene Persistenz sichtbar behandeln, Retry ohne Rückschreiben älterer Werte.
- Request-/Selection-Orchestrierung aus großen Routen in überschaubare Controller/Stores extrahieren, zusammen mit Vertragsfällen.
- Short-Window- und Empty-Zustände auch ohne Paare mounten. Backend-Frühreturns liefern konsistente Flags; Analytics-Opt-out bleibt eigenständiger Zustand.

**Regression / Abnahme**
- 14/28/90 Tage stimmen in Request, Backend-Auswertung und UI; Tests an Tages-/DST-Grenzen und mit lückenhafter Historie.
- Verzögerte Antworten in vertauschter Reihenfolge und Login-/Nutzerwechsel überschreiben keine neueren/fremden Zustände.
- Schnell aufeinanderfolgende PATCHes, Offline/Fehler/Retry und Reload erhalten die letzte erfolgreich gewählte Einstellung.
- 0, 1, 14, 15 Beobachtungstage, ausreichend Daten ohne Paar, API-Fehler und Opt-out am Elternscreen getestet.
- Das Rechenlimit aus A02 erhält einen eigenen Zustand und erscheint nicht als „kein Zusammenhang“.

## A08 — R6/R9: Handoffs und Detailnavigation

**Umsetzung**
- Strukturierte Paaridentität aus Signalart, ID, Metrik, Kontext und gegebenenfalls Lag verwenden. Ein Treffer zu nur einem Pin gilt nicht als Nachweis für das Paar.
- Mitgegebene Treffer sichtbar fokussieren/filtern bzw. hervorheben; Mobile-Primärkarte und Desktop-Liste müssen denselben Kontext berücksichtigen.
- Tag-, Symptom- und Work-Context-Pins im ESM-Handoff erhalten; vorhandenen festen Partner anzeigen.
- Kein Treffer erst nach erfolgreicher fachlicher Suche anzeigen; Netzwerkfehler separat behandeln.
- Parameternavigation Signal A→B im echten Router reproduzieren. Falls die Komponente wiederverwendet wird, an ID gebunden laden und alte Requests entwerten; Zurück/Vorwärts und Refresh berücksichtigen.

**Regression / Abnahme**
- Compare→Insights→Detail→Bericht mit exaktem Paar und exakter Auswahl.
- Beide Pin-Reihenfolgen, Work-Context, Composite-Paar mit leerem `subject_id`, gültiger einzelner aber falscher Paar-Treffer.
- Fester ESM-Partner, keine Treffer, API-Ausfall und Direct-Link; mobile Fokussierung.
- A→B→Zurück ohne Vollreload zeigt jeweils korrekte Daten. Verdacht erst mit Browsernachweis schließen.

## A09 — R9: Plattform und Übersetzungsqualität

**Umsetzung**
- Timezone-Auflösung um gezielte Behandlung erwartbarer ungültiger Pfad-/Zone-Eingaben einschließlich Windows-`OSError` ergänzen. Keine pauschale Exception-Unterdrückung; gültige IANA-Zonen und begrenztes sicheres Logging erhalten.
- Doppelte `trends.compare.check_question`-Keys auflösen, DE/EN abgleichen.
- Duplicate-Key-Prüfung vor normalem JSON-Parsing in CI aufnehmen; ein Parser, der Duplikate bereits verwirft, reicht nicht.
- Exporthinweise aus A05 und Evidenztexte aus A06 gemeinsam prüfen.

**Regression / Abnahme**
- Timezone-Fälle auf Linux und Windows, gültige Zonen, unbekannte Namen, CR/LF und lange Eingaben; kein 500 für erwartbar ungültige Werte.
- Locale-Prüfung schlägt bei absichtlich dupliziertem Fixture fehl; Übersetzungs-Keys konsistent.

## A10 — Verifikationslücken und belastbare CI schließen

**Umsetzung**
- Frische lockfile-gebundene Installation in sauberem Checkout; voller Lint-, Typecheck-, Unit- und Produktionsbuild-Lauf auf dem finalen SHA.
- Web-Workerzahl passend zu Runner-Ressourcen begrenzen. Worker-Startfehler bleiben Fehlschläge; keine pauschale Retry-/Ignore-Maskierung.
- Kritische Backend-Pfade mit eigener Coverage-Auswertung gegen das dokumentierte Ziel prüfen; jede Test-Skip-Gruppe begründen. Upgrade-/Backfill-Tests müssen wirklich laufen.
- Reale API-/DB-E2E neben Mock-Smokes: zwei Nutzer, Login, Datenerfassung/Sync, Migration, Ausblendung, Fenster, Compare und Export.
- Dependency-/Image-Advisories frisch prüfen. Container-Findings nicht allein wegen `--exit-code 0` als bestanden werten; schärfere definierte Schwellen, begründete befristete Ausnahmen und klare Verantwortliche.
- Authentifizierten DAST-Pfad in isoliertem Staging ergänzen, einschließlich erreichbarer Analyse-/Export-Endpunkte und repräsentativer Proxy-Konfiguration. Befundbehandlung blockierend nach definierter Policy.
- Security-Regression für Ownership/RLS, Scoped-DEK, Cache-Isolation und begrenzte Berechnung; erneuter Diff-Review von S1/S2 und angrenzenden Änderungen.
- Visuelle/Accessibility-Smokes für geänderte Kernwege, Druck/Download und kleine Viewports.

**Abnahme**
Ein verlinktes Evidenzpaket für denselben Commit und dieselben gebauten Images: Linux-CI, Windows-Zeitzonenprüfung, Migration, reale E2E, Security-/Dependency-Ergebnisse, Performancebudget und visuelle Abnahme. Kein Ersatz durch grüne Jobs eines früheren PR-Heads.

## A11 — Alle Review-Kommentare und Doku abschließen

**Umsetzung**
- Jede relevante Review-Zeile mit Fix/Test oder überprüfbarer Widerlegung schließen. Historische Antworten und doppelte Bot-Kommentare nachvollziehbar gruppieren; kein Kommentar geht durch Aggregation verloren.
- Bereits reparierte #972/#973-Fälle als Regression erhalten: Sleep-Rohwerte, PDF-Seiten/Encoding, leere Auswahl, Refresh-Auswahl, Null-Winner, Filter vor Fetch-Cap, getrennte Query-Typen.
- #968→A03, #969→A05, #970→A07, #971→A06/A08, #974→A03/A06 und Doku-/Interviewnachweis.
- Rolloutplan bis zur echten Abnahme auf zutreffenden Zwischenstatus setzen. DESIGN_DOCUMENT-Exportstatus, ADR-Konsequenzen und Backlog widerspruchsfrei machen; historischen Kontext als historisch kennzeichnen.
- SECURITY.md-Supportmatrix auf tatsächlich unterstützte Releases aktualisieren.
- Für fälschlich geschlossene Themen verbleibende Gates sichtbar verknüpfen; Wiederöffnung durch berechtigte Rolle veranlassen, sofern keine Agent-Berechtigung besteht.
- PR-Body: `Closes/Fixes` ausschließlich bei vollständig erfüllter Issue-Abnahme ohne externe Restaufgabe; sonst `Relates to`. Nach der letzten Änderung eine finale Review-Runde auf genau dem zu mergenden SHA abwarten.

**Abnahme:** Keine unbeantworteten relevanten Findings; keine Fertigmeldung entgegen offenen Gates; Review-Register mit Fix-/Test-/Abnahmelinks vollständig. GitHub-Schreibaktionen separat im Rahmen eines ausdrücklichen Umsetzungsauftrags ausführen.

## A12 — Externe Abnahmen

| Gate | Konkrete Arbeit | Nachweis / Abschluss | Rolle |
|---|---|---|---|
| Nutzerverständnis #930 H.4 | Interviews/Usability-Szenarien zu Belastung, Nicht-Ergebnis und vier Ebenen gemäß ursprünglichen Kriterien durchführen; Erkenntnisse umsetzen | Dokumentierte Durchführung, Befunde, nachgeprüfte Änderungen; kein bloßes Text-Update | Produkt / Research |
| Health Connect / M8 | Reale Geräteprüfung von Einwilligung, Import, Zeitbezug, Widerruf und Wiederholung | Geräte-/OS-Matrix und Testprotokoll | Mobile QA |
| Hosted Beta / #621 | Offene Owner-Closeout-Punkte gegen tatsächlichen Betrieb prüfen | Verantwortliche bestätigen die ursprünglichen Kriterien | Betrieb / Release |
| Firebase/Play / #429 | Push auf vorgesehenem Play-/Firebase-Pfad mit realen Geräten prüfen | Zustellung, Berechtigung, Abmeldung und Fehlerfälle dokumentiert | Mobile / Betrieb |
| Laufzeit-Sicherheit | Tatsächliche DB-Rollen inkl. Superuser/BYPASSRLS, RLS, TLS/Proxy, Cookies und Worker-Konfiguration kontrollieren | Redigiertes Konfigurations-/Testprotokoll, ohne Secrets | Betrieb / Security |
| Deployment / Wiederherstellung | Kandidat im Staging auf v1.9.1-Datenfixture upgraden, Smoke, Backup-Restore; später produktive Smoke-Prüfung | Image-Digests, Migrationsstand, Restore-Nachweis und Freigabe | Betrieb / Release |

Fehlende Zugänge, Geräte oder Interviewpartner erzeugen einen offenen zugewiesenen Punkt; sie werden nicht durch Annahmen ersetzt. Staging-Abnahme ist Voraussetzung für Deployment, produktive Smoke-Prüfung ein nachgelagertes Rollout-Gate.

## Vollständige Abdeckungsmatrix

| Audit-Unterpunkt | Paket | Abschlussnachweis |
|---|---|---|
| R1 Sperrzyklus / neues ORM im alten Schema | A01 | direkter 046→Head-Integrationstest |
| R1 übersprungene detaillierte Backfill-Tests | A01/A10 | alte Schema-Fixture, keine unbemerkten Skips |
| S1 Security-Befund | A02 | Separat vorliegende validierte Abnahmekriterien erfüllen |
| R2 angepasste Layouts überschrieben | A03 | gemeinsame TS/Python-Fixtures |
| R2 bereits fehlerhaft migrierte Einstellungen | A03 | geprüfter Wiederherstellungsweg statt Rekonstruktion nach Vermutung |
| R3 Dismissal-Schlüsselwechsel | A03 | persistierte Legacy-Daten bleiben korrekt ausgeblendet |
| R4 Gruppenstärken/Abdeckung fehlen im Download | A04/A05 | gleiche Evidenz in UI + vier Formaten |
| R4 ungültiges Signal selektiert alle | A05 | sichere leere Auswahl |
| R4 Fehler wird Nicht-Reportbarkeit | A05 | getrennte fachliche/technische Zustände |
| R4 Signalverlust bei Login | A05/A08 | erlaubter Rücksprung mit Parameter |
| S2 Security-Befund | A05 | Separat vorliegende validierte Abnahmekriterien erfüllen |
| R5 F1 natürliche Häufigkeiten | A06 | Advanced-Symptom-Fläche ebenfalls abgenommen |
| R5 F2 Pfeilrichtung | A04/A06 | gleichzeitige/zeitversetzte Fälle |
| R5 F4 adjustierte Koeffizienten | A04/A06 | Disclosure zeigt vorhandene Werte |
| R5 Scatter ohne Unterstützung | A06 | Composite-/Missing-Fall |
| R6 falsche Tagesfenster 14→7 / 28→30 | A07 | API-Datumsgrenzen entsprechen UI |
| R6 veraltete Responses | A07 | deterministischer Race-Test |
| R6 Preference-Reihenfolge / verschluckte Fehler | A07 | Persistenz-/Retry-/Reload-Test |
| R6 vollständiges Paar / sichtbare Fokussierung | A08 | echte Journey, beide Pin-Arten/-Reihenfolgen |
| R6 Work-Context / ESM-Partner | A08 | Partner erhalten und sichtbar |
| R6 Load-Fehler als fehlender Befund | A07/A08 | Netzwerkfehler separat |
| R7 nicht gemounteter Short-Window-State | A07 | Elternscreen-Test |
| R7 leeres Fenster ohne Flag | A07 | Backend-Frühreturn-Test |
| R8 Stress-Richtung / Skalenkonsistenz | A04 | Rohwert, Text, Achse und Pfeil konsistent |
| R8 unbelegte gemeinsame Belastung | A04 | Text entspricht gemessener Größe |
| R9 Windows-Zeitzone | A09 | Windows + Linux |
| R9 doppelte Locale-Keys | A09 | Parserprüfung vor Überschreiben |
| R9 irreführende Export-Copy | A05/A09 | DE/EN für alle Formate |
| R9 keine direkten CSV-Tests | A05 | echte Serialisierung getestet |
| R9 Parameter-only-Detailnavigation | A08 | Router-Reproduktion/Fix oder Gegenbeleg |
| Wartbarkeit: doppelte Vertragslogik | A03/A04/A05 | gemeinsame Fixtures/Adapter/Reportmodell |
| Wartbarkeit: überladene Routen | A07/A08 | getrennte Request-/Kontextlogik, Verhaltenstests |
| Wartbarkeit: generische Payloads | A04 | familienbezogener Vertrag mit Legacy-Adapter |
| Tests spiegeln falsche Implementierung | A01/A03/A07/A10 | fachliche Integrationserwartungen |
| Zu früher Review-/Issue-Closeout | A00/A11 | Register und finale SHA-Review |
| Doku- und Supportmatrix-Drift | A11 | Status entspricht Evidenz |
| Fehlende Build-/DB-/E2E-/visuelle Nachweise | A10 | sauberer finaler Kandidatenlauf |
| Nicht blockierende DAST-/Image-Checks | A10 | ausdrückliche Gate-Policy und echte Befundbehandlung |
| Fehlende Advisory-/Runtime-/Geräte-Abnahme | A10/A12 | aktuelle Prüfergebnisse / externe Sign-offs |
| Interviews und Owner-/Play-Abnahmen | A12 | ursprüngliche Akzeptanzkriterien erfüllt |

## Roadmap-Lücken aus dem Soll-Ist-Abgleich

Diese Punkte sind absichtlich spätere Produktziele, keine durch den Audit neu entdeckten Regressionen. Sie bleiben im Gesamtplan sichtbar und dürfen nicht als bereits erfüllt ausgewiesen werden.

- **M12 SaaS:** eigener Meilenstein für mandanten-/kontogebundene Billing-Zustände und Webhooks, vollständiges Onboarding, Authentik Phase 2 einschließlich Account-Verknüpfung/Sessionverhalten sowie Betriebs-/Datenschutzanforderungen des DESIGN_DOCUMENT. Abnahme: Registrierung→Billing→erste Nutzung, Fehler-/Wiederholungsfälle und ursprüngliche M12-Exit-Kriterien einschließlich externer Nachweise erfüllt.
- **M13 Medien:** MinIO-Persistenz und Metadaten, Ownership und begrenzte Zugriffslinks, Galerie, Löschung/Cascade, Backup-/Restore sowie EXIF-Strip erhalten. `stored:false` erst nach tatsächlicher Speicherung ersetzen. Abnahme: Upload→Speicherung→Anzeige→Löschung über reale Storage-Integration; fremder Zugriff gesperrt; ursprüngliche M13-Exit-Kriterien erfüllt.
- Keine stillschweigende Scope-Erweiterung des aktuellen Stabilitätsreleases auf einen kompletten SaaS-/Medienlaunch. Wenn „vollständiges ursprüngliches Zielbild“ als Releaseziel gewählt wird, sind M12/M13 zusätzliche zwingende Meilensteine; ein technisch stabilisierter Zwischenrelease ist nicht als vollständiges Zielbild zu deklarieren.

## Definition of Done für die Audit-Behebung

- [ ] A00-Register enthält jeden Unterpunkt und jeden relevanten Review-Kommentar.
- [ ] R1–R9 und S1–S2 geschlossen durch Fix + Regression + Evidenz oder, bei Verdachtsfällen, dokumentierten Gegenbeleg.
- [ ] Bestehende Fixes #972/#973 weiterhin wirksam.
- [ ] Upgrade, Nutzerzustand, fachliche Aussagen, Fenster und Export im integrierten Produkt korrekt.
- [ ] A10 vollständig am finalen Commit/Image durchgeführt; keine ungeklärten Testfehler oder verdeckten Skips.
- [ ] Alle für den angebotenen Releaseumfang nötigen A12-Gates abgeschlossen; übrige Meilensteine ausdrücklich offen geführt.
- [ ] Review-/Doku-Status stimmt mit tatsächlicher Abnahme überein.
- [ ] Release-Verantwortung entscheidet anhand dieses Evidenzpakets; anschließend kontrollierter Rollout mit eigener produktiver Smoke-Prüfung.

**Ergebnis:** Erst diese nachgewiesene Umsetzung schließt den Audit. Das bloße Anlegen dieses Plans oder der zugehörigen PRs schließt keinen Befund.



## GitHub-Arbeitspakete

- [A00: Ausgangsstand und vollständiges Befundregister](https://github.com/Sturmi77/correlcore/issues/976)
- [A01: Sicheres Release-Upgrade und Marker-Backfill](https://github.com/Sturmi77/correlcore/issues/977)
- [A03: Layout-Einstellungen und persistierte Ausblendungen erhalten](https://github.com/Sturmi77/correlcore/issues/978)
- [A04: Fachliche Datenverträge und Stress-/Belastungssemantik](https://github.com/Sturmi77/correlcore/issues/979)
- [A06: Evidenzdarstellung F1/F2/F4 vervollständigen](https://github.com/Sturmi77/correlcore/issues/980)
- [A07: Exakte Analysefenster, Request-State und Leerzustände](https://github.com/Sturmi77/correlcore/issues/981)
- [A08: Compare-/ESM-Handoffs und Detailnavigation](https://github.com/Sturmi77/correlcore/issues/982)
- [A09: Timezone-Robustheit und Übersetzungsqualität](https://github.com/Sturmi77/correlcore/issues/983)
- [A10: CI-, Integrations- und Security-Freigabenachweise](https://github.com/Sturmi77/correlcore/issues/984)
- [A11: Review- und Dokumentationsabschluss](https://github.com/Sturmi77/correlcore/issues/985)
- [A12: Geräte-, Betriebs- und Nutzerabnahmen](https://github.com/Sturmi77/correlcore/issues/986)

A02/A05: öffentliche Issue-Veröffentlichung noch in Klärung. Existierende externe Aufgaben werden über A12 verknüpft. Die frühere M13-Medienplanung ist mit der dokumentierten neuen Priorisierung in #715 abzugleichen, bevor zusätzliche Implementierungs-Issues entstehen.

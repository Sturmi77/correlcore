# Release-Audit nach v1.9.1
Stand: 22.09.2026 · geprüfter Hauptstand: `71d1089ff77388cadf2253ac67d1471dfa99fa40`

## Entscheidung
**Für diesen Stand empfehle ich noch keine Produktionsfreigabe.** Die Erweiterung ist substanziell und die technische Basis deutlich weiterentwickelt. Die dokumentierte Fertigmeldung ist aber zu weitgehend: Upgrade-Sicherheit, Zustandsübernahme, wissenschaftliche Darstellung und mehrere Benutzerwege erfüllen ihre Abnahmekriterien noch nicht durchgängig.

**Nein, nicht alle Review-Kommentare sind im geprüften Code sauber adressiert.** Es gibt sowohl nachvollziehbar korrigierte Reviews als auch weiterhin reproduzierbare bzw. quelltextlich eindeutige Gegenbeispiele. „Merged“, „Issue closed“ und „Review thread resolved“ sind jeweils andere Zustände als „Akzeptanzkriterium erfüllt“.

Die zwei bestätigten Security-Befunde sind **Medium** (unbegrenzte CPU-Arbeit im API-Worker) und **Low** (CSV-Formelinjektion beim Teilen von Berichten). Kein bestätigter High/Critical-Befund wurde in diesem Änderungsumfang gefunden. Dies ist keine Sicherheitsgarantie oder vollständige Prüfung der produktiven Infrastruktur.

## Umfang und Methode
- Basis `v1.9.1 = ea083950590c6823cbc8d4d43d4696aac85dd631`; Ziel siehe oben. **116 Commits, 307 geänderte Dateien, +25.838/−4.974 Zeilen**.
- Quelltextprüfung am unveränderten `git archive` des Zielcommits. 85 Backend-, 112 sonstige Frontend/Package- und 44 Svelte-Dateien wurden im Security-Workflow getrennt geprüft. Die übrigen 66 Dateien betreffen insbesondere Dokumentation, Mockups, Build-/CI-Konfiguration und Hilfsskripte. Gelöschte Produktionspfade wurden am Basisstand berücksichtigt.
- 50 relevante PR-Timelines mit **524 Kommentaren**, davon **298 Inline-Kommentare inklusive Antworten**, eingelesen. Diese Zahlen sind keine Anzahl unabhängiger Findings. Historische PR-Stacks schließen auch ungemergte, später konsolidierte PRs ein.
- Ursprüngliches DESIGN_DOCUMENT am Release-Stand mit aktuellem Design, ADR-0043, Rolloutplan und Implementierung abgeglichen. Spätere ausdrücklich beschlossene Designänderungen gelten als bewusste Weiterentwicklung.
- Vorhandene **61 lokale Änderungen** und der abweichende lokale HEAD wurden nicht als veröffentlichter Fix gewertet und nicht verändert. Einige lokale Änderungen scheinen genau diese Probleme zu bearbeiten; sie benötigen eine eigene Prüfung ihres finalen Commits.
- Kein Produktcode geändert, keine Issues geschlossen, keine PR-Kommentare veröffentlicht, kein Deployment vorgenommen.

### Grenzen
Der Connector liefert hier keine vollständigen GraphQL-`isResolved`-Daten. Eine exakte Zahl momentan „offener Threads“ lässt sich daraus nicht seriös ableiten. Die Aussage über nicht erledigte Reviews stützt sich auf den aktuellen Code und konkrete Review-Verweise.

Keine produktive Datenbank, echten Nutzerdaten, TLS-/DB-Rolleneinstellungen oder Android-Geräte geprüft. Kein vollständiger Browserlauf gegen reale API. Keine neue vollständige CVE-/Dependency-Advisory-Abfrage. Vorhandene lokale Dependencies verwendet; kein frischer hermetischer Install/Build. Raster-Mockups inventarisiert, aber keine vollständige visuelle Screenshot-Abnahme.

## Priorisierte Befunde
P1/P2 in diesem Abschnitt sind **Release-/Produktprioritäten**, nicht automatisch Security-Schweregrade.

### R1 · P1 · Mehrschritt-Upgrade kann in Migration 049 hängen
**Auslöser:** Upgrade aus v1.9.1 bzw. einem Stand vor 048, mit umzuwandelnden nicht ausgeblendeten Markern.

Alembic führt die Revisionen unter einer übergreifenden Transaktion aus. Migration 048 verändert `tags` und hält DDL-Sperren. Migration 049 wartet synchron auf einen separaten Python-Prozess, dessen eigene DB-Verbindung für den Backfill dieselbe Tabelle lesen muss. Der Elternprozess kann erst nach Ende des Kindes committen; das Kind benötigt den Commit bzw. die Freigabe der Sperre. Je nach DB-Timeout hängt das Upgrade oder scheitert.

**Evidenz:** [backend/migrations/env.py:38](https://github.com/Sturmi77/correlcore/blob/71d1089ff77388cadf2253ac67d1471dfa99fa40/backend/migrations/env.py#L38), [backend/migrations/versions/048_add_tag_is_pinned.py:25](https://github.com/Sturmi77/correlcore/blob/71d1089ff77388cadf2253ac67d1471dfa99fa40/backend/migrations/versions/048_add_tag_is_pinned.py#L25), [backend/migrations/versions/049_drop_entry_note_markers.py:84](https://github.com/Sturmi77/correlcore/blob/71d1089ff77388cadf2253ac67d1471dfa99fa40/backend/migrations/versions/049_drop_entry_note_markers.py#L84), [backend/app/services/marker_tag_backfill_service.py:235](https://github.com/Sturmi77/correlcore/blob/71d1089ff77388cadf2253ac67d1471dfa99fa40/backend/app/services/marker_tag_backfill_service.py#L235).

**Sicherheit der Aussage:** statisch belegter Sperr-/Verbindungszyklus; mangels PostgreSQL hier nicht als Live-Deadlock reproduziert. Der bestehende Integrationstest startet aus bereits committed 048 und deckt den direkten Release-Upgradepfad nicht ab. Die detaillierten alten Backfill-Tests werden am normalen Head wegen der bereits entfernten Markertabelle übersprungen.

**Freigabebedingung:** Upgrade mit echter PostgreSQL-Instanz direkt von 046/v1.9.1 nach Head, repräsentativen alten Daten, neuen Custom-Tags und Fehlerfall prüfen. Backfill so organisieren, dass Kindprozess und offene Elterntransaktion keine solchen Abhängigkeiten besitzen; Wiederanlauf und Datenverlustfreiheit nachweisen.

### S1 · Security Medium · Benutzersteuerbare Analyse blockiert den API-Worker
Der neue Tag-Paar-Endpunkt ruft aus dem asynchronen Requestpfad direkt eine synchrone Analyse auf. Für jedes zulässige Tag-Paar werden Tage durchlaufen und Fisher-Statistiken berechnet, bevor geringe gemeinsame Häufigkeit ausgesiebt wird. Eine Obergrenze für Gesamtzahl der Tags bzw. Paararbeit fehlt.

**Quellpfad:** [backend/app/api/v1/endpoints/insights.py:310](https://github.com/Sturmi77/correlcore/blob/71d1089ff77388cadf2253ac67d1471dfa99fa40/backend/app/api/v1/endpoints/insights.py#L310) → [backend/app/services/stats_service.py:538](https://github.com/Sturmi77/correlcore/blob/71d1089ff77388cadf2253ac67d1471dfa99fa40/backend/app/services/stats_service.py#L538) → [backend/app/services/symptom_analytics.py:615](https://github.com/Sturmi77/correlcore/blob/71d1089ff77388cadf2253ac67d1471dfa99fa40/backend/app/services/symptom_analytics.py#L615) / [backend/app/services/symptom_analytics.py:395](https://github.com/Sturmi77/correlcore/blob/71d1089ff77388cadf2253ac67d1471dfa99fa40/backend/app/services/symptom_analytics.py#L395).

**Lokale Probe:** 60 Tags, 15 Tage, 20 Tags/Tag, 1.770 Paarprüfungen: **16,39 Sekunden** im tatsächlichen Analysecode. Keine HTTP-Last oder fremde Systeme belastet. Das ist eine lokale Messung mit gemeinsam genutzten Rechnerressourcen, keine Produktions-Latenzgarantie.

Verifiziertes Konto, Mindesthistorie, 50 Tags pro Eintrag und Rate-Limit begrenzen den Zugang, verhindern aber keine teure Einzelanfrage. Betroffen ist der gemeinsame Event-Loop; der ausgelieferte Uvicorn-Start verwendet standardmäßig keinen zusätzlichen Worker-Parameter. Tatsächliche Produktions-Workerzahl unbekannt.

**Maßnahme:** explizites Rechenbudget/Paarlimit vor teurer Statistik, begrenzte Worker-Ausführung, Fairness pro Nutzer und Cache. Nur `to_thread` schützt noch nicht gegen unbeschränkte CPU-/Queue-Belegung. Parallel laufende Health-/Nutzeranfragen müssen unter Grenzlast weiterhin antworten.

### R2 · P2 · Migration verändert bewusst angepasste Layouts
Die v1→v2-Migration setzt auch bei einem angepassten/reihenfolgeveränderten Layout bisher aktivierte optionale Bereiche auf `false`. Damit werden nicht nur exakte alte Defaults reduziert. Eine lokale Probe mit vertauschten ersten zwei Einträgen deaktivierte sechs vorher aktive Bereiche.

**Evidenz:** [backend/app/services/insight_sections.py:172](https://github.com/Sturmi77/correlcore/blob/71d1089ff77388cadf2253ac67d1471dfa99fa40/backend/app/services/insight_sections.py#L172) und gespiegelte TypeScript-Migration. **Widerspruch:** ADR F6 verlangt Erhalt angepasster Enabled-Flags. Der vorhandene Test erwartet teilweise gerade die falsche Produktsemantik; ein grüner Test genügt hier nicht.

**Maßnahme:** nur exakte unveränderte Legacy-Defaults reduzieren; angepasste Layouts konservativ erhalten. Backend und Frontend gegen dieselben Vertragsfälle prüfen. [Offener Code-Gegenbeleg zum Review](https://github.com/Sturmi77/correlcore/pull/974#discussion_r4070128091).

### R3 · P2 · Persistierte Ausblendungen passen nicht zu neuen Schlüsseln
Die neuen Family-/Subject-Schlüssel für Changepoints bzw. Null-Assoziationen werden beim Lesen/Erzeugen umgestellt, ohne vorhandene Dismissal-Schlüssel entsprechend zu migrieren. Die Dismissal-Service-Sonderbehandlung betrifft bisher Lag-Schlüssel. Alte ausgeblendete Befunde können erneut erscheinen.

**Evidenz:** [backend/app/services/insight_service.py:418](https://github.com/Sturmi77/correlcore/blob/71d1089ff77388cadf2253ac67d1471dfa99fa40/backend/app/services/insight_service.py#L418), [backend/app/services/insight_dismissal_service.py](https://github.com/Sturmi77/correlcore/blob/71d1089ff77388cadf2253ac67d1471dfa99fa40/backend/app/services/insight_dismissal_service.py); [Review #968](https://github.com/Sturmi77/correlcore/pull/968#discussion_r4057277069).

**Maßnahme:** vorhandene Schlüssel deterministisch migrieren bzw. kompatibel lesen; Upgrade-Test mit tatsächlich persistierten alten Dismissals. Für Release-1.9.1 insbesondere bereits vorhandene Changepoint-Ausblendungen prüfen.

### R4 · P2 · Berichte verlieren wesentliche Evidenz und Auswahlkontext
Die Bildschirmtabelle berücksichtigt Gruppengrößen, die heruntergeladenen Berichte weiterhin nicht vollständig: PDF und CSV/JSON verwenden wesentlich `sample_n`, nicht die getrennten Mit-/Ohne-Gruppen. 5 versus 95 Tage dürfen nicht allein als `n=100` vermittelt werden.

Zusätzlich führt ein ungültiger/alter `?signal=`-Link zur Auswahl aller reportbaren Zeilen. Ein fehlgeschlagener Request kann als „Signal nicht reportbar“ interpretiert werden; der konkrete Signalparameter geht im Login-Weiterleitungsweg verloren.

**Evidenz:** [apps/web/src/lib/utils/insightMatrixExport.ts:180](https://github.com/Sturmi77/correlcore/blob/71d1089ff77388cadf2253ac67d1471dfa99fa40/apps/web/src/lib/utils/insightMatrixExport.ts#L180), [apps/web/src/lib/utils/insightMatrixExport.ts:282](https://github.com/Sturmi77/correlcore/blob/71d1089ff77388cadf2253ac67d1471dfa99fa40/apps/web/src/lib/utils/insightMatrixExport.ts#L282), [apps/web/src/routes/insights/report/+page.svelte:84](https://github.com/Sturmi77/correlcore/blob/71d1089ff77388cadf2253ac67d1471dfa99fa40/apps/web/src/routes/insights/report/+page.svelte#L84). [Gruppen-Review](https://github.com/Sturmi77/correlcore/pull/969#discussion_r4057276851), [Auswahl-Review](https://github.com/Sturmi77/correlcore/pull/969#discussion_r4057276856).

**Maßnahme:** ein gemeinsames Berichtsmodell für UI und alle Exportformate, explizite Gruppengrößen/Abdeckung, sichere leere Auswahl bei nicht gefundenem Signal, Fehlerzustand getrennt von fachlichem Nicht-Ergebnis. Keine automatische Fremddatenfreigabe nachgewiesen; Export erfolgt weiterhin durch den Nutzer.

### S2 · Security Low · CSV-Formelinjektion bei geteilten Berichten
Benutzerdefinierte Namen erreichen `subject_label` und die erste CSV-Spalte. `csvCell` maskiert CSV-Trennzeichen und Anführungszeichen, neutralisiert aber keine Tabellenformeln.

**Evidenz:** [apps/web/src/lib/utils/insightMatrixExport.ts:273](https://github.com/Sturmi77/correlcore/blob/71d1089ff77388cadf2253ac67d1471dfa99fa40/apps/web/src/lib/utils/insightMatrixExport.ts#L273) und [apps/web/src/lib/utils/insightMatrixExport.ts:332](https://github.com/Sturmi77/correlcore/blob/71d1089ff77388cadf2253ac67d1471dfa99fa40/apps/web/src/lib/utils/insightMatrixExport.ts#L332). Probe mit tatsächlichem Exportcode und harmlosem Namen `=1+1`: erzeugte CSV-Zelle bleibt `=1+1`.

Ein Sicherheitsgewinn über das eigene Konto hinaus setzt voraus, dass der Autor den Bericht weitergibt und der Empfänger ihn als Formeln interpretierend öffnet. Keine RCE, Datenexfiltration oder tatsächliche Tabellenkalkulationsausführung bewiesen.

**Maßnahme:** zentrale, getestete Textzellen-Policy für CSV. Formelführende Zeichen und relevante führende Steuerzeichen berücksichtigen; echte numerische Spalten nicht pauschal in Text umwandeln. Getrennte Tests für Quotes/Kommas/Zeilenumbrüche und Formula-Neutralisierung.

### R5 · P2 · Evidenzsprache entspricht ADR F1/F2/F4 noch nicht überall
- Die optionale Symptom-Kookkurrenz zeigt für fortgeschrittene Nutzer weiterhin Lift/Signifikanz als primäre Zellbeschriftung statt natürlicher Häufigkeiten.
- Der Signal-Detailtitel verwendet pauschal `→`, auch für gleichzeitige Zusammenhänge, die laut F2 `↔` benötigen.
- Die „gleiche Situation“-Parser halten adjustierte Koeffizienten vor, die Detaildarstellung zeigt sie aber nicht wie F4 zugesagt.
- Bei nicht unterstützter Verifikation wird trotzdem ein Scatter-Umschalter angeboten.

**Evidenz:** [apps/web/src/lib/components/insights/symptoms/SymptomCooccurrenceHeatmap.svelte:194](https://github.com/Sturmi77/correlcore/blob/71d1089ff77388cadf2253ac67d1471dfa99fa40/apps/web/src/lib/components/insights/symptoms/SymptomCooccurrenceHeatmap.svelte#L194), [apps/web/src/routes/insights/signal/[id]/+page.svelte:73](https://github.com/Sturmi77/correlcore/blob/71d1089ff77388cadf2253ac67d1471dfa99fa40/apps/web/src/routes/insights/signal/[id]/+page.svelte#L73). [F1](https://github.com/Sturmi77/correlcore/pull/974#discussion_r4070128060), [F2](https://github.com/Sturmi77/correlcore/pull/974#discussion_r4070128073), [F4](https://github.com/Sturmi77/correlcore/pull/974#discussion_r4070128082).

**Maßnahme:** Produktsemantik über alle erreichbaren Detail-/Advanced-Flächen abnehmen. Bewusst nicht gewählter Forest-Plot und verworfene Navigation werden nicht als fehlende Implementierung gewertet.

### R6 · P2 · Zeitfenster und Compare-Kontext sind nicht durchgängig zuverlässig
`loadTrends` setzt das aktive Fenster vor asynchronen Requests; eine ältere langsame Antwort kann eine neuere Auswahl überschreiben. Ein Request-Generation-Guard fehlt. Präferenz-PATCHes erfolgen ohne Serialisierung; Fehler werden still verworfen. Ergebnisdaten können dadurch nicht zur aktuellen Auswahl passen.

Der Compare→Insights-Weg berechnet `carriedMatches`, nutzt diese aber nicht zur Auswahl/Fokussierung der sichtbaren Insights. Ein einzelnes passendes `subject_id` ist außerdem kein Beleg für das vollständige mitgegebene Paar. Work-Context-Pins und ESM-Partner gehen in Teilpfaden verloren. Ladefehler können als fachlich fehlender Befund dargestellt werden.

**Evidenz:** [apps/web/src/routes/trends/+page.svelte:194](https://github.com/Sturmi77/correlcore/blob/71d1089ff77388cadf2253ac67d1471dfa99fa40/apps/web/src/routes/trends/+page.svelte#L194), [apps/web/src/routes/insights/+page.svelte:771](https://github.com/Sturmi77/correlcore/blob/71d1089ff77388cadf2253ac67d1471dfa99fa40/apps/web/src/routes/insights/+page.svelte#L771), [apps/web/src/lib/components/trends/TrendsComparePanel.svelte:455](https://github.com/Sturmi77/correlcore/blob/71d1089ff77388cadf2253ac67d1471dfa99fa40/apps/web/src/lib/components/trends/TrendsComparePanel.svelte#L455). [Review #971](https://github.com/Sturmi77/correlcore/pull/971#discussion_r4057288839).

**Maßnahme:** Antworten an Fenster/Generation binden, Persistenz explizit behandeln, mitgegebenes Paar strukturiert matchen und sichtbar fokussieren; Race-/Fehlerfalltests über den Benutzerweg.

### R7 · P2 · Short-Window-Erklärung wird im Elternscreen ausgeblendet
Das Backend liefert bei zu wenig Daten leere Paare und `window_too_short`. Der Elternscreen mountet den Block aber nur während des Ladens oder bei vorhandenen Paaren. Damit verschwindet gerade die neu implementierte Erklärung. Bei völlig leerem Zeitfenster setzt ein früher Backend-Return das Flag außerdem nicht.

**Evidenz:** [apps/web/src/routes/insights/+page.svelte:754](https://github.com/Sturmi77/correlcore/blob/71d1089ff77388cadf2253ac67d1471dfa99fa40/apps/web/src/routes/insights/+page.svelte#L754), [backend/app/services/stats_service.py:478](https://github.com/Sturmi77/correlcore/blob/71d1089ff77388cadf2253ac67d1471dfa99fa40/backend/app/services/stats_service.py#L478). [Review #970](https://github.com/Sturmi77/correlcore/pull/970#discussion_r4057279391).

**Maßnahme:** fachlichen Leer-/Short-Window-Zustand unabhängig von vorhandenen Paaren rendern; Test am Elternscreen, nicht nur an der isolierten Heatmap.

### R8 · P2 · Stress-Interpretation und Belastungs-Aussagen benötigen semantische Abnahme
Die Changepoint-Aussage invertiert für Stress die Richtung und formuliert beim Anstieg des rohen Mittelwerts etwa von 2 auf 5 „lower levels“. Eine invertierte grafische Wohlbefindensachse darf die Aussage über den tatsächlichen Stress-Mittelwert nicht umdrehen.

**Evidenz:** [backend/app/services/insights/changepoint.py:67](https://github.com/Sturmi77/correlcore/blob/71d1089ff77388cadf2253ac67d1471dfa99fa40/backend/app/services/insights/changepoint.py#L67). Darüber hinaus werden Belastungsbausteine über einzelne Marginaländerungen kombiniert; eine Formulierung wie „häufiger gemeinsam“ benötigt eine tatsächlich gemessene gemeinsame Häufigkeit. Diese Semantik ist vor einer fachlichen Produktabnahme zu klären; keine klinische Wirksamkeit wurde untersucht.

**Maßnahme:** klar zwischen rohem Messwert, positiv orientierter Anzeige und sprachlicher Aussage unterscheiden. Konkrete Beispiele steigender/fallender Stresswerte sowie getrennt/gemeinsam auftretender Symptome als Vertragsfälle testen.

### R9 · P2/P3 · Plattformfehler und kleine Wartbarkeitsschulden
Zwei Backend-Tests scheitern auf Windows: `ZoneInfo` wirft für CR/LF-haltige Eingaben `OSError`, der Fallback fängt nur `ZoneInfoNotFoundError/ValueError`. Das ist ein Robustheitsfehler; kein nachgewiesener systemweiter Linux-Produktions-DoS.

Weitere konkrete Kleinigkeiten: doppelte `trends.compare.check_question`-Keys in beiden Sprachdateien (späterer Wert überschreibt früheren), Export-Hilfetext nennt nur PNG/PDF trotz CSV/JSON, fehlende direkte CSV-Exporttests. Signal-Detail lädt nur bei Mount; Navigation zwischen IDs ist zusätzlich im realen Router zu prüfen.

## Sind die Reviews sauber abgeschlossen?
| Gruppe | Bewertung am geprüften Head |
|---|---|
| PR #973: Winner-Auswahl von Null-Assoziationen, Filter vor Fetch-Cap, Refresh-Auswahl und Query-Typen | Nach Folgecommit im Code adressiert; nicht erneut als offene Bugs gewertet. Antworten und Änderungen sind nachvollziehbar. |
| PR #972/#973: Sleep-Rohwerte, PDF-Seitenaufteilung, Zeichenbehandlung und leere Auswahl | Wesentliche Korrekturen vorhanden. Daraus folgt aber noch keine vollständige Export-Abnahme. |
| PR #968 | Dismissal-Schlüsselmigration weiterhin offen (R3). |
| PR #969 | Gruppenevidenz im Download sowie ungültiger Signal-/Fehler-/Login-Kontext weiterhin unvollständig (R4). |
| PR #970 | Short-Window-Zustand im Elternscreen weiterhin defekt (R7). |
| PR #971 | Compare-/ESM-Handoffs und vollständige Paarzuordnung nur teilweise erledigt (R6). |
| PR #974 | F1/F2/F4/F6 und Doku-/Interview-Closeout nicht ausreichend belegt (R2/R5). |

**Chronologie:** #974 wurde am 22.09.2026 um 09:13:38 UTC gemergt. Die sechs einschlägigen Review-Kommentare kamen um 09:19:41 UTC. Der geprüfte Merge-Stand kann diese späteren Hinweise schon zeitlich nicht als Folgeänderung enthalten.

Issue #958 dokumentierte für einen älteren Stand 55 ungelöste Threads und 22 offene Prüfpunkte; spätere Kommentare unterscheiden 17 valide, zwei nicht reproduzierte und drei unklare Punkte. Das ist historische Evidenz, keine unverändert aktuelle Zählung. Die Folgereparaturen #968–#971 lösten Teile, erzeugten aber ihrerseits die oben belegten Anschlussreviews.

**Prozessproblem:** Issues werden durch `Closes` geschlossen, obwohl manuelle Prüfungen/Interviews oder Akzeptanzkriterien offen bleiben. Gerade #930 H.4 bleibt im Rolloutplan ausdrücklich außerhalb der Implementierung, ohne dass damit das Gesamtziel erfüllt wäre. Das widerspricht der AGENTS-Regel „kein Auto-Close bei externer Restabnahme“. [Closeout-Review](https://github.com/Sturmi77/correlcore/pull/974#discussion_r4070128068).

## Umsetzung gegenüber dem Zielbild
Eine einzelne Prozentzahl würde UI-Vorhandensein, technische Korrektheit und externe Abnahme vermischen. Die folgende Matrix bewertet diese Dimensionen ausdrücklich getrennt.

| Ziel | Implementierungsgrad | Qualität / verbleibende Abnahme |
|---|---|---|
| Tracking-Grundlage, Tags, Symptome, Arbeitskontext, Gewohnheiten und Offline-/Sync-Basis | Weitgehend vorhandene Produktbasis, keine neue bloße Attrappe | Nur geänderte Pfade geprüft; globale Regression/Device-QA nicht vollständig abgenommen. |
| Vier Ebenen: Hub → Detail → Compare → Bericht | Alle vier Oberflächen und wesentliche Datenwege vorhanden | Durchgängige Kontextübernahme, Evidenztreue und Fehlerzustände noch lückenhaft. |
| F1: natürliche Häufigkeiten an der Oberfläche | Teilweise | Verteilungsvergleiche verbessert; Advanced-Symptom-Kookkurrenz bleibt Gegenbeispiel. |
| F2: zeitliche Richtung korrekt unterscheiden | Teilweise | Copy/Utilities vorhanden, pauschaler Detailpfeil verletzt Vertrag. |
| F3: Signal-Detail als sekundäre Route | Implementiert | Kein unnötiger zusätzlicher Hauptscreen; konkrete Detail-Navigation noch testen. |
| F4: adjustierte Effekte hinter Disclosure | Teilweise | Daten/Parser vorhanden, zugesagte Koeffizienten nicht durchgängig sichtbar. |
| F5: Nicht-Ergebnis als echte Antwort | Wesentlich implementiert | `null_association`, Filter/Winner-Korrekturen vorhanden; Persistenz alter Ausblendungen separat offen. |
| F6: Hub reduzieren und Anpassungen erhalten | Teilweise / widersprüchlich | Migration vorhanden, Erhalt kundenspezifischer Enabled-Flags verletzt. |
| Einheitliches ehrliches Analysefenster | Wesentlich implementiert | Request-Races, Persistenz und Short-Window-State verhindern vollständige Abnahme. |
| Bericht für nachvollziehbare Weitergabe | Vier Formate vorhanden | Gruppenevidenz, Auswahlkontext und CSV-Sicherheit fehlen; fachlich noch nicht releasefertig. |
| Belastung/Erholung als verständlicher Bereich | Foundation und Oberflächen vorhanden | Semantik kombinierter Aussagen und Nutzerverständnis noch abzusichern; keine Wirksamkeitsvalidierung. |
| Marker→Tag-Konsolidierung | Code und Migration vorhanden | Release-Upgrade-/Backfill-Nachweis ist hartes Gate (R1). |
| Zielgruppen-/Positionierungsarbeit #930 | Doku erweitert | Interviews H.4 weiter offen; Umsetzung von Text ist keine Nutzervalidierung. |
| M8 / Health Connect | Technische Grundlage und Importpfade vorhanden | Gerätespezifische Integration/Abnahme bleibt außerhalb dieses Audits. |
| M10.2 / Hosted Beta | Umfangreich dokumentiert/technisch vorbereitet | Owner-/Live-Closeout, u. a. #621, nicht durch Codeaudit ersetzt. |
| M11 / Play und Push | Engineering-Pfade vorhanden | Live Firebase/Play-Push-Prüfung #429 weiterhin eigenes Gate. |
| M12 / SaaS | Weiteres Roadmap-Ziel | Billing, vollständiges SaaS-Onboarding, Authentik Phase 2 und zugehörige Betriebsabnahmen nicht abgeschlossen. |
| M13 / Fotos und Medien | EXIF-Strip-Foundation mit Tests vorhanden | `stored:false`-Stub; MinIO-Persistenz/Galerie fehlen weiterhin. Absichtlich später geplant. |

Quellen: [docs/DESIGN_DOCUMENT.md](https://github.com/Sturmi77/correlcore/blob/71d1089ff77388cadf2253ac67d1471dfa99fa40/docs/DESIGN_DOCUMENT.md), [docs/adr/0043-insight-surface-layers.md:170](https://github.com/Sturmi77/correlcore/blob/71d1089ff77388cadf2253ac67d1471dfa99fa40/docs/adr/0043-insight-surface-layers.md#L170), [docs/frontend/INSIGHT_SURFACE_LAYERS_ROLLOUT_PLAN.md](https://github.com/Sturmi77/correlcore/blob/71d1089ff77388cadf2253ac67d1471dfa99fa40/docs/frontend/INSIGHT_SURFACE_LAYERS_ROLLOUT_PLAN.md).

**Gesamtbewertung:** guter Ausbau mit echter Implementierung über alle Schichten; Abschlussqualität und integrierte Abnahme halten mit dem Umfang noch nicht Schritt. Das gilt besonders für bestehende Nutzer beim Upgrade und für die fachliche Bedeutung von Analyseergebnissen.

## Code Quality und Maintainability
**Stärken:** SvelteKit/FastAPI-Trennung bleibt erkennbar; Statistik ist weitgehend in dedizierten Services/Utilities untergebracht. Neue DTOs/API-Typen und viele gezielte Tests sind vorhanden. Owner-Filter, RLS-Kontext und DEK-Aufräumen blieben auf den untersuchten Pfaden erhalten. Escaped Svelte-Interpolation und kontrollierte Detail-IDs reduzieren typische XSS-/IDOR-Risiken. Backfill verwendet keinen durch Nutzereingaben zusammengesetzten Shell-Aufruf.

**Schwächen mit konkreter Wirkung:**
1. Produktverträge sind mehrfach implementiert: Python-/TypeScript-Layoutmigration und getrennte UI-/PDF-/CSV-Modelle. Die festgestellten Abweichungen sind bereits reale Folgekosten.
2. Große Route-Komponenten koordinieren Datenladen, Fensterwahl, Preferences, Selection und Fachzustände gleichzeitig. Race-/Handoff-Fehler sind dadurch schwer isoliert abzusichern.
3. Generische Insight-Payloads verschieben semantische Typprüfung in Parser und UI; OpenAPI-Konformität allein garantiert keine richtige Gruppenevidenz oder Stress-Semantik.
4. Tests prüfen häufig Einzelbausteine oder bestehende Implementierungserwartungen statt Nutzervertrag: falsche Migrationserwartung, Heatmap ohne Elternscreen, Upgrade ab bereits committed 048.
5. Doku-/Issue-Abschluss erfolgt teilweise vor letzter Review-Runde. DESIGN_DOCUMENT führt Exportfunktionen zugleich als umgesetzt und im Backlog; SECURITY.md nennt noch 1.0.x. Das erschwert eine belastbare „Definition of Done“.

**Empfehlung:** keine große Umbauaktion vorziehen. Zunächst gemeinsame fachliche Vertragsfälle definieren und die konkreten Fehler beseitigen; anschließend Exportmodell, Analytics-Ausführung und Fenster-/Request-State an jeweils einer Stelle bündeln.

## Verifikation
| Prüfung | Tatsächliches Ergebnis |
|---|---|
| Backend Ruff Lint | Bestanden |
| Backend Ruff Format | 309 Dateien bereits formatiert |
| Backend volle Pytest-Suite, ohne Coverage | 1.028 bestanden, 2 fehlgeschlagen, 24 übersprungen, 5 Setup-Fehler |
| Gezielter Backend-Rerun mit eigenem Temp-Verzeichnis | 18 bestanden, dieselben 2 Timezone-Fehler; die 5 Temp-Rechte-Setupfehler beseitigt |
| SvelteKit Sync + svelte-check | 0 Fehler, 0 Warnungen |
| Web volle Vitest-Suite | 209 Dateien / 1.326 Tests bestanden; 6 Worker-Start-Timeouts, Exit 1 |
| Sechs betroffene Web-Dateien seriell erneut | Alle 6 bestanden: 89 Tests bestanden, 7 übersprungen, Exit 0 |
| Harmlose CSV-Probe | Formelpräfix unverändert bestätigt |
| Begrenzte Analyseprobe | 60 Tags / 15 Tage / 1.770 Paare: 16,39 s |
| PostgreSQL-/Docker-Upgrade-Test | Nicht ausführbar: lokale Docker-Engine nicht verfügbar |
| Vollständiger Web-Build, reale API-E2E, Android-/manuelle visuelle QA | Nicht durchgeführt |

CI wurde zusätzlich anhand verfügbarer GitHub-Workflows gelesen: für PR #973 Head `9a303566f81945a66e37086bf9c8bad52ccee489` sind API, Web, Contract, CodeQL, Security, Container und DAST erfolgreich. Das ersetzt keinen neu beobachteten vollständigen Lauf am auditierten Merge-Head.

Die vorhandene DAST-Prüfung ist unauthentifiziert und bei inhaltlichen Alerts nicht generell blockierend. Der Container-Scan verwendet `--exit-code 0`; ein grüner Lauf beweist damit nicht „keine kritischen CVEs“. Coverage-Ziele und reale User-Journey-Abnahme sind getrennt zu bewerten.

Reproduktionsrahmen: Python 3.12 aus vorhandener Backend-Venv, Node 22 und vorhandene pnpm-Dependencies; Tests im isolierten Commit-Snapshot. Der normale pnpm-Typecheck wollte Dependencies neu installieren und wurde wegen Nicht-TTY abgebrochen; stattdessen wurden die vorhandenen lokalen Svelte-Binaries direkt verwendet. Shared Dependencies wurden nicht neu installiert.

## Empfohlene Freigabereihenfolge
1. **Upgrade zuerst:** R1 mit echtem v1.9.1-Datenbestand und Wiederanlauf nachweisen.
2. **Security und Nutzerzustand:** S1/S2, Layout-Erhalt und Dismissal-Migration korrigieren.
3. **Fachliche Wahrheit:** Gruppenstärken in Exporten, Stressrichtung, F1/F2/F4 und Short-Window-State abnehmen.
4. **Durchgängige Wege:** Fenster schnell wechseln; Compare→Detail→Bericht; ungültiger Link; Login-Rückkehr; API-Ausfall und Refresh prüfen.
5. **Ein finaler Commit als Freigabekandidat:** Linux-CI, echte DB-Integration und reale Browser-Smokes auf genau diesem Stand. Ausstehende Geräte-/Ops-/Interview-Abnahmen separat mit Verantwortlichen führen.
6. **Review-/Doku-Closeout:** jeden weiterhin relevanten Kommentar auf Fix-Commit + Regressionstest oder begründete Ablehnung abbilden. Erst danach „Abgeschlossen“ und Closing-Keywords verwenden.

## Artefakte
Im selben Verzeichnis: `review-evidence.json` (Kommentar-/PR-Evidenz), `backend-review.json`, `frontend-code-review.json`, `svelte-review.json`, `architecture.json`, `security-candidates.jsonl`, `frontend-csv-probe.cjs/json`.

Der Security-Scan verwendet ID `60b0ed0e-8ee1-4e19-8728-d8b01f78b524`. Ein Writer prüfte zunächst fälschlich Zeilenlängen der abweichenden Arbeitskopie. Die mitgelieferte Normalisierung wurde deshalb gegen den unveränderten Commit-Snapshot ausgeführt; exakte Fundstellen blieben erhalten. Dies ist im Scan-Kontext als Werkzeuggrenze dokumentiert.

## Nachtrag Verifikation
Die sechs beim ersten Lauf nicht gestarteten Web-Testdateien liefen mit `--maxWorkers=1` erfolgreich durch (66,32 Sekunden). Zusammengenommen: 215 Dateien, 1.415 bestandene Tests, 7 übersprungen; kein verbliebener Assertion-Fehler im Web-Rerun. Der erste Gesamtlauf selbst blieb wegen seiner sechs Infrastrukturfehler Exit 1.

Zusätzlicher quelltextlich bestätigter Fensterfehler zu R6: Die Insights-Kookkurrenz bildet 14 Tage über `week` auf `7d` und 28 Tage über `month` auf `30d` ab; `fetchTagCooccurrence` erhält keinen exakten Tages-Override. Die Oberfläche und die API-Auswertung verwenden damit nicht überall das gleiche Fenster. Siehe `trendWindowDays.ts:26`, `analysisRange.ts:17` und `insights/+page.svelte:328` am auditierten Commit. Vor Freigabe die tatsächlichen Start-/Enddaten sämtlicher Analyseaufrufe gegen die gewählte Tageszahl prüfen.

Der Security-Scan wurde erfolgreich validiert und abgeschlossen; das vollständige Bundle liegt unter `security/71d1089ff77388cadf2253ac67d1471dfa99fa40_20260922T093429Z_o8gae66a/`, einschließlich `report.md`, `findings.json`, `coverage.json`, Manifest und SARIF. Die SHA-256-Werte der kopierten Findings-/Coverage-Artefakte stimmen mit dem versiegelten Manifest überein. Gemessene Scan-Tool-Nutzung: 15.467.131 summierte Tokens, davon 14.921.088 gecachte Eingabetokens; diese Summe enthält wiederholt eingelesenen Kontext über mehrere Agenten und ist keine Netto-Kontextgröße. Die separate Goal-Zählung meldet 657.671 Tokens und rund 34 Minuten Laufzeit; beide Zähler haben unterschiedliche Erfassungsbereiche.

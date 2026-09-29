# Zielbild und Umsetzungsplan: verständliche, persönlich relevante Insights

Stand: 29.09.2026. Status: **Vorschlag zur Umsetzung, keine Release-Abnahme**.

Begleitdokumente: [Findings und Entscheidungen](INSIGHT_USER_VALUE_FINDINGS_2026-09-29.md) · [Arbeitsplan und Merge-Strategie](INSIGHT_USER_VALUE_EXECUTION_2026-09-29.md). Die Fragewahl wurde nach dem Nutzerfeedback konkretisiert: mehrere Fragen merken, eine Frage als Fokus; die tatsächlichen Analysefähigkeiten bleiben maßgeblich.

## 1. Produktentscheidung

**CorrelCore hilft mir, eine persönliche Frage zu meinem Alltag zu beantworten: Was zeigen meine Einträge, wie belastbar ist diese Aussage und welche Beobachtung hilft mir als Nächstes?**

Ein erfolgreicher Besuch endet mit Orientierung. Ein weiterer Chart oder ein neuer statistischer Treffer ist dafür weder notwendig noch hinreichend. Eine verständlich begründete offene Frage ist besser als eine scheinbar sichere Antwort.

Das bestehende Vier-Ebenen-Modell bleibt erhalten: **Antwort → Prüfung → vertiefte Analyse → Bericht**. Die Ebenen sind Nutzungssituationen derselben Person. SvelteKit, die bestehenden Routen und das tägliche Check-in bleiben die Grundlage. Keine zusätzlichen Pflichtfelder, keine zusätzliche Hauptnavigation und kein Chatbot sind für dieses Zielbild erforderlich.

### Grundlage und Nachweisgrenze

Der Vorschlag baut auf der Produktbewertung der 17 am 29.09.2026 offenen PRs auf. Für die zentralen PRs #993, #994, #995, #996 und #1001 wurden lokale Remote-Refs mit den aktuellen GitHub-Head-SHAs abgeglichen und relevante Implementierungen gelesen. Ein gemeinsamer Release-Kandidat wurde dabei nicht gebaut oder visuell abgenommen. Vorhandene uncommittete Änderungen sind keine Release-Nachweise.

Die aktuellen PRs bilden die fachliche Grundlage; sie werden nicht durch neue Parallelimplementierungen ersetzt:

| Vorhandene Arbeit                                                                                                                                                                                                                      | Beitrag zum Zielbild                                                          | Noch erforderlicher Nachweis                            |
| -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------- | ------------------------------------------------------- |
| [#993](https://github.com/Sturmi77/correlcore/pull/993), [#994](https://github.com/Sturmi77/correlcore/pull/994)                                                                                                                       | Evidenzverträge, Stressrichtung, Häufigkeiten, Zeitversatz und Kontextprüfung | Gemeinsame Semantik auf allen Oberflächen               |
| [#995](https://github.com/Sturmi77/correlcore/pull/995), [#996](https://github.com/Sturmi77/correlcore/pull/996)                                                                                                                       | Einheitliche Fenster, unveränderte Fragestellung zwischen Ansichten           | Vollständiger Browserweg mit echter API                 |
| [#1001](https://github.com/Sturmi77/correlcore/pull/1001)                                                                                                                                                                              | Gemeinsame Berichtsdaten, Auswahl und Exporte                                 | Visuelle Dateien und Empfängerprogramme                 |
| [#992](https://github.com/Sturmi77/correlcore/pull/992), [#997](https://github.com/Sturmi77/correlcore/pull/997), [#1012](https://github.com/Sturmi77/correlcore/pull/1012)                                                            | Bestehende Präferenzen, Sprachkonsistenz, fehlende Schlafwerte                | Bestandsnutzer- und Eingaberegression                   |
| [#991](https://github.com/Sturmi77/correlcore/pull/991), [#1000](https://github.com/Sturmi77/correlcore/pull/1000), [#1002](https://github.com/Sturmi77/correlcore/pull/1002), [#999](https://github.com/Sturmi77/correlcore/pull/999) | Migration, begrenzte Analyse, technische und externe Abnahme                  | Nachweise am finalen Kandidaten gemäß bestehenden Gates |

Die historischen Desktop-Befunde vom 24.09. sind Regressionseingaben. Sie beweisen nicht, dass die neuen PRs weiterhin dieselben Fehler enthalten.

## 2. Das Erlebnis aus Nutzersicht

### Einstieg: meine Frage statt meiner Statistik

Die Fragewahl ist optional und überspringbar. Beispiele: „Hängt Sport mit meiner Stimmung zusammen?“, „Wie passt mein Schlaf zur Energie am Folgetag?“ oder „Was fällt in meinen Einträgen auf?“ Eine Frage wird aus vorhandenen Faktoren und Zielgrößen zusammengestellt; ihre Formulierung muss keine neue Freitext- oder KI-Funktion sein.

Ich kann **mehrere Fragen merken und eine davon als aktuellen Fokus wählen**. Die eine aktive Frage begrenzt die Startseiten-Darstellung, nicht meine Interessen. Andere Erkenntnisse bleiben zugänglich. Eine technische Höchstzahl gespeicherter Fragen wird erst aus Bedienbarkeit und Rechenbudget abgeleitet und anschließend sichtbar dokumentiert. Gespeicherte Fragen lösen nicht automatisch zusätzliche Vollanalysen aus.

Eine gespeicherte Frage existiert unabhängig davon, ob die Analyse bereits einen Insight erzeugt hat. „Kein passender Insight gefunden“ ist keine Antwort auf die Frage. Bei noch nicht unterstützten Kombinationen erklärt die App ihre Grenze; sie verspricht keine beliebige Analyse.

### Woher Fragen kommen und wie frei sie wählbar sind

| Einstieg                     | Beispiel                                                          | Auswahlregel                                                                                                  |
| ---------------------------- | ----------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------- |
| Passenden Vorschlag wählen   | „Hängt Sport mit deiner Stimmung zusammen?“                       | Vorhandene Faktoren und Messgrößen, unterstützte Verfahren; ein statistischer Treffer ist keine Voraussetzung |
| Beobachtung weiterverfolgen  | Aus einem Insight oder Trendvergleich „Diese Frage merken“ wählen | Faktor, Ziel, Zeitbezug und Kontext unverändert übernehmen                                                    |
| Eigene Frage zusammenstellen | „Wie hängt [Spaziergang] mit [Stress] [am selben Tag] zusammen?“  | Strukturierter Baukasten aus vorhandenen, auch selbst erstellten Tags und unterstützten Messgrößen            |

Vorschläge kommen aus einem kleinen fachlich geprüften Vorlagenkatalog, der auf die im Konto verfügbaren Faktoren abgebildet wird. Der Katalog umfasst auch Fragen mit fehlenden Daten und ohne gefundenes Muster. Er wird weder aus Klickhäufigkeit noch ausschließlich aus statistischen Treffern abgeleitet. Ohne passende Daten zeigt die Vorschau die Datenlücke, bevor die Frage als Fokus gespeichert wird.

Der erste Vorschlagsumfang wird anhand der bestehenden Zielgruppen und ihrer Alltagssituationen in Z1 geprüft. Jede Vorlage besitzt Faktorart, Zielart, erlaubten Zeitbezug, unterstützte Methode, lokalisierte Formulierung und Datenanforderungen. Automatisch vorgeschlagene Fragen verändern keine Tags oder Einträge.

| Frei wählbarer Teil                                                                         | Grenze im ersten Ausbau                                                                                                           |
| ------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------- |
| Aktivitäten, eigene Tags, Symptome, Arbeitssituation und unterstützte Messgrößen wie Schlaf | Nur Kombinationen, für die eine geprüfte Methode existiert; eigene Tags sind möglich, beliebige neue Messverfahren nicht          |
| Zielgröße, etwa Stimmung, Energie oder Stress                                               | Unterstützte Ziele werden aus einer expliziten Fähigkeitsliste angeboten                                                          |
| Zeitbezug                                                                                   | Nur die für das gewählte Paar unterstützten gleichzeitigen oder verzögerten Varianten; Nacht-/Tageszuordnung aus dem Datenvertrag |
| Zeitraum                                                                                    | Bestehende 14/28/90 Tage; optionaler Parameter, kein Pflichtschritt beim Einstieg                                                 |
| Kontextprüfung                                                                              | In der vertieften Prüfung, sofern Daten und Methode sie tragen                                                                    |
| Persönliche Formulierung                                                                    | Optionaler privater Titel/Notiz; keine automatisch ausführbare Freitextanalyse                                                    |

Die Vorschau unterscheidet **unterstützt und auswertbar**, **unterstützt mit fehlenden Daten** und **methodisch nicht unterstützt**. Im zweiten Fall bleibt Speichern möglich, mit konkretem Datenstatus. Im dritten Fall bietet die App eine unterstützte Alternative an; die ursprüngliche Formulierung kann als private Notiz erhalten bleiben, gilt aber nicht als aktiv analysierbare Frage.

„Warum bin ich montags erschöpft?“ kann beispielsweise als Ausgangspunkt dienen. Unterstützte Prüfungen wie Schlaf ↔ Energie oder Montag ↔ andere Wochentage werden nur dann angeboten, wenn die Fähigkeitsliste sie tatsächlich enthält. Der Nutzer bestätigt die konkrete Vergleichsfrage; die App behauptet damit keine vollständige Ursachenklärung.

Für gespeicherte Fragen sind Umbenennen, Fokus wechseln, Archivieren und Löschen vorgesehen. Ein privater Titel verändert keine Analyseparameter. Ein Wechsel von Faktor, Ziel oder Zeitbezug erzeugt eine neue Frageidentität; frühere Antworten werden nicht rückwirkend umgedeutet. Entfernte Faktoren behalten einen erklärbaren historischen Status, bis die Frage gelöscht wird.

### Heute: eine Antwort mit einem klaren Weg zur Prüfung

Die Startseite zeigt den Check-in und höchstens eine führende Antwort. Die Erkenntnisse-Seite zeigt die aktive Frage und bis zu zwei weitere unterschiedliche Hinweise; weitere Ergebnisse sind auf Wunsch erreichbar. Diese Mengen sind Startwerte für den Nutzertest.

**Synthetisches Darstellungsbeispiel, kein echter Nutzerbefund:**

> **An Tagen mit Sport war deine Stimmung häufiger gut.**
>
> 7 von 10 Tagen mit Sport · 7 von 18 Tagen ohne Sport
>
> 1.–28. September · 28 vergleichbare Tage · „gut“ = Stimmung 4 oder 5
>
> Deine Einträge zeigen einen Unterschied, aber noch keine Ursache.
>
> **Antwort prüfen**

Ob dieses Beispiel ein berichtbares Muster ergibt, entscheiden die validierten Analysebedingungen, nicht die Gestaltung oder diese Beispielzahlen. Die Unsicherheitszeile benennt im echten Produkt den tatsächlich belegten Vorbehalt.

Gestaltungsregeln:

- Der verständliche Satz ist die Überschrift. Roh-Keys, Koeffizienten und Pfeilpaare sind keine primäre Botschaft.
- Eine kompakte Evidenzzeile und der relevante Vorbehalt bleiben sichtbar. Methodendetails öffnen sich auf Nachfrage.
- Eine primäre Aktion führt zur Detailprüfung. Ausblenden und Frage wechseln sind sekundäre Aktionen.
- Farbe unterstützt die Bedeutung; Text und Symbole tragen sie auch ohne Farbe. Stress wird überall ausdrücklich als mehr/weniger Stress beschrieben.
- Lange Faktoren und deutsche Sätze umbrechen. Aussage, Unsicherheit und primäre Aktion werden nicht abgeschnitten.
- Veraltete Ergebnisse tragen einen sichtbaren Stand. Ladefehler verdrängen keinen vorhandenen Befund durch eine vermeintlich neue Antwort.

### Detail: erst Bedeutung, dann Zahlen

Die Detailansicht beantwortet in dieser Reihenfolge:

1. **Was wurde beobachtet?** Derselbe Satz wie auf der Karte, mit derselben Frage und Zeitbasis.
2. **Wie groß ist der Unterschied?** Häufigkeiten beziehungsweise ein Unterschied in verständlichen Einheiten. Eine Korrelation von 0,4 ist kein Unterschied von 0,4 Skalenpunkten.
3. **Worauf beruht das?** Gruppengrößen, tatsächliche Datumsgrenzen, fehlende Messwerte, Verteilungen und Überlappung. Tage und Einträge werden getrennt benannt.
4. **Was könnte ebenfalls eine Rolle spielen?** Zum Beispiel Arbeitssituation, Wochentag oder wenige Vergleichstage. Verfügbare Kontextprüfungen werden in einem Satz erklärt; Koeffizienten stehen darunter.
5. **Was hilft als Nächstes?** Genau ein vorrangiger, zur Datensituation passender Schritt. Weitere Analyse und Bericht bleiben sekundär erreichbar.

Beispiel bei belegter Abschwächung: „Wenn wir ähnliche Arbeitstage vergleichen, fällt der Unterschied kleiner aus.“ Fehlt eine solche Berechnung, darf die App diesen Satz nicht erzeugen. Ein statistisch berücksichtigter Faktor ist kein Nachweis gleicher Lebensbedingungen oder einer Ursache.

Bei Zeitversatz werden Ausgangsgröße, Zielgröße und Reihenfolge ausgeschrieben: „Schlaf in der Nacht vor dem Eintrag und Energie am folgenden Tag“. Die genaue Zuordnung folgt dem vorhandenen Schlafdatenvertrag; die Oberfläche darf Nacht- und Tagesbezug nicht selbst erfinden.

### Wiederkehr: dieselbe Frage weiterverfolgen

Die aktive Frage behält ihren Platz, auch wenn kein klares Muster vorliegt. Nach einem neuen Analyselauf zeigt die App eine Änderung nur, wenn sie fachlich nachvollziehbar ist. Ein neuer Laufzeitstempel allein ist keine neue Erkenntnis.

Zuerst wird ein deterministischer Vergleich derselben Frage, Methode und Fensterdefinition umgesetzt. Geänderte Datengrundlagen werden genannt. Überlappende rollierende Zeitfenster sind keine unabhängige Bestätigung. Nach Methodenänderungen beginnt ein neuer Vergleichsstand; die App behauptet keine Veränderung des Menschen.

„Weiter beobachten“ speichert die Frage und ihren letzten betrachteten Analysestand. Es erzeugt keine tägliche Pflicht, keinen Streak und keine automatische Push-Serie. Eine Nutzerwahl zur Sichtbarkeit beeinflusst die Priorisierung, niemals den statistischen Befund.

### Bericht: eine verständliche Antwort zum Mitnehmen

PDF und PNG beginnen mit Frage, Antwort, Zeitraum und wesentlicher Einschränkung. Die Evidenztabelle folgt. CSV und JSON erhalten dieselben fachlichen Werte in strukturierten Spalten/Feldern; sie müssen nicht dieselbe visuelle Form haben.

Ein Nicht-Ergebnis ist auf ausdrückliche Auswahl berichtbar, sofern die Analyse es trägt. Fehler und fehlende Analysen werden nicht als Nicht-Ergebnisse exportiert. Bei ausdrücklich gewünschtem Datenstatus-Bericht muss der Status sichtbar als solcher benannt sein. Ein ungültiger Link darf niemals andere Ergebnisse auswählen.

## 3. Aussage und Verfügbarkeit getrennt modellieren

Die folgenden Zustände sind Zielsemantik. Ihre Zuordnung zu bestehenden Engine-Ergebnissen wird in Arbeitspaket Z1 festgelegt und getestet. Neue statistische Nachweise werden nicht aus vorhandenen UI-Labels abgeleitet.

| Zustand                     | Verständliche Aussage                                      | Passender nächster Schritt                                                             |
| --------------------------- | ---------------------------------------------------------- | -------------------------------------------------------------------------------------- |
| Datenbasis reicht nicht     | „Für deine Frage fehlen bisher Vergleichstage ohne Sport.“ | Vorhandene Datenabdeckung ansehen; Erfassung bei passenden Alltagstagen erläutern      |
| Noch unklar                 | „Die bisherigen Daten lassen mehrere Deutungen zu.“        | Unsicherheit und Verteilung ansehen; Frage weiterverfolgen                             |
| Muster beobachtet           | „An Tagen mit X lag Y häufiger/höher/niedriger …“          | Vergleich und mögliche weitere Faktoren prüfen                                         |
| Kein klares Muster gefunden | „In diesem Zeitraum zeigt sich kein klarer Zusammenhang.“  | Frage behalten oder andere Frage wählen; keine Aufforderung, bis zum Treffer zu suchen |

Zusätzliche Informationen wie „wenige Vergleichstage“, „Arbeitssituation könnte mitwirken“ oder „älterer Analysestand“ sind begründete Eigenschaften der jeweiligen Antwort. Sie ersetzen den fachlichen Zustand nicht.

Unabhängige technische Zustände: lädt, aktuell verfügbar, älterer Stand, Analyse ausgeschaltet, Kombination nicht unterstützt, Budgetlimit, vorübergehend nicht verfügbar. Ein Timeout wird niemals zu „kein Muster“.

**Kein klares Muster ist kein Beweis fehlender Wirkung.** Ein nicht signifikanter oder kleiner geschätzter Effekt reicht nicht für „X macht keinen Unterschied“. Eine stärkere Aussage über einen praktisch vernachlässigbaren Effekt setzt eine begründete Relevanzgrenze und einen geeigneten Unsicherheitsnachweis voraus; sie gehört nicht automatisch zum ersten Ausbau.

**Datenreife ist keine Sicherheit pro Frage.** 100 erfasste Tage können nur zwei vergleichbare Tage für eine konkrete Frage enthalten. Die Kontoreife dient der Orientierung über verfügbare Funktionen; sie darf ein einzelnes Ergebnis nicht als „bestätigt“ etikettieren. Konfidenzwerte werden nicht als Wahrscheinlichkeit dargestellt, dass eine Behauptung wahr ist.

## 4. Persönliche Relevanz ohne Verfälschung der Analyse

### Priorisierung in zwei Schritten

**Schritt 1: fachliche Zulässigkeit.** Engine, Datenqualität, unterstützte Methode, Datenschutz- und Budgetregeln entscheiden, welche Aussagen möglich sind. Keine Rangfolge kann fehlende Evidenz ersetzen. Ein Datenstatus zur aktiven Frage bleibt sichtbar, auch wenn kein Ergebnis zulässig ist.

**Schritt 2: Auswahl der sichtbaren Antworten.** Eine explizite, nachvollziehbare Reihenfolge ersetzt einen universellen Effektstärke-Score:

1. Aktive persönliche Frage einschließlich ihres Nicht-Ergebnisses oder offenen Datenbedarfs.
2. Fachlich relevante Veränderung einer bereits betrachteten Antwort, sofern vergleichbar und nachvollziehbar.
3. Weitere zulässige Hinweise, nach Evidenzqualität und innerhalb vergleichbarer Methoden nach Effektgröße geordnet.

Ähnliche Varianten derselben Frage werden gruppiert; gleichzeitige und zeitversetzte Befunde bleiben unterscheidbar. Ein Grenzwechsel zwischen zwei nahezu gleichen Scores darf die Hauptkarte nicht bei jedem Reload austauschen. Regeln und Gleichstandsauflösung sind versioniert und deterministisch.

Auf Wunsch erklärt „Warum sehe ich das?“ den konkreten Grund: „Du verfolgst diese Frage“, „Die Datengrundlage hat sich geändert“ oder „Ein weiterer Hinweis aus deinen Einträgen“. Kein verborgenes Persönlichkeitsprofil, keine Ableitung aus Klickhäufigkeit.

Ohne Fragewahl funktioniert die bisherige automatische Entdeckung weiter. Der erste Ausbau priorisiert vorhandene Ergebnisse und Datenstatus; er führt keine unbeschränkte Berechnung aller Wunschkombinationen ein.

### Nächster Schritt als begründete Entscheidung

Eine kleine, übersetzte Regelbibliothek liefert Aktion und Begründung aus dem Evidenzvertrag:

| Belegter Grund                 | Beispiel                                                          | Grenze                                                                                     |
| ------------------------------ | ----------------------------------------------------------------- | ------------------------------------------------------------------------------------------ |
| Eine Gruppe fehlt/ist zu klein | „Bisher gibt es nur zwei vergleichbare Tage ohne diesen Tag.“     | Keine Empfehlung, Schlaf, Medikamente oder andere Gesundheitsfaktoren gezielt zu verändern |
| Kontextprüfung verfügbar       | „Vergleiche Tage mit derselben Arbeitssituation.“                 | Nur anbieten, wenn Daten und Methode diese Prüfung tragen                                  |
| Hohe Unsicherheit              | „Behalte die Frage im Blick; die bisherigen Werte streuen stark.“ | Kein Versprechen, nach X weiteren Tagen sicher zu sein                                     |
| Kein klares Muster             | „Du kannst diese Frage weiterverfolgen oder eine andere wählen.“  | Kein automatisches Durchprobieren von Fenstern bis zu einem Treffer                        |
| Ergebnis für Gespräch relevant | „Nimm Frage und Vergleich als Bericht mit.“                       | Keine diagnostische Schlussfolgerung                                                       |

Die Wahl eines anderen Zeitfensters bleibt in der Analyse möglich. Der Wechsel verändert sichtbar die Fragebasis; ein günstigeres Fenster ist kein stärkerer Beweis.

## 5. Gemeinsamer fachlicher Vertrag

Auf den Evidenzverträgen aus #993 und dem Berichtmodell aus #1001 aufbauen. Vorgeschlagene Ergänzungen, nicht bereits existierende API-Felder:

| Teil           | Inhalt und Verantwortung                                                                                                                    |
| -------------- | ------------------------------------------------------------------------------------------------------------------------------------------- |
| Frageidentität | Stabile Faktor-/Ziel-IDs, Arten, Kontext, signierter Lag und Fensterregel; bestehende Paaridentität aus #996 wiederverwenden                |
| Analysestand   | Ergebnis-ID, tatsächlicher Beginn/Ende, Erzeugungszeit, Daten- und Methodenversion; historisch fehlend bleibt unbekannt                     |
| Evidenz        | Fachlicher Zustand, begründende Codes, Effekt plus Einheit, Unsicherheit soweit berechnet, Gruppen/Paare, fehlende Werte, geprüfte Kontexte |
| Darstellung    | Lokalisierte Satzbausteine, Evidenzzeile, Einschränkung und zulässige Aktion; kein freies Generieren statistischer Aussagen                 |
| Nutzerwahl     | Aktive Frage, zuletzt betrachteter Stand, explizite Ausblendung; getrennt von wissenschaftlicher Evidenz                                    |

Gruppengrößen gelten nur für passende Verfahren. Lag-Analysen verwenden die Zahl tatsächlich gepaarter Beobachtungen; ein zusammengesetzter Belastungshinweis darf keine gemeinsame Tagesbasis vortäuschen, wenn seine Komponenten getrennte Abdeckungen haben.

Das Backend verantwortet Aussagezustand und Gründe. Eine gemeinsame Frontend-Projektion übersetzt diese in DE/EN und versorgt Heute, Karten, Details und Bericht. Der Digest verwendet dieselben Prioritätsregeln beziehungsweise gemeinsame Vertragsfixtures, statt unabhängig nur große Effekte auszuwählen. Der vorhandene Mindestumfang von drei Digest-Ergebnissen wird überprüft: eine hilfreiche Antwort sollte als einzelne Antwort möglich sein.

Gespeicherte Fragen werden serverseitig pro Konto gehalten, mit kontrolliertem lokalem Cache. Kontowechsel, Offline-Änderungen, Löschung, Export, entfernte Tags und umbenannte Faktoren erhalten explizite Regeln. Fällt die neue Priorisierung aus, bleiben vorhandene Ergebnisse sichtbar; die Frage bleibt gespeichert. Methodische Änderungen werden dadurch nicht zurückgerollt.

## 6. Umsetzung in überprüfbaren Paketen

Aufwand: vorläufige Größenordnung für eine Person mit Kenntnis des Repos, einschließlich gezielter Tests und Review. Keine Terminzusage; bestehende PR-Konflikte, unbekannte Statistiklücken und externe Abnahmen können Zusatzaufwand erzeugen. Gerätezugang und sechs Testpersonen ab Z0 organisieren.

| Paket                                       | Ergebnis                                                                                                             | Betroffene Stellen / Anschluss                                                                                         | Abnahme                                                                                                                                                                     | Aufwand                                   |
| ------------------------------------------- | -------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------- |
| **Z0 – Gemeinsame Grundlage**               | Einen Kandidaten aus den bestehenden PRs zusammenführen, Identität fixieren, offene Gates zuordnen                   | Bestehende A00–A12-Arbeit, PR #1012/#1013; keine erneute Umsetzung der Fixes                                           | Die fünf unten genannten Kernwege laufen gegen dieselben Images; verbleibende Blocker haben Verantwortliche und Nachweise                                                   | 2–4 Tage, Integration kann mehr benötigen |
| **Z1 – Antwortsemantik und Prototyp**       | Zustände, Gründe, Satzmuster und sechs klickbare Szenarien; zwei frühe Verständnistests                              | ADR-0043 ergänzen; `INSIGHT_STATEMENT_PATTERN.md`, `INSIGHT_MATURITY.md`, `InsightEvidence.svelte`, Engine-Verträge    | Fragebezogene Evidenz von Kontoreife getrennt; keine Gleichsetzung von Fehler, Nicht-Ergebnis und fehlenden Daten; Schwellen und Verfahren vor Implementierung dokumentiert | 3–5 Tage                                  |
| **Z2 – Eine verständliche Antwort überall** | Gemeinsame Darstellung und begründete nächste Schritte auf Heute, Karte und Detail; passende Berichtszusammenfassung | `HomeDailyBrief.svelte`, `InsightCard.svelte`, `MobileInsightLead.svelte`, Signalroute, DE/EN, Berichtmodell aus #1001 | Identische fachliche Antwort und Einheiten auf allen Oberflächen; lange Texte, Stress und historische Payloads geprüft                                                      | 4–6 Tage                                  |
| **Z3 – Meine Frage verfolgen**              | Optionaler Fragenaufbau, Persistenz, Priorisierung, sichtbares Nicht-Ergebnis, „Warum sehe ich das?“                 | Paaridentität aus #996, Präferenzen/API, `insightRanking.ts`, `insight_service.py`, Analysebudget aus #1000            | Persönliche Frage bleibt bei fehlendem Insight sichtbar; Speichern/Neuladen/Kontowechsel funktionieren; automatischer Modus bleibt nutzbar                                  | 5–8 Tage                                  |
| **Z4 – Wiederkehr und Mitnehmen**           | Vergleichbare Änderungen erklären, Bericht über Antworttypen hinweg, Digest auf gleiche Regeln ausrichten            | Analysestand, Report/Export, `insight_digest.py`, vorhandener Digest-Worker                                            | Keine Neuigkeitsbehauptung aus neuem Zeitstempel; Nicht-Ergebnis exportierbar; ein hilfreiches Digest-Ergebnis möglich; Fenster-/Methodenwechsel offengelegt                | 4–7 Tage                                  |
| **Z5 – Abnahme und gestufter Rollout**      | Sechs Nutzertests, reale Geräte-/Browserwege, Dateiprüfung, Befunde korrigieren und nachtesten                       | Vorhandene A10/A12-Gates, `docs/quality/TESTING.md`, E2E-Suite                                                         | Kriterien aus Abschnitt 7 erfüllt, keine offenen kritischen Missverständnisse oder falschen Evidenzaussagen                                                                 | 3–5 Tage plus externe Wartezeit           |

**Summe: grob 21–35 Arbeitstage**, zuzüglich externer Wartezeiten und größerer Integrations-/Statistikarbeiten. Nach Z1 neu schätzen. Falls die Engine die erforderliche Zustandssemantik nicht liefern kann, wird der Umfang sichtbar reduziert oder ein eigenes Methodenpaket ergänzt; die Oberfläche simuliert keinen Nachweis.

Reihenfolge: **Z0 → Z1 → Z2 → Z3 → Z4 → Z5**. Prototyp-Vorbereitung und Rekrutierung können während Z0 beginnen. Frühe Tests können spätere Arbeit verändern; sie sind keine zusätzliche Endabnahme derselben unveränderten Oberfläche.

### Sinnvolle Release-Schnitte

- **R0 – Vertrauenswürdige Basis:** Bestehende Fix-PRs plus Z0, sofern die bestehenden Release-Gates erfüllt sind. Keine Behauptung, das vollständige Zielbild sei erreicht.
- **R1 – Verständliche persönliche Antworten:** Z1–Z3 plus die dafür relevanten Z5-Abnahmen. Das ist der kleinste Release, der die wichtigsten Produktlücken adressiert.
- **R2 – Kontinuität und vollständige Weitergabe:** Z4 plus restliche Z5-Abnahme. Keine neue Analysefläche nur zur Erfüllung des Plans.

Neue Priorisierung zunächst als deaktivierbare Fähigkeit auf einem isolierten Teststand, dann in einer bewusst ausgewählten Beta. Vor dem breiteren Rollout denselben Kandidaten abnehmen. Bei Fehlverhalten kann die Priorisierung zurückgestellt werden, ohne Evidenzfixes oder gespeicherte Fragen zu verlieren.

### Erste umsetzbare Tickets

Die Kennungen sind lokale Plan-IDs, keine angelegten GitHub-Issues.

| ID   | Auftrag                                                                                                          | Abhängigkeit       |
| ---- | ---------------------------------------------------------------------------------------------------------------- | ------------------ |
| Z1.1 | Bestehende Evidenzfelder auf die vier Aussagezustände abbilden; fehlende Gründe und Methodenlücken dokumentieren | Z0-Bestand         |
| Z1.2 | Fragebezogene Evidenzsprache und Vorbehalte in DE/EN definieren; Kontoreife getrennt darstellen                  | Z1.1               |
| Z1.3 | Sechs Szenarien prototypisieren und mit zwei Personen früh testen                                                | Z1.2               |
| Z2.1 | Gemeinsame Präsentationsprojektion samt API→UI-Vertragsfixtures implementieren                                   | Z1-Abnahme         |
| Z2.2 | Heute/Karte/Detail auf Satzhierarchie und begründete Aktion umstellen                                            | Z2.1               |
| Z2.3 | Bericht mit Frage, Aussage, Einschränkung und identischer Evidenz ergänzen                                       | Z2.1, #1001        |
| Z3.1 | Stabile Frageidentität und kontoabhängige Speicherung einschließlich Lifecycle implementieren                    | #996, Z1           |
| Z3.2 | Deterministische Priorisierung und Gruppierung, aktive Frage ohne Treffer erhalten                               | Z3.1, Z2.1         |
| Z4.1 | Vergleichbare Analysestände und begründete Änderungsanzeige implementieren                                       | Z3.2               |
| Z4.2 | Digest und Nicht-Ergebnis-Berichte an dieselben Regeln anbinden                                                  | Z4.1, Z2.3         |
| Z5.1 | Gesamtabnahme mit Fixtures, Geräten, Dateien und sechs Personen protokollieren                                   | Je Release-Schnitt |

Produktverantwortung: Repo-Owner entscheidet Scope und Sprachvertrag. Entwicklung verantwortet Verträge und Umsetzung; die Analytics-Verantwortung bestätigt methodische Zuordnungen. QA dokumentiert denselben Kandidaten. Dieselbe Person kann mehrere Rollen übernehmen; die sechs Nutzertests benötigen externe Teilnehmer. Offene externe Gates bleiben in #984/#986 und bestehenden Trackern sichtbar. Closing-Keywords erst bei tatsächlich vollständiger Abnahme gemäß AGENTS.md.

## 7. Abnahme: Nutzen und Richtigkeit getrennt prüfen

### Fünf verbindliche Nutzerwege

| Weg                   | Konkrete Prüfung                                                                 | Erfolg                                                                        |
| --------------------- | -------------------------------------------------------------------------------- | ----------------------------------------------------------------------------- |
| Wenige Daten          | Frage wählen, nur eine kleine Vergleichsgruppe verfügbar                         | App benennt den konkreten Datenbedarf; niemand bekommt eine fingierte Antwort |
| Beobachtetes Muster   | Heute → Karte → Detail → Kontextprüfung                                          | Aussage, Richtung, Gruppen, Einheit und Zeitraum bleiben fachlich identisch   |
| Kein klares Muster    | Persönliche Frage ohne klares Ergebnis erneut öffnen                             | Frage bleibt auffindbar; Text behauptet keinen bewiesenen Nulleffekt          |
| Vollständige Übergabe | Trends → Insights → Detail → Bericht, einschließlich Reload und Zurück/Vorwärts  | Faktor, Ziel, Lag, Kontext, Fenster und Auswahl bleiben erhalten              |
| Smartphone und Datei  | Antwort auf echtem Telefon prüfen, PDF/PNG und CSV/JSON derselben Auswahl öffnen | Keine abgeschnittene Kernaussage; vollständige und gleiche fachliche Evidenz  |

### Gezielte Daten- und Zustandsfixtures

- 0 Tage, wenige Tage, viele Tage mit nur zwei Tagen in einer Vergleichsgruppe sowie 5/95-Gruppen.
- Bekannter positiver/negativer Zusammenhang, hohe Streuung und kein klares Muster; erwartete Werte vorab aus Rohdaten dokumentieren.
- Stress-Rohwerte, fehlende Schlafqualität, positive und negative Lags, ungleiche Abdeckung der Belastungskomponenten.
- Zusammenhang, der bei einer verfügbaren Kontextprüfung schwächer wird; fehlende Kontextprüfung darf dieselbe Aussage nicht erhalten.
- Historische Payload ohne neue Felder, gelöschter Faktor, umbenannter Faktor, bereits ausgeblendetes Signal.
- Schneller 14/28/90-Tage-Wechsel, Methodenversion gewechselt, Offline-Stand, Timeout, Opt-out und Budgetlimit.
- Kontowechsel, ungültiger Berichtlink, bewusst leere Auswahl und fehlgeschlagener Refresh.

Methoden-/Rangfolgelogik mit fokussierten Unit- und Vertragsprüfungen absichern; Persistenz mit echter DB; die fünf kritischen Wege mit echter API. Mock-Smokes bleiben ergänzend. CSV-Empfängerprüfung und PDF-/PNG-Sichtprüfung übernehmen die bestehenden A05/A10/A12-Anforderungen. Keine Scheintests, die lediglich einen Implementierungswert nochmals als Erwartung eintragen.

### Vorgeschlagene Produktkriterien

Diese Werte sind **Abnahmeziele**, keine bereits gemessenen Ergebnisse und keine statistisch repräsentative Marktvalidierung.

| Kriterium                   | Ziel und Messung                                                                                                                                                                                           |
| --------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Orientierung                | Mindestens 5 von 6 Personen finden in höchstens 15 Sekunden die Antwort auf ihre Frage und können sie sinngemäß wiedergeben                                                                                |
| Evidenzverständnis          | Mindestens 5 von 6 nennen Zeitraum, Vergleich und wichtigsten Vorbehalt ohne Hilfestellung                                                                                                                 |
| Nächster Schritt            | Mindestens 5 von 6 können die angebotene Aktion und ihren Zweck erklären                                                                                                                                   |
| Kritische Missverständnisse | Nach Nachtest 0 ungelöste Fälle von „Ursache bewiesen“, „kein Einfluss bewiesen“ oder „100 Tage machen jede Frage sicher“                                                                                  |
| Aufgabenabschluss           | Mindestens 5 von 6 schaffen Frage → Prüfung → passenden Bericht ohne Moderatorhilfe                                                                                                                        |
| Fachliche Konsistenz        | Alle definierten Vertragsfixtures stimmen über Karte, Detail und exportierte Werte überein; 0 bekannte falsche Kernaussagen                                                                                |
| Darstellung                 | 320/375/390 CSS-Pixel sowie Desktop, DE/EN, hell/dunkel, 200 % Textvergrößerung; keine abgeschnittenen Kernaussagen/Aktionen. Dichte Tabellen dürfen einen bewusst bedienbaren eigenen Scrollbereich haben |
| Bedienbarkeit               | Kritische Wege per Tastatur und mit benannten Screenreader-Labels; reale Android-/Browserprüfung gemäß unterstütztem Produktscope                                                                          |

Zwei frühe Tests in Z1 dienen der Korrektur. Die finale Runde umfasst sechs Personen aus den bestehenden Zielgruppen; möglichst mindestens vier haben die Prototypen nicht vorher gesehen. Ergebnisse als konkrete Anzahlen und Beobachtungen dokumentieren. Kleine Stichproben entdecken Verständnishürden, belegen aber keine allgemeine Erfolgsquote.

Messung zunächst in moderierten Sitzungen mit synthetischen Daten. Keine neue Telemetrie für Gesundheitsinhalte oder persönliche Fragen. Time-to-First-Answer bleibt Produktziel, darf aber keine fachlich ungedeckte Antwort vor Tag 14 erzwingen. Ein hilfreicher Datenstatus wird getrennt von einer analytischen Antwort gemessen.

## 8. Dokumentationsentscheidungen und Risiken

Vor der Umsetzung einen ADR-Nachtrag für persönliche Frage, Priorisierung und Evidenzsprache erstellen. Danach die folgenden Dokumente synchronisieren; dieses vorgeschlagene Zielbild ersetzt sie nicht stillschweigend:

- [DESIGN_DOCUMENT.md](../DESIGN_DOCUMENT.md): Nutzenversprechen auf beobachtete Zusammenhänge und Orientierung präzisieren; „warum“ nicht als Kausalitätszusage verwenden.
- [ADR-0043](../adr/0043-insight-surface-layers.md): Vier Ebenen beibehalten, persönliche Frage und Ergebniszustände ergänzen.
- [INSIGHT_STATEMENT_PATTERN.md](INSIGHT_STATEMENT_PATTERN.md): Aussagehierarchie übernehmen; die historische Bewertung der Effektstärke-Rangfolge als „bereits richtig“ für den neuen Scope ersetzen.
- [INSIGHT_MATURITY.md](INSIGHT_MATURITY.md): Kontoreife und Einzelfrage trennen; historische „Confirmed“- und Feier-/Fortschrittsvorgaben mit Evidenzsprache und No-Gamification-Prinzip abgleichen.
- [Arbeitsmuster-Vokabular](../features/arbeitsmuster-vokabular.md): bestehende Grenzen beibehalten, alltagstaugliche Kontextformulierungen ergänzen.
- [TESTING.md](../quality/TESTING.md): tatsächlich implementierte Release-Gates aus den Audit-PRs und die neuen Abnahmen konsistent dokumentieren.

Größte Risiken sind widersprüchliche Zusammenführung überlappender PRs, unzureichende Engine-Gründe für verständliche Aussagen und eine zu komplizierte Fragewahl. Gegenmaßnahmen: gemeinsamer Kandidat vor Abnahme, explizite Methodenlücken in Z1 und frühe Nutzertests vor Persistenz-/Ranking-Ausbau.

Weitere Charts, KI-Erklärungen, ein Experiment-Coach und zusätzliche Benachrichtigungen sind für die ersten Release-Schnitte nicht eingeplant. Priorität haben die überprüfbare Antwort, ihre persönliche Relevanz und der geschlossene Nutzerweg.

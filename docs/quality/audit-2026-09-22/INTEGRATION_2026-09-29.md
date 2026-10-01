# Gemeinsame Integration der Insight-Basis

Stand: 29.09.2026. Basis: `7e59ba5a1c9b46c89511d6c706a30cf61809122f`.

Die Integration vereint #990–#1002, #1012, #1013 und #1014. Die Dependency-PRs #1008 und #1009 bleiben separat. Die ursprünglichen Branch-Heads bleiben durch Merge-Commits nachvollziehbar. Der vorhandene Arbeitsstand außerhalb dieses isolierten Worktrees wurde nicht übernommen.

## Konfliktauflösung und Review-Befunde

- A01/A10: automatische Erkennung der Integrationstestmodule erhalten; die an Revision 048 gebundene Legacy-Suite bleibt vom Head-Lauf ausgeschlossen. Die direkten Upgrade-Regressionen laufen weiterhin gegen PostgreSQL. Ein Downgrade ist kein Ersatz für den operativen Backup-/Restore-Nachweis.
- A02/A07: Ressourcenlimits und explizite Überlastungszustände mit exakten 14-/28-/90-Tage-Fenstern vereinigt. Lade-, Fehler-, Opt-out- und unzureichende Datenzustände bleiben getrennt. Fensterlänge und erfasste Tage bleiben auch in Abbruch- und Leerantworten erhalten. Beschäftigte, abgebrochene oder vorübergehend unerreichbare Analysepanels bieten einen direkten Wiederholungsweg, ohne die Backend-Ressourcenbegrenzung aufzuheben.
- A07/A08: strukturierte Paaridentität, Nutzerwechsel, Präferenzladen und Request-Abbruch gemeinsam erhalten. Veraltete Antworten dürfen den neuen Kontext nicht überschreiben. Ein noch ablaufender Schreibvorgang des alten Kontos verhindert nicht mehr das Laden der Präferenz des neuen Kontos. Alte untypisierte Paar-Links werden ohne ungültige Serverfilter im geladenen Feed gesucht; bei fehlendem Treffer wird die Begrenzung erklärt und auf eine gezielte neue Auswahl verwiesen.
- A04/A05/A06: ein gemeinsamer Reportvertrag trägt Rohkoeffizient, Anzeigekoeffizient und tatsächliche Beziehungsendpunkte. PDF-Zeilen werden umgebrochen; Richtungspfeile werden im WinAnsi-PDF verlustfrei als ASCII dargestellt. Matrix/Report unterscheiden Lag-Endpunkte und Symptom/Tag-Paare.
- A04: neue Belastungs-Payloads speichern die vor Rundung berechneten Bedingungen. Historische, nur gerundet gespeicherte Werte lösen in der unsicheren Grenzzone keine neue Änderungsbehauptung aus. Textmittelwerte neben dem Stress-Scatter folgen dessen Anzeigeskala.
- A06: historische Metrik `mood` bleibt verifizierbar. Adjustierte Koeffizienten bleiben in der Detailansicht, nicht in der Layer-1-Karte.
- A00/A11: CSV-Formelanfänge werden neutralisiert, Originalfelder im JSON erhalten. Der A11-Prüfer vergleicht alle ursprünglichen Felder und URLs, nicht nur Anzahlen. Generator-Eingaben werden vor Ausgabe validiert; Kandidateninventar erfasst indexierte, nicht indexierte und unversionierte Dateien. Historische Baseline und Ausführungsrevision bleiben unterscheidbar. Fehlende lokale Audit-Artefakte gelten ausdrücklich nicht als versionierter Nachweis.
- A11: Kommentarzeilen und eindeutige Threads unterscheiden; M13 bleibt verschoben, ohne unbeauftragte Streichung der Medien-Roadmap. Der ursprüngliche M13-Abschnittsanker bleibt erhalten.
- A09: der begrenzte Zeichen-Whitelist-Filter bleibt für die Eingabeprüfung erhalten. Das Timezone-Log verwendet ausschließlich einen konstanten Platzhalter; auch unbekannte, formal gültige Eingaben gelangen nicht in Logs.
- A10: Staging-Smoke verlangt einen heute datierten Seed-Eintrag und eine verifizierbare Insight-Familie. Laufende Docker-Image-IDs und OCI-Revision werden unabhängig von `/instance` über den geschützten Staging-Host geprüft. Ein Scan mit HTTP 429 oder fehlender HTTP-Historie liefert keinen erfolgreichen Coverage-Nachweis. Zusätzlich sind erfolgreiche GET-Antworten auf beiden geschützten Routen `/api/v1/entries` und `/api/v1/insights/latest` erforderlich; reine 401-/403-Historien reichen nicht aus.

## Verifikation

Die abschließenden Ergebnisse werden im Integrations-PR auf dessen konkreten Head dokumentiert. Zwischenzeitliche Fehlversuche gelten nicht als erfolgreiche Abnahme. Lokal werden gezielte Regressionen, komplette Web-Suite, Lint/Typen, Build, Schema-Regeneration und Backend-Prüfungen ausgeführt; PostgreSQL-Integration und frische Dependency-Installation werden zusätzlich durch die gemeinsame CI geprüft.

## Offene Release-Gates

Ein Merge integriert die technische Basis und den Produktplan. Er bestätigt keine abgeschlossenen A10-/A12-Betriebs-, Geräte-, Accessibility-, CSV-Empfänger- oder Nutzerabnahmen. Deren Tracking-Issues bleiben offen. Insbesondere sind produktives Backup/Restore und die vollständige Journey gegen exakt die ausgelieferten Images separat nachzuweisen.

Main-Pushes starten die bestehende Image-Publikation (`main`/`latest`/SHA). Deshalb ist genau ein gemeinsamer Main-Merge vorgesehen. Vor der Betriebsfreigabe müssen die veröffentlichten Digests gegen den endgültigen Merge-SHA geprüft werden.

Der manuelle A10-Workflow benötigt im geschützten Environment `audit-rc` zusätzlich `A10_SSH_HOST`, `A10_SSH_KEY`, `A10_SSH_KNOWN_HOSTS` sowie die Variablen `A10_API_CONTAINER` und `A10_WEB_CONTAINER`. Der Host muss das zur Staging-URL gehörende Docker-Deployment sein; der SSH-Zugang benötigt die dortige Image-/Container-Inspektion und Python 3. Fehlende Konfiguration lässt das Gate fehlschlagen. Der Workflow verändert keine Container. Die SSH-Hostschlüssel müssen unabhängig bestätigt werden; keine automatische Übernahme per keyscan.

ZAP-Hook-Schnittstelle: [offizielle Scan-Hook-Dokumentation](https://www.zaproxy.org/docs/docker/scan-hooks/).

Nach Abschluss der Basisintegration folgt Z1 des [Produkt-Ausführungsplans](../../frontend/INSIGHT_USER_VALUE_EXECUTION_2026-09-29.md): unterstützte Fragen, Capability-Vertrag und Prototypen vor Implementierung der gespeicherten Fragen.

## Nachtrag 30.09.2026

Der [Desktop-Retest gegen `main`](QA_RETEST_2026-09-30.md) bestätigt mehrere der am 24.09. gemeldeten
Befunde als behoben (Berichtsauswahl, natürliche Häufigkeiten, adjustierte Stressrichtung,
Tagesfenster). Offen bleiben Sprachmischung, die Fensterbezeichnung „letzte 90 Tage“, gemischte
Fenster auf der Detailseite. Die A10-/A12-Gates sind davon
unberührt.

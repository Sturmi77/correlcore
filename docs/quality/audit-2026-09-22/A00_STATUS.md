# A00 – Ausgangsstand und Befundregister

Stand: 22.09.2026. Audit-Basis: `71d1089ff77388cadf2253ac67d1471dfa99fa40`.

## Isolierter Implementierungsstand

- Worktree-Branch: `codex/audit-a00-register`, erstellt aus `origin/main` = `acd98492c77d8e053c37b9165698e243146060c1`.
- Lokaler `main` beim Start: `50ef171336edfd03f92466167fb81dd7e81e3b19` (älter als der abgerufene Remote-Main).
- Vorhandener Arbeitsbranch: `feat/928-phase14-sleep-next-day` auf `2e8a7f8f5e4217c61a54b344b202e5aeb52fba73` mit 61 modifizierten, nicht committeten Dateien und einem unversionierten Audit-Verzeichnis. Diese Änderungen wurden nicht als Release-Fix übernommen oder überschrieben. Urheber der nicht committeten Änderungen ist aus Git allein nicht bestimmbar; Arbeitsstand und Pfade siehe `A00_LOKALE_FIXES.csv`.
- Dokumentationsquelle: der durch PR #987 versionierte Plan auf aktuellem Main sowie das zuvor unversionierte `AUDIT.md` und `review-evidence.json` aus dem vorhandenen Arbeitsstand. `review-threads-current.json` ist der aktuelle GraphQL-Abgleich.

## Register und Bewertung

- `A00_BEFUNDREGISTER.csv`: 40 Zeilen, exakt eine je Unterpunkt der Abdeckungsmatrix. Zielverhalten, betroffene Pfade, Rolle und benötigte Nachweise sind eingetragen. Fix-Commit und Release-CI bleiben leer, solange sie nicht existieren.
- `A00_REVIEWREGISTER.csv`: 524 archivierte Review-Kommentare einzeln mit URL, Thread-Status und technischem Status. Davon 298 Inline-Kommentare. 20 aktuelle Review-Findings sind direkt einem Matrix-Unterpunkt zugeordnet; ältere Kommentare erhalten eine explizit vorläufige Zuordnung anhand ihres PR-Kontexts und bleiben in A11 zur Einzelprüfung offen. Aktuelle GraphQL-Daten enthalten 234 Threads, 149 ungelöst. `isResolved` belegt nur den GitHub-Threadzustand.
- `A00_LOKALE_FIXES.csv`: Kandidaten im anderen, nicht committeten Arbeitsstand. Das Register kennzeichnet sie als Kandidaten; A01–A09 müssen Zielverhalten und Tests auf dem späteren Integrationsstand prüfen.

## Prüfung vorhandener Fix-Kandidaten

Auf dem unveränderten Arbeitsbranch `feat/928-phase14-sleep-next-day` liefen am 22.09.2026 gezielte Regressionstests: 24/24 Vitest-Tests (`insightSections`, `insightMatrixExport`, `trendWindowDays`, Insights-Seite) und 66/66 Pytest-Tests (`test_insight_sections.py`, `test_insights.py`, `test_stats_service.py`). Für den gezielten Pytest-Lauf wurde `--no-cov` verwendet, da die globale 70-Prozent-Schwelle bei einer kleinen Testauswahl naturgemäß nicht erreicht wird; der erste Lauf hatte 66 erfolgreiche Tests, aber 47,43 Prozent Gesamtabdeckung und daher Exit 1. Ein erster Vitest-Lauf mit mehreren Forks scheiterte an Worker-Timeouts; der Einzel-Worker-Lauf bestand. Das sind Tests des fremden, nicht committeten Stands und keine Freigabe der 61 Kandidaten. Wegen fehlender End-to-End- und finaler Release-SHA-Nachweise bleiben diese im Register offen.

## Abschlussgrenzen

Dieses A00-Register ist eine nachvollziehbare Ausgangsbasis. Es bestätigt noch keinen Produkt-Fix und keine Freigabe. Die 40 Audit-Zeilen und die historischen Kommentare brauchen die jeweiligen Fix-Commits, Regressionstests und Nachweise am finalen Release-Kandidaten. A11 klärt die fachliche Relevanz historischer Antworten. Kein bestätigter Befund wird hier als akzeptiertes Risiko klassifiziert; eine Widerlegung erfordert konkreten Test oder Gegenbeleg.

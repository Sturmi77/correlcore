# A12 Acceptance Runbook

Dieses Runbook koordiniert vorhandene Operator- und Geräte-Checklisten für **einen**
Release-Kandidaten. Es ersetzt keine der verlinkten Fachchecklisten.

## 1. Kandidat einfrieren

Vor jedem A12-Lauf in `A12_ACCEPTANCE_REGISTER.json` eintragen:

- vollständiger 40-stelliger Git-SHA;
- OCI-Digests `sha256:<64 hex>` für API, Web und Worker;
- Staging-Deployment-ID oder unveränderliche URL/Run-ID;
- UTC-Zeitpunkt der Bereitstellung.

Ändert sich Code oder ein Image, beginnt die betroffene Abnahme erneut. Tags wie
`latest`, Branch-Namen und PR-Heads sind kein unveränderlicher Kandidatenbezug.

## 2. Evidenz sicher erfassen

- Pro Gate einen redigierten Markdown-Nachweis nach
  [`a12-evidence/README.md`](a12-evidence/README.md) anlegen oder eine stabile
  Issue-/Run-URL eintragen.
- Keine Tokens, Cookies, E-Mail-Adressen, Health-Connect-Rohdaten, Interviewnamen,
  Datenbank-URLs oder Schlüssel committen.
- Screenshots vor dem Commit auf Benachrichtigungen, Kontonamen, Geräte-IDs und
  Gesundheitsdaten prüfen.
- `passed` verlangt Evidenz, ein Sign-off mit Rolle, Datum und Ergebnis sowie
  unter `candidate` einen Snapshot des geprüften Release-Kandidaten. SHA und
  Image-Digests müssen exakt mit `release_candidate` übereinstimmen.
- Mobile Gates (`health_connect_m8`, `firebase_play`, `compare_device`) verlangen
  zusätzlich den SHA-256-Digest des installierten APK/AAB unter
  `android_artifact_digest` im Kandidaten und im Gate-Snapshot.
- `not_applicable` ist nur für Gates außerhalb des angebotenen Releaseumfangs
  zulässig und verlangt `not_applicable_reason` sowie ein Sign-off mit dem
  Ergebnis `not_applicable`.
- Das Gate `deployment_restore` darf erst auf `passed`, wenn `staging` und
  `production_smoke` jeweils bestanden und an denselben Kandidaten gebunden sind.

## 3. Nutzerverständnis – #930 H.4

Tracking: [#930](https://github.com/Sturmi77/correlcore/issues/930) und
[#986](https://github.com/Sturmi77/correlcore/issues/986).

Mit 4–6 Zielnutzern denselben Leitfaden verwenden. Keine Frage darf die gewünschte
Antwort „Burnout-Prävention“ vorgeben.

1. Auslöser für das Tracking und erwarteter Nutzen.
2. 60-Sekunden-Eintrag: Was ist verständlich, was wäre zu viel?
3. Wochenreview: Kann die Person eine eigene Frage formulieren und den Weg von Antwort
   zu Prüfung nachvollziehen?
4. Belastungsdarstellung: Wird sie als Muster statt Diagnose verstanden, und ist die
   Grenze „nie für Arbeitgeber“ klar?
5. Nicht-Ergebnis: Wird „kein belastbarer Zusammenhang“ als nützliche Antwort verstanden?
6. Vier Ebenen: Findet die Person Antwort, Prüfung, Labor und Bericht passend zum
   jeweiligen Job, ohne sie als getrennte Produkte zu verstehen?

Der Nachweis enthält anonymisierte Teilnehmercodes, Szenario, Beobachtungen, Befunde
mit Schweregrad, daraus entstandene Änderungen und einen Nachtest der Änderungen. Ein
reines Gesprächsprotokoll ohne Befundbehandlung besteht das Gate nicht.

## 4. Health Connect / M8

Basis: [`features/HEALTH_CONNECT.md`](../../features/HEALTH_CONNECT.md). Geprüft wird
der `sideload`-Flavor, weil der `play`-Flavor Health Connect gemäß #718 nicht enthält.

Mindestens Android 13 mit installierter Health-Connect-App und Android 14+ mit
integriertem Health Connect prüfen; gehärtete ROMs bleiben eine explizite Matrixzeile,
falls ein Gerät verfügbar ist.

1. Ohne Server-Consent öffnet sich kein OS-Permission-Sheet.
2. Nach Consent werden ausschließlich Schlaf und Herzrate angefordert.
3. Ablehnen, partiell erlauben, vollständig erlauben und später widerrufen.
4. Import mit Daten und ohne Daten; Tagesgrenzen in der Gerätezeitzone dokumentieren.
5. Denselben Zeitraum erneut importieren: keine Duplikate, manuelle Werte behalten
   ihre dokumentierte Priorität.
6. Nach Widerruf keine neuen Reads; erneute Einwilligung funktioniert.

Jede Matrixzeile enthält Gerät/Emulator, OS-Build, Health-Connect-Version,
App-Build/Digest, Zeitzone, Ergebnis und redigierten Nachweis.

## 5. Hosted Beta

Die operative Quelle bleibt [#621](https://github.com/Sturmi77/correlcore/issues/621)
mit `M10_2_PUBLIC_HOSTED_LAUNCH_STATUS.md` und
`runbooks/hosted-topology-h-cutover.md`. A12 zeichnet nur den Abgleich auf:

- Hosted läuft ohne Mailpit; SMTP-Domain sowie SPF/DKIM/DMARC sind bestätigt;
- öffentliche Mail-Links, Login, Registrierung, Reset und Legal-Seiten stimmen mit
  dem tatsächlichen Operator überein;
- genau ein TLS-Edge ist aktiv; Proxy-Header und Cookie-Verhalten entsprechen dem
  dokumentierten Pfad;
- Owner entscheidet jeden offenen #621-Punkt mit Evidenz, `N/A` plus Begründung oder
  einem weiterhin offenen Folge-Issue.

## 6. Firebase, Play und Geräte

Die Quellen bleiben [#717](https://github.com/Sturmi77/correlcore/issues/717),
[#722](https://github.com/Sturmi77/correlcore/issues/722),
[#723](https://github.com/Sturmi77/correlcore/issues/723) und
[#724](https://github.com/Sturmi77/correlcore/issues/724).

- Live-FCM: Berechtigung erlauben/ablehnen, Zustellung, Logout/Token-Abmeldung,
  ungültiges Token und deaktiviertes FCM prüfen.
- Play: AAB-Digest dem Kandidaten zuordnen, Internal-Install, Pre-Launch-Report ohne
  kritische Crashes und Closed-Testing-Status dokumentieren.
- Datenschutz: öffentliche Privacy-URL und Data-Safety-Angaben müssen den wirklich
  ausgelieferten Flavor widerspiegeln.
- Compare-Zoom separat nach [#585](https://github.com/Sturmi77/correlcore/issues/585)
  und `COMPARE_AXIS_ZOOM_CAZ3_QA.md` auf dem Release-Build abzeichnen.

## 7. Laufzeit-Sicherheit

Die folgenden Ergebnisse werden redigiert gespeichert; Befehle niemals mit Secrets in
die Shell-History oder Evidenz kopieren.

1. **API-DB-Rolle:** `current_user`, `rolsuper` und `rolbypassrls` aus `pg_roles`
   prüfen. Die API-Rolle darf weder Superuser noch BYPASSRLS sein.
2. **RLS:** `relrowsecurity`/`relforcerowsecurity` für alle nutzerbezogenen Tabellen
   erfassen und einen Cross-User-Zugriffstest mit der echten API-Rolle durchführen.
3. **TLS/Proxy:** Zertifikat, HTTPS-Weiterleitung, genau einen Edge und
   `X-Forwarded-Proto` prüfen.
4. **Cookies:** Login/Refresh im Browser prüfen; `Secure`, `HttpOnly`, `SameSite` und
   Pfade redigiert dokumentieren.
5. **Worker:** tatsächlichen Containerbefehl, Zeitplan, letzte erfolgreiche Jobs und
   `/api/v1/worker/status` prüfen. Keine Umgebungswerte dumpen.

Ein Screenshot der Compose-Datei oder ein grüner Unit-Test allein belegt die laufende
Konfiguration nicht.

## 8. Staging-Upgrade, Smoke und Restore

1. Verschlüsseltes Backup der Staging-Daten und separat gesicherten
   `ENCRYPTION_KEY` bestätigen.
2. Repräsentative v1.9.1-Fixture wiederherstellen; Ausgangs-Migrationsstand und
   Prüfsummen notieren.
3. Kandidaten-Images **per Digest** deployen; Migration bis `head` ausführen und den
   resultierenden Revisionsstand erfassen.
4. Smoke: Health/Readiness, Login, bestehende verschlüsselte Notes/Marker, Eintrag,
   Sync, Insights/Worker, Reportexport und Account-Export.
5. Backup nach dem Upgrade erstellen, in eine isolierte leere Datenbank restoren und
   Row-Counts sowie mindestens einen entschlüsselbaren Datensatz prüfen. Verfahren aus
   [`M9_BACKUP_RESTORE_TEST.md`](../M9_BACKUP_RESTORE_TEST.md) verwenden.
6. Rollback-Entscheidung und Verantwortliche dokumentieren. Kein destruktiver
   Alembic-Downgrade als Restore-Ersatz.
7. Erst nach bestandenem Staging-Gate Deployment freigeben. Danach separate
   Produktions-Smoke-Prüfung mit denselben Digests und ohne Testdatenmutation.

## 9. Register aktualisieren

Nach jedem Lauf:

1. Evidenz-URLs/-Pfade und Ergebnis in `A12_ACCEPTANCE_REGISTER.json` eintragen.
2. Bei `failed` ein offenes Finding-/Fix-Issue verlinken.
3. Bei `blocked_external` konkreten Blocker und verantwortliches Issue beibehalten.
4. `python docs/quality/audit-2026-09-22/verify_a12_acceptance.py` ausführen.
5. Finale Review auf dem exakten Kandidaten-SHA abwarten.

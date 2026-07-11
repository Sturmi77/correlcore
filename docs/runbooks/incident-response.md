# Runbook: Incident Response (Datenpannen)

**Bezug:** [`docs/DSGVO.md`](../DSGVO.md) §8, [`docs/PRIVACY.md`](../PRIVACY.md)  
**Status:** M9 — Beta-Härtung  
**Letzte Aktualisierung:** 2026-07-11

Dieses Runbook beschreibt den internen Ablauf bei Sicherheitsvorfällen und
Datenpannen (Art. 33–34 DSGVO). Es gilt für **Selfhost-Betreiber** als
Verantwortliche und für die CorrelCore-Projektwartung bei koordinierter
Offenlegung.

---

## 1. Wann dieses Runbook greift

| Ereignis                                | Beispiel                                                | Meldepflicht                         |
| --------------------------------------- | ------------------------------------------------------- | ------------------------------------ |
| Unbefugter Zugriff                      | kompromittierte Admin-Zugänge, offene DB-Port           | oft ja                               |
| Datenleck                               | Backup-Diebstahl, Log-Exfiltration mit Gesundheitsdaten | ja bei Art.-9-Daten                  |
| Verfügbarkeitsvorfall ohne Datenabfluss | API-Ausfall, Redis-Ausfall                              | in der Regel nein                    |
| Fehlkonfiguration Error-Tracking        | PII in GlitchTip-Events                                 | internes Incident; ggf. Meldepflicht |

**Faustregel:** Sobald **personenbezogene Gesundheitsdaten** (Art. 9 DSGVO) in
falschen Händen sein könnten → Incident-Prozess starten.

---

## 2. Sofortmaßnahmen (0–2 Stunden)

1. **Eingrenzen:** betroffene Instanz isolieren (Traefik-Route deaktivieren,
   API-Container stoppen, kompromittierte Credentials rotieren).
2. **Beweise sichern:** relevante JSON-Logs, GlitchTip-Events, Postgres-
   `pg_stat_activity`, Reverse-Proxy-Access-Logs — **keine** Gesundheitsdaten in
   Tickets kopieren.
3. **Verantwortlichen informieren:** Instanz-Betreiber + technischer Ansprechpartner.
4. **Schaden einschätzen:** Welche Datenkategorien? Wie viele Betroffene?
   Verschlüsselung at-rest noch wirksam?

Checkliste:

- [ ] Betroffene Systeme identifiziert
- [ ] Zugriff auf kompromittierte Accounts/Keys gesperrt
- [ ] `ENCRYPTION_KEY` / DB-Passwörter rotiert (falls nötig) — siehe [`RUNBOOK_KEY_ROTATION.md`](../RUNBOOK_KEY_ROTATION.md)
- [ ] GlitchTip/Logs auf PII-Leaks geprüft

---

## 3. Bewertung (2–24 Stunden)

| Frage                                                   | Ja →                                                       |
| ------------------------------------------------------- | ---------------------------------------------------------- |
| Art.-9-Daten (Mood, Symptome, Notizen) betroffen?       | **Meldepflicht prüfen** (meist ja)                         |
| Nur E-Mail/Metadaten ohne Gesundheitsinhalt?            | Risikoanalyse; Meldung je nach Eintrittswahrscheinlichkeit |
| Daten verschlüsselt und Schlüssel nicht kompromittiert? | Risiko reduziert, dokumentieren                            |

Dokumentiere in einem internen Incident-Record (Markdown/Ticket):

- Zeitpunkt der Entdeckung
- Ursache (falls bekannt)
- Betroffene Nutzerzahl (Schätzung)
- Datenkategorien
- Getroffene Maßnahmen

---

## 4. Meldung an Aufsichtsbehörde (Art. 33)

**Frist:** innerhalb von **72 Stunden** nach Kenntnisnahme.

- **Österreich:** [Datenschutzbehörde](https://www.dsb.gv.at/meldung-datenverletzung)
- Inhalt: Art der Panne, Kategorien, ungefähre Zahl Betroffener, wahrscheinliche
  Folgen, ergriffene Maßnahmen

Bei Selfhost-Betrieb ist der **Instanz-Betreiber** Meldepflichtiger, nicht das
CorrelCore-Open-Source-Projekt.

---

## 5. Information der Betroffenen (Art. 34)

Erforderlich wenn die Panne **voraussichtlich ein hohes Risiko** für Rechte und
Freiheiten bedeutet.

- Kanal: E-Mail an betroffene Nutzer (keine Gesundheitsdaten in der Betreffzeile)
- Inhalt: was passiert ist, welche Daten, was Nutzer tun können (Passwort ändern,
  Export, Löschung)
- Frist: unverzüglich, parallel zur Behördenmeldung wenn möglich

---

## 6. Observability & GlitchTip (M9)

Error-Tracking ist **optional** (`GLITCHTIP_DSN` leer = kein Traffic).

| Regel                 | Umsetzung                                     |
| --------------------- | --------------------------------------------- |
| Selfhosted only       | Compose-Profil `monitoring`, kein SaaS-Sentry |
| Kein PII in Events    | `before_send`-Scrub in API + Web              |
| Zugriff auf GlitchTip | Nur Betreiber; separates Admin-Passwort       |
| Retention             | 90 Tage (siehe DSGVO.md §9)                   |

Nach einem Verdacht auf PII in GlitchTip:

1. betroffene Projekte/Events löschen
2. Scrub-Tests erneut ausführen (`test_error_tracking.py`, `scrubEvent.test.ts`)
3. Root Cause (z. B. fehlendes Scrub-Feld) beheben

---

## 7. Wiederherstellung

1. Patch/Config-Fix deployen
2. Backup-Restore nur nach [`M9_BACKUP_RESTORE_TEST.md`](../quality/M9_BACKUP_RESTORE_TEST.md) Protokoll (Sprint 3)
3. `/health/ready` und Smoke-Tests grün
4. Post-Incident-Review: Was wird in Install-Guide / Betreiber-Doku ergänzt?

---

## 8. Kontakte

| Rolle                        | Kanal                                                |
| ---------------------------- | ---------------------------------------------------- |
| Sicherheitslücken (Produkt)  | [`SECURITY.md`](../../SECURITY.md)                   |
| Instanz-Betreiber (Selfhost) | vom Betreiber dokumentiert (Impressum/Support)       |
| CorrelCore Maintainers       | GitHub Security Advisories / security@correlcore.app |

---

## 9. Verwandte Dokumente

- [`docs/DSGVO.md`](../DSGVO.md)
- [`docs/PRIVACY.md`](../PRIVACY.md)
- [`docs/adr/0007-healthchecks-and-logging.md`](../adr/0007-healthchecks-and-logging.md)
- [`docs/RUNBOOK_KEY_ROTATION.md`](../RUNBOOK_KEY_ROTATION.md)

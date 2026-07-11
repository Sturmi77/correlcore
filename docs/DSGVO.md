# CorrelCore — Datenschutz-Schutzkonzept (DSGVO)

**Version:** 1.0 | **Datum:** 2026-04-20 | **Verantwortlicher:** [Name / Firmenname]
**Rechtsgrundlage:** DSGVO (EU 2016/679), DSG (Österreich), Art. 9 besondere Datenkategorien

---

## 1. Zweck und Geltungsbereich

CorrelCore verarbeitet Gesundheitsdaten (Stimmungsdaten, Symptome, Schlafdaten, biometrische Wearable-Daten), die gemäß Art. 9 DSGVO als besondere Kategorien personenbezogener Daten einzustufen sind. Dieses Dokument beschreibt alle technischen und organisatorischen Maßnahmen (TOMs) zur Sicherstellung der Datenschutz-Compliance.

## 2. Verarbeitete Datenkategorien

| Datenkategorie                                 | Art-9-relevant              | Speicherort     | Verschlüsselung      | Rechtsgrundlage                                       |
| ---------------------------------------------- | --------------------------- | --------------- | -------------------- | ----------------------------------------------------- |
| Stimmungsdaten (mood_score, energy, stress)    | ✅ Ja                       | PostgreSQL      | App-Level AES-256    | Einwilligung Art. 6(1)(a) + Art. 9(2)(a)              |
| Symptom-Daten (Kopfschmerzen, Verdauung, etc.) | ✅ Ja                       | PostgreSQL      | App-Level AES-256    | Einwilligung                                          |
| Notizen (Freitext)                             | ⚠️ potenziell               | PostgreSQL      | App-Level AES-256    | Einwilligung                                          |
| Fotos                                          | ⚠️ potenziell (biometrisch) | MinIO (geplant) | SSE-S3 (vorbereitet) | Einwilligung                                          |
| Schlafdaten (Garmin/Health Connect)            | ✅ Ja                       | PostgreSQL      | App-Level AES-256    | Einwilligung + explizite separate Einwilligung für HC |
| Aktivitäts-Tags                                | ❌ nein (abstrakt)          | PostgreSQL      | Standard             | berechtigtes Interesse                                |
| E-Mail-Adresse                                 | ❌ nein                     | PostgreSQL      | Standard             | Vertragserfüllung                                     |

## 3. Technische und organisatorische Maßnahmen (TOMs, Art. 32 DSGVO)

### 3.1 Verschlüsselung

- **Transport:** TLS 1.3 (HSTS, HSTS-Preload)
- **Daten at-rest:** App-Level Fernet/AES-256 für alle Art.-9-Felder
- **Objekte:** MinIO SSE-S3 für alle Buckets
- **Backups:** restic mit AES-256-GCM-Verschlüsselung

### 3.2 Zugriffskontrolle

- **Authentifizierung:** Native JWT mit HttpOnly-Cookies und Refresh-Rotation; MFA/TOTP ist erst mit Authentik/OIDC geplant
- **Autorisierung:** PostgreSQL Row-Level-Security (user_id-basiert)
- **API:** Rate-Limiting, JWT-Refresh-Token-Rotation
- **Docker:** Socket-Proxy, no-new-privileges, interne Netzwerke

### 3.3 Datenminimierung

- Nur explizit eingegebene Daten werden erfasst (kein Background-Tracking)
- EXIF-Strip bei Foto-Upload ist verpflichtender M13-Scope; aktuell gibt es noch keine Foto-/Attachment-API
- Logs enthalten keine Gesundheitsdaten im Klartext
- Push-Notification-Payloads sind inhaltsleer (nur Reminder-Signal)

### 3.4 Verfügbarkeit und Integrität

- Backups: täglich via restic, 30-Tage-Retention
- Monitoring: GlitchTip (Fehlertracking), Uptime-Kuma (Verfügbarkeit)
- Health-Checks auf allen Containern
- Sync-Konflikt-Log verhindert stillen Datenverlust

## 4. Betroffenenrechte (Art. 15–22 DSGVO)

| Recht                                 | Endpunkt / Umsetzung                                                        | Frist                  | Status |
| ------------------------------------- | --------------------------------------------------------------------------- | ---------------------- | ------ |
| Auskunft (Art. 15)                    | `GET /api/v1/user/data` → JSON-Dump aller Daten                             | sofort (automatisiert) | ✅ M2  |
| Berichtigung (Art. 16)                | Standard-Edit-UI                                                            | sofort                 | ✅ M1  |
| Löschung / Right to Erasure (Art. 17) | `DELETE /api/v1/user/me` → Cascade alle Daten + Cryptographic Erasure (DEK) | sofort                 | ✅ M1  |
| Datenübertragbarkeit (Art. 20)        | `GET /api/v1/user/export` → ZIP (JSON/CSV; Foto-Sektion bis M13 leer)       | automatisiert          | ✅ M2  |
| Widerspruch Analyse (Art. 21)         | `PATCH /api/v1/user/preferences {analytics_enabled: false}`                 | sofort                 | ✅ M3  |
| Einschränkung (Art. 18)               | Support-Anfrage an Instanz-Betreiber (siehe unten)                          | 72h                    | ✅ M9  |

### Einschränkung der Verarbeitung (Art. 18) — Support-Workflow

Betroffene können die Einschränkung der Verarbeitung per E-Mail oder Ticket beim
**Betreiber der jeweiligen Instanz** beantragen (Selfhost: der Server-Administrator).

**Prozess (Ziel: Antwort innerhalb 72 Stunden):**

1. Anfrage enthält: registrierte E-Mail-Adresse, gewünschte Einschränkung (z. B.
   „keine weitere Analyse“, „Konto einfrieren bis Klärung“).
2. Betreiber verifiziert Identität (Antwort von der registrierten E-Mail oder
   erneute Authentifizierung).
3. Technische Umsetzung je nach Anfrage:
   - Analyse stoppen: `analytics_enabled = false` (Nutzer kann selbst in Settings
     oder Betreiber per DB/Support).
   - Vollständige Einfrierung: Konto temporär sperren / keine weiteren Schreibzugriffe
     bis zur Klärung (manuell, kein Self-Service-API in M9).
4. Antwort an Nutzer mit Bestätigung und voraussichtlicher Dauer.

Kein separater REST-Endpoint in M9 — bewusst zur Minimierung der API-Oberfläche;
vollständige Self-Service-UI kann in M10+ evaluiert werden.

## 5. Einwilligungsmanagement

- Opt-in bei Registrierung: explizite Checkbox für Art.-9-Datenverarbeitung
- Separate Einwilligung für Health-Connect-Import (gesonderte UI, mit Erklärung was importiert wird)
- Einwilligungen werden mit Timestamp gespeichert (`consent_log` Tabelle)
- Widerruf jederzeit möglich (Settings → Datenschutz → Einwilligungen verwalten)

## 6. Auftragsverarbeitung (Art. 28 DSGVO)

### Selfhosted-Betrieb

- Keine Auftragsverarbeitung — User ist selbst Verantwortlicher
- Kein DPA erforderlich

### Cloud-Betrieb (CorrelCore Cloud, ab M12)

| Auftragsverarbeiter             | Zweck                        | AV-Vertrag                                                                                                   |
| ------------------------------- | ---------------------------- | ------------------------------------------------------------------------------------------------------------ |
| Hetzner Online GmbH (Frankfurt) | Hosting / Infrastruktur      | https://www.hetzner.com/AV/ · [`legal/AV_VERTRAG_HETZNER_TEMPLATE.md`](legal/AV_VERTRAG_HETZNER_TEMPLATE.md) |
| Resend Inc.                     | Transaktions-E-Mail          | vorhanden                                                                                                    |
| Stripe Payments Europe Ltd.     | Billing / Zahlungsabwicklung | vorhanden                                                                                                    |

Keine weiteren Auftragsverarbeiter.

## 7. Datenschutz-Folgeabschätzung (DSFA, Art. 35 DSGVO)

Eine DSFA ist durchzuführen wenn Gesundheitsdaten im Cloud-Betrieb verarbeitet werden.

| #   | Risikofeld                    | Mitigationsmaßnahme                                                                                                     |
| --- | ----------------------------- | ----------------------------------------------------------------------------------------------------------------------- |
| 1   | Unbefugter Datenbankzugriff   | Verschlüsselung at-rest, RLS, starke Auth                                                                               |
| 2   | Backup-Diebstahl              | restic-Verschlüsselung, separate Key-Aufbewahrung                                                                       |
| 3   | Insider-Threat (SaaS-Betrieb) | RLS, App-Level-Verschlüsselung, keine menschliche Zugriffsnotwendigkeit auf Nutzdaten; Admin-Audit-Log ist noch geplant |
| 4   | Third-Party-Kompromittierung  | kein Third-Party-Analytics, minimale externe Abhängigkeiten                                                             |
| 5   | Gesetzliche Auskunftspflicht  | AV-Verträge, Daten in EU (Hetzner Frankfurt)                                                                            |

**DSFA-Status:** 🔄 Vor M12 (Cloud-Launch) zu erstellen

## 8. Datenpannen (Art. 33–34 DSGVO)

**Meldepflicht:** 72h an zuständige Aufsichtsbehörde (AT: Datenschutzbehörde, dsb.gv.at)

**Interner Prozess:**

1. Entdeckung → sofortige Isolierung des betroffenen Systems
2. Bewertung: Betroffene Datenkategorien? Art.-9-Daten betroffen?
3. Wenn Art.-9-Daten betroffen: immer Meldepflicht (auch bei geringem Risiko)
4. DSB-Meldung via https://www.dsb.gv.at/meldung-datenverletzung
5. Betroffene informieren wenn hohes Risiko (Art. 34)

**Incident-Response-Plan:** [`docs/runbooks/incident-response.md`](runbooks/incident-response.md) (M9)

## 9. Aufbewahrungsfristen

| Datenkategorie              | Aufbewahrungsdauer                                    | Löschauslöser                            |
| --------------------------- | ----------------------------------------------------- | ---------------------------------------- |
| Mood-Entries                | bis Account-Löschung oder explizite Nutzer-Löschung   | Account-Delete / Nutzeraktion            |
| Analytics/Insights          | 90 Tage Rolling Window (ältere werden neu berechnet)  | Automatisch                              |
| Nicht verifizierte Accounts | 7 Tage (konfigurierbar via `UNVERIFIED_CLEANUP_DAYS`) | Worker-Job `cleanup_unverified_accounts` |
| Sync-Konflikt-Log           | 90 Tage                                               | Geplant mit M4                           |
| Auth-Logs (Login-Versuche)  | 30 Tage                                               | Automatisch                              |
| Error-Logs (GlitchTip)      | 90 Tage                                               | Automatisch                              |
| Billing-Daten               | 7 Jahre                                               | Gesetzliche Aufbewahrungspflicht AT      |

## 10. Meilenstein-Checkpoints

Für jeden Meilenstein der DSGVO-relevante Features enthält:

### M0 – Fundament

- [ ] 🔒 DSGVO: Dieses Dokument (DSGVO.md) vorhanden und im Repo
- [ ] 🔒 DSGVO: Kein Third-Party-Tracking im Frontend-Code verifiziert
- [ ] 🔒 DSGVO: ENCRYPTION_KEY in .env.example dokumentiert
- [ ] 🔒 DSGVO: MinIO SSE in docker-compose.yml aktiviert

### M1 – Core Entry

- [ ] 🔒 DSGVO: consent_log Tabelle implementiert
- [ ] 🔒 DSGVO: note_enc und symptoms.details verschlüsselt at-rest (Fernet)
- [ ] 🔒 DSGVO: Opt-in-Checkbox bei Registrierung mit korrektem Rechtstext
- [ ] 🔒 DSGVO: Keine Klartextloggung sensibler Felder verifiziert (Log-Review)

### M2 – Visualisierung

- [x] 🔒 DSGVO: Datenexport-Funktion (Art. 20) implementiert und getestet
- [x] 🔒 DSGVO: Export enthält alle aktuell gespeicherten M1/M2-Daten (Entries, Tags, Symptome; zukuenftige Fotos/Habits/Insights/Sleep als leere, versionierte Sektionen)

### M3 – Insights

- [x] 🔒 DSGVO: Analytics-Opt-Out implementiert (`analytics_enabled` Flag) — Settings-Toggle + `PATCH /api/v1/user/preferences`; E2E [`gdpr-self-service.spec.ts`](../apps/web/tests/e2e/gdpr-self-service.spec.ts)

### M7 – Insights v2 (LLM)

- [ ] 🔒 DSGVO: Ollama/LLM verarbeitet keine Daten außerhalb der lokalen Instanz (verifiziert)

### M8 – Health Connect

- [ ] 🔒 DSGVO: Separate Health-Connect-Einwilligung mit klarer Erklärung implementiert
- [ ] 🔒 DSGVO: Nur minimale Health-Daten importiert (Schlaf + HR, keine Bewegungsprofile)

### M9 – Beta

- [x] 🔒 DSGVO: Datenschutzerklärung (`docs/PRIVACY.md` + in-app Link `/privacy`) vorhanden
- [x] 🔒 DSGVO: Account-Löschung (Right to Erasure) End-to-End getestet — Playwright [`gdpr-self-service.spec.ts`](../apps/web/tests/e2e/gdpr-self-service.spec.ts) + Backend [`test_user_endpoints.py`](../backend/tests/test_user_endpoints.py)
- [x] 🔒 DSGVO: Incident-Response-Runbook vorhanden — [`docs/runbooks/incident-response.md`](runbooks/incident-response.md)
- [ ] 🔒 DSGVO: Backup-Verschlüsselung verifiziert

### M11 – Play Store

- [ ] 🔒 DSGVO: Google Play Data Safety Section wahrheitsgemäß ausgefüllt
- [ ] 🔒 DSGVO: Datenschutzerklärung URL im Store hinterlegt

### M12 – SaaS

- [ ] 🔒 DSGVO: DSFA erstellt und dokumentiert
- [ ] 🔒 DSGVO: AV-Vertrag mit Hetzner nachweislich abgeschlossen
- [ ] 🔒 DSGVO: Auftragsverarbeitungsverzeichnis (Art. 30) gepflegt
- [ ] 🔒 DSGVO: Datenlöschung bei Kündigung in ≤30 Tagen implementiert und getestet

### M13 – Fotos

- [ ] 🔒 DSGVO: Foto-/Attachment-API implementiert
- [ ] 🔒 DSGVO: EXIF-Strip automatisch getestet (Unit-Test mit GPS-haltigen Testfotos)
- [ ] 🔒 DSGVO: Account-Delete löscht auch alle MinIO-Objekte (Cascade-Test)

# Auftragsverarbeitungsvertrag (AVV) — Template Hetzner

Last updated: 2026-07-11 (M9 Sprint 4)

> **Hinweis:** Dieses Dokument ist eine **Betreiber-Checkliste** für den geplanten
> CorrelCore-Cloud-Betrieb (M12+). Für **Selfhost** ist kein AVV mit Hetzner nötig —
> der Nutzer ist selbst Verantwortlicher ([`DSGVO.md`](../DSGVO.md) §6).

## 1. Vertragsparteien

| Rolle | Partei | Anschrift |
| ----- | ------ | --------- |
| **Verantwortlicher** (Auftraggeber) | _[Firma / Name des CorrelCore-Cloud-Betreibers]_ | _[Adresse]_ |
| **Auftragsverarbeiter** | Hetzner Online GmbH | Industriestr. 25, 91710 Gunzenhausen, Deutschland |

## 2. Gegenstand und Dauer

| Feld | Inhalt |
| ---- | ------ |
| Gegenstand | Bereitstellung von Infrastructure-as-a-Service (Cloud-Server, Volumes, Netzwerk) zur Hostung der CorrelCore-Cloud-Anwendung |
| Dauer | Laufzeit des Hauptvertrags (Hetzner Cloud / Dedicated) vom _[Startdatum]_ bis zur Vertragsbeendigung |
| Art der Verarbeitung | Speicherung und Übertragung von personenbezogenen Daten auf den vom Auftraggeber gemieteten Servern |

## 3. Art und Zweck der Verarbeitung

| Datenkategorie | Zweck | Besondere Kategorien (Art. 9)? |
| -------------- | ----- | ------------------------------ |
| Account-Daten (E-Mail, Passwort-Hash) | Authentifizierung | Nein |
| Stimmungs- und Gesundheitsdaten (verschlüsselt) | Kernfunktion CorrelCore | **Ja** — Art. 9 DSGVO |
| Technische Metadaten (IP, Logs ohne Gesundheitsinhalt) | Betrieb, Sicherheit | Nein |

Verarbeitung erfolgt ausschließlich auf Weisung des Verantwortlichen gemäß
[`PRIVACY.md`](../PRIVACY.md) und [`DESIGN_DOCUMENT.md`](../DESIGN_DOCUMENT.md).

## 4. Hetzner-Standard-AVV

Hetzner stellt einen vorformulierten Auftragsverarbeitungsvertrag bereit:

- **URL:** https://www.hetzner.com/AV/
- **Stand:** vom Betreiber beim Abschluss zu prüfen

### Checkliste für den Betreiber

- [ ] Hetzner-AVV PDF heruntergeladen und archiviert
- [ ] AVV im Hetzner-Kundenportal aktiviert / unterzeichnet (falls erforderlich)
- [ ] Verarbeitungsverzeichnis (Art. 30) um Hetzner-Eintrag ergänzt
- [ ] Server-Standort **EU** (empfohlen: Falkenstein / Nürnberg / Helsinki — Frankfurt-Region)
- [ ] Sub-Auftragsverarbeiter-Liste von Hetzner geprüft
- [ ] TOM-Dokumentation verknüpft ([`adr/0005-verschluesselung-at-rest.md`](../adr/0005-verschluesselung-at-rest.md))

## 5. Technische und organisatorische Maßnahmen (TOM) — Auftraggeber-seitig

Der Verantwortliche implementiert auf der Hetzner-Infrastruktur:

| Maßnahme | Referenz |
| -------- | -------- |
| TLS 1.2+ via Traefik | [`selfhost/INSTALL.md`](../selfhost/INSTALL.md) |
| LUKS-Volume-Verschlüsselung (optional) | INSTALL.md §LUKS |
| App-Level Fernet-Verschlüsselung | ADR-0005 |
| Verschlüsselte Backups (restic) | [`M9_BACKUP_RESTORE_TEST.md`](../quality/M9_BACKUP_RESTORE_TEST.md) |
| Zugriffskontrolle (SSH-Keys, Firewall) | Betreiber-Runbook |
| Incident Response | [`runbooks/incident-response.md`](../runbooks/incident-response.md) |

## 6. Unterauftragsverarbeiter

Hetzner kann weitere Unterauftragsverarbeiter einsetzen. Der aktuelle Stand ist in
Hetzners AVV / Subprocessor-Liste dokumentiert. Der Verantwortliche:

- [ ] Subprocessor-Liste bei Vertragsabschluss gespeichert
- [ ] Änderungsbenachrichtigungen von Hetzner abonniert / regelmäßig geprüft

## 7. Rechte der betroffenen Personen

CorrelCore stellt Self-Service-Werkzeuge bereit (Art. 15–20):

- Datenexport: `GET /api/v1/user/export`
- Account-Löschung: `DELETE /api/v1/user/me`
- Datenschutzerklärung: [`PRIVACY.md`](../PRIVACY.md)

Der Auftragsverarbeiter (Hetzner) hat **keinen** inhaltlichen Zugriff auf
Anwendungsdaten — nur Infrastruktur-Hosting.

## 8. Meldepflicht bei Datenpannen

| Partei | Pflicht |
| ------ | ------- |
| Hetzner | Meldung an Auftraggeber gemäß AVV |
| CorrelCore-Betreiber | 72h-Meldung an Aufsichtsbehörde ([`DSGVO.md`](../DSGVO.md) §8, [`incident-response.md`](../runbooks/incident-response.md)) |

## 9. Löschung und Rückgabe

Bei Vertragsende:

- [ ] Anwendungs-Backups gemäß Retention-Policy löschen
- [ ] Hetzner-Volume / Server kündigen und Löschbestätigung dokumentieren
- [ ] `ENCRYPTION_KEY`-Backup separat vernichten (falls Instanz eingestellt)

## 10. Dokumentation im Repository

| Dokument | Zweck |
| -------- | ----- |
| Dieses Template | AVV-Checkliste für M12 Cloud |
| [`DSGVO.md`](../DSGVO.md) §6 | Auftragsverarbeitung Übersicht |
| [`DESIGN_DOCUMENT.md`](../DESIGN_DOCUMENT.md) M9 DSGVO-Checkpoint | AV-Vertrag-Template vorhanden |

**Nach Unterzeichnung:** Kopie des signierten Hetzner-AVV **nicht** ins Git-Repo —
nur im internen Compliance-Archiv des Betreibers ablegen.

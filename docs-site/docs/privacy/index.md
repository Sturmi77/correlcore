# CorrelCore — Datenschutzerklärung

**Version:** 1.0 (M9)  
**Stand:** 2026-07-11  
**Geltung:** Selfhosted CorrelCore-Installationen und deren Endnutzer

Diese Datenschutzerklärung beschreibt, wie CorrelCore personenbezogene und
gesundheitsbezogene Daten verarbeitet. Technische Details zu TOMs und
Meilenstein-Checkpoints:
[DSGVO.md](https://github.com/Sturmi77/correlcore/blob/main/docs/DSGVO.md).

---

## 1. Verantwortlicher

### Selfhosted-Betrieb

Wenn du CorrelCore auf eigener Infrastruktur betreibst, **bist du
Verantwortlicher** im Sinne der DSGVO. Du legst Zweck, Rechtsgrundlage und
Aufbewahrung fest. CorrelCore stellt dir die Software; du betreibst die Instanz.

Kontakt für Betroffenenanfragen richtet sich an den Betreiber deiner Instanz
(z. B. in Impressum oder Support-Kanal des Selfhosters).

### CorrelCore Cloud (geplant, ab M12)

Für eine verwaltete Cloud-Instanz gilt ein separater Verantwortlicher — siehe
dann die auf der Landing-Page verlinkte Datenschutzerklärung (M10/M12).

---

## 2. Welche Daten werden verarbeitet?

| Kategorie           | Beispiele                            | Art. 9 DSGVO    |
| ------------------- | ------------------------------------ | --------------- |
| Stimmungsdaten      | mood, energy, stress                 | Ja              |
| Symptome            | ausgewählte Symptome, Intensität     | Ja              |
| Notizen             | Freitext zu Einträgen                | Potenziell      |
| Tags / Gewohnheiten | Aktivitäts- und Lifestyle-Tags       | Nein (abstrakt) |
| Konto               | E-Mail, Anzeigename, Passwort-Hash   | Nein            |
| Einwilligungen      | `consent_log`, Analytics-Opt-Out     | Nein            |
| Technisch           | Session-Cookies, Request-IDs in Logs | Nein            |

**Nicht verarbeitet:** Third-Party-Tracking, Werbe-Pixel, Hintergrund-Ortung.
Schlaf-/Wearable-Daten nur nach expliziter Einwilligung (M8, optional).

---

## 3. Zwecke und Rechtsgrundlagen

| Zweck                          | Rechtsgrundlage                                                     |
| ------------------------------ | ------------------------------------------------------------------- |
| Tagebuch & Stimmungserfassung  | Einwilligung Art. 6(1)(a), Art. 9(2)(a)                             |
| Korrelationsanalyse / Insights | Einwilligung; Opt-Out über `analytics_enabled`                      |
| Konto & Authentifizierung      | Vertragserfüllung Art. 6(1)(b)                                      |
| Betrieb & Fehlerbehebung       | Berechtigtes Interesse Art. 6(1)(f); keine Gesundheitsdaten in Logs |

Die Einwilligung bei Registrierung kann in den Einstellungen widerrufen werden
(Analytics deaktivieren, Konto löschen).

---

## 4. Speicherung und Sicherheit

- **Verschlüsselung at-rest:** App-Level Fernet für sensible Felder (Notizen, Symptom-Details).
- **Transport:** TLS (empfohlen über Reverse-Proxy).
- **Zugriff:** Row-Level-Security, JWT-Sessions, Rate-Limiting.
- **Logs:** Keine Klartext-Gesundheitsdaten — siehe ADR-0007.
- **Backups:** Betreiber-Verantwortung; restic-Verschlüsselung empfohlen (M9 Install-Guide).

---

## 5. Deine Rechte (DSGVO Art. 15–22)

| Recht                              | In der App                                                             |
| ---------------------------------- | ---------------------------------------------------------------------- |
| **Auskunft** (Art. 15)             | Datenexport (ZIP/JSON/CSV) unter Einstellungen                         |
| **Berichtigung** (Art. 16)         | Einträge und Profil bearbeiten                                         |
| **Löschung** (Art. 17)             | „Account löschen“ unter Einstellungen → Datenschutz                    |
| **Datenübertragbarkeit** (Art. 20) | GDPR-ZIP-Export                                                        |
| **Widerspruch Analyse** (Art. 21)  | Toggle „Analyse aktiviert“ in Einstellungen                            |
| **Einschränkung** (Art. 18)        | Support-Anfrage an Instanz-Betreiber (siehe [DSGVO.md §4](https://github.com/Sturmi77/correlcore/blob/main/docs/DSGVO.md)) |

Antwortfrist für manuelle Anfragen (Art. 18): innerhalb von 72 Stunden.

---

## 6. Weitergabe an Dritte

CorrelCore sendet **keine Gesundheitsdaten** an externe Analyse-, Werbe- oder
Cloud-LLM-Dienste. Optionaler Error-Tracking-Dienst (GlitchTip) ist
selfhosted; es werden keine Klartext-Gesundheitsdaten übermittelt.

---

## 7. Aufbewahrung

| Daten                       | Dauer                                     |
| --------------------------- | ----------------------------------------- |
| Einträge, Tags, Symptome    | Bis Account-Löschung oder Nutzer-Löschung |
| Analytics/Insights          | Rolling Window (~90 Tage, Neuberechnung)  |
| Nicht verifizierte Accounts | 7 Tage (konfigurierbar)                   |
| Error-Logs (GlitchTip)      | 90 Tage                                   |

---

## 8. Änderungen

Diese Erklärung wird bei wesentlichen Produktänderungen aktualisiert. Die
in-app-Version unter `/privacy` und diese Datei im Repository sind die
maßgeblichen Quellen für Selfhost-Nutzer.

---

## 9. Kontakt & Sicherheitsmeldungen

- **Sicherheitslücken:** siehe [SECURITY.md](https://github.com/Sturmi77/correlcore/blob/main/SECURITY.md)
- **Datenschutz-Anfragen (Selfhost):** an den Betreiber deiner Instanz
- **Projekt:** [github.com/Sturmi77/correlcore](https://github.com/Sturmi77/correlcore)

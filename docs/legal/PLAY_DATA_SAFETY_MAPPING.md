# Google Play Data Safety — Mapping-Vorlage (AP-3 / #721)

Last updated: 2026-08-17

Feld-für-Feld-Vorlage zum wahrheitsgemäßen Ausfüllen des **Data-Safety-Formulars**
in der Play Console. 🤖 Agent-Entwurf → 👤 Operator überträgt in die Console und
verantwortet die finale Richtigkeit.

**Quellen der Wahrheit:** [`docs/PRIVACY.md`](../PRIVACY.md),
[`docs/DSGVO.md`](../DSGVO.md),
[ADR-0033](../adr/0033-sensitive-health-data-handling-cycle-signals.md) (SHD),
ADR-0005 (Encryption at rest), ADR-0007 (keine Gesundheitsdaten in Logs).

> **Grundprinzip:** *Nur deklarieren, was der ausgelieferte Build wirklich tut.*
> Der Data-Safety-Umfang hängt von **AP-HC (#718)** ab: ohne HC-Permissions im
> Play-Build entfällt die HC-Zeile, ohne Push-Build entfällt die Token-Zeile.

---

## 0. Globale Antworten (gelten für alle „collected" Datentypen)

| Frage | Antwort | Begründung |
| ----- | ------- | ---------- |
| Werden Daten erhoben/übertragen? | **Ja** | App überträgt Eingaben an die konfigurierte CorrelCore-Instanz |
| Werden Daten mit Dritten **geteilt**? | **Nein** (Ausnahme prüfen: FCM, §4) | Keine Weitergabe an Werbe-/Analyse-Dienste (PRIVACY.md §6) |
| Verschlüsselung **bei der Übertragung**? | **Ja** | TLS/HTTPS (PRIVACY.md §4, ADR-0033 §4) |
| Können Nutzer **Löschung** beantragen? | **Ja** | Account-Löschung + selektive Zyklus-Löschung + Export (PRIVACY.md §5) |
| Verschlüsselung **at rest**? | Ja (App-Level Fernet für sensible Felder) | ADR-0005; **kein** Data-Safety-Pflichtfeld, aber für Review-Konsistenz notieren |

> **Selfhost-Hinweis für den Reviewer:** Die Daten fließen an die vom Nutzer
> gewählte Instanz (Selfhost oder `correlcore.com`), nicht an einen
> CorrelCore-Werbe-/Analyse-Backend. Play verlangt die Deklaration dennoch aus
> App-Sicht („collected") — das ist korrekt so.

---

## 1. Data-Type-Mapping (Play-Kategorien → CorrelCore-Realität)

| Play-Datentyp | Erhoben? | Zweck | Pflicht/Optional | Geteilt? | Anmerkung |
| ------------- | -------- | ----- | ---------------- | -------- | --------- |
| **Personal info › Email address** | Ja | Account/Auth (Art. 6(1)(b)) | Pflicht | Nein | Registrierung/Login |
| **Personal info › Name** | Ja (Anzeigename) | Personalisierung | Optional | Nein | frei wählbar |
| **Personal info › User IDs** | Ja (interne User-UUID) | Account-Zuordnung | Pflicht | Nein | keine externen IDs |
| **Health & fitness › Health info** | Ja | Tagebuch + Korrelationsanalyse (Art. 9(2)(a)) | Optional (Einwilligung) | Nein | Stimmung, Energie, Stress, Symptome, Notizen, Zyklus (SHD, ADR-0033) |
| **Health & fitness › Health info (Health Connect: Schlaf/HR)** | **Nur bei AP-HC Option B** | Schlaf↔Stimmung-Insights | Optional (HC-Consent) | Nein | **entfällt bei Option A (Play-Build ohne HC)** |
| **App activity › App interactions** | Ja (abgeleitete Insights) | Korrelations-/Trend-Berechnung | Optional (`analytics_enabled`) | Nein | Opt-out in Einstellungen |
| **App info & performance › Crash logs / Diagnostics** | Nur wenn GlitchTip aktiv | Fehlerdiagnose | Optional | Nein | selfhosted GlitchTip; **keine** Klartext-Gesundheitsdaten (ADR-0007) |
| **Device or other IDs › Device/push token** | **Nur bei Push-Build (AP-4)** | Push-Zustellung (Check-in-Erinnerung) | Optional (Notif-Consent) | **Prüfen: FCM, §4** | `device_tokens.token`; entfällt ohne `google-services.json` |
| Financial info | Nein | — | — | — | keine Zahlungsdaten in der App |
| Location | Nein | — | — | — | keine Ortung (PRIVACY.md §2) |
| Contacts / Messages / Photos / Audio / Calendar / Web history | Nein | — | — | — | nicht erhoben |

---

## 2. Notizen / Freitext (Sonderfall)

- `entries.note` ist **Freitext** und kann gesundheitsbezogene Angaben enthalten
  → wird **unter „Health info"** subsumiert, nicht als „Messages".
- At-rest Fernet-verschlüsselt (ADR-0005), nie im Klartext geloggt (ADR-0007).

## 3. Sensitive Health Data (SHD) — Zyklus (ADR-0033 §8)

Falls Zyklus-Tracking im ausgelieferten Build aktiv ist, deklarieren als:

- **Health and fitness › Other health info** (Zyklusdaten):
  **collected · not shared · encrypted · user-deletable**.
- Selektive Löschung: `DELETE /api/v1/entries/cycle-data` (ADR-0033 §6).

## 4. Offener Entscheidungspunkt — FCM-Token & „Sharing"

Der Push-Token wird zur Zustellung an **Google FCM** übergeben. Data-Safety
unterscheidet „Sharing" (Weitergabe an Dritte) von „Processing durch einen
Service-Provider zur App-Funktion".

- [ ] **Entscheiden/bestätigen (👤 Operator):** FCM-Token als „processed by a
      service provider (Google FCM) for app functionality", **nicht** als
      „shared for other purposes" — Standardauslegung für Push. Quelle:
      Google-Data-Safety-Guidance heranziehen und Ergebnis hier dokumentieren.
- Entfällt vollständig, wenn Closed Testing **ohne Push** startet (kein
  `google-services.json` → kein Token erhoben).

## 5. Aufbewahrung (Kontext, kein Play-Pflichtfeld)

| Daten | Dauer (PRIVACY.md §7) |
| ----- | --------------------- |
| Einträge/Tags/Symptome | bis Account-/Nutzer-Löschung |
| Analytics/Insights | Rolling ~90 Tage |
| Nicht verifizierte Accounts | 7 Tage (konfigurierbar) |
| Error-Logs (GlitchTip) | 90 Tage |
| Device-Token | Cascade-Löschung bei Account-Löschung (`ondelete=CASCADE`) |

## 6. Verknüpfte Play-Felder

- **Datenschutz-URL:** öffentliche Privacy-Policy (AP-3-Checkliste, aus M10-Landing) — vor Absenden auf HTTP 200 ohne Login prüfen.
- **Account-Löschung:** Play verlangt Angabe eines Löschwegs — In-App „Account löschen" (PRIVACY.md §5) + ggf. Web-Löschlink dokumentieren.

## 7. Pflege-Regel

Dieses Mapping und ADR-0033 §8 müssen **vor jeder Store-Einreichung** abgeglichen
werden. Änderungen am Datenmodell (z. B. neue Domänen wie Food-Tracking #715,
Wearable-Import) erfordern ein Update dieser Tabelle **vor** dem Rollout.

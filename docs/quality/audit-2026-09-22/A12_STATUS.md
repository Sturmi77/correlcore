# A12 – Geräte-, Betriebs- und Nutzerabnahmen

Stand: 23.09.2026. Audit-Basis: `71d1089ff77388cadf2253ac67d1471dfa99fa40`.

## Status

**Alle A12-Gates sind offen.** Es liegen im Repository keine aktuellen Nachweise für
Interviews, reale Health-Connect-/Play-Geräte, die Hosted-Produktionskonfiguration,
eine Staging-Migration des finalen Kandidaten oder dessen Backup-Restore vor. Frühere
Labor- und Sideload-Nachweise werden als Vorarbeiten wiederverwendet, gelten aber nicht
als Abnahme des neuen Release-Kandidaten.

Der maschinenlesbare [A12-Abnahmestand](A12_ACCEPTANCE_REGISTER.json) enthält sieben
Gates. [Der Validator](verify_a12_acceptance.py) verhindert, dass ein Gate ohne
vollständigen Kandidatenbezug, Evidenz und Sign-off auf `passed` gesetzt wird. Der
[A12-Laufplan](A12_ACCEPTANCE_RUNBOOK.md) beschreibt die Durchführung, ohne bestehende
Operator-Checklisten zu duplizieren.

| Gate                           | Status           | Verantwortliches Tracking                                                                                                                                                                                                                  | Fehlender Nachweis                                                                                        |
| ------------------------------ | ---------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | --------------------------------------------------------------------------------------------------------- |
| Nutzerverständnis #930 H.4     | Extern blockiert | [#930](https://github.com/Sturmi77/correlcore/issues/930), [#986](https://github.com/Sturmi77/correlcore/issues/986)                                                                                                                       | 4–6 Gespräche, Befunde, umgesetzte Änderungen und Nachtest                                                |
| Health Connect / M8            | Extern blockiert | [#986](https://github.com/Sturmi77/correlcore/issues/986)                                                                                                                                                                                  | reale Android-/OS-Matrix für Consent, Berechtigungen, Import, Zeitbezug, Widerruf und Wiederholung        |
| Hosted Beta                    | Extern blockiert | [#621](https://github.com/Sturmi77/correlcore/issues/621)                                                                                                                                                                                  | Owner-Abgleich gegen tatsächlichen Hosted-Betrieb                                                         |
| Firebase / Play                | Extern blockiert | [#717](https://github.com/Sturmi77/correlcore/issues/717), [#722](https://github.com/Sturmi77/correlcore/issues/722), [#723](https://github.com/Sturmi77/correlcore/issues/723), [#724](https://github.com/Sturmi77/correlcore/issues/724) | FCM-Zustellung/Abmeldung/Fehlerfälle, Pre-Launch-Report und Closed-Testing-Sign-off                       |
| Compare Device-QA              | Extern blockiert | [#585](https://github.com/Sturmi77/correlcore/issues/585)                                                                                                                                                                                  | offene Strip-Zoom-, Persistenz- und Performance-Zeilen auf realem Gerät                                   |
| Laufzeit-Sicherheit            | Extern blockiert | [#986](https://github.com/Sturmi77/correlcore/issues/986)                                                                                                                                                                                  | redigierter Ist-Abgleich von DB-Rollen/RLS, TLS/Proxy, Cookies und Worker                                 |
| Deployment / Wiederherstellung | Extern blockiert | [#986](https://github.com/Sturmi77/correlcore/issues/986)                                                                                                                                                                                  | finaler SHA + Image-Digests, v1.9.1-Staging-Upgrade, Smoke, Restore und spätere Produktions-Smoke-Prüfung |

## Abgrenzung vorhandener Nachweise

- [#429](https://github.com/Sturmi77/correlcore/issues/429) belegt signierte
  Sideload-Releases bis v1.0.8. Der Abschlusskommentar nennt Play Console, App Signing,
  Closed Testing, Data Safety, Store Assets und den Pre-Launch-Report ausdrücklich als
  nicht durchgeführt. Diese Punkte bleiben daher in #717/#719–#724 offen.
- [`M9_BACKUP_RESTORE_TEST.md`](../M9_BACKUP_RESTORE_TEST.md) belegt einen früheren
  Labor-Restore. A12 verlangt denselben Nachweis mit v1.9.1-Datenfixture und den
  Digests des finalen Kandidaten in Staging.
- Automatisierte Android-, Backend- und Browser-Tests sind Vorbedingungen. Sie ersetzen
  weder eine reale OS-/Gerätematrix noch den Abgleich der tatsächlichen
  Produktionskonfiguration.

## Freigaberegel

1. A10 friert den zu prüfenden Commit und die gebauten Image-Digests ein.
2. A12 führt alle für den angebotenen Releaseumfang relevanten Gates genau auf diesem
   Kandidaten aus.
3. Staging-Migration, Smoke und Restore müssen bestanden sein, bevor ein Deployment
   freigegeben wird.
4. Die Produktions-Smoke-Prüfung erfolgt erst nach dem kontrollierten Deployment und
   ist ein eigenes nachgelagertes Gate.
5. Fehlende Zugänge, Geräte oder Gesprächspartner bleiben `blocked_external`; sie
   werden nie durch Annahmen oder frühere Releases ersetzt.

Ein PR für diesen vorbereitenden A12-Stand verwendet `Relates to #986`. `Closes` oder
`Fixes` ist erst zulässig, wenn Register, Evidenz und Sign-offs vollständig sind.

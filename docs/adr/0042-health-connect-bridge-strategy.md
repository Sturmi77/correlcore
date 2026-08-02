# ADR-0042: Health Connect via a thin custom Capacitor plugin

**Datum:** 2026-08-02
**Status:** Accepted
**Kontext-Meilenstein:** M8 Sprint 3 (#172)

---

## Kontext

M8 Sprint 3 liest Schlaf- und Herzfrequenz-Daten aus **Health Connect** (on-device,
Android) in die Capacitor-App. Zwei Wege standen zur Wahl:

1. **`@capacitor-community/health-connect`** — fertiges Community-Plugin.
2. **Eigenes dünnes Kotlin-Capacitor-Plugin** direkt auf
   `androidx.health.connect:connect-client`.

Randbedingungen:

- Das Repo ist gerade auf **Capacitor 8** migriert (#619). Die Cap-8-Unterstützung des
  Community-Plugins ist zum Entscheidungszeitpunkt unsicher.
- Es existiert bereits ein etabliertes Muster **dünner eigener Kotlin-Plugins**
  (`push/`, `widget/`, `session/` unter `de/correlcore/app/`).
- Ziel ist **Datenminimierung** (nur Schlaf + HR, technisch erzwungen) und
  F-Droid-/Sideload-Tauglichkeit ohne unnötige transitive Abhängigkeiten.

---

## Entscheidung

**Eigenes dünnes Kotlin-Plugin** (`HealthConnectPlugin`), das direkt gegen
`androidx.health.connect:connect-client` arbeitet. Kein Community-Plugin.

Umfang Sprint 3 (Bridge, **kein** Backend-Import — das ist Sprint 4):

- `isAvailable` — HealthConnect-SDK-Status auf dem Gerät.
- `checkPermissions` / `requestPermissions` — nur `READ_SLEEP` + `READ_HEART_RATE`.
- `readSleepAndHeartRate(start, end)` — liest `SleepSessionRecord` +
  `HeartRateRecord` und gibt normalisierte Werte an die WebView zurück.

Der JS-Zugriff ist zusätzlich durch `canUseHealthConnectImport()` (DSGVO Art. 9
Consent, #31) gegated.

---

## Alternativen erwogen

| Option                       | Vorteile                                                                                                       | Nachteile                                                                                                                 |
| ---------------------------- | -------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------- |
| **Community-Plugin**         | Weniger eigener Code                                                                                           | Cap-8-Kompatibilität unsicher; Dritt-Dep + transitive Deps; weniger Kontrolle über Datenminimierung; F-Droid-Fragezeichen |
| **Eigenes Kotlin-Plugin** ✅ | Kein Cap-8-Risiko, keine Dritt-Dep, volle Kontrolle über Permission-Umfang, konsistent mit push/widget/session | Mehr Kotlin-Code, eigene Wartung der HC-Client-Version                                                                    |

---

## Konsequenzen

- Neue Gradle-Abhängigkeit `androidx.health.connect:connect-client` (Version in
  `variables.gradle` gepinnt; bei HC-Client-Updates mitziehen).
- Manifest deklariert exakt zwei Health-Permissions plus den Rationale-Intent-Filter.
- **Verifikation:** Der native Pfad wird **nicht** in CI ohne Android-SDK gebaut; nur
  `pnpm --filter @correlcore/android validate` (config-only) läuft. Geräte-QA
  (Permission-Flow, Sideload-APK, gehärtete ROMs) ist manuell — siehe
  [`docs/features/HEALTH_CONNECT.md`](../features/HEALTH_CONNECT.md).
- Play-Store-**Declaration** der Datentypen bleibt an den späteren Play-Exit gekoppelt
  (nicht Teil dieses ADR / dieser Sprint-Arbeit).

# ADR-0002: Capacitor statt TWA als Mobile-Strategie

**Datum:** 2026-04-20
**Status:** Accepted

---

## Kontext

- **TWA (Trusted Web Activity via Bubblewrap)** war die ursprünglich geplante Mobile-Strategie: die SvelteKit-PWA wird als TWA-Shell in den Play Store gebracht, ohne nativen Code.
- **Play-Store-Policies** können TWA-Apps jederzeit ablehnen oder entfernen, wenn sie zu wenig „native" wirken (Spielraum der Policy-Interpretation liegt bei Google).
- **Health Connect** (Android API für Garmin- und Wearable-Daten) ist über TWA nicht direkt zugänglich – der Zugriff erfordert native Android-Bridges.
- **Push Notifications** via Web Push im TWA-Kontext sind unzuverlässiger als FCM (Firebase Cloud Messaging), besonders auf Geräten mit aggressivem Doze-Mode.
- **Capacitor** (Ionic) wrappt dieselbe SvelteKit-Codebase in eine native Android-App und stellt offizielle Plugin-Bridges für native APIs bereit.

---

## Entscheidung

**Capacitor** wird als Mobile-Strategie eingesetzt. TWA/Bubblewrap wird aufgegeben.

Die SvelteKit-Codebase bleibt unverändert. Capacitor wird als zusätzlicher Build-Step eingeführt, der das SvelteKit-Build-Output in eine native Android-App einbettet.

---

## Alternativen erwogen

| Option               | Vorteile                                                                                                     | Nachteile                                                                                                     |
| -------------------- | ------------------------------------------------------------------------------------------------------------ | ------------------------------------------------------------------------------------------------------------- |
| **TWA (Bubblewrap)** | Kein nativer Code, minimaler Aufwand, bestehende PWA direkt nutzbar                                          | Play-Store-Policy-Risiko, kein Health Connect, unzuverlässige Push Notifications, kein Zugang zu nativen APIs |
| **Capacitor** ✅     | SvelteKit-Code unverändert, offizielle Plugin-Bridges (Health Connect, FCM), Play-Store-konform, CI/CD-fähig | Zusätzlicher Build-Step, Android Studio für Plugin-Updates nötig, etwas höhere Build-Komplexität              |
| **React Native**     | Ausgereiftes natives Ökosystem, große Community, gute Performance                                            | Komplette Neuimplementierung des UI-Layers (Svelte → React), massiver Mehraufwand, Code-Duplikation           |
| **Flutter**          | Exzellente native Performance, eigenes Rendering, starke UI-Konsistenz                                       | Komplette Neuimplementierung in Dart, kein Code-Sharing mit SvelteKit, noch höherer Aufwand als React Native  |

---

## Konsequenzen

- **SvelteKit-Code bleibt unverändert.** Capacitor konsumiert den `build/`-Output als statisches Web-Asset.
- **Health Connect** ist über das Plugin `@capacitor-community/health-connect` zugänglich → Garmin- und Wearable-Daten können direkt aus der Android Health Connect API gelesen werden.
- **FCM** (Firebase Cloud Messaging) via `@capacitor/push-notifications` ist nativ und zuverlässig verfügbar.
- **Build-Komplexität** ist etwas höher (separater `capacitor build android` Step), aber vollständig in CI/CD (GitHub Actions) abbildbar.
- **M11** bleibt im Zeitplan: Capacitor-Setup verursacht ≤ 1 Woche Mehraufwand gegenüber der ursprünglich geplanten TWA-Integration.
- **iOS** (App Store) ist via Capacitor ebenfalls erreichbar, falls in einer späteren Phase relevant.

---

## Umsetzung

| Meilenstein                  | Aufgabe                                                                                                      |
| ---------------------------- | ------------------------------------------------------------------------------------------------------------ |
| **M4** (Mobile Polish)       | Capacitor einrichten, Android-Build-Pipeline aufsetzen, Health Connect Plugin integrieren, FCM konfigurieren |
| **M11** (Play Store Release) | Play Store Release via Capacitor-Build, App-Signing-Konfiguration in CI/CD                                   |

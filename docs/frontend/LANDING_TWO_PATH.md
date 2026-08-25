# Landing: Zwei-Pfade-Konzept (Hosted-Laie vs. Self-host) — I1 (#735)

> **Status:** Konzept / Review. Noch nicht implementiert.
> **Kontext:** #731 (Modernisierung), #735 I1 (Positionierung), #734 (Blocker, erledigt).
> **Baut auf:** [`selfhost/INSTANCE_MODE.md`](../selfhost/INSTANCE_MODE.md) (Runtime-Mode, #736),
> [`MARKET_ANALYSIS.md`](../MARKET_ANALYSIS.md) (Zielgruppen).

## 1. Problem (I1)

Die Landing bedient heute zwei Zielgruppen gleichzeitig — Laien („verstehe deine
Tage") **und** Selfhoster/Devs (Docker, AGPL, APK) — auf **einer** undifferenzierten
Seite und damit keine richtig. Es gibt keine bewusste Führung: Charts kommen vor der
ersten Einordnung, und die einzige mode-abhängige Anpassung ist die primäre CTA
(via Instance-Mode). Es fehlt eine **Informationsarchitektur, die den Besucher nach
Absicht führt**.

## 2. Was bereits existiert (nicht neu erfinden)

- **Instance-Mode (Runtime, #736):** `/api/v1/instance → { mode, registration_enabled,
  version }`. Ein Bundle, das per Truth-Table **eine** primäre CTA + Badge setzt. Der
  `instanceConfig`-Store liegt schon im Frontend vor und wird in `LandingPage.svelte`
  konsumiert (`showRegisterCta`, `badgeText`).
- **Zielgruppen (Market-Analysis):** (a) **Lifestyle/Laie** — Remote-Worker 30–50,
  „erwachsene Reflexion statt Punkte-Jagd"; (b) **Selfhost/Dev/Privacy-affin** —
  r/selfhosted, ehrlicher `docker compose up`, AGPL. Tiers: **Selfhost Free (0€)** vs.
  Hosted-SaaS (Billing erst M12).

**Konsequenz:** Instance-Mode ist **pro Deployment exklusiv** — ein anonymer Besucher
sieht immer nur einen Modus. Das Zwei-Pfad-Konzept ist deshalb **mode-aware**: dieselbe
Seite, aber welche Spur betont wird und wohin die CTAs zeigen, leitet sich aus
`instanceConfig` ab. So bleibt I1 konsistent mit #736 statt es zu duplizieren.

## 3. Entscheidung (gewählte Variante: „Pfad-Wahl oben")

Single-Page bleibt. **Oberhalb der Chart-Flut** ein **Pfad-Chooser** mit zwei
Optionen, der zu zwei klar getrennten, verankerten Abschnitten führt. Der Hero bleibt
mode-adaptiv (wie heute).

```
Header (mode-adaptive CTA)
Hero (Titel, Plain-Copy, Trust-Belege, Strip-Visual)   ← unverändert
────────────────────────────────────────────────────────
PFAD-CHOOSER  ▸ „Ich will es ausprobieren"  |  „Ich will es selbst hosten"
   (Anker-Links, keine Route; mode-aware Reihenfolge/Emphase)
────────────────────────────────────────────────────────
#try   — Hosted/Laie: 60-Sekunden-Check-in-Shot (I2) + eine primäre CTA (I4)
#host  — Selfhoster: Ops-Substanz (I7) + eine primäre CTA (docs/repo)
────────────────────────────────────────────────────────
Beweis-Sektionen (Previews, Weekday, Bento, Journey …)  ← bestehend
FAQ / Footer
```

### 3.1 Die zwei Pfade

| | **Pfad A — „Ausprobieren" (`#try`)** | **Pfad B — „Selbst hosten" (`#host`)** |
|---|---|---|
| Zielgruppe | Laie / Lifestyle | Selfhoster / Dev / Privacy |
| Versprechen | „In 60 Sekunden pro Tag eintragen, die App zeigt Zusammenhänge" | „Deine Daten, deine Maschine — `docker compose up`, AGPL" |
| Inhalt | **Check-in-Shot (I2)** — die tägliche Eingabemaske, nicht nur Auswertung | **Ops-Substanz (I7)** — Systemanforderungen, Postgres/Volumes, Backup, Reverse-Proxy/TLS, Update-Pfad, ARM/NAS, ENV (kuratiert aus vorhandener Doku, kein Rebuild) |
| Primäre CTA (I4) | **Create account** (mode-aware, s. u.) | **Self-host guide** → `DOCS_SITE_URL` |
| Sekundär | „Oder selbst hosten" → `#host` | „Oder die gehostete Version testen" → `#try`/Registrierung, **GitHub** |

### 3.2 Mode-Awareness (erweitert die INSTANCE_MODE-Truth-Table)

Der Chooser zeigt **immer beide** Pfade (Devs auf correlcore.com sollen wissen, dass sie
selbst hosten können; Laien auf einer offenen Selfhost-Instanz sollen registrieren
können). **Emphase und CTA-Ziel** folgen dem Modus:

| Backend meldet | Default-Pfad (betont) | Pfad-A-CTA | Pfad-B-CTA |
|---|---|---|---|
| `mode=hosted` | **A (Ausprobieren)** | Create account → `/auth/register` | Self-host guide → docs + GitHub |
| `mode=selfhost`, `registration_enabled=true` | **A** | Create account (**auf dieser Instanz**) → `/auth/register` | Über das Projekt / selbst hosten → docs |
| `mode=selfhost`, `registration_enabled=false` | **B (Selbst hosten)** | *(entfällt / „Log in")* | Self-host guide → docs |
| Deskriptor nicht erreichbar | **B** (Safe Fallback, wie heute) | — | Self-host guide → docs |

Die bestehende `showRegisterCta`/`badgeText`-Logik bleibt die Quelle der Wahrheit; der
Chooser konsumiert sie nur zusätzlich.

## 4. Zusammenspiel mit weiteren #735-Punkten

Dieses Konzept ist der **Träger** für mehrere offene Punkte — sie werden hier verortet,
aber in eigenen Schritten umgesetzt:

- **I2** (60-Sek-Check-in) → Inhalt von Pfad A.
- **I4** (eine primäre CTA) → genau eine dominante CTA **pro Pfad**; APK/Obtainium raus
  aus dem Above-the-fold, in Pfad B bzw. Android-Sektion.
- **I7** (Ops-Substanz) → Inhalt von Pfad B.
- **I12** (Wert + Aktion früher) → der Chooser liefert genau das oberhalb der Charts.

Bereits erledigt und kompatibel: I3 (Jargon), I5 (Trust-Belege), I6 (Anti-Gamification
entdoppelt), I9/I10/I11 (Effekt-Budget, Previews, Weekday-Legende).

## 5. Verhalten / Barrierefreiheit

- **Anker, keine Routen:** Der Chooser sind zwei In-Page-Links (`#try`/`#host`) plus
  `scrollIntoView`. Kein SPA-Routing, kein zusätzlicher Ladepfad.
- **Ohne JS nutzbar:** Beide Abschnitte sind immer im DOM und sichtbar; der Chooser
  funktioniert als reine Ankernavigation auch ohne JS. (Konsistent mit `@media
  (scripting: none)` der Reveals.)
- **Reduced-Motion:** kein Auto-Scroll-Effekt erzwingen; `scrollIntoView({ behavior })`
  respektiert die Nutzerpräferenz.
- **Tastatur/Screenreader:** Chooser als Liste von Links mit klaren Labels; die
  Zielabschnitte tragen `id` + `tabindex="-1"` für Fokus-Sprung.
- **i18n:** neue Keys unter `landing.paths.*` (DE/EN-Parität), keine Fachbegriffe im
  Chooser (I3-konform).

## 6. Scope

**In diesem Konzept (I1):** die IA — Chooser oben, zwei verankerte Abschnitte,
Mode-Awareness der Emphase/CTAs, i18n-Gerüst.

**Nicht hier (Folgeschritte):** die eigentlichen Inhalte von Pfad A (I2) und Pfad B
(I7), die CTA-Bereinigung (I4). Diese werden nach Freigabe dieses Konzepts einzeln
umgesetzt.

## 7. Offene Fragen (für Review)

1. **Default-Emphase auf Selfhost-Instanzen mit offener Registrierung:** Pfad A
   (registrieren) oder neutral? Vorschlag oben: A, weil offene Registrierung „diese
   Instanz nutzen" bedeutet.
2. **Chooser-Optik:** zwei große Karten (empfohlen, klar) vs. Tab-/Segmented-Control.
3. **APK/Android:** als dritter Mini-Pfad im Chooser oder weiter als eigene Sektion?
   Vorschlag: eigene Sektion, im Chooser nicht als gleichwertiger dritter Pfad
   (vermeidet die alte CTA-Überladung, I4).

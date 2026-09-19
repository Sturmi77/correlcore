# Play Store Listing — Copy-Entwurf (AP-2 / #720)

Last updated: 2026-09-19

Entwurf der Store-Listing-Texte für Google Play (Internal → Closed Testing).
🤖 Agent-Entwurf → 👤 Operator prüft/freigibt und pflegt in der Play Console.

**Leitplanken (verbindlich):**

- **Keine medizinischen Aussagen / Health-Claims** (keine Diagnose, keine
  Vorhersage, keine Fruchtbarkeits-/Verhütungsaussagen) — konsistent mit
  ADR-0033 §9 und dem produktweiten „non-medical"-Prinzip.
- **Kein Gamification-Wording** (keine Streaks, keine „Belohnungen") — Kern-USP.
- **Arbeitsmuster-Vokabular (#930 G3), kein klinisches Framing** — siehe
  [`docs/features/arbeitsmuster-vokabular.md`](../features/arbeitsmuster-vokabular.md).
  Kein Burnout-Label, keine Präventions-Claims, keine Inventare (MBI/CBI).
  Mood/Habit bleiben im Alltagstext; `work_context` ist Feld, nicht Kategorie-Titel.
- Konsistent mit README-USP: _Korrelationen statt Rohdaten · Privacy-first ·
  Selfhosted & offline-ready · 60 Sekunden/Tag_.
- Die App ist ein **Client zu einer CorrelCore-Instanz** (Selfhost oder
  `correlcore.com`) — die Texte dürfen keine reine Standalone-Cloud-App suggerieren.

---

## Deutsch (Primär-Locale de-DE)

### App-Name

```
CorrelCore
```

### Kurzbeschreibung (max. 80 Zeichen)

> Verstehe, warum manche Tage gut sind — Privacy-first, in 60 Sekunden pro Tag.

_(76 Zeichen inkl. Leerzeichen — vor Veröffentlichung nachzählen)_

Alternative (72 Zeichen):

> Dein Wohlbefinden verstehen: Korrelationen statt Rohdaten. Privacy-first.

### Langbeschreibung (max. 4000 Zeichen)

```
CorrelCore hilft dir zu verstehen, WARUM manche Tage gut sind und andere nicht –
aus einem 60-Sekunden-Check-in pro Tag.

Viele spüren, dass Schlaf, Bewegung, Homeoffice-Tage oder soziale Kontakte ihr
Wohlbefinden beeinflussen – wissen aber selten, WELCHE Faktoren wirklich zählen,
wie stark und mit welcher zeitlichen Verzögerung. CorrelCore schließt diese
Lücke: Es zeigt Muster in deinen eigenen Daten, statt nur Stimmungs-Emojis zu
sammeln.

WAS CORRELCORE ANDERS MACHT

• Korrelationen statt Rohdaten: Die App erklärt Zusammenhänge – nicht bloß
  Zahlenreihen.
• Privacy-first: Deine Daten bleiben auf deiner Instanz (Selfhost) oder der von
  dir gewählten CorrelCore-Instanz. Keine Weitergabe an Werbe- oder
  Analyse-Dienste.
• 60 Sekunden pro Tag: Ein kurzer Check-in genügt – mehr braucht es nicht.
• Kein Gamification: Du sammelst Datenpunkte – keine Streaks, keine Punkte,
  keine Jagd nach App-Öffnungen.
• Arbeitsmuster ohne Klinik-Framing: optionaler Hinweis auf Belastung und
  Erholung aus deinen eigenen Einträgen – Muster und Hinweise, keine Diagnose
  und nichts für einen Arbeitgeber.

FUNKTIONEN

• Täglicher Check-in: Stimmung, Energie, Stress und frei wählbare Tags für
  Aktivitäten und Gewohnheiten.
• Arbeitssituation als Kontextfeld (z. B. Homeoffice, Büro, Wochenende) – nicht
  als Produktkategorie.
• Insights: Zusammenhänge zwischen Lebensgewohnheiten und Wohlbefinden – mit
  ehrlicher Einordnung, wie belastbar ein Muster ist; bei Bedarf Signal-Detail
  zum Nachprüfen.
• Optional: Belastung & Erholung als dünnes Overlay auf bestehenden Daten
  (opt-in in den Einstellungen).
• Trends: Verlaufsansichten und Vergleiche über Zeiträume.
• Homescreen-Widget: Tages-Status und Schnell-Eintrag direkt vom Startbildschirm.
• Datenhoheit: Export deiner Daten (ZIP/JSON/CSV) und Löschung jederzeit in den
  Einstellungen.

FÜR WEN

Für alle, die ihr Wohlbefinden und ihre Arbeitsmuster in den eigenen Daten
verstehen wollen, ohne Gesundheitsdaten in eine Werbe-Cloud zu geben. CorrelCore
lässt sich selbst hosten und funktioniert offline-fähig als PWA.

HINWEIS

CorrelCore zeigt Muster in deinen eigenen Daten. Es ist kein Medizinprodukt,
stellt keine Diagnosen und gibt keine medizinischen Empfehlungen. Es ist keine
Burnout-App und kein klinisches Inventar. Bei gesundheitlichen Fragen wende
dich an medizinisches Fachpersonal.

CorrelCore verbindet sich mit deiner eigenen CorrelCore-Instanz oder einer von
dir gewählten Instanz. Open Source (AGPL-3.0).
```

---

## English (Locale en-US)

### App name

```
CorrelCore
```

### Short description (max. 80 chars)

> Understand why some days are good — privacy-first, in 60 seconds a day.

_(70 chars — recount before publishing)_

### Full description (max. 4000 chars)

```
CorrelCore helps you understand WHY some days are good and others are not — from
a 60-second daily check-in.

Many people sense that sleep, exercise, remote-work days, or social contact shape
their wellbeing — but rarely know WHICH factors actually matter, how strongly, and
with what time delay. CorrelCore closes that gap by showing patterns in your own
data, instead of just collecting mood emojis.

WHAT MAKES CORRELCORE DIFFERENT

• Correlations, not raw data: the app explains relationships — not just rows of
  numbers.
• Privacy-first: your data stays on your instance (self-host) or the CorrelCore
  instance you choose. Never shared with advertising or analytics services.
• 60 seconds a day: a short check-in is enough — nothing more.
• No gamification: you collect data points — no streaks, no points, no chasing
  app opens.
• Work patterns without clinical framing: an optional load-and-recovery hint from
  your own entries — patterns and hints, not a diagnosis, and never for an
  employer.

FEATURES

• Daily check-in: mood, energy, stress, and freely chosen tags for activities
  and habits.
• Work context as a field (e.g. remote, office, weekend) — not a product
  category.
• Insights: relationships between your habits and wellbeing — with an honest
  read on how reliable each pattern is; open a signal detail when you want to
  verify.
• Optional: load & recovery as a thin overlay on existing data (opt-in in
  Settings).
• Trends: history views and comparisons across time ranges.
• Home-screen widget: today's status and quick entry right from your launcher.
• Data ownership: export your data (ZIP/JSON/CSV) and delete it anytime in
  Settings.

WHO IT'S FOR

For anyone who wants to understand their wellbeing and work-day patterns in their
own data without handing health data to an advertising cloud. CorrelCore can be
self-hosted and works offline-capable as a PWA.

NOTE

CorrelCore shows patterns in your own data. It is not a medical device, does not
provide diagnoses, and does not give medical advice. It is not a burnout app and
not a clinical inventory. For health questions, consult a qualified healthcare
professional.

CorrelCore connects to your own CorrelCore instance or one you choose. Open
source (AGPL-3.0).
```

---

## Grafik-Assets (👤 Operator erstellt; Zielformate)

| Asset                     | Format                                     | Quelle                                                   |
| ------------------------- | ------------------------------------------ | -------------------------------------------------------- |
| App-Icon                  | 512×512 PNG (32-bit, Alpha)                | `docs/assets/brand/correlcore-logo-mark.svg` exportieren |
| Feature-Graphic           | 1024×500 PNG/JPG                           | Brand-Farben + Logo; kein Text-Overkill                  |
| Phone-Screenshots         | ≥ 2 (empf. 4–8), 16:9 o. 9:16, min. 320 px | Realgerät/Emulator                                       |
| Tablet-Screenshots 7"/10" | nur falls Tablet-Support deklariert        | optional                                                 |

## Screenshot-Shotlist (empfohlen, 5 Stück)

1. **Täglicher Check-in** — Entry-Form mit Stimmung/Energie/Stress (der „60-Sekunden"-Claim visuell).
2. **Insights** — eine Korrelations-/Insight-Karte mit ehrlicher Stärke-Einordnung (optional: Signal-Detail).
3. **Trends** — Verlaufs-/Compare-Ansicht über einen Zeitraum.
4. **Homescreen-Widget** — Widget auf dem Startbildschirm + „+ Eintrag".
5. **Datenschutz/Einstellungen** — Export + „Account löschen" (Datenhoheit sichtbar).

> Screenshots ohne echte personenbezogene Daten aufnehmen (Demo-Account/Seed).
> Belastung-Overlay nur zeigen, wenn der Demo-Account es opt-in hat — und nur als
> Hinweis/Muster, nie mit Burnout-Labeling.

## Weitere Pflichtfelder (👤 Operator in Console)

- [ ] Kategorie: „Gesundheit & Fitness" oder „Lifestyle" (Owner-Entscheidung; kein Health-Claim in der Copy; **nicht** „Burnout"/Occupational Health als Anker)
- [ ] Tags/Keywords
- [ ] Content-Rating-Fragebogen
- [ ] Kontakt-E-Mail + Website (`correlcore.com`)
- [ ] Datenschutz-URL (siehe AP-3 / #721)

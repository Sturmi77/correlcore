# CorrelCore — Markt- und Wettbewerbsanalyse

**Version:** 0.2
**Datum:** 2026-05-16
**Quelle:** Desk Research + Analyse Google Play, App Store, LinkedIn, Crunchbase, GitHub

**Changelog:**

- v0.2 (2026-05-16): HabitHeat und Habit Tracker — Completer ergänzt (Indie- und Minimalist-Wettbewerber)

---

## 1. Marktüberblick

Der Mood- und Habit-Tracker-Markt ist fragmentiert, wird von wenigen Indie-Playern dominiert und zeigt eine klare Konsolidierung auf Freemium-Abo-Modelle. Fast alle Marktführer sind Teams von 2–10 Personen — ein Solo-Dev-Einstieg ist realistisch.

**Benchmarks:**

- Bearable (~770k USD ARR bei 500k+ Downloads): ~1,50 USD Revenue/Download
- Daylio (10M+ Downloads, 4.7 Rating): Dominiert durch First-Mover-Effekt (seit 2015)
- Abo-Apps wachsen jährlich ~15,8% beim User-Spending

---

## 2. Wettbewerber im Detail

### Daylio — der Platzhirsch

| Attribut  | Details                                                |
| --------- | ------------------------------------------------------ |
| Downloads | 10M+ (Play Store)                                      |
| Rating    | 4.7/5                                                  |
| Team      | Habitics (Samuel Bednar, Bratislava, gegr. 2015)       |
| Preis     | Free (mit Ads) + Premium 4,99 $/Mon. oder 35,99 $/Jahr |
| Plattform | Android + iOS                                          |

**Stärken:** Bullet-Journal-Ansatz ohne Tippzwang, sehr schnelle Einträge, umfangreiche Statistiken, „Year in Pixels", Goals, starke Customization, breite kostenlose Basis.

**Schwächen:** UI nicht besonders modern, viele Stats nur in Premium, kein automatisches Cloud-Backup in Free-Version, Korrelationsanalyse oberflächlich (nur Activity-Counts, keine echte Regression), enthält Ads.

**Für CorrelCore relevant:** Daylio ist mit 10M+ Downloads nicht frontal schlagbar. Positionierung als „Daylio für Privacy-Nerds mit Wearables" ist realistisch.

---

### Bearable — der Health-Fokus-Spezialist

| Attribut     | Details                                                 |
| ------------ | ------------------------------------------------------- |
| Downloads    | 500k+ (Play Store)                                      |
| Rating       | 4.5/5                                                   |
| Team         | Bearable Ltd (James Saady, London, gegr. 2019), < 10 MA |
| Finanzierung | ~204k USD Seed                                          |
| ARR          | ~770k USD                                               |
| Preis        | Free + Abo (ca. 4,99 $/Mon.)                            |

**Stärken:** Sehr starker Fokus auf Symptom-Tracking + Korrelationsanalyse (Chronic Illness, Bipolar, Migräne, PCOS), Medikamenten-Tracking, Schlafdaten, Energielevel; „built by patients", explizite Ärzte-Empfehlungen.

**Schwächen:** Hoher Tracking-Aufwand (Konfigurations-Overhead), Zielgruppe chronisch Kranke → weniger Lifestyle-Feeling, Datenhoheit: Cloud-basiert, nur 500k Downloads trotz 6 Jahren.

**Für CorrelCore relevant:** Bearable zeigt, dass Korrelationsanalyse als USP funktioniert. Die Lifestyle-Zielgruppe (nicht chronisch krank) ist eine offene Lücke.

---

### Moodflow — der kostenlose Herausforderer

| Attribut  | Details                              |
| --------- | ------------------------------------ |
| Downloads | 100k–500k                            |
| Team      | Kleines Indie-Studio (iOS seit 2019) |
| Preis     | Kostenlos (Opt-in-Ads)               |

**Stärken:** Free ohne Ad-Zwang, Daten lokal auf dem Gerät, moderne UI, Mood-Kalender/Symptome/Habits/Gratitude/Routinen/Foto-Album, Insights über Zusammenhänge.

**Schwächen:** Monetarisierungsmodell unklar/fragil, kleinerer Feature-Umfang bei Statistik, kein Wearables-Sync.

---

### How We Feel — der wissenschaftliche Non-Profit

| Attribut  | Details                                       |
| --------- | --------------------------------------------- |
| Downloads | 1M+                                           |
| Team      | Ben Silbermann, Marc Brackett (Yale-Methodik) |
| Preis     | Komplett kostenlos, spendenfinanziert         |

**Stärken:** Wissenschaftlich basiert (RULER-Methodik, 144 Emotionswörter), Mini-Kurse zu Emotionsregulation, keine Ads.

**Schwächen:** Fokus auf Emotionsvokabular, keine tiefe Korrelationsanalyse zwischen Lifestyle-Variablen, nachhaltige Finanzierung abhängig von Spenden.

---

### HabitHeat — der Indie-Heatmap-Webtracker

| Attribut     | Details                                                                                     |
| ------------ | ------------------------------------------------------------------------------------------- |
| URL          | [habitheat.com](https://habitheat.com/) (Vercel-gehostet)                                   |
| Repository   | [BaraniVA/Habitheat](https://github.com/BaraniVA/Habitheat) (MIT-Lizenz)                    |
| Downloads    | „hundreds of users" (Eigenangabe Reddit, kein App-Store)                                    |
| Team         | Solo-Indie-Entwickler (BaraniVA), seit ~2025                                                |
| Preis        | 100% kostenlos, keine Ads                                                                   |
| Plattform    | Web only (PWA-fähig, responsive) — kein iOS/Android-Native                                  |
| Tech-Stack   | React 18 + TypeScript + Tailwind + Vite (Frontend), Node/Express (Backend)                  |
| Datenhaltung | Hybrid: LocalStorage **plus** Backend mit User-Auth (Passport.js, Google OAuth, Cloudinary) |

**Stärken:**

- Vielseitige Tracking-Typen: Binary, Numerisch, Mood (gut/neutral/schlecht), **Timer-basiert** (Start/Stop für Zeit-Tracking — selten am Markt).
- GitHub-Style-Heatmap als zentrales Visualisierungselement, prägnante Marke.
- Embryonale Mood-Tracking-Integration mit 5-Punkte-Skala plus Energie- und Stress-Level + Notizen → konzeptionell ähnlich zu CorrelCore.
- Gamification-Layer (Achievements, Challenges, Difficulty Levels) für Habit-Aufbau-Zielgruppe.
- „Smart Insights" als geplantes Differenzierungs-Feature (laut Reddit-Roadmap des Entwicklers in Arbeit).
- MIT-Lizenz + öffentliches Repo = theoretisch self-hostbar (npm run dev läuft).
- Habit-Templates und Kategorien (Health, Learning, Mindfulness) senken Einstiegshürde.

**Schwächen:**

- **Architektur-Widerspruch zur Privacy-Botschaft:** README sagt „all data stored locally", Codebase enthält aber Backend mit User-Models, OAuth und Cloudinary-Upload — die tatsächliche Datenhaltung ist intransparent.
- Kein offizielles Selfhost-Deployment (kein Dockerfile, kein docker-compose, keine Production-Setup-Doku, keine Backup-/Restore-Strategie).
- Web-only ohne nativen Mobile-Client → schwach für tägliches On-the-Go-Tracking, keine OS-Native-Notifications, keine Widgets.
- Keine Wearable-/Health-Connect-/HealthKit-Integration.
- Analytics-Bereich explizit als „Beta" gelabelt; keine echte Korrelationsanalyse, nur Streaks und Completion-Raten.
- Solo-Dev ohne sichtbare Roadmap, ohne Issue-Triage-Prozess; nachhaltige Maintenance unsicher.
- Keine Sprach-Lokalisierung über Englisch hinaus.
- Kein DSGVO-/AVV-Hinweis, kein Impressum sichtbar — für DACH-Markt nicht einsatzfähig.

**Für CorrelCore relevant:**

- HabitHeat bedient denselben „Dev/Selfhost-affin + Heatmap-Liebhaber"-Subsegment, das auch für CorrelCore relevant ist — aber **schlecht ausgeführt** (keine Docker-Story, intransparente Datenhaltung). CorrelCore kann hier mit einem sauberen `docker compose up`-Workflow und ehrlicher Privacy-Kommunikation direkt punkten.
- Timer-basiertes Tracking (Pomodoro-/Deep-Work-Style) ist eine interessante Lücke im CorrelCore-Featureset — Bewertung für Backlog: niedrige Priorität, aber als „Activity-Duration"-Feld bei M5+ ergänzbar.
- Die Gamification-Schiene (Achievements, Challenges) ist bewusst _nicht_ CorrelCores Spielfeld — Daylio und HabitHeat decken das ab; CorrelCore positioniert sich als „erwachsene Reflexion statt Punkte-Jagd".
- Die 5-Punkt-Mood + Energy + Stress + Notes-Kombination von HabitHeat validiert das CorrelCore-Datenmodell (siehe DESIGN_DOCUMENT §2.1).

---

### Habit Tracker — Completer (Plainzer) — der Apple-Ecosystem-Minimalist

| Attribut     | Details                                                                                   |
| ------------ | ----------------------------------------------------------------------------------------- |
| URL          | [App Store](https://apps.apple.com/us/app/habit-tracker-completer/id6757959722)           |
| Downloads    | Unbekannt (keine sichtbaren Ratings/Reviews — frische App, Version 1.2)                   |
| Team         | Plainzer Sp. z o.o. (Polen)                                                               |
| Preis        | Free + Pro: 1,99 USD/Monat oder 11,99 USD/Jahr                                            |
| Plattform    | iPhone (iOS 18+), iPad (iPadOS 18+), Mac (macOS 15 + M1), Apple Vision (visionOS 2)       |
| Sprachen     | DE, EN, FR, IT, PL, PT, RU, ES (8 Sprachen — überdurchschnittlich für Indie)              |
| Datenhaltung | Lokal + iCloud-Sync (nur Pro); Telemetrie: Usage + Diagnostics, nicht identitätsverknüpft |

**Stärken:**

- **Aggressive Preisgestaltung:** 11,99 USD/Jahr ist ~⅓ von Daylios 35,99 USD/Jahr und unterbietet auch Habitify und Bearable deutlich — klares Value-Play für die Apple-Bubble.
- Sehr enge Apple-Ecosystem-Integration (iPhone, iPad, Mac, Vision Pro) — Universal-Binary-Erlebnis ohne Mehrkosten.
- Explizite Zielgruppenansprache **ADHS**: positioniert sich als Begleiter für Konsistenz-Schwierigkeiten — emotional-relevantes Nischen-Marketing.
- Hochwertige UI-Polish: kompaktes vs. reguläres Layout, Custom-Farben, Drag-to-Reorder, Datumsbereiche für Nachtrag.
- Mehrere Checklisten / mehrere Boards (Pro) — gut für Trennung „Arbeit vs. privat" oder „Morning Routine vs. Evening Routine".
- Datenschutz-Linkbar: erhobene Daten nicht identitätsverknüpft (App-Privacy-Label).
- Sehr klein (~16 MB) — Indie-Hand-Craft erkennbar.

**Schwächen:**

- **Hohe System-Hürde:** iOS 18 / macOS 15 / M1 — schließt einen großen Teil der Installed Base aus (Stand 2026: viele Geräte noch iOS 17 oder älter, viele Mac-User auf Intel).
- **Apple-Lock-in:** Keine Android-, Web-, Windows- oder Linux-Variante. Apple-Bubble-Strategie blockt 70%+ des deutschsprachigen Smartphone-Markts.
- Pro-Paywall trifft die Kernfunktionen hart: ohne Pro **kein iCloud-Sync, keine Multi-Device-Nutzung, kein erweiterter Analytics**. Free-Version ist eher Demo als brauchbares Produkt.
- **Keine HealthKit-/Wearable-Integration** — überraschende Lücke gerade im Apple-Ökosystem, wo Apple Watch und HealthKit naheliegend wären.
- Keine Korrelationsanalyse, keine Lifestyle-Kontextfelder (Schlaf, Office/Homeoffice, Wetter) — reines „Habit Done / Not Done"-Checklisten-Paradigma.
- Selfhosting/Datenexport: keine Aussage zur Datenmobilität bei Pro-Abkündigung. iCloud-Lock-in.
- Keine sichtbaren Reviews → kein Social Proof, kaum Marktpenetration bisher.
- Notifications nur „motivational reminders" — keine Smart-Reminders basierend auf Tageskontext.
- Polnischer Anbieter ohne deutlich kommunizierte DSGVO-Position (zwar EU-basiert, aber kein dediziertes Trust-Marketing).

**Für CorrelCore relevant:**

- Validiert, dass aggressive Preisgestaltung (~12 €/Jahr) im Markt funktioniert. CorrelCores empfohlene 39 €/Jahr ist im **Premium-Segment** positioniert, was eine bewusste Wert-Argumentation (Korrelationen, Wearable, Privacy) erfordert — sonst ist Completer der Discount-Wettbewerber.
- Die ADHS-Positionierung ist ein interessanter Submarkt — CorrelCores Reflektions-Tiefe wäre für ADHS-Nutzer eher Overload. Bewusst _nicht_ adressieren.
- Universal-Binary-Strategie (eine App über alle Geräte) ist bei einem Selfhost/Web-First-Stack wie CorrelCore über PWA bereits gegeben und sollte stärker beworben werden (Phone-PWA + Desktop-PWA + zukünftig Android-Native).
- Die fehlende HealthKit-Integration eines Apple-only-Konkurrenten bestätigt: Wearable-Integration ist eine reale Marktlücke, kein „Nice-to-have".
- Completer zeigt, wie viel UI-Polish + Universal-Binary in 16 MB möglich sind — Erinnerung für CorrelCores Mobile-Client-Roadmap, das Bundle schlank zu halten.

---

### eMoods — der Bipolar-Nischenplayer

| Attribut  | Details                            |
| --------- | ---------------------------------- |
| Downloads | 100k+                              |
| Team      | Liviant LLC (schlankes Indie-Team) |
| Preis     | Free + Premium Abo                 |

**Stärken:** Klarer Bipolar-Fokus, PDF-Report für Arzt, Zyklus-/Mondphasen-Integration, Dropbox-Export, Classic-Variante 100% offline.

**Schwächen:** Enge Zielgruppe, UI funktional-nüchtern, geringe Reichweite.

---

## 3. Marktlücken & Differenzierung für CorrelCore

| Lücke                                  | Beschreibung                                                                     | CorrelCore-Ansatz                                                   |
| -------------------------------------- | -------------------------------------------------------------------------------- | ------------------------------------------------------------------- |
| **Selfhost/Privacy-first**             | Keine der Top-Apps bietet offizielles Selfhosting                                | Kern-USP: `docker compose up`, Daten bleiben lokal                  |
| **Korrelationstiefe für Lifestyle**    | Bearable führend bei Health, aber Cloud-only + chronisch-krank-Fokus             | Lifestyle-Zielgruppe (Remote-Worker 30–50) mit echter Statistik     |
| **Wearable via Health Connect**        | Keine App hat saubere Garmin-/Wearables-Pipeline                                 | Health Connect als First-Class-Feature ab M8                        |
| **Work-Context (Homeoffice)**          | Nirgends als First-Class-Feature                                                 | `work_context`-Feld als dediziertes Pflichtfeld                     |
| **DACH-Datenschutz-Positionierung**    | Alle großen Anbieter US/UK-basiert                                               | DSGVO-native, österreichischer Developer, DE/AT/CH-First            |
| **Ehrlicher Selfhost statt Theater**   | HabitHeat verspricht „local-first", liefert aber stiller Backend-Stack ohne Doku | Transparente Compose-Files, klare Datenflüsse, AGPL                 |
| **Cross-Plattform statt Apple-Bubble** | Completer/Habit Heatmap ignorieren Android/Linux/Windows komplett                | PWA-first, später Android-Native via Play Store, alles Selfhost-bar |

---

## 4. Preis- und Geschäftsmodelle

### Markt-Trend: Abo dominiert

- Der In-App-Purchase-Markt erreicht 2025 ~170 Mrd. USD; Weekly Plans machen 55,6% des weltweiten App-Umsatzes aus
- Nur noch 6% aller iOS-Apps sind Upfront-Paid (2020: 9,4%) — Einmalkäufe sind Nischenprodukt
- Abo-Apps wachsen jährlich ~15,8% beim User-Spending
- Einmalkäufe haben dennoch ihren Revenue-Anteil von 6,4% (2023) auf 10,3% (2025) gesteigert (+6%) — Subscription Fatigue ist real

### Empfohlenes Hybrid-Modell für CorrelCore

| Tier                  | Beschreibung                                                    | Preis (Empfehlung)          |
| --------------------- | --------------------------------------------------------------- | --------------------------- |
| **Selfhost Free**     | Vollständige Features für Selfhoster (AGPL)                     | 0 €                         |
| **Cloud Abo**         | Managed Hosting, kein eigener Server nötig                      | 4,99 €/Monat oder 39 €/Jahr |
| **Founders Lifetime** | Einmalzahlung, zeitlich/mengenmäßig begrenzt (erste 500 Käufer) | 89 € (einmalig)             |

**Begründung:**

- „Du zahlst einmal, du besitzt es, deine Daten bleiben bei dir" ist ideologisch kohärent und glaubwürdig — reine Abo-Player (Daylio, Bearable) können das nicht senden
- Lifetime zeitlich/mengenmäßig begrenzen: Dringlichkeit, schützt Unit Economics
- Lifetime **außerhalb des Play Store** verkaufen (via Stripe auf Website) → spart 15% Google-Cut

**Warnung:** Niemals bestehenden Käufern Features entziehen (Notability-Fail 2021, Apple-Richtlinie 3.1.2(a)).

---

## 5. Kosten & Infrastruktur

### Einmalige Startkosten

| Position                       | Kosten            |
| ------------------------------ | ----------------- |
| Google Play Console            | 25 USD (einmalig) |
| Domain (.app oder .io, 1 Jahr) | ~15–20 €          |
| Sonstiges (Assets, Tools)      | ~0–50 €           |
| **Gesamt**                     | **~40–100 €**     |

### Laufende Kosten nach Skalierungsstufe

**Stufe 1 — Pre-Launch / Beta (bis 500 MAU)**
| Position | Kosten/Monat |
|---|---|
| Hetzner CX23 (2 vCPU, 4 GB RAM) | 3,99 € |
| Backup-Space 20 GB | ~1 € |
| Domain anteilig | ~1,50 € |
| E-Mail (Resend Free-Tier) | 0 € |
| **Gesamt** | **~6–8 €/Monat** |

**Stufe 2 — Öffentlicher Release (500–5.000 MAU)**
| Position | Kosten/Monat |
|---|---|
| Hetzner CCX13 / CPX21 | ~15–25 € |
| Backup-Space 100 GB | ~6 € |
| Transactional Mail (Resend Pro) | ~18 € |
| Cloudflare Pro (optional) | 20 € |
| **Gesamt** | **~40–70 €/Monat** |

**Stufe 3 — SaaS (10.000+ MAU)**
| Position | Kosten/Monat |
|---|---|
| 2× CCX23 + Managed DB + Object Storage | ~150–250 € |
| Status-Page, Monitoring | +20–40 € |
| Support-Tool | 0–30 € |
| **Gesamt** | **~200–350 €/Monat** |

### Google Play Provisionen

- **15%** auf alle Abos (ab März 2026: Standard 20%, mit App Experience Program 15%)
- **15%** auf Einmalkäufe/Lifetime (bis 1 Mio. USD Jahresumsatz)
- **Stripe auf eigener Website:** 0% Google-Cut → starkes Argument für Lifetime außerhalb Play Store

### Break-Even-Kalkulation

- Bei 4,99 €/Monat-Abo und 15% Google-Cut → Netto ~4,24 €/Abo
- Stufe-2-Kosten ~65 €/Monat → nur **~15 zahlende Abonnenten** nötig
- Bei 5% Free→Paid Conversion → entspricht ~300 aktiven Nutzern
- 10 Lifetime-Lizenzen à 89 € via Stripe = ~860 € netto → > 1 Jahr laufende Kosten gedeckt

---

## 6. Werbung & Affiliate (Bewertung)

### Warum Ads für CorrelCore nicht empfohlen werden

- Ad-ARPU ≈ 0,07 USD/Monat vs. Subscriber-ARPPU ≈ 2,82 USD/Monat → Faktor 40
- 5.000 DAU × 3 Interstitials × 3 USD eCPM = ~1.350 USD/Monat brutto; dieselben 5.000 DAU mit 3% Abo-Conversion = 748 USD netto — ohne Friction
- Ads widersprechen dem Privacy-first Brand-Versprechen fundamental

### Affiliate: Nur als Akquise-Kanal

- Affiliate als **User-Acquisition-Instrument** sinnvoll (20–25% Revenue-Share an Mental-Health-Blogger)
- Nicht als Einnahmequelle
- Optional: Settings-Seite „Recommended Tools" mit 1–3 transparent gekennzeichneten Partnerprodukten (z. B. Garmin-kompatibles Wearable)

---

## 7. Marketing-Strategie

### Kernprinzipien

1. **Retention vor Acquisition:** Erst D7 > 40%, dann Geld für Ads ausgeben
2. **Ein Differenzierungs-Satz:** „Der Mood-Tracker, dessen Daten dein Zuhause nie verlassen." — überall, identisch, monatelang
3. **Build-in-Public:** Gratis-Traffic, SEO-Content, Vertrauen aufbauen
4. **DACH-Nische zuerst:** Datenschutz-Marketing ist in DE/AT/CH 5× effektiver als in den USA
5. **Reviews:** In-App-Prompt nach positivem Moment (nach erstem Insight), nur bei Usern mit ≥ 10 Einträgen

### Maßnahmen nach Meilenstein

**M0–M2: Pre-Product (Budget 0–30 €)**

- Build-in-Public starten: Mastodon, BlueSky, LinkedIn (2–3 Posts/Woche)
- Landing-Page + Mailing-Liste (Listmonk self-hosted)
- Problem-Interviews: 10–15 Gespräche mit Zielgruppe
- Konkurrenz-Reviews systematisch lesen: 1-Sterne-Reviews von Daylio/Bearable → Feature-Priorisierung

**M3–M5: Closed Alpha (Budget 20–50 €)**

- Private Beta: 10–20 Tester aus Problem-Interviews; Lifetime-Key als Benefit
- BetaList-Listung (kostenlos)
- Reddit präsent: r/selfhosted, r/quantifiedself, r/PrivacyApps (hilfreich kommentieren, kein direktes Marketing)
- Dev-Blog/Changelog auf Hashnode/dev.to (Keywords: „selfhosted mood tracker", „daylio alternative privacy")
- GitHub-Repo öffnen (zumindest Issues + Roadmap)

**M6–M9: Beta-Härtung (Budget 50–200 €)**

- Awesome-Lists-PRs: `awesome-selfhosted`, `awesome-privacy`, `awesome-android`
- Selfhosted-Community-Outreach: Selfh.st Newsletter, The Self-Hosted Podcast
- Mini-Case-Studies: „Ich habe 90 Tage Stimmung + Homeoffice getrackt — 3 überraschende Muster"
- Erste Domain-Authority: 3–5 Blogposts (2.000+ Wörter) zu Mood-Tracking-Science

**M10: Public Selfhost Release (Budget 100–400 €)**

- Show HN auf Hacker News (potenziell 5.000–50.000 Visits)
- Product Hunt Launch (500–2.000 Downloads realistisch)
- Lobste.rs, r/opensource, r/androidapps
- Optional: Indie App Santa Android-Promotion (~150 USD)

**M11: Play Store (Budget 200–800 €)**

- ASO: Title, Short-Desc, 5 Screenshots, Featured Graphic
- Keywords: „mood tracker", „habit tracker", „mood journal", „privacy tracker"
- Reviews aus Beta-Testern (DSGVO-konform)
- Optional: Google Ads UAC (~200–500 € Test) — erst nach verifizierter Organic-Conversion

**M12: SaaS-Skalierung (Budget 500–2.000 €/Monat)**

- Paid Ads nur wenn CAC < 1/3 LTV bewiesen
- Content-SEO: 1 Artikel/Woche
- Affiliate-Programm: 20–25% Revshare an Mental-Health-Blogger
- Community: Discord/Matrix

### Gesamtbudget Jahr 1

| Phase                  | Budget                                  |
| ---------------------- | --------------------------------------- |
| Pre-Launch bis Beta    | ~70–280 €                               |
| Play-Store-Launch      | ~225–825 €                              |
| Post-Launch SaaS-Start | ~500–2.000 €/Monat (nur wenn LTV passt) |
| **Gesamt Jahr 1**      | **~300–1.100 € Cash**                   |

---

## 8. SWOT-Analyse

### Stärken

- Privacy-first / Selfhosted als echter Marktalleinstellungsmerkmal
- Tiefe Korrelationsanalyse (über Lifestyle-Apps hinaus)
- Offline-First ermöglicht Nutzung ohne Vertrauen in Cloud
- Work-Context (Homeoffice) als spezifischer Mehrwert für Remote-Worker
- DACH-Markt: Datenschutz-Glaubwürdigkeit durch österreichischen Entwickler

### Schwächen

- Solo-Dev: begrenzte Entwicklungskapazität
- Keine Marke / kein Publikum zu Beginn
- Health Connect erst ab Android 14+ verbreitet
- E2E-Verschlüsselung bricht serverseitige Korrelationsanalyse (Trade-off)

### Chancen

- Subscription Fatigue: Lifetime-Modell als Differenzierung
- Wachsende Selfhost-Community (YunoHost, Umbrel, Casaos)
- Health Connect-Ökosystem wächst (Garmin, Fitbit, Samsung schreiben alle hinein)
- Nischenkeywords mit niedriger Konkurrenz für ASO/SEO

### Risiken

- Daylio nicht frontal schlagbar (10M+ Downloads, Netzwerkeffekt)
- Play-Store-Rejection wegen Health-Claims
- Solo-Dev-Burnout bei zu ambitionierter Roadmap
- Garmin API-Änderungen / TOS-Risiko

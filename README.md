# MoodSync

> **Privacy-first Mood & Habit Tracker mit Korrelationsanalyse**
> Verstehe, warum manche Tage gut und andere schlecht waren — selfhosted, offline-first, 60 Sekunden pro Tag.

[![License](https://img.shields.io/badge/license-AGPL--3.0-blue)](LICENSE)
[![Status](https://img.shields.io/badge/status-pre--alpha-orange)](https://github.com/Sturmi77/moodsync/milestones)
[![Stack](https://img.shields.io/badge/stack-FastAPI%20%2B%20SvelteKit%20%2B%20PostgreSQL-green)](#tech-stack)

---

## Was ist MoodSync?

Menschen spüren, dass Schlaf, Sport, Homeoffice-Tage oder Sozialkontakte ihr Wohlbefinden beeinflussen — aber niemand weiß **welche** Faktoren wirklich wirken, **wie stark** und mit welcher **Verzögerung**. Bestehende Apps sind entweder zu simpel (nur Emoji), zu Cloud-abhängig (Datenschutzproblem bei Gesundheitsdaten) oder zu komplex (Quantified-Self-Nerd-Zielgruppe).

**MoodSync** schließt diese Lücke:

| Versprechen | Beschreibung |
|---|---|
| 🔍 **Zusammenhänge statt Rohdaten** | Die App erklärt dir, warum Tage gut oder schlecht waren |
| 🏠 **Selfhosted & Offline-First** | Deine Gesundheitsdaten verlassen nie dein Zuhause |
| ⏱️ **60 Sekunden pro Tag** | Nicht mehr, sonst wird es nicht gemacht |

---

## Features (Roadmap)

- [x] **M0** — Monorepo, CI/CD, Docker-Stack, Auth (Authentik), leeres App-Shell
- [ ] **M1** — Täglicher Eintrag: Mood, Energy, Stress, Tags, Symptome, Notiz, Offline-Sync
- [ ] **M2** — Visualisierungen: Zeitreihe, Heatmap, Streaks, CSV-Export
- [ ] **M3** — Insights v1: Korrelationsanalyse, Template-Statements, Confidence-Level
- [ ] **M4** — Mobile Polish: PWA, Bottom-Sheet-UX, UnifiedPush, App-Lock
- [ ] **M5** — Habits & Ziele: Streak-Logik, Badges, Habit-Dashboard
- [ ] **M6** — Fotos: lokaler Upload → MinIO, EXIF-Strip, Immich-Integration (v2)
- [ ] **M7** — Health Connect: Android-Wearables-Import, Schlaf-Korrelation
- [ ] **M8** — Insights v2: Lasso-Regression, Lag-Analyse, optionales lokales LLM (Ollama)
- [ ] **M9** — Beta-Härtung: Monitoring, GlitchTip, externe Tester, Dokumentation
- [ ] **M10** — Public Selfhost Release v1.0
- [ ] **M11** — Android Play Store (TWA)
- [ ] **M12** — SaaS-Modus (Managed Hosting)

Vollständige Roadmap: [`docs/DESIGN_DOCUMENT.md#roadmap`](docs/DESIGN_DOCUMENT.md)

---

## Tech Stack

| Schicht | Technologie | Begründung |
|---|---|---|
| **Backend API** | FastAPI (Python 3.12) | Async, OpenAPI-nativ, schnell iterierbar |
| **Web Frontend** | SvelteKit + Skeleton UI | Performance, Bundle < 150 KB gz |
| **Mobile** | PWA → TWA (Bubblewrap) | Code-Sharing max., Play Store ohne RN |
| **Datenbank** | PostgreSQL 16 + pgvector | RLS für Multi-User, Vektor für Insights |
| **Cache / Queue** | Redis 7 | Session, Rate-Limit, Sync-Queue |
| **Object Storage** | MinIO | Selfhost-kompatibles S3, EXIF-Strip |
| **Reverse Proxy** | Traefik v3 | Automatisches TLS, Docker-Labels |
| **Auth** | Authentik | OIDC, SSO, selfhost |
| **Offline-Sync** | Dexie.js (IndexedDB) | Delta-Sync, Last-Write-Wins |
| **Analytics** | pandas + scikit-learn | Korrelation, Lasso, Lag-Analyse |
| **Migrations** | Alembic | Schema-Versionierung |
| **Monitoring** | GlitchTip + Uptime Kuma | Selfhost-Error-Tracking |
| **Notifications** | UnifiedPush / FCM | Privacy-first Push |

---

## Schnellstart (Selfhost)

### Voraussetzungen

- Docker ≥ 24 + Docker Compose v2
- Eine Domain mit DNS auf deinen Server
- Optional: Authentik-Instanz (oder mitgelieferter Stack)

### Setup

```bash
git clone https://github.com/Sturmi77/moodsync.git
cd moodsync
cp infra/docker/.env.example infra/docker/.env
# .env anpassen (DOMAIN, SECRET_KEY, POSTGRES_PASSWORD, …)
docker compose -f infra/docker/docker-compose.yml up -d
```

Danach erreichbar unter `https://deine-domain.tld`

> **Hinweis:** MoodSync befindet sich in aktiver Entwicklung (Pre-Alpha). Produktiveinsatz erst ab v1.0 empfohlen.

---

## Monorepo-Struktur

```
moodsync/
├── apps/
│   ├── web/          # SvelteKit PWA
│   └── android/      # Bubblewrap TWA (ab M11)
├── backend/
│   ├── app/          # FastAPI Anwendung
│   ├── migrations/   # Alembic Migrationen
│   └── workers/      # Analytics Worker, Insight Engine
├── infra/
│   ├── docker/       # docker-compose.yml, .env.example
│   └── traefik/      # Traefik Konfiguration
├── docs/
│   ├── DESIGN_DOCUMENT.md      # Single Source of Truth
│   ├── ARCHITECTURE.md
│   ├── API.md
│   ├── FRONTEND.md
│   ├── MARKET_ANALYSIS.md
│   └── adr/                    # Architecture Decision Records
└── .github/
    └── ISSUE_TEMPLATE/
```

---

## KI-Assistenten Prompt-Template

Beim Einsatz von KI-Modellen (Claude, Cursor, Copilot, Perplexity) diese Datei **immer zuerst** in den Kontext laden:

```
Kontext: Lies zuerst DESIGN_DOCUMENT.md vollständig. Halte dich strikt an die dort
definierte Architektur, Tech-Stack und Frontend-Prinzipien. Wenn du davon abweichen
willst, begründe es und schlage einen ADR-Eintrag vor.
Aufgabe: <hier konkrete Aufgabe>
```

---

## Dokumentation

| Dokument | Inhalt |
|---|---|
| [DESIGN_DOCUMENT.md](docs/DESIGN_DOCUMENT.md) | Vision, Features, Architektur, Roadmap — **Single Source of Truth** |
| [ARCHITECTURE.md](docs/ARCHITECTURE.md) | Komponentendiagramm, Deployment-Topologien, Sync-Protokoll |
| [API.md](docs/API.md) | OpenAPI-Richtlinien, Endpunkte, Auth-Flow |
| [FRONTEND.md](docs/FRONTEND.md) | Design-Prinzipien, Atomic Design, i18n, Performance-Budget |
| [MARKET_ANALYSIS.md](docs/MARKET_ANALYSIS.md) | Wettbewerbs- und Marktanalyse, Monetarisierung, Marketing |
| [ADR Index](docs/adr/) | Architecture Decision Records |

---

## Mitwirken

MoodSync ist aktuell ein Solo-Projekt. Sobald v1.0 erscheint, werden Contribution-Guidelines veröffentlicht. Issues und Diskussionen sind willkommen.

**Interesse an Beta-Testing?** → [Issue öffnen](https://github.com/Sturmi77/moodsync/issues/new?template=beta_tester.md) oder auf der [Landing Page](https://moodsync.app) eintragen (coming soon).

---

## Lizenz

MoodSync wird unter der [GNU Affero General Public License v3.0](LICENSE) veröffentlicht. Für kommerzielle Selfhost-Lizenzen ohne AGPL-Copyleft: Kontakt via Issue.

---

## Disclaimer

MoodSync ist **kein medizinisches Diagnose-Tool**. Alle angezeigten Korrelationen und Insights dienen ausschließlich zur persönlichen Reflexion und ersetzen keine ärztliche oder therapeutische Beratung.

# CorrelCore

> **Privacy-first Mood & Habit Tracker with Correlation Analysis**
> Understand why some days are good and others are not — selfhosted, offline-first, 60 seconds per day.

[![License](https://img.shields.io/badge/license-AGPL--3.0-blue)](LICENSE)
[![Status](https://img.shields.io/badge/status-pre--alpha-orange)](https://github.com/Sturmi77/correlcore/milestones)
[![Stack](https://img.shields.io/badge/stack-FastAPI%20%2B%20SvelteKit%20%2B%20PostgreSQL-green)](#tech-stack)

---

## What is CorrelCore?

People sense that sleep, exercise, remote work days, or social contacts influence their wellbeing — but rarely know **which** factors actually matter, **how strongly**, and with what **time delay**. Existing apps are either too simple (just mood emojis), too cloud-dependent (a privacy problem for health data), or too complex (targeting quantified-self enthusiasts).

**CorrelCore** fills this gap:

| Promise                        | Description                                            |
| ------------------------------ | ------------------------------------------------------ |
| **Correlations, not raw data** | The app explains why days were good or bad             |
| **Selfhosted & Offline-First** | Your health data never leaves your home                |
| **60 seconds per day**         | No more, or it simply won't get done                   |
| **No gamification, ever**      | You track your habits — not how often you open the app |

---

## Features & Roadmap

- [x] **M0** — Monorepo, CI/CD, Docker stack, native JWT auth, empty app shell
- [x] **M1** — Daily entry: mood, energy, stress, tags (curated + custom), symptoms (curated + custom), notes, app-level Fernet encryption at rest, login/register UI, email verification, GDPR erasure (offline sync moved to M4 — [ADR-0009](docs/adr/0009-offline-sync-nach-m4.md))
- [x] **M2** — Visualisations: mood time series (multi-metric), tag frequency heatmap with drilldown, entry streak widgets, CSV/JSON export (GDPR Art. 20), custom SVG charts, habit schema prep ([ADR-0012](docs/adr/0012-m2-m5-streak-semantik.md)), developer view ([ADR-0015](docs/adr/0015-developer-view-version-identifikation.md))
- [x] **M3** — Insights v1: correlation analysis, template-based statements, tiered confidence system, cold-start UX (retrospective onboarding, insight confidence scale, day-over-day delta, weekday pattern insight, onboarding profile questionnaire)
- [x] **M3.1** — Insights polish: non-blocking InsightStore, canonical InsightCard, full Insights feed, correlation disclaimer, and neutral heatmap styling
- [ ] **M3.5** — Frontend web and mobile optimisation: app shell, entry bottom sheet, Home recomposition, Trends tabs, Settings/i18n, tag lifecycle. Implementation is on `main`; release closeout still needs rendered QA, Web CI confirmation, and GitHub issue closure.
- [ ] **M3.6** — Insight maturity phases: ADR-0021 API contract (`insight_maturity`), Journey Banner, Maturity Badge, phase-aware empty states, and phase milestone cards. Implementation is documented through Sprint 4; release closeout remains blocked by Web CI diagnostics and GitHub write access.
- [ ] **M4** — Mobile polish: PWA, bottom-sheet UX, UnifiedPush, app lock, offline sync (Dexie.js)
- [ ] **M5** — Habits & goals: adherence rate, tracking consistency, habit dashboard
- [ ] **M6** — Health Connect: Android wearables import, sleep correlation
- [ ] **M7** — Insights v2: Lasso regression, lag analysis, optional local LLM (Ollama)
- [ ] **M8** — Beta hardening: monitoring, GlitchTip, external testers, documentation
- [ ] **M9** — Public selfhost release v1.0
- [ ] **M10** — Android Play Store (Capacitor)
- [ ] **M11** — SaaS mode (managed hosting)
- [ ] **M12** — Photo & media: local upload to MinIO, EXIF strip, Immich integration (v2)

Full roadmap: [`docs/DESIGN_DOCUMENT.md`](docs/DESIGN_DOCUMENT.md)

### Current Milestone Status

| Milestone | Status | Notes |
| --------- | ------ | ----- |
| **M3** | Complete | Insights v1 is closed with backend analytics, worker generation, read APIs, Home preview, cold-start onboarding, and day-over-day delta. See [`docs/M3_SPRINT_STATUS.md`](docs/M3_SPRINT_STATUS.md). |
| **M3.1** | Complete | Focused Insights polish after M3: InsightCard/InsightFeed, non-blocking store behaviour, disclaimer route/modal, and neutral correlation matrix styling. See [`docs/M3.1_SPRINT_STATUS.md`](docs/M3.1_SPRINT_STATUS.md). |
| **M3.5** | Implementation complete, release gates pending | Frontend/mobile optimisation is implemented and documented, but final release tagging still needs rendered browser QA, Web CI rerun, and authenticated GitHub issue closure/rescope. See [`docs/M3_5_SPRINT_STATUS.md`](docs/M3_5_SPRINT_STATUS.md) and [`docs/quality/M3_5_VISUAL_QA.md`](docs/quality/M3_5_VISUAL_QA.md). |
| **M3.6** | Implementation documented, release gates pending | Insight maturity phases are implemented through Sprint 3 and Sprint 4 documents the remaining blockers: Web typecheck/lint diagnostics, rendered QA, and GitHub milestone/issue updates. See [`docs/M3_6_SPRINT_STATUS.md`](docs/M3_6_SPRINT_STATUS.md). |

---

## Tech Stack

| Layer              | Technology                             | Rationale                                                                                             |
| ------------------ | -------------------------------------- | ----------------------------------------------------------------------------------------------------- |
| **Backend API**    | FastAPI (Python 3.12)                  | Async, OpenAPI-native, fast iteration                                                                 |
| **Web Frontend**   | SvelteKit + Skeleton UI                | Performance, bundle < 150 KB gz                                                                       |
| **Mobile**         | PWA + Capacitor (Android)              | Maximum code sharing, native Health Connect access ([ADR-0002](docs/adr/0002-capacitor-statt-twa.md)) |
| **Charts**         | Custom SVG components                  | No external framework, JS budget maintained, token-compliant                                          |
| **Database**       | PostgreSQL 16 + pgvector               | Row-level security for multi-user, vector for insights                                                |
| **Cache / Queue**  | Redis 7                                | Sessions, rate limiting, sync queue                                                                   |
| **Object Storage** | MinIO                                  | Selfhost-compatible S3, EXIF strip                                                                    |
| **Reverse Proxy**  | Traefik v3                             | Automatic TLS, Docker label routing                                                                   |
| **Auth**           | Native JWT phase 1, Authentik from M11 | OIDC, SSO, selfhostable ([ADR-0004](docs/adr/0004-auth-strategie.md))                                 |
| **Offline Sync**   | Dexie.js (IndexedDB)                   | Delta sync, last-write-wins (M4)                                                                      |
| **Analytics**      | pandas + scikit-learn                  | Correlation, Lasso, lag analysis                                                                      |
| **Migrations**     | Alembic                                | Schema versioning                                                                                     |
| **Monitoring**     | GlitchTip + Uptime Kuma                | Selfhosted error tracking                                                                             |
| **Notifications**  | UnifiedPush / FCM                      | Privacy-first push                                                                                    |

---

## Quickstart (Selfhost)

### Prerequisites

- Docker >= 24 + Docker Compose v2
- A domain with DNS pointing to your server

### Setup

```bash
git clone https://github.com/Sturmi77/correlcore.git
cd correlcore
cp infra/docker/.env.example infra/docker/.env
# Edit .env: set DOMAIN, SECRET_KEY, POSTGRES_PASSWORD, ...
docker compose -f infra/docker/docker-compose.yml up -d
```

After startup, CorrelCore is available at `https://your-domain.tld`

> **Note:** CorrelCore is under active development (pre-alpha). Production use is recommended from v1.0 onwards.

---

## Monorepo Structure

```
correlcore/
├── apps/
│   ├── web/          # SvelteKit PWA
│   └── android/      # Capacitor Android app (from M10)
├── backend/
│   ├── app/          # FastAPI application
│   ├── migrations/   # Alembic migrations
│   └── workers/      # Analytics worker, insight engine
├── infra/
│   ├── docker/       # docker-compose.yml, .env.example
│   └── traefik/      # Traefik configuration
├── docs/
│   ├── DESIGN_DOCUMENT.md      # Single source of truth
│   ├── ARCHITECTURE.md
│   ├── API.md
│   ├── FRONTEND.md
│   ├── MARKET_ANALYSIS.md
│   ├── quality/                # Quality gate reports (M1, M2, ...)
│   └── adr/                    # Architecture decision records
└── .github/
    └── ISSUE_TEMPLATE/
```

---

## AI Assistant Prompt Template

When working with AI models (Claude, Cursor, Copilot, Perplexity), always load `DESIGN_DOCUMENT.md` as context first:

```
Context: Read DESIGN_DOCUMENT.md in full first. Strictly follow the architecture,
tech stack and frontend principles defined there. If you want to deviate,
justify it and propose an ADR entry.
Task: <your specific task here>
```

---

## Documentation

| Document                                                              | Content                                                           |
| --------------------------------------------------------------------- | ----------------------------------------------------------------- |
| [DESIGN_DOCUMENT.md](docs/DESIGN_DOCUMENT.md)                         | Vision, features, architecture, roadmap — single source of truth  |
| [ARCHITECTURE.md](docs/ARCHITECTURE.md)                               | Component diagram, deployment topologies, sync protocol           |
| [API.md](docs/API.md)                                                 | OpenAPI guidelines, endpoints, auth flow                          |
| [FRONTEND.md](docs/FRONTEND.md)                                       | Design principles, atomic design, i18n, performance budget        |
| [MARKET_ANALYSIS.md](docs/MARKET_ANALYSIS.md)                         | Competitive and market analysis, monetisation, marketing          |
| [DOCUMENTATION_LANGUAGE_PLAN.md](docs/DOCUMENTATION_LANGUAGE_PLAN.md) | English-first collaboration and documentation migration plan      |
| [RENAMING_TO_CORRELCORE.md](docs/RENAMING_TO_CORRELCORE.md)           | Rename and deployment migration notes from MoodSync to CorrelCore |
| [ADR Index](docs/adr/)                                                | Architecture decision records                                     |
| [Quality Gates](docs/quality/)                                        | M1/M2 quality gate reports                                        |

---

## Contributing

CorrelCore is currently a solo project. Contribution guidelines will be published once v1.0 is released. Issues and discussions are welcome.

**Interested in beta testing?** Open an [issue](https://github.com/Sturmi77/correlcore/issues/new?template=beta_tester.md) or sign up on the [landing page](https://correlcore.app) (coming soon).

---

## License

CorrelCore is released under the [GNU Affero General Public License v3.0](LICENSE). For commercial selfhost licenses without AGPL copyleft, contact via issue.

---

## Disclaimer

CorrelCore is **not a medical diagnostic tool**. All correlations and insights shown are intended solely for personal reflection and do not replace medical or therapeutic advice.

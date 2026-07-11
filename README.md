# CorrelCore

> **Privacy-first Mood & Habit Tracker with Correlation Analysis**
> Understand why some days are good and others are not — selfhosted today, offline-capable by design, 60 seconds per day.

[![License](https://img.shields.io/badge/license-AGPL--3.0-blue)](LICENSE)
[![Status](https://img.shields.io/badge/status-pre--alpha-orange)](https://github.com/Sturmi77/correlcore/milestones)
[![Stack](https://img.shields.io/badge/stack-FastAPI%20%2B%20SvelteKit%20%2B%20PostgreSQL-green)](#tech-stack)

---

## What is CorrelCore?

People sense that sleep, exercise, remote work days, or social contacts influence their wellbeing — but rarely know **which** factors actually matter, **how strongly**, and with what **time delay**. Existing apps are either too simple (just mood emojis), too cloud-dependent (a privacy problem for health data), or too complex (targeting quantified-self enthusiasts).

**CorrelCore** fills this gap:

| Promise                                | Description                                                                                                            |
| -------------------------------------- | ---------------------------------------------------------------------------------------------------------------------- |
| **Correlations, not raw data**         | The app explains why days were good or bad                                                                             |
| **Selfhosted now, offline-ready next** | Your health data stays on your instance; PWA shell caching is live; Dexie offline sync ships in M4.1 (feature-flagged) |
| **60 seconds per day**                 | No more, or it simply won't get done                                                                                   |
| **No gamification, ever**              | You track your habits — not how often you open the app                                                                 |

---

## Features & Roadmap

- [x] **M0** — Monorepo, CI/CD, Docker stack, native JWT auth, empty app shell
- [x] **M1** — Daily entry: mood, energy, stress, tags (curated + custom), symptoms (curated + custom), notes, app-level Fernet encryption at rest, login/register UI, email verification, GDPR erasure (offline sync moved to M4 — [ADR-0009](docs/adr/0009-offline-sync-nach-m4.md))
- [x] **M2** — Visualisations: mood time series (multi-metric), tag frequency heatmap with drilldown, entry streak widgets, CSV/JSON export (GDPR Art. 20), custom SVG charts, habit schema prep ([ADR-0012](docs/adr/0012-m2-m5-streak-semantik.md)), developer view ([ADR-0015](docs/adr/0015-developer-view-version-identifikation.md))
- [x] **M3** — Insights v1: correlation analysis, template-based statements, tiered confidence system, cold-start UX (retrospective onboarding, insight confidence scale, day-over-day delta, weekday pattern insight, onboarding profile questionnaire)
- [x] **M3.1** — Insights polish: non-blocking InsightStore, canonical InsightCard, full Insights feed, correlation disclaimer, and neutral heatmap styling
- [x] **M3.5** — Frontend web and mobile optimisation: app shell, entry bottom sheet, Home recomposition, Trends tabs, Settings/i18n, tag lifecycle. Release-complete after rendered QA on 2026-05-27. See [`docs/M3_5_SPRINT_STATUS.md`](docs/M3_5_SPRINT_STATUS.md) and [`docs/quality/M3_5_VISUAL_QA.md`](docs/quality/M3_5_VISUAL_QA.md).
- [x] **M3.6** — Insight maturity phases: ADR-0021 API contract (`insight_maturity`), Journey Banner, Maturity Badge, phase-aware empty states, and phase milestone cards. Release-complete after rendered QA on 2026-05-27. See [`docs/M3_6_SPRINT_STATUS.md`](docs/M3_6_SPRINT_STATUS.md) and [`docs/quality/M3_6_VISUAL_QA.md`](docs/quality/M3_6_VISUAL_QA.md).
- [x] **M3.7** — Color system hardening: complete semantic tokens, legacy primary alias cleanup, ADR-0027 contrast gate, light-mode QA documentation, and Web CI integration. Release-complete locally after rendered QA on 2026-05-28. See [`docs/M3_7_SPRINT_STATUS.md`](docs/M3_7_SPRINT_STATUS.md).
- [x] **M4** — Quick wins + PWA hardening: entry slots, cycle day, guided onboarding, Dev Mode mocks, install banner, service worker (app shell), `/offline` fallback — **Complete** (2026-06-30). Offline sync → M4.1; push/app lock deferred. See [`docs/M4_SPRINT_STATUS.md`](docs/M4_SPRINT_STATUS.md) and [`docs/quality/M4_VISUAL_QA.md`](docs/quality/M4_VISUAL_QA.md).
- [x] **M4.1** — Offline-first sync: Dexie.js, `/sync/push` + `/sync/pull`, LWW merge, `sync_conflicts` log, local-first entry path — **Complete** (2026-06-30). Feature-flagged for verified users. Closes #10, #24. See [`docs/M4.1_SPRINT_STATUS.md`](docs/M4.1_SPRINT_STATUS.md) and [`docs/quality/M4.1_VISUAL_QA.md`](docs/quality/M4.1_VISUAL_QA.md).
- [x] **M5 (Habits Core)** — Goal-based habit adherence (`build`/`reduce`), `/api/v1/habits`, Settings tag configuration, Trends Habits tab — **Complete** (2026-06-30). See [`docs/M5_SPRINT_STATUS.md`](docs/M5_SPRINT_STATUS.md) and [`docs/quality/M5_VISUAL_QA.md`](docs/quality/M5_VISUAL_QA.md).
- [x] **M5.1 (UX Polish)** — Flow consolidation for onboarding, Home, Insights, Habits, PWA, and desktop Trends (`ux(O-xx)` #251–#273); tag co-occurrence quick win — **Complete** (2026-07-10). See [`docs/M5_1_SPRINT_STATUS.md`](docs/M5_1_SPRINT_STATUS.md), [`docs/quality/M5_1_UX_VISUAL_QA.md`](docs/quality/M5_1_UX_VISUAL_QA.md), and [`docs/quality/M5_1_VISUAL_QA.md`](docs/quality/M5_1_VISUAL_QA.md).
- [x] **M7** — Insights v2: Lasso, lag, symptom analytics, tag clustering, Sprint 9 interaction UX — **Complete** (2026-06-30). See [`docs/M7_SPRINT_STATUS.md`](docs/M7_SPRINT_STATUS.md), [`docs/quality/M7_QUALITY_GATE.md`](docs/quality/M7_QUALITY_GATE.md). Optional LLM/digest → M7-S8.
- [ ] **M8** — Sleep & Health Connect: manual sleep fields, Android wearable import, sleep↔mood insights, cycle HC sync (with M11). See [`docs/M8_NOTES.md`](docs/M8_NOTES.md).
- [ ] **M9** — Beta hardening: monitoring, GlitchTip, external testers, documentation (Sprint 1 GDPR complete). See [`docs/M9_SPRINT_PLAN.md`](docs/M9_SPRINT_PLAN.md) and [`docs/M9_SPRINT_STATUS.md`](docs/M9_SPRINT_STATUS.md).
- [ ] **M10** — Public selfhost release v1.0
- [ ] **M11** — Android Play Store (Capacitor)
- [ ] **M12** — SaaS mode (managed hosting)
- [ ] **M13** — Photo & media: local upload to MinIO, EXIF strip, thumbnail gallery; optional Immich reference integration as follow-up

Full roadmap: [`docs/DESIGN_DOCUMENT.md`](docs/DESIGN_DOCUMENT.md)

### Current Milestone Status

| Milestone | Status                    | Notes                                                                                                                                                                                                                                                    |
| --------- | ------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **M3**    | Complete                  | Insights v1 is closed with backend analytics, worker generation, read APIs, Home preview, cold-start onboarding, and day-over-day delta. See [`docs/M3_SPRINT_STATUS.md`](docs/M3_SPRINT_STATUS.md).                                                     |
| **M3.1**  | Complete                  | Focused Insights polish after M3: InsightCard/InsightFeed, non-blocking store behaviour, disclaimer route/modal, and neutral correlation matrix styling. See [`docs/M3.1_SPRINT_STATUS.md`](docs/M3.1_SPRINT_STATUS.md).                                 |
| **M3.5**  | Complete                  | Frontend/mobile optimisation release-complete after rendered QA (2026-05-27). See [`docs/M3_5_SPRINT_STATUS.md`](docs/M3_5_SPRINT_STATUS.md) and [`docs/quality/M3_5_VISUAL_QA.md`](docs/quality/M3_5_VISUAL_QA.md).                                     |
| **M3.6**  | Complete                  | Insight maturity phases release-complete after rendered QA (2026-05-27). See [`docs/M3_6_SPRINT_STATUS.md`](docs/M3_6_SPRINT_STATUS.md) and [`docs/quality/M3_6_VISUAL_QA.md`](docs/quality/M3_6_VISUAL_QA.md).                                          |
| **M3.7**  | Complete                  | Color system hardening release-complete locally after rendered light-mode QA (2026-05-28). See [`docs/M3_7_SPRINT_STATUS.md`](docs/M3_7_SPRINT_STATUS.md).                                                                                               |
| **M4**    | **Complete** (2026-06-30) | Quick wins + PWA hardening closed out. Dexie sync/conflict log → M4.1 (#10/#24). See [`docs/M4_SPRINT_STATUS.md`](docs/M4_SPRINT_STATUS.md) and [`docs/quality/M4_VISUAL_QA.md`](docs/quality/M4_VISUAL_QA.md).                                          |
| **M4.1**  | **Complete** (2026-06-30) | Offline-first Dexie sync, push/pull API, conflict log, local-first entries. Visual QA signed off. Closes #10/#24. See [`docs/M4.1_SPRINT_STATUS.md`](docs/M4.1_SPRINT_STATUS.md) and [`docs/quality/M4.1_VISUAL_QA.md`](docs/quality/M4.1_VISUAL_QA.md). |
| **M5**    | **Complete** (2026-06-30) | Habits Core + M5-C1/C2 closeout. Visual QA signed off. See [`docs/M5_SPRINT_STATUS.md`](docs/M5_SPRINT_STATUS.md) and [`docs/quality/M5_VISUAL_QA.md`](docs/quality/M5_VISUAL_QA.md).                                                                    |
| **M5.1**  | **Complete** (2026-07-10) | UX polish & flow consolidation (#251–#273); co-occurrence quick win. **Next main milestone: M9.** See [`docs/M5_1_SPRINT_STATUS.md`](docs/M5_1_SPRINT_STATUS.md).                                                                                        |
| **M7**    | **Complete** (2026-06-30) | Sprints 1–9 + M7-C closeout. Quality gate and visual QA signed off. Optional LLM/digest deferred to M7-S8. See [`docs/CLOSEOUT_SPRINT_PLAN.md`](docs/CLOSEOUT_SPRINT_PLAN.md).                                                                           |
| **M9**    | **In progress** (Sprint 1) | Beta hardening: GDPR self-service done (privacy policy, E2E delete/export). Sprints 2–6 pending. See [`docs/M9_SPRINT_PLAN.md`](docs/M9_SPRINT_PLAN.md) and [`docs/M9_SPRINT_STATUS.md`](docs/M9_SPRINT_STATUS.md).                                                              |

---

## Tech Stack

| Layer              | Technology                                                                              | Rationale                                                                                                   |
| ------------------ | --------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------- |
| **Backend API**    | FastAPI (Python 3.12)                                                                   | Async, OpenAPI-native, fast iteration                                                                       |
| **Web Frontend**   | SvelteKit + Skeleton UI                                                                 | Performance, bundle < 150 KB gz                                                                             |
| **Mobile**         | Responsive web + partial PWA (install banner, SW shell cache); Capacitor Android in M11 | Maximum code sharing, native Health Connect access later ([ADR-0002](docs/adr/0002-capacitor-statt-twa.md)) |
| **Charts**         | Custom SVG components                                                                   | No external framework, JS budget maintained, token-compliant                                                |
| **Database**       | PostgreSQL 16 + pgvector                                                                | Row-level security for multi-user, vector for insights                                                      |
| **Cache / Queue**  | Redis 7                                                                                 | Sessions, rate limiting, sync queue                                                                         |
| **Object Storage** | MinIO                                                                                   | Selfhost-compatible S3 foundation; photo upload and EXIF strip are M13 scope                                |
| **Reverse Proxy**  | Traefik v3                                                                              | Automatic TLS, Docker label routing                                                                         |
| **Auth**           | Native JWT phase 1, Authentik from M12                                                  | OIDC, SSO, selfhostable ([ADR-0004](docs/adr/0004-auth-strategie.md))                                       |
| **Offline Sync**   | Dexie.js (IndexedDB) — M4.1 complete, feature-flagged                                   | Push/pull LWW merge, conflict log, local-first entry path; default off until user enables in Settings       |
| **Analytics**      | pandas + scikit-learn                                                                   | M7: Lasso, lag, symptom analytics; correlation engine live since M3                                         |
| **Migrations**     | Alembic                                                                                 | Schema versioning                                                                                           |
| **Monitoring**     | GlitchTip + Uptime Kuma                                                                 | Selfhosted error tracking                                                                                   |
| **Notifications**  | UnifiedPush / FCM                                                                       | Privacy-first push                                                                                          |

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
│   ├── web/          # SvelteKit web app; partial PWA (service worker, install banner)
│   └── android/      # Capacitor Android app (from M11)
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

| Document                                                              | Content                                                                                 |
| --------------------------------------------------------------------- | --------------------------------------------------------------------------------------- |
| [DESIGN_DOCUMENT.md](docs/DESIGN_DOCUMENT.md)                         | Vision, features, architecture, roadmap — single source of truth                        |
| [ARCHITECTURE.md](docs/ARCHITECTURE.md)                               | Component diagram, deployment topologies, sync protocol                                 |
| [API.md](docs/API.md)                                                 | OpenAPI guidelines, endpoints, auth flow                                                |
| [API_CONTRACTS.md](docs/API_CONTRACTS.md)                             | API contract strategy, frontend constants, OpenAPI client plan                          |
| [FRONTEND.md](docs/FRONTEND.md)                                       | Mobile/Web roles, responsive shell, component ownership                                 |
| [DEVELOPMENT.md](docs/DEVELOPMENT.md)                                 | Local setup, quality gates, NAS/pnpm notes, test database                               |
| [MARKET_ANALYSIS.md](docs/MARKET_ANALYSIS.md)                         | Competitive and market analysis, monetisation, marketing                                |
| [DOCUMENTATION_LANGUAGE_PLAN.md](docs/DOCUMENTATION_LANGUAGE_PLAN.md) | English-first collaboration and documentation migration plan                            |
| [RENAMING_TO_CORRELCORE.md](docs/RENAMING_TO_CORRELCORE.md)           | Rename and deployment migration notes from MoodSync to CorrelCore                       |
| [Closeout Sprint Plan](docs/CLOSEOUT_SPRINT_PLAN.md)                  | M4/M5/M7 closeout sequence, audit findings, deferred-work index                         |
| [M4 Sprint Status](docs/M4_SPRINT_STATUS.md)                          | M4 quick wins + PWA hardening tracking                                                  |
| [M4.1 Sprint Plan](docs/M4.1_SPRINT_PLAN.md)                          | Offline-first Dexie sync implementation plan                                            |
| [M4.1 Visual QA](docs/quality/M4.1_VISUAL_QA.md)                      | M4.1 offline sync closeout sign-off                                                     |
| [M5 Sprint Status](docs/M5_SPRINT_STATUS.md)                          | M5 Habits Core tracking                                                                 |
| [M7 Notes](docs/M7_NOTES.md)                                          | Insights v2: Lasso, lag, symptom analytics, clustering                                  |
| [M7 Sprint 9](docs/M7_SPRINT9_PLAN.md)                                | Spec-complete closeout: interaction, feed UX, cluster API, a11y                         |
| [Phase & Insight Matrix](docs/PHASE_INSIGHT_MATRIX.md)                | Developer reference: maturity phases, unlock gates, per-insight computation, thresholds |
| [M8 Notes](docs/M8_NOTES.md)                                          | Sleep, Health Connect, cycle deep integration                                           |
| [M7/M8 swap](docs/M7_M8_MILESTONE_SWAP.md)                            | Milestone reorder rationale and consequence index (2026-05-29)                          |
| [M5.1 Visual QA](docs/quality/M5_1_VISUAL_QA.md)                      | Tag co-occurrence heatmap closeout (2026-05-29)                                         |
| [M5.1 Sprint Status](docs/M5_1_SPRINT_STATUS.md)                      | UX polish & flow consolidation closeout (2026-07-10)                                    |
| [M5.1 UX Visual QA](docs/quality/M5_1_UX_VISUAL_QA.md)                | Onboarding, Home, Insights, Habits, PWA flow sign-off                                   |
| [M13 Notes](docs/M13_NOTES.md)                                        | Photo & media milestone scope (deferred post-M12)                                       |
| [PWA](docs/features/PWA.md)                                           | Install banner, service worker, offline fallback                                        |
| [Cycle tracking](docs/features/cycle-tracking.md)                     | Neutral `cycle_day` domain scope                                                        |
| [COLOR_SCHEME_CONCEPT](docs/frontend/COLOR_SCHEME_CONCEPT.md)         | Token framework and contrast rationale (M3.7)                                           |
| [Mobile/Web Audit](docs/frontend/MOBILE_WEB_AUDIT.md)                 | Critical frontend findings, status matrix, conflicts                                    |
| [Mobile/Web Plan](docs/frontend/MOBILE_WEB_IMPLEMENTATION_PLAN.md)    | Mobile-first delivery sequence and verification gates                                   |
| [ADR Index](docs/adr/)                                                | Architecture decision records (0001–0034)                                               |
| [Quality Gates](docs/quality/)                                        | M1–M4 visual QA and quality gate reports                                                |

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

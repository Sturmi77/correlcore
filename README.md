<p align="center">
  <img src="docs/assets/brand/correlcore-logo-mark.svg" alt="CorrelCore" width="88" height="88" />
</p>

<h1 align="center">CorrelCore</h1>

<p align="center">
  <strong>Privacy-first correlation analysis for your wellbeing</strong><br />
  Understand why some days are good and others are not — from a 60-second daily check-in. Selfhosted, offline-capable.
</p>

<p align="center">
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-AGPL--3.0-blue" alt="License" /></a>
  <a href="https://sturmi77.github.io/correlcore/"><img src="https://img.shields.io/badge/release-selfhost%20v1.x-blue" alt="Release" /></a>
  <a href="#tech-stack"><img src="https://img.shields.io/badge/stack-FastAPI%20%2B%20SvelteKit%20%2B%20PostgreSQL-green" alt="Stack" /></a>
  <a href="https://github.com/Sturmi77/correlcore/releases"><img src="https://img.shields.io/badge/latest-v1.3.0-informational" alt="Latest tag" /></a>
</p>

---

## What is CorrelCore?

People sense that sleep, exercise, remote work days, or social contacts influence their wellbeing — but rarely know **which** factors actually matter, **how strongly**, and with what **time delay**. Existing apps are either too simple (just mood emojis), too cloud-dependent (a privacy problem for health data), or too complex (targeting quantified-self enthusiasts).

**CorrelCore** fills this gap:

| Promise                        | Description                                                                                                  |
| ------------------------------ | ------------------------------------------------------------------------------------------------------------ |
| **Correlations, not raw data** | The app explains why days were good or bad                                                                   |
| **Selfhosted & offline-ready** | Your health data stays on your instance; PWA shell caching and feature-flagged Dexie sync (M4.1) are shipped |
| **60 seconds per day**         | No more, or it simply won't get done                                                                         |
| **No gamification, ever**      | You collect data points — not streaks, and not how often you open the app                                    |

**Public selfhost line:** tag **`v1.0.0`** (2026-07-11, M10) through the `v1.0.x` patch line, then **`v1.1.x`**, through latest **`v1.3.0`** (sleep-quality slider input + a 4th trend line, Health Connect sync visibility, on the M8 sleep & HC core — no new database migrations). Docs: [sturmi77.github.io/correlcore](https://sturmi77.github.io/correlcore/). Release notes: [`CHANGELOG.md`](CHANGELOG.md).

---

## Roadmap

### Active

- [ ] **M8** — Sleep & Health Connect: manual sleep fields, Android wearable import, sleep↔mood insights, cycle HC sync (with M11). HC **consent** foundation shipped (#31). See [`docs/M8_NOTES.md`](docs/M8_NOTES.md).
- [ ] **M10.2** — Public Hosted Launch (`correlcore.com`): Nginx edge on NAS, real SMTP, login without VPN, APK on landing — [`docs/M10_2_PUBLIC_HOSTED_LAUNCH_PLAN.md`](docs/M10_2_PUBLIC_HOSTED_LAUNCH_PLAN.md), backlog [`docs/M10_2_PUBLIC_HOSTED_LAUNCH_BACKLOG.md`](docs/M10_2_PUBLIC_HOSTED_LAUNCH_BACKLOG.md). Selfhost path stays independent.
- [ ] **M11** — Android Play Store (Capacitor) — Sprints 1–5 **complete** (shell, signed sideload, Bearer auth, Glance widget, FCM registration). Play Console / Firebase / ops remaining — [`docs/M11_SPRINT_PLAN.md`](docs/M11_SPRINT_PLAN.md), [#429](https://github.com/Sturmi77/correlcore/issues/429). Sideload APKs attach to `v*` GitHub Releases.
- [ ] **M12** — SaaS mode (managed hosting)
- [ ] **M13** — Photo & media: MinIO persist + gallery; **EXIF strip foundation** shipped (`POST /media/photos`, #28); optional Immich follow-up

Full roadmap: [`docs/DESIGN_DOCUMENT.md`](docs/DESIGN_DOCUMENT.md)  
Doc/version gaps for the `1.0.x` line: [`docs/releases/RELEASE_1_0_X_DOC_SYNC.md`](docs/releases/RELEASE_1_0_X_DOC_SYNC.md)

<details>
<summary><strong>Completed milestones (M0–M10.1) — archived</strong></summary>

<br />

Shipped with public selfhost **v1.x** (latest **v1.3.0**). Full table and links:
[`docs/releases/COMPLETED_MILESTONES.md`](docs/releases/COMPLETED_MILESTONES.md).

| Milestone            | Summary                                                  |
| -------------------- | -------------------------------------------------------- |
| **M0–M2**            | Monorepo, daily entry, Fernet, auth, charts, export      |
| **M3–M3.7**          | Insights v1, polish, maturity phases, color system       |
| **M4 / M4.1**        | PWA hardening + Dexie offline sync (feature-flagged)     |
| **M5 / M5.1**        | Habits Core + UX polish                                  |
| **M7**               | Insights v2 (Lasso, lag, clustering; digest foundations) |
| **M9 / M10 / M10.1** | Beta hardening, public selfhost v1.0, insight triggers   |

</details>

---

## Tech Stack

| Layer              | Technology                                                                                          | Rationale                                                                                                    |
| ------------------ | --------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------ |
| **Backend API**    | FastAPI (Python 3.12)                                                                               | Async, OpenAPI-native, fast iteration                                                                        |
| **Web Frontend**   | SvelteKit + Skeleton UI                                                                             | Performance, bundle < 150 KB gz                                                                              |
| **Mobile**         | Responsive web + PWA; Capacitor Android (`apps/android`) — sideload via GitHub Releases; Play = M11 | Maximum code sharing, Health Connect later ([ADR-0002](docs/adr/0002-capacitor-statt-twa.md))                |
| **Charts**         | Custom SVG components                                                                               | No external framework, JS budget maintained, token-compliant                                                 |
| **Database**       | PostgreSQL 16 + pgvector                                                                            | Row-level security for multi-user, vector for insights                                                       |
| **Cache / Queue**  | Redis 7                                                                                             | Sessions, rate limiting, sync queue                                                                          |
| **Object Storage** | MinIO (**M13**)                                                                                     | Not in current compose; EXIF-strip API stub only — see [`docs/M13_NOTES.md`](docs/M13_NOTES.md)              |
| **Reverse Proxy**  | Traefik v3 (selfhost Path A); host Nginx for correlcore.com (M10.2)                                 | One TLS edge only — see [`docs/M10_2_PUBLIC_HOSTED_LAUNCH_PLAN.md`](docs/M10_2_PUBLIC_HOSTED_LAUNCH_PLAN.md) |
| **Auth**           | Native JWT phase 1, Authentik from M12                                                              | OIDC, SSO, selfhostable ([ADR-0004](docs/adr/0004-auth-strategie.md))                                        |
| **Offline Sync**   | Dexie.js (IndexedDB) — M4.1 complete, feature-flagged                                               | Push/pull LWW merge, conflict log, local-first entry path; enable in Settings                                |
| **Analytics**      | pandas + scikit-learn                                                                               | M7: Lasso, lag, symptom analytics; correlation engine live since M3                                          |
| **Migrations**     | Alembic                                                                                             | Schema versioning                                                                                            |
| **Monitoring**     | GlitchTip + Uptime Kuma                                                                             | Selfhosted error tracking                                                                                    |
| **Notifications**  | FCM (Capacitor, optional) · UnifiedPush planned (M4.2)                                              | Privacy-first push; Firebase off by default for selfhost                                                     |

---

## Quickstart (Selfhost)

Full install guide: [`docs/selfhost/INSTALL.md`](docs/selfhost/INSTALL.md) (Traefik, DNS, backup, homelab variant).

### Prerequisites

- Docker >= 24 + Docker Compose v2
- A domain with DNS pointing to your server (public VPS path)

### Setup

```bash
git clone https://github.com/Sturmi77/correlcore.git
cd correlcore/infra/docker
cp .env.example .env
# Edit .env: DOMAIN, LETSENCRYPT_EMAIL, SECRET_KEY, ENCRYPTION_KEY, passwords — see INSTALL.md
# Prefer IMAGE_TAG=v1.3.0 (or latest v1.x) for published GHCR images
# Set acme email in traefik/traefik.yml to match LETSENCRYPT_EMAIL
docker compose up -d
```

After startup, CorrelCore is available at `https://your-domain.tld`

Homelab / Tailnet without public DNS: see [`infra/dockhand/README.md`](infra/dockhand/README.md).

Compose stack matrix (canonical vs secondary, profiles `worker` / `digest`):
[`docs/selfhost/COMPOSE_STACKS.md`](docs/selfhost/COMPOSE_STACKS.md).

Android sideload (optional, M11 pre-Play): download the APK from a [`v*`](https://github.com/Sturmi77/correlcore/releases) release — see [`docs/selfhost/ANDROID_SIDELOAD.md`](docs/selfhost/ANDROID_SIDELOAD.md).

> **Note:** Public selfhost **`1.x`** is the supported release line (latest `v1.3.0`). M8 core (manual sleep + HC sleep import) ships in this tag; remaining M8 follow-ups, M11 Play exit, and M13 full scope stay active development. See [`SECURITY.md`](SECURITY.md) and [`CHANGELOG.md`](CHANGELOG.md).

### Deployment mode (hosted vs. self-host)

One web bundle serves both a self-hosted instance and the managed SaaS. The
anonymous landing decides its primary call-to-action **at runtime** from a
public descriptor (`GET /api/v1/instance`) — no separate build. Two env vars
control it:

| Env variable           | Default    | Effect                                                                                     |
| ---------------------- | ---------- | ------------------------------------------------------------------------------------------ |
| `DEPLOYMENT_MODE`      | `selfhost` | `selfhost` \| `hosted` — badge wording + default CTA framing.                              |
| `REGISTRATION_ENABLED` | `true`     | Open self-registration → landing shows **Create account**; `false` → **Self-host** (docs). |

Defaults need no configuration: a self-host instance shows **Create account**
(register on _your_ instance); **Log in** is always present; logged-in users
never see the landing. Full behavior table and per-role walkthrough:
[`docs/selfhost/INSTANCE_MODE.md`](docs/selfhost/INSTANCE_MODE.md).

---

## Monorepo Structure

```
correlcore/
├── apps/
│   ├── web/          # SvelteKit web app + PWA (service worker, install banner)
│   └── android/      # Capacitor Android app (sideload APK; Play Store = M11 exit)
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
│   ├── releases/               # Completed milestones archive, 1.0.x sync checklist
│   ├── assets/brand/           # Logo mark for docs / README
│   ├── quality/                # Quality gate reports
│   └── adr/                    # Architecture decision records
├── docs-site/                  # MkDocs Material → GitHub Pages
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

**Public docs site:** [sturmi77.github.io/correlcore](https://sturmi77.github.io/correlcore/) —
install guide, user guide, API overview, privacy. Source: [`docs-site/`](docs-site/).

| Document                                                                | Content                                                            |
| ----------------------------------------------------------------------- | ------------------------------------------------------------------ |
| [DESIGN_DOCUMENT.md](docs/DESIGN_DOCUMENT.md)                           | Vision, features, architecture, roadmap — single source of truth   |
| [ARCHITECTURE.md](docs/ARCHITECTURE.md)                                 | Component diagram, deployment topologies, sync protocol            |
| [API.md](docs/API.md)                                                   | OpenAPI guidelines, endpoints, auth flow                           |
| [FRONTEND.md](docs/FRONTEND.md)                                         | Mobile/Web roles, responsive shell, component ownership            |
| [DEVELOPMENT.md](docs/DEVELOPMENT.md)                                   | Local setup, quality gates, NAS/pnpm notes, test database          |
| [Completed milestones](docs/releases/COMPLETED_MILESTONES.md)           | Archived M0–M10.1 checklist                                        |
| [1.0.x doc sync](docs/releases/RELEASE_1_0_X_DOC_SYNC.md)               | Remaining updates to fully reflect the release line                |
| [M11 Sprint Plan](docs/M11_SPRINT_PLAN.md)                              | Android Capacitor → Play Closed Testing                            |
| [Android sideload](docs/selfhost/ANDROID_SIDELOAD.md)                   | Install signed APK from GitHub Releases                            |
| [Instance mode](docs/selfhost/INSTANCE_MODE.md)                         | Hosted vs. self-host landing CTA — `DEPLOYMENT_MODE`, registration |
| [Phase & Insight Matrix](docs/PHASE_INSIGHT_MATRIX.md)                  | Maturity phases, unlock gates, thresholds                          |
| [Open decisions](docs/quality/OPEN_DECISIONS_AND_BACKLOG_2026-07-16.md) | What still needs a product/ops decision                            |
| [ADR Index](docs/adr/)                                                  | Architecture decision records                                      |
| [Quality Gates](docs/quality/)                                          | Visual QA and quality gate reports                                 |

Additional milestone plans, market analysis, and feature notes live under [`docs/`](docs/).

---

## Contributing

CorrelCore is currently a solo project. See [`CONTRIBUTING.md`](CONTRIBUTING.md) for language policy, PR rules, and Definition of Done. Issues and discussions are welcome.

**Interested in beta / sideload testing?** Open an [issue](https://github.com/Sturmi77/correlcore/issues/new?template=beta_tester.md) or follow [Android sideload](docs/selfhost/ANDROID_SIDELOAD.md).

---

## License

CorrelCore is released under the [GNU Affero General Public License v3.0](LICENSE). For commercial selfhost licenses without AGPL copyleft, contact via issue.

---

## Disclaimer

CorrelCore is **not a medical diagnostic tool**. All correlations and insights shown are intended solely for personal reflection and do not replace medical or therapeutic advice.

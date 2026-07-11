# M9 Visual QA Closeout

Date: 2026-07-11

Scope: Settings privacy self-service surfaces and install/onboarding documentation
flows for beta hardening (M9 Sprints 1, 3, 5, 6). Full-app smoke remains covered
by existing `smoke.spec.ts`.

## Result

**M9 GUI QA: passed.**

No critical blocker was found. Settings privacy controls render, GDPR E2E paths
complete with mocked API, and install/beta documentation is internally consistent.
Remaining items are operator actions (live beta cohort, production GlitchTip DSN,
external pentest vendor) — not functional blockers for M9 exit.

## Test Environment

| Area | Detail |
| ---- | ------ |
| Web | Playwright dev server at `http://127.0.0.1:4173` |
| API | Mocked via `page.route('**/api/v1/**')` in GDPR spec |
| Locale | `en` forced via localStorage |
| M9 phase | Sprint 6 closeout |

## GUI Coverage — Settings privacy (Sprint 1)

| Surface | Result | Evidence |
| ------- | ------ | -------- |
| Settings → Privacy policy link | Pass | `gdpr-self-service.spec.ts` — navigates to `/privacy`, sections render |
| `/privacy` page | Pass | PRIVACY.md content reachable in-app |
| ZIP export (Art. 20) | Pass | Export button triggers `GET /user/export`; download initiated |
| Analytics opt-out (Art. 21) | Pass | Toggle sends `PATCH /user/preferences` with `analytics_enabled: false` |
| Account deletion (Art. 17) | Pass | Password confirm → `DELETE /user/me` → session cleared |

## GUI Coverage — Core smoke (regression)

| Route / surface | Result | Notes |
| --------------- | ------ | ----- |
| `/auth/login` | Pass | Redirects to protected workflow |
| `/entries/new` | Pass | Autosave for daily metrics |
| `/trends`, `/insights` | Pass | Authenticated analytics surfaces render |

## Documentation flows — Install & beta (Sprint 3 + 5)

Checklist review (no live VPS required for M9 exit):

| Doc / flow | Result | Notes |
| ---------- | ------ | ----- |
| [`selfhost/INSTALL.md`](../selfhost/INSTALL.md) Path A (VPS) | Pass | Compose, Traefik, DNS, secrets, backup/restic/LUKS sections present |
| [`selfhost/INSTALL.md`](../selfhost/INSTALL.md) Path B (homelab) | Pass | Local dev pointer to AGENTS.md / DEVELOPMENT.md |
| [`traefik/traefik.yml`](../../infra/docker/traefik/traefik.yml) | Pass | Static config referenced from install guide |
| [`BETA_CHECKLIST.md`](../selfhost/BETA_CHECKLIST.md) | Pass | Links USER_WORKFLOWS + onboarding |
| [`BETA_ONBOARDING.md`](../selfhost/BETA_ONBOARDING.md) | Pass | Instance URL, test accounts, feedback channels |
| [`BETA_FEEDBACK_TRIAGE.md`](../selfhost/BETA_FEEDBACK_TRIAGE.md) | Pass | P0/P1/P2 routing documented |
| `.github/ISSUE_TEMPLATE/beta_feedback.md` | Pass | Structured GitHub feedback template |

## Observability note (Sprint 2)

GlitchTip integration is optional (`GLITCHTIP_DSN` unset = no outbound traffic).
PII scrub unit tests pass; staging 500 → GlitchTip verification is an operator
step after monitoring profile bootstrap — documented in [`M9_SPRINT_STATUS.md`](../M9_SPRINT_STATUS.md).

## Follow-ups (post-M9, non-blocking)

| Item | Target |
| ---- | ------ |
| External pentest vendor report | Operator — see [`M9_PENTEST.md`](M9_PENTEST.md) |
| Live beta tester roster (5–10) | Operator — [`BETA_ONBOARDING.md`](../selfhost/BETA_ONBOARDING.md) |
| Production restore log row | Operator — [`INSTALL.md`](../selfhost/INSTALL.md) §Backup |
| Symptom analytics external round 1 | [`M9_SYMPTOM_ANALYTICS_BETA_REVIEW.md`](M9_SYMPTOM_ANALYTICS_BETA_REVIEW.md) |

## Sign-off

M9 visual QA **approved** for milestone closeout (2026-07-11).

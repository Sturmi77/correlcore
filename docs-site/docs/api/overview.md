# API Overview

Summary of the CorrelCore REST API. Full reference:
[`docs/API.md`](https://github.com/Sturmi77/correlcore/blob/main/docs/API.md) in the repository.

Interactive OpenAPI docs are available on a running instance at `/api/docs` (Swagger UI).

---

## General conventions

| Topic       | Convention                                                                    |
| ----------- | ----------------------------------------------------------------------------- |
| Base path   | `/api/v1/...`                                                                 |
| Auth        | HttpOnly cookies (`access_token`, `refresh_token`) or `Authorization: Bearer` |
| Dates       | ISO 8601 UTC                                                                  |
| IDs         | UUID v4                                                                       |
| Errors      | FastAPI `{"detail": ...}` (422 for validation)                                |
| Rate limits | Per-endpoint via SlowAPI (Redis in production)                                |

---

## Authentication

Native JWT auth (Phase 1 selfhost). OIDC via Authentik planned for SaaS (M12+).

| Method | Path                               | Notes                               |
| ------ | ---------------------------------- | ----------------------------------- |
| `POST` | `/api/v1/auth/register`            | Always `202`; verify email required |
| `POST` | `/api/v1/auth/login`               | Sets cookies; `5/min/IP`            |
| `POST` | `/api/v1/auth/refresh`             | Rotates refresh token               |
| `POST` | `/api/v1/auth/logout`              | Clears cookies                      |
| `POST` | `/api/v1/auth/verify-email`        | Single-use token, 24h TTL           |
| `POST` | `/api/v1/auth/resend-verification` | Always `202`; `3/min/IP`            |
| `POST` | `/api/v1/auth/forgot-password`     | Always `202`; password reset mail   |
| `POST` | `/api/v1/auth/reset-password`      | Token + new password                |
| `GET`  | `/api/v1/auth/me`                  | Current user profile                |

Registration and resend endpoints use generic responses to prevent email enumeration.

---

## Health

| Method | Path             | Auth                               |
| ------ | ---------------- | ---------------------------------- |
| `GET`  | `/api/v1/health` | No                                 |
| `GET`  | `/health/live`   | No (container probe)               |
| `GET`  | `/health/ready`  | No (Postgres + Redis + encryption) |

---

## Entries & symptoms

| Method   | Path                                      | Notes                              |
| -------- | ----------------------------------------- | ---------------------------------- |
| `GET`    | `/api/v1/entries`                         | List with date filters             |
| `POST`   | `/api/v1/entries`                         | Create daily entry                 |
| `GET`    | `/api/v1/entries/{id}`                    | Single entry                       |
| `PATCH`  | `/api/v1/entries/{id}`                    | Update entry                       |
| `DELETE` | `/api/v1/entries/{id}`                    | Delete entry                       |
| `POST`   | `/api/v1/entries/{id}/note-markers`       | Add note marker                    |
| `DELETE` | `/api/v1/entries/{id}/note-markers/{mid}` | Remove note marker                 |
| `GET`    | `/api/v1/entries/{id}/note-signals`       | Extracted note signals             |
| `GET`    | `/api/v1/symptoms`                        | Curated + custom symptoms          |

Mood, energy, stress, tags, symptoms, and notes are stored per calendar day.
Custom symptom slugs are HMAC-stabilized ([ADR-0039](https://github.com/Sturmi77/correlcore/blob/main/docs/adr/0039-slug-hmac-custom-symptoms.md)).

---

## Insights & analytics

| Method | Path                              | Notes                               |
| ------ | --------------------------------- | ----------------------------------- |
| `GET`  | `/api/v1/insights`                | Generated insight cards             |
| `GET`  | `/api/v1/insights/digest/latest`  | Weekly digest snapshot (foundation) |
| `GET`  | `/api/v1/insights/tag-clusters`   | Tag groups (tiered maturity, M10.1) |
| `POST` | `/api/v1/insights/regenerate`     | On-demand insight run (1×/hour)     |
| `POST` | `/api/v1/insights/trigger`        | Admin manual worker run             |
| `GET`  | `/api/v1/analysis/notes/marker-summary` | Note-marker mood aggregates   |
| `GET`  | `/api/v1/analytics/...`           | Trends, correlations (authenticated)|

Insight generation runs in the background **worker** (nightly 03:00 UTC) or on demand via
**Settings → Analysis → Refresh insights** (`POST /insights/regenerate`).
Weekly digests: `python -m app.workers.digest --once` (push delivery still depends on M4.2).

---

## Habits

| Method   | Path                  | Notes                     |
| -------- | --------------------- | ------------------------- |
| `GET`    | `/api/v1/habits`      | User habit definitions    |
| `POST`   | `/api/v1/habits`      | Create build/reduce habit |
| `PATCH`  | `/api/v1/habits/{id}` | Update habit              |
| `DELETE` | `/api/v1/habits/{id}` | Remove habit              |

---

## User & GDPR

| Method   | Path                           | Notes                              |
| -------- | ------------------------------ | ---------------------------------- |
| `GET`    | `/api/v1/user/export`          | GDPR Art. 20 data export           |
| `DELETE` | `/api/v1/user/me`              | Account erasure (password confirm) |
| `GET`    | `/api/v1/user/me/consents`     | Consent history + current state    |
| `POST`   | `/api/v1/user/me/consents`     | Record grant/revoke                |
| `POST`   | `/api/v1/user/me/consents/revoke` | Revoke consent                  |
| `GET`    | `/api/v1/user/preferences`     | Insight / onboarding preferences   |
| `PATCH`  | `/api/v1/user/preferences`     | Update preferences                 |

---

## Media (M13 foundation)

| Method | Path                    | Notes                                              |
| ------ | ----------------------- | -------------------------------------------------- |
| `POST` | `/api/v1/media/photos`  | Upload with server-side EXIF strip; MinIO later    |

---

## Offline sync (M4.1)

| Method | Path                          | Notes                       |
| ------ | ----------------------------- | --------------------------- |
| `POST` | `/api/v1/sync/push`           | Client change batches       |
| `GET`  | `/api/v1/sync/pull`           | Server changes since cursor |
| `GET`  | `/api/v1/user/sync-conflicts` | Conflict log                |

Feature-flagged; requires verified user and server-side enablement.

---

## Web proxy note

The SvelteKit web container proxies `/api/*` to the internal API (`INTERNAL_API_URL`,
default `http://api:8000`). Browser clients should call `/api/v1/...` on the same
origin as the web UI — no CORS configuration needed for same-host deployments.

See [ADR-0011](https://github.com/Sturmi77/correlcore/blob/main/docs/adr/0011-web-internal-reverse-proxy.md).

---

## Rate limits (summary)

| Endpoint group      | Limit                                             |
| ------------------- | ------------------------------------------------- |
| Login / Register    | 5 / min / IP                                      |
| Resend verification | 3 / min / IP                                      |
| Entries (write)     | 60–120 / min / user                               |
| General API         | 100 / min / IP (Traefik middleware in production) |

Production uses Redis-backed rate limit storage.

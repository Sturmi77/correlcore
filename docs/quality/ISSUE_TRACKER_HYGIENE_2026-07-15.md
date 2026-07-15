# Issue Tracker Hygiene — 2026-07-15

Operator close list for issues that are **already shipped on `main`** but still
open on GitHub. The cloud-agent token cannot call `closeIssue` (HTTP 403);
maintainers should close these with the comments below.

## Close now (18)

| Issue | Reason | Evidence |
| ----- | ------ | -------- |
| #251–#254, #260–#271, #273 | M5.1 UX polish O-02–O-19 | PR #281, CHANGELOG, `OPTIMIZATION_BACKLOG.md` |
| #272 | O-20 password reset | PR #284, `auth/forgot-password`, migration `019_*` |
| #29 | DSGVO Art. 17 account deletion | `DELETE /api/v1/user/me`, M9 quality gate |

Suggested close comment (UX cluster):

> Shipped on main (M5.1 / PR #281). Tracker hygiene — acceptance criteria met.
> See CHANGELOG and `docs/frontend/OPTIMIZATION_BACKLOG.md`.

Suggested close comment (#272):

> Shipped in PR #284. See `docs/frontend/O-20_PASSWORD_RESET_PLAN.md`.

Suggested close comment (#29):

> Shipped as `DELETE /api/v1/user/me` (M9). See CHANGELOG / M9 quality gate.

## Remains open (implement in this PR series)

| Wave | Issues |
| ---- | ------ |
| M4.1.1 | #258 |
| Notes A–C | #194–#199, #198 |
| M8 signals | #201, #202 |
| M11 / HC | #27, #31 |
| Optional | #147, #148, #149, #62, #28 |

Doc drift fixed in-repo: O-20 status → **Done** in `OPTIMIZATION_BACKLOG.md`.

# Issue Tracker Hygiene — 2026-07-15

> **Follow-up:** see [`ISSUE_TRACKER_HYGIENE_2026-07-31.md`](ISSUE_TRACKER_HYGIENE_2026-07-31.md)
> for the current open-issue close list (#488, #459, #588).

Operator close list for issues that are **already shipped on `main`**
(merged via PR [#393](https://github.com/Sturmi77/correlcore/pull/393) and earlier
milestone work). The cloud-agent token (`cursor[bot]`) cannot call `closeIssue`
(HTTP 403 / no triage permission).

### Close immediately (repo owner)

```bash
for n in 29 251 252 254 260 261 262 263 264 265 266 267 268 269 270 271 272 273 \
         258 194 195 196 197 198 199 201 202 27 31 147 148 149 62 28; do
  gh issue close "$n" --repo Sturmi77/correlcore \
    --comment "Closed as part of open-issues implementation (PR #393)."
done
```

PR #393 is merged; close the issue numbers above if GitHub auto-close did not fire.

## Close now (18 — UX / account, already on main before #393)

| Issue                      | Reason                         | Evidence                                           |
| -------------------------- | ------------------------------ | -------------------------------------------------- |
| #251–#254, #260–#271, #273 | M5.1 UX polish O-02–O-19       | PR #281, CHANGELOG, `OPTIMIZATION_BACKLOG.md`      |
| #272                       | O-20 password reset            | PR #284, `auth/forgot-password`, migration `019_*` |
| #29                        | DSGVO Art. 17 account deletion | `DELETE /api/v1/user/me`, M9 quality gate          |

Suggested close comment (UX cluster):

> Shipped on main (M5.1 / PR #281). Tracker hygiene — acceptance criteria met.
> See CHANGELOG and `docs/frontend/OPTIMIZATION_BACKLOG.md`.

Suggested close comment (#272):

> Shipped in PR #284. See `docs/frontend/O-20_PASSWORD_RESET_PLAN.md`.

Suggested close comment (#29):

> Shipped as `DELETE /api/v1/user/me` (M9). See CHANGELOG / M9 quality gate.

## Close after merge of PR #393 (implemented foundations)

These items were implemented in the open-issues series and should be closed on
GitHub if still open:

| Wave               | Issues           | Evidence                                    |
| ------------------ | ---------------- | ------------------------------------------- |
| M4.1.1             | #258             | Migration 023, sync hardening               |
| Notes A–C + ADRs   | #194–#199        | Migration 024, ADR-N-01–03                  |
| Notes signals      | #201, #202       | `note_signal_extractor`, evidence           |
| M11 / HC           | #27, #31         | `apps/android`, `consent_log`               |
| Digest / analytics | #147, #148, #149 | Digest worker, Ollama optional, changepoint |
| Security / media   | #62, #28         | ADR-0039 / migration 027, `/media/photos`   |

Doc drift fixed in-repo: O-20 status → **Done** in `OPTIMIZATION_BACKLOG.md`;
status sync for foundations → docs PR `docs-status-sync`.

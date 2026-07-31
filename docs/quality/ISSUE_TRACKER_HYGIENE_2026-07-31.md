# Issue Tracker Hygiene — 2026-07-31

Operator close list for issues that are **already shipped / tracking-complete**
but still open (missing `Closes #…` on the shipping PR, or tracking doc done).

The cloud-agent token (`cursor[bot]`) **cannot** call `closeIssue` /
`addComment` (HTTP 403 / no triage permission). Repo owner must run the
commands below.

Audit of all **12** open issues on 2026-07-31; July-15 hygiene list is already
fully closed.

---

## Close immediately (repo owner)

```bash
gh issue close 488 --repo Sturmi77/correlcore --comment "$(cat <<'EOF'
Shipped on main:

- Phase 1: #581 (lag-aware event windows + sheet marker)
- Phase 1b: #583 (lag profile mini-bars on InsightCard)
- Phase 2: #586 (lag-correlation heatmap; acceptance met)
- Backfill: #596 (`lag_profile` on persisted lag insights)

Tracker hygiene — auto-close did not fire (`Completes #488` without `Closes`). Closing as done.
EOF
)"

gh issue close 459 --repo Sturmi77/correlcore --comment "$(cat <<'EOF'
Sprint 0 / tracking deliverables done (#458: plan + status + roadmap). M10 closed; M10.2 exists.

Phase 0 domain sync (#548) and landing Phase 2 (#550) done. Remaining M10.2 work stays in #461 / #462 / #464.

Closing this tracking issue (hygiene).
EOF
)"

gh issue close 588 --repo Sturmi77/correlcore --comment "$(cat <<'EOF'
Fixed / clarified on main via #593:

- Anonymous visitors on `/` get `LandingPage` (marketing)
- Authenticated sessions get Home (Topologie A/B by design)
- Escape hatch: `/?landing=1` for landing preview while logged in

If apex still shows App-Home while logged out (incognito), reopen with repro. Closing as done / WAD after the fix.
EOF
)"
```

---

## Close candidates (detail)

| Issue    | Title                                       | Evidence                                                                                                                                                                                                                                       | Why still open                                   |
| -------- | ------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------ |
| **#488** | Lag correlation visualization               | PRs [#581](https://github.com/Sturmi77/correlcore/pull/581), [#583](https://github.com/Sturmi77/correlcore/pull/583), [#586](https://github.com/Sturmi77/correlcore/pull/586), [#596](https://github.com/Sturmi77/correlcore/pull/596) on main | PR #586 said “Completes #488”, not `Closes #488` |
| **#459** | docs(M10.2): sprint plan + status + roadmap | [#458](https://github.com/Sturmi77/correlcore/pull/458); Altlasten-Plan Phase 0.2 + Phase 2 done (#548, #550)                                                                                                                                  | Tracking issue never closed after Sprint 0       |
| **#588** | correlcore.com → App statt Landing          | [#593](https://github.com/Sturmi77/correlcore/pull/593) (`Relates to #588`); anonymous → Landing, auth → Home, `?landing=1`                                                                                                                    | No `Closes #588`; expected for logged-in users   |

---

## Keep open

| Issue    | Why                                                                                                                     |
| -------- | ----------------------------------------------------------------------------------------------------------------------- |
| **#601** | Insight-Dismiss Archiv/Undo — Feature Request only (spec in #602); not implemented                                      |
| **#591** | Push ohne Play Store — open discussion                                                                                  |
| **#587** | Tag-Gruppen-Benennung — fix on main (`a7de9fb` / #593 area) but **prod** still older image; close after redeploy verify |
| **#585** | Device QA Compare strip zoom — manual sign-off pending (`COMPARE_AXIS_ZOOM_CAZ3_QA.md`)                                 |
| **#547** | Cycle Tracking v1 — Stages 2–3 / bleeding enum still open                                                               |
| **#528** | Capacitor 7→8 — not started (`@capacitor/core` still 7.x); correctly supersedes closed #522                             |
| **#464** | `docs/runbooks/nas-to-vps.md` still missing                                                                             |
| **#462** | Hosted Impressum still generic Selfhost placeholder                                                                     |
| **#461** | SMTP checkboxes mostly done; Hosted Mailpit removal still open                                                          |

---

## After close — optional M10.2 note

Milestone **M10.2** should then retain only **#461, #462, #464** (plus any new work).
#460 / #463 already closed earlier.

## Soft follow-up (not in the close script)

After production redeploy past `a7de9fb` / verify script green:

```bash
gh issue close 587 --repo Sturmi77/correlcore --comment \
  "Verified on production after redeploy (tag-group auto-naming). Closing."
```

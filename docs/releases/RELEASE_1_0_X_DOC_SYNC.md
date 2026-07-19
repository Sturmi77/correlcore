# Release 1.0.x — documentation & version sync

**Date:** 2026-07-19  
**Current line:** **`v1.0.6`** / manifests **`1.0.6`**  
**Git tags:** `v1.0.0` … `v1.0.6`

Completed-milestone archive: [`COMPLETED_MILESTONES.md`](COMPLETED_MILESTONES.md).

## Status

P0–P2 sync from the post-`v1.0.5` doc audit is **done** (merged via #455 / #456).
Patch **`v1.0.6`** packages the remaining tester fixes (#441–#444), persistent
session (`remember_me`, #453), and bumps install pins / manifests to `1.0.6`.

## Still optional (P3)

| Item | Notes |
| ---- | ----- |
| `BETA_ONBOARDING.md` / `BETA_CHECKLIST.md` | Still “pre-release” framing — reframe or archive when convenient |
| `M4_VISUAL_QA.md` Dexie deferral banner | Low priority historical QA doc |
| OCI image labels on Dockerfiles | Optional hardening |

## Patch release policy

For each new `v1.0.N`: add a CHANGELOG section, bump manifests/i18n/export/Android
defaults, pin install docs to the new tag, then
`git tag -a v1.0.N && git push origin v1.0.N`.
See [`GO_PUBLIC_CHECKLIST.md`](../selfhost/GO_PUBLIC_CHECKLIST.md) § Post-1.0.x.

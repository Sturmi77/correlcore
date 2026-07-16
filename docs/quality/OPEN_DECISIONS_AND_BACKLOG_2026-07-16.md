# Open decisions & hygiene backlog — 2026-07-16

Companion to the security audit
([`SECURITY_MAINTAINABILITY_AUDIT_2026-07-16.md`](SECURITY_MAINTAINABILITY_AUDIT_2026-07-16.md))
and the hygiene PR that fixed live bugs / deferred-feature honesty.

This document lists what is **still open** or **needs a product/ops decision**.
It is the living pointer; historical sprint audits under `docs/frontend/` and
`docs/quality/` should be treated as **archives** unless linked from here.

---

## Fixed in hygiene pass (2026-07-16)

- Digest unauthenticated redirect → `/auth/login?next=/insights/digest`
- InsightCard dismiss wired through feed / mobile lead / insights page
- Stub per-insight “Export CSV” control removed (Settings export remains)
- `APP_VERSION` / export version defaults → `1.0.0`
- `FRONTEND_BASE_URL` aligned with `WEB_HOST_PORT` in user-test / dockge examples
- Health Connect + digest copy marked deferred / preview-honest
- docs-site `DELETE /user/account` → `/user/me` (+ password-reset rows)

---

## Needs a decision

| ID | Topic | Why it blocks | Plan / notes |
| -- | ----- | ------------- | ------------ |
| D-D1–D-D4 | Weekly digest delivery | Toggle promises Sunday summary; worker not in compose | [`WEEKLY_DIGEST_COMPLETION_PLAN.md`](../features/WEEKLY_DIGEST_COMPLETION_PLAN.md) |
| D-L1–D-L4 | LayerChart vs custom SVG | Adapter stub forever vs real dependency | [`LAYER_CHART_COMPLETION_PLAN.md`](../frontend/LAYER_CHART_COMPLETION_PLAN.md) |
| D-S1 | Access JWT in JSON body | XSS can still steal token despite HttpOnly cookies | Security audit M7 — omit for browser cookie flows |
| D-S2 | Password policy strength | Art. 9 health data; min length 8 today | Security audit M8 |
| D-S3 | SlowAPI when Redis down | Fail closed (500) vs in-memory fallback | Security audit M9 |
| D-I1 | Compose/env stack consolidation | Five stacks drift (`SLUG_HMAC`, ports, `:?` required vars) | Prefer generate-from-one-source |
| D-I2 | Dependabot / Renovate | Manual bumps + CI audit only | M9 noted; still missing |
| D-I3 | docs-site vs `docs/API.md` | German API.md stale; docs-site thin | Pick canonical: OpenAPI + English docs-site |
| D-I4 | Archive stamp for old audits | Agents re-open fixed GUI findings | Add `Status: Historical` headers opportunistically |

---

## Explicitly deferred (documented, do not “finish” early)

| Feature | Milestone | Foundation today | Spec |
| ------- | --------- | ---------------- | ---- |
| Photo / MinIO media | **M13** | `POST /media/photos` EXIF strip stub (`stored=false`) | [`M13_NOTES.md`](../M13_NOTES.md) |
| Health Connect import | **M8** (+ **M11** Android shell) | Consent API + Settings UI only; no sync | [`M8_NOTES.md`](../M8_NOTES.md) |
| Capacitor Play Store | **M11** | `apps/android` scaffold | README roadmap |
| SaaS / Authentik | **M12** | Native JWT only | ADR-0004 |
| Parallel React GUI | Unscheduled | `apps/web-react/CLAUDE.md` only; no package | [`PARALLEL_REACT_GUI.md`](../frontend/PARALLEL_REACT_GUI.md) |

---

## Completion plans (active)

1. [Weekly Digest completion](../features/WEEKLY_DIGEST_COMPLETION_PLAN.md)  
2. [LayerChart completion](../frontend/LAYER_CHART_COMPLETION_PLAN.md)

---

## Suggested next engineering slices

1. Digest WP1–WP2 after D-D1–D-D3  
2. LayerChart D-L1 spike (dependency fit) before any UI port  
3. Docs-site API expansion (O-20, notes, consents) under D-I3  
4. Security follow-ups D-S1–D-S3 on a dedicated PR

# M10.2 Sprint Status — Public Hosted Launch

Last updated: 2026-07-19  
Plan: [`M10_2_PUBLIC_HOSTED_LAUNCH_PLAN.md`](M10_2_PUBLIC_HOSTED_LAUNCH_PLAN.md)

## Overall

| Item                         | Status                                      |
| ---------------------------- | ------------------------------------------- |
| Sprint 0 — Baseline          | **Done** (repo docs, decisions, GitHub issues #459–#464; NAS live-audit + milestones remain maintainer) |
| Sprint 1 — DNS + Nginx       | Pending                                     |
| Sprint 2 — SMTP              | Pending                                     |
| Sprint 3 — Landing / Legal   | Pending                                     |
| Sprint 4 — APK               | Pending (blocked on #429)                   |
| Sprint 5 — Closeout          | Pending                                     |
| Exit criteria                | Not met                                     |

---

## Binding decisions (Sprint 0)

| Decision | Binding answer |
| -------- | -------------- |
| Public domain | **`correlcore.com`** (not `.app` for Hosted/project contact going forward; doc sync in Sprint 3) |
| Launch edge | **Host-Nginx** only |
| Traefik on Hosted NAS | **Do not enable** while Nginx terminates TLS. Implement Traefik at **NAS→VPS** cutover (Path A), not in parallel |
| Mailpit on Hosted | Allowed only until Sprint 2 SMTP E2E is green → then **remove** Mailpit from Hosted stack. Selfhost quickstart **keeps** Mailpit |
| Landing origin | App route `/` on same origin as auth — no second static apex site |
| APK distribution | GitHub Releases canonical; landing links only; no second update channel unless explicitly mirrored |
| Scope vs M12 | Hosted reference ≠ SaaS (no Stripe/multi-tenant in M10.2) |
| Scope vs M10.1 naming | Insight pipeline M10.1 = done. Old „M10.1 deferred“ compose A/C/G stays backlog — **not** reopened as M10.2 |

---

## Gap matrix (Exit criteria)

| Exit criterion | Repo / product today | Hosted ops gap |
| -------------- | -------------------- | -------------- |
| Landing öffentlich | `LandingPage.svelte` + CTAs shipped (M10) | DNS + Nginx + deploy not cut over |
| Login ohne VPN | JWT/cookies + ADR-0011 proxy shipped | Public HTTPS origin + `COOKIE_SECURE` / Forwarded-Proto |
| Echte Mail | SMTP env + `email_service` shipped; Mailpit default in quickstart/dockhand | Real relay + SPF/DKIM/DMARC; remove Hosted Mailpit |
| Legal | `/impressum`, `/privacy` routes shipped | Hosted operator content + public URL |
| APK auffindbar | Release workflow + sideload docs (M11) | #429 secrets/first asset; landing CTA |
| Selfhost unberührt | INSTALL Path A/B + GHCR | Keep docs generic; no product hardcode |
| VPS-ready | Volumes/images portable in principle | `runbooks/nas-to-vps.md` missing |

---

## Baseline inventory (Sprint 0)

Live NAS/router values are **maintainer-filled** (no secrets in git). Repo-known defaults:

| Area | Repo-known / assumed | Maintainer confirm |
| ---- | -------------------- | ------------------ |
| Compose path | Dockhand / quickstart / production variants exist; Hosted should expose web localhost only | [ ] Which stack runs on NAS today? |
| Traefik | Production compose includes Traefik — **must stay off** for Hosted-Nginx | [ ] Confirmed not bound to 80/443 |
| Mailpit | Dockhand/quickstart default `SMTP_HOST=mailpit` | [ ] Present on Hosted? (ok until Sprint 2) |
| Nginx | INSTALL external-proxy path documented | [ ] Synology / host / other? Server block for correlcore.com? |
| DNS | Domain owned (`correlcore.com`) | [ ] A/AAAA / CGNAT / port-forward 80/443? |
| Tailscale | Homelab docs; end users must not need it after Sprint 1 | [ ] Admin-only after cutover? |
| SMTP provider | None in repo | [ ] Provider chosen? |
| Android signing | #429 open | [ ] Secrets ready? |

---

## Sprint 0 checklist

- [x] Canonical plan written (`M10_2_PUBLIC_HOSTED_LAUNCH_PLAN.md`)
- [x] Status + gap matrix + binding decisions (this file)
- [x] Anti-duplication rules (Mailpit/SMTP, Nginx/Traefik, SSoT table)
- [x] Roadmap links: DESIGN_DOCUMENT, README, COMPLETED_MILESTONES
- [x] INSTALL external-proxy note points to M10.2 (no Traefik parallel; compose profile G stays deferred)
- [x] M10 sprint deferred section clarifies ≠ M10.2 Hosted launch
- [ ] Maintainer: fill Baseline inventory checkboxes above (live NAS)
- [x] Tracking issues filed: #459 (docs/Sprint 0), #460 (DNS/Nginx), #461 (SMTP), #462 (landing/legal), #463 (APK CTA), #464 (NAS→VPS)
- [ ] Maintainer: close GitHub milestone **M10 — Public Selfhost v1.0** (#7) if still open _(CI token cannot mutate milestones — 403)_
- [ ] Maintainer: create GitHub milestone **M10.2 — Public Hosted Launch** and attach #459–#464 _(same)_

---

## Sprint 1–5 progress

### Sprint 1 — DNS + Nginx

- [ ] DNS A/AAAA
- [ ] Nginx TLS + proxy + headers
- [ ] Hosted ENV (`FRONTEND_BASE_URL`, `CORS_ORIGINS`, `COOKIE_SECURE`)
- [ ] Traefik **not** on 80/443
- [ ] Smoke `/` + `/api/v1/health` from public network

### Sprint 2 — SMTP

- [ ] Relay + SPF/DKIM/DMARC
- [ ] Verify/Reset E2E
- [ ] **Mailpit removed from Hosted stack**
- [ ] Selfhost quickstart still documents Mailpit (unchanged)

### Sprint 3 — Landing / Legal / domain docs

- [ ] Public landing + legal URLs
- [ ] `security@correlcore.com` doc sync (SECURITY.md, GO_PUBLIC, incident)
- [ ] No second apex static site

### Sprint 4 — APK

- [ ] #429 first signed release assets
- [ ] Landing CTA (only when asset exists)
- [ ] Hosted `VITE_API_BASE_URL`

### Sprint 5 — Closeout

- [ ] `docs/runbooks/nas-to-vps.md`
- [ ] Full launch smoke
- [ ] Exit criteria PASS / milestone

---

## Tracking issues

See Plan §11: #459–#464. Reuse #429 / #450 / #453 — do not file duplicates.

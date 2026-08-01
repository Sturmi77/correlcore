# M10.2 Sprint Status — Public Hosted Launch

Last updated: 2026-08-01  
Plan: [`M10_2_PUBLIC_HOSTED_LAUNCH_PLAN.md`](M10_2_PUBLIC_HOSTED_LAUNCH_PLAN.md)  
Backlog: [`M10_2_PUBLIC_HOSTED_LAUNCH_BACKLOG.md`](M10_2_PUBLIC_HOSTED_LAUNCH_BACKLOG.md)  
Combined cutover: [`runbooks/hosted-cutover.md`](runbooks/hosted-cutover.md)  
Topology options: [`runbooks/hosted-topology-options.md`](runbooks/hosted-topology-options.md)  
Topology H cutover: [`runbooks/hosted-topology-h-cutover.md`](runbooks/hosted-topology-h-cutover.md)

> **Update 2026-07-26 — Cutover erfolgt.** Der öffentliche Betrieb auf
> `correlcore.com` ist live (Edge-/Auth-Cookie-/Nginx-Fixes #526/#527/#531/#540,
> Landing #510/#512). Verbleibende Punkte, Entscheidungen und Reihenfolge stehen
> gebündelt in [`proposals/M102_ALTLASTEN_ONBOARDING_PLAN.md`](proposals/M102_ALTLASTEN_ONBOARDING_PLAN.md).
> Noch offen: #461 (SMTP/Mailpit verifizieren + aus Hosted entfernen), #462
> (Hosted-Impressum/Legal + Domain-Doku-Sync), #464 (`nas-to-vps.md`). #463
> (Landing APK-CTA) ist erledigt.

## Overall

| Item                       | Status                                                                    |
| -------------------------- | ------------------------------------------------------------------------- |
| Sprint 0 — Baseline        | **Done** (repo + issues #459–#464; milestones/NAS inventory → maintainer) |
| Sprint 1 — DNS + Nginx     | **Repo done**; live ops via combined cutover                              |
| Sprint 2 — SMTP            | **Repo done** (SMTP + cutover runbooks); live ops same window as S1       |
| Topology decision (A/B/H)  | **H live** (`app.correlcore.com` + IONOS apex marketing)                  |
| Sprint 3 — Landing / Legal | **Landing live**; Legal-Content + Domain-Doku offen (#462)                |
| Sprint 4 — APK             | **APK-CTA done** (#463); Signing-Ops (#429) separat                       |
| Sprint 5 — Closeout        | Pending — `nas-to-vps.md` (#464) + Milestone-Close                        |
| Exit criteria              | **Teilweise erfüllt** — Cutover live; offen: #461/#462/#464               |

**Maintainer next step:**

Topology **H** is live (FRONTEND_BASE_URL=https://app.correlcore.com; register/verify E2E green).
Remaining open: #461 (SMTP/Mailpit verify), #462 (legal/domain docs), #464 (
as-to-vps.md).
Runbook: [
unbooks/hosted-topology-h-cutover.md](runbooks/hosted-topology-h-cutover.md).
---

## Binding decisions (Sprint 0 + topology)

| Decision                     | Binding answer                                                         |
| ---------------------------- | ---------------------------------------------------------------------- |
| Public domain                | **`correlcore.com`** (doc sync `.app`→`.com` in Sprint 3)              |
| Hosted topology              | **H** — IONOS marketing on apex + app on `app.correlcore.com`          |
| Launch edge on NAS           | **Host-Nginx** for app origin; no Traefik parallel                     |
| Traefik on Hosted NAS        | **Do not enable** while Nginx terminates TLS                           |
| Mailpit on Hosted            | Until SMTP E2E → then **remove**. Quickstart keeps Mailpit             |
| SMTP                         | Prefer **IONOS SMTP** (MX/SPF already there)                           |
| Landing origin               | Same origin as auth on the **app host** (apex for A/B, `app.` for H)   |
| Website@IONOS + API-only NAS | **Not supported** (cookies/same-origin); use **H** or full proxy **B** |
| APK                          | GitHub Releases canonical                                              |
| Scope vs M12 / M10.1 naming  | Hosted ≠ SaaS; insight M10.1 done; compose A/C/G not M10.2             |

---

## Gap matrix (Exit criteria)

| Exit criterion     | Repo / product today                      | Hosted ops gap                            |
| ------------------ | ----------------------------------------- | ----------------------------------------- |
| Landing öffentlich | Landing code shipped; Nginx runbook ready | DNS still IONOS Apache — cutover S1-O6/O7 |
| Login ohne VPN     | Auth + ADR-0011 shipped                   | Public edge + Hosted ENV on NAS           |
| Echte Mail         | SMTP code shipped                         | Sprint 2 ops                              |
| Legal              | Routes shipped                            | Public URL + Hosted content (Sprint 3)    |
| APK auffindbar     | Workflow + sideload docs                  | #429 + landing CTA                        |
| Selfhost unberührt | INSTALL Path A/B                          | Keep generic                              |
| VPS-ready          | Images/volumes portable                   | `nas-to-vps.md` (Sprint 5)                |

---

## Baseline inventory (Sprint 0 → maintainer)

| Area            | Repo-known / observed                                                    | Maintainer confirm                 |
| --------------- | ------------------------------------------------------------------------ | ---------------------------------- |
| Compose path    | Dockhand / quickstart / production                                       | [ ] Which stack on NAS?            |
| Traefik         | Must stay off 80/443 for Hosted-Nginx                                    | [ ] Confirmed                      |
| Mailpit         | OK until Sprint 2                                                        | [ ] Present on Hosted?             |
| Nginx           | Runbook [`runbooks/hosted-nginx-edge.md`](runbooks/hosted-nginx-edge.md) | [ ] Synology RP / host Nginx?      |
| DNS             | Apex A `217.160.0.166` (IONOS Apache, 2026-07-19)                        | [ ] Cutover plan A/B/C in runbook? |
| Tailscale       | Admin-only after cutover                                                 | [ ]                                |
| SMTP            | IONOS MX + SPF already                                                   | [ ] Relay choice Sprint 2          |
| Android signing | #429 open                                                                | [ ]                                |

---

## Sprint 0 checklist

- [x] Plan + status + anti-duplication
- [x] Roadmap links
- [x] Issues #459–#464
- [ ] Maintainer: NAS inventory + milestones M10 close / M10.2 create

---

## Sprint 1 checklist

### Repo (done)

- [x] Runbook [`runbooks/hosted-nginx-edge.md`](runbooks/hosted-nginx-edge.md)
- [x] Backlog [`M10_2_PUBLIC_HOSTED_LAUNCH_BACKLOG.md`](M10_2_PUBLIC_HOSTED_LAUNCH_BACKLOG.md)
- [x] STATUS/PLAN/INSTALL pointers
- [x] DNS observation documented (IONOS placeholder vs NAS target)

### Live cutover (maintainer — backlog S1-O1…O7)

- [ ] Web on localhost + Hosted ENV
- [ ] Nginx/RP + TLS + `X-Forwarded-Proto https`
- [ ] Traefik not on 80/443
- [ ] DNS/tunnel cutover from IONOS Apache to CorrelCore edge
- [ ] Public smoke `/` + `/api/v1/health` without VPN

---

## Sprint 2 checklist

### Repo (done)

- [x] [`runbooks/hosted-smtp.md`](runbooks/hosted-smtp.md)
- [x] [`runbooks/hosted-cutover.md`](runbooks/hosted-cutover.md) (S1+S2 one flip)
- [x] Backlog S2-R1 + cutover policy

### Live (maintainer — with Sprint 1 cutover)

- [ ] IONOS (or other) SMTP + DKIM/DMARC
- [ ] Hosted `SMTP_*` in same ENV apply as S1-O2
- [ ] Public verify/reset E2E
- [ ] Mailpit removed from Hosted

## Sprint 3–5

See [`M10_2_PUBLIC_HOSTED_LAUNCH_BACKLOG.md`](M10_2_PUBLIC_HOSTED_LAUNCH_BACKLOG.md).

---

## Tracking issues

| Sprint | Issue                  |
| ------ | ---------------------- |
| 0      | #459                   |
| 1      | #460                   |
| 2      | #461                   |
| 3      | #462                   |
| 4      | #463 (blocked by #429) |
| 5      | #464                   |

Reuse #429 / #450 / #453 — do not file duplicates.

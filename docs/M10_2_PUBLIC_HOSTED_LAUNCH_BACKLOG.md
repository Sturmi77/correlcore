# M10.2 Backlog — Public Hosted Launch

Last updated: 2026-07-19  
**Plan:** [`M10_2_PUBLIC_HOSTED_LAUNCH_PLAN.md`](M10_2_PUBLIC_HOSTED_LAUNCH_PLAN.md)  
**Status:** [`M10_2_PUBLIC_HOSTED_LAUNCH_STATUS.md`](M10_2_PUBLIC_HOSTED_LAUNCH_STATUS.md)  
**Combined cutover:** [`runbooks/hosted-cutover.md`](runbooks/hosted-cutover.md)

Single backlog for remaining Hosted-launch work. Do not duplicate these items into
ad-hoc checklists elsewhere — update this file + STATUS when items move.

**Cutover policy:** Prep Sprint 1 + Sprint 2 offline, then flip DNS/ENV **once**
(see combined runbook). Avoid public web without working SMTP if possible.

## Legend

| Tag       | Meaning                                              |
| --------- | ---------------------------------------------------- |
| `repo`    | Can ship as PR / docs / code in git                  |
| `ops`     | Maintainer on NAS / DNS / registrar / GitHub secrets |
| `blocked` | Waiting on another issue or external asset           |

---

## Sprint 1 — DNS + Nginx (in progress)

**Issue:** #460 · **Runbook:** [`runbooks/hosted-nginx-edge.md`](runbooks/hosted-nginx-edge.md)

| ID    | Item                                                          | Tag    | Notes                                      |
| ----- | ------------------------------------------------------------- | ------ | ------------------------------------------ |
| S1-R1 | Hosted Nginx edge runbook + ENV/smoke                         | `repo` | **Done** (this PR)                         |
| S1-R2 | Roadmap/STATUS/backlog wiring for Sprint 1                    | `repo` | **Done** (this PR)                         |
| S1-O1 | Confirm NAS compose variant; web on `127.0.0.1`               | `ops`  | Baseline inventory                         |
| S1-O2 | Apply Hosted ENV (`FRONTEND_BASE_URL`, CORS, `COOKIE_SECURE`) | `ops`  |                                            |
| S1-O3 | Configure Nginx or Synology RP + TLS renew                    | `ops`  | Follow runbook §B                          |
| S1-O4 | Ensure Traefik not bound to 80/443                            | `ops`  |                                            |
| S1-O5 | Router port-forward or tunnel (CGNAT path)                    | `ops`  |                                            |
| S1-O6 | DNS cutover: apex → NAS **or** IONOS proxy/tunnel             | `ops`  | Today apex is IONOS Apache `217.160.0.166` |
| S1-O7 | Public smoke `/` + `/api/v1/health` without VPN               | `ops`  | Exit for Sprint 1                          |

---

## Sprint 2 — SMTP

**Issue:** #461 · **Runbook:** [`runbooks/hosted-smtp.md`](runbooks/hosted-smtp.md)  
**Execute with Sprint 1 live steps via:** [`runbooks/hosted-cutover.md`](runbooks/hosted-cutover.md)

| ID    | Item                                                 | Tag    | Notes                               |
| ----- | ---------------------------------------------------- | ------ | ----------------------------------- |
| S2-R1 | Hosted SMTP runbook + combined cutover runbook       | `repo` | **Done**                            |
| S2-O1 | Choose SMTP relay (prefer **IONOS SMTP**)            | `ops`  | MX/SPF already IONOS — simplest     |
| S2-O2 | SPF / DKIM / DMARC for sending domain                | `ops`  | Prefetch before DNS flip OK         |
| S2-O3 | Hosted `SMTP_*` + `SMTP_FROM=noreply@correlcore.com` | `ops`  | Same window as S1-O2 ENV            |
| S2-O4 | Verify / resend / reset E2E on public origin         | `ops`  | After A flip                        |
| S2-O5 | **Remove Mailpit from Hosted stack**                 | `ops`  | After E2E; quickstart keeps Mailpit |

---

## Sprint 3 — Landing / Legal / domain docs

**Issue:** #462

| ID    | Item                                                  | Tag          | Notes                            |
| ----- | ----------------------------------------------------- | ------------ | -------------------------------- |
| S3-O1 | Deploy/pin web image with desired landing             | `ops`        | Same origin `/`                  |
| S3-O2 | Hosted Impressum/Privacy content truthful             | `ops`/`repo` | Content may need PR              |
| S3-R1 | `security@correlcore.app` → `security@correlcore.com` | `repo`       | SECURITY.md, GO_PUBLIC, incident |
| S3-R2 | Keep INSTALL examples generic                         | `repo`       | No hardcode                      |
| S3-O3 | Parallel marketing landing merges into app `/` only   | `ops`        | No second apex site              |

---

## Sprint 4 — APK on website

**Issue:** #463 · **Blocked by:** #429

| ID    | Item                                        | Tag              | Notes                           |
| ----- | ------------------------------------------- | ---------------- | ------------------------------- |
| S4-O1 | Android signing secrets + first Release APK | `ops` `blocked`  | #429                            |
| S4-R1 | Landing APK download CTA                    | `repo` `blocked` | Only when asset exists (#450)   |
| S4-O2 | Hosted Capacitor `VITE_API_BASE_URL`        | `ops`            | `https://correlcore.com/api/v1` |
| S4-R2 | Selfhost override docs remain               | `repo`           | ANDROID_SIDELOAD                |

---

## Sprint 5 — Closeout / VPS-ready

**Issue:** #464

| ID    | Item                                           | Tag    | Notes                               |
| ----- | ---------------------------------------------- | ------ | ----------------------------------- |
| S5-R1 | `docs/runbooks/nas-to-vps.md`                  | `repo` | Traefik Path A **instead of** Nginx |
| S5-O1 | Full launch smoke (mail + login + legal + APK) | `ops`  |                                     |
| S5-O2 | GitHub milestone M10.2 close / attach issues   | `ops`  | Agent cannot mutate milestones      |
| S5-O3 | Close stale milestone M10 (#7)                 | `ops`  |                                     |

---

## Explicitly out of M10.2 (do not pull in)

| Item                                                                     | Where it lives                                      |
| ------------------------------------------------------------------------ | --------------------------------------------------- |
| Stripe / multi-tenant / Authentik                                        | M12                                                 |
| Play Closed Testing / Data Safety                                        | M11                                                 |
| MinIO / photos                                                           | M13                                                 |
| Compose profile unification / Caddy / external-proxy **compose** profile | M10 deferred compose backlog (not Hosted Nginx ops) |
| Traefik on Hosted NAS in parallel with Nginx                             | **Forbidden** — dual edge                           |

---

## Parallel / reuse (do not re-file)

| Issue | Topic                                               |
| ----- | --------------------------------------------------- |
| #429  | Android signing + first APK                         |
| #450  | APK links in release notes only if asset exists     |
| #453  | Persistent session (“Angemeldet bleiben”)           |
| #459  | Sprint 0 docs (repo done; milestone attach pending) |

# Runbook — Hosted SMTP (`correlcore.com`)

Last updated: 2026-07-19  
**Milestone:** M10.2 Sprint 2  
**Plan:** [`../M10_2_PUBLIC_HOSTED_LAUNCH_PLAN.md`](../M10_2_PUBLIC_HOSTED_LAUNCH_PLAN.md)  
**Issue:** #461  
**Combined cutover:** [`hosted-cutover.md`](hosted-cutover.md)

Operator runbook for **real email** on the Hosted reference instance.
Selfhost eval still enables Mailpit via profile `mailpit` (`COMPOSE_PROFILES`
in the quickstart/dockhand env examples) — do not delete the service from compose.

## Goal

Verify- and password-reset mails leave `@correlcore.com` via a real SMTP
relay. Mailpit is Compose profile `mailpit` and must stay **off** on Hosted.

## Recommendation for correlcore.com

DNS already has (observed 2026-07-19):

| Record  | Value                                   |
| ------- | --------------------------------------- |
| MX      | `mx00.ionos.de` / `mx01.ionos.de`       |
| SPF TXT | `v=spf1 include:_spf-eu.ionos.com ~all` |

**Preferred Hosted path:** send via **IONOS SMTP** for `@correlcore.com`.

Why: SPF already authorizes IONOS; MX already receives `security@` / inbox mail;
fewer DNS edits at cutover. External relays (Resend/Postmark/…) work but need
SPF `include:` updates + their DKIM CNAMEs — do that only if you intentionally
leave IONOS for sending.

---

## A. Provider setup (before cutover window)

### A.1 IONOS SMTP (preferred)

1. In IONOS: create / confirm mailbox or SMTP credentials allowed to send as
   `noreply@correlcore.com` (or a dedicated transactional sender).
2. Note: host (often `smtp.ionos.de`), port **587** (STARTTLS), user, password.
3. Confirm webmail/inbox for `security@correlcore.com` if used in SECURITY.md
   (domain doc sync is Sprint 3 — address can exist earlier).

### A.2 External relay (alternative)

1. Verify domain in provider dashboard.
2. Add provider DKIM CNAMEs / TXT as instructed.
3. Update SPF to include provider **and** keep IONOS if you still receive on MX:
   example shape (exact include from provider docs):

   ```txt
   v=spf1 include:_spf-eu.ionos.com include:spf.example-relay.com ~all
   ```

4. Add DMARC (same as below).

### A.3 DMARC (both paths)

Add TXT on `_dmarc.correlcore.com` (start relaxed):

```txt
v=DMARC1; p=none; rua=mailto:security@correlcore.com; pct=100
```

Tighten to `p=quarantine` after a clean week of mail.

### A.4 DKIM

- IONOS: enable DKIM in mail/DNS panel if not already; publish their TXT/CNAME.
- External: publish provider records. Do not invent keys in git.

---

## B. Hosted app ENV

```env
SMTP_HOST=smtp.ionos.de          # or your relay host
SMTP_PORT=587
SMTP_USER=<smtp-user>
SMTP_PASSWORD=<smtp-password>
SMTP_FROM=noreply@correlcore.com
SMTP_USE_TLS=true                # or leave unset for auto when USER set
FRONTEND_BASE_URL=https://correlcore.com
```

Rules:

- `SMTP_HOST` must **not** be `mailpit` after cutover.
- `FRONTEND_BASE_URL` must be the public HTTPS origin so verify links work.
- Restart `api` (and any worker that sends mail) after ENV change.
- Never commit real passwords.

---

## C. Mailpit (Hosted off by default)

Mailpit is Compose profile `mailpit`, not part of the default stack. Hosted
and any instance with a real relay: do **not** enable that profile.

After verify/reset E2E passes:

1. Confirm `COMPOSE_PROFILES` / Dockhand **Profiles to enable** does not include
   `mailpit`.
2. Redeploy with orphan removal (`docker compose up -d --remove-orphans` or
   Dockhand equivalent) so a leftover `correlcore-mailpit` container is dropped.
3. Confirm `SMTP_HOST` is the relay, not `mailpit`.
4. Selfhost eval still enables Mailpit via `COMPOSE_PROFILES=mailpit` in the
   quickstart/dockhand `.env*.example` files — do not delete the service from
   compose.

---

## D. E2E checks

| Test                 | Expect                                            |
| -------------------- | ------------------------------------------------- |
| Register new address | Mail arrives (not only Mailpit UI)                |
| Click verify link    | Host is `https://correlcore.com/...`              |
| Resend verification  | Second mail arrives                               |
| Password reset       | Reset link works; login with new password         |
| Spam score           | SPF/DKIM pass (mail-tester or provider dashboard) |

From API logs: successful send, no connection errors to `mailpit`.

---

## E. Done when

- [ ] Relay credentials live in Hosted `.env` (not git)
- [ ] SPF/DKIM/DMARC appropriate for chosen relay
- [ ] Verify + reset E2E on public origin
- [ ] Mailpit profile not enabled on Hosted (`SMTP_HOST` ≠ `mailpit`)
- [ ] Selfhost quickstart still documents `COMPOSE_PROFILES=mailpit`

# Runbook — Hosted SMTP (`correlcore.com`)

Last updated: 2026-07-19  
**Milestone:** M10.2 Sprint 2  
**Plan:** [`../M10_2_PUBLIC_HOSTED_LAUNCH_PLAN.md`](../M10_2_PUBLIC_HOSTED_LAUNCH_PLAN.md)  
**Issue:** #461  
**Combined cutover:** [`hosted-cutover.md`](hosted-cutover.md)

Operator runbook for **real email** on the Hosted reference instance.
Selfhost quickstart keeps Mailpit — do not change that path.

## Goal

Verify- and password-reset mails leave `@correlcore.com` via a real SMTP
relay. After E2E green: **Mailpit is removed from the Hosted stack**.

## Recommendation for correlcore.com

DNS already has (observed 2026-07-19):

| Record | Value |
| ------ | ----- |
| MX | `mx00.ionos.de` / `mx01.ionos.de` |
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

## C. Remove Mailpit (Hosted only)

After verify/reset E2E passes:

1. Stop/remove Mailpit service from the Hosted compose project.
2. Unpublish Mailpit ports (8025/1025) if mapped.
3. Confirm no container still named/using `mailpit` as SMTP target.
4. **Do not** change [`docker-compose.quickstart.yml`](../../infra/docker/docker-compose.quickstart.yml)
   defaults — Selfhost/dev keeps Mailpit.

---

## D. E2E checks

| Test | Expect |
| ---- | ------ |
| Register new address | Mail arrives (not only Mailpit UI) |
| Click verify link | Host is `https://correlcore.com/...` |
| Resend verification | Second mail arrives |
| Password reset | Reset link works; login with new password |
| Spam score | SPF/DKIM pass (mail-tester or provider dashboard) |

From API logs: successful send, no connection errors to `mailpit`.

---

## E. Done when

- [ ] Relay credentials live in Hosted `.env` (not git)
- [ ] SPF/DKIM/DMARC appropriate for chosen relay
- [ ] Verify + reset E2E on public origin
- [ ] Mailpit removed from Hosted stack
- [ ] Selfhost quickstart still documents Mailpit

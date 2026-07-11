# CorrelCore — Beta Onboarding (Operator Guide)

Last updated: 2026-07-11 (M9 Sprint 5)

Guide for instance operators onboarding **5–10 external beta testers** without third-party
analytics (no Hotjar, Mixpanel, etc.).

**Related:** [`BETA_CHECKLIST.md`](BETA_CHECKLIST.md) · [`BETA_FEEDBACK_TRIAGE.md`](BETA_FEEDBACK_TRIAGE.md) ·
[`INSTALL.md`](INSTALL.md) · [`../quality/M9_PENTEST.md`](../quality/M9_PENTEST.md)

---

## Prerequisites (operator)

Before inviting testers, confirm:

- [ ] Instance deployed per [`INSTALL.md`](INSTALL.md) (Path A or B)
- [ ] Backup + restore procedure documented ([`M9_BACKUP_RESTORE_TEST.md`](../quality/M9_BACKUP_RESTORE_TEST.md))
- [ ] Internal security assessment PASS ([`M9_PENTEST.md`](../quality/M9_PENTEST.md))
- [ ] External pentest commissioned or explicitly waived for closed alpha (document decision)
- [ ] SMTP works (verification emails reach testers — Mailpit only for lab)
- [ ] `docs/PRIVACY.md` linked in-app (`/privacy`)

---

## Target cohort

| Goal      | Count       | Personas (from [`USER_WORKFLOWS.md`](../frontend/USER_WORKFLOWS.md)) |
| --------- | ----------- | -------------------------------------------------------------------- |
| Core beta | 5–10        | Mix of P1 (Self-Optimizer) and P2 (Health-Aware Recoverer)           |
| Stretch   | +2 waitlist | Replace dropouts within week 1                                       |

**Recruitment channels (no tracking SaaS):**

- Personal network / communities you trust
- GitHub issue template: [`.github/ISSUE_TEMPLATE/beta_tester.md`](../../.github/ISSUE_TEMPLATE/beta_tester.md)
- Email to interested users who contacted you directly

---

## Instance URL & access model

### Recommended: dedicated beta subdomain

```text
https://beta.correlcore.example.com
```

Set in `infra/docker/.env`:

```env
DOMAIN=beta.correlcore.example.com
FRONTEND_BASE_URL=https://beta.correlcore.example.com
CORS_ORIGINS=https://beta.correlcore.example.com
```

### Tailnet / homelab (Path B)

Share the Tailscale or LAN URL from [`infra/dockhand/README.md`](../../infra/dockhand/README.md).
Document that testers need Tailscale access — not suitable for more than 2–3 trusted testers.

---

## Test accounts

Choose **one** model:

### Model A — Self-registration (preferred)

1. Send testers the instance URL only.
2. They register with their own email (`/auth/register`).
3. They verify via SMTP (ensure relay works).
4. Operator does **not** know passwords.

**Pros:** Realistic auth flow, no shared credentials.  
**Cons:** SMTP must be reliable; unverified accounts auto-delete after `UNVERIFIED_CLEANUP_DAYS` (default 7).

### Model B — Operator-provisioned accounts

For testers without reliable email or for controlled demos:

```bash
# 1. Tester registers (or operator registers on their behalf)
# 2. Verify email via Mailpit UI (lab) or manual DB flag — production: use real SMTP

# Optional: pre-seed entries for demo — only with tester consent
```

Share credentials via **password manager secure send** or Signal — never in plain GitHub issues.

| Account     | Email | Purpose                 | Week-1 status |
| ----------- | ----- | ----------------------- | ------------- |
| _tester-01_ | _@_   | P1 daily tracking       | invited       |
| _tester-02_ | _@_   | P2 privacy/export focus | invited       |
| …           |       |                         |               |

> **Do not commit** this table with real emails to the repository. Keep the live roster in your
> operator wiki or encrypted doc; this template is structural only.

---

## Onboarding email template

Subject: `CorrelCore Beta — your access`

```text
Hi <name>,

thanks for joining the CorrelCore closed beta (pre-release, selfhosted mood & habit tracker).

Instance URL: https://beta.<your-domain>
Privacy policy: https://beta.<your-domain>/privacy

Please:
1. Register and verify your email.
2. Complete week-1 checklist: <link to BETA_CHECKLIST.md or hosted copy>
3. Send feedback via GitHub issue (preferred) or reply to this email.

Feedback template: <link to BETA_FEEDBACK_TRIAGE.md §Reporter template>
Severity guide: blocker = cannot use core flow; major = misleading/wrong; minor = UI/copy.

This is pre-release software. Export your data anytime in Settings → Export (ZIP).
Account deletion is self-service in Settings → Privacy.

Thanks,
<operator name>
```

---

## Tester week-1 package

Share these links (in email or pinned GitHub discussion):

| Document                                             | Purpose                         |
| ---------------------------------------------------- | ------------------------------- |
| [`BETA_CHECKLIST.md`](BETA_CHECKLIST.md)             | Flows to complete in week 1     |
| [`USER_WORKFLOWS.md`](../frontend/USER_WORKFLOWS.md) | Detailed workflow reference     |
| [`PRIVACY.md`](../PRIVACY.md)                        | Legal / data processing summary |

**Symptom analytics focus (week 2):** ask testers with ≥15 entries to review Insights → Symptoms tab
and co-occurrence heatmap; see [`M9_SYMPTOM_ANALYTICS_BETA_REVIEW.md`](../quality/M9_SYMPTOM_ANALYTICS_BETA_REVIEW.md).

---

## Feedback channels

| Channel                | When to use                                     | Template                                                                                   |
| ---------------------- | ----------------------------------------------- | ------------------------------------------------------------------------------------------ |
| **GitHub issue**       | Default; structured, public to repo maintainers | [`.github/ISSUE_TEMPLATE/beta_feedback.md`](../../.github/ISSUE_TEMPLATE/beta_feedback.md) |
| **Email**              | Testers without GitHub                          | Same fields as issue template                                                              |
| **Registration issue** | Initial interest only                           | [`beta_tester.md`](../../.github/ISSUE_TEMPLATE/beta_feedback.md)                          |

Apply label `beta` to all feedback issues. Triage per [`BETA_FEEDBACK_TRIAGE.md`](BETA_FEEDBACK_TRIAGE.md).

**Forbidden for M9:** Hotjar, Mixpanel, Google Analytics, Intercom, or any third-party session replay.

---

## Beta timeline (suggested)

| Week | Operator                                   | Testers                            |
| ---- | ------------------------------------------ | ---------------------------------- |
| 0    | Deploy, pentest gate, send invites         | —                                  |
| 1    | Daily triage; fix P0 within 48h            | Complete BETA_CHECKLIST core flows |
| 2    | Round-1 summary; symptom analytics prompts | Optional PWA + symptom review      |
| 3    | Close beta round; backlog → M10            | Final export/delete if leaving     |

**Exit criterion (Sprint 5):** ≥5 active testers, ≥1 complete feedback round triaged.

---

## Operator roster (fill locally — do not commit PII)

| #    | Codename | Persona | Platform | Invited | Active W1 | Feedback filed |
| ---- | -------- | ------- | -------- | ------- | --------- | -------------- |
| 1    |          | P1      |          | ☐       | ☐         | ☐              |
| 2    |          | P2      |          | ☐       | ☐         | ☐              |
| 3    |          | P1      |          | ☐       | ☐         | ☐              |
| 4    |          | P2      |          | ☐       | ☐         | ☐              |
| 5    |          | P1      |          | ☐       | ☐         | ☐              |
| 6–10 |          |         |          | ☐       | ☐         | ☐              |

---

## Checklist — ready to invite

- [ ] Instance URL live and TLS valid
- [ ] Registration + email verification tested end-to-end
- [ ] Privacy policy reachable
- [ ] Export + delete tested (see E2E `gdpr-self-service.spec.ts` for expected behaviour)
- [ ] Feedback issue template enabled
- [ ] Triage owner assigned ([`BETA_FEEDBACK_TRIAGE.md`](BETA_FEEDBACK_TRIAGE.md))
- [ ] Roster started (5+ slots)

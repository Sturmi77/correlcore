# CorrelCore — Beta Tester Checklist

Last updated: 2026-07-11 (M9 Sprint 5)

Use this checklist when onboarding **5–10 external beta testers** (M9 Sprint 5).
Instance operators share the checklist link together with the instance URL and test account
credentials.

**Operator onboarding:** [`BETA_ONBOARDING.md`](BETA_ONBOARDING.md)  
**Operator setup:** [`INSTALL.md`](INSTALL.md)  
**Feedback triage:** [`BETA_FEEDBACK_TRIAGE.md`](BETA_FEEDBACK_TRIAGE.md)  
**User workflows:** [`../frontend/USER_WORKFLOWS.md`](../frontend/USER_WORKFLOWS.md)  
**Privacy policy:** [`../PRIVACY.md`](../PRIVACY.md)

---

## Before you start

- [ ] You received the beta instance URL (`https://…`)
- [ ] You received login credentials or an invite to register
- [ ] You read the [privacy policy](../PRIVACY.md) (German/English summary in-app at `/privacy`)
- [ ] You understand this is **pre-release** software — export your data anytime via Settings

---

## Core flows (please complete in week 1)

| #   | Workflow                    | Steps                                                   | Pass? | Notes |
| --- | --------------------------- | ------------------------------------------------------- | ----- | ----- |
| 1   | **Register & verify**       | Register → open verification email → log in             | ☐     |       |
| 2   | **First entry**             | Home → add mood entry (≤ 60 s)                          | ☐     |       |
| 3   | **Second day entry**        | Add another entry on a different day                    | ☐     |       |
| 4   | **Trends**                  | Open Trends → view mood time series                     | ☐     |       |
| 5   | **Insights**                | Open Insights → read at least one card                  | ☐     |       |
| 6   | **Habits** (if enabled)     | Configure a habit in Settings → check Trends Habits tab | ☐     |       |
| 7   | **Settings / privacy**      | Open Settings → Privacy → open policy link              | ☐     |       |
| 8   | **Data export**             | Settings → Export → download ZIP                        | ☐     |       |
| 9   | **Analytics opt-out**       | Settings → disable analytics → save                     | ☐     |       |
| 10  | **Mobile or narrow window** | Repeat entry flow at ≤ 768 px width                     | ☐     |       |

Detailed step references: [`USER_WORKFLOWS.md`](../frontend/USER_WORKFLOWS.md) (W1–W10).

---

## Optional (week 2)

- [ ] Install as PWA (mobile browser → Add to Home Screen)
- [ ] Enable offline sync in Settings (if offered) and add entry offline
- [ ] Review symptom analytics (if enough data collected)

---

## Feedback template

Please send feedback via **GitHub issue** (preferred) or email to the operator.

Template: [`.github/ISSUE_TEMPLATE/beta_feedback.md`](../../.github/ISSUE_TEMPLATE/beta_feedback.md)  
Triage guide: [`BETA_FEEDBACK_TRIAGE.md`](BETA_FEEDBACK_TRIAGE.md)

```markdown
**Instance URL:** …
**Device / browser:** …
**Workflow:** (e.g. W3 daily entry)
**Expected:** …
**Actual:** …
**Severity:** blocker | major | minor | suggestion
**Screenshot:** (optional)
```

### Severity guide

| Level          | Examples                                                          |
| -------------- | ----------------------------------------------------------------- |
| **Blocker**    | Cannot log in, data loss, export fails                            |
| **Major**      | Core workflow broken, misleading insight, privacy control missing |
| **Minor**      | UI glitch, copy issue, slow load                                  |
| **Suggestion** | UX improvement, feature idea → may defer to M10                   |

---

## Operator triage (internal)

| Priority     | Action                                        |
| ------------ | --------------------------------------------- |
| P0 / blocker | Fix in M9 or pause beta onboarding            |
| P1 / major   | Fix in M9 if scoped; else document workaround |
| P2+          | Backlog → M10 / M9+                           |

Track feedback in GitHub issues with label `beta` (operator-defined).

---

## GDPR reminders for testers

- Do not enter real third-party health information about other people.
- Use the ZIP export before account deletion if you want a local copy.
- Account deletion is self-service in Settings (Art. 17).

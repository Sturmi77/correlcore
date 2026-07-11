# User Guide

How to use CorrelCore day to day. Based on the
[workflow catalog](https://github.com/Sturmi77/correlcore/blob/main/docs/frontend/USER_WORKFLOWS.md)
in the repository.

## Navigation

CorrelCore uses four main tabs: **Home**, **Insights**, **Trends**, and **Settings**.
Daily entry opens from Home via the entry sheet (not a separate tab).

---

## Getting started

### Create an account

1. Open **Register** and enter email, password, and optional display name.
2. Check your email for a verification link (Mailpit in homelab eval; real SMTP in production).
3. After verification, sign in. Unverified accounts have limited API access.

### First-time onboarding

New users see a guided onboarding flow: profile questions, first entry prompt, and
maturity-aware empty states until enough data exists for insights.

---

## Daily tracking (W3)

**Goal:** Log mood, energy, stress, tags, symptoms, and optional notes in ~60 seconds.

1. From **Home**, tap **Add entry** (or open `/entries/new`).
2. Set mood / energy / stress sliders.
3. Select tags and symptoms; add a note if needed.
4. Save — the entry appears on Home and in Trends.

**Tips:**

- Tags can be curated defaults or custom labels you create in Settings.
- Notes are encrypted at rest when `ENCRYPTION_KEY` is configured on the server.
- Backdated entries are supported via the date picker.

---

## Insights (W5–W6)

**Goal:** Understand correlations between habits, tags, and wellbeing.

| Maturity phase | What you see |
| -------------- | ------------ |
| Collecting | Encouragement to keep logging; minimal insight cards |
| Early patterns | First correlation statements with confidence tiers |
| Established | Fuller insight feed, weekday patterns, habit correlations |

Insights generate in the background when the **worker** profile/service is enabled on your instance.

Open **Insights** tab for the full feed; Home shows a preview of top insights.

!!! note "Disclaimer"
    Insights show statistical correlations, not medical causation. See the in-app
    correlation disclaimer.

---

## Trends & habits (W6–W7)

**Trends** tab: mood time series, tag heatmaps, habit adherence (when habits are configured).

Configure habits in **Settings → Tags & habits**: build or reduce goals tied to tags.

---

## Privacy & data export (W9)

**Settings → Privacy & data:**

- Toggle analytics / insight generation (`analytics_enabled`)
- Export your data (JSON/ZIP — GDPR Art. 20)
- Delete your account (irreversible)

Selfhost operators are data controllers; see [Privacy notice](../privacy/index.md).

---

## PWA & offline (W10)

Install CorrelCore as a PWA from the browser install prompt. Offline sync (Dexie.js)
is available for verified users when enabled on the instance — entries sync on reconnect.

---

## Support

- **Instance issues:** contact your selfhost operator.
- **Software bugs:** [GitHub Issues](https://github.com/Sturmi77/correlcore/issues)
- **Security:** [SECURITY.md](https://github.com/Sturmi77/correlcore/blob/main/SECURITY.md)

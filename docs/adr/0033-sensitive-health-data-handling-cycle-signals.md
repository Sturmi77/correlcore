# ADR-0033: Sensitive Health Data Handling for Cycle-related Signals

Date: 2026-05-29

## Status

Accepted

## Context

Cycle-related data — bleeding levels, cycle phases, pain scores, and
cycle events — qualifies as **health data (Article 9 GDPR / special
category data)**. CorrelCore already applies Privacy-by-Design principles
(see `docs/DSGVO.md`) and encryption at rest (ADR-0005). However, those
documents do not define cycle-specific rules for logging, analytics, export,
deletion, and Play Store / App Store health data declarations.

This ADR closes that gap before any cycle data is written to production.

## Decision

### 1. Data classification

The following fields are classified as **Sensitive Health Data (SHD)**
and receive stricter handling than standard entry fields:

```
cycle_day, cycle_bleeding_level, cycle_phase_reported,
cycle_phase_inferred, cycle_events, and all symptom codes
in the `cycle` category.
```

Standard entry fields (mood score, energy, tags like "sport" or "homeoffice")
remain classified as **Personal Lifestyle Data (PLD)** with the existing rules.

### 2. Storage

- SHD fields are stored in the same `day_entries` table as PLD fields.
  No separate table is created to avoid JOIN complexity and sync issues.
- The column-level encryption applied to `day_entries` (ADR-0005) covers
  SHD fields implicitly. No additional column-level encryption is added
  at this stage (consistent with ADR-0005 scope decision).
- Row-Level Security (RLS) on PostgreSQL already isolates data per user;
  no additional RLS policy is needed for SHD columns specifically.

### 3. Logging and analytics

- **SHD field values are never logged** in application logs, error trackers
  (Sentry, etc.), or structured log outputs — not even at DEBUG level.
- Log sanitisation: any log formatter touching a `DayEntry` object must
  redact the fields listed in §1 above. A shared `sanitise_entry_for_log()`
  utility is added to `packages/shared-types`.
- Internal analytics (e.g., anonymous aggregate usage metrics) must not
  include SHD fields. Counters and rates ("N users have cycle tracking
  enabled") are permissible without value data.

### 4. API and transport

- SHD fields are always transmitted over HTTPS/TLS (already enforced).
- The API never returns SHD fields in list endpoints that are accessible
  without per-user authentication (e.g., public sharing links, if ever
  introduced, must strip SHD fields).
- SHD fields are excluded from any future "public profile" or social
  sharing feature by default; explicit user action is required to include them.

### 5. Export and portability

- The data export (CSV / JSON) includes SHD fields **by default** because
  data portability is a GDPR right.
- The export UI must clearly label the SHD section: "This export includes
  sensitive health data (cycle tracking). Store it securely."
- A future "export without health data" option may be added in M8+.

### 6. Deletion

- Account deletion already cascades to all `day_entries` (existing behaviour).
- A new **Selective SHD deletion** endpoint is added in M4:
  `DELETE /api/v1/entries/cycle-data` — deletes all SHD column values for
  the authenticated user while preserving the base entry record (mood,
  energy, tags). This allows users to stop cycle tracking without losing
  all historical data.

### 7. Consent and transparency

- Cycle tracking is opt-in via the onboarding toggle (ADR-0034).
- Enabling cycle tracking triggers a one-time in-app notice:
  > "Cycle tracking records health-related data. This data is stored only
  > on your server / device and is never shared with third parties."
- This notice is not a modal blocking the flow; it is an inline card shown
  once, dismissible, with a "Learn more" link to the privacy documentation.

### 8. Play Store / App Store health data declarations

- When submitting to Google Play (M11), the Data Safety form must declare:
  - **Health and fitness > Other health info** (cycle data): collected,
    not shared, encrypted, user-deletable.
- Apple App Store (future): Nutrition/Health category requires equivalent
  privacy label entries.
- These declarations must be reviewed before each store submission and
  must stay synchronised with this ADR.

### 9. Medical disclaimer

A persistent disclaimer is shown in the cycle tracking UI:

> "CorrelCore shows patterns in your own data. It does not provide medical
> advice, diagnoses, or fertility guidance. Consult a healthcare provider
> for medical questions."

This disclaimer applies to all insight cards referencing cycle data.

## Considered Alternatives

| Alternative | Reason rejected |
|---|---|
| Separate encrypted table for SHD | Sync complexity, JOIN overhead, migration risk — benefits do not outweigh costs at current scale |
| Field-level encryption for SHD columns only | High implementation cost; ADR-0005 already encrypts the full table at rest |
| Opt-out instead of opt-in for cycle tracking | Contradicts Privacy-by-Design; health data must be explicitly consented |

## Consequences

- A `sanitise_entry_for_log()` utility must be implemented before the first
  SHD field reaches production.
- The `DELETE /api/v1/entries/cycle-data` endpoint is an M4 deliverable.
- The Play Store data safety form must be updated before M11 submission.
- Future features that expose entry data (sharing, public API, webhooks)
  must consult this ADR and redact SHD fields by default.

# A12 evidence files

Commit only redacted evidence for the exact release candidate. Prefer stable CI, issue
or deployment URLs when the source already retains immutable logs.

Filename: `<gate-id>-<yyyy-mm-dd>.md`.

Each evidence file contains:

```markdown
# <Gate> — <UTC date>

- Git SHA: <40 characters>
- API image: sha256:<64 hex>
- Web image: sha256:<64 hex>
- Worker image: sha256:<64 hex>
- Environment/deployment ID: <non-secret ID>
- Executor role: <role; personal name only with consent>
- Result: passed | failed

## Procedure

<steps actually performed>

## Observations

<redacted results, versions, device/OS matrix or command output>

## Findings and follow-up

<issue URLs or “none”>

## Sign-off

- Role:
- Date:
- Result:
```

Never include tokens, cookies, secrets, database URLs, raw health data, interview names,
private e-mail addresses, device identifiers or unredacted screenshots.

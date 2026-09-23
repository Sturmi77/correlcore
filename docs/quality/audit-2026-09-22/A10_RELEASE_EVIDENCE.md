# A10 release evidence

Issue [#984](https://github.com/Sturmi77/correlcore/issues/984) is implemented
by the manually dispatched **Audit A10 - Release evidence** workflow. It is a
release-candidate gate, not a substitute for ordinary pull-request CI.

## Immutable candidate

The dispatcher supplies:

- a full 40-character commit SHA;
- the API image as a registry reference ending in `@sha256:<digest>`;
- the web image in the same immutable form;
- the URL of an isolated, proxy-fronted staging deployment.

The workflow checks out the exact SHA. Staging must expose that SHA and both
image references through `GET /api/v1/instance`. Compose deployments pass the
API reference as `IMAGE_DIGEST` and the web reference as `WEB_IMAGE_DIGEST`.
A tag such as `latest` is not accepted.

## Required `audit-rc` environment

Create a protected GitHub environment named `audit-rc` with four secrets:

| Secret                | Purpose                                                                      |
| --------------------- | ---------------------------------------------------------------------------- |
| `A10_USER_A_EMAIL`    | Verified seeded release-candidate user with entries and at least one insight |
| `A10_USER_A_PASSWORD` | Password for user A                                                          |
| `A10_USER_B_EMAIL`    | Second verified seeded user with separate entries                            |
| `A10_USER_B_PASSWORD` | Password for user B                                                          |

The two accounts belong only to the isolated release-candidate environment.
The smoke test performs a lossless update of an existing entry and creates,
then removes, an insight dismissal. It rejects shared entry IDs and verifies
that user B receives 404 for user A's entry.

## Gates

The workflow does not create a final manifest unless all seven gates pass:

1. **Linux CI** — frozen installs, lint, formatting, types, full unit tests,
   production build, and 85% coverage for auth, scoped-DEK and insight compute.
2. **Windows/timezone** — timezone and export regressions on `windows-latest`.
3. **Migration** — fresh upgrade, downgrade/upgrade round trip, every test
   module marked `integration`, and zero skipped integration cases.
4. **Real API E2E** — two real logins, capture, owner isolation, sync, 30/90
   day analysis windows, event windows, verification/compare, dismissal, and
   JSON export against the staging API.
5. **Security/dependencies** — fresh pnpm and pip advisories, exact-image
   Trivy scans that fail on HIGH/CRITICAL, and authenticated ZAP through the
   representative proxy. Temporary dependency exceptions live in
   `A10_SECURITY_EXCEPTIONS.json`; CI rejects missing owner, reason, scope, or
   an expired date.
6. **Performance** — bounded analytics/worker tests and a 150 KiB gzip ceiling
   for every emitted JavaScript asset.
7. **Visual/accessibility** — production-server Playwright smoke, serious and
   critical axe checks, print media at 390 px, mobile viewports, and the GDPR
   download flow.

Vitest uses at most two workers in CI and Playwright uses one. Worker start
failures fail the job. There is no blanket retry or ignore path.

## Evidence and release decision

The final `a10-release-evidence-<sha>` artifact contains a JSON manifest. The
validator rejects missing gates, pending status, mutable image tags, mismatched
SHAs or digests, and non-HTTPS evidence links. Artifacts are retained for 90
days.

The workflow run URL and final manifest are the linked approval package.
Issue #984 remains open until a complete run for the intended release
candidate exists and any human release sign-off is recorded.

# Changelog

Alle signifikanten Änderungen werden hier dokumentiert.
Format basiert auf [Keep a Changelog](https://keepachangelog.com/).
Versionierung nach [Semantic Versioning](https://semver.org/).

---

## [Unreleased]

### Docs

- **Reverse-proxy edges now document the required large proxy buffers** — the
  SvelteKit web container sends big response headers (adapter-node
  `Link: rel=preload`), so an edge with the default `proxy_buffer_size` (4k/8k)
  returns `502 Bad Gateway` (`upstream sent too big header`) even when the
  forward, cert and headers are all correct. The shipped
  `infra/nginx/correlcore.com.conf` now sets `proxy_buffer_size 32k` etc., and
  `infra/nginx/README.md`, `docs/selfhost/INSTALL.md`, ADR-0040, the
  hosted-nginx-edge / hosted-topology-options / hosted-cutover runbooks gained
  the requirement plus a **Nginx Proxy Manager (NPM)** note (paste the buffer
  lines into the Advanced field — never a full `server {}` block).

### Fixed

- **Onboarding first-entry save no longer aborts when finalize fails under a
  stale reachable flag (P1b residual)** — `#536` deferred `completeOnboarding`
  when `serverReachable === false`, but a stale `true`/`null` plus a failed
  finalize (network blip / 5xx) still threw out of `resolveOnboardingTags` and
  aborted `persist()` before `saveEntryOffline`, losing the first onboarding
  entry. With offline sync enabled, finalize errors are now caught and
  deferred; the Dexie write proceeds and the finalize is retried when API
  reachability recovers (a `connectivity` watcher, not only `window.online`),
  so the deferred onboarding tags are no longer lost when the user makes no
  further edit. A successful finalize whose follow-up catalogue `refreshTags`
  fails now still applies the created tag associations (the `try` no longer
  swallows that result).
- **Offline sync no longer wedges the outbox on deleted tag/symptom IDs** —
  entry push still called `assign_tags_to_entry` /
  `assign_symptoms_to_entry` with every client association ID. After a custom
  tag or symptom was deleted (cascade clears server links; Dexie is not
  pruned), those errors were uncaught → HTTP 500 and the web client never
  acked the batch, blocking newer pending changes. Sync now drops
  unknown/deleted (and newly-hidden) association IDs before assign; residual
  assign errors map to 400.
- **EntryForm unresolved-relation writeback no longer drops chips picked
  during re-resolve** — after #536, `preserveUnresolvedRelations` wrote back
  `server ∪ dirty-snap` only. TagPicker/SymptomChecker stay enabled while
  autosave re-fetches, so a tag/symptom chosen in that window was clobbered
  and never reached the replace-set save. Merge now includes live selections;
  a mid-resolve entry switch aborts the save instead of writing onto the wrong
  row.
- **Re-saving an entry after hiding a linked tag no longer 422s** — hide keeps
  historical `entry_tags` (M3.5), and `list_tags_for_entry` still returns those
  IDs so the client can round-trip them, but `assign_tags_to_entry` rejected any
  `is_hidden` ID. Every mood/energy edit then failed; with offline sync the
  uncaught error aborted the whole push batch so newer pending rows never
  acked. Already-linked hidden tags are now allowed; new hidden assignments
  remain rejected.
- **Offline EntryForm no longer writes stale tags/symptoms into IndexedDB
  (R-05)** — when `listTagsForEntry` / `listSymptomsForEntry` failed after a
  successful entry list, the offline load path hydrated Dexie with the previous
  form's selections. Hydration now runs only when both relation fetches
  succeed, and failed fetches clear the in-form selections first.
- **Onboarding tag suggestions are applied while online even if offline sync
  is enabled (R-04)** — `resolveOnboardingTags` previously returned early on
  `canUseOfflineSync()` alone, so first-entry suggestion chips never became
  tags. It now skips only when the device is actually offline.
- **Overlapping insight regeneration no longer leaves stale or duplicate
  rows** — `generate_and_store_insights` delete-then-insert had no per-user
  lock, so concurrent `POST /insights/regenerate`, post-batch import hooks,
  and the analytics worker could interleave: a slower writer that loaded
  earlier data could wipe fresher committed insights, or two empty-table
  writers could both insert. Take `pg_advisory_xact_lock` for the user
  before loading inputs so waiters re-read after the winner commits.
- **Web login Set-Cookie no longer dropped by the SvelteKit `/api` proxy** —
  PR #468 moved upstream auth cookies onto `event.cookies` and stripped them
  from the proxied `Response`. That handle never calls `resolve()`, so
  SvelteKit ignores the cookie jar (sveltejs/kit#7611): `POST /auth/login`
  returned 200 with no browser cookie, then `GET /auth/me` failed. Restore
  multi-value `Set-Cookie` forwarding on the Response (ADR-0011).
- **Landing-page login no longer mislabels a dropped session cookie as
  "wrong password"** (ADR-0040) — the web login is a two-step flow (`POST
/auth/login` then `GET /auth/me`). When the HttpOnly session cookie did not
  persist (edge/proxy misconfig), the store threw a bare `401` that the login
  page rendered as "E-Mail oder Passwort ist falsch", sending every recurrence
  down a dead-end credential hunt. It now throws a distinct
  `SessionPersistenceError` mapped to a cookie/HTTPS-specific message
  (`error.session_not_persisted`, de/en). The Capacitor/APK Bearer path is
  unaffected.

### Added

- **Canonical hosted Nginx edge config** at `infra/nginx/correlcore.com.conf`
  (ADR-0040) — a single self-contained one-rule passthrough server block (no
  `include` snippet, so it also deploys on a standalone edge machine or a
  Synology custom config). Proxy params are defined once at `server{}` level and
  inherited by both `location /` and `location /api/v1/auth/`, so auth requests
  can never be proxied differently from the rest of the app (the divergence that
  silently drops the login `Set-Cookie`). Replaces the hand-written example in
  `docs/runbooks/hosted-nginx-edge.md`.
- **`scripts/verify-auth-cookie.sh`** — deploy-time self-test that confirms the
  login cookie survives the edge (login 200 + `Set-Cookie` present + `/auth/me` 200) and pinpoints the failing hop otherwise. Wired into the hosted-edge
  runbook "Done when" checklist.
- **ADR-0040** — Self-Host-Auth-Edge decision: keep secure cookie auth by
  default, make the edge contract trivial and self-verifying, and document an
  opt-in Bearer fallback for genuinely cross-origin self-host topologies.

---

## [1.1.1] — 2026-07-24

Patch on the public line: insight previews and install polish, an ops
monitoring overlay, and two date fixes. No database migration; upgrade is a
plain image pull.

### Added

- **Tag-group clustering on the co-occurrence heatmap** (#489) — in clustered
  mode the Insights tag heatmap now orders axes by server `cluster_id` with a
  gap between clusters, and "focus cluster" chips filter to one group. Falls
  back to the previous hierarchical order when clusters are unavailable.
- **Insight previews on the landing** (#510) — the marketing page now shows the
  Insight Matrix, an Insight Card, and the tag heatmap as static product shots.
- **Android download section on the landing** (#463) — a prominent "Download
  APK" CTA (latest signed GitHub Release) plus an Obtainium auto-update link and
  a SHA256 verification note.
- **Ops overlay for autostart hardening + availability monitoring** (#491) —
  opt-in `infra/docker/docker-compose.ops.yml` with **autoheal** (restarts
  containers Docker marks `unhealthy`, which base `restart: unless-stopped` does
  not) and **Uptime Kuma** (selfhosted monitor + email/ntfy alerts on
  `/api/v1/health/ready`). `docs/selfhost/INSTALL.md` gains an
  "Autostart & monitoring" section. Compose audit confirmed every long-lived
  service already carries `restart: unless-stopped`.

### Fixed

- **Entry sheet uses the local calendar day** (#507, #508) — the default entry
  date and the "today" comparison now follow the device's local day instead of
  the UTC server day, so an evening entry in a positive-UTC-offset zone no
  longer lands on the wrong date.
- **MinIO secret passed to migrate/api/worker** (#511).

### Internal

- CI now gates Android `NewApi` lint on debug and signed release builds (#506),
  catching `java.time` usage that would crash on API 23–25.

---

## [1.1.0] — 2026-07-23

First minor bump on the public line. Carries two new features and a database
migration, which is why this is not a `1.0.x` patch: pinning by semver, a patch
should not add API fields or require a migration.

### Added

- **Weekday top signal on Home** (#487) — the weekday strip now names the tag,
  symptom or work context that occurs most often on each day.
  `GET /dashboard/summary` gained an optional
  `weekday_summary[].top_signal { kind, id, label, count, share }`. Suppressed
  below 2 occurrences or a 30% share so a single entry cannot look typical.
  Copy-on-write tag overrides are collapsed onto their canonical slug first, so
  a renamed tag and its default twin no longer split the count.
- **Build vs reduce habits are visually distinct** (#490) — `build` keeps the
  solid meter, `reduce` gets a hatched, outlined one at the same value, plus
  `+`/`−` glyphs and separate "Building" / "Reducing" sections. The value is
  deliberately _not_ inverted: adherence is already normalised so that fuller
  always means better.

### Fixed

- **Widget "today" follows the device timezone** (#445) — entries are stored
  against a local date, so a UTC-derived day made the widget disagree with the
  app for anyone whose local day differs from UTC.
- **Widget polls only while a widget is installed** (#446) — app start used to
  schedule the 15-minute worker unconditionally, and nothing cancelled it when
  the last widget was removed.
- **Widget "+ Add entry" opens the entry sheet** (#447, #496) — the custom
  scheme was declared but never bridged into the WebView. Cold start, warm
  resume and the signed-out path are handled.
- **Brand mark left the nav landmark** (#448) — it was a second link to `/`,
  putting five links in a landmark contracted to four.
- **APK links only when the asset exists** (#450) — every `v*` tag published a
  download link, including tags built without signing secrets, where it 404s.
- **Release backfill builds from the target tag** (#451) — `attach_to_tag` used
  the input only for naming, so newer source could be attached to an older tag.
- **No duplicate tags in heatmaps** (#485) and **login redirect plus offline
  boot on server outage** (#486).

### Changed

- **Weekly digest is now opt-in for existing installs too** (#449) — migration
  `031` resets every `user_preferences.digest_enabled = true` row that carried
  the pre-#398 default. Migration 026 created the column as
  `NOT NULL DEFAULT true`, so those rows were never an explicit opt-in.
  **Upgrading operators:** anyone who wants the weekly digest re-enables it
  under **Settings → Analysis**. No digest was ever delivered from those rows —
  the worker only runs behind `COMPOSE_PROFILES=digest`.
- Web storage guardrail in CI (#453) — `pnpm check:no-token-storage` fails the
  build if auth material ever reaches `localStorage` / `sessionStorage`.

### Upgrade notes

- Run `alembic upgrade head`: migration `031` must run as a superuser or
  `BYPASSRLS` role, since `user_preferences` enforces `FORCE ROW LEVEL
SECURITY`. It fails loudly rather than silently resetting nothing.
- Android `versionCode` moves to `1001000`.

---

## [1.0.8] — 2026-07-21

Tester / selfhost patch on the public `1.0.x` line. Prefer this tag for GHCR
pins and Android sideload APK installs.

### Added

- **Trends Compare shared-axis zoom (bird’s-eye)** — stages `1/3/7/14/28` days
  per cell (default 7), synced timeline + Comparison Heatmap, `+/-` controls,
  multi-day tap zoom-in, coverage/partial tooltips, strip-mode gate, marker
  dedupe (#472, CAZ-0…3 via #473 / #477 / #479 / #480 / #481 / #483).
- **Split-Hero-Bento public landing** redesign from design handoff (#478).

### Changed

- M10.2 hosted topology: Topology H end-state traffic diagram (#474).
- Compare / landing docs and QA checklist for axis zoom
  (`docs/frontend/COMPARE_AXIS_ZOOM_*.md`,
  `docs/quality/COMPARE_AXIS_ZOOM_CAZ3_QA.md`).

### Fixed

- P1/P2 review findings across auth, pull-to-refresh, and Android (#476).

---

## [1.0.7] — 2026-07-20

Tester / selfhost patch on the public `1.0.x` line. Prefer this tag for GHCR
pins and Android sideload APK installs.

### Added

- **Pull-to-refresh** on authenticated screens (Home, Insights, Trends, Settings
  and related subpages) (#469).
- Rudimentary **public landing** with login CTA and APK download link (#471).

### Changed

- Trends compare timeline defaults to **smoothed** (week uses a 3-day window;
  longer ranges keep the 7-day SMA). Explicit Raw preference is still
  respected (#470).
- Heatmap under the Trends timeline keeps the shared date axis when pruning
  sparse rows (mobile alignment) (#470).
- M10.2 hosted-launch docs: plan/backlog, Nginx/SMTP runbooks, topology
  options (#458, #465, #466, #467).

### Fixed

- HTTP Homelab auth: Secure-cookie defaults and session refresh so selfhost
  over plain HTTP no longer fails with „Could not validate credentials“
  (#468).

---

## [1.0.6] — 2026-07-19

Tester-focused patch on the public selfhost / Android sideload line. Prefer this
tag for GHCR pins and sideload APK installs.

### Added

- **Persistent session („Angemeldet bleiben“)** — Issue #453 / ADR-0006 amendment:
  login checkbox (default on); Web/PWA session vs persistent HttpOnly cookies via
  `remember_me`; Capacitor restores refresh from EncryptedSharedPreferences before
  `hydrate()`. Plan: `docs/features/PERSISTENT_SESSION_PLAN.md`,
  `docs/PERSISTENT_SESSION_SPRINT_PLAN.md`.

### Changed

- README / docs aligned to selfhost **`1.0.x`**: brand logo, archived M0–M10.1,
  design doc v0.15, CHANGELOG sections for patch tags; install pins recommend
  **`v1.0.6`**. See [`docs/releases/RELEASE_1_0_X_DOC_SYNC.md`](docs/releases/RELEASE_1_0_X_DOC_SYNC.md).

### Fixed

- Trends: 401 on `/entries/stats/symptoms` (credential validation) (#444).
- Android Sprint A hardening: backup off, redact URLs, SW cleanup (#443).
- Auth P1: push unregister order, widget refresh, cookie JWT gate (#442).
- UI: CorrelCore logo as Home nav; sticky timeseries legend (#441).

---

## [1.0.5] — 2026-07-18

### Fixed

- Android: gate FCM `PushNotifications.register()` when sideload builds omit
  `google-services.json` (post-login crash); bake optional `PUBLIC_GLITCHTIP_DSN`
  into Capacitor APKs; skip service workers in native shell (#440).

---

## [1.0.4] — 2026-07-18

### Fixed

- Android: allow mixed content so `https://localhost` WebView can call
  `http://` Tailscale / selfhost API bases (#439).

---

## [1.0.3] — 2026-07-18

### Fixed

- Android: Capacitor API reachability (CORS for WebView origin, cleartext for
  selfhost HTTP), status-bar safe area, brand splash hold ≥850ms; shrink launcher
  mark for OEM adaptive-icon masks (#438).

---

## [1.0.2] — 2026-07-18

### Added

- Brand: Claude Design logo mark, boot splash, PWA/Android launcher assets,
  Settings footer + desktop AppNav mark (#437, #436).

### Fixed

- Android: require absolute API URL with clearer login errors (#435).
- CI: Android signed release always runs on `v*` tags; `workflow_dispatch` can
  attach to an existing tag via `attach_to_tag` (#434).

---

## [1.0.1] — 2026-07-18

First Android sideload-capable patch on the public selfhost line. Tag `v1.0.0`
remains Docker/selfhost-only (no APK). Prefer `v1.0.1+` for APK installs.

### Added (M11 Sprint 5 — FCM registration)

- Device push-token API: `PUT/DELETE /devices/push-token`, `GET /devices/push-tokens`,
  `POST /devices/push-test` (neutral check-in copy); migration `030_device_tokens`.
- Optional `firebase-admin` extra (`correlcore-backend[fcm]`) + `FCM_ENABLED` /
  `FCM_CREDENTIALS_JSON` settings (off by default for selfhost).
- Capacitor `@capacitor/push-notifications` wiring after login; sideload builds
  without `google-services.json` omit FCM. Docs: [`docs/features/PUSH.md`](docs/features/PUSH.md).

### Added (M11 Sprint 4 — Widget API + Glance)

- `GET /api/v1/widget/summary` — compact JWT summary (`has_entry`, `mood_avg_7d`,
  `suggested_next_entry_at`) for homescreen polling; see `docs/API.md` §7b.
- Jetpack Glance `CorrelCoreWidget` + WorkManager (15 min, battery-aware) under
  `apps/android/…/widget/`; “+ Add entry” deep-links to `correlcore://entries/new`.
- Capacitor plugin `WidgetCredentials` mirrors in-memory access token + API base
  into app-private SharedPreferences (ADR-0006 exception for Glance only).
- Feature doc: [`docs/features/WIDGET.md`](docs/features/WIDGET.md).

### Added (M11 Sprint 3 — Capacitor Bearer auth)

- Capacitor builds (`VITE_CAPACITOR=1`) use in-memory Bearer tokens via `apiFetch`
  (ADR-0006); browser/PWA cookie path unchanged.
- Login/refresh/verify/reset opt-in returns `access_token` + `refresh_token` when
  `?include_access_token=true`.
- Runtime API base URL for selfhost (Settings → App) + build-time `VITE_API_BASE_URL`.
- Ops checklist + tracking issue for signing/Play: [`docs/selfhost/M11_OPS_CHECKLIST.md`](docs/selfhost/M11_OPS_CHECKLIST.md), #429.

### Added (M11 Sprint 1–2 — Capacitor shell + signed sideload)

- Committed Capacitor Android platform under `apps/android/android/` (`de.correlcore.app`).
- Static SPA build for the shell: `pnpm --filter @correlcore/web build:capacitor`
  (`adapter-static` → `build-capacitor`); Docker/selfhost still uses `adapter-node`.
- Aligned `@capacitor/{core,cli,android}` to **7.6.7**; brand launcher/splash assets;
  deep link `correlcore://entries/new`.
- Root scripts `pnpm cap:sync` / `pnpm cap:assemble:debug` / `pnpm cap:assemble:release`.
- CI: debug APK artifact; signed `assembleRelease` + `bundleRelease` on `v*` tags when
  `ANDROID_KEYSTORE_*` secrets are set; attaches APK/AAB/`SHA256SUMS.txt` to GitHub Release.
- Sideload tester guide: [`docs/selfhost/ANDROID_SIDELOAD.md`](docs/selfhost/ANDROID_SIDELOAD.md).
  See [`docs/M11_SPRINT_PLAN.md`](docs/M11_SPRINT_PLAN.md).

### Added (M10.1 — Insight pipeline & tag groups)

- **Insight triggers (ADR-0037):** `POST /api/v1/insights/regenerate` (owner, 1×/hour),
  admin `POST /api/v1/insights/trigger`, post-batch debounced regeneration, worker `--once` CLI.
- **Tiered tag clusters:** pair (30+ days), provisional k-means (45+), robust (90+);
  API fields `cluster_maturity`, `cluster_mode`, `entries_until_robust`, `silhouette_score`.
- **Frontend:** `TagGroupsSection` maturity badges; Settings → **Refresh insights** /
  **Erkenntnisse aktualisieren**.

### Added (Open-issues / foundations — post-v1.0.0)

- **M4.1.1 offline sync hardening (#258):** revision locking, initial pull backfill,
  note conflict markers, ValidationError→400, tag/symptom `updated_at` on create,
  conflict retention RLS, tag/symptom pull apply, per-user Dexie, multi-tab sync locks.
- **Notes in Analysis (#194–#202, #199):** ADR-N-01/02/03; entry note visibility/summary;
  markers + marker insights; `NoteSignalExtractor` + insight evidence UI.
- **M11 Capacitor scaffold + HC consent (#27, #31):** `apps/android` package, CI validate;
  `consent_log` + Settings Privacy gate for Health Connect.
- **M7-S8 / analytics (#147–#149):** weekly digest endpoint + worker CLI; optional Ollama
  statement layer; changepoint detection (`ruptures`).
- **Security / media (#62, #28):** custom symptom slug HMAC (ADR-0039); server-side EXIF
  strip foundation + `/media/photos` stub.
- Digest opt-in, prefer stored weekly digest on GET (WP1), auth hardening, LayerChart
  defer, security audit remediations (#396–#399).
- Onboarding card for insight maturity phases (#425).

### Changed

- GitHub Releases put **Android APK download links at the top** of the release
  notes (tappable on mobile); sideload docs updated (#433). `v1.0.0` itself has no APK
  (selfhost-only tag).

### Fixed (Codex review follow-up for #393)

- Honor `note_visibility=hidden` in marker analytics and GDPR export.
- Bind per-user DEK in digest worker; HMAC custom symptom slugs on sync upsert.
- `has_note` list filter applied before SQL `LIMIT`; null visibility patches no longer 500.
- Batch create schedules note-signal extraction; digest login redirect → `/auth/login`.
- Note marker chips keep pending selections; visibility changes mark autosave dirty.
- Marker insights respect 90-day window; timeseries note dots use full axis dates.
- Move/lazy-load `httpx` for optional Ollama path; pass `SLUG_HMAC_KEY` in compose stacks.
- Password hashing via bcrypt directly (passlib wrap bug) (#414).

### Documentation

- **Status sync (2026-07-15):** Aligned milestone/status docs with post-#393 foundations —
  digest/Ollama/changepoint, notes-in-analysis, slug HMAC, EXIF strip, Capacitor scaffold,
  HC consent. Updated `API.md`, docs-site API overview, `DESIGN_DOCUMENT.md` v0.14,
  `CLOSEOUT_SPRINT_PLAN`, `M7_*`, `M11_NOTES`, `M13_NOTES`, `FRONTEND_STATUS`, ADR-0025 index,
  `symptom-analytics.md`, issue-tracker hygiene, `AGENTS.md`.
- M11 sprint plan with pre-Play APK distribution (#426).

---

## [1.0.0] — Public Selfhost Release — 2026-07-11

First public selfhost release (**M10**). CorrelCore is a privacy-first mood and habit
tracker with correlation insights — deployable on your own infrastructure via Docker Compose.

### Release highlights

- **Selfhost compose:** quickstart homelab path, production VPS (Traefik), bootstrap script, MinIO removed (photos → M13)
- **Published images:** multi-arch (`linux/amd64`, `linux/arm64`) on GHCR and optional Docker Hub; GitHub Release workflow
- **Documentation:** MkDocs site ([GitHub Pages](https://sturmi77.github.io/correlcore/)) with install, user guide, API overview, privacy
- **Landing & legal:** marketing home, `/impressum`, public `/privacy`, footer links (DSGVO M10)
- **License:** AGPL-3.0-or-later (see `LICENSE`)

Since `0.6.0`, this release includes milestones **M1–M9** (daily entry through beta hardening) and **M10** release engineering. See [`docs/M10_SPRINT_PLAN.md`](docs/M10_SPRINT_PLAN.md) and per-milestone docs under `docs/`.

### Added

- **M10 Sprint 6 — Milestone closeout (M10-C).** Quality gate
  ([`docs/quality/M10_QUALITY_GATE.md`](docs/quality/M10_QUALITY_GATE.md)) and visual QA
  ([`docs/quality/M10_VISUAL_QA.md`](docs/quality/M10_VISUAL_QA.md)); version **`1.0.0`**
  in manifests; final `v1.0.0` tag procedure; GitHub milestone #7 closeout.

- **M10 Sprint 5 — Version & go-public prep.** CHANGELOG `[1.0.0]` section; AGPL-3.0-or-later metadata in root, web, and backend manifests; `v1.0.0-rc.1` release candidate tag; go-public operator checklist ([`docs/selfhost/GO_PUBLIC_CHECKLIST.md`](docs/selfhost/GO_PUBLIC_CHECKLIST.md)).

- **M10 Sprint 4 — Landing & legal.** Marketing landing page for anonymous users
  (replaces pre-alpha badge), `/impressum` route with AT/DE template, public
  `/privacy` access, and legal footer links on landing, auth, and privacy pages.
  See [`docs/quality/M10_LANDING_LEGAL_TEST.md`](docs/quality/M10_LANDING_LEGAL_TEST.md).

- **M10 Sprint 3 — Docs site.** MkDocs Material site under `docs-site/` with install
  guide, user guide, API overview, and privacy notice. CI: `mkdocs build --strict`;
  GitHub Pages deploy workflow. See [`docs/quality/M10_DOCS_SITE_TEST.md`](docs/quality/M10_DOCS_SITE_TEST.md).

- **M10 Sprint 2 — Container publish & release.** Multi-arch (`linux/amd64`,
  `linux/arm64`) image builds in `release-images.yml`; optional Docker Hub mirror
  when `DOCKERHUB_USERNAME` / `DOCKERHUB_TOKEN` CI secrets are set; GitHub Release
  workflow on `v*` tags with CHANGELOG section extraction; `IMAGE_REGISTRY` compose
  override (default `ghcr.io/sturmi77`). See
  [`docs/selfhost/CONTAINER_IMAGES.md`](docs/selfhost/CONTAINER_IMAGES.md) and
  [`docs/quality/M10_RELEASE_PUBLISH_TEST.md`](docs/quality/M10_RELEASE_PUBLISH_TEST.md).

- **M10 Sprint 1 — Compose & install parity.** Production compose: `migrate`
  init, YAML-DRY anchors, MinIO removed (photos → M13); quickstart compose +
  bootstrap script; INSTALL Path B first. See
  [`docs/M10_SPRINT_STATUS.md`](docs/M10_SPRINT_STATUS.md).

- **M9 — Beta Hardening (complete).** Formal closeout of ops, privacy, backup,
  observability, security CI, and beta program between M5.1 and M10: `PRIVACY.md`
  - in-app link, GDPR self-service E2E (delete, ZIP export, analytics opt-out),
    optional selfhosted GlitchTip with PII scrub, consolidated
    [`docs/selfhost/INSTALL.md`](docs/selfhost/INSTALL.md), backup restore protocol,
    CI dependency audits + style-contract lint, beta onboarding/triage docs, and
    milestone quality gate. Closes #29 (operator: close issue on GitHub). See [`docs/M9_SPRINT_PLAN.md`](docs/M9_SPRINT_PLAN.md),
    [`docs/M9_SPRINT_STATUS.md`](docs/M9_SPRINT_STATUS.md), and
    [`docs/quality/M9_QUALITY_GATE.md`](docs/quality/M9_QUALITY_GATE.md).

- **M5.1 — UX Polish & Flow Consolidation (complete).** Formal closeout of the
  `ux(O-xx)` issue cluster (#251–#273) between M5 and M9: onboarding → first
  entry funnel, Home brief-first layout, maturity-gated Insights analytics,
  unified entry sheet, inline habit setup, contextual PWA/export flows, and
  desktop Trends sticky range. Implementation delivered via GUI optimization
  Phases 1–3; this release adds sprint tracking, visual QA sign-off, and
  milestone docs. Closes #251–#271, #273. #272 (password reset) remains open.
  See [`docs/M5_1_SPRINT_STATUS.md`](docs/M5_1_SPRINT_STATUS.md) and
  [`docs/quality/M5_1_UX_VISUAL_QA.md`](docs/quality/M5_1_UX_VISUAL_QA.md).

- **M4.1 — Offline-first sync (complete).** Dexie.js local persistence
  (`correlcore-offline`), append-only `change_log`, stable `client_id`, and
  `sync_meta` cursors. Backend: `POST /api/v1/sync/push`, `GET /api/v1/sync/pull`
  with per-field LWW merge, opaque `user_rev` cursor, idempotent
  `(client_id, batch_id)` batches, and `sync_conflicts` log with 90-day retention
  (`GET /api/v1/user/sync-conflicts`). Frontend: local-first entry saves behind
  `canUseOfflineSync()` (verified users + feature flag), `syncOrchestrator`
  push/pull on reconnect, Settings → App & offline sync summary. Contract:
  [ADR-0036](docs/adr/0036-offline-sync-v1-scope.md). Visual QA:
  [`docs/quality/M4.1_VISUAL_QA.md`](docs/quality/M4.1_VISUAL_QA.md). Closes #10, #24.

### Changed

- **GitHub tracker hygiene (post-closeout).** Closed stale M3 issues (#15–#17); relabeled
  #31→M8, #147/#148→M7-S8, #149→post-M7, #27→M11; closed shipped milestones M0–M3 on GitHub.
  See [`docs/CLOSEOUT_SPRINT_PLAN.md`](docs/CLOSEOUT_SPRINT_PLAN.md) §1.3.

- **M4-C quick wins + PWA closeout.** Visual QA sign-off in
  [`docs/quality/M4_VISUAL_QA.md`](docs/quality/M4_VISUAL_QA.md). Offline sync (#10) and conflict
  log (#24) rescoped to M4.1; Capacitor strategy (#27) → M11. Milestones M4/M5 closed on GitHub.

- **M5-C2 Habits Core closeout.** Target-aware insufficient-data gating (heatmap stays visible
  for sparse habits); correlation metric labels normalized (`mood_score` → mood). Visual QA in
  [`docs/quality/M5_VISUAL_QA.md`](docs/quality/M5_VISUAL_QA.md). Closes #157/#159.

- **M5-C1 habit dashboard polish.** Habit list shows adherence + window summary and correlation
  hint; detail adds adherence bar, predictor copy, insufficient-data state, and mobile bottom sheet.
  Backend adds `correlation_metric` on habit stats. See #157/#159.

- **M7 milestone complete (Sprint M7-C).** Formal closeout: audit findings and deferred-work
  index in [`docs/CLOSEOUT_SPRINT_PLAN.md`](docs/CLOSEOUT_SPRINT_PLAN.md); quality gate verdict
  **M7 Complete** in [`docs/quality/M7_QUALITY_GATE.md`](docs/quality/M7_QUALITY_GATE.md);
  Sprint 9 visual QA sign-off [`docs/quality/M7_SPRINT9_VISUAL_QA.md`](docs/quality/M7_SPRINT9_VISUAL_QA.md);
  GitHub #146/#150 closed. Optional LLM/digest (#147/#148) → M7-S8; changepoint (#149) → post-M7.

- **M7 Sprint 9 complete — spec complete.** Entry-history drawer and symptom×tag detail sheet on
  `/insights`; confounded insight cards with ranking tie-break; heatmap keyboard navigation, tag
  cluster sort at `robust`, and mixed signal clusters API (`members[]` with tags + symptoms). Quality
  gates: backend 459 tests, web 489 tests. See [`docs/M7_SPRINT_STATUS.md`](docs/M7_SPRINT_STATUS.md).

- **M7 Sprint 9 plan (spec complete).** Work packages A–E in
  [`docs/M7_SPRINT9_PLAN.md`](docs/M7_SPRINT9_PLAN.md): interaction, feed confounder UX,
  heatmap polish, combined cluster API, docs sign-off (excludes sleep/cycle/LLM).

- **M7 Sprint 7 complete — core milestone exit.** OLS weekday confounder (#146) with
  Newey-West HAC in `weekday_confounder.py`; hierarchical co-occurrence heatmap reorder (#150) at
  `robust` phase; changepoint (#149) remains deferred. See [`docs/M7_SPRINT_STATUS.md`](docs/M7_SPRINT_STATUS.md).

- **M7 Sprint 6 symptom visualisation complete.** Calendar heatmap and trend overlay in
  `SymptomAnalyticsSection`; Lift methodology in `CorrelationDisclaimer`; component tests for M7
  insight sections. See [`docs/M7_SPRINT_STATUS.md`](docs/M7_SPRINT_STATUS.md).

- **M7 Sprint 5 closeout complete.** ADR-0025 accepted; QA seed + integration tests
  (`test_m7_qa_seed_integration.py` in CI migrations-smoke); API verifier
  (`scripts/verify_m7_qa_api.py`); sign-off [`docs/quality/M7_SPRINT5_FULLSTACK_QA.md`](docs/quality/M7_SPRINT5_FULLSTACK_QA.md).

- **M7/M8 milestone swap (docs only).** Roadmap reordered: M7 = Insights v2
  (Lasso, lag, symptom analytics, clustering); M8 = Sleep & Health Connect.
  Rationale and consequence index: [`docs/M7_M8_MILESTONE_SWAP.md`](docs/M7_M8_MILESTONE_SWAP.md).
  No code or schema changes.

### Added

- **M7 weekday OLS confounder.** `backend/app/services/weekday_confounder.py` adjusts tag/symptom
  associations for weekday effects; co-occurrence pairs flagged when overlap is weekday-driven.

- **M7 clustered heatmap sort.** `cooccurrenceClusterOrder.ts` reorders symptom×tag axes by Jaccard
  profile similarity when `sortMode === 'clustered'` (`robust` phase).

- **M7 symptom views.** `SymptomCalendarHeatmap`, `SymptomTrendOverlay`, and
  `symptomAnalyticsViews` helpers (eligibility, calendar grid, rolling trend series).

- **M7 QA seed script.** `backend/scripts/seed_m7_qa.py` seeds a verified user with
  100 days of tag/symptom patterns for full-stack `/insights` QA without mock mode.

- **Mobile Insights Phase 3 closeout.** Mobile `/insights` ranks insights via
  `insightRanking`, surfaces the strongest signal in `MobileInsightLead` with
  semantic confidence and maturity context, and keeps matrices/co-occurrence
  behind explicit detail controls. Figma Sprint 3 flow (`98:1573`), Playwright
  coverage (`mobile-insights-foundation`, `m7-insights-mobile`), and QA sign-off:
  [`docs/quality/MOBILE_INSIGHTS_PHASE3_QA.md`](docs/quality/MOBILE_INSIGHTS_PHASE3_QA.md).

- **Mobile supporting flows Figma Sprint 4.** Production-aligned frames for
  Settings, symptom management, App & Offline, auth recovery, onboarding touch
  states, and PWA recovery overlays — flow board `105:1626` (22 screens at
  390×844, 1680 px layout board). See [`apps/web/figma/README.md`](apps/web/figma/README.md).

- **Mobile web Sprint C closeout.** Cross-phase QA at 390/430/1280 px across
  Entry, Trends, Insights, Settings/PWA; 17/17 Playwright mobile specs green.
  Sign-off: [`docs/quality/MOBILE_WEB_CLOSEOUT_QA.md`](docs/quality/MOBILE_WEB_CLOSEOUT_QA.md).
  Added `npm run test:e2e:mobile` and serial Playwright workers for stable runs.

- **Mobile web Sprint D closeout.** Audit matrix refreshed to green for Phases 0–4
  mobile surfaces; `MobileInsightLead.figma.ts` Code Connect template; GitHub #200
  rescoped/closed (M8); #214 M5.1 follow-ups closed on `main`.

- **M7 Sprint 1 opened: Lasso & Lag backend slice.** Added M7 sprint
  plan/status docs, the additive `symptom_cluster` insight type, a multivariate
  design matrix with metric/tag/symptom features, deterministic
  `TimeSeriesSplit` Lasso models, and 1-7 day lag analysis with causal
  `shift()`/`dropna()` handling.

- **M7 Sprint 2 Symptom Analytics.** Added `symptom_mood_association` and
  `symptom_tag_cooccurrence` insight types, symptom Level 1/2 analytics with
  FDR and weekday confounder metadata, `GET /api/v1/insights/symptom-tag-cooccurrence`,
  and a symptom-tag co-occurrence heatmap in `/insights`.

- **M7 Sprint 3 Tag Clustering.** Added pgvector-backed `tag_vectors`, nightly
  tag-vector recomputation, `GET /api/v1/insights/tag-clusters`, k-means tag
  groups with insufficient-data guards, and a `/insights` Tag Groups section.

- **M5.1 Tag co-occurrence heatmap.** `GET /api/v1/insights/tag-cooccurrence`
  plus Insights **Patterns** section with `TagCooccurrenceHeatmap` and filtered
  entry sheet. Closeout: [`docs/quality/M5_1_VISUAL_QA.md`](docs/quality/M5_1_VISUAL_QA.md).

- **M5 Habits Core ohne Gamification.** Tags expose `habit_type` and
  `target_frequency` through API/UI, new `/api/v1/habits` endpoints return
  goal-based adherence plus optional correlation contribution, Settings > Tags
  configures build/reduce habits, and `/trends` adds a Habits tab with neutral
  adherence list/detail and heatmap reuse. Co-occurrence is documented as
  M5.1/backlog and is not an M5 exit criterion.

- **M4 Quick Wins + Mobile/PWA Hardening.** Entry create/update/read now carries
  `cycle_day` and the existing `slot` field is editable with clean `409`
  conflict handling. The web entry flow adds slot chips and cycle day behind
  `+ More`; Trends Mood adds persisted `Raw | Smoothed` client-side SMA; guided
  `/onboarding` creates/reuses custom tags by slug; Dev Mode gains in-memory
  phase/onboarding/entry-count overrides; PWA hardening adds an install banner,
  `/offline`, manifest/iOS metadata, and a service worker that skips `/api/*`.

- **M3.7 Color System Hardening.** `apps/web/src/app.css` now contains the
  complete gold and insight-maturity semantic token set for dark, light, and
  system-preference fallback themes. Legacy `--color-ms-primary*` aliases were
  removed from runtime CSS usage, auth surfaces now use canonical
  `--color-primary`, and `pnpm check:contrast` enforces ADR-0027 contrast pairs
  in Web CI. `docs/FRONTEND.md` and `docs/M3_7_SPRINT_STATUS.md` document the
  theming source of truth, QA status, and closeout criteria.

- **M3.5 / M3.6 Release-Closeout.** Rendered browser QA passed from local clone (`correlcore-ci`, `70bb5ed`) on 2026-05-27. M3.5 and M3.6 marked release-complete in README, sprint status docs, and design-doc checklists. GitHub issues #186 and #188–#192 closed. Refs #186, #188, #189, #190, #191, #192.

- **M3.5 Sprint 1 — App Shell.** Mobile bottom navigation (four ADR-0017 primary screens), side nav from 768px, skip link, and `AppNav` routing helpers. Refs #186.

- **M3.5 Sprint 2 — Entry Flow Foundation.** Entry form sections, informative work-context hint with weekend auto-fill, central `metrics.ts` / stress display inversion for trends charts, and `defaultWorkContextForDate`. Refs #170, #171, #182.

- **M3.5 Sprint 3 — Entry bottom sheet.** `EntryForm` + `EntrySheet` from Home CTA; optional fields behind “+ More”; `/entries/new` deep link preserved. Sleep quality (#172) deferred to M8 (Variant B). Refs #186.

- **M3.5 Sprint 4 — Home recomposition.** Three-zone Home per ADR-0017; matrix, summary, recent entries, and confidence scale removed from the first screen. Refs #186.

- **M3.5 Sprint 5 — Insights quality and progressive disclosure.** New `InsightQualityMeter` on `/insights` shows descriptive readiness stages from real day-entry dates: neutral 0-3 entry copy, `X/30` plus a 14-day pace estimate for 4-29 entries, no estimate when recent entries are absent, and first/full insight stages from 30/90 entries. Feed copy, DE/EN i18n, and tests were extended while preserving filter tabs, disclaimer access, and sorting by `confidence × |effect_size|`. Refs #184, #186.

- **M3.5 Sprint 6 — Trends tabbed analysis surface.** `/trends` now uses Mood / Activities / Health tabs with unified 7D / 30D / 90D / 1Y controls, a 90-day `quarter` stats range, and read-only Entry History as an overlay instead of a primary route. The Health tab avoids unfinished charts and keeps visible copy neutral around tracking consistency. Refs #182, #186.

- **M3.5 Sprint 7 — Settings, language and developer UX.** Settings is organized into the canonical TRACKING / ANALYSIS / PRIVACY & DATA / APPEARANCE / DEVELOPER sections, with local `DE | EN` language switching and Dev Mode Force Visualizations backed by centralized mock data. Refs #183, #185, #186.

- **M3.5 Sprint 8 — Tag lifecycle and inactive correlations.** Tag settings now split active and inactive tags, hidden tags remain reactivatable via `include_hidden=true`, entry pickers and tag stores keep hidden tags out of new entries, and new stats/insight calculations skip hidden tags without deleting existing insights. Existing tag insights are marked neutrally when their tag is inactive. Refs #173.

- **M3.5 Sprint 9 — Visual QA, docs and closeout.** Added the M3.5 visual QA handoff, reconciled `FRONTEND.md` with the implemented screen model, documented the remaining rendered-QA/tooling blockers for the NAS UNC environment, and captured the GitHub issue closure status for #170, #171, #172, #173, #182, #183, #184, #185, and #186.

- **M3.5 Vollständigkeitsprüfung.** The milestone is implementation-complete but not release-complete: rendered browser QA, GitHub issue closure/rescope, CI gate confirmation, and API/Web image verification remain required before M3.5 should be tagged as complete.

- **M3.5 Restpunkt-Recherche.** Public GitHub checks now identify the remaining closeout state precisely: release image build succeeded for `8274144`, Web CI failed on two lint/typecheck findings that are fixed locally, and the M3.5 issue closure/rescope matrix is documented for authenticated GitHub execution.

- **M3.6 Meilenstein eingeführt.** ADR-0021 Insight Maturity Phases now has a dedicated implementation milestone between M3.5 and M4, with sprint plan/status docs for issues #188-#192 covering the API `insight_maturity` contract, Journey Banner, Maturity Badge, phase-aware empty states, and milestone notification card. GitHub milestone assignment is documented but blocked locally by missing `gh`/token tooling.

- **M3.6 Sprint 0 — API Contract and Shared Types.** `GET /api/v1/insights` und `/api/v1/insights/latest` liefern jetzt ein serverseitig berechnetes `insight_maturity`-Objekt auf Basis eindeutiger Tracking-Tage (`collecting`, `early_patterns`, `provisional`, `robust`). Web-API-Typen und der Insight Store lesen diesen Contract, Phase-Boundary-Tests decken 1/6/7/13/14/29/30+ Eintraege ab, und `docs/API.md` dokumentiert die neue Response-Form. Refs #191.

- **M3.6 Sprint 1 — Journey Banner and Explainer.** Neue Komponenten `InsightJourneyBanner` und `InsightJourneyExplainer` zeigen die vom Backend gelieferte Insight-Maturity-Phase auf `/insights` sowie als einklappbare Home-Variante. DE/EN `maturity.*` Copy beschreibt alle vier Phasen neutral, ohne dass das Frontend die Phase aus Entry-Counts neu berechnet. Refs #188.

- **M3.6 Sprint 2 — Maturity Badge and Phase-Aware Empty States.** Insight-Karten zeigen im Standardzustand jetzt `InsightMaturityBadge` statt Confidence-Skala; statistische Confidence-Details bleiben im aufgeklappten Detailbereich. Der Insights-Feed nutzt `insight_maturity` fuer phase-aware Empty-/Locked-State-Copy inklusive Unsicherheitshinweisen fuer `early_patterns` und `provisional`. Refs #189, #190.

- **M3.6 Sprint 3 — Phase Milestone Card.** Home und `/insights` zeigen eine einmalige `InsightPhaseMilestoneCard`, wenn Nutzer eine neue Insight-Maturity-Phase erreichen. Explizites Dismiss wird optimistisch ausgeblendet und ueber `reached_milestone_keys` in den User Preferences persistiert; es gibt keine Toasts und keine Auto-Dismiss-Logik. Refs #192.

- **M3.6 Sprint 4 — QA and Closeout.** Sprint 4 dokumentiert den M3.6-Closeout-Status: `main` ist auf `72f5a9c` synchron, GitHub hat nach `12bdad4` erneut einen Prettier-Autofix-Commit erzeugt, `CI — Web` ist fuer den Feature-Commit in Typecheck und Lint fehlgeschlagen, Build und Prettier-Autofix waren erfolgreich. Public GitHub checks liefern keine konkreten Diagnosen ausser `exit code 1`; lokale pnpm-Typechecks bleiben in der Windows/NAS-Corepack-Umgebung blockiert. Die Issues #188-#192 sind weiterhin offen und ohne Milestone, weil GitHub-Schreibzugriff (`gh`/Token) lokal fehlt.

- **M3 Abschluss umgesetzt.** Die offenen M3-Themen #151, #152, #154 und #156 sind lokal implementiert und per Abschluss-Gates verifiziert. Backend-Gates: `ruff check`, `ruff format --check`, `mypy app` und 372 Pytest-Tests gruen mit gueltigem Test-Fernet-Key. Web-Gates: Typecheck, Lint, 195 Vitest-Tests und Production-Build gruen. Die finale Veroeffentlichung erfolgt ueber PR nach `main` und anschliessende Verifikation des `release-images.yml`-Workflows fuer neue `correlcore-api`- und `correlcore-web`-Images.

- **M3 Day-over-Day Delta umgesetzt.** Neuer Backend-Endpoint `GET /api/v1/entries/delta?entry_date=YYYY-MM-DD&slot=day` liefert einen neutralen Vergleich zwischen Eintrag und Vortag: metric-only `today`/`previous`, Delta-Werte fuer Mood/Energy/Stress und gemeinsame Tags. Das Web ergaenzt `fetchEntryDelta` und `DayDeltaCard.svelte`; `/entries/new` aktualisiert die Karte nach Auto-Save sowie beim Laden bestehender Eintraege und blendet sie ohne Vortagsvergleich aus. Copy bleibt rein deskriptiv und vermeidet Bewertungs-, Diagnose- oder Kausalframing.

- **M3 Cold-start Onboarding implementiert und verifiziert.** Neue Entry-Source `direct | retrospective | import | wearable` und `POST /api/v1/entries/batch` erlauben bis zu sieben retrospektive Onboarding-Eintraege, die serverseitig als `retrospective` markiert und weiterhin durch das bestehende 7-Tage-Backdate-Limit begrenzt werden. Neue Tabelle `user_profiles` plus `PUT /api/v1/user/profile` speichert optionale Profilantworten; Export enthaelt Entry-Source und optionales Profil, Erasure laeuft ueber `ON DELETE CASCADE`. Das Web ergaenzt `/onboarding/retro` und `/onboarding/profile` sowie `insight_previews.json` mit statischen Preview-Karten, die als allgemeine Forschungshinweise gelabelt sind und keine persoenlichen oder diagnostischen Aussagen treffen. Der Entry-Service nutzt fuer date-only Backdate-Checks bewusst das lokale Serverdatum statt UTC, damit Europe/Vienna-Nutzer nach Mitternacht nicht faelschlich blockiert werden.

- **M3 Insights-Seite und Korrelations-Matrix umgesetzt.** Neue Route `/insights` zeigt aktuelle worker-generierte Insights aus `GET /api/v1/insights/latest` mit Statement, Tier, Konfidenz, Sample-Count und Datum. `InsightMatrix.svelte` stellt Tag-Mood-Korrelationen heatmap-artig dar, filtert Low-Confidence-Zeilen, sortiert nach absoluter Effektstaerke, kodiert positive/negative/neutrale Effekte farblich und legt Statement, `sample_n` und Confidence als Hover-/Tap-Tooltip ab. Ein PNG-Export erzeugt eine einfache Matrix-Grafik fuer externe Gespraeche oder Dokumentation. `HomeInsight` verlinkt jetzt mit "Mehr Erkenntnisse" auf die dedizierte Seite. Der fruehere `X/30`-Leerzustand aus dem Legacy-Issue wurde nicht wieder eingefuehrt, weil Sprint 8 die permanente Confidence-Skala liefert.

- **M3 First-Week Tracking Consistency UX umgesetzt.** Weekday-Pattern-Insights enthalten nun vollstaendige Wochentags-Mood-Averages und Entry-Counts im Payload. Neuer Preferences-Service plus `GET/PATCH /api/v1/user/preferences` persistiert `dismissed_insight_keys` in der bestehenden `user_preferences`-Tabelle. Auf Home zeigt `WeekdayPatternChart.svelte` einen neutralen 7-Balken-Chart fuer durchschnittliche Stimmung pro Wochentag und `FirstWeekInsightBanner.svelte` erscheint nur einmal, wenn ein Weekday-Pattern bereitsteht; Dismiss wird optimistisch ausgeblendet und serverseitig gespeichert. Die Copy bleibt bewusst sachlich: keine Streak-, Reward-, Badge-, Diagnose- oder Dringlichkeits-Sprache.

- **M3 Insight Confidence Scale umgesetzt.** Neuer Backend-Endpoint `GET /api/v1/dashboard/summary` liefert `entry_count`, `insight_tier` und einen logarithmisch skalierten `confidence_score` fuer die permanente Home-Skala. Der Score nutzt feste Anker (0, 3, 8, 15, 30, 100 Eintraege), damit fruehe Datenqualitaetsverbesserungen sichtbar sind, ohne einen `X/30`-Countdown oder ein Fertig-Gefuehl zu erzeugen. Das Web-Frontend hat einen neuen `dashboard`-API-Client und `InsightConfidenceScale.svelte`; die Komponente rendert kontinuierlichen Fill, neutrale Tier-Labels, Entry-Count nur als sekundare Meta-Info, tokenbasierte Farben und respektiert `prefers-reduced-motion`. Neue Backend- und Vitest-Tests decken Endpoint, Score-Boundaries und alle Tier-Zustaende ab.

- **M3 Statistik-Haertung fuer Analytics Engine abgeschlossen.** Sprint 7 haertet die bestehenden M3-Korrelationen gegen Fehlalarme und Look-ahead-Bias: Spearman-Kandidaten sind auf `energy_mood` und `stress_mood` begrenzt, Spearman- und Point-biserial-Kandidaten speichern Benjamini-Hochberg-FDR-Metadaten (`p_corrected`, `multiple_testing_correction=fdr_bh`), Tag-Korrelationen respektieren `ANALYTICS_MIN_TAG_USAGES`, und konzentrierte Wochenmuster werden als `weekday_confounded` markiert. Die Persistenzabfrage nutzt ausschliesslich `entry_date < as_of`, damit `created_at`/`updated_at` keine Zukunftsinformation in backfilled Entries einschleusen. Neue Tests decken FDR-Zufallsrauschen, seltene Tags, Wochentags-Bias und die temporale Query-Semantik ab; DE/EN-Locale-Templates fuer neutrale Insight-Aussagen sind vorbereitet.

- **M3 Home-Insight-Preview angebunden.** Das Web-Frontend nutzt die in Sprint 5 eingefuehrten Read-API-Endpunkte ueber einen neuen `insights`-Client und zeigt auf der authentifizierten Home-Seite eine neutrale, read-only Karte fuer die neueste worker-generierte Erkenntnis inklusive Tier, Konfidenz, Sample-Anzahl, Datum und medizinischem Disclaimer. Fehler beim Insight-Fetch blockieren Home-Summary, Recent Entries oder Sparkline nicht. Keine Onboarding-Route, keine Dismiss-/Preference-UI, kein manueller Trigger und keine Backend-Aenderung in diesem Sprint.

- **M3 Insights Read-API freigeschaltet.** Neuer Router `GET /api/v1/insights` und `GET /api/v1/insights/latest` liefert worker-generierte Insights fuer verifizierte User read-only aus. Beide Endpunkte sind owner-gefiltert, rate-limitiert, nutzen den bestehenden Auth/DEK-Pfad fuer `statement_enc` und geben `InsightListResponse` mit neutralen Statement-/Confidence-/Tier-Feldern zurueck. `latest` dedupliziert nach analytischem Subject, ohne Postgres-spezifisches `DISTINCT ON`. Kein manueller Trigger, keine UI und keine neue Worker-Logik in diesem Sprint.

- **M3 Analytics Worker angebunden.** Der bestehende `python -m app.workers.analytics`-Worker fuehrt im taeglichen 03:00-UTC-Lauf nun neben dem Unverified-Account-Cleanup auch die M3-Insight-Generation aus. Neuer Service `insight_worker_service` waehlt nur aktive, verifizierte User mit vorhandener DEK und ohne `analytics_enabled=false`, bindet pro User den entschluesselten DEK fuer `insights.statement_enc` und ruft die Engine aus Sprint 3 auf. Jeder User laeuft in einer eigenen Transaktion; defekte DEKs oder Datenfehler werden pro User geloggt und rollen nur dessen Batch zurueck. Keine API-/UI-Routen und kein manueller Trigger in diesem Sprint.

- **M3 Analytics Engine v1 gestartet.** Neuer interner Service `app.services.insight_engine` berechnet deterministische Insight-Kandidaten ohne API-/Worker-Scope vorzuziehen: Tier-Grenzen 3/8/15/30 Eintraege, Weekday-Pattern ab 7 Eintraegen, Spearman-Korrelationen fuer Mood/Energy/Stress und punkt-biseriale Tag-vs-Mood-Korrelationen ab 15 Eintraegen, inklusive Effektstaerke, Confidence, Sample-Count, neutralen template-basierten Statements und `medical_disclaimer_required`/`causal_claim=false`-Flags. `generate_and_store_insights` regeneriert idempotent die `insights`-Rows pro User/Datum auf Basis eigener Entries/Tags; ein spaeterer Worker muss dabei den User-DEK fuer `statement_enc` binden. Neue Tests decken Tier-Grenzen, Cold-Start-Weekday-Insights, bivariate Sample-Gates, Tag-Gruppengroessen und Persistenz-Semantik ab. Noch nicht enthalten: Scheduler-Aenderung, API-Routen, Home-Insight-UI oder Onboarding.

- **M3 Analytics-Foundation vorbereitet.** Backend-Runtime, API-CI und das lokale `backend/scripts/check.sh` installieren ab diesem Sprint das `analytics`-Extra (`pandas`, `scikit-learn`, `scipy`, `statsmodels`, `apscheduler`), damit Deployments und Checks dieselbe Dependency-Oberflaeche wie die kommenden Insight-Sprints nutzen. Neue Migration `010_add_insight_and_preference_foundations.py` legt owner-isolierte Tabellen `insights` und `user_preferences` mit RLS, `updated_at`-Triggern, JSONB-Metadaten, verschluesseltem `insights.statement_enc`, Confidence-/Sample-Constraints und DSGVO-relevantem `analytics_enabled`-Flag an. Neue SQLAlchemy-Modelle und Pydantic-Schemas bilden Insight-Typen/Tiers, Insight-Listen sowie Onboarding-/Dismiss-State ab. Noch nicht enthalten: Worker-Logik, API-Routen, Onboarding-UI oder echte Insight-Berechnung.

- **CorrelCore rename completed.** The product, package metadata, UI copy, export filenames, GHCR image names, Docker/Compose service names, deployment examples and collaboration docs now use `CorrelCore` / `correlcore`. Release images are published as `ghcr.io/sturmi77/correlcore-api` and `ghcr.io/sturmi77/correlcore-web`. Export JSON now uses the neutral `app_version` field and `format_version=1.2`; the old deterministic symptom UUID namespace is intentionally preserved for compatibility. Theme preferences migrate from `moodsync-theme` to `correlcore-theme`.

- **M2 Quality-Gate-Findings aus Issue #133 geschlossen.** Die Trends-Visualisierung hat nun selbstbeschreibende Score-Skalen im Export (`format_version=1.1`, `score_legend`, CSV-Scale-Spalten), 44px-Touch-Ziele fuer Slider-Buttons und Trend-Controls, Heatmap-Auto-Scroll zum neuesten/rechten Datum, Heatmap-Intensitaetslegende, Skeleton Loader, Empty States mit CTA, range-aware X-Achsenlabels, Y-Achsenlabel `Score 1-5`, nicht-farbliche Metrik-Unterscheidung per Dash-Pattern und Punktform sowie eine tokenbasierte Dark-Mode-Haertung der `/trends`-Panels. Dokumentiert in `docs/quality/M2_ISSUE_133_CLOSURE.md`.

- **M2-Stretch: Developer-View mit echter Versionsidentifikation umgesetzt (Issue #125).** Neuer default-off Endpoint `GET /api/v1/dev/info` hinter `DEV_VIEW_ENABLED=true` liefert fuer verifizierte User GitHub-Commit, Branch, Build-Time, Image-Tag, optionalen OCI/RepoDigest, Runtime-Versionen, DB-Migration-Head, DB-Pool, Redis/MinIO/Health und Uptime. Release-Builds betten `GIT_COMMIT`, `GIT_BRANCH` und `BUILD_TIME` per Build-Args ins API-Image ein; `IMAGE_TAG` und `IMAGE_DIGEST` bleiben Runtime-Konfiguration aus Compose/Dockhand/Dockge. Neues `/dev` im Web zeigt Commit, Tag und Digest prominent, verlinkt den Commit nach GitHub, bietet Copy-to-Clipboard und Auto-Refresh alle 30 Sekunden. Kein Docker-Socket im API-Container; fehlender Digest wird als `null`/`Digest not provided` angezeigt. Doku: `docs/API.md`, `docs/RUNBOOK_DEPLOYMENT.md`, ADR-0015.

- **M2-Stretch: Heatmap-Drilldown und editierbare Tag-Overrides umgesetzt (Issues #127/#124).** Heatmap-Zellen verlinken nun auf `/entries/day/YYYY-MM-DD` und zeigen die Entries des Tages, optional gefiltert nach dem Tag der Zelle, mit direktem Bearbeiten-/Erfassen-Link. Tags erhalten `is_hidden` per Migration `009_add_tag_hidden_flag.py`; `PATCH /api/v1/tags/{id}` erzeugt bei Default-Tags einen user-owned Copy-on-Write-Override statt globale Defaults zu ändern, `GET /api/v1/tags?include_hidden=true` liefert Hidden-/Override-Zeilen für Settings, normale Tag-Listen und Entry-Picker filtern Hidden-Tags aus. Neue Settings-Route `/settings/tags` erlaubt Name, Kategorie, Icon, Farbe, Ausblenden/Einblenden und Reset von Overrides.

- **Auto-Cleanup fuer unverified Accounts umgesetzt (Issue #101).** Neuer Worker-Job `cleanup_unverified_accounts` loescht unverifizierte User nach `UNVERIFIED_CLEANUP_DAYS` Tagen (Default 7) per hartem `DELETE FROM users`, sodass die bestehende `ON DELETE CASCADE`-Kette Entries, Verification-Tokens und User-Encryption-Keys mit entfernt. Der Worker laeuft taeglich um 03:00 UTC ueber `python -m app.workers.analytics`, loggt nur aggregierten Count plus `user_ids` und niemals E-Mail-Adressen. Compose-Stacks reichen `UNVERIFIED_CLEANUP_DAYS` an API/Migrate/Worker durch; Dockhand/user-test behalten den Worker konservativ hinter dem bestehenden `worker`-Profile. Doku: `.env.example`, `docs/DSGVO.md`, `docs/RUNBOOK_DEPLOYMENT.md` und `infra/dockhand/README.md`.

- **M2 Visualisierung und Datenexport umgesetzt.** Backend: Habit-Schema-Vorgriff nach ADR-0012 (`tags.habit_type`, `tags.target_frequency`, CHECK-Constraints), neue Stats-Endpunkte fuer Zeitreihe, Tag-Frequenz-Heatmap und Eintrags-Streak sowie vollstaendiger Export-Service mit kanonischem `GET /api/v1/user/export` ZIP plus `GET /api/v1/export/json` und `/csv`. Frontend: neue Routen `/trends` und `/settings`, Custom-SVG-Zeitreihe, Tag-Heatmap, Backend-Streak-Datenquelle auf Home, Export-Downloads und Tests fuer API-Clients, Chart-Utilities, Backend-Stats und Export. Doku: `docs/API.md`, `docs/DSGVO.md` und neues `docs/DATA_EXPORT_FORMAT.md`.

- **Home-Dashboard mit Recent-Entries-Liste, 7-Tage-Summary und 14-Tage-Mood-Sparkline gemäß ADR-0014.** Die authentifizierte Startseite (`apps/web/src/routes/+page.svelte`) erhält drei neue Komponenten unterhalb des bisherigen Today-Status-Bereichs: `HomeRecentEntries.svelte` rendert sieben Cards (Heute, Gestern, plus die letzten fünf Wochentage) mit Mood-Emoji (1→😢 … 5→😄), erstem Tag-/Symptom-Icon-Präview und Notiz-Snippet — jede Card linkt auf `/entries/new?date=YYYY-MM-DD`, leere Tage erscheinen als gestrichelte „Kein Eintrag"-Placeholder mit demselben Klick-Pfad; Tag-/Symptom-Daten werden über `Promise.allSettled` lazy nachgeladen, damit ein einzelner 401/Timeout nicht das Grid blockiert. `HomeSummary.svelte` zeigt 7-Tage-Durchschnitte für Mood/Energy/Stress (eine Dezimalstelle, leere Zelle = `–`), den Eintrags-Streak nach ADR-0012 (`computeEntryStreak` mit Coulance-Regel: heute fehlend bricht den Streak nicht) und die `n/7`-Anzahl an erfassten Tagen. `HomeSparkline.svelte` ist ein Custom-SVG (~80 LOC, kein Charting-Lib-Bundle: uPlot 45 KB / Chart.js 175 KB / ApexCharts 400 KB gespart) für 14 Tage Mood-Verlauf, theme-aware via `currentColor`, mit ResizeObserver für responsive Breite, durchgezogenen Linien zwischen benachbarten Datenpunkten, gestrichelten Bridges über Lücken und einem `<title>`-Tooltip pro Punkt für Screenreader. Loader-Logik im Home-Page-Script: ein einziger `listEntries({start: today-13, end: today})`-Call deckt Sparkline und Recent-Liste ab; füllt der so berechnete Streak die 14-Tage-Baseline aus, wird automatisch ein zweiter Call mit 30-Tage-Fenster nachgeschoben (Cap), Werte ≥ 30 erscheinen als `30+`. `/entries/new` respektiert nun den `?date=YYYY-MM-DD`-Query-Parameter via `resolveInitialDate` (Validierung: ISO-Pattern + 7-Tage-Rückblick-Clamp; ungültige Werte fallen still auf heute zurück), die initiale `workContext`-Heuristik nutzt das aufgelöste Initialdatum statt blind `today`. Drei neue Util-Module mit insgesamt 36 Vitest-Tests: `lib/utils/streak.ts` (`localIsoDate`, `shiftIsoDate`, `computeEntryStreak`, `averageOver`, `countDayEntries`, 18 Tests), `lib/utils/sparkline.ts` (`buildSparkline` mit getrennten `solidSegments`/`dashedSegments`-Geometrien, 13 Tests), `lib/utils/dateLabels.ts` (`classifyDateLabel` → `today | yesterday | weekday`, 5 Tests). i18n-Keys neu (DE+EN) unter `home.recent.*` (heading, today, yesterday, empty_card, tags_count, symptoms_count, aria_filled, aria_empty), `home.summary.*` (heading, mood_avg, energy_avg, stress_avg, streak, streak_unit, count), `home.sparkline.*` (heading, caption, aria_label) und `home.weekday.*` (mon…sun). A11y: jede Card hat `aria-label="Eintrag vom DD.MM.YYYY, Stimmung X von 5"` bzw. „Kein Eintrag am DD.MM.YYYY", Sparkline hat `role="img"` plus `aria-label`, Punkte tragen `<title>`-Tooltips. Anonymous-Landing bleibt unverändert. Keine neue Dependency, keine neue Migration, kein neuer Backend-Endpoint — alles aus dem bestehenden `listEntries`/`listTagsForEntry`/`listSymptomsForEntry`-Pfad. Lint 0/0, svelte-check 0/0, alle Vitest-Tests grün (116 → 152, +36 wie geplant). Architektur-Konsistenz: `computeEntryStreak` behält denselben Aufrufpunkt, wenn M2 die Backend-Streak-API liefert; nur die Datenquelle wechselt. Sparkline-Komponente ist als wiederverwendbares M2-Asset für Energy/Stress-Charts vorbereitet.

- **Auto-Save für die Tagesansicht (`/entries/new`) gemäß ADR-0013.** Der bisherige manuelle Submit-Button entfällt; jede semantische Eingabe (Slider, Tags, Symptome, Work-Context, Notiz) markiert das Formular `dirty` und löst nach 800 ms Debounce einen Save aus. Die persistierte State-Maschine (`idle | dirty | saving | saved | error`) wird in einem wiederverwendbaren Controller `apps/web/src/lib/utils/autoSave.ts` gekapselt: bei laufendem Save werden weitere `dirty`-Trigger gepuffert (Re-Flush nach Antwort, kein überlappender POST/PATCH), erfolgreich gespeicherte Stati blenden nach 5 s zurück auf `idle`, Fehler exponieren `lastError` plus expliziten Retry-Pfad. POST→PATCH-Flip bleibt aus PR #117 erhalten: erste Save-Operation eines Tages erzeugt den Eintrag via `submitEntry` (POST) und merkt sich die `existingEntryId`, alle weiteren Saves laufen über `updateEntry` (PATCH) plus die idempotenten Tag-/Symptom-Replace-Set-Endpoints — der 409-Race aus dem Vorgänger-Issue ist damit strukturell ausgeschlossen. Neue Komponente `SaveStatusBadge.svelte` neben der Page-Headline zeigt den Status mit `aria-live="polite"` (Wird in Kürze gespeichert… / Wird gespeichert… / Gespeichert um HH:MM / Fehler beim Speichern + Retry-Button). Ein `beforeunload`-Listener flößt offene Edits noch vor Tab-Close best-effort an den Server und ruft den Browser-Native-Dialog auf, falls Status `dirty` oder `saving` ist. Datumswechsel löst explizit _kein_ Auto-Save aus, sondern nur die bestehende Hydration; während der Hydration werden reaktive Watcher kurz unterbunden, damit das Laden eines Eintrags nicht sofort einen Rücksave triggert. Online-only-Verhalten gemäß ADR-0009 — kein localStorage- oder IndexedDB-Buffer (Offline-Sync bleibt M4); bei `error` bleiben die Felder editierbar und der Retry-Pfad nutzt den aktuellen Snapshot. i18n-Keys ergänzt (DE+EN): `entry.autosave.dirty`, `entry.autosave.saving`, `entry.autosave.saved_at`, `entry.autosave.error`, `entry.autosave.retry`, `entry.autosave.offline`, `entry.autosave.leave_warning`. 14 neue Vitest-Tests in `autoSave.test.ts` decken: Initial-State, Debounce-Window (kein Save vor 800 ms, genau ein Save nach 800 ms, Coalescing mehrerer Edits), Saved→Idle-Fade nach 5 s plus `lastSavedAt`, Re-Flush während `saving` mit gepuffertem zweiten Save, Error-Path mit `lastError`-Surface, manueller Retry, `markDirty`-after-error, `flushNow` ohne Debounce, `reset` cancelt anhängenden Timer, `destroy` blockt späte State-Mutationen. Lint 0/0, svelte-check 0/0, 116/116 Vitest-Tests grün (102 → 116, +14 wie geplant). Submit-Button entfällt; Cancel-Button bleibt und navigiert zurück zu `/` ohne den State zu verwerfen — Auto-Save hat ja bereits persistiert. Keine neue Dependency, keine Backend-Änderung, keine Architektur-Abweichung von DESIGN_DOCUMENT.md.

### Documentation

- **M3 Sprint-/Issue-Status dokumentiert.** Neues Dokument `docs/M3_SPRINT_STATUS.md` trennt den lokalen Mainline-Stand der geschlossenen Sprints 1-6 von den weiterhin offenen GitHub-Issues #151-#159, benennt die naechsten CI-konformen Sprints und haelt die zuletzt ausgefuehrten Backend-/Web-Checks fest.

- **ADR-0013 — Auto-Save für Day-Entries (M1.5)** vorgeschlagen. Wechsel von manuellem Submit auf Hybrid Auto-Save mit sichtbarer Status-Anzeige, 800 ms-Debounce, POST→PATCH-Flip (aus PR #117 wiederverwendet), Last-Write-Wins-Konfliktauflösung (Single-Device-M1-Scope). Offline-Verhalten explizit out-of-scope, bleibt M4 (siehe [ADR-0009](docs/adr/0009-offline-sync-nach-m4.md)). State-Maschine (`idle | dirty | saving | saved | error`) ist offline-erweiterungsfähig. Submit-Button entfällt, Cancel bleibt, `beforeunload`-Listener fängt Tab-Close während `saving` ab. Mit dem Implementierungs-PR auf `Akzeptiert` gehoben. ADR-Datei: `docs/adr/0013-autosave-day-entries.md`.
- **ADR-0014 — Home-Dashboard mit Recent-Entries und 14-Tage-Sparkline (M1.5)** vorgeschlagen. Recent-Entries-Liste (7 Tage, klickbar mit `?date=YYYY-MM-DD`-Param), 7-Tage-Summary (Mood-/Energy-/Stress-Avg + Eintrags-Streak gemäß [ADR-0012](docs/adr/0012-m2-m5-streak-semantik.md)) und 14-Tage-Mood-Sparkline werden von M2 nach M1.5 vorgezogen. Keine neue Dependency: Sparkline ist eigenes SVG (~80 LOC, theme-aware, wiederverwendbar für M2-Charts statt uPlot/Chart.js/ApexCharts). Kein neuer Backend-Endpoint; alles aus dem bestehenden `listEntries`-Pfad. Streak-Berechnung clientseitig in `lib/utils/streak.ts`, in M2 wechselt nur die Datenquelle wenn der Backend-Streak-Endpoint kommt. Anonymous-Landing bleibt unverändert. Implementierungs-PR folgt separat. ADR-Datei: `docs/adr/0014-home-dashboard-recent-entries-sparkline.md`. Status: `Vorgeschlagen`.
- **ADR-0014 auf `Akzeptiert` gehoben.** Status-Übergangsnotiz im ADR-Footer und im Index `docs/adr/README.md` aktualisiert.
- **DESIGN_DOCUMENT.md §6 Roadmap:** neuer **M1.5-Abschnitt** „UX-Pflege Tagesansicht & Home-Dashboard" mit acht Akzeptanzkriterien zwischen M1 und M2 eingefügt. M2 (Visualisierung) wird auf erweiterte Multi-Metric-Charts plus Habit-Schema-Vorgriff gemäß ADR-0012 fokussiert. ADR-Index `docs/adr/README.md` um beide Einträge erweitert.

### Changed

- **No-Gamification-Prep für M3 gestartet (Issue #158).** Die sichtbare Web-Copy für Eintrags-Serien wurde neutral auf `Tracking consistency` / `Tracking-Konsistenz` umgestellt: Home-Summary und Trends-Seite sprechen nicht mehr von Streaks, sondern von Datenkontinuität und ergänzen den Hinweis, dass konsistentere Daten die Insight-Qualität verbessern. Berechnung, Backend-Endpoint und API-Typen bleiben in diesem Sprint unverändert. Neuer Vitest-Regressionscheck stellt sicher, dass Locale-Strings keine Streak-/Reward-/Badge-/Fire-Framings exponieren.

- **`SymptomIcon` in `IconRender` umbenannt (kosmetischer Refactor zu PR #117/#118).** Die in PR #117 eingeführte Komponente klassifiziert beliebige Icon-Strings (Emoji oder Lucide-Slug) und ist nicht symptom-spezifisch — mit der Wiederverwendung im `TagPicker` (PR #118) wurde der Name irreführend. Datei umbenannt: `apps/web/src/lib/components/common/SymptomIcon.svelte` → `IconRender.svelte`, zusammen mit `SymptomIcon.test.ts` → `IconRender.test.ts`. Verwender (`SymptomChecker.svelte`, `TagPicker.svelte`) auf den neuen Namen umgestellt; CSS-Klasse `.symptom-icon-emoji` → `.icon-render-emoji`. Doc-Kommentar aktualisiert (referenziert jetzt `Symptom.icon` und `Tag.icon`). Keine Verhaltensänderung, keine Änderung an der Klassifikations-Logik, keine Backend-Auswirkung. Lint 0/0, typecheck 0/0, 102/102 Vitest-Tests grün.

### Fixed

- **`COOKIE_SECURE` wird in der Dockhand-Compose nun korrekt an alle API-Container durchgereicht (Folge-Fix zum Auth-Cookie-Problem aus PR #115).** Beim Live-Test auf der Synology-Instanz zeigte sich, dass die in PR #115 eingefuehrte Settings-Variable `COOKIE_SECURE` zwar im Backend-Code respektiert wird, aber im Compose-Stack nicht in den Container gelangte: `docker exec correlcore-api env | grep COOKIE_SECURE` lieferte leeren Output, sodass die Auto-Heuristik `APP_ENV=staging` weiterhin auf `Secure=true` schloss und die Cookies vom Browser auf der HTTP-Tailscale-Origin verworfen wurden. Ursache: der gemeinsame YAML-Anchor `&api-env` in `infra/dockhand/compose.yaml` listete `COOKIE_SECURE` nicht auf, sodass die Variable trotz korrektem `.env.example`-Eintrag von `migrate`/`api`/`worker` ignoriert wurde. Fix: `COOKIE_SECURE: ${COOKIE_SECURE:-false}` direkt nach `APP_ENV` im `&api-env`-Anchor ergaenzt (mit Inline-Kommentar zu ADR-0006 und zum HTTP-Tailscale-Default). Damit erscheint die Variable automatisch in allen drei Services, die den Anchor referenzieren. `infra/dockhand/.env.example` enthielt `COOKIE_SECURE=false` bereits (PR #115); kein weiterer Eintrag noetig. Keine Architektur-Abweichung von DESIGN_DOCUMENT.md/ADR-0006/ADR-0011, kein neues ADR.

- **Tag-Chips rendern Lucide-Icons jetzt als SVG statt als Wort (Folge-Fix zu PR #117).** Aus dem produktiven Test gemeldet: nach Merge von PR #117 zeigten zwar die Symptome korrekte Icons, die Tag-Chips in der Tagesansicht (`TagPicker.svelte`) gaben aber weiterhin den Slug als Text aus — z. B. `"dumbbell Krafttraining"`, `"footprints Laufen"`, `"alert-triangle Konflikt"`. Ursache: derselbe Bug wie bei den Symptomen (Icon-String unkonditional in `<span>` gepackt), aber `TagPicker.svelte` wurde im Vorgänger-PR übersehen, weil das Bug-Reporting zunächst nur die Symptom-Auswahlliste nannte. Fix: die in PR #117 eingeführte gemeinsame `SymptomIcon.svelte`-Komponente wird jetzt auch im `TagPicker` verwendet (Emoji- und Lucide-Slug-Klassifikation, Lazy-Import, Caching, stiller Fallback bei Tippfehlern bleiben unverändert). Konsistente Icon-Größe `size=16` matcht das `tag-chip`-Line-Height (kompakter als die 18 px der Symptome). Keine Backend-Änderung, keine neuen i18n-Keys, keine Architektur-Abweichung von DESIGN_DOCUMENT.md. Tag-Erstellung läuft serverseitig via Seed/API (kein Frontend-Form), daher kein zusätzlicher Hilfetext nötig. Komponentenname `SymptomIcon` wurde nicht umbenannt, um den Refactor minimal zu halten — der Name ist nicht symptom-spezifisch im Sinne der Logik (akzeptiert beliebige Icon-Strings); ein Rename in `IconRender` wäre kosmetisch und kann separat erfolgen, falls gewünscht. Lint 0/0, typecheck 0/0, 102/102 Vitest-Tests grün.

- **Symptom-Icons werden jetzt korrekt gerendert statt als Wort ausgeschrieben.** Aus dem produktiven Test gemeldet: in der Symptom-Auswahlliste (`SymptomChecker.svelte`) erschien neben dem Symptomnamen der Icon-Wert als Text — z. B. `"dumbbell krafttraining"` statt SVG-Icon plus Label. Ursache: das Icon-Feld wurde unkonditional in einen `<span>` gepackt; der `Symptom.icon`-Spaltenkommentar in `backend/app/models/tag.py` deklarierte das Feld ausdrücklich als _entweder_ Emoji _oder_ Lucide-Icon-Slug, aber das Frontend hatte keinen Lucide-Pfad. Fix: neue gemeinsame Komponente `apps/web/src/lib/components/common/SymptomIcon.svelte` klassifiziert den Icon-String per zwei eng gefassten Regexes (Emoji = irgendein non-ASCII-Codepoint, Lucide-Slug = `^[a-z][a-z0-9]*(-[a-z0-9]+)*$` mit Länge ≥ 2) und rendert entweder einen Emoji-`<span>` oder via `lucide-svelte/icons/<slug>.svelte` lazy-importiertes SVG. Slugs werden in einer modul-skalierten Map gecacht, sodass Wiederverwendung in der Liste keinen erneuten Chunk-Download auslöst. Bei Treffer-Failure (Tippfehler im Slug, kein passendes Icon) wird _nichts_ gerendert — das umgebende Namens-Label bleibt, das Symptom ist weiter identifizierbar; der ehemalige Wort-Bug ist damit ausgeschlossen. Custom-Form (`SymptomChecker.svelte`) bekommt einen Hilfetext (`symptom.custom.icon_hint`) mit Beispielen (`dumbbell`, `brain`, `heart-pulse`) und Verweis auf [lucide.dev/icons](https://lucide.dev/icons), das Icon-`maxlength` wächst von 8 auf 32 (matcht `String(32)` im Backend), eine Live-Vorschau zeigt das eingegebene Icon im Eingabefeld. Neues Paket: `lucide-svelte@^0.469.0` (~5 KB pro tatsächlich genutztem Icon, tree-shakeable, lazy). 5 neue Vitest-Klassifizierungs-Tests (`SymptomIcon.test.ts`) decken Emojis (Default-Seed + Compound-ZWJ), valide Slugs, Whitespace-Trim und mehrere Klassen kaputter Eingaben (Trailing-Hyphen, Leading-Hyphen, Doppelhyphen, Uppercase, Single-Char, Whitespace-im-String, Underscore). Keine Backend-Änderung nötig (Backend speichert das Feld bereits als opaker String).

- **Tagesansicht hydratisiert sich beim Aufruf eines bereits gespeicherten Tages aus dem bestehenden Eintrag.** Aus dem produktiven Test gemeldet: beim erneuten Aufruf von `/entries/new` mit einem Datum, an dem bereits gespeichert wurde, zeigte das Formular die neutralen Defaults (Mood/Energy/Stress = 3, kein Tag/Symptom/Notiz), sodass ein Update des Tages effektiv unmöglich war — jeder zweite Submit lief mit `409 entry_exists` ins Leere. Fix: neuer reaktiver Loader in `apps/web/src/routes/entries/new/+page.svelte` ruft bei jedem Datumswechsel `listEntries({start_date,end_date,limit:5})` ab, wählt den Eintrag mit `slot=day` und füllt das Formular damit auf; Tags und Symptome werden parallel via `Promise.allSettled` (`listTagsForEntry` / `listSymptomsForEntry`) nachgeladen. Konkurrierende Loads werden über einen monoton steigenden `loadToken` debounced — stale Antworten für ein bereits geändertes Datum werden verworfen, das Formular schnappt nicht zurück. Submit-Flow flippt automatisch: bei vorhandenem `existingEntryId` PATCH über `updateEntry`, sonst weiter POST über `submitEntry`; Tag-/Symptom-Assignment läuft in beiden Pfaden über dieselben Replace-Set-Endpoints (PUT, idempotent). Header zeigt im Edit-Modus einen sichtbaren Hinweis (`entry.edit_hint`) plus testid `entry-edit-hint`, der Submit-Button wechselt zu `entry.update`/"Aktualisieren". `aria-busy="true"` und `data-loading="true"` während des Ladens, das Formular wird visuell + klick-blockiert (kein Submit auf inkonsistentem State). Work-Context-Defaults werden im Edit-Modus respektiert (Auto-Heuristik per Wochentag bleibt nur für neue Tage aktiv). Fehler beim Lade-Pfad sind nicht-fatal: das Formular fällt auf neutrale Defaults zurück und zeigt `entry.error_load`; Speichern bleibt möglich. i18n-Keys ergaenzt: `entry.edit_hint`, `entry.update`, `entry.error_load` (DE+EN). Lint 0/0, typecheck 0/0, 102/102 Vitest-Tests grün.

- **Auth-Cookies werden bei HTTP-Origins (Tailscale-IP / Homelab ohne TLS) jetzt korrekt gesetzt.** Aus dem produktiven Test gemeldet: nach Login lieferte das Speichern in der Tagesansicht die Meldung "Bitte melde dich erneut an" und Custom-Symptome konnten nicht angelegt werden. Beide Pfade mündeten in einem 401, weil der Browser das `Set-Cookie` der Login-Antwort verwarf — DevTools-Application-Tab zeigte zur Bestätigung _keine_ `access_token`/`refresh_token`-Cookies für die Origin `http://100.120.157.82:3010`. Root-Cause: `backend/app/core/auth_cookies.py` setzte `secure=True` hartkodiert; gemäß RFC 6265bis §4.1.2.5 verwirft jeder Browser `Secure`-Cookies bei HTTP-Schemes (Tailscale-IPs zählen _nicht_ als Secure-Context). Fix: neue Settings-Variable `COOKIE_SECURE: bool | None = None` mit Auto-Heuristik (`None` → `False` für `APP_ENV=development`, `True` sonst) und Property `Settings.cookie_secure_effective`; `set_auth_cookies` nutzt diesen Wert statt hartkodiertem `True`. Operatoren von HTTP-only Staging-/Homelab-Setups setzen explizit `COOKIE_SECURE=false` in der `.env`. ADR-0006 wird gewahrt: ein Model-Validator verweigert `COOKIE_SECURE=false` in `APP_ENV=production` mit klarer Fehlermeldung. `infra/dockhand/.env.example` setzt `COOKIE_SECURE=false` mit Begründung (Tailscale ohne TLS), `infra/docker/.env.example` dokumentiert die Variable als optionalen Override. ADR-0006 erhält eine _Implementation-Notiz_ zum Fix mit RFC-Verweis und Querverweis auf ADR-0011. Neue Tests: 12 Settings-Regression-Tests in `tests/test_settings_cookie_secure.py` (Auto-Heuristik pro APP_ENV, expliziter Override, Production-Guard, Boolean-Parsing-Edge-Cases) und 3 Unit-Tests in `tests/test_auth_cookies.py`, die direkt auf `Set-Cookie`-Header-Bytes prüfen (Secure raus in Dev, Secure rein bei Override, Path-konsistente `clear_auth_cookies`). Backend-Quality-Gate: 306/306 Tests grün (ohne Crypto-Trio das ohnehin lokal `ENCRYPTION_KEY`-ENV erwartet), Coverage 95.96 %, ruff/format/mypy clean. Bug 2 ("Symptom konnte nicht angelegt werden") implizit mitgefixt — derselbe 401-Pfad.

- **Theme-Toggle (Hell/Dunkel) jetzt auch in der Tagesansicht (`/entries/new`) sichtbar.** Aus dem produktiven Test nach PR #112-Merge gemeldet: in der Tagesansicht fehlte der Toggle, sodass das Erfassen eines Eintrags zwingend im aktiven Theme erfolgen musste — bisher war der Toggle nur auf Home und im Auth-Layout vorhanden. Refactoring: gemeinsame `ThemeToggle.svelte`-Komponente unter `apps/web/src/lib/components/common/ThemeToggle.svelte` extrahiert (zwei Varianten via `withLabel`-Prop: Icon+Label für Home/Tagesansicht, Icon-only für Auth-Header). Drei Verwender umgestellt: `apps/web/src/routes/+page.svelte` (authenticated home + anonymous landing), `apps/web/src/routes/auth/+layout.svelte` und neu `apps/web/src/routes/entries/new/+page.svelte`. Code-Duplizierung (~110 Zeilen Inline-SVG ✕ 3 Stellen) eliminiert; i18n-Keys `theme.toggle_light` / `theme.toggle_dark` unverändert. Keine Architektur-Abweichung von DESIGN_DOCUMENT.md, kein ADR nötig. Lint 0/0, typecheck 0/0, 97/97 Vitest-Tests grün.

### Added

- **Interner Reverse-Proxy im Web-Container (ADR-0011, dauerhafte Lösung des Vite-Build-Time-Kopplungsproblems).** Neuer SvelteKit-`handle`-Hook in `apps/web/src/hooks.server.ts` leitet jeden Request mit Pfad `/api/*` zur Laufzeit an `INTERNAL_API_URL` (Default `http://api:8000`) weiter — inklusive Method, Headers, Body, Query-String und vollständiger `Set-Cookie`-Behandlung (mehrere Cookies bleiben separate Header-Lines via `getSetCookie()`-Lift, Hop-by-Hop-Header werden gemäß RFC 7230 §6.1 entfernt, `Host`-Header wird auf den Upstream-Host gesetzt). Bei Upstream-Verbindungsfehler wird ein JSON-`502 {"detail":"Upstream API unreachable"}` zurückgegeben, sodass `apiFetch` weiterhin strukturiert parsen kann. Vollständig getestet (9 neue Vitest-Tests in `hooks.server.test.ts` decken: Pass-Through für Nicht-API-Pfade, GET/POST mit Query und JSON-Body, `INTERNAL_API_URL`-Override mit Trailing-Slash-Strip, Hop-by-Hop-Stripping, Set-Cookie-Forwarding mit Multi-Cookie, 502 bei Upstream-Failure, Status-Code-Forwarding für 4xx/5xx).

### Changed

- **`VITE_API_BASE_URL` ist nun fest auf `/api/v1` gepinnt; pro Topologie wird stattdessen die Runtime-ENV `INTERNAL_API_URL` am Web-Container gesetzt.** Konsequenz aus ADR-0011: ein Image funktioniert in jeder Topologie, kein Rebuild bei IP-/Port-Wechsel mehr nötig. Der `workflow_dispatch`-Input `vite_api_base_url` ist aus `.github/workflows/release-images.yml` entfernt; der Build-Arg-Default im Workflow ist hartkodiert auf `/api/v1`. `apps/web/Dockerfile` enthält einen Kommentar, der die neue Topologie und `INTERNAL_API_URL` referenziert. ADR-0011 ist von `Vorgeschlagen` auf `Accepted` (2026-05-08) hochgesetzt.
- **API-Container kann nun ohne Host-Port-Mapping deployed werden.** Mit dem internen Proxy ist der API-Container nur noch über das Docker-Netzwerk erreichbar; `expose: ["8000"]` reicht, kein `ports:` mehr nötig (Sicherheitsplus, schließt Direkt-Zugriff auf API von außerhalb).

### Documentation

- **`docs/RUNBOOK_DEPLOYMENT.md` §7 vollständig neu geschrieben** („Frontend 404 bei `/api/v1/...`: dauerhaft gelöst durch ADR-0011"). Dokumentiert die historische Ursache (Build-Time-Konstante + Auto-`:latest`-Build), die jetzige Architektur (`hooks.server.ts`-Proxy, `INTERNAL_API_URL`-ENV) und liefert Verifikations-`curl`, Compose-Beispiel mit `expose:` statt `ports:`, sowie Verweise auf ADR-0011 und ADR-0006. Die Quick-Reference-Tabelle hat einen neuen 502-Eintrag (Web-Container kann API nicht erreichen) und der bestehende 404-Eintrag wurde auf den neuen Sofort-Check (`docker compose exec web env | grep INTERNAL_API_URL`) umgeschrieben.
- **ADR-Index (`docs/adr/README.md`) aktualisiert.** ADR-0011 in der Statustabelle auf `Accepted` (2026-05-08); Kurzübersicht erweitert um Implementierungs-Hinweis (~140 Zeilen TS inkl. Hop-by-Hop- und Set-Cookie-Behandlung) und um die Konsequenz, dass `vite_api_base_url`-Input entfernt und `VITE_API_BASE_URL` fix `/api/v1` ist.
- **Dockhand-Stack-Doku auf ADR-0011 ausgerichtet (`infra/dockhand/`).** `compose.yaml`: API-Service hat kein `ports:`-Mapping mehr, sondern nur noch `expose: ["8000"]` — die API ist ausschließlich über das interne Compose-Netz unter `http://api:8000` erreichbar; Web-Service `environment:` enthält `VITE_API_BASE_URL` nicht mehr und dokumentiert `INTERNAL_API_URL` als optionalen Override. Header-Kommentar erweitert um ADR-0011-Verweis und neue Topologie. `.env.example`: Block `Host-Ports` umbenannt auf `Host-Port (nur Web)` mit Erklärung, dass `API_HOST_PORT` und `VITE_API_BASE_URL` obsolet sind und gelöscht werden können; verbliebene Variable ist `WEB_HOST_PORT`. `README.md`: Variablen-Tabelle ersetzt `VITE_API_BASE_URL`-Zeile durch `INTERNAL_API_URL` (Default `http://api:8000`); Tailscale-Bind-Tabelle entfernt die API-Host-Port-Zeile und ersetzt sie durch `kein Host-Port` mit Erklärung der einzigen externen Origin (Web); Konflikt-Abschnitt fokussiert nur noch `WEB_HOST_PORT` mit Hinweis auf `FRONTEND_BASE_URL`-Nachzug. Hinweis auf alte `.env`-Dateien hinzugefügt: `API_HOST_PORT`/`VITE_API_BASE_URL`-Reste werden ignoriert, stören aber nicht. **Scope bewusst nur Dockhand** (User-aktiver Stack); `infra/dockge/` und `infra/docker/` bleiben in dieser PR unberührt und werden als Folge-Aufgabe getrackt, falls dort relevant.

### Documentation

- **ADR-0012 (Vorgeschlagen) — M2/M5 Streak-Semantik + Habit-Schema-Vorgriff** (`docs/adr/0012-m2-m5-streak-semantik.md`). Löst die im Design-Doc unsaubere Abgrenzung zwischen M2 (Visualisierung) und M5 (Habits & Ziele) auf. M2 liefert ausschließlich **Eintrags-Streaks** (aufeinanderfolgende Tage mit Eintrag, ohne Habit-Semantik) und Tag-Frequenz-Heatmap; M5 liefert **Habit-Streaks** (zielbezogen via `habit_type` + `target_frequency`) und das Habit-Dashboard. Begriffe „Eintrags-Streak" und „Habit-Streak" werden kanonisch. Schema-Vorgriff in M2: `tags`-Tabelle erhält zwei nullable Spalten (`habit_type`, Default `'none'`; `target_frequency`, nullable) inkl. CHECK-Constraints — API/UI/Streak-Logik bleiben M5-Lieferung. Vermeidet Daten-Backfill in M5. `docs/DESIGN_DOCUMENT.md` §2.3 erhält einen Verweis auf ADR-0012; M2-Akzeptanzkriterium präzisiert auf „Eintrags-Streak-Berechnung", M5-Akzeptanzkriterium auf „Habit-Streak-Reset-Logik". `docs/adr/README.md` Index + Kurzübersicht erweitert.

### Status

- **Stand 2026-05-07: M1 ist review-bereit.** Alle 8 Quality-Gate-Tail-Issues (#64–#71) sind als PRs #102–#106 (plus Vorgänger) gemerged, alle 12 protokollierten Findings (CQR-1..6, SA-1..6 aus `docs/quality/M1_QUALITY_GATE.md`) sind geschlossen, der Quality-Gate-Report selbst ist von „bestanden mit Auflagen“ auf „vollständig bestanden“ aktualisiert. **Final-State-Verifikation:** 288 Backend-Tests grün, projektweite Coverage **96.11 %** (Threshold: 70 %), `ruff check` / `ruff format --check` / `mypy --strict app` clean, alle 8 CI-Checks (Build, Format, Lint, Tests, Migrations × 2, Typecheck × 2) auf `main` grün. `docs/DESIGN_DOCUMENT.md` ist auf Version **0.10** mit M1-Review-Bereit-Vermerk gehoben, der M1-Checkpoint dort vollständig auf `[x]` gesetzt; `README.md` M1-Roadmap-Eintrag auf `[x]`; `docs/ARCHITECTURE.md` Encryption-Zeile (App-Level Fernet pro User-DEK statt `pgcrypto`-Heuristik) und Auth-Zeile (Native JWT Phase 1 M1 ✅ / OIDC Phase 2 M12+) konsolidiert. ADR-Index (`docs/adr/README.md`) führt 0001–0011 inkl. ADR-0010 (Build-Toolchain-Pinning) und ADR-0011 (Web-internal Reverse-Proxy, Status `Vorgeschlagen`, Umsetzung in M2). Empfohlener Folgepfad nach Review-Merge: M2-Visualisierung (#11 Mood-Zeitreihe → #13 Streak-Widgets → #12 Tag-Frequenz-Heatmap), parallel #14/#30 CSV/JSON-Export (DSGVO Art. 20) und #101 Auto-Cleanup unverified Accounts.

### Changed

- **M1-Review-Empfehlungen nachgezogen:** ausführbares Quality-Gate ergänzt (`pnpm quality:m1`, `scripts/quality-gate-m1.sh`, `backend/scripts/check.sh`) und Backend-Checks auf Python 3.12 gepinnt (`backend/.python-version`). Auth-Cookie-Namen, Pfade und Security-Attribute wurden in `backend/app/core/auth_cookies.py` zentralisiert, sodass Login/Refresh/Logout und DSGVO-Account-Delete nicht mehr separat gepflegte Cookie-Pfade besitzen. Stale M1-Kommentare zu Plaintext-Encryption, Offline-Sync und Lifespan-TODOs wurden bereinigt; `docs/quality/M1_QUALITY_GATE.md` dokumentiert den ausführbaren Gate-Pfad und den weiterhin expliziten RLS-Enforcement-Follow-up.

- **`@sveltejs/vite-plugin-svelte` auf `^4.0.0` (resolved zu `4.0.4`) angehoben** (CQR-6 aus `docs/quality/M1_QUALITY_GATE.md`, Issue #71). Das M1-Quality-Gate hatte protokolliert, dass `apps/web` mit `svelte@^5.0.0` aber `vite-plugin-svelte@3.x` lief — das Plugin warnte bei jedem `pnpm lint`/`pnpm build` viermal mit `You are using Svelte 5.55.5 with vite-plugin-svelte@3. Active Svelte 5 support has moved to vite-plugin-svelte@4.`. Funktional kein Fehler (svelte-check 0/0, Lint 0/0), aber Lint-Output wurde verrauscht und Bugfixes/Features kommen nur noch über v4. Update auf v4.0.4 (latest stable v4) gewählt, **nicht** v5/v6: v5 setzt `vite ^6.0.0` voraus, v6 setzt `vite ^6.3 || ^7` voraus — beide würden einen Vite-Major-Bump erzwingen, der nicht zum Scope von #71 gehört (separates Tracking). v4.0.4 verlangt `vite ^5.0.0` und `svelte ^5` — beides bereits erfüllt (`vite@5.4.21`, `svelte@5.55.5`). Side-Effect des Plugin-Updates: `@sveltejs/vite-plugin-svelte-inspector` zog von `2.1.0` auf `3.0.1` mit (transitive devDependency, nicht direkt referenziert), `pnpm-lock.yaml` reduziert um die alten `vite-plugin-svelte@3`-Einträge. Plugin-Warning verschwindet aus `pnpm build`/`pnpm lint`/`pnpm typecheck`-Output (verifiziert: `pnpm build 2>&1 | grep vite-plugin-svelte` liefert keinen Treffer mehr). Kein Code-Change in `vite.config.js`/`svelte.config.js` nötig — die `svelte()`-Plugin-API ist zwischen v3 und v4 abwärtskompatibel für unsere Konfiguration (kein Pre-Process-Inspector, keine Hot-Hooks, keine `kit`-Plugin-Optionen außerhalb von SvelteKit selbst). Quality-Gate komplett: typecheck 0/0, lint 0/0, build erfolgreich (4.29s), `pnpm audit --prod` clean.

- **`release-images.yml`: `VITE_API_BASE_URL` als `workflow_dispatch`-Input parametrisierbar.** Bisher war der Build-Arg im Workflow auf den relativen Default `/api/v1` hardcoded — dieser Wert ist Build-Time-konstant in das JS-Bundle einkompiliert und funktioniert nur in Setups mit Reverse-Proxy, der `/api/*` an den API-Container weiterleitet. Im user-test/Dockhand-Setup mit direktem Host-Port-Mapping (Web=3010, API=8210) sendet der Browser API-Calls an den Web-Port (`POST http://<host>:3010/api/v1/auth/register`), der nur Static-Files serviert → 404 bei jeder Aktion (Symptom: „Registrierung scheitert“, API-Log zeigt keinen POST). Fix: Workflow erweitert um einen `workflow_dispatch`-Input `vite_api_base_url` (Default `/api/v1`, optional absolut z. B. `http://100.120.157.82:8210/api/v1`), der via `${{ github.event.inputs.vite_api_base_url || '/api/v1' }}` als `build-arg` an den Web-Build durchgereicht wird. Push- und Tag-Builds bleiben unverändert beim Default. Für proxylose Topologien wird das Image manuell via `gh workflow run release-images.yml -R Sturmi77/correlcore --ref main -f vite_api_base_url=...` neu gebaut. Caveat dokumentiert: Bundle ist an die im Input angegebene URL gekoppelt (IP-/Port-Wechsel = Rebuild). Architektonisch saubere Lösung (interner Reverse-Proxy im Web-Container) ist als ADR-0011 vorgesehen. Runbook `docs/RUNBOOK_DEPLOYMENT.md` §7 mit Symptom, Ursache, Fix-Snippet und Lehre ergänzt; Quick-Reference-Tabelle bekam eine neue Zeile.
- **Dockhand-Compose: `pull_policy: always` auf den Anwendungs-Services.** Die ursprüngliche Annahme (Dockhand managt Image-Pulls selbst, Re-pull-Button im UI reicht) hielt sich in der Praxis nicht: nach Merge eines Hotfix-Images zog Dockhand das alte gecachte Image weiter, auch nach simplem Redeploy — erst der explizite „Re-pull images“-Klick aktualisierte. Für ein „latest“-Setup im Homelab ist das eine Reibung, die wir wegoperieren wollen. `pull_policy: always` jetzt gesetzt auf den `x-api-image`-YAML-Anchor (deckt damit `migrate`, `api` und `worker` per `<<: *api-image` ab) sowie auf den eigenständigen `web:`-Service. **Bewusst nicht** auf `postgres`, `redis` und `mailpit`: diese laufen auf gepinnten Versions-Tags (`postgres:16.4-alpine`, `redis:7.4-alpine`, `axllent/mailpit:v1.21`) und sollen sich nicht ungewollt aktualisieren. `infra/dockhand/README.md` aktualisiert: Update-Callout neu formuliert (Re-pull entfällt bei `:latest`-Setup), Vergleichstabelle Spalte `pull_policy` geändert auf `always (api/migrate/worker/web)`, Warnhinweis hinzugefügt zur Mischung mit `:latest` (kaputtes main-Image propagiert sofort — für Production lieber `IMAGE_TAG=vX.Y.Z` pinnen). Dockge- und user-test-Compose unverändert (hatten bereits `pull_policy: always`).
- **Build-Toolchain: pnpm-Version explizit auf 11.0.8 gepinnt** (siehe [ADR-0010](docs/adr/0010-build-toolchain-pinning.md)). `pnpm/action-setup@v4 version: 'latest'` zog je nach Tag pnpm 10.x oder 11.x, was wiederholt zu Drift in der `pnpm-workspace.yaml`-Konfiguration führte (`onlyBuiltDependencies` in v10 vs. `allowBuilds` in v11) und reproduzierbar `ERR_PNPM_IGNORED_BUILDS` auf Branches ohne Cache-Hit auslöste. Drei kombinierte Änderungen: (1) `packageManager: "pnpm@11.0.8"` als Single-Source-of-Truth in der Root-`package.json` (wird von Corepack im Web-Dockerfile gelesen), (2) `version: '11.0.8'` in allen vier `pnpm/action-setup`-Steps in `.github/workflows/ci-web.yml` (Action hätte sonst Vorrang vor `packageManager`), (3) `engines.pnpm: ">=11.0.0"` für lokale Setups ohne Corepack. `pnpm-workspace.yaml` wurde auf reine v11-Syntax bereinigt (`onlyBuiltDependencies` entfernt, nur noch `allowBuilds`-Map). CI- und Image-Toolchain liefern jetzt deterministisch dasselbe Ergebnis unabhängig vom Tag oder Cache-Status.

### Documentation

- **Neuer ADR-Eintrag [ADR-0011](docs/adr/0011-web-internal-reverse-proxy.md): Interner Reverse-Proxy im Web-Container** (Status `Vorgeschlagen`, Umsetzung in M2). Adressiert die strukturelle Schwäche, die PR #92 nur taktisch gelöst hat: `VITE_API_BASE_URL` ist Build-Time-konstant, deshalb ist das aktuelle `:latest`-Bundle an die im Workflow-Input angegebene Tailscale-IP+Port-Kombination gekoppelt und API-Port muss extern gemappt sein. Der ADR schlägt vor, in M2 einen SvelteKit-`hooks.server.ts`-Handle-Hook einzuziehen, der `/api/*` intern an `http://api:8000/*` weiterleitet. Damit wird `:latest` topologie-agnostisch (Default `/api/v1` bleibt in allen Setups korrekt), API-Port kann auf `expose:` zurückgenommen werden (Sicherheitsplus, kein direktes Tailnet-Exposure mehr), und Cookie-Auth (ADR-0006) profitiert durch Same-Origin (kein `SameSite=None`-Workaround mehr nötig). Drei Varianten gegenübergestellt (Sidecar-nginx, Handle-Hook, Caddy-in-Image), Variante B (Handle-Hook, ~40 Zeilen TS, kein zusätzlicher Container) gewählt. Umsetzungsplan mit sieben Schritten (Hook, Dockerfile-ENV, Compose-`expose`, Healthcheck-Erweiterung, Playwright-Smoke, Runbook-Update) im ADR; `workflow_dispatch`-Input bleibt als Escape-Hatch für lokale Web-Dev-Setups erhalten. ADR-Index und Kurzübersicht in `docs/adr/README.md` aktualisiert. RUNBOOK §7 mit Cross-Ref auf ADR-0011 und Verifikations-Note (Registrierung end-to-end produktiv getestet am 2026-05-07) ergänzt.
- **Neues Runbook `docs/RUNBOOK_DEPLOYMENT.md`** mit den drei Erkenntnissen aus dem ersten User-Test-Deployment: (1) `backend/Dockerfile` braucht `COPY app/ app/` vor dem editable Install, sonst bricht `correlcore-migrate` mit `ModuleNotFoundError: No module named 'app'` ab — Hatchling-Editable-Installs erfordern Package-Source zur Build-Zeit; (2) Synology+Tailscale läuft im Userspace-Networking-Modus, weshalb `TAILSCALE_IP=0.0.0.0` (statt der eigentlichen Tailscale-IP) gebunden werden muss — die IP existiert nicht auf einem Kernel-Interface, und Linux-Bind läuft auf `cannot assign requested address`; (3) pnpm-Build-Scripts brechen auf frischen Branches mit `ERR_PNPM_IGNORED_BUILDS` ab, Fix über Pin auf 11.0.8 + `allowBuilds`-Map. Erste-Hilfe-Tabelle, Image-Pull-Verifikations-Snippet, Cross-Refs zu ADR-0010, `infra/dockhand/README.md`, `infra/docker/README.user-test.md` und CHANGELOG.
- **Neuer ADR-Eintrag [ADR-0010](docs/adr/0010-build-toolchain-pinning.md)** dokumentiert die Pinning-Entscheidung mit Update-Pfad (Patch-Update via `corepack use pnpm@<version>` plus Workflow-Edit; Major-Updates erfordern zusätzlich `pnpm-workspace.yaml`-Settings-Review). Verworfene Alternativen festgehalten: nur `packageManager` ohne Workflow-Pin (greift halb), Range-Pin (re-introduziert Drift), pnpm-10-Pin (kein offizielles LTS, EOL-Risiko ab Q3 2026).
- **`docs/DESIGN_DOCUMENT.md` Version 0.9:** Cross-Refs zum neuen Runbook und ADR-0010 in der Header-Zeile, Datum auf 2026-05-07 gehoben.
- **`docs/adr/README.md`** Index- und Kurzübersicht-Eintrag für ADR-0010 ergänzt.

### Security

- **`esbuild`-Advisory `GHSA-67mh-4wv8-2f99` (moderate) durch `pnpm-overrides` auf `^0.25.0` gepatcht** (SA-6 aus `docs/quality/M1_QUALITY_GATE.md`, Issue #69). Im M1-Quality-Gate hatte `pnpm audit --prod` eine moderate Advisory gemeldet: esbuild ≤ 0.24.2 erlaubt jeder beliebigen Website, Requests an den lokalen esbuild-Dev-Server zu senden und Antworten zu lesen — relevant nur für Dev-Setups, in Production-Bundles unbeteiligt, daher in M1 als nicht-blockierend eingestuft. Die Advisory traf uns über zwei transitive Pfade: `svelte-i18n@4.0.1` ist seit allen 4.x-Versionen auf `esbuild ^0.19.2` festgenagelt (`pnpm up svelte-i18n` bringt nichts), zusätzlich zieht `vite@5.4.21` esbuild 0.21.5 — beide Versionen vulnerable. Ein Range-Override im Manifest ist deshalb der einzige praktikable Weg ohne Major-Bumps von svelte-i18n oder vite. Fix: neuer `overrides:`-Block in `pnpm-workspace.yaml` (pnpm 11+ liest Overrides ausschließlich aus dem Workspace-File, nicht mehr aus `package.json`-`pnpm.overrides` wie unter pnpm 10.x — der ursprünglich an `package.json` angebrachte Block griff bei Re-Installs nicht). Pin auf `^0.25.0` (nicht `>=0.25.0`): esbuild 0.28+ enthält Breaking-Changes beim Transpilieren von Object-Spread-Destructuring für die SvelteKit-Default-Browser-Targets `chrome87/edge88/firefox78/safari14` (Build bricht mit `Transforming destructuring to the configured target environment is not supported yet`); 0.25.x patched die Advisory laut [Release-Notes 0.25.0](https://github.com/evanw/esbuild/releases/tag/v0.25.0) und ist API-stabil. Resultat lokal verifiziert: `pnpm why esbuild` zeigt nur noch `esbuild@0.25.12` (eine Version, dedupliziert über alle Konsumenten); `pnpm audit --prod` meldet `No known vulnerabilities found`; Quality-Gate (Typecheck, Lint, Build) durchgehend grün. Inline-Kommentar im `pnpm-workspace.yaml` dokumentiert Pin-Begründung und Verweis auf SA-6/Issue #69 für künftige Toolchain-Upgrades. Nicht abgedeckt durch Issue #69 und beim erneuten Audit-Lauf neu sichtbar geworden: `vite` Advisory `GHSA-4w7w-66w2-5vf9` (moderate) und `cookie` Advisory `GHSA-pxg6-pf52-xh8x` (low) — beide außerhalb des SA-6-Scopes, werden in separaten Folge-Issues nachgezogen (vite-Update überlappt mit Issue #71 für `vite-plugin-svelte` v3→v4).

### Fixed

- **Web: i18n-Race-Condition — Slot erst rendern, wenn `svelte-i18n` geladen ist** (Web-Bug, nach PR #99 weiterhin `[svelte-i18n] Cannot format a message without first setting the initial locale` auf der Synology). Nachdem PR #99 die Asset-404s behoben hatte, lieferte das HTML alle Chunks korrekt aus, die Browser-Console zeigte aber weiterhin denselben i18n-Error und alle Auth-Seiten rendern leer. Ursache: `svelte-i18n`s `init()` registriert die Locale-Dictionary **asynchron** (`register('de', () => import('./locales/de.json'))`), und `+layout.svelte` rief `setupI18n()` zwar synchron auf, **awaitete** aber nicht den Load. Bei Svelte-5-Reaktivitätsreihenfolge auf bestimmten Routen (`/auth/login`, `/auth/verify-email`, `/auth/register`) feuert das `$_(...)` der Page-Component, bevor das Layout-Setup-Promise resolved — erstes Format wirft, der Render-Tree bricht ab, der Slot bleibt leer. Auf `/` lief es zufällig durch, weil dort kein `$_(...)` vor dem Layout-Mount liegt. Fix: `isLoading`-Store aus `svelte-i18n` in `+layout.svelte` importieren und den `<slot />` hinter ein `{#if $isLoading} … {:else}`-Gate stellen — erst wenn die aktive Locale geladen ist, mounten Children. Während des Loads wird der bestehende `auth-splash`-Block (sr-only) wiederverwendet. Auswirkung minimal sichtbar, weil Locale-Files Teil des initialen Bundle-Loads sind und in der Praxis innerhalb desselben Frames landen.
- **Web: Absolute Asset-Pfade erzwingen — `kit.paths.relative: false` in `apps/web/svelte.config.js`** (Web-Bug, beim Klick auf den Email-Verifikations-Link auf der Synology aufgetaucht). Symptom: `/auth/verify-email?token=...` rendert eine komplett leere Seite, gleich nach Page-Load wirft die Browser-Console `Uncaught (in promise) Error: [svelte-i18n] Cannot format a message without first setting the initial locale`. Auch `/auth/login` und `/auth/register` waren betroffen, nur die Root-Route `/` lief zufällig korrekt. Ursache: SvelteKit 2.x setzt `paths.relative: true` als Default — der vom adapter-node-Server gerenderte HTML-Index referenziert Assets als `../_app/immutable/...` (Parent-Directory-relativ). Auf Root (`/`) löst der Browser das zu `/_app/immutable/...` auf, das passt. Auf einer Sub-Route wie `/auth/login` wird `..` aber ein Verzeichnis tief aufgelöst, ergibt `/auth/_app/immutable/...` — jeder JS-Chunk und jedes CSS-Asset liefert 404. Die Folge: kein i18n-Bundle wird geladen, deshalb wirft das erste `$_('auth.verify.title')` aus `+layout.svelte`/`+page.svelte`, der Render bricht ab, die `<slot>`-Children im Auth-Layout bleiben unsichtbar, das User-sichtbare Resultat ist eine weiße Seite ohne Layout-Header. Browser-Cache und Service-Worker waren nicht beteiligt: `curl http://localhost:3010/auth/login` direkt am Container zeigt im HTML-Body `<link href="../_app/immutable/assets/0.CjaDVzbb.css" rel="stylesheet">` und Modulepreload-Einträge mit demselben `..`-Präfix — das ist die kanonische Server-Antwort, nicht ein zwischengelagertes Cache-Artefakt. Fix: `kit.paths.relative: false` explizit in `apps/web/svelte.config.js` gesetzt; SvelteKit generiert jetzt absolute `/`-Pfade, die unabhängig von der aktuellen URL auflösen. Inline-Kommentar im Config-File erklärt das Default-Verhalten und warum es für SPA-Mode (`ssr=false`) systematisch bricht. Image-Rebuild via `release-images.yml` erforderlich.
- **Dockhand/Dockge/user-test: `FRONTEND_BASE_URL` aus `.env` an API-Container durchreichen + `.env.example`-Dokumentation** (Deployment-Bug, beim Email-Verifikations-Test auf der Synology aufgetaucht). Symptom: Verifikations-Mails enthielten Links auf `http://localhost:5173/auth/verify-email?token=...` (Vite-Dev-Default), nicht auf den extern erreichbaren Web-URL `http://<tailscale-ip>:<web-port>` — User konnte den Link nicht klicken. Ursache: `Settings.FRONTEND_BASE_URL` (`backend/app/core/config.py`) hat den Vite-Dev-Default `http://localhost:5173` und wird vom `EmailService.build_verify_url` als Präfix verwendet, wurde aber von keinem der drei Compose-Anchor (`x-api-env` in `infra/dockhand/compose.yaml`, `infra/dockge/compose.yaml`, `infra/docker/docker-compose.user-test.yml`) an den Container durchgereicht — selbst wenn man die Variable in `.env` gesetzt hatte, kam sie nie im API-Container an. Zusätzlich fehlte ein Eintrag in allen drei `.env.example`-Templates, sodass User den Bug nur bei direkter Code-Lektüre des Backend-Configs erahnen konnten. Fix: (1) `FRONTEND_BASE_URL: ${FRONTEND_BASE_URL:-http://localhost:5173}` in den `x-api-env`-Anchor aller drei Compose-Files ergänzt (gilt damit für `migrate`, `api` und Worker per `<<: *api-env`); (2) `.env.example` aller drei Stack-Varianten bekommt einen neuen Block mit Erklärung, Default-Format `http://${TAILSCALE_IP}:${WEB_HOST_PORT}`, konkretes Beispiel für Tailscale-Setups; Default-Wert auf `http://localhost:3010` umgestellt (matcht den `WEB_HOST_PORT`-Default aus PR #90), damit Quick-Start ohne weitere Anpassung lokal-erreichbare Mail-Links produziert. Bug-Klasse identisch zu PR #92 (Topologie-Coupling von Build-/Runtime-URLs), siehe ADR-0011 — strukturelle Lösung via internem Reverse-Proxy weiterhin in M2.
- **Theme-Toggle reagiert wieder — `[data-theme]`-Selektoren in `app.css` und stabiler Bootstrap in `app.html`** (UX-Bug, beim Post-Registration-Test aufgefallen). Symptom: Klick auf den Light/Dark-Button schreibt zwar wie vorgesehen `data-theme="light"`/`"dark"` auf `<html>`, sichtbar änderte sich aber nichts. Ursache: `apps/web/src/app.css` enthielt **null** `[data-theme]`-Selektoren — das Attribut war reine Dead-Air. Zusätzlich setzte `app.html` initial `data-theme="skeleton"` (Legacy aus der verworfenen Skeleton-UI-Phase), was vom Store (`getInitial()` akzeptiert nur `light|dark`) ignoriert wurde, also fiel der initiale Render auf `prefers-color-scheme` zurück und konnte vom persistierten `localStorage`-Wert abweichen → Flash of Wrong Theme. Fix: (1) `app.css` bekommt zwei Token-Blöcke `:root, [data-theme="dark"]` und `[data-theme="light"]` mit semantischen CSS-Variablen (`--color-bg`, `--color-fg`, `--color-surface`, `--color-surface-2`, `--color-muted`, `--color-border` plus `--color-success/warning/error`), `body` rendert jetzt `background: var(--color-bg)` mit weicher Transition; `.card` nutzt die neuen Tokens statt der alten `Canvas`-Heuristik; `color-scheme` korrekt gesetzt (Form-Controls/Scrollbars folgen). (2) `app.html` initialisiert auf `data-theme="dark"` (matcht `theme.ts`-Store-Default) und enthält einen winzigen Inline-Bootstrap-`<script>`, der vor First Paint `localStorage.getItem('correlcore-theme')` liest und `data-theme` setzt — verhindert FOWT, scheitert silent in sandboxed Iframes. (3) `+layout.svelte` `onMount` mirror weiterhin den persistierten Wert in den Store (für Toggle-Konsumenten); Kommentar von "Skeleton UI" auf "CSS variables in app.css" aktualisiert. **`bg-surface-900` Tailwind-Class auf `<body>` entfernt** (Tailwind v4 ohne Skeleton-Plugin löst diese nicht mehr auf, war seit Skeleton-Removal toter Code).
- **Auth: Login mit unbestätigter E-Mail wird jetzt mit HTTP 403 abgelehnt** (Security/UX-Bug, beim Post-Registration-Test auf der Synology aufgefallen). `login_user()` in `backend/app/services/auth_service.py` prüfte bislang nur `is_active`, nicht `is_verified` — ein User konnte sich also direkt nach `register` ohne Klick auf den Verifizierungslink anmelden, obwohl der Verify-Flow existiert und das Frontend (`apps/web/src/lib/i18n/messages.ts`) bereits einen Mapping-Eintrag `auth.login.error_unverified` für HTTP 403 vorhält. Backend lieferte das 403 nie, also griff der Eintrag nie. Fix: Neue Exception-Klasse `EmailNotVerifiedError(AuthError)` in `auth_service.py`; `login_user()` raised sie nach dem `is_active`-Check, falls `is_verified is False`. Endpoint `backend/app/api/v1/endpoints/auth.py` fängt `EmailNotVerifiedError` _vor_ dem generischen `AuthError`-Handler ab und mappt auf `HTTP_403_FORBIDDEN` mit Detail `"Email not verified"`. Generischer 401-Pfad bleibt unverändert (anti-enumeration für falsche Credentials/unbekannte E-Mails). Neuer Test `test_login_user_unverified_email_raises_email_not_verified_error` deckt den neuen Pfad ab und verifiziert die Subclass-Beziehung (wichtig für Endpoint-Mapping-Reihenfolge); bestehende Login-Tests bleiben unberührt, weil `make_user()` defaultmäßig `verified=True` liefert.
- **`SMTP_USE_TLS`-Default auf Tri-State (`bool | None`) mit Smart-Auto-Default umgestellt** (Deployment-Bug, beim ersten Registrierungsversuch auf der Synology aufgetaucht). `correlcore-api`-Log zeigte beim Registrieren `verification token issued` direkt gefolgt von `smtp send failed` — die Fehler werden in `email_service._send` bewusst geschluckt (`# Do NOT raise — let the user retry via /resend-verification`, nötig für Email-Enumeration-Resistenz), also bekam der User keine Fehlermeldung. Mailpit (Standard-Dev-Mail-Catcher in allen drei Compose-Stacks) lauscht auf `:1025` im Plain-Modus und unterstützt _kein_ STARTTLS — das Mailpit-Log meldet beim Start explizit `[smtpd] starting on [::]:1025 (no encryption)`. Backend-Default `SMTP_USE_TLS=True` (in `app/core/config.py`) zwang `aiosmtplib.send()` zu `start_tls=True`, was Mailpit ablehnte. Fix: `SMTP_USE_TLS: bool | None = None` als neuer Default plus Property `Settings.smtp_should_use_tls`, die das `None` per Heuristik auflöst: "`SMTP_USER` gesetzt = echter Relay = STARTTLS an", "`SMTP_USER` leer = Dev-Catcher = STARTTLS aus". Explizites `SMTP_USE_TLS=true` oder `SMTP_USE_TLS=false` in der `.env` überschreibt die Heuristik immer (Escape-Hatch für trusted-network-Relays, lokale Debug-Setups). `email_service._send` ruft `start_tls=settings.smtp_should_use_tls` statt `settings.SMTP_USE_TLS`. Neuer Test `backend/tests/test_settings_smtp_tls.py` (8 Cases: Default-ohne-User, Default-mit-User, expliziter Override beider Richtungen, truthy/falsy ENV-Strings, leerer SMTP_USER) verhindert Regression. `infra/dockhand/.env.example`, `infra/dockge/.env.example` und `infra/docker/.env.user-test.example` mit Erklärungs-Block zum neuen Tri-State und einer auskommentierten `# SMTP_USE_TLS=`-Zeile als Doku-Anker. `infra/dockhand/README.md` SMTP-Tabelle aktualisiert: alter Hinweis "für Mailpit `SMTP_USE_TLS=false`" durch Beschreibung des neuen Smart-Defaults ersetzt.
- **Dockhand/Dockge/user-test: Host-Ports für API und Web konfigurierbar via `API_HOST_PORT` / `WEB_HOST_PORT`** (Deployment-Bug, beim Stack-Start auf der Synology aufgetaucht). `correlcore-api` brach beim Container-Create mit `Error starting userland proxy: listen tcp4 0.0.0.0:8000: bind: address already in use` ab — Port 8000 ist auf typischen Selfhosted-Setups oft schon belegt (z.B. Paperless-ngx). Die drei Compose-Files (`infra/dockhand/compose.yaml`, `infra/dockge/compose.yaml`, `infra/docker/docker-compose.user-test.yml`) hatten den Host-Port hardcoded als `8000:8000` bzw. `3000:3000`. Fix: Beide Mappings auf `${API_HOST_PORT:-8210}:8000` und `${WEB_HOST_PORT:-3000}:3000` umgestellt — Default-API-Port ist jetzt **8210**, weil dieser mit keinem der üblichen Selfhosted-Tools (Plex, Portainer, Home Assistant, Jellyfin, \*arr-Stack, Grafana, Paperless) kollidiert. Container-interne Ports bleiben fix bei 8000/3000. Alle drei `.env.example`-Dateien (`infra/dockhand/.env.example`, `infra/dockge/.env.example`, `infra/docker/.env.user-test.example`) haben einen neuen `Host-Ports`-Block mit Default-Werten und expliziter Warnung, dass beim Ändern von `WEB_HOST_PORT` die Ports in `CORS_ORIGINS` nachgezogen werden müssen. READMEs (Dockhand/Dockge/user-test) entsprechend aktualisiert.
- **Migration 004: `tags.category`-Spalte in `op.bulk_insert` als ENUM statt `sa.String` deklarieren** (Deployment-Bug, beim ersten erfolgreichen Migrate-Lauf nach den vorigen Hotfixes aufgetaucht). `correlcore-migrate` brach in der Seed-Phase von Migration 004 mit `asyncpg.exceptions.DatatypeMismatchError: column "category" is of type tag_category but expression is of type character varying` ab — nachdem die Tabelle und der ENUM-Typ `tag_category` bereits korrekt erzeugt waren. Ursache: Im `sa.table(...)`-Stub für `op.bulk_insert` war `category` als `sa.String` deklariert, weshalb SQLAlchemy bei der Generierung des INSERT-Statements `$3::VARCHAR` band; PostgreSQL verweigert den impliziten Cast von `character varying` auf einen Custom-ENUM-Typ. (Bei direktem `INSERT ... VALUES ('sport', ...)` mit String-Literal hätte Postgres den Cast erlaubt — mit gebundenem Parameter und explizit geforderter Typ-Annotation greift das nicht.) Da Migration 004 unter Transactional DDL läuft, wurde der gesamte 004-Schritt zurückgerollt; die DB blieb auf Revision 003 sauber stehen. Fix: `category`-Stub auf `postgresql.ENUM(*_TAG_CATEGORY_VALUES, name="tag_category", create_type=False)` umgestellt — SQLAlchemy generiert daraufhin `$3::tag_category`, Postgres akzeptiert. Verifiziert offline durch SQL-Compilation gegen den asyncpg-Dialekt; CI-seitig durch den neuen Migrations-Smoke-Job (siehe **Added**) bei jedem Backend-PR scharf gestellt.
- **Settings: `CORS_ORIGINS` und `ENCRYPTION_KEYS` als kommagetrennte ENV-Strings akzeptieren** (Deployment-Bug, beim zweiten Dockhand-Redeploy aufgetaucht). `correlcore-migrate`-Container brach mit `pydantic_settings.exceptions.SettingsError: error parsing value for field "CORS_ORIGINS" from source "EnvSettingsSource"` ab, sobald die ENV-Variable als CSV-Liste gesetzt wurde (`CORS_ORIGINS=http://a,http://b`). Ursache: pydantic-settings v2 versucht für komplexe Felder (`list[str]`) den ENV-Wert _zuerst_ per `json.loads` zu dekodieren — _bevor_ `field_validator(mode="before")` aufgerufen wird. Der bestehende Validator zum CSV-Splitten kam also nie zum Zug. Fix: `Annotated[list[str], NoDecode]` (aus `pydantic_settings`) auf beide betroffenen Felder (`CORS_ORIGINS`, `ENCRYPTION_KEYS`) angeheftet — damit überspringt pydantic-settings den JSON-Pre-Parse, der existierende `mode="before"`-Validator splittet wie dokumentiert auf Komma. Neuer Test `backend/tests/test_settings_csv_lists.py` (9 Cases, deckt CSV-Split, Whitespace-Trim, Single-Origin, leere ENV, Default-Fallback, `effective_encryption_keys`-Präzedenz ab) verhindert künftige Regression. `infra/docker/.env.example` und `infra/dockhand/.env.example` dokumentieren weiterhin das CSV-Format als kanonisch.
- **`backend/Dockerfile`: `app/`-Source vor editable install kopieren** (Deployment-Bug, beim ersten Dockhand-Stack-Run aufgetaucht). `correlcore-migrate`-Container brach mit `ModuleNotFoundError: No module named 'app'` beim Alembic-Bootstrap (`migrations/env.py:11 → import app.models`) ab. Ursache: Builder-Stage führte `uv pip install -e .` aus, bevor `app/` im Build-Context lag — Hatchlings `[tool.hatch.build.targets.wheel] packages = ["app"]` fand zur Build-Zeit kein Package-Source, also landeten zwar Dependencies in der venv, aber kein `.pth`-Eintrag für `app` selbst. uvicorn (API) startete in `/app` und konnte `app` per Working-Dir importieren; Alembic wechselt aber in `migrations/`, wodurch `app` aus `sys.path` fiel. Fix: Zusätzliches `COPY app/ app/` zwischen `COPY pyproject.toml …` und `RUN uv venv …` im Builder. Damit ist der Package zur Build-Zeit verfügbar, der editable install registriert ihn korrekt in der venv, und Alembic findet `app.models` unabhängig vom Working-Dir.
- **CI: pnpm-Build-Script-Allowlist gegen `ERR_PNPM_IGNORED_BUILDS`.** Auf frischen Branches (kein `node_modules`-Cache-Hit in den Web-Workflows) brach `pnpm install --no-frozen-lockfile` mit Exit 1 ab, sobald für `esbuild@0.19.12`, `esbuild@0.21.5` oder `es5-ext@0.10.64` Build-Scripts liefen — pnpm 10 verlangt seit Anfang 2025 explizite Freigabe (`approve-builds`) und behandelt unbestätigte Build-Scripts in CI-Umgebungen als harten Fehler. `main` lief nur durch, weil dort der GitHub-Actions-Cache die `node_modules` mit installierten Build-Artefakten vorhielt; jeder neue Feature-/Fix-Branch traf den Bug aufs Neue (zuletzt PR #84). Fix: `onlyBuiltDependencies: [esbuild, es5-ext]` plus `allowBuilds: { esbuild: true, es5-ext: true }` in `pnpm-workspace.yaml` (pnpm 10 liest Workspace-Settings nicht mehr aus `package.json`, sondern ausschließlich aus `pnpm-workspace.yaml`; pnpm 11 ersetzt `onlyBuiltDependencies` durch `allowBuilds`, deshalb beide Schlüssel für Versionskompatibilität). Damit erlaubt pnpm die Build-Scripts dieser zwei Pakete deterministisch (esbuild postinstall lädt Native-Binaries, es5-ext registriert seine Polyfill-Hooks), ohne andere Build-Scripts ungewollt zu aktivieren.
- **Container-Image-Builds zum ersten Mal lauffähig.** Beide Dockerfiles waren zwar im Repo, aber kein Image war je gebaut/gepublished worden — was beim ersten Run des neuen `release-images.yml`-Workflows (PR #76 / Commit 4378fcb) sichtbar wurde.
  - **`backend/Dockerfile`**: `OSError: Readme file does not exist: README.md` beim `uv pip install -e .` — Hatchling liest `readme = "README.md"` aus `pyproject.toml`, die Datei war aber nicht im Build-Context. Fix: `COPY pyproject.toml uv.lock README.md ./` (statt nur `pyproject.toml`). Gleichzeitig `[dev]`-Extras aus dem Production-Image entfernt (`-e .` statt `-e .[dev]`) → ruff/mypy/pytest landen nicht mehr im Runtime-Image, kleinere Angriffsfläche. `uv.lock` wird mitkopiert für reproducible Builds.
  - **`apps/web/Dockerfile`**: `pnpm prune --prod` hängte mit "confirmModulesPurge"-Prompt im non-TTY-CI-Container und brach mit Exit 1 ab. Erster Fix-Versuch (`pnpm install --prod --frozen-lockfile` nach Build) hatte denselben Effekt mit `ERR_PNPM_ABORTED_REMOVE_MODULES_DIR_NO_TTY`. Zwischen-Fix: zusätzliches `ENV CI=true` ganz oben im Dockerfile (GitHub-Actions setzt `CI=true` im Runner-Env, vererbt das aber nicht in den Buildx-Container, deshalb muss es im Dockerfile selbst stehen). Damit übergeht pnpm interaktive Prompts — doch der `prepare`-Lifecycle-Hook in `apps/web/package.json` (`svelte-kit sync`) bricht beim Prod-Install dann mit `sh: svelte-kit: not found` ab, weil `@sveltejs/kit` als devDependency bei `--prod` nicht installiert wird. **Finaler Fix:** `--ignore-scripts` beim Prod-Install — `prepare` wird für das Production-Image ohnehin nicht gebraucht, der Build ist im vorigen Step bereits gelaufen.
  - Beide Fixes betreffen ausschließlich Build-Mechanik, keine Runtime-Semantik. Erste erfolgreiche GHCR-Pushes (`ghcr.io/sturmi77/correlcore-{api,web}:latest`) entstehen mit dem main-Push dieses PRs.

### Added

- **Coverage für `email_service` und `health_service` auf 100 % gehoben** (CQR-4 + CQR-5 aus `docs/quality/M1_QUALITY_GATE.md`, Issue #70). Der M1-Quality-Gate hatte bei beiden Modulen Coverage unterhalb der projektweiten 70 %-Mindestschwelle protokolliert: `email_service.py` lag bei **39 %** — die SMTP-Fehlerpfade (`SMTPResponseException`, `SMTPConnectError`, `ConnectionRefusedError`, `TimeoutError`) waren ungetestet, und das ist genau der Pfad, der bei der ersten Synology-Registrierung im M1-Hotfix-Block tatsächlich zugeschlagen hat (PR #94, SMTP_USE_TLS-Smart-Default). `health_service.py` lag bei **59 %** — die internen Probes `_probe_postgres` / `_probe_redis` waren ungetestet, weil `tests/test_health.py` den öffentlichen `check_readiness`-Aggregator als `AsyncMock` ausstubbt und die echte Probe-Logik damit nie angefasst hat. Zwei neue Test-Module: **`backend/tests/test_email_service.py`** (14 Tests) deckt `_send` mit leerem `SMTP_HOST` (Dev-Fallback, kein Network-Call, INFO-Log mit `to_domain`-only DSGVO-Privacy), Happy-Path mit allen Settings durchgereicht zu `aiosmtplib.send` (Hostname, Port, User/Password als `None` bei leeren Strings, `start_tls`, Timeout), vier separate Fehlerpfade (`SMTPResponseException(550)` / `SMTPConnectError` / `ConnectionRefusedError` / `TimeoutError`) mit Verifikation, dass jeder Fehler geschluckt wird (kein Re-Raise) und ein ERROR-Log mit `error_type=type(exc).__name__` plus `to_domain` (nicht voller E-Mail-Adresse) emittiert wird, sowie die beiden Public-API-Funktionen `send_verification_email` / `send_already_registered_email` mit korrekt gerenderter `verify_url`/`login_url`, gesetzten Headern (`Subject`, `From`, `To`) und der Garantie, dass `send_already_registered_email` **keinen** Token-Wert ins HTML/Text-Body schreibt (Issue #65 Enumeration-Safety). **`backend/tests/test_health_service.py`** (12 Tests) deckt `check_liveness` (statisches Payload, kein I/O), `_probe_postgres` mit drei Pfaden (Happy-Path mit gemockter `engine.connect()`-AsyncCM → OK, `OperationalError` direkt beim `connect()` → DOWN mit `detail="OperationalError"`, `TimeoutError` beim `execute("SELECT 1")` → DOWN mit `detail="TimeoutError"`) inklusive Verifikation, dass das Log nur den Klassennamen mentioniert und **nicht** die SQLAlchemy-Detail-Message (DSN-/Password-Leak-Risiko aus ADR-0007), `_probe_redis` mit vier Pfaden (Happy-Path mit `socket_connect_timeout=2`-Forward, `redis.ConnectionError` → DOWN, `TimeoutError` → DOWN, `ValueError` aus `Redis.from_url(...)` → DOWN), sowie `check_readiness`-Aggregation mit allen vier Kombinationen (beide OK → ready=True, einer DOWN → not_ready, beide DOWN → not_ready). Alle 26 neuen Tests sind reine Unit-Tests — keine echte DB, keine echte Redis-Instanz, kein SMTP-Relay; gemockt wird konsequent an der Bibliotheks-Boundary (`aiosmtplib.send`, `Redis.from_url`, `engine.connect`). Coverage-Resultat: `app/services/email_service.py` **100 % (50/50 Statements)**, `app/services/health_service.py` **100 % (54/54 Statements)**, projektweit **96.08 %** (vorher 60.52 %). Threshold `--cov-fail-under=70` (in `backend/pyproject.toml`) wird damit komfortabel überschritten.

- **Home-Screen „Heute-Ansicht“ für eingeloggte User auf `/`** (Issue #97). Bisher zeigte die Root-Route auch authentifizierten Usern weiterhin die generische Landing (Logo + Tagline + Theme-Toggle + Pre-Alpha-Badge) — das war das letzte fehlende Stück für das M1-Exit-Kriterium „Produktive Online-Nutzung durch Entwickler selbst möglich (inkl. Login im Browser)“ (`DESIGN_DOCUMENT.md`, M1-Sektion): nach erfolgreichem Login landete der User wieder auf der Pre-Alpha-Seite ohne sichtbaren nächsten Schritt zum Eintrag-Erfassen, und es gab keinen Logout-Button außerhalb des Browser-DevTools-Cookie-Pfads. Issue ursprünglich als M2-„Dashboard“ geplant, während der M1-Implementierung neu eingeordnet: M2 ist explizit die Visualisierungs-Schicht (Mood-Zeitreihe, Heatmap, Streaks, Export, `DESIGN_DOCUMENT.md` M2-Sektion), während ein minimaler Auth-Gate-Home-Screen ohne Visualisierungen zu M1 gehört. Issue umbenannt von „Dashboard-Route nach Login“ auf „Heute-Ansicht (Home-Screen) nach Login“, Milestone von M2 auf M1 verschoben, Scope auf das Notwendigste reduziert. **Implementierung in `apps/web/src/routes/+page.svelte`:** zwei Render-Pfade gegated auf `$auth.status` — anonyme User sehen unverändert die bestehende Landing (Logo + Tagline + Theme-Toggle + Pre-Alpha-Badge), authentifizierte User sehen die neue Heute-Ansicht. Heute-Ansicht enthält: (1) zeitabhängige Begrüßung mit Display-Name (`home.greeting_morning`/`_day`/`_evening` je nach `new Date().getHours()` — 05–11→morning, 12–17→day, 18–04→evening), (2) Heute-Status-Badge, der nach `onMount` per `listEntries({ start_date: todayIso, end_date: todayIso, limit: 1 })` prüft, ob ein Eintrag für heute existiert (success-Variant „Heute schon getrackt ✓“ bzw. warning-Variant „Noch kein Eintrag heute“), (3) Hero-CTA-Card als `<a href="/entries/new">` mit Text „Neuer Eintrag“ bzw. „Heutigen Eintrag bearbeiten“ (Routing nutzt die existierende `/entries/new`-Route, da Backend per `POST /entries` mit Conflict-Handling arbeitet — separate `/entries/edit/:id`-Route ist M2-Scope), (4) Logout-Button oben rechts der `auth.logout()` ruft und auf `/` redirectet, (5) Theme-Toggle bleibt erhalten und wandert oben links neben den Logout-Button. Bewusst **nicht** enthalten und für M2/M3 reserviert: Liste der letzten 3–5 Einträge, Streak-Counter, Heatmap-Vorschau, Charts, Insight-Karte (entspricht Home-Screen-Heuristik im `DESIGN_DOCUMENT.md`, „Heute + Streak + letzter Insight. Keine Dashboard-Überladung“). Reine Logik (Greeting-Key-Selektion, lokale ISO-Datums-Formatierung ohne UTC-Shift, Eintrag-Lookup) wurde in `apps/web/src/lib/utils/home.ts` ausgelagert, um sie unabhängig von Svelte-Component-Test-Infrastruktur per Vitest abzudecken; neuer Test `apps/web/src/lib/utils/home.test.ts` (10 Cases: `localIsoDate`-Padding, `localIsoDate`-Regression gegen `toISOString`-TZ-Shift, drei `greetingKey`-Bereiche, `findEntryForDate`-Hit/Miss/Empty/Null/Undefined). Neue i18n-Keys in `apps/web/src/lib/i18n/locales/de.json` und `…/en.json`: `home.entry_today_present`, `home.cta_new_entry`, `home.cta_edit_entry`, `home.loading_today` (bestehende Keys `home.greeting_*`, `home.no_entry_today`, `auth.logout.label` werden wiederverwendet). Auth-Gate auf `/` ist nicht nötig, da `+layout.svelte` ohnehin nur Routen unter `/auth/` und `/status` als public führt — anonyme User auf `/` sind ein gültiger Zustand (Landing).
- **CI-Job `migrations-smoke` in `.github/workflows/ci-api.yml`.** Spinnt einen `postgres:16.4-alpine`-Service hoch (selbe Version wie Dockhand-Compose) und führt `alembic upgrade head` aus. Anschließend Round-Trip `alembic downgrade base → alembic upgrade head` als Bonus-Paranoia, der die `downgrade()`-Pfade exerciert (rotten sonst still vor sich hin, weil keine Tests sie auslösen) und sicherstellt, dass die Up-Kette idempotent gegen eine leere DB durchläuft. Fängt die Bug-Klasse, die Migration 004 produzierte: SQL kompiliert, wird aber zur Ausführungszeit von Postgres mit `DatatypeMismatchError` o.ä. abgelehnt. Unit-Tests mit DB-Mocks fangen das prinzipbedingt nicht. Erhöht die Backend-CI-Laufzeit um ca. 30 Sekunden, ist dafür aber der einzige automatische Schutz vor Migrations-Sprengsätzen.
- **Deployment-Bundle für ersten User-Test** (Tailscale-internes Homelab-Szenario). Nach abgeschlossenem M1-Quality-Gate steht der Stack jetzt out-of-the-box für ersten Real-User-Feedback bereit, ohne dass Production-Voraussetzungen wie öffentliche Domain oder Letsencrypt erfüllt sein müssen.
  - **Neue Compose** `infra/docker/docker-compose.user-test.yml` (Stack-Name `correlcore-test`): API + Web + Postgres + Redis + Mailpit als Default; GlitchTip via `--profile monitoring`; Worker-Slot via `--profile worker` (vorbereitet für M2, Code noch nicht vorhanden). Ports binden ausschließlich an `${TAILSCALE_IP}` (Default `127.0.0.1`) statt `0.0.0.0` → kein WAN-Exposure. `migrate`-Init-Container führt `alembic upgrade head` einmalig vor `api` aus (`condition: service_completed_successfully`-Gate), idempotent. MinIO bewusst weggelassen, weil Foto-Upload erst M3+ ist.
  - **Web-Dockerfile** (`apps/web/Dockerfile`, war bisher nicht vorhanden): Multi-Stage-Build (Node 22 alpine), pnpm via Corepack, `--frozen-lockfile`, SvelteKit-Adapter-Node-Server (`build/index.js`), non-root-User `correlcore`, Build-Arg `VITE_API_BASE_URL`. Zugehöriges `apps/web/.dockerignore` und `backend/.dockerignore` neu.
  - **GHCR-Release-Workflow** (`.github/workflows/release-images.yml`): baut und published `ghcr.io/sturmi77/correlcore-api` und `ghcr.io/sturmi77/correlcore-web` bei Push auf `main` (`:latest` + `:main` + `:sha-<short>`) und bei `v*`-Tags (`:vX.Y.Z` + `:vX.Y` + `:latest`) — getrennt von den bestehenden Lint/Test-Workflows. GitHub-Actions-Cache (Buildx + GHA-Cache, scope-getrennt für api/web).
  - **`.env.user-test.example`** (`infra/docker/.env.user-test.example`, separat von der bestehenden Production-`.env.example` aus Issue #41) mit allen Variablen, Generierungs-Snippets (Fernet, `secrets.token_urlsafe`) und expliziten Hinweisen zur ENCRYPTION_KEY-Backup-Pflicht. **Neue README** `infra/docker/README.user-test.md` mit Setup-, Update-, Backup- und Troubleshooting-Anleitung.
  - Production-Compose `docker-compose.yml` (Traefik + Letsencrypt + MinIO + Worker) bleibt unverändert — beide Stacks parallel nutzbar (`correlcore` vs. `correlcore-test`).
- **Dockge-Stack-Variante** unter `infra/dockge/` (`compose.yaml` + `.env.example` + `README.md`). Drop-in für [Dockge](https://github.com/louislam/dockge) im Homelab — Stack-Verzeichnis (z. B. `/opt/stacks/correlcore/`) wird zum Stack-Namen, daher kein top-level `name:`-Key. Funktional identisch zur user-test-Compose (gleiche GHCR-Images, gleiche Services, gleiche Healthchecks, gleicher Tailscale-IP-Bind), aber ohne `--profile`-Konstrukte (Dockge UI ignoriert Profile beim Deploy → GlitchTip- und Worker-Blöcke stattdessen auskommentiert mit Aktivierungs-Anleitung). Volumes explizit benannt (`correlcore_postgres_data`, `correlcore_redis_data`) für saubere Anzeige im Dockge-UI. README dokumentiert Setup-, Update-, Backup-Workflow und die Unterschiede zur user-test-Compose.
- **Dockhand-Stack-Variante** unter `infra/dockhand/` (`compose.yaml` + `.env.example` + `README.md`). Drop-in für [Dockhand](https://dockhand.pro) — unterstützt Git-Stack-Deployment (Repo-URL + `infra/dockhand`-Pfad direkt im UI eintragen, Auto-Sync via Webhook) und manuelles Adopt-Setup. `name: correlcore` ist gesetzt (Dockhand respektiert top-level Name im UI-Header). Profiles `monitoring` und `worker` bleiben aktiv (Dockhand-UI hat ein „Profiles to enable“-Feld). Kein `pull_policy: always` — Dockhand managt Image-Pulls selbst und scannt mit Grype+Trivy vor dem Deploy, daher pinned `IMAGE_TAG` (sha- oder vX.Y.Z) empfohlen. Logging-Limits explizit per `x-logging`-Anchor (`json-file`, max-size 10m, max-file 3) damit der UI-Log-Viewer nicht Gigabyte streamt. README mit Vergleichstabelle zu user-test- und Dockge-Variante.
- **`DELETE /api/v1/user/me` — DSGVO-Art.-17-Erasure-API** (Issue #66, M1-Quality-Gate-Finding **SA-4**, ADR-0005). Schließt den letzten blockierenden M1-Exit-Pfad: User können ihren Account jetzt vollständig per API löschen, statt auf manuelle DB-Eingriffe angewiesen zu sein.
  - **Auth + Re-Auth:** Endpoint läuft hinter `get_current_user` (Verifizierung **nicht** erforderlich — das Recht auf Löschung darf nicht von einer ausstehenden E-Mail-Bestätigung abhängen). Body verlangt das aktuelle Passwort als Defense-in-Depth gegen XSRF-via-Cookie und gegen einen geleakten Access-Token.
  - **Cascade-Reichweite:** Hard-Delete der `users`-Row triggert `ON DELETE CASCADE` auf `entries`, `entry_tags`, `entry_symptoms`, Custom-`tags`, Custom-`symptoms`, `email_verification_tokens` und — entscheidend — `user_encryption_keys`. Damit werden `entries.note_enc` und Custom-`symptoms.name_enc` ab dem Commit kryptografisch unentschlüsselbar („cryptographic erasure“, ADR-0005). Default-Tags/Symptome (`user_id IS NULL`) bleiben erhalten.
  - **Refresh-Token-Revoke:** `TokenStore.revoke_all(user_id)` wird **vor** dem DB-DELETE aufgerufen — selbst bei späterem DB-Fehler ist der User damit force-logged-out auf allen Geräten. Auf der Response werden `access_token`- und `refresh_token`-Cookies invalidiert.
  - **Status-Codes:** `204 No Content` bei Erfolg, `401` für fehlende Auth **und** falsches Passwort (generische `"Invalid credentials"`-Meldung verhindert Unterscheidbarkeit), `422` für Body-Validierung.
  - **Logs:** ausschließlich `user_id`, niemals Email — abgesichert durch zwei dedizierte Tests (`test_user_service.py::test_delete_user_*_logs_user_id_not_email`).
  - **Neuer Service** `app/services/user_service.py` (`delete_user_account`, `UserDeletionError`), neuer Endpoint-Router `app/api/v1/endpoints/user.py` unter `/api/v1/user`, neues Schema `DeleteAccountRequest`. Tests: 5 Service-Unit-Tests + 7 Endpoint-Tests, alle DB-/Redis-frei via Mocks.
  - **Doku:** Neuer Abschnitt §6 „User“ in `docs/API.md`; ADR-0005, `docs/DSGVO.md`, `docs/ARCHITECTURE.md` und `docs/DESIGN_DOCUMENT.md` (DSGVO-Checkpoint M1) auf den finalen URL `/api/v1/user/me` konsolidiert (vorher inkonsistent zwischen `/user/me` und `/user/account`). M1-Quality-Gate-Report aktualisiert: SA-4 als behoben markiert.
  - **M1-Quality-Gate-Checkpoint** (DESIGN_DOCUMENT §3 „M1 — Core Entry“) ist mit diesem PR auf `[x]` gesetzt: alle drei blockierenden Major-Findings (#64 Auth-Coverage, #65 `/auth/register` Enumeration, #66 Erasure-API) sind adressiert.

### Added

- **Encryption-Healthcheck in `/health/ready`** (Issue #68, M1-Quality-Gate-Finding SA-5): `health_service.py` hat eine neue dritte Probe `_probe_encryption`, die einen vollständigen Master-Fernet-Roundtrip ausführt (`generate_dek()` → `wrap_dek()` → `unwrap_dek()` → Byte-Vergleich). Bisher hätte ein fehlerhaft rotierter oder gelöschter `ENCRYPTION_KEY`/`ENCRYPTION_KEYS` zu `200 OK` auf `/health/ready` geführt, während Login, `/me`, Refresh und jeder authentifizierte Request still mit 401 (DEK unwrap failed) abgebrochen wären. **Verhalten:** `ComponentHealth(name="encryption", status=ok|down)`, `detail` enthält nur den Exception-Klassennamen (ADR-0007: niemals Settings-Dump, Key-Material oder Plain-/Ciphertext). Aggregation in `check_readiness` erweitert — `ready=True` jetzt nur, wenn Postgres + Redis + Encryption alle OK. **Synchronous probe:** Fernet ist CPU-bound (Mikrosekunden), kein `await` nötig, keine messbare Verzögerung am Endpoint. **Tests:** 5 neue Unit-Tests in `tests/test_health_service.py` (Happy-Path, fehlender Master-Key, ungültiger Master-Key, Unwrap-Fehler, Roundtrip-Mismatch) plus 1 neuer Aggregat-Test (`encryption=down` flippt Readiness). Probe-Mocks an Library-Grenze (`generate_dek`/`wrap_dek`/`unwrap_dek` aus `app.core.crypto`), keine echten Crypto-Keys nötig. `health_service.py` Coverage 100 % (69/69), Vollsuite 288 passed (vorher 282). **Doku:** `docs/RUNBOOK_KEY_ROTATION.md` Abschnitt **Healthcheck-Verhalten während Rotation** mit Phasen-Tabelle (welcher Status bei welcher Rotations-Phase erwartet wird) und operativer Pre-Flight-Hinweis (Probe MUSS grün sein, bevor Re-Wrap-Job in Phase 4 startet — sonst Risiko unrecoverable DEKs). Verifikations-Snippet in Schritt 6 ergänzt: `curl /health/ready | jq '.components[] | select(.name=="encryption")'`.

### Tests

- **Log-Scrubbing-Tests um Tag-, Custom-Symptom- und Encryption-Felder erweitert** (Issue #67, M1-Quality-Gate-Finding SA-3): `tests/test_log_scrubbing.py` deckt nun zusätzlich die mit Issues #8 (Tags), #57 (Custom-Symptome) und #26 (Encryption-at-Rest) eingeführten Felder ab. **Erweiterte Forbidden-Sentinels:** `Migräne mit Aura` (Custom-Symptom-Klartext), `migraene-mit-aura` (Custom-Symptom-Slug, semantischer Leak laut ADR-0005-Trade-off), `Stress bei Arbeit` / `stress-bei-arbeit` (Custom-Tag-Name + -Slug), `name_enc_ciphertext_bytes` (`Symptom.name_enc` BYTEA), `wrapped_dek_ciphertext_bytes` (`UserEncryptionKey.wrapped_dek` BYTEA). **Anti-Pattern-Regex erweitert** um `name_enc` und `wrapped_dek` — `logger.X(...name_enc...)` schlägt jetzt CI an. **6 neue Repr-Stripping-Tests:** `Entry.__repr__` ohne Mood-/Energy-/Stress-/Notiz-Payload, `Symptom.__repr__` zeigt kuratierte Default-Slugs (`headache`) aber maskiert Custom-Slugs als `<custom>`, dito für `Tag.__repr__`, `UserEncryptionKey.__repr__` ohne `wrapped_dek`-Bytes oder -Länge. **Modell-Anpassung:** `Tag.__repr__` und `Symptom.__repr__` liefern für User-eigene Einträge jetzt `slug=<custom>` statt des Klartext-Slugs (Default-Einträge unverändert). 6 → 12 Tests in `test_log_scrubbing.py`, 282 Tests gesamt-grün, projektweite Coverage 96.08 %.

- **Auth-Coverage auf ≥85 % gehoben** (Issue #64, M1-Quality-Gate-Finding CQR-1/2/3): die drei sicherheitskritischsten Auth-Module sind jetzt umfassend unit-getestet, ohne DB- oder Redis-Abhängigkeit. **Coverage-Sprung:** `app/services/auth_service.py` 53 % → **95 %**, `app/api/v1/deps/auth.py` 38 % → **100 %**, `app/core/security.py` 58 % → **100 %**. **Gesamt-Backend-Coverage** 84.95 % → **92.29 %**, 160 → **213 grüne Tests**.
  - **`tests/test_auth_service.py`** (23 Tests): `register_user` (duplicate + happy path), `verify_email` (token-not-found, expired, already-used, user-not-found, success, idempotency), `create_verification_token`, `request_verification_resend` (success + inactive-user-skip), `login_user` (unknown-email-constant-time, wrong-password, disabled, success), `refresh_tokens` (wrong-type, replay-revokes-all, malformed-sub, disabled, success-mit-Rotation, valid-but-not-in-store), `logout_user` (valid + invalid-token).
  - **`tests/test_auth_deps.py`** (17 Tests): `_resolve_user` (8 Pfade inkl. wrong-type, missing-sub, malformed-sub, user-not-found, disabled, success), `_load_and_bind_dek` inkl. `DecryptionError` → 401 (ADR-0005-konform), `get_current_user` Yield/Finally-DEK-Cleanup, `get_current_verified_user` (verified + unverified), Endpoint-Integration für Bearer-Header und Cookie-Auth.
  - **`tests/test_security.py`** (13 Tests): bcrypt-Roundtrip (Hash + Verify, Salt-Eindeutigkeit, Wrong-Password-Reject), JWT-Roundtrip für Access- und Refresh-Token, `extra`-Claim-Merge, JTI-Eindeutigkeit, Refresh > Access Expiry, Reject expired/tampered/foreign-secret/garbage Tokens.

### Changed

- **`POST /api/v1/auth/register` enumeration-safe** (Issue #65, SA-1/SA-2): Endpoint liefert jetzt **immer `202 Accepted`** mit derselben generischen Antwort, unabhängig davon, ob die Adresse neu oder bereits registriert ist — der bisherige `409 "Email already registered"` ist ersatzlos entfallen, weil er die Existenz einer Adresse leakte. Bei bereits registrierter Adresse wird kein User angelegt und keine Verify-Mail versandt; stattdessen geht einmalig eine "Diese Adresse ist bereits registriert"-Notiz an die Adresse (neue Templates `already_registered.txt.j2` / `.html.j2`, neue `EmailService.send_already_registered_email`). Service-Layer-Wrapper `request_registration` kapselt die Branch-Wahl in einem `RegistrationOutcome` ohne Exception. **Rate-Limit:** zusätzlich `5/min/IP` per SlowAPI auf den Endpoint, identisch zu `/login`. `docs/API.md` aktualisiert (known-limitation-Hinweis ersetzt durch finale Doku); 4 neue Endpoint-Tests (neuer User → 202 + Verify-Mail, bestehender User → 202 + Already-registered-Mail, Response-Äquivalenz, Rate-Limit-Trigger nach 6. Versuch) plus 2 Service-Tests.

### Documentation

- **M1 Quality-Gate-Report** (`docs/quality/M1_QUALITY_GATE.md`): kombinierter Code-Quality-Review + Security-Audit gemäß Design-Doc §9. Verdikt **bestanden mit Auflagen** — vier Major-Findings als blockierende Folge-Issues angelegt (#64 Auth-Coverage, #65 Register-Enumeration + Rate-Limit, #66 `DELETE /user/me`-Erasure-API), fünf weitere Findings als nicht-blockierende Folge-Issues (#67 Log-Scrubbing-Tests, #68 Encryption-Healthcheck, #69 esbuild-Advisory, #70 email/health-Service-Coverage, #71 vite-plugin-svelte-Update). DESIGN_DOCUMENT-Checkpoint M1-Quality-Gate referenziert den Report; wird auf `[x]` gesetzt, sobald die drei Major-Issue-Pakete gemerged sind.
- **Auth-Endpoints in `docs/API.md` vereinheitlicht** (Issue #50): `POST /auth/register`, `POST /auth/login`, `POST /auth/refresh`, `POST /auth/logout` und `GET /auth/me` haben jetzt jeweils einen vollständigen, dokumentierten Abschnitt analog zu `verify-email`/`resend-verification` (Body-Schemas, Cookie-Verhalten mit Pfad-Scopes und Max-Age, Statuscodes inkl. 401/409/422/429, Rate-Limits, Beispiel-Requests/Responses). Hinweis auf den Enumeration-Leak im aktuellen `register`-409 als known limitation mit Backlog-Verweis.
- **Environment-Variablen-Referenz in `infra/dockhand/README.md`**: neuer Abschnitt mit acht Tabellen (Stack-Steuerung, App-Modus, Auth & Krypto, DB, Redis, CORS, Frontend, SMTP) plus GlitchTip-Optional und einer Pflicht-Kurzliste der vier Variablen, die zwingend gesetzt sein müssen damit der Stack überhaupt startet (`SECRET_KEY`, `ENCRYPTION_KEY`, `POSTGRES_PASSWORD`, `REDIS_PASSWORD`). Beschreibungen verlinken auf die tatsächliche Backend-Quelle (`backend/app/core/config.py`) und nennen jeweils Default, Validierungsregeln (z. B. `POSTGRES_PASSWORD` darf kein `@` oder `/` enthalten wegen Asyncpg-DSN, `SECRET_KEY` ≥ 32 Bytes mit `APP_ENV=staging|production`-Validator), Generierungs-Snippets und Auswirkungen bei Wechsel (z. B. `SECRET_KEY`-Rotation invalidiert alle ausgegebenen Tokens). Inkonsistenz zwischen Backend-Default `SMTP_PORT=587` und Compose-Override `1025` explizit dokumentiert. Hinweis zu `FRONTEND_BASE_URL` für produktive Verifikations-Mails ergänzt.

### Added

- **App-Level Fernet at-rest** (Issue #26, ADR-0005): `entries.note` und `symptoms.name` (Custom) werden ab sofort serverseitig pro User mit einem eigenen Data-Encryption-Key (DEK) verschlüsselt gespeichert. Das schließt den letzten DSGVO-Art.-9-Blocker für M1.
  - **Master-Schlüssel:** `ENCRYPTION_KEY` (single) bzw. `ENCRYPTION_KEYS=key1,key2,...` (Liste während Rotation) als Umgebungsvariablen — als `MultiFernet` aufgesetzt, sodass `MultiFernet.rotate()` den Master ohne Downtime tauschen kann (Runbook: `docs/RUNBOOK_KEY_ROTATION.md`).
  - **Per-User-DEK:** Bei Registrierung wird ein 256-bit Fernet-Key generiert, mit dem Master-Key gewrappt und in der neuen Tabelle `user_encryption_keys` (PK = `user_id`, `wrapped_dek BYTEA`, `key_version INT`) abgelegt. RLS-Policies sind analog zu Migration 006 (Owner-Read/Update, kein Insert/Delete für User — wird ausschließlich vom Server erzeugt).
  - **Crypto-Layer** (`backend/app/core/crypto.py`): `generate_dek`/`wrap_dek`/`unwrap_dek`, `encrypt_with_dek`/`decrypt_with_dek`, request-scoped `ContextVar` (`_current_dek`) mit `set_current_user_dek`/`reset_current_user_dek`/`get_current_user_dek`, plus die SQLAlchemy-`EncryptedString`-`TypeDecorator`-Klasse für transparenten BYTEA-Roundtrip. Eigene Exceptions: `CryptoError`/`DekUnavailableError`/`DecryptionError`.
  - **Auth-Dependency:** `get_current_user` ist jetzt eine Yield-Dependency, die nach Token-Validierung den DEK des aktuellen Users entwrappt und bis zum Response-Ende in der `ContextVar` hält; Cleanup im `finally`-Pfad. `unwrap_dek`-Fehler (z. B. nach falschem Master-Key-Tausch) werden als 401 quittiert, nicht als 500, um Crypto-Details nicht zu leaken.
  - **Modelle:**
    - `Entry.note_enc` ist jetzt `EncryptedString` (vormals `Text`) — ORM-Aufrufer können weiterhin Strings setzen/lesen, der TypeDecorator macht den Encrypt/Decrypt unsichtbar.
    - `Symptom`: neue Spalte `name_enc BYTEA NULL`; `name` ist jetzt nullable. Eine CHECK-Constraint (`ck_symptoms_name_storage_consistency`) erzwingt: Default-Symptome haben `name` plaintext und `name_enc IS NULL`, Custom-Symptome haben `name IS NULL` und `name_enc` gefüllt. Neue Property `Symptom.display_name` und Helper `Symptom.set_custom_name(...)` machen den Polymorphismus für Service-/Schema-Layer transparent. `SymptomResponse.name` mappt via `validation_alias=AliasChoices("display_name", "name")`.
  - **Trade-off Slug:** `symptoms.slug` bleibt auch für Custom-Symptome plaintext (z. B. `migraene_mit_aura`), weil Operability (Debugging, Recovery, eindeutige Fehler-Logs) für M1 wichtiger ist als die zusätzliche Vertraulichkeit des semantischen Hinweises. Hardening via Slug-HMAC ist als Backlog-Issue für M9+ eingeplant und in ADR-0005 dokumentiert.
  - **Migration 007** (`007_add_app_level_encryption.py`): legt `user_encryption_keys` mit RLS an, **backfilled** für alle bestehenden User je einen DEK, migriert `entries.note` (TEXT) → `entries.note_enc` (BYTEA, ciphertext) und `symptoms.name` → `symptoms.name_enc` (nur Custom). Liest `ENCRYPTION_KEY`/`ENCRYPTION_KEYS` direkt aus dem Environment ohne App-Imports. Downgrade ist destruktiv (Daten gehen verloren) und in der Migration explizit dokumentiert.
  - **Cryptographic Erasure:** Account-Löschung kaskadiert via `ON DELETE CASCADE` in `user_encryption_keys` und macht damit alle Ciphertext-Felder des Users in einer Bewegung kryptografisch unentschlüsselbar (Art.-17-DSGVO).
  - **Tests:** 19 neue Unit-Tests in `tests/test_crypto.py` (DEK-Lifecycle, ContextVar-Isolation, `EncryptedString`-Roundtrip inkl. Pre-Encrypted-Bypass, `Symptom.display_name`-Polymorphismus, `set_custom_name`-Default-Block, repr-Log-Scrubbing). Test-`conftest.py` bindet einen synthetischen DEK autouse-weit, damit die bestehenden 137 Tests ohne Änderung weiterlaufen. **Stand:** 156 Backend-Tests grün, 85 % Coverage.
  - **Konfiguration:** `Settings.ENCRYPTION_KEYS: list[str]` neu (Komma-Liste) plus `Settings.effective_encryption_keys()`, `validate_production_secrets()` prüft Format und mind. einen Key in Produktion. `.env.example` enthält nun Generierungsbefehl und Hinweis zur Rotation.

### Changed

- **Roadmap-Scope** (ADR-0009): Issues #10 (Offline-Sync) und #24 (Sync-Conflict-Log) verschoben von **M1 — Core Entry** nach **M4 — Mobile Polish & PWA-Hardening**. M1-Exit ist 'Produktive Online-Nutzung im Browser'; Offline-Sync (Dexie.js + `/sync/push` + `/sync/pull` + LWW-Merge + Conflict-Reports) ist substantieller Aufwand und thematisch in M4 besser aufgehoben, wo bereits Offline-Modus-Akzeptanz dokumentiert war (frueher Doppelung mit M1). Issue #26 (App-Level Fernet at-rest) bleibt M1, da DSGVO-blockierend für realen Eigen-User-Test mit echten Symptom-Namen. DESIGN_DOCUMENT §3 M1 + M4 entsprechend umgestellt; Sync-Protokoll-Spezifikation in §3.5 unverändert.
- **CI** (Issue #49): `ci-web.yml` triggert jetzt zusätzlich auf `docs/**`, `**/*.md` und `.prettierignore`. Damit werden Prettier-Format-Drifts in der Dokumentation (z. B. `docs/API.md`, ADRs, Root-Markdown wie `CHANGELOG.md`) bei docs-only-PRs verlässlich erkannt — vorher liefen die Web-Jobs gar nicht, sodass Drift erst beim nächsten code-touchenden PR auffiel.

### Added

- **Custom-Symptome** (Issue #57, ADR-0008): User können eigene Symptome (z. B. „Migräne mit Aura“, „Tinnitus“, „Knieschmerzen“) anlegen, bearbeiten und löschen — vollständig analog zum Tag-System (Issue #8).
  - **Architektur:** Symptom-Master-Tabelle `symptoms` (mirror von `tags`) ersetzt die geschlossene Standard-Key-Menge; `entry_symptoms.symptom_key:String` wurde durch `entry_symptoms.symptom_id:UUID` als FK auf `symptoms` ersetzt. Defaults nutzen einen deterministischen `uuid5(NAMESPACE_DNS, "moodsync.symptom.<slug>")`, sodass die Daten-Migration aus `entry_symptoms` per Slug-Join idempotent gelingt.
  - **Backend Model:** Neue `Symptom`-Klasse (`backend/app/models/symptom.py`) mit `is_default`/`user_id`-Konsistenz-CHECK; `EntrySymptom` refactored auf `symptom_id`; helper `default_symptom_uuid()`; `(entry_id, symptom_id)`-Unique-Constraint statt vormals `(entry_id, symptom_key)`.
  - **Migration `006_add_symptom_master_table.py`** (single-transaction): erstellt `symptoms` mit zwei partiellen Unique-Indexen (`ux_symptoms_default_slug` WHERE `is_default`, `ux_symptoms_user_slug` WHERE NOT `is_default`), seedet 5 Defaults (`headache` 🤕, `digestion` 🌀, `back_pain` 🦴, `fatigue` 😴, `cold` 🤧), backfilled `entry_symptoms.symptom_id` per Join über Slug, swapped Unique-Constraint und droppt die alte `symptom_key`-Spalte. Vier RLS-Policies (`default_or_owner_select`, `owner_insert`, `owner_update`, `owner_delete`) analog zu `tags`. Vollständiges `downgrade()` enthalten.
  - **Service-Layer** (`symptom_service.py`) komplett neu: `list_default_symptoms`, `list_visible_symptoms`, `create_custom_symptom`, `update_custom_symptom`, `delete_custom_symptom`, sowie `assign_symptoms_to_entry` mit Visibility-Check auf `symptom_id`s (unbekannte oder fremde IDs → `SymptomsNotFoundError`). Hard Cap `MAX_SYMPTOMS_PER_USER=50` (analog Tags). Typisierte Exceptions: `SymptomNotFoundError`, `SymptomConflictError`, `SymptomOperationDeniedError`, `SymptomsNotFoundError`. **Privacy:** weder `slug`/`name`/`symptom_id` noch `intensity` werden geloggt — nur `user_id`, `entry_id` und Zähler.
  - **Endpoints:** `GET /api/v1/symptoms/default` (ohne Auth), `GET /api/v1/symptoms`, `POST /api/v1/symptoms`, `PATCH /api/v1/symptoms/{id}`, `DELETE /api/v1/symptoms/{id}`, plus `GET/PUT /api/v1/entries/{id}/symptoms` (Replace-Set, max. `MAX_SYMPTOMS_PER_ENTRY=32`). Der alte `/symptoms/standard`-Endpoint und das `StandardSymptomKeyList`-Schema entfallen.
  - **Schemas:** `SymptomCreate`/`SymptomUpdate`/`SymptomResponse` mit Slug-Normalisierung (lowercase, `[a-z0-9_]+`, 2..64 Zeichen) und Name-Validierung (1..80 Zeichen); `SymptomEntry` nutzt `symptom_id: UUID` statt `symptom_key: str`; `EntrySymptomResponse` ersetzt das vormalige `SymptomResponse`. Slug ist bewusst **nicht** patchbar (bräche Verweise in `entry_symptoms`).
  - **Frontend:** API-Client (`apps/web/src/lib/api/symptoms.ts`) komplett neu mit CRUD-Methoden (`createSymptom`, `updateSymptom`, `deleteSymptom`, `listVisibleSymptoms`, `listDefaultSymptoms`); Svelte-Store (`stores/symptoms.ts`) analog `tags`-Store mit `idle/loading/ready/error`-States, derived `symptomsList` (Defaults zuerst, dann Custom, je alphabetisch); `SymptomChecker`-Komponente erweitert um Inline-„Eigenes Symptom hinzufügen“-Form (Auto-Slug-Ableitung aus Name, 409/422-Fehlermapping ohne Payload-Leak), nutzt jetzt `symptom_id` statt `symptom_key` und fällt bei Defaults auf `symptom.key.<slug>`-i18n zurück, während Custom-Symptome ihren User-Namen verbatim zeigen.
  - **i18n:** Neuer `symptom.custom.*`-Block (de + en) mit Labels für Add-Button, Form-Felder, Save/Cancel-Buttons und Fehlertexten (`error_required`, `error_slug_invalid`, `error_conflict`, `error_validation`, `error_generic`); zusätzlich `symptom.empty` als Leerzustand-Hinweis.
  - **Tests:** 39 Backend-Tests in `test_symptoms.py` (Schemas, Service-CRUD, Owner-Isolation, Slug-Konflikte gegen Defaults und gegen eigene Customs, Cap-Erreichen, Default-vs-Custom-Schutz, alle Endpoints inkl. 422-Pfade für unbekannte/fremde `symptom_id`s, statischer Log-Scrubbing-Check der jetzt `slug`/`name`/`symptom_id`/`intensity` verbietet); 19 Frontend-Tests für API-Client und Store (CRUD, Sortierung, Cache-Updates).
  - **Privacy/DSGVO:** Custom-Symptom-Namen sind ähnlich wie freie `entries.note`-Einträge Art.-9-relevant. Issue #26 (Fernet at-rest) muss `symptoms.name` zusätzlich zu `entries.note` berücksichtigen — dieser Pfad ist in ADR-0008 explizit dokumentiert.
  - **Doku:** ADR-0008 (`docs/adr/0008-symptom-master-tabelle.md`) mit Rationale, 4 Decisions, 3 Alternativen-Erwägung und Consequences; ADR-Index (`docs/adr/README.md`) erweitert; API.md §5 vollständig auf das neue Modell umgestellt.
- **Symptom-Checkliste** (Issue #9): Gesundheits-Symptome können pro Entry mit einer Intensität von 0–3 erfasst werden — parallel zum Tag-System.
  - Backend: `EntrySymptom`-Modell ohne separate Master-Symptom-Tabelle (geschlossene Standard-Key-Menge `headache`/`digestion`/`back_pain`/`fatigue`/`cold`); CHECK-Constraints für `intensity BETWEEN 0 AND 3` und für die zulässigen Keys; `(entry_id, symptom_key)`-Unique-Constraint verhindert doppelte Symptome am selben Entry.
  - Migration `005_create_entry_symptoms.py`: `entry_symptoms`-Tabelle, denormalisiertes `user_id` für RLS, vier owner-scoped Row-Level-Security-Policies (`SELECT/INSERT/UPDATE/DELETE`), `updated_at`-Trigger.
  - Service-Layer (`symptom_service.py`) mit Replace-Set-Semantik und Key-basiertem Diff (add / update intensity / remove); typisierte Exception `EntryNotFoundForSymptomError`. **Privacy:** weder `symptom_key` noch `intensity` werden geloggt — nur `user_id`, `entry_id` und Zähler.
  - Endpoints: `GET /api/v1/symptoms/standard` (ohne Auth, Rate-Limit 120/min), `GET /api/v1/entries/{id}/symptoms` (Auth, 120/min) und `PUT /api/v1/entries/{id}/symptoms` (Auth, 60/min, max. `MAX_SYMPTOMS_PER_ENTRY=32`).
  - Pydantic-Schemas (`SymptomEntry`/`EntrySymptomAssignment`/`SymptomResponse`/`StandardSymptomKey`) mit Schlüssel-Normalisierung (lowercase + trim), Range-Validierung 0..3 und Duplikat-Prüfung.
  - Frontend: API-Client (`apps/web/src/lib/api/symptoms.ts`) mit lokalen Konstanten für `STANDARD_SYMPTOM_KEYS`/`MAX_SYMPTOMS_PER_ENTRY`/`INTENSITY_MIN`/`INTENSITY_MAX`, Svelte-Store (`symptoms.ts`, Fällt bei Fetch-Fehler auf die Build-Time-Konstante zurück), `SymptomChecker`-Komponente mit visueller 4-Punkt-Skala (`<button aria-pressed>` je Intensität, klick auf aktiven Dot löscht das Symptom) und permanentem medizinischem Disclaimer (`disclaimer.medical`).
  - Integration in `/entries/new`: Symptom-Zuweisung erfolgt nach erfolgreichem Entry-Create (best-effort, eigenes Fehlertext-Mapping `symptom.error_assign`).
  - i18n (`de.json`/`en.json`) um den `symptom.*`-Block (Picker-Labels, Schlüssel-Namen `Kopfschmerzen`/`Verdauung`/`Rückenschmerzen`/`Müdigkeit`/`Erkältung`, Intensitäts-Legenden, Fehlertexte) erweitert.
  - Tests: 21 Backend-Tests (Schemas, Service, Endpoints inkl. 422-Pfade für unbekannte Keys und out-of-range-Intensitäten, statischer Log-Scrubbing-Check) sowie 11 Frontend-Tests (API-Client, Store inkl. Fallback-Verhalten).
  - DESIGN_DOCUMENT.md M1-Akzeptanzkriterium für die Symptom-Checkliste auf `[x]` gesetzt; DSGVO-Checkpoint zur At-Rest-Verschlüsselung der `entry_symptoms`-Tabelle bleibt offen und verweist explizit auf Issue #26 (Fernet, ADR-0005). API.md §5 vollständig ergänzt; nachfolgende Abschnitte (Insights/Sync/Export/Admin/Fehlerformat) entsprechend renumeriert.
  - Hinweis: M1 speichert Symptom-Daten als Plaintext; RLS und Log-Scrubbing schirmen die Daten serverseitig ab. App-Level-Verschlüsselung folgt in Issue #26.
- **Tag-System** (Issue #8): Einträge können mit kuratierten Default-Tags und User-eigenen Custom-Tags annotiert werden.
  - Backend: `Tag`- und `EntryTag`-Modelle mit `TagCategory`-Enum (`sport`/`social`/`work`/`leisure`/`consumption`/`health`/`other`); Default-vs-Custom-Invariante über CHECK-Constraint (`is_default = true` ⇔ `user_id IS NULL`); Slug-Eindeutigkeit per partieller Unique-Indexe.
  - Migration `004_create_tags.py`: `tags`- und `entry_tags`-Tabellen, RLS-Policies (Public-Read für Defaults, Owner-Scoped CRUD für Custom-Tags) sowie Seed mit 30 kuratierten Default-Tags (Sport, Laufen, Familie, Alkohol, Meditation, …).
  - Service-Layer (`tag_service.py`) mit typisierten Exceptions (`TagNotFoundError`, `TagConflictError`, `TagOperationDeniedError`, `EntryNotFoundForTagError`, `TagsNotFoundError`); Replace-Set-Semantik für Tag-Zuweisungen, `MAX_TAGS_PER_ENTRY=50`.
  - Endpoints unter `/api/v1/tags` (`GET /default` ohne Auth; `GET /`, `POST /`, `PATCH /{id}`, `DELETE /{id}`) sowie `/api/v1/entries/{id}/tags` (`GET`, `PUT` Replace); Rate-Limit 60/min für Schreib- und 120/min für Lese-Operationen.
  - Pydantic-Schemas (`TagCreate`/`TagUpdate`/`TagResponse`/`EntryTagAssignment`) inkl. Slug-Normalisierung (lowercase, 2..64 Zeichen) und Hex-Color-Validierung.
  - Frontend: API-Client (`apps/web/src/lib/api/tags.ts`), Svelte-Store (`tags.ts` mit `idle/loading/ready/error` und nach Kategorie gruppiertem Derived Store), `TagPicker`-Komponente (Multi-Select Chips, Kategorie-Gruppierung, A11y via `aria-pressed`), Integration in `/entries/new` (Tag-Zuweisung erfolgt nach erfolgreichem Entry-Create, Fehler werden separat angezeigt).
  - i18n (`de.json`/`en.json`) um den `tag.*`-Block (Picker-Labels, Kategorie-Namen, Fehlertexte) erweitert.
  - Tests: 32 Backend-Tests (Schemas, Service, Endpoints, statischer Log-Scrubbing-Check) sowie 17 neue Frontend-Tests (API-Client, Store, gruppierter Derived Store).
  - API.md §4 vollständig auf den Issue-#8-Stand gebracht (alle Endpoints mit Request-/Response-Beispielen, Validierungsregeln, Fehlercodes, `TagResponse`-Schema).
- **Tägliches Eintrags-Formular** (Issue #7): Erste Kern-Funktion von M1.
  - Backend: `Entry`-Modell mit `EntrySlot` (`morning`/`midday`/`evening`/`unscheduled`)
    und `WorkContext` (`work_day`/`off_day`/`vacation`/`sick`); CHECK-Constraints für
    `mood_score`/`energy`/`stress` (1–5) und Unique-Constraint auf
    `(user_id, entry_date, slot)`. Migration `003_create_entries.py` legt Tabelle,
    Indizes und vier Row-Level-Security-Policies (`SELECT/INSERT/UPDATE/DELETE`)
    über `current_setting('app.current_user_id')` an.
  - Endpoints unter `/api/v1/entries` (`POST`, `GET /`, `GET /{id}`, `PATCH /{id}`)
    sämtlich hinter `get_current_verified_user`; Rate-Limit 60/min für Schreib- und
    120/min für Lese-Operationen.
  - Service-Layer (`entry_service.py`) mit typisierten Exceptions
    (`EntryNotFoundError`, `EntryConflictError`, `EntryReadOnlyError`,
    `EntryDateOutOfRangeError`); Backdate-Fenster `BACKDATE_DAYS_LIMIT=7`,
    Notiz-Maxlänge `MAX_NOTE_LENGTH=4000`.
  - Pydantic-Schemas (`EntryCreate`/`EntryUpdate`/`EntryResponse`); Wire-Feld
    `note_enc` wird via `validation_alias` auf das API-Feld `note` gemappt
    (Vorbereitung für App-Level-Encryption gemäß ADR-0005).
  - Frontend: API-Client (`apps/web/src/lib/api/entries.ts`), Svelte-Store
    (`entries.ts` mit `idle/loading/ready/error`), Formular-Page
    `/entries/new/+page.svelte` mit Datepicker (auf 7-Tage-Fenster begrenzt),
    drei `ScaleSlider`-Komponenten (1–5 mit +/--Buttons für Tastatur/A11y),
    Work-Context-Select mit Wochentag-Default, Notiz-Textarea (4000 Zeichen)
    und Fehler-Mapping für 401/409/422.
  - i18n (`de.json`/`en.json`) um den `entry.*`-Block erweitert.
  - Tests: 21 Backend-Tests (Service + Endpoints + statischer Log-Scrubbing-
    Check für `mood_score`/`energy`/`stress`/`note_enc`) und 12 Frontend-Tests
    (API-Client + Store).
  - API.md §3 vollständig auf den M1-Stand gebracht (4 implementierte Endpoints +
    2 geplante Operationen mit Request-/Response-Beispielen, Validierungsregeln,
    Fehlercodes, Backdate-Fenster).
- E-Mail-Verifikation komplett umgesetzt (Issue #39): `POST /api/v1/auth/verify-email`,
  `POST /api/v1/auth/resend-verification` (rate-limitiert 3/min/IP), Single-Use-Token
  in neuer Tabelle `email_verification_tokens` mit SHA-256-Hash + 24h TTL (ADR-0004).
  `POST /api/v1/auth/register` versendet Verify-Mail asynchron via BackgroundTask.
- MailPit-Service in `infra/docker/docker-compose.yml` als Dev/Test-SMTP-Catcher
  (Web-UI an `127.0.0.1:8025`, kein externer Zugriff).
- Verify-Mail-Templates (HTML + Plain-Text) in `backend/app/templates/email/`,
  ohne Tracking-Pixel und ohne externe Assets (DSGVO).
- `aiosmtplib`-basierter Async-`EmailService` ersetzt sync `emails`-Lib.
- Migration `002_create_email_verification_tokens.sql` (Cascade-Delete bei User-Erasure).
- API.md: vollständige Auth-Endpoint-Dokumentation; Phase-1-Native-JWT vs.
  Phase-2-OIDC-Block sauber getrennt (war zuvor inkonsistent).
- **Frontend-Auth-Flow** (Issue #40):
  - Zentraler `apiFetch`-Client mit `credentials: 'include'` + Single-Flight-Refresh auf 401.
  - Auth-API-Modul (`register`, `login`, `logout`, `fetchCurrentUser`, `verifyEmail`, `resendVerification`).
  - Auth-Store (`loading | authenticated | anonymous`) mit `hydrate()`, abgeleitete Stores (`currentUser`, `isAuthenticated`).
  - Routen: `/auth/login`, `/auth/register`, `/auth/check-email`, `/auth/verify-email`, `/auth/resend-verification`.
  - Auth-Layout für `/auth/*` (zentriert, ohne Hauptnavigation).
  - Reaktiver Auth-Guard im Root-Layout: Redirect auf `/auth/login?next=…` für geschützte Routen.
  - Verify-Page mit explizitem Confirm-Button (kein Auto-Submit — Schutz gegen Mail-Scanner).
  - Password-Strength-Indicator (Score 0–4, Live-Validierung gegen Backend-Regeln).
  - i18n-Strings für Auth-Flow (de/en).
  - Vitest-Suite: 24 Tests für Client, Store und Password-Strength.

### Fixed

- `infra/docker/.env.example` und `infra/docker/docker-compose.yml` konsistent mit `backend/app/core/config.py` gemacht (Issue #41):
  - MinIO-Env-Vars im API/Worker-Service vereinheitlicht (`MINIO_ENDPOINT`/`MINIO_ACCESS_KEY`/`MINIO_SECRET_KEY`/`MINIO_BUCKET_PHOTOS`/`MINIO_SECURE` statt der nirgends gelesenen `S3_*`-Variablen)
  - SMTP-Schema (`SMTP_HOST`/`SMTP_PORT`/`SMTP_USER`/`SMTP_PASSWORD`/`SMTP_FROM`) in `.env.example` dokumentiert (statt nicht gelesenem `EMAIL_URL`/`FROM_EMAIL`)
  - `CORS_ORIGINS`, `APP_VERSION`, `DEBUG`, `JWT_ALGORITHM` in `.env.example` ergänzt
  - Compose erzwingt jetzt explizit `ENCRYPTION_KEY` als Pflichtvariable (`:?error`)
  - Anmerkung: Der ursprüngliche `SECRET_KEY`/`JWT_SECRET`-Mismatch war bereits durch `AliasChoices` in `config.py` behoben — Restscope war Vollständigkeits-Check
- CI-API-Workflow scheiterte mit `Failed to spawn pytest`, weil `uv sync --dev` Dev-Dependencies aus `[project.optional-dependencies]` nicht installiert (uv 0.5+ erwartet PEP 735 `[dependency-groups]` für `--dev`). Workflow nutzt jetzt `uv sync --extra dev --frozen`, damit Dev-Tools (pytest/mypy/ruff) deterministisch aus dem Lockfile installiert werden.
- `backend/uv.lock` regeneriert: war noch auf altem Stand mit `emails`-Paket, obwohl der Email-Service in Issue #39 bereits auf `aiosmtplib` + `jinja2` migriert wurde. Lock entspricht jetzt wieder `pyproject.toml`.
- Bestehende Backend-Dateien (`auth_service.py`, `tests/test_auth.py`, `tests/test_email_verification.py`) gemäß `ruff format`-Standard formatiert — wurden vom Format-Check im CI-Lint-Job sonst gerejected.
- Auth-UI-Dateien (`apps/web/src/lib/api/client.ts` + Tests, `apps/web/src/lib/stores/auth.ts`, `apps/web/src/routes/auth/{+layout,check-email,verify-email}/...`) sowie zugehörige Doku (`docs/FRONTEND.md`, `docs/adr/0006-...`, `docs/adr/README.md`) gemäß Prettier-Standard formatiert — wurden vom CI-Web-Format-Check sonst gerejected.
- `@eslint/js` zur Root-`devDependencies` ergänzt (Issue #46): `eslint.config.js` importierte das Paket bereits, es war aber nicht deklariert. Daher schlug `pnpm lint` (auch im CI-Web-Lint-Job) seit M0 mit `ERR_MODULE_NOT_FOUND` fehl. ESLint 9 liefert die `js`-Recommended-Configs nur noch über das separate `@eslint/js`-Paket.

### Security

- Verify-Endpoint gibt einheitlich `Invalid or expired verification token` (kein
  Detail über Ursache) — verhindert Enumeration.
- Resend-Endpoint antwortet immer mit generischem 202 — verhindert E-Mail-Enumeration.
- Plaintext-Token wird nie persistiert, nur SHA-256-Hash; Token-Versand ausschließlich über Mail.
- **DSGVO Log-Scrubbing-Test** (`backend/tests/test_log_scrubbing.py`) als M1-DSGVO-Checkpoint-Absicherung ergänzt. Prüft das fixe JSON-Log-Schema gegen Top-Level-Key-Whitelist, blockt `extra=`-Leaks von Health-Daten, deckt Exception-Logging ohne User-Daten ab und scannt Production-Code auf `print()`-Aufrufe sowie auf Logger-Templates mit sensiblen Feldnamen (`mood_score`, `note_enc`, `password_plain`, ...). Schliesst M1-DSGVO-DoD `Keine Klartextloggung von Mood-/Symptom-Werten in App-Logs`.

### Changed

- **Code-Quality-Cleanup nach M1-Vorbereitung** (Issues #49 vorbereitend, kein neuer Issue):
  - SlowAPI-`Limiter` in neues Modul `backend/app/core/rate_limit.py` extrahiert.
    Vorher wurde der `Limiter(key_func=get_remote_address)` doppelt instanziert
    (`app/main.py` und `app/api/v1/endpoints/auth.py`) — funktional unauffällig
    mit dem aktuellen In-Memory-Backend, aber konzeptuell falsch und würde beim
    Wechsel auf einen geteilten Redis-Storage zwei separate State-Buckets erzeugen.
    Beide Stellen importieren jetzt dieselbe Instanz.
  - Schwergewichts-Dependencies (`pandas`, `scikit-learn`, `scipy`, `apscheduler`)
    aus `[project.dependencies]` in neue Optional-Group `analytics` verschoben.
    Diese Libraries werden im aktuellen M0/M1-Code an keiner Stelle importiert
    und sparen ~150–200 MB Image-Size sowie deutlich verkürzte `uv sync`-Zeiten
    in CI. Aktivierung erfolgt automatisch sobald ADR-0006-Insights-Worker (M2+)
    startet — dann via `uv sync --extra analytics`.
  - Test-Factories in zentrales `backend/tests/conftest.py` extrahiert
    (`make_user`, `make_verification_token`, `make_db_session_with_results`,
    `async_client`-Fixture, Token-Konstanten). Vorher waren `_make_user` /
    `_make_token` / `_make_db_with_token` 2× leicht abweichend in `test_auth.py`
    und `test_email_verification.py` dupliziert; das `AsyncClient`-Setup wurde
    in 17 Tests wörtlich kopiert. M1-Test-Suite (Entries/Tags/Symptome) baut
    jetzt direkt auf den Fixtures auf.
  - Frontend: `mapApiError(err, statusMap)`-Helper in `apps/web/src/lib/utils/error.ts`
    konsolidiert vier nahezu identische `mapError`-Funktionen aus den Auth-Pages
    (`login`, `register`, `verify-email`, `resend-verification`). Reduziert
    Boilerplate, vereinheitlicht den Fallback-Pfad (`error.generic`) und ist mit
    7 Vitest-Tests abgedeckt.

### Documentation

- **DESIGN_DOCUMENT.md §9 "Definition of Done" um Quality-Gate erweitert**: Pro Milestone
  ist nun ein Code-Quality-Review (CQR) und ein Security-Audit (SA) verpflichtend.
  CQR prüft u.a. Reuse/DRY, Test-Factories, Library-Hygiene, Konsistenz, Coverage-Schwellen
  (≥70% gesamt / ≥85% Auth+Sync+Krypto), statische Analyse (ruff, mypy, ESLint, svelte-check)
  und CHANGELOG-Pflege. SA prüft Auth-Coverage aller neuen Endpoints, Input-Validation,
  Rate-Limiting, Healthchecks (3-Tier nach ADR-0007), Logging-Hygiene (kein PII/Secrets,
  ADR-0007 Scrubbing), DSGVO-Pfade, Anti-Enumeration-Pattern, Security-Headers/Cookies,
  Dependency-Scan (`pip-audit`, `pnpm audit`) und Secrets-Scan. Jeder Milestone-
  Akzeptanzkriterienblock (M0–M12) erhält eine Quality-Gate-Checkbox; M0 ist retroaktiv
  durch ADR-0007, PR #51 und PR #52 abgedeckt.
- ADR-0005 (Verschlüsselung at-rest) re-evaluiert und nachgeschärft (2026-05-04):
  - Bedrohungsmodell-Tabelle hinzugefügt
  - Begründung gegen pgcrypto explizit dokumentiert (Connection-Pool-Risiko, teure Key-Rotation, pro-User-Key-Overhead)
  - Konkretes Schlüssel-Rotationsverfahren via `MultiFernet.rotate()` mit Code-Skizze
  - Datenmodell-Erweiterung `user_encryption_keys` definiert (KEK/DEK-Pattern)
  - Cryptographic-Erasure-Hinweis für Account-Löschung (Art. 17 DSGVO)
- DESIGN_DOCUMENT.md: D-011 von „Offen“ auf „Entschieden“ gesetzt; DSGVO-01 als entschieden markiert; Version 0.7
- DESIGN_DOCUMENT.md: M0/M1-Definition-of-Done konsistent gemacht — Issues #39 (E-Mail-Verifikation, PR #44), #40 (Login/Register-UI, PR #45) und #41 (`.env.example`/`SECRET_KEY`, PR #43) als `[x]` mit PR-Verweis markiert.
- Prettier-Konformität: `docs/API.md` und `docs/adr/0005-verschluesselung-at-rest.md` formatiert (kein semantischer Inhalt geändert, nur Whitespace/Tabellen-Alignment).
- **Neuer ADR-0007 "Healthchecks und strukturiertes Logging"** angelegt; dokumentiert das seit PR #35 gelebte 3-Tier-Healthcheck-Pattern, das JSON-Log-Schema und die Request-ID-Middleware. Schliesst die Doku-Lücke, dass DESIGN_DOCUMENT.md an drei Stellen auf eine nicht existierende `ADR-0003-healthchecks-and-logging.md` verwies.
- Tote ADR-Pfade in `docs/DESIGN_DOCUMENT.md` korrigiert: D-008 → [ADR-0002](docs/adr/0002-capacitor-statt-twa.md) (war `0002-mobile-strategie-capacitor-vs-twa.md`), D-009 → [ADR-0003](docs/adr/0003-sync-conflict-log.md) (war `0003-sync-conflict-handling.md`); Status von D-008/D-009 auf `✅ Entschieden` aktualisiert (passend zu den existierenden Accepted-ADRs).
- Risiko-Tabelle aktualisiert: SEC-02 (`SECRET_KEY`-Mismatch, PR #43), SW-01 (Sync-Conflict-Log, ADR-0003 + Issue #24), ZS-01 (TWA → Capacitor, ADR-0002) jeweils auf `✅ behoben`.
- ADR-Verzeichnis-Listing in der Repo-Tree-Skizze (Abschnitt 3.6) auf den tatsächlichen Stand (0001–0007) gebracht.

---

## [0.6.0] — M0 Fundament — 2026-04-28

### Added

- Initiales Monorepo-Setup
- Docker Compose Stack (Traefik, FastAPI, SvelteKit, PostgreSQL, Redis, MinIO)
- Authentik OIDC-Integration
- Basis-Dokumentation: DESIGN_DOCUMENT, ARCHITECTURE, API, FRONTEND, MARKET_ANALYSIS
- Architecture Decision Records (ADR) Framework
- `.env.example` für Selfhost-Setup
- GitHub Issue-Templates
- CONTRIBUTING.md

### Infrastructure

- Verzeichnisstruktur: `apps/web`, `apps/android`, `backend/app`, `backend/migrations`, `backend/workers`, `infra/docker`, `docs/adr`

---

_Nächstes Release: see `[Unreleased]` above. **v1.0.0** tag documented in [`docs/selfhost/GO_PUBLIC_CHECKLIST.md`](docs/selfhost/GO_PUBLIC_CHECKLIST.md) — push post-merge to `main`._

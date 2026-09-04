# Play Console Bootstrap (AP-1 / #719)

Last updated: 2026-09-04

Operator runbook for **M11 Internal Testing**: create the Play app, enroll
Play App Signing with the existing CI upload key, and publish the first AAB.

Tracking: [#719](https://github.com/Sturmi77/correlcore/issues/719) · umbrella
[#717](https://github.com/Sturmi77/correlcore/issues/717) · checklist
[`docs/selfhost/M11_OPS_CHECKLIST.md`](../selfhost/M11_OPS_CHECKLIST.md) C ·
gap analysis [`docs/M11_PLAY_STORE_GAP_ANALYSIS.md`](../M11_PLAY_STORE_GAP_ANALYSIS.md) §5.

> **Agent vs operator:** Everything below that needs a Google login, $25, or
> Console clicks is **👤 Operator only**. Agent-verified prep is marked ✅.

---

## Preconditions (verified 2026-09-04)

| Item                                            | Status                                                                                     |
| ----------------------------------------------- | ------------------------------------------------------------------------------------------ |
| AP-HC (#718) Option A — `play` flavor HC-free   | ✅ Done                                                                                    |
| Package ID `de.correlcore.app`                  | ✅ `apps/android/android/app/build.gradle`                                                 |
| CI publishes play AAB as `correlcore-<ver>.aab` | ✅ `release-android.yml` → `bundlePlayRelease`                                             |
| Latest Release has AAB                          | ✅ `v1.6.0` → `correlcore-1.6.0.aab`                                                       |
| versionCode formula monotonic                   | ✅ `MAJOR×1e6 + MINOR×1e3 + PATCH` (see § Version mapping)                                 |
| Listing copy draft                              | ✅ [`docs/marketing/PLAY_STORE_LISTING.md`](../marketing/PLAY_STORE_LISTING.md) (AP-2)     |
| Data Safety mapping draft                       | ✅ [`docs/legal/PLAY_DATA_SAFETY_MAPPING.md`](../legal/PLAY_DATA_SAFETY_MAPPING.md) (AP-3) |

**Upload this AAB:**  
https://github.com/Sturmi77/correlcore/releases/download/v1.6.0/correlcore-1.6.0.aab  
(`versionName` `1.6.0` → `versionCode` **1006000**)

Do **not** upload the `.apk` to Play — that asset is the **sideload** (HC) flavor.

---

## Version mapping (tag → versionCode)

From [`.github/workflows/release-android.yml`](../../.github/workflows/release-android.yml):

```text
versionCode = MAJOR * 1_000_000 + MINOR * 1_000 + PATCH
```

| Tag    | versionName | versionCode   |
| ------ | ----------- | ------------- |
| v1.2.1 | 1.2.1       | 1_002_001     |
| v1.3.0 | 1.3.0       | 1_003_000     |
| v1.4.0 | 1.4.0       | 1_004_000     |
| v1.5.0 | 1.5.0       | 1_005_000     |
| v1.6.0 | 1.6.0       | **1_006_000** |

Play rejects non-monotonic `versionCode`. After the first upload, every later
`v*` tag must be strictly greater (normal SemVer tags already are).

Manual `workflow_dispatch` **without** `attach_to_tag` uses `GITHUB_RUN_NUMBER`
as `versionCode` — do **not** upload those AABs to Play unless you have checked
they still sort above the last Play version.

---

## Upload-key fingerprint (before or during App Signing)

The CI keystore (`ANDROID_KEYSTORE_*` secrets) **is** the Play upload key.
Print its SHA-256 certificate fingerprint from your offline keystore backup:

```bash
# From repo root (or any machine with the .keystore file + JDK keytool):
apps/android/scripts/print-upload-cert-fingerprint.sh /path/to/correlcore-upload.keystore correlcore
# Prompts for store password, or pass -storepass via env (see script header).
```

Or directly:

```bash
keytool -list -v \
  -keystore /path/to/correlcore-upload.keystore \
  -alias correlcore
# → Certificate fingerprints → SHA-256: …
```

In Play Console → **Setup → App integrity → App signing**, the **Upload key
certificate** SHA-256 must match this value.

---

## Operator steps (Console)

### 1. Developer account

1. Open https://play.google.com/console
2. Accept the developer agreement and pay the **$25** one-time fee
3. Complete identity verification if prompted

### 2. Create the app

1. **Create app**
2. App name: **CorrelCore** (store listing can refine later)
3. Default language: German or English (your choice; listing has both)
4. App or game: **App**
5. Free / paid: **Free**
6. Declarations: accept Play policies / US export as applicable
7. **Package name must be exactly `de.correlcore.app`**  
   (set when creating the app / first upload — must match Gradle `applicationId`)

### 3. Play App Signing

Recommended (and assumed by this repo):

- **Google-managed app signing key**
- **Your CI keystore = upload key** (same key that signs GitHub Release APKs)

Enrollment usually happens on the **first AAB upload** (Play asks you to
opt in). Prefer “use the signing key from this AAB as the upload key” / let
Play generate the app signing key.

Document the choice on #717 when done:  
`Play App Signing: Google-managed app key + CI upload key (correlcore alias)`.

### 4. First Internal Testing upload

1. Download `correlcore-1.6.0.aab` from the GitHub Release (link above)
2. Play Console → **Testing → Internal testing → Create new release**
3. Upload the **AAB** (not the APK)
4. Release name: `1.6.0 (1006000)` or Play’s default from the bundle
5. Save → **Review release** → **Start rollout to Internal testing**
6. Confirm App integrity shows upload-key SHA-256 matching § fingerprint

### 5. Testers + install smoke

1. Internal testing → **Testers** → create a list (e.g. `owner`)
2. Add your Google account email (and any early testers)
3. Copy the **opt-in link**, open it on a Play-services device, accept
4. Install CorrelCore from the Play Store (Internal track)
5. Smoke: open app → login against `https://app.correlcore.com` (or your API) → create one entry

---

## Exit criterion (#719)

- [ ] Internal testing track live with installable AAB
- [ ] Owner installed from Internal track on a real device
- [ ] Upload-key fingerprint verified against CI keystore
- [ ] App Signing choice noted on #717

Then close #719 with `Closes #719` on a follow-up comment / housekeeping PR,
or `gh issue close 719` after the install smoke.

**Next:** AP-2 screenshots/graphics (#720) and AP-3 Data Safety form (#721) —
drafts exist; Console fields still need Operator fill-in. Then AP-5 (#723).

---

## Common pitfalls

| Pitfall                                                    | Fix                                                                  |
| ---------------------------------------------------------- | -------------------------------------------------------------------- |
| Uploading `.apk` instead of `.aab`                         | Use `correlcore-*.aab` only                                          |
| Package ID typo                                            | Must be `de.correlcore.app`                                          |
| New keystore for Play                                      | Breaks sideload update continuity; use existing CI key as upload key |
| Uploading a `workflow_dispatch` AAB with low `versionCode` | Stick to `v*` Release AABs                                           |
| Expecting HC in Play build                                 | Play flavor is HC-free by design (#718 Option A)                     |

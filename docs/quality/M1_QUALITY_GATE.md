# M1 Quality-Gate — Code-Quality-Review + Security-Audit

**Milestone:** M1 — Core Entry (Mood-Logging, Tags, Symptome, App-Level-Verschlüsselung)
**Stand:** 2026-05-07 (alle Findings geschlossen, M1-Review-bereit)
**Audit-Basis-Commit:** [`a48966c`](https://github.com/Sturmi77/moodsync/commit/a48966c) (`main`, post #50, Audit-Stand 2026-05-04)
**Schließungs-Commit:** [`2b520cf`](https://github.com/Sturmi77/moodsync/commit/2b520cf) (`main`, post #106 / SA-5)
**Referenz:** [`docs/DESIGN_DOCUMENT.md` §9](../DESIGN_DOCUMENT.md) — Quality-Gate-Definition

Dieses Dokument bündelt den gemäß Design-Doc §9 verpflichtenden **Code-Quality-Review (CQR)** und **Security-Audit (SA)** für M1. Findings sind nach Severity klassifiziert und entweder im selben Milestone gefixt **oder** als getracktes Folge-Issue dokumentiert. Alle 12 Findings (6 CQR + 6 SA) sind zum Stichtag 2026-05-07 vollständig geschlossen — der M1-Quality-Gate-Checkpoint im Design-Doc steht damit auf `[x]`.

---

## 1. Scope

M1-Inhalte (gemäß Design-Doc §3):

| Bereich                      | Issues / PRs                  | Status |
| ---------------------------- | ----------------------------- | ------ |
| Auth (Native JWT)            | #38, #39, #40, #41, #43       | done   |
| Mood-Entries                 | #7                            | done   |
| Custom-Tags                  | #8 (PR #46), #57 (PR #58)     | done   |
| Custom-Symptome              | #57 (PR #58)                  | done   |
| Symptom-Checkliste 0–3       | #9 (PR #56)                   | done   |
| App-Level Fernet at-rest     | #26 (PR #61), ADR-0005        | done   |
| API-Doku-Konsistenz          | #50 (PR #63)                  | done   |
| Roadmap-Cleanup (Offline→M4) | #10/#24 verschoben (ADR-0009) | done   |
| CI für docs-only-PRs         | #49 (PR #59)                  | done   |

Ausserhalb des M1-Scope (zur Vermeidung von Falsch-Erwartungen):

- Foto-Upload mit EXIF-Strip → **M6**
- Health-Connect / Wearables → **M7**
- Offline-Sync (Dexie + Conflict-Log) → **M4** (ADR-0009)
- DSFA-Dokument → **M9**
- OIDC / Authentik → **M12**

---

## 2. Code-Quality-Review (CQR)

### 2.1 Statische Analyse

| Tool                              | Ergebnis                         |
| --------------------------------- | -------------------------------- |
| `ruff check .` (backend)          | **All checks passed**            |
| `ruff format --check .` (backend) | **62 files already formatted**   |
| `mypy app` (backend, default)     | **Success: no issues, 43 files** |
| `mypy --strict app` (backend)     | **Success: no issues, 43 files** |
| `prettier --check .` (root)       | **All matched files**            |
| `eslint .` (apps/web)             | clean                            |
| `svelte-check` (apps/web)         | **0 errors, 0 warnings**         |

`mypy --strict` ist clean — das Quality-Gate-Kriterium ist damit nicht nur formal, sondern strikt erfüllt.

### 2.2 Testabdeckung

**Audit-Stand 2026-05-04 (Repo `a48966c`, vor Issue-Pakete #64/#67/#68/#70):** `pytest --cov=app` lieferte **156 passed**, Total-Coverage **85.04 %** (Threshold: 70 % global, 85 % für Auth/Sync/Krypto). Auth-spezifischer 85 %-Threshold **nicht erreicht** — primärer CQR-Blocker.

**Schließungs-Stand 2026-05-07 (Repo `2b520cf`, post #106):** `pytest --cov=app` liefert **288 passed**, Total-Coverage **96.11 %**. Alle kritischen Pfade ≥ 85 %; sicherheitskritische Auth- und Crypto-Module bei 95–100 %.

Aufschlüsselung der kritischen Pfade (Stichtag 2026-05-07):

| Modul                              | Coverage  | Schwellwert | Status                             |
| ---------------------------------- | --------- | ----------- | ---------------------------------- |
| `app/core/crypto.py`               | **96 %**  | 85 %        | ✅                                 |
| `app/api/v1/endpoints/auth.py`     | **100 %** | 85 %        | ✅                                 |
| `app/services/symptom_service.py`  | **99 %**  | 85 %        | ✅                                 |
| `app/services/tag_service.py`      | **100 %** | 85 %        | ✅                                 |
| `app/services/entry_service.py`    | **97 %**  | 85 %        | ✅                                 |
| `app/api/v1/endpoints/entries.py`  | **96 %**  | 70 %        | ✅                                 |
| `app/api/v1/endpoints/tags.py`     | **98 %**  | 70 %        | ✅                                 |
| `app/api/v1/endpoints/symptoms.py` | **92 %**  | 70 %        | ✅                                 |
| `app/services/auth_service.py`     | **95 %**  | 85 %        | ✅ (vorher 47 %, behoben über #64) |
| `app/api/v1/deps/auth.py`          | **100 %** | 85 %        | ✅ (vorher 38 %, behoben über #64) |
| `app/core/security.py`             | **100 %** | 70 %        | ✅ (vorher 58 %, behoben über #64) |
| `app/services/email_service.py`    | **100 %** | 70 %        | ✅ (vorher 39 %, behoben über #70) |
| `app/services/health_service.py`   | **100 %** | 70 %        | ✅ (vorher 59 %, behoben über #70) |

**Gesamt-Threshold (70 % global): erreicht.** Auth-spezifischer 85 %-Threshold **erreicht** (auth_service.py 95 %, deps/auth.py 100 %, core/security.py 100 %, core/crypto.py 96 %).

### 2.3 Library-Hygiene

| Bereich  | Befund                                                                                                                                                                                                                                                                                               |
| -------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Backend  | Neue Dependency in M1: `cryptography` (für Fernet, ADR-0005). Dokumentiert in `pyproject.toml` und ADR-0005. Keine ungenutzten Dependencies in `pyproject.toml`.                                                                                                                                     |
| Frontend | `svelte@^5.0.0` läuft jetzt mit `@sveltejs/vite-plugin-svelte@^4.0.0` (resolved 4.0.4). Plugin-Warning `Active Svelte 5 support has moved to vite-plugin-svelte@4` ist beseitigt. ✅ (CQR-6 behoben über #71/PR #103). v5/v6 würde einen Vite-Major-Bump erzwingen und wird separat in M2+ getrackt. |

### 2.4 Reuse / DRY / Konsistenz

- **Custom-Symptome** (#57) wurden 1:1 nach dem Tag-System (#8) modelliert (gleiches RLS-Pattern, gleiche Slug-Validation, analoge Service-API, parallele Endpoint-Struktur). Konsistent. ✅
- **EncryptedString-TypeDecorator** (#26) konsolidiert die Crypto-Round-Trip-Logik für `entries.note_enc` und ist explizit nicht für `symptoms.name_enc` verwendet, weil Default-Reads ohne DEK funktionieren müssen — die Asymmetrie ist in ADR-0005 begründet.
- **Auth-Cookie-Helper** (`_set_auth_cookies`/`_clear_auth_cookies` in `endpoints/auth.py`) sind privat im Endpoint-Modul. Reuse-Bedarf entsteht erst, wenn ein zweiter Auth-Pfad (OIDC, M12) hinzukommt — bewusst kein Premature-Refactor.
- **Test-Factories**: `make_symptom`/`make_tag`/`make_user` sind in `tests/conftest.py` als Fixtures vorhanden; #26 hat `_bind_test_dek` autouse ergänzt, sodass alle bis dahin bestehenden 156 Tests ohne Anpassung weiterlaufen. Mit den Test-Erweiterungen aus #64/#67/#70 liegt die Suite jetzt bei 288 Tests, die Fixture-Architektur trägt diese Last ohne Refactor weiter.

### 2.5 CHANGELOG

`CHANGELOG.md` enthält für M1 dedizierte Einträge unter `[Unreleased] — M1 Vorbereitung` mit Sektionen `Added` / `Changed` / `Fixed` / `Tests` / `Security` / `Documentation`. Keep-a-Changelog-Format. ✅ Sämtliche im M1-Quality-Gate adressierten Findings (#64–#71) haben dedizierte Einträge mit Begründung, Trade-Off-Diskussion und Test-Coverage-Vermerk.

### 2.6 CQR-Findings

| ID    | Severity  | Beschreibung                                                                                                                                 | Status                                                                                                                                                                                                                                                                                    |
| ----- | --------- | -------------------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| CQR-1 | **major** | `auth_service.py` Coverage 47 % statt geforderter 85 %. Ungetestet: `register_user`-Edge-Cases, Verifikations-Flow, Token-Rotation in Redis. | ✅ **Closed** über [#64](https://github.com/Sturmi77/moodsync/issues/64) — `auth_service.py` jetzt 95 % (23 neue Unit-Tests in `tests/test_auth_service.py`).                                                                                                                             |
| CQR-2 | **major** | `deps/auth.py` Coverage 38 %. Token-Validation, DEK-Bind, 401-Pfade ungetestet.                                                              | ✅ **Closed** über [#64](https://github.com/Sturmi77/moodsync/issues/64) — `deps/auth.py` jetzt 100 % (17 neue Unit-Tests in `tests/test_auth_deps.py`).                                                                                                                                  |
| CQR-3 | minor     | `core/security.py` 58 %. Password-Hashing/-Verify und Token-Helper laufen indirekt, aber keine direkten Edge-Case-Tests.                     | ✅ **Closed** über [#64](https://github.com/Sturmi77/moodsync/issues/64) — `core/security.py` jetzt 100 % (13 neue Unit-Tests in `tests/test_security.py`).                                                                                                                               |
| CQR-4 | minor     | `email_service.py` 39 %. SMTP-Pfad ist im Test gemockt, Fehlerpfade ungetestet.                                                              | ✅ **Closed** über [#70](https://github.com/Sturmi77/moodsync/issues/70) / PR #104 — `email_service.py` jetzt 100 % (14 neue Unit-Tests in `tests/test_email_service.py` decken Dev-Fallback, Happy-Path, vier SMTP-Fehlerklassen, Public-API-Templates inkl. Anti-Enumeration-Garantie). |
| CQR-5 | minor     | `health_service.py` 59 %. Postgres/Redis-Probe-Fehlerpfade nicht abgedeckt.                                                                  | ✅ **Closed** über [#70](https://github.com/Sturmi77/moodsync/issues/70) / PR #104 — `health_service.py` jetzt 100 % (12 neue Unit-Tests in `tests/test_health_service.py`); zusätzlich Encryption-Probe-Tests aus #68/PR #106 enthalten.                                                 |
| CQR-6 | minor     | Frontend `vite-plugin-svelte@3` mit Svelte 5 — Plugin selbst empfiehlt v4.                                                                   | ✅ **Closed** über [#71](https://github.com/Sturmi77/moodsync/issues/71) / PR #103 — Plugin-Update auf `^4.0.0` (resolved 4.0.4); Plugin-Warning verschwindet aus `pnpm build`/`pnpm lint`/`pnpm typecheck`. Major-Bump auf v5/v6 erfordert Vite-Major-Bump → separat M2+ getrackt.       |

---

## 3. Security-Audit (SA)

### 3.1 Auth-Coverage / RLS-Pfad

- Alle nicht-öffentlichen Endpoints sind hinter `get_current_user` oder `get_current_verified_user` (Entries, Tags, Symptome). ✅
- Öffentlich (bewusst): `POST /auth/register`, `POST /auth/login`, `POST /auth/verify-email`, `POST /auth/resend-verification`, `POST /auth/refresh`, `POST /auth/logout`, `GET /symptoms/default`. ✅
- RLS-Policies vorhanden für `users`, `entries`, `tags`, `entry_tags`, `symptoms`, `entry_symptoms`, `user_encryption_keys`, `email_verification_tokens` (Migrationen 002–007). ✅

### 3.2 Input-Validation

Alle Schemas (`app/schemas/*`) nutzen `Field`-Constraints:

- `RegisterRequest.password` 8–128, mindestens 1 Buchstabe + 1 Ziffer (Validator)
- `RegisterRequest.display_name` ≤ 100
- `VerifyEmailRequest.token` 16–128
- `EntryCreate` mood/energy/stress als bounded `int`
- `TagCreate.name` 1–80, slug-regex
- `SymptomCreate.name` 1–80, slug-regex, `MAX_SYMPTOMS_PER_USER=50`, `MAX_TAGS_PER_USER=50`, `MAX_SYMPTOMS_PER_ENTRY=32`

Keine Lücken identifiziert. ✅

### 3.3 Rate-Limiting

| Endpoint                         | Limit        | Quelle                                 |
| -------------------------------- | ------------ | -------------------------------------- |
| `POST /auth/register`            | 5 / min / IP | `endpoints/auth.py` — über #65 ergänzt |
| `POST /auth/login`               | 5 / min / IP | `endpoints/auth.py:197`                |
| `POST /auth/resend-verification` | 3 / min / IP | `endpoints/auth.py:165`                |
| `POST /entries`                  | 60 / min     | siehe `docs/API.md`                    |
| `GET /entries`                   | 120 / min    | siehe `docs/API.md`                    |
| `PATCH /entries`                 | 60 / min     | siehe `docs/API.md`                    |

`POST /auth/register` ist seit #65 rate-limitiert (5/min/IP, identisch zu `/login`); kombiniert mit der enumeration-safen `202`-Response (siehe SA-1) ist der Mass-Enumeration-Vektor geschlossen. ✅

### 3.4 Healthchecks

`/health/ready` prüft seit #68 (PR #106) Postgres + Redis + **Encryption**. Die neue dritte Probe `_probe_encryption` führt einen vollständigen Master-Fernet-Roundtrip aus (`generate_dek()` → `wrap_dek()` → `unwrap_dek()` → Byte-Vergleich). Damit kippt das Ready-Signal jetzt bereits dann auf 503, wenn der Master-Encryption-Key fehlt, ungültig ist oder ein Roundtrip-Mismatch auftritt — vor #68 hätte derselbe Defekt bei `/health/ready` weiter `200 OK` geliefert und erst beim ersten authentifizierten Request mit 401 (DEK unwrap failed) sichtbar werden können. `detail` enthält ausschließlich den Exception-Klassennamen (ADR-0007: niemals Settings-Dump, Key-Material oder Plain-/Ciphertext). Probe ist synchronous (Fernet ist CPU-bound, Mikrosekunden) — keine messbare Endpoint-Latenz. SA-5 ✅ closed.

### 3.5 Logging-Hygiene

`tests/test_log_scrubbing.py` deckt nach #67 (PR #105) sämtliche M1-relevanten Felder ab:

- **Mood/Energy/Stress/Note:** `mood_score`, `energy_level`, `stress_level`, `note_enc`, `symptom_intensity`, `hashed_password`, `password_plain`
- **Tags (#8):** `tag.name` und `tag.slug` als Forbidden-Sentinels (Custom-Tag-Klartext-Beispiel `Stress bei Arbeit` / `stress-bei-arbeit`)
- **Custom-Symptome (#57):** `symptom.name` (Custom-Klartext `Migräne mit Aura`), `symptom.slug` (`migraene-mit-aura`, semantischer Leak laut ADR-0005-Trade-off)
- **Encryption (#26):** `name_enc` BYTEA-Sentinel `name_enc_ciphertext_bytes`, `wrapped_dek` BYTEA-Sentinel `wrapped_dek_ciphertext_bytes`
- **Repr-Stripping** auf `Entry`, `EntrySymptom`, `Symptom`, `Tag`, `UserEncryptionKey`. `Tag.__repr__` und `Symptom.__repr__` liefern für User-eigene Einträge `slug=<custom>` statt des Klartext-Slugs (Default-Einträge unverändert).
- **Anti-Pattern-Regex:** `name_enc` und `wrapped_dek` als verbotene f-String-Tokens in `logger.X(...)`

Test-Erweiterung von 6 auf 12 Tests in `test_log_scrubbing.py`. SA-3 ✅ closed.

### 3.6 DSGVO-Pfad / Erasure

- ✅ Cryptographic Erasure ist auf DB-Ebene implementiert: `user_encryption_keys.user_id ON DELETE CASCADE` macht alle `entries.note_enc` und `symptoms.name_enc` (Custom) eines Users in einer Bewegung unentschlüsselbar. ADR-0005 dokumentiert das. Migration 007 setzt RLS so, dass User die Row weder selbst inserten noch löschen können.
- ✅ **API-Endpoint für Account-Löschung implementiert** über [#66](https://github.com/Sturmi77/moodsync/issues/66): `DELETE /api/v1/user/me` mit Re-Auth via Passwort, Refresh-Token-Revoke (vor DB-DELETE für Force-Logout-Garantie auch bei späterem DB-Fehler) und Cascade-Delete über alle abhängigen Tabellen inkl. `user_encryption_keys`. Default-Tags/Symptome (`user_id IS NULL`) bleiben erhalten. Statuscodes `204` Erfolg, `401` für fehlende Auth oder falsches Passwort (generische `Invalid credentials`-Meldung), `422` für Body-Validierung. Logs nur `user_id`, niemals Email — durch zwei dedizierte Tests abgesichert. SA-4 ✅ closed.

### 3.7 Anti-Enumeration

| Endpoint                         | Verhalten                                                                                                                                                                                      | Status             |
| -------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------ |
| `POST /auth/login`               | Generisches `Invalid email or password`, deckt unbekannte Mail + falsches Passwort + unverifizierten Account ab.                                                                               | ✅                 |
| `POST /auth/resend-verification` | Immer `202 Accepted`, identische Antwort egal ob Mail existiert.                                                                                                                               | ✅                 |
| `POST /auth/verify-email`        | Generisches `Invalid or expired verification token`.                                                                                                                                           | ✅                 |
| `POST /auth/register`            | Immer `202 Accepted` mit identischer Response — bei bestehender Adresse wird einmalig eine "Already-registered"-Notiz versandt (kein User-Create, keine Verify-Mail, kein Token-Wert im Body). | ✅ (#65 ✅ closed) |

SA-1 ✅ closed über [#65](https://github.com/Sturmi77/moodsync/issues/65): `409 Email already registered` ist ersatzlos entfallen. Service-Layer-Wrapper `request_registration` kapselt die Branch-Wahl in einem `RegistrationOutcome` ohne Exception. SA-2 ✅ closed über dasselbe Issue: Rate-Limit `5/min/IP` zusätzlich auf den Endpoint, identisch zu `/login`.

### 3.8 Headers / Cookies

- `access_token` Cookie: `HttpOnly; Secure; SameSite=Strict; Path=/api; Max-Age=900` ✅
- `refresh_token` Cookie: `HttpOnly; Secure; SameSite=Strict; Path=/api/v1/auth/refresh; Max-Age=2592000` — Pfad-Scope ist eng. ✅
- Refresh-Token-Logout/-Rotation löscht beide Cookies bei 401 in `/refresh`. ✅

### 3.9 Dependency-Scan

| Scan                                      | Befund (Audit-Stand 2026-05-04)                                                                                                                                                                                                                       | Befund (Schließungs-Stand 2026-05-07)                                                                                                                                                                                  |
| ----------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Backend `pip-audit` (sandbox-`.venv`)     | 3 Findings — alle in `pip` selbst (`pip 24.3.1`). pip ist Build-Tool, kein Runtime-Pfad der App. App-Dependencies (FastAPI, SQLAlchemy, cryptography, asyncpg, redis, slowapi, …) **ohne** Findings. CI nutzt `uv` statt pip — kein Container-Impact. | Unverändert: weiterhin nur pip-Tooling-Findings, App-Runtime ohne Findings.                                                                                                                                            |
| Frontend `pnpm audit --prod` (`apps/web`) | 1 moderate Finding: `esbuild ≤0.24.2` via `svelte-i18n` (GHSA-67mh-4wv8-2f99). Kein high/critical → Quality-Gate-Blocker nein, aber tracken. → SA-6                                                                                                   | ✅ **Closed** über [#69](https://github.com/Sturmi77/moodsync/issues/69) / PR #102 — `esbuild ^0.25.0` via `pnpm-overrides` (Workspace-File für pnpm 11). `pnpm audit --prod` meldet `No known vulnerabilities found`. |

### 3.10 Secrets-Scan / `.env.example`

- `.env.example` enthält `ENCRYPTION_KEYS=` mit Generierungsbefehl (`python -c 'from cryptography.fernet import Fernet; ...'`) und Rotation-Hinweis.
- `SECRET_KEY` als Env-Var, nicht im Repo.
- `JWT_SECRET`/`SECRET_KEY`-Mismatch ist seit #41/PR #43 behoben.
- Repo-Stichprobensuche nach `password=`, `secret=`, `api_key=` in committed code: keine Treffer. ✅

### 3.11 SA-Findings

| ID   | Severity  | Beschreibung                                                                                                    | Status                                                                                                                                                                                                                                                                              |
| ---- | --------- | --------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| SA-1 | **major** | `POST /auth/register` 409 leakt Email-Existenz (`Email already registered`).                                    | ✅ **Closed** über [#65](https://github.com/Sturmi77/moodsync/issues/65) — `409` entfällt ersatzlos, Endpoint liefert immer `202 Accepted` mit identischer Response. Bei bestehender Adresse einmalige "Already-registered"-Notiz ohne Token-Wert im Body.                          |
| SA-2 | minor     | `POST /auth/register` ist ungerate-limitiert — verstärkt SA-1.                                                  | ✅ **Closed** über [#65](https://github.com/Sturmi77/moodsync/issues/65) — Rate-Limit `5/min/IP` per SlowAPI ergänzt, identisch zu `/login`.                                                                                                                                        |
| SA-3 | minor     | Log-Scrubbing-Tests decken `name_enc`/`tag.name`/`tag.slug`/`symptom.slug` nicht ab.                            | ✅ **Closed** über [#67](https://github.com/Sturmi77/moodsync/issues/67) / PR #105 — `tests/test_log_scrubbing.py` von 6 auf 12 Tests erweitert; Forbidden-Sentinels und Anti-Pattern-Regex decken Tags, Custom-Symptome, `name_enc`, `wrapped_dek` ab; Repr-Stripping verifiziert. |
| SA-4 | **major** | Kein API-Endpoint `DELETE /user/me` für DSGVO-Art.-17-Erasure. Cryptographic Erasure ist nur DB-seitig wirksam. | ✅ **Closed** über [#66](https://github.com/Sturmi77/moodsync/issues/66) — `DELETE /api/v1/user/me` mit Re-Auth + Refresh-Token-Revoke + Cascade-Delete über alle abhängigen Tabellen inkl. `user_encryption_keys`.                                                                 |
| SA-5 | minor     | `/health/ready` prüft Encryption-Key-Verfügbarkeit nicht.                                                       | ✅ **Closed** über [#68](https://github.com/Sturmi77/moodsync/issues/68) / PR #106 — Neue Probe `_probe_encryption` mit Master-Fernet-Roundtrip; Ready-Signal kippt bei fehlendem/ungültigem `ENCRYPTION_KEY` jetzt korrekt auf 503.                                                |
| SA-6 | minor     | `esbuild` ≤ 0.24.2 (transitive via `svelte-i18n`) hat moderate Advisory.                                        | ✅ **Closed** über [#69](https://github.com/Sturmi77/moodsync/issues/69) / PR #102 — `esbuild ^0.25.0` via `pnpm-overrides` in `pnpm-workspace.yaml` (pnpm 11 liest Overrides nur noch dort, nicht aus `package.json`-`pnpm.overrides`). `pnpm audit --prod` clean.                 |

---

## 4. Ergebnis

| Bereich                 | Status (Audit 2026-05-04) | Status (Schließung 2026-05-07) |
| ----------------------- | ------------------------- | ------------------------------ |
| Statische Analyse       | ✅ bestanden              | ✅ bestanden                   |
| Coverage-Threshold 70 % | ✅ 85.04 %                | ✅ **96.11 %**                 |
| Coverage Auth/Krypto    | ⚠️ Krypto ✅, Auth ❌     | ✅ Auth + Krypto ≥ 95 %        |
| Library-Hygiene         | ⚠️ minor (CQR-6)          | ✅ vite-plugin-svelte@4        |
| Test-Factories          | ✅                        | ✅ (288 Tests grün)            |
| CHANGELOG-Eintrag       | ✅                        | ✅                             |
| Auth-Coverage / RLS     | ✅                        | ✅                             |
| Input-Validation        | ✅                        | ✅                             |
| Rate-Limiting           | ⚠️ register fehlt         | ✅ register 5/min/IP           |
| Healthchecks            | ⚠️ Crypto-Probe fehlt     | ✅ encryption probe live       |
| Logging-Hygiene         | ⚠️ Felder-Drift           | ✅ tags+symptoms+enc abgedeckt |
| DSGVO-Erasure-Pfad      | ❌ API fehlt              | ✅ `DELETE /api/v1/user/me`    |
| Anti-Enumeration        | ❌ register               | ✅ register 202-only           |
| Cookies/Headers         | ✅                        | ✅                             |
| Dependency-Scan         | ⚠️ esbuild moderate       | ✅ `pnpm audit --prod` clean   |
| Secrets-Scan            | ✅                        | ✅                             |

**Quality-Gate-Verdikt (Stand 2026-05-07):** **vollständig bestanden**. Alle 12 Findings (4 major + 8 minor) sind geschlossen — die Audit-Bewertung 2026-05-04 ("bestanden mit Auflagen") ist mit dem Merge der M1-Tail-PRs #102–#106 hinfällig.

**Zeitlinie der Findings-Schließung:**

| Datum      | Issue / PR                                                      | Findings                       |
| ---------- | --------------------------------------------------------------- | ------------------------------ |
| 2026-05-04 | Audit-Stichtag (Repo `a48966c`)                                 | 12 Findings angelegt (#64–#71) |
| 2026-05-04 | [#65](https://github.com/Sturmi77/moodsync/issues/65)           | SA-1, SA-2 ✅                  |
| 2026-05-04 | [#64](https://github.com/Sturmi77/moodsync/issues/64)           | CQR-1, CQR-2, CQR-3 ✅         |
| 2026-05-04 | [#66](https://github.com/Sturmi77/moodsync/issues/66)           | SA-4 ✅                        |
| 2026-05-07 | [#69](https://github.com/Sturmi77/moodsync/issues/69) / PR #102 | SA-6 ✅                        |
| 2026-05-07 | [#71](https://github.com/Sturmi77/moodsync/issues/71) / PR #103 | CQR-6 ✅                       |
| 2026-05-07 | [#70](https://github.com/Sturmi77/moodsync/issues/70) / PR #104 | CQR-4, CQR-5 ✅                |
| 2026-05-07 | [#67](https://github.com/Sturmi77/moodsync/issues/67) / PR #105 | SA-3 ✅                        |
| 2026-05-07 | [#68](https://github.com/Sturmi77/moodsync/issues/68) / PR #106 | SA-5 ✅                        |

Mit dem Schließen aller Findings ist der M1-Quality-Gate-Checkpoint im Design-Doc auf `[x]` gesetzt. M1 ist bereit für das Milestone-Review.

---

## 5. Reproduktion

```bash
# Backend
cd backend
APP_ENV=test \
  DATABASE_URL='postgresql+asyncpg://moodsync:moodsync@localhost:5432/moodsync' \
  REDIS_URL='redis://:changeme@localhost:6379/0' \
  SECRET_KEY='test-secret-key-min-32-bytes-long-padding' \
  ENCRYPTION_KEY='<gültiger Fernet-Key>' \
  uv run pytest --cov=app --cov-report=term -q

uv run ruff check .
uv run ruff format --check .
uv run mypy --strict app
PIPAPI_PYTHON_LOCATION=$PWD/.venv/bin/python uv run pip-audit --skip-editable

# Frontend
cd ..
pnpm format:check
pnpm -r lint
pnpm -r typecheck
pnpm -C apps/web audit --prod
```

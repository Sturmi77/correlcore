# M1 Quality-Gate — Code-Quality-Review + Security-Audit

**Milestone:** M1 — Core Entry (Mood-Logging, Tags, Symptome, App-Level-Verschlüsselung)
**Stand:** 2026-05-04
**Basis-Commit:** [`a48966c`](https://github.com/Sturmi77/moodsync/commit/a48966c) (`main`, post #50)
**Referenz:** [`docs/DESIGN_DOCUMENT.md` §9](../DESIGN_DOCUMENT.md) — Quality-Gate-Definition

Dieses Dokument bündelt den gemäß Design-Doc §9 verpflichtenden **Code-Quality-Review (CQR)** und **Security-Audit (SA)** für M1. Findings sind nach Severity klassifiziert und entweder im selben Milestone gefixt **oder** als getracktes Folge-Issue dokumentiert. Erst nach Triage darf der M1-Checkpoint im Design-Doc auf `[x]` gesetzt werden.

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

`pytest --cov=app` (Repo-State) liefert **156 passed**, Total-Coverage **85.04 %** (Threshold: 70 % global, 85 % für Auth/Sync/Krypto).

Aufschlüsselung der kritischen Pfade:

| Modul                              | Coverage  | Schwellwert | Status                 |
| ---------------------------------- | --------- | ----------- | ---------------------- |
| `app/core/crypto.py`               | **96 %**  | 85 %        | ✅                     |
| `app/api/v1/endpoints/auth.py`     | **100 %** | 85 %        | ✅                     |
| `app/services/symptom_service.py`  | **99 %**  | 85 %        | ✅                     |
| `app/services/tag_service.py`      | **100 %** | 85 %        | ✅                     |
| `app/services/entry_service.py`    | **97 %**  | 85 %        | ✅                     |
| `app/api/v1/endpoints/entries.py`  | **96 %**  | 70 %        | ✅                     |
| `app/api/v1/endpoints/tags.py`     | **98 %**  | 70 %        | ✅                     |
| `app/api/v1/endpoints/symptoms.py` | **92 %**  | 70 %        | ✅                     |
| `app/services/auth_service.py`     | **47 %**  | **85 %**    | ❌ → Finding **CQR-1** |
| `app/api/v1/deps/auth.py`          | **38 %**  | **85 %**    | ❌ → Finding **CQR-2** |
| `app/core/security.py`             | **58 %**  | 70 %        | ❌ → Finding **CQR-3** |
| `app/services/email_service.py`    | **39 %**  | 70 %        | ❌ → Finding **CQR-4** |
| `app/services/health_service.py`   | **59 %**  | 70 %        | ❌ → Finding **CQR-5** |

**Gesamt-Threshold (70 % global): erreicht.** Auth-spezifischer 85 %-Threshold **nicht erreicht** — primärer CQR-Blocker.

### 2.3 Library-Hygiene

| Bereich  | Befund                                                                                                                                                                                                                                          |
| -------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Backend  | Neue Dependency in M1: `cryptography` (für Fernet, ADR-0005). Dokumentiert in `pyproject.toml` und ADR-0005. Keine ungenutzten Dependencies in `pyproject.toml`.                                                                                |
| Frontend | `svelte@^5.0.0` läuft mit `@sveltejs/vite-plugin-svelte@3` — Plugin warnt: "Active Svelte 5 support has moved to vite-plugin-svelte@4". Lint-Output wird verrauscht, kein Funktionsfehler. → Finding **CQR-6** (minor, Library-Aktualisierung). |

### 2.4 Reuse / DRY / Konsistenz

- **Custom-Symptome** (#57) wurden 1:1 nach dem Tag-System (#8) modelliert (gleiches RLS-Pattern, gleiche Slug-Validation, analoge Service-API, parallele Endpoint-Struktur). Konsistent. ✅
- **EncryptedString-TypeDecorator** (#26) konsolidiert die Crypto-Round-Trip-Logik für `entries.note_enc` und ist explizit nicht für `symptoms.name_enc` verwendet, weil Default-Reads ohne DEK funktionieren müssen — die Asymmetrie ist in ADR-0005 begründet.
- **Auth-Cookie-Helper** (`_set_auth_cookies`/`_clear_auth_cookies` in `endpoints/auth.py`) sind privat im Endpoint-Modul. Reuse-Bedarf entsteht erst, wenn ein zweiter Auth-Pfad (OIDC, M12) hinzukommt — bewusst kein Premature-Refactor.
- **Test-Factories**: `make_symptom`/`make_tag`/`make_user` sind in `tests/conftest.py` als Fixtures vorhanden; #26 hat `_bind_test_dek` autouse ergänzt, sodass alle 156 bestehenden Tests ohne Anpassung weiterlaufen.

### 2.5 CHANGELOG

`CHANGELOG.md` enthält für M1 dedizierte Einträge unter `[Unreleased] — M1 Vorbereitung` mit Sektionen `Added` / `Changed` / `Documentation`. Keep-a-Changelog-Format. ✅

### 2.6 CQR-Findings

| ID    | Severity  | Beschreibung                                                                                                                                 | Maßnahme                                                                                                              |
| ----- | --------- | -------------------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------- |
| CQR-1 | **major** | `auth_service.py` Coverage 47 % statt geforderter 85 %. Ungetestet: `register_user`-Edge-Cases, Verifikations-Flow, Token-Rotation in Redis. | Folge-Issue [#64](https://github.com/Sturmi77/moodsync/issues/64) (CQR-1/2/3 zusammen). **Blocker für M1-Exit-Done.** |
| CQR-2 | **major** | `deps/auth.py` Coverage 38 %. Token-Validation, DEK-Bind, 401-Pfade ungetestet.                                                              | Folge-Issue [#64](https://github.com/Sturmi77/moodsync/issues/64). **Blocker für M1-Exit-Done.**                      |
| CQR-3 | minor     | `core/security.py` 58 %. Password-Hashing/-Verify und Token-Helper laufen indirekt, aber keine direkten Edge-Case-Tests.                     | Folge-Issue [#64](https://github.com/Sturmi77/moodsync/issues/64).                                                    |
| CQR-4 | minor     | `email_service.py` 39 %. SMTP-Pfad ist im Test gemockt, Fehlerpfade ungetestet.                                                              | Folge-Issue [#70](https://github.com/Sturmi77/moodsync/issues/70). Nicht-Blocker.                                     |
| CQR-5 | minor     | `health_service.py` 59 %. Postgres/Redis-Probe-Fehlerpfade nicht abgedeckt.                                                                  | Folge-Issue [#70](https://github.com/Sturmi77/moodsync/issues/70).                                                    |
| CQR-6 | minor     | Frontend `vite-plugin-svelte@3` mit Svelte 5 — Plugin selbst empfiehlt v4.                                                                   | Folge-Issue [#71](https://github.com/Sturmi77/moodsync/issues/71). Nicht-blockierend.                                 |

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

| Endpoint                         | Limit        | Quelle                  |
| -------------------------------- | ------------ | ----------------------- |
| `POST /auth/login`               | 5 / min / IP | `endpoints/auth.py:197` |
| `POST /auth/resend-verification` | 3 / min / IP | `endpoints/auth.py:165` |
| `POST /entries`                  | 60 / min     | siehe `docs/API.md`     |
| `GET /entries`                   | 120 / min    | siehe `docs/API.md`     |
| `PATCH /entries`                 | 60 / min     | siehe `docs/API.md`     |

`POST /auth/register` ist **ungerate-limitiert** — kombinierbar mit dem Enumeration-Leak (siehe SA-1) ein Mass-Enumeration-Vektor. → Finding **SA-2**.

### 3.4 Healthchecks

`/health/ready` prüft Postgres + Redis. **Nicht** geprüft: Master-Encryption-Key gesetzt + Fernet-Format korrekt. Fehlt der Key, schlägt `validate_production_secrets()` beim Startup fehl, die App startet nicht — funktional ist Crypto damit indirekt abgesichert. Trotzdem: ein Master-Key, der unter Rotation abhandenkommt, würde nur bei der nächsten Request einen 500/401 produzieren statt das Ready-Signal zu kippen. → Finding **SA-5** (minor).

### 3.5 Logging-Hygiene

`tests/test_log_scrubbing.py` deckt:

- `mood_score`, `energy_level`, `stress_level`, `note_enc`, `symptom_intensity`, `hashed_password`, `password_plain`
- Repr-Stripping auf `Entry`, `EntrySymptom`, `Symptom` (eingeführt mit #26)
- Pattern-Sniff auf f-Strings in `logger.X(...)`

Nicht abgedeckt: `name_enc` (Custom-Symptom-Name, neu mit #26), `tag.name`, `tag.slug`, `symptom.slug`. → Finding **SA-3**.

### 3.6 DSGVO-Pfad / Erasure

- ✅ Cryptographic Erasure ist auf DB-Ebene implementiert: `user_encryption_keys.user_id ON DELETE CASCADE` macht alle `entries.note_enc` und `symptoms.name_enc` (Custom) eines Users in einer Bewegung unentschlüsselbar. ADR-0005 dokumentiert das. Migration 007 setzt RLS so, dass User die Row weder selbst inserten noch löschen können.
- ❌ **Es existiert kein API-Endpoint für Account-Löschung.** Weder `DELETE /user/me` (laut Design-Doc §9) noch `DELETE /user/account` (laut ADR-0005 §"Account-Löschung") sind im Backend implementiert. Manuelle DB-DELETEs greifen zwar (Cascade ist da), aber für eine DSGVO-Art.-17-Antrag-Pipeline fehlt der API-Pfad. → Finding **SA-4** **(blocker für M1-Exit-Done)** — **✅ behoben in [#66](https://github.com/Sturmi77/moodsync/issues/66)**: `DELETE /api/v1/user/me` mit Re-Auth via Passwort, Refresh-Token-Revoke und Cascade-Delete über alle abhängigen Tabellen inkl. `user_encryption_keys`.

### 3.7 Anti-Enumeration

| Endpoint                         | Verhalten                                                                                                        | Status                |
| -------------------------------- | ---------------------------------------------------------------------------------------------------------------- | --------------------- |
| `POST /auth/login`               | Generisches `Invalid email or password`, deckt unbekannte Mail + falsches Passwort + unverifizierten Account ab. | ✅                    |
| `POST /auth/resend-verification` | Immer `202 Accepted`, identische Antwort egal ob Mail existiert.                                                 | ✅                    |
| `POST /auth/verify-email`        | Generisches `Invalid or expired verification token`.                                                             | ✅                    |
| `POST /auth/register`            | `409 Conflict` mit `"Email already registered"` — leakt Existenz einer Adresse.                                  | ❌ → Finding **SA-1** |

### 3.8 Headers / Cookies

- `access_token` Cookie: `HttpOnly; Secure; SameSite=Strict; Path=/api; Max-Age=900` ✅
- `refresh_token` Cookie: `HttpOnly; Secure; SameSite=Strict; Path=/api/v1/auth/refresh; Max-Age=2592000` — Pfad-Scope ist eng. ✅
- Refresh-Token-Logout/-Rotation löscht beide Cookies bei 401 in `/refresh`. ✅

### 3.9 Dependency-Scan

| Scan                                      | Befund                                                                                                                                                                                                                                                                                               |
| ----------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Backend `pip-audit` (sandbox-`.venv`)     | 3 Findings — alle in `pip` selbst (`pip 24.3.1`, CVE-2025-8869 / CVE-2026-1703 / CVE-2026-3219). pip ist Build-Tool, kein Runtime-Pfad der App. App-Dependencies (FastAPI, SQLAlchemy, cryptography, asyncpg, redis, slowapi, …) **ohne** Findings. CI nutzt `uv` statt pip — kein Container-Impact. |
| Frontend `pnpm audit --prod` (`apps/web`) | 1 moderate Finding: `esbuild ≤0.24.2` via `svelte-i18n` (GHSA-67mh-4wv8-2f99). Kein high/critical → kein Quality-Gate-Blocker, aber tracken. → Finding **SA-6**.                                                                                                                                     |

### 3.10 Secrets-Scan / `.env.example`

- `.env.example` enthält `ENCRYPTION_KEYS=` mit Generierungsbefehl (`python -c 'from cryptography.fernet import Fernet; ...'`) und Rotation-Hinweis.
- `SECRET_KEY` als Env-Var, nicht im Repo.
- `JWT_SECRET`/`SECRET_KEY`-Mismatch ist seit #41/PR #43 behoben.
- Repo-Stichprobensuche nach `password=`, `secret=`, `api_key=` in committed code: keine Treffer. ✅

### 3.11 SA-Findings

| ID   | Severity  | Beschreibung                                                                                                    | Maßnahme                                                                                                                     |
| ---- | --------- | --------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------- |
| SA-1 | **major** | `POST /auth/register` 409 leakt Email-Existenz (`Email already registered`).                                    | Folge-Issue [#65](https://github.com/Sturmi77/moodsync/issues/65). **Blocker für M1-Exit-Done** wegen DSGVO/Privacy-Wirkung. |
| SA-2 | minor     | `POST /auth/register` ist ungerate-limitiert — verstärkt SA-1.                                                  | Folge-Issue [#65](https://github.com/Sturmi77/moodsync/issues/65) (gemeinsam mit SA-1).                                      |
| SA-3 | minor     | Log-Scrubbing-Tests decken `name_enc`/`tag.name`/`tag.slug`/`symptom.slug` nicht ab.                            | Folge-Issue [#67](https://github.com/Sturmi77/moodsync/issues/67).                                                           |
| SA-4 | **major** | Kein API-Endpoint `DELETE /user/me` für DSGVO-Art.-17-Erasure. Cryptographic Erasure ist nur DB-seitig wirksam. | ✅ Behoben in [#66](https://github.com/Sturmi77/moodsync/issues/66): `DELETE /api/v1/user/me` mit Re-Auth + Cascade.         |
| SA-5 | minor     | `/health/ready` prüft Encryption-Key-Verfügbarkeit nicht.                                                       | Folge-Issue [#68](https://github.com/Sturmi77/moodsync/issues/68).                                                           |
| SA-6 | minor     | `esbuild` ≤ 0.24.2 (transitive via `svelte-i18n`) hat moderate Advisory.                                        | Folge-Issue [#69](https://github.com/Sturmi77/moodsync/issues/69). Nicht-Blocker.                                            |

---

## 4. Ergebnis

| Bereich                 | Status                |
| ----------------------- | --------------------- |
| Statische Analyse       | ✅ bestanden          |
| Coverage-Threshold 70 % | ✅ 85.04 %            |
| Coverage Auth/Krypto    | ⚠️ Krypto ✅, Auth ❌ |
| Library-Hygiene         | ⚠️ minor              |
| Test-Factories          | ✅                    |
| CHANGELOG-Eintrag       | ✅                    |
| Auth-Coverage / RLS     | ✅                    |
| Input-Validation        | ✅                    |
| Rate-Limiting           | ⚠️ register fehlt     |
| Healthchecks            | ⚠️ Crypto-Probe fehlt |
| Logging-Hygiene         | ⚠️ Felder-Drift       |
| DSGVO-Erasure-Pfad      | ❌ API fehlt          |
| Anti-Enumeration        | ❌ register           |
| Cookies/Headers         | ✅                    |
| Dependency-Scan         | ✅ kein high/critical |
| Secrets-Scan            | ✅                    |

**Quality-Gate-Verdikt:** **bestanden mit Auflagen**. Vier Findings sind als **major** eingestuft und müssen vor dem M1-Exit-Done geschlossen werden:

- **CQR-1/2/3** — [#64](https://github.com/Sturmi77/moodsync/issues/64) (Auth-Coverage)
- **SA-1/2** — [#65](https://github.com/Sturmi77/moodsync/issues/65) (`/auth/register` Enumeration + Rate-Limit)
- **SA-4** — [#66](https://github.com/Sturmi77/moodsync/issues/66) (`DELETE /user/me` Erasure-API)

Alle übrigen Findings sind als getrackte Folge-Issues akzeptiert ([#67](https://github.com/Sturmi77/moodsync/issues/67), [#68](https://github.com/Sturmi77/moodsync/issues/68), [#69](https://github.com/Sturmi77/moodsync/issues/69), [#70](https://github.com/Sturmi77/moodsync/issues/70), [#71](https://github.com/Sturmi77/moodsync/issues/71)). Sobald die drei major-Issue-Pakete (#64, #65, #66) geschlossen sind, darf der M1-Quality-Gate-Checkpoint im Design-Doc auf `[x]` gesetzt werden.

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

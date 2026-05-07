# Changelog

Alle signifikanten Änderungen werden hier dokumentiert.
Format basiert auf [Keep a Changelog](https://keepachangelog.com/).
Versionierung nach [Semantic Versioning](https://semver.org/).

---

## [Unreleased] — M1 Vorbereitung

### Fixed

- **CI: pnpm-Build-Script-Allowlist gegen `ERR_PNPM_IGNORED_BUILDS`.** Auf frischen Branches (kein `node_modules`-Cache-Hit in den Web-Workflows) brach `pnpm install --no-frozen-lockfile` mit Exit 1 ab, sobald für `esbuild@0.19.12`, `esbuild@0.21.5` oder `es5-ext@0.10.64` Build-Scripts liefen — pnpm 10 verlangt seit Anfang 2025 explizite Freigabe (`approve-builds`) und behandelt unbestätigte Build-Scripts in CI-Umgebungen als harten Fehler. `main` lief nur durch, weil dort der GitHub-Actions-Cache die `node_modules` mit installierten Build-Artefakten vorhielt; jeder neue Feature-/Fix-Branch traf den Bug aufs Neue (zuletzt PR #84). Fix: `onlyBuiltDependencies: [esbuild, es5-ext]` in `pnpm-workspace.yaml` (pnpm 10 liest Workspace-Settings nicht mehr aus `package.json`, sondern ausschließlich aus `pnpm-workspace.yaml`). Damit erlaubt pnpm die Build-Scripts dieser zwei Pakete deterministisch (esbuild postinstall lädt Native-Binaries, es5-ext registriert seine Polyfill-Hooks), ohne andere Build-Scripts ungewollt zu aktivieren.
- **Container-Image-Builds zum ersten Mal lauffähig.** Beide Dockerfiles waren zwar im Repo, aber kein Image war je gebaut/gepublished worden — was beim ersten Run des neuen `release-images.yml`-Workflows (PR #76 / Commit 4378fcb) sichtbar wurde.
  - **`backend/Dockerfile`**: `OSError: Readme file does not exist: README.md` beim `uv pip install -e .` — Hatchling liest `readme = "README.md"` aus `pyproject.toml`, die Datei war aber nicht im Build-Context. Fix: `COPY pyproject.toml uv.lock README.md ./` (statt nur `pyproject.toml`). Gleichzeitig `[dev]`-Extras aus dem Production-Image entfernt (`-e .` statt `-e .[dev]`) → ruff/mypy/pytest landen nicht mehr im Runtime-Image, kleinere Angriffsfläche. `uv.lock` wird mitkopiert für reproducible Builds.
  - **`apps/web/Dockerfile`**: `pnpm prune --prod` hängte mit "confirmModulesPurge"-Prompt im non-TTY-CI-Container und brach mit Exit 1 ab. Erster Fix-Versuch (`pnpm install --prod --frozen-lockfile` nach Build) hatte denselben Effekt mit `ERR_PNPM_ABORTED_REMOVE_MODULES_DIR_NO_TTY`. Zwischen-Fix: zusätzliches `ENV CI=true` ganz oben im Dockerfile (GitHub-Actions setzt `CI=true` im Runner-Env, vererbt das aber nicht in den Buildx-Container, deshalb muss es im Dockerfile selbst stehen). Damit übergeht pnpm interaktive Prompts — doch der `prepare`-Lifecycle-Hook in `apps/web/package.json` (`svelte-kit sync`) bricht beim Prod-Install dann mit `sh: svelte-kit: not found` ab, weil `@sveltejs/kit` als devDependency bei `--prod` nicht installiert wird. **Finaler Fix:** `--ignore-scripts` beim Prod-Install — `prepare` wird für das Production-Image ohnehin nicht gebraucht, der Build ist im vorigen Step bereits gelaufen.
  - Beide Fixes betreffen ausschließlich Build-Mechanik, keine Runtime-Semantik. Erste erfolgreiche GHCR-Pushes (`ghcr.io/sturmi77/moodsync-{api,web}:latest`) entstehen mit dem main-Push dieses PRs.

### Added

- **Deployment-Bundle für ersten User-Test** (Tailscale-internes Homelab-Szenario). Nach abgeschlossenem M1-Quality-Gate steht der Stack jetzt out-of-the-box für ersten Real-User-Feedback bereit, ohne dass Production-Voraussetzungen wie öffentliche Domain oder Letsencrypt erfüllt sein müssen.
  - **Neue Compose** `infra/docker/docker-compose.user-test.yml` (Stack-Name `moodsync-test`): API + Web + Postgres + Redis + Mailpit als Default; GlitchTip via `--profile monitoring`; Worker-Slot via `--profile worker` (vorbereitet für M2, Code noch nicht vorhanden). Ports binden ausschließlich an `${TAILSCALE_IP}` (Default `127.0.0.1`) statt `0.0.0.0` → kein WAN-Exposure. `migrate`-Init-Container führt `alembic upgrade head` einmalig vor `api` aus (`condition: service_completed_successfully`-Gate), idempotent. MinIO bewusst weggelassen, weil Foto-Upload erst M3+ ist.
  - **Web-Dockerfile** (`apps/web/Dockerfile`, war bisher nicht vorhanden): Multi-Stage-Build (Node 22 alpine), pnpm via Corepack, `--frozen-lockfile`, SvelteKit-Adapter-Node-Server (`build/index.js`), non-root-User `moodsync`, Build-Arg `VITE_API_BASE_URL`. Zugehöriges `apps/web/.dockerignore` und `backend/.dockerignore` neu.
  - **GHCR-Release-Workflow** (`.github/workflows/release-images.yml`): baut und published `ghcr.io/sturmi77/moodsync-api` und `ghcr.io/sturmi77/moodsync-web` bei Push auf `main` (`:latest` + `:main` + `:sha-<short>`) und bei `v*`-Tags (`:vX.Y.Z` + `:vX.Y` + `:latest`) — getrennt von den bestehenden Lint/Test-Workflows. GitHub-Actions-Cache (Buildx + GHA-Cache, scope-getrennt für api/web).
  - **`.env.user-test.example`** (`infra/docker/.env.user-test.example`, separat von der bestehenden Production-`.env.example` aus Issue #41) mit allen Variablen, Generierungs-Snippets (Fernet, `secrets.token_urlsafe`) und expliziten Hinweisen zur ENCRYPTION_KEY-Backup-Pflicht. **Neue README** `infra/docker/README.user-test.md` mit Setup-, Update-, Backup- und Troubleshooting-Anleitung.
  - Production-Compose `docker-compose.yml` (Traefik + Letsencrypt + MinIO + Worker) bleibt unverändert — beide Stacks parallel nutzbar (`moodsync` vs. `moodsync-test`).
- **Dockge-Stack-Variante** unter `infra/dockge/` (`compose.yaml` + `.env.example` + `README.md`). Drop-in für [Dockge](https://github.com/louislam/dockge) im Homelab — Stack-Verzeichnis (z. B. `/opt/stacks/moodsync/`) wird zum Stack-Namen, daher kein top-level `name:`-Key. Funktional identisch zur user-test-Compose (gleiche GHCR-Images, gleiche Services, gleiche Healthchecks, gleicher Tailscale-IP-Bind), aber ohne `--profile`-Konstrukte (Dockge UI ignoriert Profile beim Deploy → GlitchTip- und Worker-Blöcke stattdessen auskommentiert mit Aktivierungs-Anleitung). Volumes explizit benannt (`moodsync_postgres_data`, `moodsync_redis_data`) für saubere Anzeige im Dockge-UI. README dokumentiert Setup-, Update-, Backup-Workflow und die Unterschiede zur user-test-Compose.
- **Dockhand-Stack-Variante** unter `infra/dockhand/` (`compose.yaml` + `.env.example` + `README.md`). Drop-in für [Dockhand](https://dockhand.pro) — unterstützt Git-Stack-Deployment (Repo-URL + `infra/dockhand`-Pfad direkt im UI eintragen, Auto-Sync via Webhook) und manuelles Adopt-Setup. `name: moodsync` ist gesetzt (Dockhand respektiert top-level Name im UI-Header). Profiles `monitoring` und `worker` bleiben aktiv (Dockhand-UI hat ein „Profiles to enable“-Feld). Kein `pull_policy: always` — Dockhand managt Image-Pulls selbst und scannt mit Grype+Trivy vor dem Deploy, daher pinned `IMAGE_TAG` (sha- oder vX.Y.Z) empfohlen. Logging-Limits explizit per `x-logging`-Anchor (`json-file`, max-size 10m, max-file 3) damit der UI-Log-Viewer nicht Gigabyte streamt. README mit Vergleichstabelle zu user-test- und Dockge-Variante.
- **`DELETE /api/v1/user/me` — DSGVO-Art.-17-Erasure-API** (Issue #66, M1-Quality-Gate-Finding **SA-4**, ADR-0005). Schließt den letzten blockierenden M1-Exit-Pfad: User können ihren Account jetzt vollständig per API löschen, statt auf manuelle DB-Eingriffe angewiesen zu sein.
  - **Auth + Re-Auth:** Endpoint läuft hinter `get_current_user` (Verifizierung **nicht** erforderlich — das Recht auf Löschung darf nicht von einer ausstehenden E-Mail-Bestätigung abhängen). Body verlangt das aktuelle Passwort als Defense-in-Depth gegen XSRF-via-Cookie und gegen einen geleakten Access-Token.
  - **Cascade-Reichweite:** Hard-Delete der `users`-Row triggert `ON DELETE CASCADE` auf `entries`, `entry_tags`, `entry_symptoms`, Custom-`tags`, Custom-`symptoms`, `email_verification_tokens` und — entscheidend — `user_encryption_keys`. Damit werden `entries.note_enc` und Custom-`symptoms.name_enc` ab dem Commit kryptografisch unentschlüsselbar („cryptographic erasure“, ADR-0005). Default-Tags/Symptome (`user_id IS NULL`) bleiben erhalten.
  - **Refresh-Token-Revoke:** `TokenStore.revoke_all(user_id)` wird **vor** dem DB-DELETE aufgerufen — selbst bei späterem DB-Fehler ist der User damit force-logged-out auf allen Geräten. Auf der Response werden `access_token`- und `refresh_token`-Cookies invalidiert.
  - **Status-Codes:** `204 No Content` bei Erfolg, `401` für fehlende Auth **und** falsches Passwort (generische `"Invalid credentials"`-Meldung verhindert Unterscheidbarkeit), `422` für Body-Validierung.
  - **Logs:** ausschließlich `user_id`, niemals Email — abgesichert durch zwei dedizierte Tests (`test_user_service.py::test_delete_user_*_logs_user_id_not_email`).
  - **Neuer Service** `app/services/user_service.py` (`delete_user_account`, `UserDeletionError`), neuer Endpoint-Router `app/api/v1/endpoints/user.py` unter `/api/v1/user`, neues Schema `DeleteAccountRequest`. Tests: 5 Service-Unit-Tests + 7 Endpoint-Tests, alle DB-/Redis-frei via Mocks.
  - **Doku:** Neuer Abschnitt §6 „User“ in `docs/API.md`; ADR-0005, `docs/DSGVO.md`, `docs/ARCHITECTURE.md` und `docs/DESIGN_DOCUMENT.md` (DSGVO-Checkpoint M1) auf den finalen URL `/api/v1/user/me` konsolidiert (vorher inkonsistent zwischen `/user/me` und `/user/account`). M1-Quality-Gate-Report aktualisiert: SA-4 als behoben markiert.
  - **M1-Quality-Gate-Checkpoint** (DESIGN_DOCUMENT §3 „M1 — Core Entry“) ist mit diesem PR auf `[x]` gesetzt: alle drei blockierenden Major-Findings (#64 Auth-Coverage, #65 `/auth/register` Enumeration, #66 Erasure-API) sind adressiert.

### Tests

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

_Nächstes Release: M1 — Core Entry (Täglicher Eintrag, Tags, Symptome, Offline-Sync)_

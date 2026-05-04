# Changelog

Alle signifikanten Änderungen werden hier dokumentiert.
Format basiert auf [Keep a Changelog](https://keepachangelog.com/).
Versionierung nach [Semantic Versioning](https://semver.org/).

---

## [Unreleased] — M1 Vorbereitung

### Changed

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

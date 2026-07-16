# CorrelCore — API-Richtlinien & Endpunkte

> **Status: Historical / superseded (2026-07-16)**  
> Canonical sources for operators and integrators:
>
> 1. Runtime **OpenAPI** from a running API (`/openapi.json`; Swagger UI when `DEBUG=true`)
> 2. English docs-site overview: [`docs-site/docs/api/overview.md`](../docs-site/docs/api/overview.md)
>
> This German file is kept for historical design notes. Prefer OpenAPI + the
> docs-site when they disagree with the tables below.

Dieses Dokument leitet sich aus [`DESIGN_DOCUMENT.md`](DESIGN_DOCUMENT.md) ab.

---

## 1. Allgemeine Richtlinien

- **OpenAPI 3.1** — Spec wird von FastAPI aus Annotationen erzeugt. Ein TypeScript-Client-Generator ist noch nicht eingeführt; zentrale Frontend-Konstanten werden über Contract-Tests gegen Backend-Schemas abgesichert.
- **Versionierung:** `/api/v1/...` — Version im URL-Pfad
- **Auth:** Phase 1 nutzt native JWTs. Browser authentifizieren primär über HttpOnly-Cookies `access_token` und `refresh_token`; API-/Mobile-Clients können den Access-Token als `Authorization: Bearer <token>` senden. Authentik/OIDC folgt erst in Phase 2 (M12+).
- **Fehlerformat:** FastAPI-Standardfehler (`{"detail": ...}`) mit `422`-Validation-Details. RFC 7807 ist ein zukünftiges Hardening-Ziel, nicht aktueller Ist-Stand.
- **Datumsformat:** ISO 8601 (`2026-04-20T17:00:00Z`)
- **IDs:** UUID v4
- **Paginierung:** Endpoint-spezifisch; aktuelle Listen nutzen `limit` und Datumsfilter, noch keine generische Cursor-Paginierung.
- **Rate Limiting:** Endpoint-spezifisch per SlowAPI. Login/Register sind `5/min/IP`, Resend Verification `3/min/IP`, Entries je nach Methode `60/min` oder `120/min`. Deployments nutzen Redis-Storage, lokale Setups fallen auf Memory zurück.

---

## 2. Auth-Endpunkte

Phase 1 (Selfhost, M0–M10): Native JWT — siehe **ADR-0004**.
Phase 2 (SaaS, M12+): Authentik OIDC — wird zusätzlich aktiviert.

### Phase 1 — Native JWT

```
POST   /api/v1/auth/register              Registrierung (5/min/IP, immer 202; Issue #65)
POST   /api/v1/auth/login                 Login (5/min/IP, setzt HttpOnly-Cookies)
POST   /api/v1/auth/refresh               Refresh-Token rotieren
POST   /api/v1/auth/logout                Refresh-Token invalidieren, Cookies löschen
POST   /api/v1/auth/verify-email          E-Mail bestätigen (Issue #39, Token im Body)
POST   /api/v1/auth/resend-verification   Verify-Mail erneut senden (3/min/IP, immer 202)
POST   /api/v1/auth/forgot-password       Password-Reset anfordern (3/min/IP, immer 202; O-20)
POST   /api/v1/auth/reset-password        Password mit Token setzen (10/min/IP; O-20)
GET    /api/v1/auth/me                    Aktueller User
```

#### `POST /api/v1/auth/verify-email`

Bestätigt eine User-E-Mail anhand des Tokens, der bei der Registrierung
per Mail versendet wurde. Token-TTL: **24 Stunden** (ADR-0004). Token ist
**single-use** — zweiter Aufruf mit demselben Token gibt 400.

```http
POST /api/v1/auth/verify-email
Content-Type: application/json

{
  "token": "<64-zeichen-aus-mail>"
}
```

**Antworten**

- `200 OK` — `{"message": "Email verified. You can now sign in."}`
- `400 Bad Request` — generisch `Invalid or expired verification token`
  (kein Detail über Ursache, um Enumeration zu verhindern)
- `422 Unprocessable Entity` — Token zu kurz / Schema-invalid

#### `POST /api/v1/auth/resend-verification`

Fordert eine neue Verify-Mail an. Liefert immer `202 Accepted` mit
generischer Antwort, unabhängig davon, ob die E-Mail-Adresse existiert
oder bereits verifiziert ist (Schutz vor User-Enumeration).

```http
POST /api/v1/auth/resend-verification
Content-Type: application/json

{
  "email": "alice@example.com"
}
```

**Rate-Limit:** 3 Requests / Minute / IP.

#### `POST /api/v1/auth/register`

Legt einen neuen User an und versendet asynchron eine Verify-Mail. Liefert
**immer `202 Accepted`** mit derselben generischen Antwort, unabhängig
davon, ob die Adresse neu oder bereits registriert ist (Schutz vor
User-Enumeration, Issue #65 / SA-1). Der Account ist nach `register`
`unverified` und kann sich erst nach erfolgreichem `verify-email`
einloggen. Mail-Versand läuft im Hintergrund; SMTP-Fehler werden geloggt,
blocken die Antwort aber nicht (Issue #39).

```http
POST /api/v1/auth/register
Content-Type: application/json

{
  "email": "alice@example.com",
  "password": "hunter2-correct-horse",
  "display_name": "Alice"
}
```

**Body**

- `email` — gültige E-Mail-Adresse (RFC 5322), required
- `password` — 8–128 Zeichen, mindestens **ein Buchstabe und eine Ziffer**, required
- `display_name` — optional, max. 100 Zeichen

**Verhalten je nach Mail-Status (intern, niemals an den Client geleakt)**

- _Adresse neu_ — User wird angelegt, DEK provisioniert, Verify-Mail
  asynchron versandt.
- _Adresse bereits registriert_ — **kein** neuer User, **keine** Verify-Mail.
  Stattdessen wird einmalig eine "Diese Adresse ist bereits registriert"-
  Notiz an die Adresse versendet, mit Hinweis auf Login bzw.
  "Passwort vergessen".

**Antworten**

- `202 Accepted` — `{"message": "If the email is not yet registered, a verification mail has been sent."}`
  (identisch in beiden Branches)
- `422 Unprocessable Entity` — Schema-Verstoß (z.B. Passwort ohne Ziffer,
  ungültige Mail, `display_name` zu lang)
- `429 Too Many Requests` — Rate-Limit überschritten

**Rate-Limit:** 5 Requests / Minute / IP (SA-2).

**Hinweis:** Setzt **noch keine** Auth-Cookies — diese werden erst nach
erfolgreichem `verify-email` + `login` ausgegeben.

#### `POST /api/v1/auth/login`

Login mit E-Mail und Passwort. Setzt zwei HttpOnly-Cookies (Access +
Refresh) und liefert den Access-Token zusätzlich im Body, damit Native-
und Mobile-Clients ihn ohne Cookie-Jar verwenden können (ADR-0004).

```http
POST /api/v1/auth/login
Content-Type: application/json

{
  "email": "alice@example.com",
  "password": "hunter2-correct-horse"
}
```

**Cookies (gesetzt bei 200)**

- `access_token` — `HttpOnly; Secure; SameSite=Strict; Path=/api;
Max-Age=900` (15 min, aus `JWT_ACCESS_TOKEN_EXPIRE_MINUTES`)
- `refresh_token` — `HttpOnly; Secure; SameSite=Strict;
Path=/api/v1/auth/refresh; Max-Age=2592000` (30 Tage, aus
  `JWT_REFRESH_TOKEN_EXPIRE_DAYS`). Der enge Pfad-Scope sorgt dafür, dass
  das Refresh-Cookie ausschließlich am Refresh-Endpunkt mitgesendet wird.

**Antworten**

- `200 OK` — `TokenResponse`
  ```json
  {
    "access_token": "<jwt>",
    "token_type": "bearer",
    "expires_in": 900,
    "user": {
      "id": "<uuid>",
      "email": "alice@example.com",
      "display_name": "Alice",
      "is_verified": true
    }
  }
  ```
- `401 Unauthorized` — generisch `Invalid email or password`; deckt
  unbekannte Mail und falsches Passwort ab (Schutz vor User-Enumeration)
- `403 Forbidden` — `Email not verified`; der Client darf daraus die
  Resend-Verifikation-UI anbieten
- `422 Unprocessable Entity` — Schema-Verstoß
- `429 Too Many Requests` — Rate-Limit überschritten

**Rate-Limit:** 5 Requests / Minute / IP (SlowAPI).

#### `POST /api/v1/auth/refresh`

Rotiert das Refresh-Token (Single-Use) und gibt ein frisches Access-Token
aus. Primärer Eingabepfad ist das HttpOnly-`refresh_token`-Cookie; als
Fallback für Native-Clients ohne Cookie-Jar wird das Token alternativ im
JSON-Body akzeptiert.

```http
POST /api/v1/auth/refresh
Cookie: refresh_token=<jwt>
```

_oder, ohne Cookie:_

```http
POST /api/v1/auth/refresh
Content-Type: application/json

{
  "refresh_token": "<jwt>"
}
```

**Verhalten**

- Bei Erfolg: Altes Refresh-Token wird in Redis als verwendet markiert
  (Single-Use), neues Access- und Refresh-Cookie werden gesetzt.
- Bei Fehler: Auth-Cookies werden defensiv gelöscht, damit ein
  kompromittiertes Refresh-Token keinen weiteren Zugriff erlaubt.

**Antworten**

- `200 OK` — `TokenResponse` (identisch zu `/login`), neue Cookies werden gesetzt
- `401 Unauthorized` — Token fehlt, abgelaufen, bereits verwendet oder
  ungültig; konkrete Ursache wird im `detail` zurückgegeben (kein
  Enumerations-Risiko, da das Cookie/Token nur für eingeloggte Clients
  existiert)

#### `POST /api/v1/auth/logout`

Invalidiert das aktuelle Refresh-Token in Redis und löscht beide Auth-
Cookies. Idempotent: Liefert auch ohne gültiges Token `200`, damit
Client-seitiges Aufräumen immer funktioniert.

```http
POST /api/v1/auth/logout
Cookie: refresh_token=<jwt>
```

_Body-Fallback (analog `/refresh`):_

```http
POST /api/v1/auth/logout
Content-Type: application/json

{
  "refresh_token": "<jwt>"
}
```

**Antworten**

- `200 OK` — `{"message": "Logged out successfully"}`; `Set-Cookie`-Header
  löscht `access_token` und `refresh_token`

#### `GET /api/v1/auth/me`

Liefert das Profil des aktuell eingeloggten Users. Auth erfolgt über das
`access_token`-Cookie (oder `Authorization: Bearer <token>` für API-
Clients). Endpunkt ist Teil der Auth-Boundary: Lädt zusätzlich den per-User
DEK in den Request-Context (siehe ADR-0005).

```http
GET /api/v1/auth/me
Cookie: access_token=<jwt>
```

**Antworten**

- `200 OK` — `UserResponse`
  ```json
  {
    "id": "<uuid>",
    "email": "alice@example.com",
    "display_name": "Alice",
    "is_verified": true
  }
  ```
- `401 Unauthorized` — kein Token, ungültiger/abgelaufener Token, oder
  DEK des Users konnte nicht entschlüsselt werden (Master-Key-Mismatch,
  siehe ADR-0005 / Issue #26)

### Phase 2 — OIDC (geplant, M12+)

```
POST   /api/v1/auth/callback     OIDC Callback (Code → Session)
```

---

## 3. Entries

Daily mood/energy/stress log (M1+). Tags and symptoms are assigned via
separate entry sub-routes (§4, §5). Sleep fields follow in M8. All
endpoints require `get_current_verified_user` and are rate-limited per IP.

```
POST   /api/v1/entries                  Create entry                         (60/min)
POST   /api/v1/entries/batch            Retrospective onboarding batch       (20/min)
GET    /api/v1/entries                  List (filtered, newest first)        (120/min)
GET    /api/v1/entries/delta            Day-over-day comparison              (120/min)
GET    /api/v1/entries/{id}             Single entry                         (120/min)
PATCH  /api/v1/entries/{id}             Update entry                         (60/min)
POST   /api/v1/entries/{id}/note-markers      Add note marker                (60/min)
DELETE /api/v1/entries/{id}/note-markers/{mid} Remove note marker            (60/min)
GET    /api/v1/entries/{id}/note-signals      List extracted note signals    (120/min)
```

**Geplant:**

```
DELETE /api/v1/entries/{id}             Delete entry (#23 — or via DELETE /user/me, siehe §6)
GET    /api/v1/entries/date/{date}      Lookup by date (backlog)
```

### Datentypen

- `slot` — Enum: `day` (Default), `morning`, `noon`, `evening` (ADR-0028).
- `source` — Enum: `direct`, `retrospective`, `import`, `wearable`. Batch
  onboarding sets `retrospective`; normal creates default to `direct`.
- `work_context` — Enum: `homeoffice`, `office`, `vacation`, `sick`, `weekend`, `travel`.
- `mood_score`, `energy`, `stress` — Integer 1..5 (DB-CHECK + Pydantic-Validierung).
- `cycle_day` — Optionaler Integer 1..35; neutraler Kontext, keine medizinische Interpretation.
- `note` — Optional, max. 4000 Zeichen. Wird in der Spalte `note_enc` (BYTEA) als Fernet-Ciphertext unter dem User-DEK gespeichert (Issue #26, ADR-0005). API-Surface bleibt Klartext: Requests senden `note: "..."`, Responses geben den entschlüsselten String zurück. Ohne gültigen Auth-Kontext (DEK fehlt) liefert das Backend 401.
- `note_visibility` — Enum: `full` (Default), `analysis_only`, `hidden` (Notes-in-Analysis; Text + CHECK, Migration 024).
- `note_summary_short` — Optional, max. 120 Zeichen Preview (ADR-N-01); serverseitig gespiegelt.

### Backdate-Fenster

Neue Einträge sind für **heute** und die letzten **7 Tage** erlaubt.
Aktualisierungen sind nur innerhalb desselben 7-Tage-Fensters möglich;
ältere Einträge sind read-only (`409 Conflict`).

### `POST /api/v1/entries`

Request:

```json
{
  "entry_date": "2026-05-04",
  "slot": "day",
  "mood_score": 4,
  "energy": 3,
  "stress": 2,
  "cycle_day": 12,
  "work_context": "homeoffice",
  "note": "Lange Sitzung, aber produktiv."
}
```

Response `201 Created`:

```json
{
  "id": "uuid",
  "user_id": "uuid",
  "entry_date": "2026-05-04",
  "slot": "day",
  "mood_score": 4,
  "energy": 3,
  "stress": 2,
  "cycle_day": 12,
  "work_context": "homeoffice",
  "note": "Lange Sitzung, aber produktiv.",
  "created_at": "2026-05-04T17:00:00Z",
  "updated_at": "2026-05-04T17:00:00Z"
}
```

Fehler:

- `401 Unauthorized` — fehlender / abgelaufener Token.
- `403 Forbidden` — nicht verifizierter Account.
- `409 Conflict` — für `(user, entry_date, slot)` existiert bereits ein Eintrag.
- `422 Unprocessable Entity` — Range-Verletzung (mood/energy/stress ∉ 1..5),
  `entry_date` in der Zukunft, oder älter als 7 Tage.

### `GET /api/v1/entries`

Query-Parameter (alle optional):

- `start_date` (ISO `YYYY-MM-DD`) — inklusiv.
- `end_date` (ISO `YYYY-MM-DD`) — inklusiv.
- `limit` (1..365, Default 100).

Response `200 OK`: Liste von Entry-Objekten, sortiert nach `entry_date` (desc),
bei Gleichstand nach `slot` (asc).

### `GET /api/v1/entries/{id}`

Response `200 OK` mit Entry-Objekt; `404 Not Found` falls die ID einem anderen User gehört
oder nicht existiert (RLS + Service-Layer-Check).

### `PATCH /api/v1/entries/{id}`

Request (alle Felder optional):

```json
{
  "mood_score": 5,
  "slot": "evening",
  "energy": 4,
  "stress": 1,
  "cycle_day": 12,
  "work_context": "office",
  "note": "Korrektur"
}
```

Fehler:

- `404 Not Found` — wie oben.
- `409 Conflict` — Eintrag ist älter als 7 Tage (read-only) oder der Ziel-Slot
  kollidiert mit einem vorhandenen `(user, entry_date, slot)`-Eintrag.

### `POST /api/v1/entries/batch`

Creates up to **7** retrospective entries for cold-start onboarding. Each
entry is validated like a normal create and marked `source: retrospective`.
The same 7-day backdate window applies.

Request:

```json
{
  "entries": [
    {
      "entry_date": "2026-05-20",
      "slot": "day",
      "mood_score": 3,
      "energy": 3,
      "stress": 2,
      "work_context": "office",
      "note": null
    }
  ]
}
```

Response `201 Created`: list of `EntryResponse` objects.

### `GET /api/v1/entries/delta`

Returns a neutral day-over-day comparison for one `(entry_date, slot)` pair:
metric-only `today`/`previous`, mood/energy/stress deltas, and shared tags.
No causal or diagnostic framing.

Query parameters:

- `entry_date` (required, ISO `YYYY-MM-DD`)
- `slot` (optional, default `day`)

Response `200 OK`:

```json
{
  "today": {
    "entry_date": "2026-05-04",
    "slot": "day",
    "mood_score": 4,
    "energy": 3,
    "stress": 2
  },
  "previous": {
    "entry_date": "2026-05-03",
    "slot": "day",
    "mood_score": 3,
    "energy": 2,
    "stress": 3
  },
  "delta": { "mood": 1, "energy": 1, "stress": -1 },
  "shared_tags": []
}
```

When no prior-day entry exists, `previous` is `null` and delta fields are
`null`.

### Tag-Zuweisung

Der Tag-Set eines Eintrags wird über einen separaten, idempotenten
`PUT`-Endpunkt verwaltet — siehe §4. `entries`-Antworten enthalten
**keine** Tag-Liste; Clients laden Tags pro Entry on-demand über
`GET /entries/{id}/tags`. Damit bleibt das Entry-Schema stabil und
batch-fähig (`GET /entries`).

### Zukünftige Felder

```jsonc
// Sobald Issue #9 / M8 landen, erweitert sich die Antwort um:
// "symptoms": [{ "symptom_id": "uuid", "intensity": 1 }],
// "sleep_minutes": 450,
// "sleep_quality": 3
```

---

## 4. Tags

M1-Implementierungsstand (Issue #8). Tags sind in zwei Klassen geteilt:

- **Default-Tags** — kuratierte Liste (30 Tags, gepflegt im Migration-Seed `004_create_tags.py`). `user_id IS NULL`, `is_default = true`. Read-only für alle User; lesbar auch ohne Auth über `/tags/default`.
- **Custom-Tags** — pro User mit `user_id = <user>`. Vollständige CRUD-Hoheit, Slugs müssen sich nicht mit Defaults überschneiden.

Kategorien (`TagCategory`): `sport`, `social`, `work`, `leisure`, `consumption`, `health`, `other`.

M2-Stretch (#124) erweitert den Vertrag um persoenliche Default-Overrides:
`PATCH /api/v1/tags/{id}` mutiert globale Default-Tags nicht direkt, sondern
legt fuer den User eine Copy-on-Write-Zeile mit gleichem `slug` an. Diese
Override-Zeile ueberschattet den Default. `is_hidden=true` blendet Tags aus
normalen Listen und aus dem Entry-Picker aus; Settings koennen sie mit
`include_hidden=true` trotzdem laden und zuruecksetzen.

```
GET    /api/v1/tags/default                Kuratierte Standard-Tags        (no auth)
GET    /api/v1/tags                        Defaults + eigene Custom-Tags   (120/min)
GET    /api/v1/tags?include_hidden=true    Inkl. Hidden-Tags/Overrides     (120/min)
POST   /api/v1/tags                        Neuen Custom-Tag erstellen      (60/min)
PATCH  /api/v1/tags/{id}                   Tag aktualisieren/Override      (60/min)
DELETE /api/v1/tags/{id}                   Custom-Tag löschen              (60/min)
GET    /api/v1/entries/{entry_id}/tags     Tags eines Eintrags             (120/min)
PUT    /api/v1/entries/{entry_id}/tags     Tag-Set ersetzen (replace)      (60/min)
```

### Datentypen

- `slug` — kanonischer Schlüssel, 2..64 Zeichen, lowercased Buchstaben/Ziffern/Dashes/Underscores; nicht patchbar (würde Historie brechen).
- `name` — Display-Name, 1..64 Zeichen.
- `category` — Enum (siehe oben).
- `icon` — optional, max. 32 Zeichen (Emoji oder kurzer Slug für Icon-Lookup).
- `color` — optional, 7-Zeichen-Hex (`#rrggbb`); fällt auf Kategorie-Default zurück.
- `is_default` — boolean, server-managed; Defaults werden per Copy-on-Write ueberschattet.
- `is_hidden` — boolean; normale Listen und Entry-Picker filtern versteckte Tags aus.
- `habit_type` — Enum: `none` (default), `build`, `reduce` (M5, ADR-0012).
- `target_frequency` — Integer 1..7; required when `habit_type` is `build` or
  `reduce`, must be `null` when `habit_type` is `none`.

### `POST /api/v1/tags`

Erstellt einen Custom-Tag. Slug-Kollisionen (mit Default oder eigenem) liefern `409 Conflict`.

Request:

```json
{
  "slug": "yoga",
  "name": "Yoga",
  "category": "sport",
  "icon": "🧘",
  "color": "#a1b2c3"
}
```

Response `201 Created`: `TagResponse` (siehe unten).

Fehler:

- `401 Unauthorized` / `403 Forbidden` — fehlender Token / nicht verifiziert.
- `409 Conflict` — Slug existiert bereits als Default oder als Custom-Tag des Users.
- `422 Unprocessable Entity` — Slug-Format invalid, Hex-Farbe falsch, Felder zu lang.

### `PATCH /api/v1/tags/{id}`

Custom-Tags des aufrufenden Users werden direkt editiert. Wird ein Default-Tag gepatcht, erzeugt oder aktualisiert das Backend stattdessen einen persoenlichen Override (`user_id = current_user`, gleicher `slug`, `is_default=false`) und gibt diesen Override zurueck. Slug ist bewusst **nicht** patchbar (wuerde Verweise in `entry_tags` brechen).

Request (alle Felder optional):

```json
{
  "name": "Yoga (zuhause)",
  "category": "sport",
  "icon": "🧘",
  "color": "#a1b2c3"
}
```

### `DELETE /api/v1/tags/{id}`

Loescht einen Custom-Tag oder einen persoenlichen Default-Override. Bei Overrides bedeutet das "zuruecksetzen auf Standard": der globale Default wird wieder sichtbar. Default-Tags selbst lassen sich nicht loeschen.

Response: `204 No Content`.

### `GET /api/v1/entries/{entry_id}/tags`

Liefert die aktuell verknüpften Tags eines Eintrags (Liste, leer wenn keine zugewiesen). `404 Not Found`, falls der Entry einem anderen User gehört oder nicht existiert.

### `PUT /api/v1/entries/{entry_id}/tags`

**Replace-Set-Semantik:** Der übergebene `tag_ids`-Array ersetzt das gesamte Tag-Set des Eintrags. Eine leere Liste entfernt alle Tags. Maximale Listenlänge: **50** (`MAX_TAGS_PER_ENTRY`).

Request:

```json
{
  "tag_ids": ["uuid-sport", "uuid-musik"]
}
```

Response `200 OK`: Liste der `TagResponse`-Objekte nach dem Replace.

Fehler:

- `404 Not Found` — Entry gehört nicht dem User.
- `422 Unprocessable Entity` — Liste enthält Duplikate, ist länger als 50, oder mindestens eine `tag_id` ist nicht sichtbar.

### `TagResponse`

```json
{
  "id": "uuid",
  "user_id": null,
  "slug": "sport",
  "name": "Sport",
  "category": "sport",
  "icon": "🏃",
  "color": "#22c55e",
  "is_default": true,
  "is_hidden": false,
  "habit_type": "build",
  "target_frequency": 4,
  "created_at": "2026-05-04T17:00:00Z",
  "updated_at": "2026-05-04T17:00:00Z"
}
```

---

## 5. Symptome

Gesundheits-Symptome werden parallel zu Tags pro Entry erfasst (Issue #9 + Issue #57, ADR-0008). Seit Issue #57 sind Symptome — analog zum Tag-System — in zwei Klassen geteilt:

- **Default-Symptome** — kuratierte Liste (5 Symptome aus Migration-Seed `006_add_symptom_master_table.py`). `user_id IS NULL`, `is_default = true`. Read-only für alle User; lesbar auch ohne Auth über `/symptoms/default`.
- **Custom-Symptome** — pro User mit `user_id = <user>`. Vollständige CRUD-Hoheit, Slugs müssen sich nicht mit Defaults überschneiden. Hard Cap: **50 pro User** (`MAX_SYMPTOMS_PER_USER`).

Die Intensität bewegt sich in einem 0–3-Bereich, der im UI als 4-Punkt-Skala gerendert wird. Symptome sind Gesundheitsdaten nach DSGVO Art. 9 — Server-Logs enthalten weder `slug`/`name`/`symptom_id` noch `intensity` (statisch via `test_log_scrubbing` und `test_symptom_service_logs_no_sensitive_fields` geprüft). Custom-Symptom-Namen werden in `symptoms.name_enc` als Fernet-Ciphertext unter dem User-DEK gespeichert (Issue #26, ADR-0005); Default-Symptom-Namen bleiben plaintext, weil sie kuratierte, nicht-personenbezogene Labels sind und ohne aktiven User-Kontext gelesen werden müssen (`GET /symptoms/default`). Custom-Symptom-`slug`-Werte sind **HMAC-stabilisiert** (ADR-0039, Migration 027, Env `SLUG_HMAC_KEY`); Default-Slugs bleiben kuratierte Klartext-Keys.

```
GET    /api/v1/symptoms/default                 Kuratierte Standard-Symptome   (no auth)
GET    /api/v1/symptoms                         Defaults + eigene Custom        (60/min)
POST   /api/v1/symptoms                         Neues Custom-Symptom anlegen   (60/min)
PATCH  /api/v1/symptoms/{id}                    Custom-Symptom aktualisieren    (60/min)
DELETE /api/v1/symptoms/{id}                    Custom-Symptom löschen          (60/min)
GET    /api/v1/entries/{entry_id}/symptoms      Aktuelle Symptome eines Entries (120/min)
PUT    /api/v1/entries/{entry_id}/symptoms      Replace-Set: gesamte Symptom-Liste (60/min)
```

### Datentypen

- `id` — UUID des Symptoms (Default-Rows nutzen weiterhin den deterministischen Legacy-Namespace `uuid5(..., "moodsync.symptom.<slug>")`, damit der CorrelCore-Rename bestehende IDs nicht verändert; siehe ADR-0008).
- `slug` — kanonischer Schlüssel, 2..64 Zeichen, lowercased Buchstaben/Ziffern/Underscores; **nicht patchbar** (bräche Verweise in `entry_symptoms`).
- `name` — Display-Name, 1..80 Zeichen.
- `icon` — optional, max. 8 Zeichen (Emoji oder kurzer Slug für Icon-Lookup).
- `is_default` — boolean, server-managed; Defaults sind nicht mutierbar.
- `intensity` — Integer 0..3 (0 = nicht vorhanden, 1 = leicht, 2 = mittel, 3 = stark). DB-CHECK + Pydantic-Field-Constraint mirroren den Range. UI rendert 4 Dots, kein freier Zahlen-Input.

### `GET /api/v1/symptoms/default`

Liefert die kuratierte Liste der M1-Standard-Symptome (5 Einträge: `headache`, `digestion`, `back_pain`, `fatigue`, `cold`). Nicht personenbezogen, daher kein Auth erforderlich — das Picker-UI kann vor Login-Abschluss rendern. Rate-Limit: 120/min/IP.

Response `200 OK`: Liste von `SymptomResponse`-Objekten mit `is_default: true` und `user_id: null`, sortiert alphabetisch nach Slug.

### `GET /api/v1/symptoms`

Liefert Defaults + alle Custom-Symptome des aufrufenden Users in einer Antwort. Reihenfolge: Defaults zuerst (alphabetisch nach Slug), dann eigene Custom-Symptome (alphabetisch nach `name`). Rate-Limit: 60/min.

### `POST /api/v1/symptoms`

Erstellt ein Custom-Symptom. Slug-Kollisionen (mit Default oder eigenem) liefern `409 Conflict`. Beim Erreichen des User-Caps liefert der Service `409 Conflict` mit der Begründung `cap_reached`.

Request:

```json
{
  "slug": "migraene_aura",
  "name": "Migräne mit Aura",
  "icon": "🧠"
}
```

Response `201 Created`: `SymptomResponse` (siehe unten).

Fehler:

- `401 Unauthorized` / `403 Forbidden` — fehlender Token / nicht verifiziert.
- `409 Conflict` — Slug existiert bereits als Default oder als Custom des Users; oder User-Cap (50) erreicht.
- `422 Unprocessable Entity` — Slug-Format invalid, Name leer/zu lang, Icon zu lang.

### `PATCH /api/v1/symptoms/{id}`

Nur Custom-Symptome des aufrufenden Users sind editierbar. Versuch, ein Default-Symptom zu ändern, liefert `403 Forbidden`. Slug ist bewusst **nicht** patchbar (würde Verweise in `entry_symptoms` brechen).

Request (alle Felder optional):

```json
{
  "name": "Migräne mit Aura (chronisch)",
  "icon": "🧠"
}
```

### `DELETE /api/v1/symptoms/{id}`

Löscht ein Custom-Symptom und kaskadiert alle `entry_symptoms`-Verknüpfungen (FK `ON DELETE CASCADE`). Default-Symptome lassen sich nicht löschen (`403 Forbidden`).

Response: `204 No Content`.

### `GET /api/v1/entries/{entry_id}/symptoms`

Liefert die aktuell auf einem Entry geloggten Symptome (Liste, leer wenn keine zugewiesen). Owner-scoped via Service-Layer; `404 Not Found`, falls der Entry einem anderen User gehört oder nicht existiert. Rate-Limit: 120/min.

Response `200 OK`: Liste von `EntrySymptomResponse`-Objekten (siehe unten).

### `PUT /api/v1/entries/{entry_id}/symptoms`

**Replace-Set-Semantik:** Die übergebene `symptoms`-Liste ersetzt das gesamte Symptom-Set des Entries. Eine leere Liste entfernt alle Symptome. Maximale Listenlänge: **32** (`MAX_SYMPTOMS_PER_ENTRY`). Rate-Limit: 60/min.

Der Service-Layer prüft, dass jede `symptom_id` für den User sichtbar ist (Default oder eigenes Custom) — unbekannte/fremde IDs liefern `422 Unprocessable Entity`. Anschließend wird ein Diff (add / update intensity / remove) berechnet, sodass die Tabelle bei Updates nicht mit veralteten Zeilen wächst.

Request:

```json
{
  "symptoms": [
    { "symptom_id": "5e4f5b7e-...-headache", "intensity": 2 },
    { "symptom_id": "a92b1c3d-...-custom", "intensity": 1 }
  ]
}
```

Response `200 OK`: Liste der `EntrySymptomResponse`-Objekte nach dem Replace, sortiert nach `symptom_id`.

Fehler:

- `404 Not Found` — Entry gehört nicht dem User oder existiert nicht.
- `422 Unprocessable Entity` — unbekannte/nicht sichtbare `symptom_id`, `intensity` außerhalb 0..3, doppelte IDs im Request oder Liste länger als 32.

### `SymptomResponse`

```json
{
  "id": "uuid",
  "user_id": null,
  "slug": "headache",
  "name": "Kopfschmerzen",
  "icon": "🤕",
  "is_default": true,
  "created_at": "2026-05-04T17:00:00Z",
  "updated_at": "2026-05-04T17:00:00Z"
}
```

### `EntrySymptomResponse`

```json
{
  "id": "uuid",
  "entry_id": "uuid",
  "user_id": "uuid",
  "symptom_id": "uuid",
  "intensity": 2,
  "created_at": "2026-05-04T17:00:00Z",
  "updated_at": "2026-05-04T17:00:00Z"
}
```

---

## 6. User

Self-Service-Endpoints für den eigenen Account. Alle Pfade liegen unter
`/api/v1/user/me` und sind ausschließlich auf den authentifizierten
Aufrufer bezogen — die Adressierung anderer User ist konzeptionell
nicht möglich.

```
GET    /api/v1/user/preferences      Eigene Insight-/Onboarding-Präferenzen laden
PATCH  /api/v1/user/preferences      Eigene Präferenzen aktualisieren
PUT    /api/v1/user/profile          Optionales Onboarding-Profil upserten
GET    /api/v1/user/me/consents      Consent-Historie + aktueller Status (Art. 9 / HC)
POST   /api/v1/user/me/consents      Consent grant/revoke protokollieren
POST   /api/v1/user/me/consents/revoke  Consent widerrufen (convenience)
GET    /api/v1/user/export           DSGVO Art. 20 ZIP mit export.json + README.txt
DELETE /api/v1/user/me               Account und alle abhängigen Daten löschen (DSGVO Art. 17)
```

### Consents (Health Connect / Art. 9)

`consent_log` speichert explizite Einwilligungen (Migration 025, Issue #31).
Settings → Privacy steuert den Health-Connect-Import-Gate (`canUseHealthConnectImport()`).
Schlaf-/Wearable-Import selbst folgt in M8; die Consent-API ist die Foundation.

### `GET/PATCH /api/v1/user/preferences`

Speichert nicht-sensitive UI-/Insight-Präferenzen des aktuellen Users:
`analytics_enabled`, Onboarding-Completion-Flags,
`dismissed_insight_keys`, `reached_milestone_keys` und
`last_seen_insight_at`. Der Analytics-Worker berücksichtigt
`analytics_enabled=false` beim Job-Listing.

### `PUT /api/v1/user/profile`

Upsert für optionale Onboarding-Antworten:
`sleep_hours_typical`, `work_context_typical`, `sport_frequency` und
`insight_curiosity`.

## 6a. Onboarding

```
GET  /api/v1/onboarding/tag-suggestions   Gruppierte Tag-Vorschläge
POST /api/v1/onboarding/complete          Onboarding abschließen
```

`GET /api/v1/onboarding/tag-suggestions` liefert statische Vorschlagsgruppen
für `work`, `health`, `social` und `cycle`.

`POST /api/v1/onboarding/complete` akzeptiert ausgewählte Vorschläge und freie
Tags:

```json
{
  "tags": [{ "slug": "deep-work", "name": "Deep work", "category": "work" }]
}
```

Der Service erstellt fehlende User-Custom-Tags idempotent nach Slug oder
verwendet sichtbare bestehende Tags wieder. Danach werden die bestehenden
Preferences `onboarding_retro_completed` und `onboarding_profile_completed`
auf `true` gesetzt.

### `GET /api/v1/user/export`

Kanonischer DSGVO-Art.-20-ZIP-Export mit `export.json` und `README.txt`.
Fotos/Attachments sind bis M13 nicht enthalten; die
Export-Struktur hält dafür leere, versionierte Sektionen vor.

### `DELETE /api/v1/user/me`

DSGVO-Art.-17-Erasure-API (Issue #66, ADR-0005). Hard-löscht den
authentifizierten User samt aller abhängigen Daten. Die Cryptographic
Erasure (`user_encryption_keys`-Cascade) sorgt dafür, dass
`entries.note_enc` und Custom-`symptoms.name_enc` ab dem Moment des
Commits mathematisch nicht mehr entschlüsselbar sind — selbst aus alten
Backups (siehe ADR-0005 §"Account-Löschung").

**Auth:** required (Access-Cookie oder `Authorization: Bearer ...`).
Im Gegensatz zu den meisten anderen Endpoints **nicht** auf `is_verified`
gegated — das Recht auf Löschung darf nicht von einer noch ausstehenden
E-Mail-Verifizierung abhängen.

**Body:**

```json
{ "password": "<aktuelles Passwort, 8–128 Zeichen>" }
```

Die Passwort-Bestätigung ist Re-Authentication als Defense-in-Depth gegen
XSRF-via-Cookie und gegen einen geleakten Access-Token. (Der Access-
Cookie nutzt zwar `SameSite=strict`, aber für eine destruktive Aktion
ist die zusätzliche Bestätigung verpflichtend.)

**Response:**

- `204 No Content` — Account und alle abhängigen Daten gelöscht; Refresh-
  Tokens des Users in Redis revoked; `access_token`- und `refresh_token`-
  Cookies auf dem Response invalidiert.
- `401 Unauthorized` — fehlender/ungültiger Access-Token **oder** falsches
  Passwort. Fehlermeldung ist generisch (`{"detail": "Invalid credentials"}`),
  damit Beobachter nicht zwischen „Token stale“ und „Passwort falsch“
  unterscheiden können.
- `422 Unprocessable Entity` — Body-Validierung (Passwort fehlt oder zu
  kurz/lang).

**Cascade-Reichweite** (durch DB-`ON DELETE CASCADE` auf jeder FK gegen
`users.id` garantiert, im Service-Modul `user_service.py` dokumentiert):

- `entries`, `entry_tags`, `entry_symptoms`
- `tags` (Custom; Defaults haben `user_id IS NULL` und bleiben)
- `symptoms` (Custom; Defaults haben `user_id IS NULL` und bleiben)
- `email_verification_tokens`
- `user_encryption_keys` — **Cryptographic Erasure**

**Beispiel:**

```bash
curl -X DELETE https://api.correlcore.example/api/v1/user/me \
  -H "Cookie: access_token=..." \
  -H "Content-Type: application/json" \
  -d '{"password":"mein-aktuelles-passwort"}'
# → 204 No Content
```

---

## 7. Insights

Alle Endpunkte erfordern einen verifizierten User. Insight-Statements werden
serverseitig aus `insights.statement_enc` entschluesselt und nur fuer den
jeweiligen Owner ausgegeben.

```
GET    /api/v1/insights              Alle Insights des Users
GET    /api/v1/insights/latest       Neuester Insight je Metrik
GET    /api/v1/insights/digest/latest  Wöchentlicher Insight-Digest (Foundation #147)
GET    /api/v1/insights/tag-cooccurrence   Tag-Paar-Co-Occurrence (M5.1)
GET    /api/v1/insights/symptom-tag-cooccurrence   Symptom×Tag-Lift-Matrix (M7)
GET    /api/v1/insights/tag-clusters   Tag-Gruppen aus M7-Clustering
POST   /api/v1/insights/regenerate    Insights + Tag-Gruppen on-demand (Owner, 1×/h)
POST   /api/v1/insights/trigger      Worker manuell anstossen (Admin only)
```

`GET /api/v1/insights/digest/latest` liefert den letzten wöchentlichen Digest-Snapshot
(Worker: `python -m app.workers.digest --once`). Push-Delivery hängt noch an M4.2.
Optionale Ollama-Formulierungen (#148) und Changepoint-Insights (#149) sind in der
Analytics-Pipeline angebunden und ohne Cloud-Fallback deaktivierbar.

`GET /api/v1/insights?limit=50` liefert die neuesten gespeicherten Insights:

```json
{
  "insight_maturity": {
    "phase": "provisional",
    "phase_index": 3,
    "current_entries": 18,
    "next_phase_at": 30,
    "next_phase_label": "Robust Insights",
    "entries_until_next": 12,
    "user_message_key": "maturity.provisional.description"
  },
  "insights": [
    {
      "id": "uuid",
      "user_id": "uuid",
      "insight_type": "pointbiserial",
      "tier": "developing",
      "metric": "mood_score",
      "subject_type": "tag",
      "subject_id": "uuid",
      "subject_label": "Sport",
      "effect_size": 0.42,
      "confidence": 0.61,
      "sample_n": 18,
      "statement": "Days tagged Sport currently line up with higher mood scores in your data. Treat this as a pattern to reflect on, not a cause.",
      "flags": {
        "method": "pointbiserial",
        "medical_disclaimer_required": true,
        "causal_claim": false
      },
      "payload": {},
      "generated_for_date": "2026-05-12",
      "generated_at": "2026-05-12T03:00:00Z",
      "created_at": "2026-05-12T03:00:00Z",
      "updated_at": "2026-05-12T03:00:00Z"
    }
  ]
}
```

`GET /api/v1/insights/latest?limit=10` liefert die neuesten Insights pro
analytischem Subject (`insight_type`, `metric`, optionaler Tag/Metric/Weekday).
Beide Insight-Listen enthalten dasselbe serverseitig berechnete
`insight_maturity`-Objekt. Die Phase wird aus den unterschiedlichen
Tracking-Tagen des Users abgeleitet: `collecting` fuer 0-6 Eintraege,
`early_patterns` fuer 7-13, `provisional` fuer 14-29 und `robust` ab 30.
Frontend-Clients duerfen diese Phase nicht selbst aus der Entry-Anzahl
rekonstruieren.
M7 ergaenzt den bestehenden Envelope um `symptom_cluster`,
`symptom_mood_association` und `symptom_tag_cooccurrence` Insights.
Lasso- und Lag-Befunde werden ueber `payload.method = "lasso" | "lag"`
unterschieden; Symptom-Insights liefern `payload.kind` sowie Symptom-/Tag-Slugs.
Clients, die neue Typen nicht kennen, sollen sie wie andere unbekannte
Insight-Typen ignorieren.
Der manuelle Trigger bleibt geplant und ist in M3 noch nicht oeffentlich
implementiert.

`GET /api/v1/insights/tag-cooccurrence?range=30d|90d|1y&min_count=2` (M5.1)
liefert Tag-Paare, die auf demselben Entry gemeinsam vorkommen. Hidden Tags
bleiben ausgeschlossen. Paare sind nach `count` absteigend sortiert.

Query-Parameter:

| Parameter   | Default | Beschreibung                                     |
| ----------- | ------- | ------------------------------------------------ |
| `range`     | `90d`   | Fenster: `30d`, `90d` oder `1y` (inklusive Tage) |
| `min_count` | `2`     | Mindest-Co-Occurrence pro Paar (1–100)           |

Response `200 OK`:

```json
{
  "range": "90d",
  "start_date": "2026-02-09",
  "end_date": "2026-05-09",
  "min_count": 2,
  "pairs": [
    {
      "tag_a": {
        "tag_id": "uuid",
        "slug": "sport",
        "name": "Sport",
        "category": "sport",
        "color": "#10b981"
      },
      "tag_b": {
        "tag_id": "uuid",
        "slug": "focus",
        "name": "Focus",
        "category": "work",
        "color": "#6366f1"
      },
      "count": 8,
      "pct_of_a": 66.7,
      "pct_of_b": 80.0
    }
  ]
}
```

`pct_of_a` / `pct_of_b` sind Anteile der Entries mit Tag A bzw. B, auf denen
beide Tags gemeinsam vorkommen (0–100, eine Nachkommastelle).

---

## 7a. Dashboard

```
GET /api/v1/dashboard/summary?as_of=YYYY-MM-DD
```

Liefert eine kompakte Insight-Confidence-Zusammenfassung fuer Home und
Cold-Start-UX: `entry_count`, `insight_tier` und `confidence_score` (0..1).
Der optionale Query-Parameter `as_of` begrenzt die Berechnung auf Eintraege
bis einschliesslich dieses Datums.

Response `200 OK`:

```json
{
  "entry_count": 18,
  "insight_tier": "developing",
  "confidence_score": 0.61
}
```

---

## 8. Visualisierungs-Stats (M2)

Alle Endpunkte erfordern einen verifizierten User und liefern ausschliesslich
Daten dieses Users.

```
GET /api/v1/entries/stats/timeseries?range=week|month|year
GET /api/v1/entries/stats/tags?start_date=YYYY-MM-DD&end_date=YYYY-MM-DD&category=work
GET /api/v1/entries/stats/streak?as_of=YYYY-MM-DD
```

`timeseries` liefert fuer `week` sieben Tagespunkte, fuer `month` 30 Tagespunkte,
fuer `quarter` 90 Tagespunkte und fuer `year` 365 Tagespunkte mit `entry_count`,
`mood_avg`, `energy_avg` und `stress_avg`. Fehlende Perioden bleiben als Punkte mit `entry_count=0` und
`*_avg=null` erhalten.

`tags` liefert die Tag-Frequenz-Heatmap pro sichtbarem Tag. Hidden Tags
(`is_hidden=true`) bleiben in historischen Entry-Beziehungen erhalten, werden
aber nicht in neuen Heatmap- oder Insight-Berechnungen verwendet:

```json
{
  "start_date": "2026-01-01",
  "end_date": "2026-05-09",
  "tags": [
    {
      "tag_id": "uuid",
      "slug": "sport",
      "name": "Sport",
      "category": "sport",
      "color": "#10b981",
      "days": [{ "date": "2026-05-09", "count": 1 }]
    }
  ]
}
```

`streak` zaehlt nach ADR-0012 nur Eintrags-Streaks: aufeinanderfolgende Tage mit
mindestens einem Entry. Es gibt keine Habit-Semantik und keine Toleranz fuer
fehlende Tage.

---

## 9. Habits (M5)

Alle Endpunkte erfordern einen verifizierten User. Habits sind sichtbare Tags
mit `habit_type=build|reduce` und `target_frequency` zwischen 1 und 7.

```
GET /api/v1/habits?window=7|14|28|90
GET /api/v1/habits/{tag_id}/stats?window=7|14|28|90
```

Antwortform:

```json
{
  "habits": [
    {
      "tag_id": "uuid",
      "habit_type": "build",
      "target_frequency": 4,
      "window": 28,
      "start_date": "2026-05-01",
      "end_date": "2026-05-28",
      "days_tracked": 10,
      "days_total": 28,
      "target_days": 16,
      "adherence_rate": 62.5,
      "correlation_score": 0.42
    }
  ]
}
```

`adherence_rate` ist zielbasiert. `build` misst Fortschritt zum Wochenziel,
`reduce` misst neutral, ob die Tag-Haeufigkeit im Zielbereich bleibt.
`correlation_score` ist der neueste passende M3-Insight-Effekt fuer diesen Tag
oder `null`, wenn noch kein Insight existiert.

---

## 10. Sync (Offline-Sync, M4.1)

**Status:** Push/pull implemented in M4.1 Sprint 2; contract in [ADR-0036](adr/0036-offline-sync-v1-scope.md).
Pydantic schemas: `backend/app/schemas/sync.py`. Service: `backend/app/services/sync_service.py`.

M4 lieferte PWA-Shell-Caching und form-level Offline-Retry; M4.1 ergänzt Dexie-
Queue, Delta-Sync und `sync_conflicts`-Logging.

```
POST   /api/v1/sync/push              Client-Änderungen hochladen (verified user)
GET    /api/v1/sync/pull              Delta seit Cursor herunterladen (verified user)
GET    /api/v1/user/sync-conflicts    Read-only Konflikt-Historie (Sprint 1)
```

Alle Sync-Endpunkte erfordern `get_current_verified_user`. Logs und Conflict-
Responses enthalten **keine** Klartext-Gesundheitswerte (ADR-0036 §2.1).

### Synced entities (v1)

| Entity                           | Push | Pull                      |
| -------------------------------- | ---- | ------------------------- |
| Entries (+ tag/symptom links)    | Ja   | Ja                        |
| Custom tags                      | Ja   | Ja                        |
| Custom symptoms                  | Ja   | Ja                        |
| Insights, analytics, worker data | Nein | Ja (server-authoritative) |

Merge: **Last-Write-Wins** pro Feld (`updated_at`); Server gewinnt bei Gleichstand.
LWW-Konflikte auf kritischen Feldern (`mood_score`, `energy`, `stress`, `note`,
`symptoms`) werden in `sync_conflicts` geloggt — **nicht** als HTTP `409`.

### Cursor

Pull-Cursor ist opaque (Base64url-JSON, nicht vom Client parsen). Erster Pull ohne
`since` liefert Änderungen der letzten 30 Tage. Folge-Pulls nutzen
`GET /api/v1/sync/pull?since=<cursor>`.

Beispiel-Cursor-Inhalt (nur zur Dokumentation — Clients behandeln ihn als opaque string):

```json
{ "user_rev": 12345, "wall": "2026-06-30T12:00:00.000000Z" }
```

### `POST /api/v1/sync/push`

Lädt einen Batch aus der Client-`change_log`-Outbox hoch. Idempotent auf
`(client_id, batch_id)` — Replay liefert `200` mit `idempotent_replay: true`
ohne erneute DB-Mutation.

**Request**

```json
{
  "client_id": "550e8400-e29b-41d4-a716-446655440000",
  "batch_id": "6ba7b810-9dad-11d1-80b4-00c04fd430c8",
  "changes": [
    {
      "seq": 1,
      "id": "7c9e6679-7425-40de-944b-e07fc1f90ae7",
      "table": "entries",
      "operation": "upsert",
      "data": {
        "entry_date": "2026-06-30",
        "slot": "day",
        "mood_score": 4,
        "energy": 3,
        "stress": 2,
        "work_context": "homeoffice",
        "note": "Guter Tag",
        "tag_ids": ["a1b2c3d4-e5f6-7890-abcd-ef1234567890"],
        "symptoms": { "b2c3d4e5-f6a7-8901-bcde-f12345678901": 2 }
      },
      "updated_at": "2026-06-30T16:55:00.000000Z"
    }
  ]
}
```

| Feld                  | Typ                               | Beschreibung                      |
| --------------------- | --------------------------------- | --------------------------------- |
| `client_id`           | UUID                              | Stabile Geräte-/Browser-Identität |
| `batch_id`            | UUID                              | Idempotency-Key pro HTTP-Request  |
| `changes[].seq`       | int ≥ 1                           | Monotone Sequenz pro `client_id`  |
| `changes[].table`     | `entries` \| `tags` \| `symptoms` | Ziel-Tabelle                      |
| `changes[].operation` | `upsert` \| `delete`              | Default `upsert`                  |

**Response `200`**

```json
{
  "cursor": "eyJ1c2VyX3JldiI6IDEyMzQ1LCAid2FsbCI6ICIyMDI2LTA2LTMwVDEyOjAwOjAwWiJ9",
  "applied": 1,
  "skipped": 0,
  "conflicts": [
    {
      "entity_id": "7c9e6679-7425-40de-944b-e07fc1f90ae7",
      "entity_type": "entry",
      "field_name": "mood_score",
      "client_ts": "2026-06-30T16:55:00.000000Z",
      "server_ts": "2026-06-30T16:54:30.000000Z",
      "winner": "server",
      "client_value": { "value": 4 },
      "server_value": { "value": 3 }
    }
  ],
  "idempotent_replay": false
}
```

| Feld                | Beschreibung                                                        |
| ------------------- | ------------------------------------------------------------------- |
| `conflicts`         | Merge-Konflikte — Server-Wert wurde angewendet; **kein** HTTP `409` |
| `idempotent_replay` | `true` wenn `batch_id` bereits verarbeitet wurde                    |

**Fehler**

| Code          | Wann                                                          |
| ------------- | ------------------------------------------------------------- |
| `400`         | Ungültige `seq`-Reihenfolge, unbekannte `table`, leerer Batch |
| `401` / `403` | Nicht authentifiziert / nicht verifiziert                     |
| `422`         | Pydantic-Validierung (z. B. `mood_score` außerhalb 1..5)      |

`409 Conflict` ist **nicht** der LWW-Konflikt-Pfad — reserviert für harte
Invarianten (z. B. Slot-Kollision im Online-CRUD).

### `GET /api/v1/sync/pull`

**Query**

| Parameter | Typ    | Default | Beschreibung                          |
| --------- | ------ | ------- | ------------------------------------- |
| `since`   | string | —       | Opaque Cursor; fehlt → letzte 30 Tage |
| `limit`   | int    | 200     | Max. Änderungen pro Response (1..500) |

**Response `200`**

```json
{
  "cursor": "eyJ1c2VyX3JldiI6IDEyMzQ2LCAid2FsbCI6ICIyMDI2LTA2LTMwVDEyOjA1OjAwWiJ9",
  "changes": [
    {
      "seq": 0,
      "id": "7c9e6679-7425-40de-944b-e07fc1f90ae7",
      "table": "entries",
      "operation": "upsert",
      "data": {
        "entry_date": "2026-06-30",
        "slot": "day",
        "mood_score": 3,
        "energy": 3,
        "stress": 2,
        "work_context": "homeoffice",
        "note": null,
        "tag_ids": [],
        "symptoms": {}
      },
      "updated_at": "2026-06-30T16:54:30.000000Z"
    }
  ],
  "has_more": false,
  "server_time": "2026-06-30T17:00:00.000000Z"
}
```

Pull-`changes[].seq` ist `0` (server-origin); nur Push-Changes tragen Client-`seq`.

### `GET /api/v1/user/sync-conflicts`

Read-only Konflikt-Historie (M4.1 Sprint 1). Paginiert mit `limit` (1..200, Default 50)
und `offset`. Optional `entity_type=entry|tag|symptom`. Erfordert verifizierten User.

**Response `200`**

```json
{
  "items": [
    {
      "id": "f47ac10b-58cc-4372-a567-0e02b2c3d479",
      "entity_id": "7c9e6679-7425-40de-944b-e07fc1f90ae7",
      "entity_type": "entry",
      "field_name": "note",
      "client_ts": "2026-06-30T16:55:00.000000Z",
      "server_ts": "2026-06-30T16:54:30.000000Z",
      "created_at": "2026-06-30T16:55:01.000000Z",
      "resolved_at": null,
      "client_value": { "present": true, "changed": true },
      "server_value": { "present": false }
    }
  ],
  "total": 1,
  "limit": 50,
  "offset": 0
}
```

`note`-Konflikte liefern nur redacted Marker — **niemals** Klartext.

### Client IndexedDB (Dexie v1)

Lokale Tabellen (Sprint 3): `entries_local`, `change_log`, `sync_meta`.
ERD und Felddefinitionen: [ADR-0036 §5](adr/0036-offline-sync-v1-scope.md).

---

## 10a. Notes analysis & signals

```
GET    /api/v1/analysis/notes/marker-summary   Aggregierte Mood-Mittelwerte je Marker
POST   /api/v1/admin/entries/{id}/note-signals/reprocess   Signal-Reprocess (Admin)
```

Marker-CRUD liegt unter `/entries/{id}/note-markers` (§3). Signal-Reads unter
`/entries/{id}/note-signals`. Admin-Reprocess nutzt dieselbe Allowlist wie
`POST /insights/trigger` (`INSIGHT_TRIGGER_ADMIN_EMAILS`). Spez:
[`features/notes-in-analysis.md`](features/notes-in-analysis.md), ADR-N-01–03.

## 10b. Media (M13 foundation)

```
POST   /api/v1/media/photos   Foto-Upload mit serverseitigem EXIF-Strip (30/min)
```

Akzeptiert JPEG/PNG/WebP/GIF bis 10 MiB, stripped GPS/biometrische Metadaten via
Pillow (`app/services/exif_strip.py`), Response enthält Metadata inkl.
`stored: false` — MinIO-Persistenz und Galerie folgen als volles M13 (#28).

## 11. Export

```
GET    /api/v1/user/export  DSGVO Art. 20 ZIP mit export.json + README.txt
GET    /api/v1/export/json  Direkter JSON-Export
GET    /api/v1/export/csv   Direkter CSV-Export der Entries
```

Der ZIP-Export ist der kanonische Datenportabilitaets-Endpunkt. JSON/CSV sind
Convenience-Downloads fuer Weiterverarbeitung und Arztgespraeche. Das Format ist
in [`DATA_EXPORT_FORMAT.md`](DATA_EXPORT_FORMAT.md) dokumentiert.

---

## 12. Developer Diagnostics

```
GET    /api/v1/dev/info
```

Default-off Diagnose-Endpunkt fuer verifizierte User. Wenn
`DEV_VIEW_ENABLED=false` ist, antwortet der Endpunkt absichtlich mit `404`.
Ohne Session kommt `401`, mit unverified User `403`.

Die Response trennt GitHub-Version und Container-Artefakt:

```json
{
  "git_commit": "26c4274e0b2688931f7ceab108d72b775233fdf7",
  "git_branch": "main",
  "build_time": "2026-05-10T16:00:00Z",
  "image_tag": "sha-26c4274",
  "image_digest": "ghcr.io/sturmi77/correlcore-api@sha256:...",
  "image_hash": "ghcr.io/sturmi77/correlcore-api@sha256:...",
  "python_version": "3.12.13",
  "fastapi_version": "0.136.1",
  "db_migration_head": "013",
  "db_pool_size": 10,
  "db_checked_out": 1,
  "redis_connected": true,
  "minio_connected": false,
  "health_ready": true,
  "uptime_seconds": 42
}
```

`git_commit` wird beim Image-Build eingebettet und ist die primaere
GitHub-Versionskennung. `image_digest` ist nur gesetzt, wenn das Deployment den
echten OCI/RepoDigest als ENV `IMAGE_DIGEST` uebergibt; sonst ist der Wert
`null`.

---

## 13. Admin (geplant)

Admin-Endpunkte und Audit-Log sind noch nicht implementiert. Aktuell gibt es
keine öffentliche `/api/v1/admin/*`-Route.

```
GET    /api/v1/admin/users          User-Liste
POST   /api/v1/admin/users/invite   Einladungslink erstellen
DELETE /api/v1/admin/users/{id}     User löschen (inkl. Datenlöschung)
GET    /api/v1/admin/audit-log      Audit-Log abrufen
```

---

## 14. Fehlerformat

Aktueller Ist-Stand ist das FastAPI-Fehlerformat. Beispiel:

```json
{
  "detail": [
    {
      "type": "greater_than_equal",
      "loc": ["body", "mood_score"],
      "msg": "Input should be greater than or equal to 1"
    }
  ]
}
```

RFC 7807 Problem Details bleiben ein mögliches API-Hardening für spätere
Milestones.

`GET /api/v1/insights/tag-clusters` (M7) liefert entweder `status: "insufficient_data"`
mit Entry-/Signal-Zaehlern oder `status: "ok"` mit Clustern unter der neutralen
Semantik "Tags that often appear together". Reifegrad-Stufen (ADR-0037):

| Tage    | `cluster_maturity`      | `cluster_mode`               |
| ------- | ----------------------- | ---------------------------- |
| &lt; 30 | — (`insufficient_data`) | —                            |
| 30–44   | `early`                 | `pair`                       |
| 45–89   | `provisional`           | `kmeans` (Fallback `pair`)   |
| ≥ 90    | `robust`                | `kmeans` (mixed tag/symptom) |

Zusaetzliche Felder: `cluster_maturity`, `cluster_mode`, `entries_until_robust`,
`silhouette_score`, `window_days` (effektive Tage im Fenster).

`POST /api/v1/insights/regenerate` (M10.1) fuehrt dieselbe Pipeline wie der
Nightly Worker fuer den eingeloggten Owner aus. Rate-Limit: 1× pro Stunde (Redis).
Bei `analytics_enabled=false` → `403`. Response:

```json
{
  "status": "ok",
  "generated_for_date": "2026-07-13",
  "insight_count": 13,
  "tag_clusters_status": "ok",
  "trigger_source": "user_regenerate"
}
```

Nach erfolgreichem `POST /entries/batch` wird eine debounced Hintergrund-Regeneration
(5 min) ausgeloest. Admin-Trigger: `POST /api/v1/insights/trigger` mit
`INSIGHT_TRIGGER_ADMIN_EMAILS`.

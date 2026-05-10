# MoodSync — API-Richtlinien & Endpunkte

Dieses Dokument leitet sich aus [`DESIGN_DOCUMENT.md`](DESIGN_DOCUMENT.md) ab.

---

## 1. Allgemeine Richtlinien

- **OpenAPI 3.1** — Spec wird bei jedem Build auto-generiert aus FastAPI-Annotationen
- **Versionierung:** `/api/v1/...` — Version im URL-Pfad
- **Auth:** Bearer Token (JWT via Authentik) im `Authorization`-Header **oder** HttpOnly-Cookie (`session_token`)
- **Fehlerformat:** RFC 7807 Problem Details
- **Datumsformat:** ISO 8601 (`2026-04-20T17:00:00Z`)
- **IDs:** UUID v4
- **Paginierung:** Cursor-basiert (`?cursor=<opaque>&limit=50`)
- **Rate Limiting:** 60 Req/Minute per User (via Redis)

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
  unbekannte Mail, falsches Passwort und unverifizierten Account ab
  (Schutz vor User-Enumeration)
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

M1-Implementierungsstand (Issue #7). `tags`, `symptoms`, `sleep_*` und der
`/entries/date/{date}`-Lookup folgen in Issues #8 (Tags), #9 (Symptome)
und M7 (Schlaf). Alle Endpunkte hier laufen hinter
`get_current_verified_user` und sind pro IP rate-limitiert.

```
POST   /api/v1/entries                  Neuen Eintrag erstellen        (60/min)
GET    /api/v1/entries                  Liste (gefiltert, neueste zuerst) (120/min)
GET    /api/v1/entries/{id}             Einzelner Eintrag              (120/min)
PATCH  /api/v1/entries/{id}             Eintrag aktualisieren          (60/min)
```

**Geplant (folgt in M1+):**

```
DELETE /api/v1/entries/{id}             Eintrag löschen            (#23 — oder via DELETE /user/me, siehe §6)
GET    /api/v1/entries/date/{date}      Eintrag für ein Datum     (M1 Followup)
```

### Datentypen

- `slot` — Enum: `day` (Default, M1), `morning`, `noon`, `evening` (reserviert für M3+).
- `work_context` — Enum: `homeoffice`, `office`, `vacation`, `sick`, `weekend`, `travel`.
- `mood_score`, `energy`, `stress` — Integer 1..5 (DB-CHECK + Pydantic-Validierung).
- `note` — Optional, max. 4000 Zeichen. Wird in der Spalte `note_enc` (BYTEA) als Fernet-Ciphertext unter dem User-DEK gespeichert (Issue #26, ADR-0005). API-Surface bleibt Klartext: Requests senden `note: "..."`, Responses geben den entschlüsselten String zurück. Ohne gültigen Auth-Kontext (DEK fehlt) liefert das Backend 401.

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
  "energy": 4,
  "stress": 1,
  "work_context": "office",
  "note": "Korrektur"
}
```

Fehler:

- `404 Not Found` — wie oben.
- `409 Conflict` — Eintrag ist älter als 7 Tage (read-only).

### Tag-Zuweisung

Der Tag-Set eines Eintrags wird über einen separaten, idempotenten
`PUT`-Endpunkt verwaltet — siehe §4. `entries`-Antworten enthalten
**keine** Tag-Liste; Clients laden Tags pro Entry on-demand über
`GET /entries/{id}/tags`. Damit bleibt das Entry-Schema stabil und
batch-fähig (`GET /entries`).

### Zukünftige Felder

```jsonc
// Sobald Issue #9 / M7 landen, erweitert sich die Antwort um:
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
  "created_at": "2026-05-04T17:00:00Z",
  "updated_at": "2026-05-04T17:00:00Z"
}
```

---

## 5. Symptome

Gesundheits-Symptome werden parallel zu Tags pro Entry erfasst (Issue #9 + Issue #57, ADR-0008). Seit Issue #57 sind Symptome — analog zum Tag-System — in zwei Klassen geteilt:

- **Default-Symptome** — kuratierte Liste (5 Symptome aus Migration-Seed `006_add_symptom_master_table.py`). `user_id IS NULL`, `is_default = true`. Read-only für alle User; lesbar auch ohne Auth über `/symptoms/default`.
- **Custom-Symptome** — pro User mit `user_id = <user>`. Vollständige CRUD-Hoheit, Slugs müssen sich nicht mit Defaults überschneiden. Hard Cap: **50 pro User** (`MAX_SYMPTOMS_PER_USER`).

Die Intensität bewegt sich in einem 0–3-Bereich, der im UI als 4-Punkt-Skala gerendert wird. Symptome sind Gesundheitsdaten nach DSGVO Art. 9 — Server-Logs enthalten weder `slug`/`name`/`symptom_id` noch `intensity` (statisch via `test_log_scrubbing` und `test_symptom_service_logs_no_sensitive_fields` geprüft). Custom-Symptom-Namen werden in `symptoms.name_enc` als Fernet-Ciphertext unter dem User-DEK gespeichert (Issue #26, ADR-0005); Default-Symptom-Namen bleiben plaintext, weil sie kuratierte, nicht-personenbezogene Labels sind und ohne aktiven User-Kontext gelesen werden müssen (`GET /symptoms/default`). Der `slug` bleibt auch für Custom-Symptome plaintext — ein Slug-HMAC-Hardening ist als Backlog für M9+ vorgesehen.

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

- `id` — UUID des Symptoms (Default-Rows nutzen einen deterministischen `uuid5` aus `moodsync.symptom.<slug>`, siehe ADR-0008).
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
DELETE /api/v1/user/me               Account und alle abhängigen Daten löschen (DSGVO Art. 17)
```

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
curl -X DELETE https://api.moodsync.example/api/v1/user/me \
  -H "Cookie: access_token=..." \
  -H "Content-Type: application/json" \
  -d '{"password":"mein-aktuelles-passwort"}'
# → 204 No Content
```

---

## 7. Insights

```
GET    /api/v1/insights              Alle Insights des Users
GET    /api/v1/insights/latest       Neuester Insight je Metrik
POST   /api/v1/insights/trigger      Worker manuell anstossen (Admin only)
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

`timeseries` liefert fuer `week` sieben Tagespunkte, fuer `month` 30 Tagespunkte
und fuer `year` 12 Monatspunkte mit `entry_count`, `mood_avg`, `energy_avg` und
`stress_avg`. Fehlende Perioden bleiben als Punkte mit `entry_count=0` und
`*_avg=null` erhalten.

`tags` liefert die Tag-Frequenz-Heatmap pro sichtbarem Tag:

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

## 9. Sync (Offline-First)

```
POST   /api/v1/sync/push    Client-Änderungen hochladen
GET    /api/v1/sync/pull    Delta seit Cursor herunterladen
```

### Push-Request

```json
{
  "client_id": "device-uuid",
  "changes": [
    {
      "id": "entry-uuid",
      "table": "entries",
      "data": {...},
      "updated_at": "2026-04-20T16:55:00Z"
    }
  ]
}
```

### Pull-Response

```json
{
  "cursor": "eyJjdXJzb3IiOiAxMjM0NX0=",
  "changes": [...],
  "conflicts": [...]
}
```

---

## 10. Export

```
GET    /api/v1/user/export  DSGVO Art. 20 ZIP mit export.json + README.txt
GET    /api/v1/export/json  Direkter JSON-Export
GET    /api/v1/export/csv   Direkter CSV-Export der Entries
```

Der ZIP-Export ist der kanonische Datenportabilitaets-Endpunkt. JSON/CSV sind
Convenience-Downloads fuer Weiterverarbeitung und Arztgespraeche. Das Format ist
in [`DATA_EXPORT_FORMAT.md`](DATA_EXPORT_FORMAT.md) dokumentiert.

---

## 11. Developer Diagnostics

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
  "image_digest": "ghcr.io/sturmi77/moodsync-api@sha256:...",
  "image_hash": "ghcr.io/sturmi77/moodsync-api@sha256:...",
  "python_version": "3.12.13",
  "fastapi_version": "0.115.0",
  "db_migration_head": "009",
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

## 12. Admin

```
GET    /api/v1/admin/users          User-Liste
POST   /api/v1/admin/users/invite   Einladungslink erstellen
DELETE /api/v1/admin/users/{id}     User löschen (inkl. Datenlöschung)
GET    /api/v1/admin/audit-log      Audit-Log abrufen
```

---

## 13. Fehlerformat (RFC 7807)

```json
{
  "type": "https://moodsync.app/errors/validation-error",
  "title": "Validation Error",
  "status": 422,
  "detail": "mood_score must be between -2 and 2",
  "instance": "/api/v1/entries"
}
```

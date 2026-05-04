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
POST   /api/v1/auth/register              Registrierung (Issue #39: sendet Verify-Mail)
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
DELETE /api/v1/entries/{id}             Eintrag löschen            (#23 oder M9 Account-Erasure)
GET    /api/v1/entries/date/{date}      Eintrag für ein Datum     (M1 Followup)
```

### Datentypen

- `slot` — Enum: `day` (Default, M1), `morning`, `noon`, `evening` (reserviert für M3+).
- `work_context` — Enum: `homeoffice`, `office`, `vacation`, `sick`, `weekend`, `travel`.
- `mood_score`, `energy`, `stress` — Integer 1..5 (DB-CHECK + Pydantic-Validierung).
- `note` — Optional, max. 4000 Zeichen. Wird in der Spalte `note_enc` gespeichert; M1
  liefert Klartext, ADR-0005 + Issue #26 ziehen Fernet-Verschlüsselung at-rest nach.

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
// "symptoms": [{ "symptom_key": "headache", "intensity": 1 }],
// "sleep_minutes": 450,
// "sleep_quality": 3
```

---

## 4. Tags

M1-Implementierungsstand (Issue #8). Tags sind in zwei Klassen geteilt:

- **Default-Tags** — kuratierte Liste (30 Tags, gepflegt im Migration-Seed `004_create_tags.py`). `user_id IS NULL`, `is_default = true`. Read-only für alle User; lesbar auch ohne Auth über `/tags/default`.
- **Custom-Tags** — pro User mit `user_id = <user>`. Vollständige CRUD-Hoheit, Slugs müssen sich nicht mit Defaults überschneiden.

Kategorien (`TagCategory`): `sport`, `social`, `work`, `leisure`, `consumption`, `health`, `other`.

```
GET    /api/v1/tags/default                Kuratierte Standard-Tags        (no auth)
GET    /api/v1/tags                        Defaults + eigene Custom-Tags   (60/min)
POST   /api/v1/tags                        Neuen Custom-Tag erstellen      (60/min)
PATCH  /api/v1/tags/{id}                   Custom-Tag aktualisieren        (60/min)
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
- `is_default` — boolean, server-managed; Defaults sind nicht mutierbar.

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

Nur Custom-Tags des aufrufenden Users sind editierbar. Versuch, einen Default-Tag zu ändern, liefert `403 Forbidden`. Slug ist bewusst **nicht** patchbar (würde Verweise in `entry_tags` brechen).

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

Löscht einen Custom-Tag und kaskadiert alle `entry_tags`-Verknüpfungen (FK `ON DELETE CASCADE`). Default-Tags lassen sich nicht löschen (`403 Forbidden`).

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
- `409 Conflict` — Mindestens eine `tag_id` ist nicht sichtbar (weder Default noch Custom-Tag des Users).
- `422 Unprocessable Entity` — Liste enthält Duplikate oder ist länger als 50.

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
  "created_at": "2026-05-04T17:00:00Z",
  "updated_at": "2026-05-04T17:00:00Z"
}
```

---

## 5. Symptome

Gesundheits-Symptome werden parallel zu Tags pro Entry erfasst (Issue #9). Standard-Keys sind eine geschlossene Menge (kein User-Custom-Surface in M1); die Intensität bewegt sich in einem 0–3-Bereich, der im UI als 4-Punkt-Skala gerendert wird. Symptome sind Gesundheitsdaten nach DSGVO Art. 9 — Server-Logs enthalten weder `symptom_key` noch `intensity` (statisch via `test_log_scrubbing` und `test_symptom_service_logs_no_sensitive_fields` geprüft).

```
GET    /api/v1/symptoms/standard                Standard-Symptom-Keys (kein Auth)
GET    /api/v1/entries/{entry_id}/symptoms      Aktuelle Symptome eines Entries
PUT    /api/v1/entries/{entry_id}/symptoms      Replace-Set: gesamte Symptom-Liste
```

### Datentypen

- `symptom_key`: String, einer aus der geschlossenen Menge `headache | digestion | back_pain | fatigue | cold`. CHECK-Constraint in der DB sowie Pydantic-Validator setzen das durch.
- `intensity`: Integer 0..3 (0 = nicht vorhanden, 1 = leicht, 2 = mittel, 3 = stark). DB-CHECK + Pydantic-Field-Constraint mirroren den Range. UI rendert 4 Dots, kein freier Zahlen-Input.

### `GET /api/v1/symptoms/standard`

Liefert die kuratierte Liste der M1-Standard-Symptom-Keys. Die Liste ist nicht personenbezogen (Build-Time-Konstante), daher kein Auth erforderlich — das Picker-UI kann vor Login-Abschluss rendern. Rate-Limit: 120/min/IP.

Response `200 OK`:

```json
{
  "keys": [
    { "symptom_key": "back_pain" },
    { "symptom_key": "cold" },
    { "symptom_key": "digestion" },
    { "symptom_key": "fatigue" },
    { "symptom_key": "headache" }
  ]
}
```

### `GET /api/v1/entries/{entry_id}/symptoms`

Liefert die aktuell auf einem Entry geloggten Symptome (Liste, leer wenn keine zugewiesen). Owner-scoped via Service-Layer; `404 Not Found`, falls der Entry einem anderen User gehört oder nicht existiert. Rate-Limit: 120/min.

Response `200 OK`: Liste von `SymptomResponse`-Objekten (siehe unten).

### `PUT /api/v1/entries/{entry_id}/symptoms`

**Replace-Set-Semantik:** Die übergebene `symptoms`-Liste ersetzt das gesamte Symptom-Set des Entries. Eine leere Liste entfernt alle Symptome. Maximale Listenlänge: **32** (`MAX_SYMPTOMS_PER_ENTRY`). Rate-Limit: 60/min.

Der Service-Layer berechnet einen Key-basierten Diff (add / update intensity / remove), sodass die Tabelle bei Updates nicht mit veralteten Zeilen wächst.

Request:

```json
{
  "symptoms": [
    { "symptom_key": "headache", "intensity": 2 },
    { "symptom_key": "cold", "intensity": 1 }
  ]
}
```

Response `200 OK`: Liste der `SymptomResponse`-Objekte nach dem Replace, sortiert nach `symptom_key`.

Fehler:

- `404 Not Found` — Entry gehört nicht dem User oder existiert nicht.
- `422 Unprocessable Entity` — unbekannter `symptom_key`, `intensity` außerhalb 0..3, doppelte Keys im Request oder Liste länger als 32.

### `SymptomResponse`

```json
{
  "id": "uuid",
  "entry_id": "uuid",
  "user_id": "uuid",
  "symptom_key": "headache",
  "intensity": 2,
  "created_at": "2026-05-04T17:00:00Z",
  "updated_at": "2026-05-04T17:00:00Z"
}
```

---

## 6. Insights

```
GET    /api/v1/insights              Alle Insights des Users
GET    /api/v1/insights/latest       Neuester Insight je Metrik
POST   /api/v1/insights/trigger      Worker manuell anstossen (Admin only)
```

---

## 7. Sync (Offline-First)

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

## 8. Export

```
GET    /api/v1/export/json      Vollexport als JSON
GET    /api/v1/export/csv       Entries als CSV
POST   /api/v1/export/zip       JSON + Fotos als ZIP (async, gibt Job-ID zurück)
GET    /api/v1/export/jobs/{id} Status des ZIP-Jobs
```

---

## 9. Admin

```
GET    /api/v1/admin/users          User-Liste
POST   /api/v1/admin/users/invite   Einladungslink erstellen
DELETE /api/v1/admin/users/{id}     User löschen (inkl. Datenlöschung)
GET    /api/v1/admin/audit-log      Audit-Log abrufen
```

---

## 10. Fehlerformat (RFC 7807)

```json
{
  "type": "https://moodsync.app/errors/validation-error",
  "title": "Validation Error",
  "status": 422,
  "detail": "mood_score must be between -2 and 2",
  "instance": "/api/v1/entries"
}
```

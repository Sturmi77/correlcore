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

- `slot`         — Enum: `day` (Default, M1), `morning`, `noon`, `evening` (reserviert für M3+).
- `work_context` — Enum: `homeoffice`, `office`, `vacation`, `sick`, `weekend`, `travel`.
- `mood_score`, `energy`, `stress` — Integer 1..5 (DB-CHECK + Pydantic-Validierung).
- `note`         — Optional, max. 4000 Zeichen. Wird in der Spalte `note_enc` gespeichert; M1
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
- `403 Forbidden`   — nicht verifizierter Account.
- `409 Conflict`    — für `(user, entry_date, slot)` existiert bereits ein Eintrag.
- `422 Unprocessable Entity` — Range-Verletzung (mood/energy/stress ∉ 1..5),
  `entry_date` in der Zukunft, oder älter als 7 Tage.

### `GET /api/v1/entries`

Query-Parameter (alle optional):

- `start_date` (ISO `YYYY-MM-DD`) — inklusiv.
- `end_date`   (ISO `YYYY-MM-DD`) — inklusiv.
- `limit`      (1..365, Default 100).

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
- `409 Conflict`  — Eintrag ist älter als 7 Tage (read-only).

### Zukünftige Felder

```jsonc
// Sobald Issues #8/#9 / M7 landen, erweitert sich die Antwort um:
// "tags":     ["uuid-sport", "uuid-musik"],
// "symptoms": [{ "symptom_key": "headache", "intensity": 1 }],
// "sleep_minutes": 450,
// "sleep_quality": 3
```

---

## 4. Tags

```
GET    /api/v1/tags              Alle Tags des Users
POST   /api/v1/tags              Neuen Tag erstellen
PATCH  /api/v1/tags/{id}         Tag aktualisieren
DELETE /api/v1/tags/{id}         Tag löschen
GET    /api/v1/tags/default      Kuratierte Standard-Tags (30 Stück)
```

---

## 5. Insights

```
GET    /api/v1/insights              Alle Insights des Users
GET    /api/v1/insights/latest       Neuester Insight je Metrik
POST   /api/v1/insights/trigger      Worker manuell anstoßen (Admin only)
```

---

## 6. Sync (Offline-First)

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

## 7. Export

```
GET    /api/v1/export/json      Vollexport als JSON
GET    /api/v1/export/csv       Entries als CSV
POST   /api/v1/export/zip       JSON + Fotos als ZIP (async, gibt Job-ID zurück)
GET    /api/v1/export/jobs/{id} Status des ZIP-Jobs
```

---

## 8. Admin

```
GET    /api/v1/admin/users          User-Liste
POST   /api/v1/admin/users/invite   Einladungslink erstellen
DELETE /api/v1/admin/users/{id}     User löschen (inkl. Datenlöschung)
GET    /api/v1/admin/audit-log      Audit-Log abrufen
```

---

## 9. Fehlerformat (RFC 7807)

```json
{
  "type": "https://moodsync.app/errors/validation-error",
  "title": "Validation Error",
  "status": 422,
  "detail": "mood_score must be between -2 and 2",
  "instance": "/api/v1/entries"
}
```

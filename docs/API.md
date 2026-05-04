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

```
GET    /api/v1/entries                  Liste (gefiltert, paginiert)
POST   /api/v1/entries                  Neuen Eintrag erstellen
GET    /api/v1/entries/{id}             Einzelner Eintrag
PATCH  /api/v1/entries/{id}             Eintrag aktualisieren
DELETE /api/v1/entries/{id}             Eintrag löschen
GET    /api/v1/entries/date/{date}      Eintrag für ein Datum (YYYY-MM-DD)
```

### Entry-Objekt

```json
{
  "id": "uuid",
  "user_id": "uuid",
  "entry_date": "2026-04-20",
  "slot": "day",
  "mood_score": 2,
  "energy": 3,
  "stress": 1,
  "work_context": "homeoffice",
  "note_enc": "...",
  "sleep_minutes": 450,
  "sleep_quality": 3,
  "tags": ["uuid-sport", "uuid-musik"],
  "symptoms": [{ "symptom_key": "headache", "intensity": 1 }],
  "created_at": "2026-04-20T17:00:00Z",
  "updated_at": "2026-04-20T17:00:00Z"
}
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

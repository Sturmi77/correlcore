# ADR-0006: Cookie-basierte Auth im Web mit geplanter Capacitor-Bearer-Migration

**Status:** Akzeptiert
**Datum:** 2026-05-04
**Kontext:** Issue #40, ergänzt ADR-0004 (Auth-Strategie) und ADR-0002 (Capacitor)

---

## Kontext

ADR-0004 legt fest, dass Phase 1 mit nativem JWT in FastAPI läuft. Offen blieb, **wie der Browser-Client die Token hält** — Cookie oder In-Memory-Bearer? Beide Varianten sind in der CorrelCore-Threat-Modellierung relevant, weil:

- DSGVO Art. 9 (Gesundheitsdaten) verlangt erhöhte Sicherheit gegen Token-Diebstahl.
- Phase 2 nutzt Capacitor (ADR-0002) — `capacitor://`-Schema blockiert Third-Party-Cookies zur API-Domain.

Eine Entscheidung "ein Mechanismus für alle Phasen" ist nicht möglich, ohne entweder XSS-Resistenz (im Web) oder Capacitor-Kompatibilität (mobil) zu opfern.

## Entscheidung

**Phase 1 (Web, M1–M10):** HttpOnly-Cookies (`SameSite=Strict`, `Secure` in Prod). Refresh-Token in `/auth/refresh` rotiert; Access-Cookie kurzlebig (15 min).

**Phase 2 (Mobile, M11+):** Bearer-Token in einer In-Memory-Variable, ausgeliefert über `TokenResponse.access_token` + `refresh_token` bei Opt-in `?include_access_token=true`. Kein `localStorage` / `sessionStorage` für Tokens. API-Requests senden `Authorization: Bearer <access>`. Refresh nutzt den bestehenden Body-Fallback `RefreshRequest.refresh_token` (nicht den Access-Header — Refresh-JWT ≠ Access-JWT) und rotiert das In-Memory-Paar.

Der Wechsel ist isoliert in **`apiFetch` / `sessionTokens` / `platform` (`apps/web/src/lib/api/`)**: Build-Flag `VITE_CAPACITOR=1`. Browser bleibt Cookie-Pfad. Keine Domain-Stores werden dupliziert.

## Begründung

| Kriterium                    | Cookie (Phase 1)                                                  | Bearer (Phase 2)                                          |
| ---------------------------- | ----------------------------------------------------------------- | --------------------------------------------------------- |
| **XSS-Resistenz**            | ✅ HttpOnly — JS kann den Token nicht lesen                       | ⚠️ JS-Heap, aber In-Memory (kein persistenter Storage)    |
| **CSRF-Risiko**              | Mitigiert via SameSite=Strict + State-Changing Requests POST/JSON | ✅ N/A (kein Cookie, kein automatisches Senden)           |
| **Capacitor-Kompatibilität** | ❌ `capacitor://`-Cookies werden nicht an API gesendet            | ✅ Header funktioniert in beiden Schemes                  |
| **JS-Bundle-Kosten**         | ✅ Null (Browser handhabt Cookie automatisch)                     | Minimal (~0.5 KB für In-Memory-Container)                 |
| **DSGVO Art.-9-Risiko**      | Niedrigste Angriffsfläche (XSS-immun)                             | Akzeptabel, da App-Container kein dritter JavaScript-Code |

**Cookie für Web** maximiert XSS-Resistenz für Gesundheitsdaten, was angesichts unserer DSGVO-Verpflichtungen den Ausschlag gibt. **Bearer für Capacitor** ist die einzige funktionierende Variante; das XSS-Risiko ist dort drastisch geringer, weil der App-Container keine eingebettete Drittanbieter-Werbung oder externe Scripts ausführt.

Die Migration ist **antizipiert, aber lokal**: nur `apiFetch` ändert sich.

## Konsequenzen

**Positiv:**

- Web nutzt das sicherste Pattern für Art.-9-Daten.
- Der Capacitor-Pfad ist bereits im Backend vorbereitet (Login/Register liefern `access_token` im Response-Body).
- Keine Code-Duplikation in API-Modulen oder Stores.

**Negativ:**

- Refresh-Logik muss in zwei Varianten getestet werden (Cookie- + Bearer-Pfad).
- CSRF-Schutz fällt in Phase 1 in unsere Verantwortung (SameSite=Strict + JSON-Content-Type-Pflicht).

**Neutral:**

- Phase 2 erbt automatisch alle aktuellen Backend-Endpoints (kein neues Interface).
- Single-Flight-Refresh-Pattern (`apps/web/src/lib/api/client.ts`) gilt in beiden Varianten unverändert.

## Implementation-Notiz — `Secure`-Flag (Update 2026-05-08)

Die ursprüngliche Implementierung (`backend/app/core/auth_cookies.py`) hat `secure=True` für beide Cookies hartkodiert. Browser verwerfen `Set-Cookie`-Header mit `Secure` jedoch bei HTTP-Origins gemäß RFC 6265bis §4.1.2.5 — darunter fallen lokale Homelab-Setups, die das Web-Image über eine Tailscale-IP oder einen plain-HTTP-Reverse-Proxy ausliefern. Symptom: Login-Endpoint liefert 200 + Set-Cookie, der Browser legt aber **nichts** in der Cookie-Jar ab; alle Folge-Requests sind 401, das Frontend zeigt "Bitte melde dich erneut an".

Fix:

- Neue Settings-Variable `COOKIE_SECURE: bool | None = None` (`backend/app/core/config.py`).
- Property `Settings.cookie_secure_effective`: explizite Werte gewinnen; `None` (Default) resolved zu `False` für `APP_ENV=development`, `True` für alles andere (staging, production).
- `set_auth_cookies` setzt `secure=settings.cookie_secure_effective` statt hartkodiert `True`.
- Model-Validator verbietet `COOKIE_SECURE=false` in `APP_ENV=production` — die Garantie aus dem Entscheidungs-Statement ("`Secure` in Prod") bleibt zwingend.
- `infra/dockhand/.env.example` setzt `COOKIE_SECURE=false` mit Begründung, weil dieser Stack über Tailscale ohne TLS-Terminierung ausgeliefert wird; `infra/docker/.env.example` dokumentiert die Variable als optional.
- Homelab-Compose-Defaults (`docker-compose.user-test.yml`, `infra/dockge/compose.yaml`, `docker-compose.quickstart.yml`, `infra/dockhand/compose.yaml`) setzen `COOKIE_SECURE=${COOKIE_SECURE:-false}` — Staging ohne diesen Default emittierte Secure-Cookies und erzeugte Folge-401 `Could not validate credentials`.
- Zusätzlich: `cookie_secure_for_request()` honoriert in Non-Production bei unset `COOKIE_SECURE` das von `hooks.server.ts` gesetzte `X-Forwarded-Proto` (`http` → Secure aus). Production bleibt zwingend Secure.

Keine Auswirkung auf den Capacitor-Pfad (Phase 2): Bearer-Tokens sind vom `Secure`-Flag nicht betroffen.

## Amendment — Persistent Session / „Angemeldet bleiben“ (Issue #453, 2026-07-18)

**Status:** Accepted with the implementation of PS-0…PS-3.

Phase-1 and Phase-2 clients share one product flag `remember_me` (default `true`)
on login. Storage backends differ; web `localStorage` / `sessionStorage` must
**never** hold JWTs.

| Surface   | `remember_me=true`                                                                                                                  | `remember_me=false`                                          |
| --------- | ----------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------ |
| Web / PWA | HttpOnly cookies with `Max-Age` (access + refresh TTLs)                                                                             | Session cookies (no `Max-Age`)                               |
| Capacitor | Refresh (+ access) in Android **EncryptedSharedPreferences** (Keystore), restored into in-memory `sessionTokens` before `hydrate()` | Memory only (cleared on process death); secure store cleared |

Logout clears cookies (Web/PWA) and secure store + widget credentials (Capacitor).
The Glance widget mirror remains an M11 exception and is only written when
remember is on.

Homelab note: if `COOKIE_SECURE` does not match the deployment scheme, browsers
silently drop cookies — symptoms look like “always login”. See Secure-Flag
section above and `docs/features/PERSISTENT_SESSION_PLAN.md`.

## Referenzen

- ADR-0002: Capacitor statt TWA
- ADR-0004: Auth-Strategie (JWT Phase 1, Authentik Phase 2)
- ADR-0011: Web-internal Reverse-Proxy (relevant für `INTERNAL_API_URL`-Topologie, in der Cookies das Web-Image überhaupt erst sehen)
- Issue #40: Frontend Login/Register-UI
- RFC 6265bis §4.1.2.5 (Set-Cookie `Secure`-Attribut, Verwerfungssemantik bei HTTP)
- OWASP Cheat-Sheet "JWT for Java" — Storage-Empfehlungen für SPA + Mobile

---

## Amendment 2026-08-26 — CSRF Content-Type enforcement, CSP, access-token residual (#779)

Follow-ups from the 2026-08-25 security audit (epic #776; findings M12, S3, L1).

### M12 — Content-Type CSRF now enforced (was: claimed only)

The "JSON Content-Type-Pflicht" this ADR promised (see the table above) was
documented but never enforced in the API — `SameSite=strict` was the only real
control. It is now enforced by `app.core.csrf.ContentTypeCSRFMiddleware`:

- State-changing methods (`POST`/`PUT`/`PATCH`/`DELETE`) whose request **body**
  declares a Content-Type other than `application/json` are rejected with
  **415**.
- `multipart/form-data` is the one documented exception, for the authenticated
  photo upload (`POST /api/v1/media/photos`); that route stays covered by
  SameSite=strict + auth.
- Bodiless mutations (logout, refresh, account delete) send no Content-Type and
  are allowed — there is no form payload to smuggle.

This blocks the classic cross-site `<form>` CSRF vector (forms can only send the
three "simple" content types) as defense-in-depth behind SameSite=strict.

### S3 — Content-Security-Policy (report-only first)

Issue #22 shipped HSTS / frameDeny / nosniff / Permissions-Policy via the
Traefik `security-headers` middleware but no CSP. A **report-only** CSP is now
attached to that middleware (`infra/docker/docker-compose.yml`) so violations
are observed without breaking the app. It is intentionally not yet enforcing:
the current SvelteKit build needs `style-src 'unsafe-inline'`, to be tightened
with hashes/nonces before the policy is promoted to a blocking
`Content-Security-Policy` header.

### L1 — Access-token denylist on logout: accepted residual

Logout revokes the refresh JTI immediately; the short-lived **access** token
(TTL ≤ 15 min, `SameSite=strict`, HttpOnly) stays valid until it expires. A
Redis denylist on logout was considered and **deferred** (accepted residual):
no denylist store is provisioned yet (the analytics Redis/arq queue is still
pending, #761), and the ≤15-minute window on an HttpOnly+SameSite cookie is a
low-severity residual for the current single-app, self-host threat model. Revisit
when the Redis job queue lands or a shared-device deployment is targeted.

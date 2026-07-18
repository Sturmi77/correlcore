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

Keine Auswirkung auf den Capacitor-Pfad (Phase 2): Bearer-Tokens sind vom `Secure`-Flag nicht betroffen.

## Referenzen

- ADR-0002: Capacitor statt TWA
- ADR-0004: Auth-Strategie (JWT Phase 1, Authentik Phase 2)
- ADR-0011: Web-internal Reverse-Proxy (relevant für `INTERNAL_API_URL`-Topologie, in der Cookies das Web-Image überhaupt erst sehen)
- Issue #40: Frontend Login/Register-UI
- RFC 6265bis §4.1.2.5 (Set-Cookie `Secure`-Attribut, Verwerfungssemantik bei HTTP)
- OWASP Cheat-Sheet "JWT for Java" — Storage-Empfehlungen für SPA + Mobile

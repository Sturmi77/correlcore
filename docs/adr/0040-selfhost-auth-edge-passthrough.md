# ADR-0040: Robuster Self-Host-Auth-Edge — Ein-Regel-Passthrough + Bearer-Fallback

**Datum:** 2026-07-25
**Status:** Accepted
**Umsetzung:** Referenz-Nginx-Config unter `infra/nginx/`, Selbsttest
`scripts/verify-auth-cookie.sh`, ehrlicher Client-Fehler
`SessionPersistenceError` (`apps/web/src/lib/api/client.ts`). Bearer-Fallback
für den Browser ist als akzeptierte Richtung dokumentiert, aber bewusst als
eigener Folge-PR ausgelagert.

---

## Kontext

Ein wiederkehrender Bug: Login über die Landing Page (`https://correlcore.com`)
meldet **„E-Mail oder Passwort ist falsch"** — obwohl dieselben Zugangsdaten in
der APK (frisch aus- und wieder eingeloggt) problemlos funktionieren. Der Fehler
wurde mehrfach „gefixt" und kam immer zurück.

### Beweiskette (Live-Diagnose 2026-07-25)

- APK-`VITE_API_BASE_URL` = `https://correlcore.com/api/v1` → **gleiches Backend,
  gleiche DB** wie der Web-Login.
- APK bekommt bei frischem Login `200` → das Passwort ist gegen diese eine DB
  beweisbar korrekt. Also liefert der Web-`POST /auth/login` **zwingend auch
  `200`**.
- Live gemessen: Web-`POST /auth/login` = `200`, aber **keinerlei Cookie im
  Browser gespeichert**, und **keine** Cookie-Ablehnungs-Warnung in der Konsole.
  → Das `Set-Cookie` wird in der Kette Nginx → SvelteKit-Proxy → API
  **weggeschnitten** (nicht vom Browser abgelehnt).

  **Nachtrag (Root Cause im Web-Proxy):** PR #468 hatte Upstream-`Set-Cookie`
  auf `event.cookies` umgebogen und vom proxied `Response` entfernt. Der
  ADR-0011-Handle gibt aber eine custom `Response` zurück und ruft nie
  `resolve()` auf — SvelteKit ignoriert die Cookie-Jar dann bewusst
  ([sveltejs/kit#7611](https://github.com/sveltejs/kit/issues/7611)). Damit
  kam `Set-Cookie` bereits **im Web-Container** nicht beim Browser an; der
  Edge-Vertrag bleibt trotzdem erforderlich, war aber nicht die alleinige
  Ursache des Live-Symptoms. Fix: `Set-Cookie` wieder 1:1 auf der Response
  forwarden.

### Warum daraus „Passwort falsch" wurde

Der Web-Login ist zweistufig (`apps/web/src/lib/stores/auth.ts`):
`POST /auth/login` (Passwort) → `GET /auth/me` (validiert per HttpOnly-Cookie).
Schlägt Schritt 2 fehl, weil das Cookie nicht klebt, warf der Store bislang
`ApiError(401)`. Die Login-Seite mappt **jeden 401 → „E-Mail oder Passwort ist
falsch"**. Ein reines **Cookie-Zustellungsproblem tarnte sich als
Credential-Fehler** — genau deshalb war es nie nachhaltig lösbar: jede
Untersuchung jagte das Passwort, nicht das Cookie. Die APK ist nie betroffen,
weil sie In-Memory-Bearer-Token statt Cookies nutzt (ADR-0006).

### Die eigentliche strukturelle Ursache

Nicht das Cookie ist fragil, sondern der **Reverse-Proxy-Vertrag am Rand**.
Cookie-Auth verlangt: Same-Origin für `/api`, `Set-Cookie` muss durch **jeden**
Hop unverändert durch, `Secure`/`SameSite`/`X-Forwarded-Proto` müssen stimmen.
Jeder Self-Host-Edge (Traefik, Nginx, Synology-RP, Dockge, Tailscale …) ist eine
neue Chance, das zu verletzen.

Konkret verletzt sogar unsere **eigene** Referenz in
`docs/runbooks/hosted-nginx-edge.md` das Designziel von
[ADR-0011](0011-web-internal-reverse-proxy.md) („proxy **all** paths to
`correlcore-web`"): Sie enthält einen **separaten `location /api/v1/auth/`-Block**,
der seine Proxy-Parameter aus einem `include`-Snippet („or inline below") zieht,
während `location /` sie inline setzt. Weichen beide auseinander (fehlendes
`Host`/`X-Forwarded-Proto` oder ein generisches `proxy_hide_header Set-Cookie`
aus einem „Härtungs"-Snippet), werden **genau die Auth-Requests** anders
behandelt — Login-Cookie kaputt, der Rest der App sieht gesund aus.

## Entscheidung

Cookie-Auth **bleibt der sichere Default** (XSS-Resistenz auf Art.-9-Daten,
ADR-0006). Die Fragilität wird nicht durch Auth-Modell-Wechsel, sondern durch
Schrumpfung der Konfigurations-Angriffsfläche auf ~null behoben:

1. **Ein-Regel-Edge-Kontrakt.** Der externe Proxy darf ausschließlich:
   (a) TLS terminieren, (b) **alle** Pfade an `correlcore-web` weiterreichen,
   (c) `X-Forwarded-Proto: https` setzen, (d) **die Proxy-Header-Puffer
   vergrößern** (`proxy_buffer_size 32k; proxy_buffers 8 32k;`). **Keine**
   Sonderregel für `/api`, kein Direkt-Routing zur API, **kein**
   Umschreiben/Verstecken von `Set-Cookie`. Die `/api`-Weiterleitung und das
   saubere `Set-Cookie` besitzt der Web-Container (ADR-0011). Ein „dummer
   Passthrough" ist praktisch nicht falsch zu konfigurieren.

   *Warum (d):* Der SvelteKit-Container (adapter-node) sendet große
   Response-Header (`Link: rel=preload` für jeden JS/CSS-Chunk). Der
   Default-`proxy_buffer_size` (4k/8k) ist zu klein → der Edge liefert
   **502** mit `upstream sent too big header` im Error-Log — obwohl Ziel,
   Cookie und Config sonst korrekt sind. Topologie-unabhängig (raw nginx, NPM,
   Caddy, Traefik, Synology RP).

2. **Kanonische Referenz-Config im Repo.** `infra/nginx/correlcore.com.conf` —
   **eine einzige, in sich geschlossene Datei ohne `include`-Snippet** (auch auf
   einer separaten Edge-Maschine bzw. in einer Synology-Custom-Config
   deploybar). Die Proxy-Parameter werden **einmal auf `server{}`-Ebene**
   definiert; beide `location`-Blöcke **erben** sie, weil keiner ein eigenes
   `proxy_set_header` deklariert (nginx erbt `proxy_set_header` nur, wenn die
   Location selbst keins setzt). Damit gibt es nur **eine** Quelle der
   Wahrheit → Auth- und Rest-Location **können** nicht divergieren. Der
   `/api/v1/auth/`-Block behält nur sein Rate-Limit _zusätzlich_. (Ein
   `proxy_set_header` in einer Location würde dort **alle** geerbten Header
   verwerfen — genau das ist verboten.)

3. **Auth-Selbsttest beim Deploy.** `scripts/verify-auth-cookie.sh` fährt einen
   echten Login-Roundtrip und meldet, ob (a) Login = 200, (b) `Set-Cookie`
   ankommt, (c) `/auth/me` = 200. Fehlkonfiguration scheitert damit beim Setup,
   nicht Wochen später bei verwirrten Nutzern.

4. **Ehrlicher Client-Fehler.** Neuer `SessionPersistenceError`: Wenn Login = 200,
   aber `/auth/me` anonym bleibt, zeigt die UI eine Cookie-/HTTPS-Meldung statt
   „Passwort falsch". Jede Rest-Fehlkonfiguration benennt sich damit selbst.

5. **Bearer-Fallback für den Browser (akzeptierte Richtung, Umsetzung
   ausgelagert).** Für Topologien, in denen Same-Origin **prinzipiell** nicht
   geht (API auf anderer Subdomain, gar kein Reverse-Proxy), wird der bereits
   existierende Capacitor-Bearer-Pfad (`usesBearerAuth()`) als **opt-in
   „Cross-Origin/Advanced"-Modus** auch für den Browser freigeschaltet. Der
   Trade-off wird explizit benannt: **Bearer = robust gegen jede Topologie, aber
   schwächer gegen XSS** (Token im JS-erreichbaren Speicher). Cookie bleibt
   Default, Bearer ist der bewusste Ausweg — kein Neubau, sondern Freischaltung +
   Doku eines vorhandenen Pfads.

## Konsequenzen

- **Der akute correlcore.com-Fix** ist das Ausrollen von
  `infra/nginx/correlcore.com.conf` (Proxy-Params auf `server{}`-Ebene, von
  beiden Locations geerbt) und ein grüner `verify-auth-cookie.sh`-Lauf. (Für den
  Juli-2026-Vorfall lag der eigentliche Strip im Web-Proxy — Fix in #527, siehe
  Kontext-Nachtrag; die Edge-Config ist Defense-in-Depth und deploybare Referenz.)
- **Der Klasse-Bug ist per Design ausgeschlossen:** Auth- und Rest-Requests
  teilen zwingend dieselben Proxy-Parameter.
- **Cookie-Sicherheitsposture bleibt unverändert** (HttpOnly/Secure/SameSite).
- **Cross-Origin-Self-Host wird ein dokumentierter, bewusster Modus** statt einer
  stillen Fehlkonfiguration.
- **Doku-Schuld getilgt:** Runbook, Topologie-Doc und ADR-Index verweisen auf
  einen einzigen, getesteten Config-Stand statt auf handgeschriebene Beispiele.

## Optionen (bewertet)

### A — Cookies behalten + Edge härten _(gewählt)_

Ein-Regel-Passthrough, Proxy-Params auf `server{}`-Ebene (von allen Locations
geerbt), Selbsttest, ehrlicher Fehler.

- **Pro:** Behält die XSS-Resistenz der HttpOnly-Cookies; minimaler Change;
  richtet sich exakt nach ADR-0011; macht den Klasse-Bug strukturell unmöglich.
- **Con:** Same-Origin bleibt Voraussetzung (durch Bearer-Fallback abgefedert).

### B — Bearer-Token auch im Browser als Default _(verworfen)_

Access-Token im Speicher, `Authorization: Bearer`, keine Cookies → keine
`Set-Cookie`/`SameSite`/Same-Origin-Fragilität, funktioniert über jede Topologie.

- **Con:** **XSS-Regression.** Token wird JS-erreichbar; Refresh-Token-Ablage im
  Web-Storage widerspricht ADR-0006 („keine Tokens im Web-Storage") und ist bei
  Art.-9-Gesundheitsdaten nicht akzeptabel als Default. Bleibt daher nur
  **opt-in Fallback** (Punkt 5), nicht Default.

### C — API in eigener Subdomain mit eigenem Cert _(verworfen als Default)_

Sauber für ein künftiges SaaS, aber für Single-Tenant-Self-Host überdimensioniert
und löst den Same-Origin-Cookie-Vorteil nicht ein. Für die seltenen echten
Cross-Origin-Fälle deckt der Bearer-Fallback (Punkt 5) das Bedürfnis ab.

## Verweise

- [ADR-0006 — Cookie-Auth im Web mit Capacitor-Bearer-Migration](0006-cookie-auth-mit-capacitor-migration.md)
- [ADR-0011 — Interner Reverse-Proxy im Web-Container](0011-web-internal-reverse-proxy.md)
- [Runbook — Hosted Nginx edge](../runbooks/hosted-nginx-edge.md)
- [Runbook — Hosted topology options](../runbooks/hosted-topology-options.md)
- `infra/nginx/correlcore.com.conf` (self-contained; server-level proxy params), `infra/nginx/README.md`
- `scripts/verify-auth-cookie.sh`
- Client: `SessionPersistenceError` in `apps/web/src/lib/api/client.ts`,
  Fehler-Mapping in `apps/web/src/lib/utils/error.ts`

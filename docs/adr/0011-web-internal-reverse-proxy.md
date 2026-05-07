# ADR-0011: Interner Reverse-Proxy im Web-Container (Auflösung des Vite-Build-Time-Kopplungsproblems)

**Datum:** 2026-05-07
**Status:** Vorgeschlagen
**Geplante Umsetzung:** M2 (Insights & Polishing)

---

## Kontext

Beim ersten erfolgreichen Hochkommen des kompletten Stacks auf der Synology
(Dockhand, Tailscale-internes Setup, **kein Reverse-Proxy davor**) trat ein
neuartiger Bug auf: API-Healthchecks 200, Migrationen sauber, Web-Frontend
lädt — aber **jede** Aktion im Frontend schlug mit 404 fehl. Browser-DevTools
zeigte den Smoking-Gun:

```
POST http://100.120.157.82:3010/api/v1/auth/register 404 (Not Found)
```

Der Browser sendete API-Calls an den **Web-Port** (3010, Static-Files-Server)
statt an den **API-Port** (8210). Im API-Container-Log tauchten die POSTs
gar nicht erst auf.

### Ursache: `VITE_API_BASE_URL` ist Build-Time-konstant

Vite ersetzt `import.meta.env.VITE_API_BASE_URL` zur **Build-Zeit** als
String-Literal im JS-Bundle. Eine ENV-Änderung am laufenden
`moodsync-web`-Container hat dadurch _keinen_ Effekt — der Wert ist im
Bundle einkompiliert.

Der Default `VITE_API_BASE_URL=/api/v1` (relativer Pfad) funktioniert nur,
wenn ein Reverse-Proxy `/api/*` an den API-Container weiterleitet. Im
proxylosen Setup serviert der Web-Container unter `/api/v1` schlicht
nichts → 404.

### Sofort-Fix (PR #92, bereits gemergt)

Der GitHub-Actions-Workflow `release-images.yml` hat einen
`workflow_dispatch`-Input `vite_api_base_url` bekommen, mit dem das
Web-Image manuell mit absoluter URL neu gebaut werden kann:

```bash
gh workflow run release-images.yml -R Sturmi77/moodsync --ref main \
  -f vite_api_base_url=http://100.120.157.82:8210/api/v1
```

Das löst das akute Problem (Registrierung funktioniert wieder), bringt aber
zwei strukturelle Schwächen mit:

1. **Bundle ist an die im Input angegebene URL gekoppelt.** Wechselt die
   Tailscale-IP (z. B. weil das Tailnet umkonfiguriert wird) oder der
   Host-Port (z. B. weil ein anderer Dienst kollidiert), muss das Image
   neu gebaut und ausgerollt werden.
2. **API-Port muss auf dem Host gemappt sein.** Der Browser sendet direkt
   an `http://<host>:8210/api/v1/...` — der API-Port ist also extern
   exponiert (im Tailnet). Im proxybasierten Production-Setup wäre der
   API-Port nicht direkt erreichbar.

Das ist akzeptabel als Hotfix, aber keine architektonische Endlösung.

## Entscheidung

**Der `moodsync-web`-Container bekommt einen integrierten Reverse-Proxy,
der `/api/*`-Requests intern an `http://api:8000/*` weiterleitet
(Inter-Container-Kommunikation über das Compose-Netzwerk).** Der
Build-Arg-Default `VITE_API_BASE_URL=/api/v1` bleibt in allen Topologien
korrekt, ohne Rebuild bei Topologie-Änderungen.

### Konsequenzen

- **Ein Image für alle Topologien.** Tailnet-Setup, lokales Docker-Compose,
  zukünftiges Production-Setup mit Traefik vor dem Stack — jeweils
  identisches `:latest`-Image, keine Topologie-spezifischen Builds mehr.
- **API-Port muss nicht mehr auf dem Host gemappt sein** (außer für
  Debugging/CI). Sicherheitsplus: Eine direkte Tailnet-Erreichbarkeit der
  API ohne Auth-Layer entfällt.
- **Single Entry Point** für den User: `http://<host>:<WEB_HOST_PORT>` ist
  alles, was er kennen muss. CORS-Konfiguration vereinfacht sich
  drastisch — `same-origin` gilt jetzt, weil API und Web denselben
  Browser-Origin teilen. Cookie-Auth (ADR-0006) profitiert direkt: keine
  Cross-Origin-Cookies, kein `SameSite=None`-Workaround nötig.
- **`workflow_dispatch`-Input bleibt erhalten** als Escape-Hatch für
  Setups, in denen man den Proxy bewusst umgehen will (z. B. lokale
  Web-Entwicklung gegen einen entfernten API-Host).

## Optionen (bewertet)

### A — sidecar nginx im Web-Pod _(verworfen)_

Zusätzlicher nginx-Container vor dem Web-Container, mit
`location /api/ { proxy_pass http://api:8000/; }`. Klassisch, gut
verstanden — aber:

- Verdoppelt die Container-Anzahl pro Stack (von 5 auf 6 in
  user-test/Dockhand)
- Doppelte Healthcheck-Konfiguration (nginx + Node)
- Zusätzlicher YAML-Anchor / Service-Block in allen drei Compose-Files

Für ein Single-Tenant-Homelab-Setup zu schwergewichtig.

### B — SvelteKit Node-Adapter mit `hooks.server.ts` _(gewählt)_

SvelteKit läuft bereits auf dem Node-Adapter (`@sveltejs/adapter-node`,
ADR-0001). Der bestehende Node-Server bekommt in `apps/web/src/hooks.server.ts`
einen Handle-Hook, der Requests an `^/api/.*` per `fetch` an die
interne API-URL (`http://api:8000`) weiterleitet und Response/Status/
Headers durchreicht. Single-Container, kein Sidecar, zero
Compose-Änderungen.

- **Pro:** Minimale Surface-Area (eine Datei, ~40 Zeilen TS), Compose
  bleibt unverändert, idiomatisch SvelteKit
- **Pro:** Cookie-Forwarding ist in einem Node-Handle trivial (Cookies
  fließen ohnehin durch `fetch`), und das saubere `Set-Cookie` vom API
  landet 1:1 im Browser-Response
- **Pro:** Streaming-Responses (z. B. SSE für künftige Notification-
  Channels) gehen durch `fetch` mit `body: ReadableStream` ohne
  Sonderbehandlung
- **Con:** Performance ist nicht ganz so hoch wie bei nginx (Node-Loop
  vs. nativer Proxy), für unsere Last (Single-User-Homelab) irrelevant
- **Con:** Web-Container hängt jetzt zur Laufzeit am API-Service —
  Healthcheck-Tiefe muss erweitert werden (`/health/ready` im Web
  prüft jetzt auch `api:8000/health/live`-Reachability), sonst zeigt
  Web bei API-Ausfall einen weniger klaren Fehlerzustand

### C — Caddy als Init-Stage im Web-Image _(verworfen)_

Caddy als binär in das Web-Image einbacken und vor dem Node-Server
starten (mit s6-overlay oder Bash-Supervision). Eleganter Ein-Container-
Ansatz, aber:

- Bringt Multi-Process-Container-Komplexität (PID 1, Signal-Handling,
  Restart-Verhalten bei Teil-Crashes)
- Caddy-Config wird zum Konfig-Surface, das mit den anderen Pfaden
  konkurriert
- Build wird signifikant größer (~30 MB statisches Caddy)

Für eine reine `/api/*`-Weiterleitung overkill.

## Umsetzungsplan (M2)

1. **`apps/web/src/hooks.server.ts`** anlegen mit Handle-Hook:
   - Match-Pattern `event.url.pathname.startsWith('/api/')`
   - Forward an `process.env.INTERNAL_API_URL` (Default `http://api:8000`)
   - Body, Headers (außer Hop-by-Hop), Method, Cookies durchreichen
   - Status, Headers, Body 1:1 zurück an den Client
2. **`apps/web/Dockerfile`**: `ENV INTERNAL_API_URL=http://api:8000` als
   Default setzen — bleibt überschreibbar pro Compose-Variante
3. **Compose-Files** (`infra/dockhand/compose.yaml`,
   `infra/dockge/compose.yaml`, `infra/docker/docker-compose.user-test.yml`):
   - `moodsync-web` `depends_on: api: { condition: service_healthy }`
     hinzufügen
   - `API_HOST_PORT`-Mapping auf `expose:`-Block umstellen (Port nur
     intern, nicht mehr aufs Host gebunden) — als _opt-out_ via
     `EXPOSE_API_HOST_PORT=true` ENV-Toggle für Debugging-Setups
4. **`workflow_dispatch`-Input `vite_api_base_url`** bleibt im Workflow,
   Default-Verhalten ändert sich aber: `:latest` ist jetzt default
   topologie-agnostisch (mit `/api/v1`)
5. **Healthcheck-Erweiterung:** Web-`/health/ready` testet zusätzlich
   `INTERNAL_API_URL/health/live`
6. **Tests:** Playwright-Smoke-Test, der `/api/v1/health` und
   `/api/v1/auth/register` über den Proxy aufruft und auf 200/201 prüft
7. **RUNBOOK §7** und §6 aktualisieren: API-Port-Default auf `expose`
   (intern), Quick-Reference-Tabellen-Eintrag zum 404-Symptom obsolet
   markieren mit Verweis auf diesen ADR

## Migrationspfad

- **Sofort (jetzt):** ADR-0011 in Status `Vorgeschlagen`, kein Code-Change
- **M1-Exit:** PR #92 (workflow_dispatch-Hotfix) bleibt aktiv, dokumentiert
- **M2-Start:** Implementierungs-PR mit obigen sieben Punkten, ADR auf
  `Accepted` heben
- **M2-Exit:** `:latest` ist topologie-agnostisch; user-test-Setup nutzt
  ohne Rebuild den Default; alter dispatch-gebauter Build bleibt
  abrufbar als `:proxyless-snapshot` für Notfall-Rollback

## Verworfene Alternativen

- **Runtime-Config-Injection (`window.__APP_CONFIG__`)**: Würde Build-Time-
  Kopplung lösen, ohne Proxy zu brauchen. Macht aber CORS-Konfiguration und
  API-Port-Exposure permanent — beides Schwächen, die die Proxy-Lösung mit
  abräumt. Außerdem ist `entrypoint.sh`-Substitution in `index.html` ein
  Pattern, das mit SvelteKit-SSR-Hydration nicht trivial spielt
  (Hydration-Mismatch-Risiko)
- **API in eigener Subdomain mit eigenem Cert**: Architektonisch sauber für
  Production, aber für Tailnet-Internal-Setup massiv überdimensioniert
  (DNS-Setup, Cert-Management, Tailscale-MagicDNS-Caveats) und löst die
  Same-Origin-Cookie-Vorteile nicht ein

## Verweise

- [PR #92 — `VITE_API_BASE_URL` workflow_dispatch-Input](https://github.com/Sturmi77/moodsync/pull/92)
- [RUNBOOK §7 — `VITE_API_BASE_URL` Build-Time](../RUNBOOK_DEPLOYMENT.md)
- [ADR-0001 — SvelteKit als Web-Framework](0001-sveltekit-vs-nextjs.md)
- [ADR-0006 — Cookie-Auth mit Capacitor-Migration](0006-cookie-auth-mit-capacitor-migration.md) (profitiert direkt durch Same-Origin)
- [ADR-0007 — Healthchecks und Logging](0007-healthchecks-and-logging.md) (`/health/ready`-Erweiterung)

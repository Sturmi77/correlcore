# Runbook: Erstes User-Test-Deployment

**Bezug:** PRs #76, #77, #78, #79, #82, #83, #84, #85, [ADR-0010](adr/0010-build-toolchain-pinning.md)
**Status:** M1 — Tailscale-internes Selfhost-Deployment, getestet auf Synology DSM mit Dockhand
**Letzte Aktualisierung:** 2026-05-07

Dieses Runbook fasst die Erkenntnisse aus dem ersten echten User-Test-Deployment zusammen. Es deckt drei Themenfelder ab, die jeweils einen produktionsblockierenden Bug verursacht haben und in dieser Form weder in den Compose-/Dockerfile-Comments noch in `infra/dockhand/README.md` ausreichend dokumentiert waren.

---

## 1. Backend-Dockerfile: `app/` muss vor `uv pip install -e .` im Build-Context liegen

### Symptom

Beim ersten Stack-Start (Dockhand, Dockge oder docker-compose user-test) bricht der Init-Container `moodsync-migrate` mit folgendem Fehler ab:

```text
Traceback (most recent call last):
  File "/app/migrations/env.py", line 11, in <module>
    import app.models
ModuleNotFoundError: No module named 'app'
```

Der API-Container (`moodsync-api`) bleibt deshalb auf dem `service_completed_successfully`-Gate hängen und startet nie.

### Ursache

Der `backend/Dockerfile`-Builder-Stage führte ursprünglich folgende Sequenz aus:

```dockerfile
COPY pyproject.toml uv.lock README.md ./
RUN uv venv .venv && uv pip install -e .   # ← bricht semantisch
COPY app/ app/                              # ← zu spät
```

`uv pip install -e .` ist ein _editable install_ via Hatchling. Hatchling liest aus `pyproject.toml`:

```toml
[tool.hatch.build.targets.wheel]
packages = ["app"]
```

und sucht zur Build-Zeit nach dem `app/`-Ordner. Da der zu diesem Zeitpunkt noch nicht im Build-Context lag, registrierte der Install **nur die Dependencies** in `.venv`, aber **keinen `.pth`-Eintrag für das `app`-Package selbst**.

Der Bug schlug nicht beim API-Container auf, weil uvicorn beim Start in `/app` (Working-Dir) lebt und Python das Package implizit über den CWD-Lookup fand. Alembic dagegen wechselt sein Working-Dir nach `migrations/` — und damit fiel `app` aus dem `sys.path`.

### Fix

Den `app/`-Ordner vor dem editable Install in den Build-Context kopieren:

```dockerfile
COPY pyproject.toml uv.lock README.md ./
COPY app/ app/                              # ← VOR dem Install
RUN uv venv .venv && uv pip install -e .
```

(siehe PR #84, Commit `5ae9cf8`)

### Lehre

**Editable installs verlangen, dass das Package zur Build-Zeit existiert.** Die Reihenfolge der `COPY`-Statements ist nicht optimal aus Layer-Cache-Sicht (jede Source-Änderung invalidiert auch den Dependency-Layer), aber der semantische Zwang geht vor. Ein `uv pip install --no-deps -e .` als zweiter Schritt nach dem Dependency-Install könnte das Caching wieder herstellen — vorerst ist die einfachere Variante akzeptabel.

---

## 2. Synology + Tailscale: Userspace-Networking blockiert IP-Bindings

### Symptom

Container starten nicht, mit Fehler:

```text
Error response from daemon: failed to bind host port for 0.0.0.0:8025:
100.120.157.82:8025: bind: cannot assign requested address
```

`docker ps` zeigt Mailpit, GlitchTip oder andere Services, die per `${TAILSCALE_IP}:PORT` gebunden werden, im `Created`- oder `Restarting`-Zustand.

### Ursache

Auf einer Synology DSM läuft Tailscale standardmäßig im **Userspace-Networking-Modus** (siehe `Tailscale-Paket → Optionen → Networking-Modus`). Das bedeutet:

- Der Tailscale-Daemon hat seinen eigenen User-Mode-TCP/IP-Stack.
- Die Tailscale-IP (z. B. `100.120.157.82`) erscheint **nicht** auf einem Kernel-Interface.
- `ip -4 addr show` listet sie nicht; nur `tailscale status` kennt sie.
- Linux-Bind-Operationen können sie deshalb nicht binden — der Kernel weiß nichts von der IP.

Tailscale leitet eingehenden Traffic für seine IP intern an `localhost`-Listener weiter, **wenn** ein Service auf `0.0.0.0` oder `127.0.0.1` lauscht. Direktes Binden auf die Tailscale-IP funktioniert nur im _Kernel-Networking-Modus_, der auf DSM nicht der Default ist.

### Fix

In `.env` der Compose-Stacks (Dockhand / Dockge / user-test):

```env
# Statt:
# TAILSCALE_IP=100.120.157.82

# Auf Synology mit Userspace-Mode:
TAILSCALE_IP=0.0.0.0
```

Das macht die Container auf allen Interfaces lauschen — Tailscale leitet weiter, das LAN (z. B. 192.168.178.0/24) erreicht den Stack ebenfalls. Der Schutz vor WAN-Zugriffen muss in dieser Konfiguration durch den Router/die FritzBox erfolgen, nicht durch das IP-Bind. **In LAN-Setups mit aktiver Firewall-Regel (FritzBox blockt Inbound-WAN) ist das in der Praxis äquivalent zum Tailscale-only-Bind.**

Wer kernel-natives Tailscale-Bind will, muss am Synology-Host das `tailscale up --tun=tailscale0` ausführen oder das Paket auf Kernel-Mode umkonfigurieren (DSM-Verfügbarkeit modellabhängig).

### Lehre

**`TAILSCALE_IP` ist ein Konfigurationswert mit Plattform-Abhängigkeit, kein fester Wert.** Die Default-Einstellung in den Compose-Variants (`infra/dockhand/.env.example`, `infra/dockge/.env.example`, `infra/docker/.env.user-test.example`) sollte in einem nachgelagerten Update auf `0.0.0.0` mit prominentem Hinweis-Kommentar gehoben werden.

---

## 3. pnpm-Build-Scripts auf frischen Branches: `ERR_PNPM_IGNORED_BUILDS`

### Symptom

Auf einem frisch erzeugten Feature- oder Fix-Branch bricht `Build (vite)` (und alle drei weiteren Web-CI-Jobs) im Step `Install dependencies` ab:

```text
[ERR_PNPM_IGNORED_BUILDS] Ignored build scripts: es5-ext@0.10.64,
                          esbuild@0.19.12, esbuild@0.21.5

Run "pnpm approve-builds" to pick which dependencies should be allowed
to run scripts.
```

`main` läuft dagegen grün. Die einzige Differenz: dort gibt es einen GitHub-Actions-Cache-Hit für `node_modules`, auf dem neuen Branch nicht.

### Ursache

Doppelt:

1. **pnpm 10+ verlangt explizite Allowlist für Package-Build-Scripts.** Ohne die Allowlist bricht der Install in non-interaktiven Umgebungen ab. `esbuild` braucht das Build-Script, weil es ein Native-Binary für die Plattform nachlädt; `es5-ext` registriert Polyfill-Hooks transitiv über die ESLint-Toolchain.
2. **Die pnpm-Version war nicht gepinnt.** `pnpm/action-setup@v4` mit `version: 'latest'` zog je nach Tag pnpm 10.x oder pnpm 11.x. Beide verlangen die Allowlist, lesen sie aber aus _unterschiedlichen Schlüsseln_ in `pnpm-workspace.yaml` (`onlyBuiltDependencies` vs. `allowBuilds` — siehe ADR-0010).

### Fix

**Permanent (siehe ADR-0010):**

- pnpm-Version pinnen via `packageManager: "pnpm@11.0.8"` in der Root-`package.json` und `version: '11.0.8'` in allen vier `pnpm/action-setup`-Steps in `.github/workflows/ci-web.yml`.
- Build-Script-Allowlist in `pnpm-workspace.yaml` als reine v11-Syntax (`allowBuilds`-Map) führen:
  ```yaml
  allowBuilds:
    esbuild: true
    es5-ext: true
  ```
- `engines.pnpm` auf `>=11.0.0` heben (lokale Setups ohne Corepack).

**Akut für einen blockierten PR:** rebase auf `main` nach Merge des Pinning-PRs.

### Lehre

**Toolchain-Versionen pinnen.** "Latest" in CI-Pipelines ist eine schleichende Drift-Falle: ein und derselbe Workflow-Code wird über die Zeit nicht-deterministisch reproduzierbar, je nachdem welche Version der Tool-Runner gerade als `latest` definiert. Der Cache-Effekt verschleiert das, bis ein Branch ohne Cache-Hit auf den Stand der Welt trifft.

---

## 4. Pydantic-Settings: CSV-ENV-Listen brauchen `NoDecode`

### Symptom

Beim ersten Redeploy mit gepinnten Image-Tags startet der `moodsync-migrate`-Container nicht und stirbt mit:

```
pydantic_settings.exceptions.SettingsError: error parsing value
  for field "CORS_ORIGINS" from source "EnvSettingsSource"
json.decoder.JSONDecodeError: Expecting value: line 1 column 1 (char 0)
```

Die betroffene `.env`-Zeile sieht harmlos aus: `CORS_ORIGINS=http://a.example,http://b.example`.

### Ursache

pydantic-settings v2 versucht für komplexe Felder (`list[str]`, `dict[...]`) den ENV-Wert **zuerst** als JSON zu dekodieren, _bevor_ irgendein `field_validator(mode="before")` aufgerufen wird. Ein bestehender Validator zum CSV-Splitten kommt damit nie zum Zug — der JSON-Parse scheitert vorher und macht die ganze `Settings()`-Instantiierung zu einem harten Crash.

### Fix

`Annotated[list[str], NoDecode]` aus `pydantic_settings` auf das Feld:

```python
from typing import Annotated
from pydantic_settings import NoDecode

CORS_ORIGINS: Annotated[list[str], NoDecode] = [...]
```

Damit überspringt pydantic-settings den JSON-Pre-Parse, der existierende `mode="before"`-Validator splittet wie dokumentiert auf Komma. Gleicher Pattern für jedes weitere `list[...]`-Settings-Feld, das über ENV gesetzt werden kann.

### Lehre

**ENV-Format und Settings-Typen müssen konsistent sein.** Wenn die `.env.example` CSV dokumentiert, muss der Settings-Code auch CSV akzeptieren — nicht nur "validatorisch im Sinne von", sondern bevor der erste implizite JSON-Decode einspringt. Tests, die `Settings()` direkt instantiieren mit `monkeypatch.setenv`, fangen das im CI ab; die Bug-Klasse fällt sonst erst im echten Deployment auf, weil die Test-Suite ohne ENV-Override mit Defaults läuft.

---

## 5. Alembic + ENUM in `op.bulk_insert`

### Symptom

`moodsync-migrate` läuft die ersten Migrationen sauber, scheitert dann in der Seed-Phase einer Migration mit:

```
asyncpg.exceptions.DatatypeMismatchError: column "category" is of type tag_category
  but expression is of type character varying
```

Die Tabelle und der ENUM-Typ wurden in derselben Migration korrekt erzeugt; erst der `op.bulk_insert(...)`-Aufruf danach kippt um. Da Alembic Transactional DDL nutzt, wird der gesamte Migrationsschritt zurückgerollt — die DB bleibt auf der vorigen Revision sauber stehen.

### Ursache

Für `op.bulk_insert` definiert man parallel zum `op.create_table(...)` einen leichtgewichtigen `sa.table(...)`-Stub mit `sa.column(...)`-Einträgen. SQLAlchemy nutzt **diesen Stub** (nicht das `Table`-Objekt aus `create_table`) zur Generierung des INSERT-Statements und bindet Parameter mit dem dort deklarierten Typ. Eine als `sa.String` deklarierte Spalte erzeugt `$N::VARCHAR`; PostgreSQL verweigert den impliziten Cast von `character varying` auf einen Custom-ENUM-Typ. Bei direktem `INSERT ... VALUES ('sport', ...)` mit String-Literal hätte Postgres den Cast erlaubt — mit gebundenem Parameter und explizit geforderter Typ-Annotation greift das nicht.

### Fix

Im Stub die ENUM-Typdefinition wiederholen, mit `create_type=False`, weil der Typ im selben Schritt schon erzeugt wurde:

```python
from sqlalchemy.dialects import postgresql

_TAG_CATEGORY_VALUES = ("emotion", "context", "activity", ...)

tags_table = sa.table(
    "tags",
    sa.column("slug", sa.String),
    sa.column(
        "category",
        postgresql.ENUM(*_TAG_CATEGORY_VALUES, name="tag_category", create_type=False),
    ),
    # ...
)
op.bulk_insert(tags_table, [...])
```

SQLAlchemy generiert daraufhin `$N::tag_category`, Postgres akzeptiert. Gleicher Pattern für jeden weiteren `bulk_insert`-Stub mit ENUM-Spalten.

### Lehre

**Der `sa.table`-Stub ist eine separate Typ-Deklaration — keine Abkürzung für "siehe `create_table` oben".** SQL aus Alembic kompiliert oft erfolgreich, wird aber zur Ausführungszeit von Postgres mit `DatatypeMismatchError`, FK-Verletzungen oder fehlenden Extensions abgelehnt. Unit-Tests mit DB-Mocks fangen diese Bug-Klasse prinzipbedingt nicht. Die einzige verlässliche Absicherung ist `alembic upgrade head` gegen einen echten Postgres in CI — seit PR #89 als Job `migrations-smoke` im Backend-Workflow verdrahtet, mit Bonus-Round-Trip `downgrade base → upgrade head` zur Idempotenz-Prüfung.

---

## 6. Host-Port-Konflikte mit anderen Selfhosted-Diensten

### Symptom

`moodsync-api` (oder `moodsync-web`) startet nicht und produziert beim Container-Create:

```
Error response from daemon: driver failed programming external connectivity
  on endpoint moodsync-api: Error starting userland proxy:
  listen tcp4 0.0.0.0:8000: bind: address already in use
```

### Ursache

Auf der Synology / im Homelab läuft bereits ein anderer Dienst auf dem Host-Port, den der Compose-Stack mappen will. Typische Kollisionen:

| Port | Belegt durch                                                         |
| ---- | -------------------------------------------------------------------- |
| 3000 | Grafana, **Gotenberg (Paperless-ngx-Sidecar für PDF-Konvertierung)** |
| 5000 | DSM                                                                  |
| 7878 | Radarr                                                               |
| 8000 | Paperless-ngx                                                        |
| 8080 | diverse Web-UIs (GlitchTip, ...)                                     |
| 8096 | Jellyfin                                                             |
| 8123 | Home Assistant                                                       |
| 8989 | Sonarr                                                               |
| 9000 | Portainer                                                            |

> **Synology-Hinweis:** Auf DSM gibt es kein `ss`/`lsof`. Der zuverlässige
> Befehl ist `sudo netstat -tlnp | grep ':3000 '` (Leerzeichen am Ende des
> Patterns wichtig, sonst matched es 3000-3999). Synology-Containerdienste
> binden ihre Ports oft auf `:::PORT` (IPv6-Listen) statt `0.0.0.0:PORT` —
> ein `docker ps`-Listing erkennt sie deshalb manchmal nicht als
> Konflikt-Quelle, der Bind-Versuch eines neuen Containers schlägt aber
> trotzdem fehl (z.B. Gotenberg, das in einem anderen Compose-Stack läuft).

### Fix

Alle drei Compose-Varianten (`infra/dockhand/`, `infra/dockge/`, `infra/docker/docker-compose.user-test.yml`) seit PR #90 mit konfigurierbaren Host-Ports:

```bash
# In der .env des Stacks:
API_HOST_PORT=8210      # Default seit PR #90; vorher hardcoded 8000
WEB_HOST_PORT=3010      # Default war 3000, bei Paperless+Gotenberg auf 3010 ausweichen
```

Container-interne Ports bleiben fix bei `8000` (API) und `3000` (Web). 8210 ist absichtlich gewählt: kollidiert mit keinem der oben gelisteten Standard-Selfhosted-Tools.

**WICHTIG:** Wenn `WEB_HOST_PORT` geändert wird, müssen die Einträge in `CORS_ORIGINS` ebenfalls angepasst werden — sonst blockiert der Browser API-Calls vom Frontend mit CORS-Fehler. Beispiel:

```bash
WEB_HOST_PORT=3010
CORS_ORIGINS=http://moodsync.tail-scale.ts.net:3010,http://100.101.102.103:3010
```

### Lehre

**Host-Ports in Compose-Stacks sind kein Implementierungsdetail — sie sind Teil der Deployment-Schnittstelle und müssen via ENV konfigurierbar sein.** Hardcoded `8000:8000` funktioniert auf einem dedizierten Server, kollidiert aber im typischen Homelab-Mehrfach-Stack. Der Container-interne Port bleibt fix (App-Konfiguration, Health-Checks, Inter-Container-Kommunikation), nur der Host-Port-Mapper-Teil bekommt ein Default mit ENV-Override. Eine kurze Default-Liste der "üblichen Belegungen" im Runbook spart später Debugging-Zeit.

---

## 7. Frontend 404 bei `/api/v1/...`: dauerhaft gelöst durch ADR-0011

### Symptom (historisch)

Stack ist sauber hochgekommen, API-Healthchecks zeigen 200, aber jede Aktion im Frontend (Login, Registrierung, Verify-Mail) scheitert. Browser-DevTools zeigt:

```
POST http://<host>:<WEB_HOST_PORT>/api/v1/auth/register 404 (Not Found)
```

Im API-Container-Log taucht der POST gar nicht auf — das Frontend sendet an sich selbst, nicht an die API.

### Ursache (historisch)

`VITE_API_BASE_URL` ist eine **Build-Time-Variable**: Vite ersetzt `import.meta.env.VITE_API_BASE_URL` zur Build-Zeit als String-Konstante im JS-Bundle. Eine ENV-Änderung am laufenden `moodsync-web`-Container hatte dadurch keinen Effekt. Mit Default `/api/v1` (relativ) funktionierte das nur, wenn ein Reverse-Proxy `/api/*` an den API-Container weiterleitete.

Im user-test/Dockhand-Setup mit direktem Host-Port-Mapping (Web=3010, API=8210) ohne Proxy sendete der Browser an den Web-Port, der nur Static-Files serviert → 404. Schlimmer: der `release-images.yml`-Workflow baute auf jedem Push auf `main` automatisch ein neues `:latest` mit Default `/api/v1`, sodass nach jedem Merge der manuelle `workflow_dispatch`-Override (siehe ältere Versionen dieses Runbooks) wieder überschrieben wurde — ein wiederkehrender Login-Bruch.

### Lösung (dauerhaft, seit ADR-0011)

Der `moodsync-web`-Container enthält einen integrierten Reverse-Proxy in `apps/web/src/hooks.server.ts`. Jeder Request mit Pfad `/api/*` wird zur Laufzeit an `INTERNAL_API_URL` (Default `http://api:8000`) weitergeleitet, inklusive Method, Headers, Body, Query-String und vollständiger `Set-Cookie`-Behandlung (mehrere Cookies bleiben separate Header-Lines, Hop-by-Hop-Header werden entfernt).

Konsequenzen:

- `VITE_API_BASE_URL` ist fest auf `/api/v1` gepinnt; der `workflow_dispatch`-Input ist aus `release-images.yml` entfernt. Ein Image funktioniert in jeder Topologie.
- Pro Topologie wird nur die **Runtime-ENV** `INTERNAL_API_URL` am Web-Container gesetzt — kein Rebuild bei IP-/Port-Wechsel.
- Im docker-compose-Setup mit Service-Namen (`api`) ist nichts zu konfigurieren; der Default trifft.
- API-Port muss am Host nicht mehr gemappt sein. `expose: ["8000"]` reicht; der API-Container ist nur intern aus dem `web`-Container erreichbar (Sicherheitsplus).

### Verifikation nach Deployment

```bash
# Web-Container muss die API-Route durchreichen
curl -v http://<host>:<WEB_HOST_PORT>/api/v1/health/live
# erwartete Antwort: HTTP 200, JSON {"status":"ok"} (oder 502 mit JSON-Body, falls API down)
```

Wenn `502 {"detail":"Upstream API unreachable"}` zurückkommt: API-Container prüfen, `INTERNAL_API_URL` im Web-Container kontrollieren (siehe `docker compose exec web env | grep INTERNAL`).

### Compose-Beispiel (Dockhand / Selfhost ohne externen Proxy)

```yaml
services:
  api:
    image: ghcr.io/sturmi77/moodsync-api:latest
    expose:
      - '8000' # nur intern; KEIN ports: mehr nötig
    # ...

  web:
    image: ghcr.io/sturmi77/moodsync-web:latest
    environment:
      INTERNAL_API_URL: http://api:8000 # default, kann auch entfallen
    ports:
      - '3010:3000' # nur Web nach außen exponiert
```

### Verwandte ADRs / Issues

- [ADR-0011](../adr/0011-web-internal-reverse-proxy.md) — Architektur-Entscheidung und gewählte Variante (B: SvelteKit-Handle-Hook)
- [ADR-0006](../adr/0006-cookie-auth-strategie.md) — Cookie-basierte Auth, durch Same-Origin-Proxy vereinfacht

### Lehre

**Vite-`VITE_*`-Variablen sind Build-Time-Konstanten, keine Runtime-Konfiguration.** Für Bundles, die in mehreren Topologien (verschiedene Hosts/Ports, mit/ohne Proxy) deployed werden, ist ein interner Reverse-Proxy oder Runtime-Config-Injection Pflicht. Build-time-gekoppelte API-Basis-URLs sind eine bekannte Sollbruchstelle bei SPA-Deployments und reproduzieren sich bei jedem automatischen Image-Build, wenn man sich auf manuelle `workflow_dispatch`-Overrides verlässt.

---

## 8. Unverified-Account-Recovery: Auto-Cleanup statt manuellem SQL

### Symptom

Ein User registriert sich, klickt den Verify-Link aber nie, etwa weil SMTP
falsch konfiguriert war oder die Mail im Spam landet. Die E-Mail-Adresse ist
danach durch den unverified Account blockiert.

### Kanonischer Pfad seit M2

Der Worker `python -m app.workers.analytics` fuehrt taeglich um 03:00 UTC
`cleanup_unverified_accounts` aus. Alle Accounts mit `is_verified=false` und
`created_at < now - UNVERIFIED_CLEANUP_DAYS` werden per `DELETE FROM users`
entfernt. Default ist `UNVERIFIED_CLEANUP_DAYS=7`.

Die bestehende Cascade-Kette entfernt dabei auch Entries, Tags/Symptome des
Users, Verification-Tokens und `user_encryption_keys`. Logs enthalten nur den
aggregierten Count und `user_ids`, nie E-Mail-Adressen.

### Notfall-Override

Manuelles SQL bleibt nur ein Admin-Notfallpfad, wenn der Worker noch nicht
laeuft oder eine Adresse sofort freigegeben werden muss:

```sql
DELETE FROM users WHERE LOWER(email) = LOWER('foo@example.com');
```

Vorher die Cascade-Reichweite bewusst pruefen: der Delete ist hart und nicht
reversibel, weil auch die verschluesselten DEKs des Users entfernt werden.

---

## Quick-Reference: Erste-Hilfe-Tabelle

| Symptom                                                                                                                   | Erste Hypothese                                                             | Sofort-Check                                                                                                                                                                                                                                         |
| ------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `moodsync-migrate` Exit 1, `ModuleNotFoundError: No module named 'app'`                                                   | Veraltetes Backend-Image im GHCR                                            | Backend-Image neu pullen (`docker pull ghcr.io/sturmi77/moodsync-api:latest`); `docker inspect` muss `Created ≥ 2026-05-07` zeigen, sonst Pull wiederholen                                                                                           |
| Container bleibt in `Restarting`, Log: `bind: cannot assign requested address` für Tailscale-IP                           | Synology+Tailscale Userspace-Mode                                           | `TAILSCALE_IP=0.0.0.0` in `.env`, Stack neu starten                                                                                                                                                                                                  |
| Web-CI-Job bricht im Install-Step mit `ERR_PNPM_IGNORED_BUILDS`                                                           | Frischer Branch + Drift in pnpm-Version                                     | Branch auf aktuelles `main` rebasen (Pin aus ADR-0010 muss vorhanden sein)                                                                                                                                                                           |
| GHCR-Pull schlägt mit `unauthorized` fehl                                                                                 | Image ist privat                                                            | GitHub → Repo-Settings → Packages → Visibility: `Public`                                                                                                                                                                                             |
| `pnpm install` lokal: `ERR_PNPM_IGNORED_BUILDS`                                                                           | Lokales pnpm liest `allowBuilds` nicht                                      | `corepack use pnpm@11.0.8` (forciert die gepinnte Version)                                                                                                                                                                                           |
| `moodsync-migrate` Exit 1, `SettingsError: error parsing value for field "CORS_ORIGINS"`                                  | CSV-Liste in ENV ohne `NoDecode`                                            | Backend-Image neuer als 2026-05-07 12:54 UTC pullen (Fix in PR #87+); alternativ ENV als JSON setzen (`CORS_ORIGINS=["http://a","http://b"]`)                                                                                                        |
| `moodsync-migrate` Exit 1, `DatatypeMismatchError: column ... is of type ... but expression is of type character varying` | ENUM-Spalte im `bulk_insert`-Stub als `sa.String` deklariert                | Backend-Image neuer als 2026-05-07 14:00 UTC pullen (Fix in PR #89+); für Eigenentwicklungen: ENUM-Typ im `sa.table`-Stub mit `create_type=False` wiederholen — siehe §5                                                                             |
| Container-Create scheitert: `Error starting userland proxy: listen tcp4 0.0.0.0:8000: bind: address already in use`       | Host-Port 8000/3000 von anderem Dienst belegt (Paperless, Grafana ...)      | `API_HOST_PORT=8210` und ggf. `WEB_HOST_PORT=<frei>` in `.env` setzen; `WEB_HOST_PORT`-Änderung erfordert `CORS_ORIGINS`-Anpassung. Siehe §6                                                                                                         |
| Frontend 404 auf `/api/v1/...` am Web-Port, API-Log zeigt keinen POST                                                     | Web-Image pre-ADR-0011 oder Container ohne `INTERNAL_API_URL`-Konnektivität | Web-Image neuer als 2026-05-08 pullen (enthält internen Proxy aus `hooks.server.ts`); `docker compose exec web env \| grep INTERNAL_API_URL` prüfen; API-Container im selben Netzwerk und unter dem konfigurierten Host (`api`) erreichbar. Siehe §7 |
| Frontend 502 auf `/api/v1/...` mit JSON `{"detail":"Upstream API unreachable"}`                                           | Web-Container kann API-Container nicht erreichen                            | API-Container-Status prüfen (`docker compose ps api`); Netzwerk-Reachability vom Web aus testen (`docker compose exec web wget -qO- http://api:8000/api/v1/health/live`); ggf. `INTERNAL_API_URL` korrigieren. Siehe §7                              |

---

## Anhang: Image-Pull verifizieren

Anonymer Pull von `:latest` (sollte HTTP 200 zurückgeben):

```bash
TOKEN=$(curl -s "https://ghcr.io/token?service=ghcr.io&scope=repository:sturmi77/moodsync-api:pull" | jq -r .token)
curl -sI -H "Authorization: Bearer $TOKEN" \
  "https://ghcr.io/v2/sturmi77/moodsync-api/manifests/latest"
```

Die Header-Antwort sollte `HTTP/2 200` zeigen. Bei `401` ist das Image privat oder der Tag existiert nicht.

---

## Verweise

- [ADR-0010: Build-Toolchain-Pinning](adr/0010-build-toolchain-pinning.md)
- [`infra/dockhand/README.md`](../infra/dockhand/README.md) — Dockhand-spezifischer Setup-Guide
- [`infra/docker/README.user-test.md`](../infra/docker/README.user-test.md) — user-test-Compose-Variante
- [`CHANGELOG.md`](../CHANGELOG.md) — vollständige Liste der Hotfixes

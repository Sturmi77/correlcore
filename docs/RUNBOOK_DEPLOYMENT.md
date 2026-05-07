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

## Quick-Reference: Erste-Hilfe-Tabelle

| Symptom                                                                                                                   | Erste Hypothese                                              | Sofort-Check                                                                                                                                                             |
| ------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `moodsync-migrate` Exit 1, `ModuleNotFoundError: No module named 'app'`                                                   | Veraltetes Backend-Image im GHCR                             | Backend-Image neu pullen (`docker pull ghcr.io/sturmi77/moodsync-api:latest`); `docker inspect` muss `Created ≥ 2026-05-07` zeigen, sonst Pull wiederholen               |
| Container bleibt in `Restarting`, Log: `bind: cannot assign requested address` für Tailscale-IP                           | Synology+Tailscale Userspace-Mode                            | `TAILSCALE_IP=0.0.0.0` in `.env`, Stack neu starten                                                                                                                      |
| Web-CI-Job bricht im Install-Step mit `ERR_PNPM_IGNORED_BUILDS`                                                           | Frischer Branch + Drift in pnpm-Version                      | Branch auf aktuelles `main` rebasen (Pin aus ADR-0010 muss vorhanden sein)                                                                                               |
| GHCR-Pull schlägt mit `unauthorized` fehl                                                                                 | Image ist privat                                             | GitHub → Repo-Settings → Packages → Visibility: `Public`                                                                                                                 |
| `pnpm install` lokal: `ERR_PNPM_IGNORED_BUILDS`                                                                           | Lokales pnpm liest `allowBuilds` nicht                       | `corepack use pnpm@11.0.8` (forciert die gepinnte Version)                                                                                                               |
| `moodsync-migrate` Exit 1, `SettingsError: error parsing value for field "CORS_ORIGINS"`                                  | CSV-Liste in ENV ohne `NoDecode`                             | Backend-Image neuer als 2026-05-07 12:54 UTC pullen (Fix in PR #87+); alternativ ENV als JSON setzen (`CORS_ORIGINS=["http://a","http://b"]`)                            |
| `moodsync-migrate` Exit 1, `DatatypeMismatchError: column ... is of type ... but expression is of type character varying` | ENUM-Spalte im `bulk_insert`-Stub als `sa.String` deklariert | Backend-Image neuer als 2026-05-07 14:00 UTC pullen (Fix in PR #89+); für Eigenentwicklungen: ENUM-Typ im `sa.table`-Stub mit `create_type=False` wiederholen — siehe §5 |

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

# MoodSync — Dockhand-Stack (User-Test)

Drop-in für [Dockhand](https://dockhand.pro). Für die Stack-Manager-UI im
Homelab — funktional identisch zu `infra/docker/docker-compose.user-test.yml`
und `infra/dockge/compose.yaml`, aber an die Dockhand-Konventionen
(Git-Stack-Sync, Vulnerability-Scan, Visual Editor) angepasst.

## Setup

### Variante A — Git-Stack (empfohlen)

Dockhand pullt das Repo selbst und re-deployt bei jedem Webhook-Push.

1. Im Dockhand-UI: **Stacks → New → From Git**
2. Felder:
   - **Repository:** `https://github.com/Sturmi77/moodsync`
   - **Branch:** `main`
   - **Compose path:** `infra/dockhand`
   - **Auto-sync:** an (für Webhook-getriggerte Re-Deploys)
3. Tab **Environment** öffnen → Variablen aus `.env.example` übernehmen und
   Secrets ausfüllen (siehe unten).
4. Optional **Profiles to enable** setzen:
   - `monitoring` für GlitchTip
   - `worker` für Analytics-Worker (M2+, Code noch nicht da)
5. **Deploy** klicken.

### Variante B — Manuelles Verzeichnis

1. Verzeichnis am Host anlegen, z. B. `/opt/stacks/moodsync/`.
2. `compose.yaml` und `.env.example` reinkopieren.
3. `cp .env.example .env` und alle leeren Variablen ausfüllen.
4. Im Dockhand-UI: **Stacks → Adopt** (oder **New → From file**) und das
   Verzeichnis verlinken.

```bash
sudo mkdir -p /opt/stacks/moodsync
sudo cp infra/dockhand/compose.yaml infra/dockhand/.env.example /opt/stacks/moodsync/
cd /opt/stacks/moodsync
sudo cp .env.example .env
sudo $EDITOR .env
# → Dockhand-UI: Adopt stack
```

## Secrets generieren

```bash
# SECRET_KEY
python3 -c 'import secrets; print(secrets.token_urlsafe(48))'

# ENCRYPTION_KEY (Fernet)
python3 -c 'from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())'

# POSTGRES_PASSWORD / REDIS_PASSWORD
python3 -c 'import secrets; print(secrets.token_urlsafe(24))'

# GLITCHTIP_SECRET_KEY (nur wenn Profile 'monitoring' aktiv)
python3 -c 'import secrets; print(secrets.token_urlsafe(48))'
```

> **WICHTIG:** `ENCRYPTION_KEY` sicher backuppen. Geht der Key verloren,
> sind alle verschlüsselten Felder unentschlüsselbar.

## Environment-Variablen-Referenz

Alle Variablen aus `.env.example` im Detail — was sie tun, ob sie pflicht
sind, welche Form sie brauchen und wo sie im Backend-Code wirken
([`backend/app/core/config.py`](../../backend/app/core/config.py)).

### Stack-Steuerung (nur in der Compose, nicht im Backend)

| Variable       | Pflicht | Default     | Beschreibung                                                                                                                                                                                                                                                                                                            |
| -------------- | ------- | ----------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `IMAGE_TAG`    | nein    | `latest`    | Welcher GHCR-Tag für `moodsync-api` und `moodsync-web` gepullt wird. Empfohlen: pinned Tag (`sha-abc1234` oder `v0.3.0`) damit Dockhands Vulnerability-Scan (Grype/Trivy) reproducible vergleichen kann. Verfügbare Tags siehe [GHCR-Pakete im Repo](https://github.com/Sturmi77/moodsync/pkgs/container/moodsync-api). |
| `TAILSCALE_IP` | nein    | `127.0.0.1` | IPv4-Adresse, auf die api/web/mailpit (und optional GlitchTip) ihre Ports binden. Default `127.0.0.1` = nur vom Host selbst erreichbar. Für Tailnet-Zugriff: `tailscale ip -4` auf dem Host → z. B. `100.101.102.103`.                                                                                                  |

### Backend — App-Modus

| Variable  | Pflicht | Default   | Beschreibung                                                                                                                                                                                                        |
| --------- | ------- | --------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `APP_ENV` | nein    | `staging` | `development` \| `staging` \| `production`. Bei `staging`/`production` greift ein zusätzlicher Validator: `SECRET_KEY` muss ≥ 32 Zeichen und nicht-Default sein, `ENCRYPTION_KEY` darf nicht den Platzhalter haben. |

### Backend — Auth & Krypto (sicherheitskritisch)

| Variable         | Pflicht | Default  | Beschreibung                                                                                                                                                                                                                                                                                                                                                                                                |
| ---------------- | ------- | -------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `SECRET_KEY`     | **ja**  | _keiner_ | Signiert JWT-Access- und Refresh-Tokens (HS256, ADR-0004). Mindestens 32 Bytes, URL-safe. Generieren: `python -c 'import secrets; print(secrets.token_urlsafe(48))'`. Wechsel führt dazu, dass alle ausgegebenen Tokens sofort ungültig werden → alle User müssen neu einloggen.                                                                                                                            |
| `ENCRYPTION_KEY` | **ja**  | _keiner_ | Master-Key (Fernet, AES-128-CBC + HMAC-SHA256), der die per-User-DEKs in `user_encryption_keys.wrapped_dek` wrapped (ADR-0005, Issue #26). Damit werden `entries.note_enc` und Custom-`symptoms.name_enc` verschlüsselt at-rest. **Verlust = Daten unentschlüsselbar**. Generieren: `python -c 'from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())'`. Backup z. B. in Bitwarden. |

> **Key-Rotation:** Optional kann statt `ENCRYPTION_KEY` eine Komma-Liste
> `ENCRYPTION_KEYS=neu,alt1,alt2` gesetzt werden. Der erste Key
> verschlüsselt neue Daten, alle Keys können entschlüsseln (siehe
> `Settings.effective_encryption_keys()`). Für User-Test nicht nötig.

### Backend — Datenbank

| Variable            | Pflicht | Default    | Beschreibung                                                                                                                                                                                                                                                            |
| ------------------- | ------- | ---------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `POSTGRES_DB`       | nein    | `moodsync` | Name der App-Datenbank, die der Postgres-Container beim ersten Start anlegt.                                                                                                                                                                                            |
| `POSTGRES_USER`     | nein    | `moodsync` | DB-User, der vom `migrate`-Container und der API genutzt wird.                                                                                                                                                                                                          |
| `POSTGRES_PASSWORD` | **ja**  | _keiner_   | Passwort für `POSTGRES_USER`. **Mindestens 20 Zeichen, kein `@` und kein `/`** — beides bricht den Asyncpg-DSN auseinander. Generieren: `python -c 'import secrets; print(secrets.token_urlsafe(24))'`. Wird von der API automatisch in `DATABASE_URL` zusammengesetzt. |

> `DATABASE_URL` wird in der Compose aus den drei Variablen gebaut:
> `postgresql+asyncpg://${POSTGRES_USER}:${POSTGRES_PASSWORD}@postgres:5432/${POSTGRES_DB}`. Du musst `DATABASE_URL` selbst nicht setzen.

### Backend — Redis

| Variable         | Pflicht | Default  | Beschreibung                                                                                                                                                                                                                                                                                     |
| ---------------- | ------- | -------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `REDIS_PASSWORD` | **ja**  | _keiner_ | Passwort für Redis. Wird via `redis-server --requirepass` an den Container übergeben. Mindestens 20 Zeichen empfohlen. Redis dient als Token-Store (Refresh-Token-Family-Tracking, ADR-0004) und Rate-Limit-Backend. Generieren: `python -c 'import secrets; print(secrets.token_urlsafe(24))'`. |

> `REDIS_URL` wird automatisch zu `redis://:${REDIS_PASSWORD}@redis:6379/0` zusammengesetzt.

### Backend — CORS

| Variable       | Pflicht | Default                 | Beschreibung                                                                                                                                                                                                                                                                                                                                                             |
| -------------- | ------- | ----------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `CORS_ORIGINS` | ja\*    | `http://127.0.0.1:3000` | Komma-separierte Liste von Origins, von denen das Frontend die API aufrufen darf. Wird im Pydantic-Validator `parse_cors_origins` aus der Komma-String in eine Python-Liste übersetzt. Für Tailnet-Tests: `http://<tailscale-ip>:3000` und/oder `http://<magicdns-name>.ts.net:3000`. \*Pflicht in dem Sinn, dass der Default nur für lokalen Host-Zugriff funktioniert. |

### Frontend — Web

| Variable            | Pflicht | Default   | Beschreibung                                                                                                                                                                                                                                                                                                                                |
| ------------------- | ------- | --------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `VITE_API_BASE_URL` | nein    | `/api/v1` | API-Pfad, den der SvelteKit-Server zur Runtime nutzt. **Achtung:** Im aktuellen Release-Workflow wird der Wert `/api/v1` zusätzlich beim Image-Build als Build-Arg fest ins Web-Image gebacken. Änderungen zur Runtime greifen nur für server-seitige Fetches, nicht für im Bundle hardgecodete URLs. Für User-Test einfach Default lassen. |

### Backend — SMTP / E-Mail-Verifikation

| Variable        | Pflicht | Default                  | Beschreibung                                                                                                                                                                                                                                                           |
| --------------- | ------- | ------------------------ | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `SMTP_HOST`     | nein    | `mailpit`                | SMTP-Server-Hostname. Default zeigt auf den lokalen Mailpit-Container. Für echten Mailversand: z. B. `smtp.eu.mailgun.org`, `smtp.fastmail.com`.                                                                                                                       |
| `SMTP_PORT`     | nein    | `1025`                   | SMTP-Port. Mailpit lauscht auf `1025` (kein TLS). Echter Provider meist `587` (STARTTLS) oder `465` (SMTPS). **Hinweis:** Backend-Default in `config.py` ist `587` — die Compose überschreibt das hier explizit auf `1025`, damit Mailpit out-of-the-box funktioniert. |
| `SMTP_USER`     | nein    | _leer_                   | Auth-User beim SMTP-Provider. Für Mailpit nicht nötig.                                                                                                                                                                                                                 |
| `SMTP_PASSWORD` | nein    | _leer_                   | Auth-Passwort. Für Mailpit nicht nötig.                                                                                                                                                                                                                                |
| `SMTP_FROM`     | nein    | `noreply@moodsync.local` | Absender-Adresse für Verifikations- und Reset-Mails. Für echten Versand auf eine validierte Domain umstellen.                                                                                                                                                          |

> Die Backend-Settings `SMTP_USE_TLS` (Default `true`), `SMTP_TIMEOUT`
> (Default `10`), `EMAIL_VERIFICATION_TTL_HOURS` (Default `24`,
> ADR-0004) und `FRONTEND_BASE_URL` (Default `http://localhost:5173`)
> sind in der Compose nicht expliziert — die Backend-Defaults reichen
> für den User-Test. Wer einen externen SMTP-Provider mit STARTTLS nutzt,
> lässt `SMTP_USE_TLS=true` (Default). Für Mailpit empfiehlt sich
> `SMTP_USE_TLS=false`, weil Mailpit standardmäßig auf `1025` ohne TLS
> lauscht.
>
> Auch `FRONTEND_BASE_URL` solltest du spätestens dann auf den Tailnet-
> Hostnamen ändern (`http://moodsync.<tailnet>.ts.net:3000` o.ä.), wenn
> du echte Verifikations-Mails verschicken willst — sonst zeigt der Link
> in der Mail auf `localhost:5173`.

### Optional — GlitchTip (Profile `monitoring`)

| Variable               | Pflicht\*\* | Default | Beschreibung                                                                                                                                                                                                                                    |
| ---------------------- | ----------- | ------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `GLITCHTIP_SECRET_KEY` | ja\*\*      | _leer_  | Django-Secret für GlitchTip (separat von `SECRET_KEY` der MoodSync-API). Mindestens 50 Zeichen empfohlen. Generieren: `python -c 'import secrets; print(secrets.token_urlsafe(48))'`. \*\*Pflicht nur, wenn das Profile `monitoring` aktiv ist. |

Weitere GlitchTip-Variablen (`DATABASE_URL`, `EMAIL_URL`,
`GLITCHTIP_DOMAIN`, `ENABLE_USER_REGISTRATION`) werden direkt in der
Compose gesetzt — nicht in `.env`.

### Pflicht-Kurzliste vor erstem Deploy

Füllen muss man **mindestens** diese vier Variablen, sonst startet der
Stack nicht (Compose-Validator wirft `must be set`-Fehler):

```env
SECRET_KEY=...                # python -c 'import secrets; print(secrets.token_urlsafe(48))'
ENCRYPTION_KEY=...            # python -c 'from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())'
POSTGRES_PASSWORD=...         # python -c 'import secrets; print(secrets.token_urlsafe(24))'
REDIS_PASSWORD=...            # python -c 'import secrets; print(secrets.token_urlsafe(24))'
```

`TAILSCALE_IP` und `CORS_ORIGINS` zusätzlich anpassen, wenn der Stack im
Tailnet erreichbar sein soll (sonst nur localhost).

## Tailscale-Bind

Setze `TAILSCALE_IP=$(tailscale ip -4)` in der `.env`. Dann binden api/web/
mailpit nur auf das Tailnet-Interface — kein WAN-Exposure.

| Service | Host-Port (Default)      | Zugriff im Tailnet                                  |
| ------- | ------------------------ | --------------------------------------------------- |
| Web     | `${WEB_HOST_PORT:-3000}` | `http://<tailscale-ip>:<WEB_HOST_PORT>`             |
| API     | `${API_HOST_PORT:-8210}` | `http://<tailscale-ip>:<API_HOST_PORT>/health/live` |
| Mailpit | 8025                     | `http://<tailscale-ip>:8025`                        |

Postgres und Redis sind nur stack-intern erreichbar (kein Port-Mapping).

### Host-Port-Konflikte (Synology-typisch)

Die Host-Ports sind über `API_HOST_PORT` und `WEB_HOST_PORT` in der `.env`
konfigurierbar, weil 8000 und 3000 auf typischen Selfhosted-Setups oft
schon belegt sind:

| Standard-Port | Häufig belegt durch | Default-Ausweich-Port (MoodSync)   |
| ------------- | ------------------- | ---------------------------------- |
| 8000          | Paperless-ngx       | `API_HOST_PORT=8210`               |
| 3000          | Grafana             | bleibt 3000 (anpassen falls nötig) |

**Wenn du `WEB_HOST_PORT` änderst, vergiss nicht, in `CORS_ORIGINS` den
entsprechenden Port nachzuziehen** — sonst blockiert der Browser API-Calls
vom Frontend mit CORS-Fehler.

Der Container-interne Port bleibt in beiden Fällen fix (8000 bzw. 3000);
das Mapping erfolgt nur auf Host-Seite.

## Migrations

Der `migrate`-Container läuft einmalig vor `api`/`worker` und führt
`alembic upgrade head` aus. Idempotent — Re-Deploys triggern automatisch
neue Migrations.

In der Dockhand-Container-Liste erscheint `moodsync-migrate` nach
erfolgreichem Run als **Exited (0)** — das ist gewollt, kein Fehler.

## Profiles in Dockhand

`compose.yaml` definiert zwei Profile:

| Profile      | Service     | Zweck                                      |
| ------------ | ----------- | ------------------------------------------ |
| `monitoring` | `glitchtip` | Error-Tracking-Web-UI auf Port 8080        |
| `worker`     | `worker`    | Analytics-Worker (M2+, Code fehlt aktuell) |

Aktivierung:

- **Variante A (Git-Stack):** Stack-Detail → **Profiles to enable** Feld →
  z. B. `monitoring` eintragen → Re-Deploy.
- **Variante B (CLI):** `docker compose --profile monitoring up -d`.

GlitchTip-Erst-Bootstrap nach erstem Up:

```bash
docker exec -it moodsync-glitchtip ./manage.py migrate
docker exec -it moodsync-glitchtip ./manage.py createsuperuser
```

## Update auf neuen Image-Tag

Dockhand integriert Vulnerability-Scanning beim Update (Grype + Trivy):
ein neues Image wird zu einem temporären Tag gepullt und nur deployed
wenn der CVE-Count nicht steigt.

```bash
# .env
IMAGE_TAG=v0.3.0       # statt 'latest' — saubere Versionierung
```

Im Dockhand-UI: Stack-Detail → **Re-pull images** → **Redeploy**.

> **Bei `IMAGE_TAG=latest`** sorgt `pull_policy: always` (gesetzt auf
> `api`, `migrate`, `worker` via Anchor und auf `web`) dafür, dass
> jeder Redeploy automatisch das aktuellste GHCR-Image holt — ein
> manueller **Re-pull** ist dafür nicht mehr nötig. Für `postgres`,
> `redis` und `mailpit` ist `pull_policy` bewusst nicht gesetzt:
> diese laufen auf gepinnten Versions-Tags und sollen sich nicht
> ungewollt aktualisieren.
>
> **Achtung beim Mischen mit `:latest`:** Da Auto-Pull zwangsläufig
> `:latest` hält, propagiert ein fehlerhaftes main-Image direkt zum
> nächsten Redeploy. Für Production-ähnliche Stabilität lieber auf
> `IMAGE_TAG=vX.Y.Z` oder `IMAGE_TAG=sha-<short>` pinnen — siehe
> `docs/RUNBOOK_DEPLOYMENT.md` für die Verifikations-Snippets.

## Logging

Alle Services nutzen `json-file`-Driver mit `max-size=10m, max-file=3`
(per `x-logging`-Anchor). Damit explodiert Dockhands Log-Viewer nicht
und der Plattenverbrauch bleibt vorhersehbar.

## Backup

```bash
# Postgres-Dump
docker exec moodsync-postgres pg_dump -U moodsync moodsync \
  | gzip > moodsync-$(date +%F).sql.gz

# Volumes (alternativ, vollständig)
docker run --rm -v moodsync_postgres_data:/data -v "$PWD":/backup \
  alpine tar czf /backup/postgres-data-$(date +%F).tar.gz -C /data .
```

`ENCRYPTION_KEY` gehört NICHT in den DB-Dump — zusätzlich getrennt sichern.

## Unterschiede zu den anderen Compose-Varianten

| Punkt              | user-test (CLI)        | Dockge                     | Dockhand                           |
| ------------------ | ---------------------- | -------------------------- | ---------------------------------- |
| Top-level `name:`  | `moodsync-test`        | _kein_ (nimmt Verzeichnis) | `moodsync` (Dockhand respektiert)  |
| Container-Präfix   | `moodsync-test-*`      | `moodsync-*`               | `moodsync-*`                       |
| `pull_policy`      | `always`               | `always`                   | `always` (api/migrate/worker/web)  |
| Profiles           | `monitoring`, `worker` | _auskommentiert_           | `monitoring`, `worker` (UI-Feld)   |
| Logging-Limits     | _default_              | _default_                  | `json-file` 10 MB × 3 (per Anchor) |
| Volume-Namen       | compose-default        | explizit (`moodsync_*`)    | explizit (`moodsync_*`)            |
| Network-Name       | `internal`             | `moodsync`                 | `moodsync`                         |
| Git-Sync supported | nein                   | nein                       | ja (Webhook-Auto-Deploy)           |

Funktional identisch — gleiche GHCR-Images, gleiche Services, gleiche
Healthchecks, gleicher Tailscale-IP-Bind.

# CorrelCore — Dockhand-Stack (User-Test)

Drop-in für [Dockhand](https://dockhand.pro). Für die Stack-Manager-UI im
Homelab — funktional identisch zu `infra/docker/docker-compose.user-test.yml`
und `infra/dockge/compose.yaml`, aber an die Dockhand-Konventionen
(Git-Stack-Sync, Vulnerability-Scan, Visual Editor) angepasst.

## Setup

### Variante A — Git-Stack (empfohlen)

Dockhand pullt das Repo selbst und re-deployt bei jedem Webhook-Push.

1. Im Dockhand-UI: **Stacks → New → From Git**
2. Felder:
   - **Repository:** `https://github.com/Sturmi77/correlcore`
   - **Branch:** `main`
   - **Compose path:** `infra/dockhand`
   - **Auto-sync:** an (für Webhook-getriggerte Re-Deploys)
3. Tab **Environment** öffnen → Variablen aus `.env.example` übernehmen und
   Secrets ausfüllen (siehe unten).
4. Optional **Profiles to enable** setzen:
   - `monitoring` für GlitchTip
   - `worker` fuer den M2-Cleanup-Worker
5. **Deploy** klicken.

### Variante B — Manuelles Verzeichnis

1. Verzeichnis am Host anlegen, z. B. `/opt/stacks/correlcore/`.
2. `compose.yaml`, `initdb/` und `.env.example` reinkopieren.
3. `cp .env.example .env` und alle leeren Variablen ausfüllen.
4. Im Dockhand-UI: **Stacks → Adopt** (oder **New → From file**) und das
   Verzeichnis verlinken.

```bash
sudo mkdir -p /opt/stacks/correlcore
sudo cp infra/dockhand/compose.yaml infra/dockhand/.env.example /opt/stacks/correlcore/
sudo cp -r infra/dockhand/initdb /opt/stacks/correlcore/
cd /opt/stacks/correlcore
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

# POSTGRES_PASSWORD / APP_DB_PASSWORD / REDIS_PASSWORD
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

| Variable       | Pflicht | Default     | Beschreibung                                                                                                                                                                                                                                                                                                                    |
| -------------- | ------- | ----------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `IMAGE_TAG`    | nein    | `latest`    | Welcher GHCR-Tag für `correlcore-api` und `correlcore-web` gepullt wird. Empfohlen: pinned Tag (`sha-abc1234` oder `v0.3.0`) damit Dockhands Vulnerability-Scan (Grype/Trivy) reproducible vergleichen kann. Verfügbare Tags siehe [GHCR-Pakete im Repo](https://github.com/Sturmi77/correlcore/pkgs/container/correlcore-api). |
| `TAILSCALE_IP` | nein    | `127.0.0.1` | IPv4-Adresse, auf die api/web/mailpit (und optional GlitchTip) ihre Ports binden. Default `127.0.0.1` = nur vom Host selbst erreichbar. Für Tailnet-Zugriff: `tailscale ip -4` auf dem Host → z. B. `100.101.102.103`.                                                                                                          |

### Backend — App-Modus

| Variable  | Pflicht | Default   | Beschreibung                                                                                                                                                                                                        |
| --------- | ------- | --------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `APP_ENV` | nein    | `staging` | `development` \| `staging` \| `production`. Bei `staging`/`production` greift ein zusätzlicher Validator: `SECRET_KEY` muss ≥ 32 Zeichen und nicht-Default sein, `ENCRYPTION_KEY` darf nicht den Platzhalter haben. |

### Backend — Auth & Krypto (sicherheitskritisch)

| Variable           | Pflicht                         | Default                  | Beschreibung                                                                                                                                                                                                                                                                                                                                                                                                |
| ------------------ | ------------------------------- | ------------------------ | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `SECRET_KEY`       | **ja**                          | _keiner_                 | Signiert JWT-Access- und Refresh-Tokens (HS256, ADR-0004). Mindestens 32 Bytes, URL-safe. Generieren: `python -c 'import secrets; print(secrets.token_urlsafe(48))'`. Wechsel führt dazu, dass alle ausgegebenen Tokens sofort ungültig werden → alle User müssen neu einloggen.                                                                                                                            |
| `ENCRYPTION_KEY`   | **ja**                          | _keiner_                 | Master-Key (Fernet, AES-128-CBC + HMAC-SHA256), der die per-User-DEKs in `user_encryption_keys.wrapped_dek` wrapped (ADR-0005, Issue #26). Damit werden `entries.note_enc` und Custom-`symptoms.name_enc` verschlüsselt at-rest. **Verlust = Daten unentschlüsselbar**. Generieren: `python -c 'from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())'`. Backup z. B. in Bitwarden. |
| `SLUG_HMAC_KEY`    | **ja** (bei staging/production) | _keiner_                 | HMAC für Custom-Symptom-Slugs (ADR-0039), **separat** von `ENCRYPTION_KEY`. ≥32 Zeichen, nicht `CHANGE_ME*`. Generieren: `python -c 'import secrets; print(secrets.token_hex(32))'`. Wird an `migrate`/`api`/`worker` durchgereicht.                                                                                                                                                                        |
| `MINIO_SECRET_KEY` | nur bei `PHOTOS_ENABLED=true`   | `CHANGE_ME_MINIO_SECRET` | Placeholder bis M13 (Fotos). Fotos sind standardmäßig aus; erst mit `PHOTOS_ENABLED=true` lehnen Production-Settings `CHANGE_ME*` und Secrets &lt; 16 Zeichen ab (#543). Compose reicht beide an `migrate`/`api`/`worker` durch — nur in der `.env` setzen reicht nicht ohne Compose-Mapping. Generieren: `python -c 'import secrets; print(secrets.token_urlsafe(24))'`.                                   |

> **Key-Rotation:** Optional kann statt `ENCRYPTION_KEY` eine Komma-Liste
> `ENCRYPTION_KEYS=neu,alt1,alt2` gesetzt werden. Der erste Key
> verschlüsselt neue Daten, alle Keys können entschlüsseln (siehe
> `Settings.effective_encryption_keys()`). Für User-Test nicht nötig.

### Backend — Datenbank

| Variable            | Pflicht | Default          | Beschreibung                                                                                                                                                                                                                                  |
| ------------------- | ------- | ---------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `POSTGRES_DB`       | nein    | `correlcore`     | Name der App-Datenbank, die der Postgres-Container beim ersten Start anlegt.                                                                                                                                                                  |
| `POSTGRES_USER`     | nein    | `correlcore`     | Migrations-/Owner-User, der das Schema anlegt. API und Worker nutzen diesen User nicht mehr.                                                                                                                                                  |
| `POSTGRES_PASSWORD` | **ja**  | _keiner_         | Passwort für `POSTGRES_USER`. **Mindestens 20 Zeichen, kein `@` und kein `/`** — beides bricht den Asyncpg-DSN auseinander. Generieren: `python -c 'import secrets; print(secrets.token_urlsafe(24))'`. Wird vom `migrate`-Container genutzt. |
| `APP_DB_USER`       | nein    | `correlcore_app` | Eingeschränkter Runtime-DB-User für API und Worker. Der Postgres-Init legt ihn beim ersten Volume-Start an; Migration 012 erteilt Tabellenrechte und erzwingt RLS.                                                                            |
| `APP_DB_PASSWORD`   | **ja**  | _keiner_         | Passwort für `APP_DB_USER`. Separat von `POSTGRES_PASSWORD` generieren.                                                                                                                                                                       |

> `DATABASE_URL` wird in der Compose getrennt gebaut: `migrate` nutzt
> `POSTGRES_USER`, API/Worker nutzen `APP_DB_USER`.

### Backend — Redis

| Variable         | Pflicht | Default  | Beschreibung                                                                                                                                                                                                                                                                                     |
| ---------------- | ------- | -------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `REDIS_PASSWORD` | **ja**  | _keiner_ | Passwort für Redis. Wird via `redis-server --requirepass` an den Container übergeben. Mindestens 20 Zeichen empfohlen. Redis dient als Token-Store (Refresh-Token-Family-Tracking, ADR-0004) und Rate-Limit-Backend. Generieren: `python -c 'import secrets; print(secrets.token_urlsafe(24))'`. |

> `REDIS_URL` wird automatisch zu `redis://:${REDIS_PASSWORD}@redis:6379/0` zusammengesetzt.

### Backend — CORS

| Variable       | Pflicht | Default                 | Beschreibung                                                                                                                                                                                                                                                                                                                                                             |
| -------------- | ------- | ----------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `CORS_ORIGINS` | ja\*    | `http://127.0.0.1:3010` | Komma-separierte Liste von Origins, von denen das Frontend die API aufrufen darf. Wird im Pydantic-Validator `parse_cors_origins` aus der Komma-String in eine Python-Liste übersetzt. Für Tailnet-Tests: `http://<tailscale-ip>:3010` und/oder `http://<magicdns-name>.ts.net:3010`. \*Pflicht in dem Sinn, dass der Default nur für lokalen Host-Zugriff funktioniert. |

### Frontend — Web

| Variable           | Pflicht | Default           | Beschreibung                                                                                                                                                                                                                                                                                                                                                                                            |
| ------------------ | ------- | ----------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `INTERNAL_API_URL` | nein    | `http://api:8000` | Upstream für den Web-internen Reverse-Proxy (ADR-0011). `apps/web/src/hooks.server.ts` leitet alle `/api/*`-Requests serverseitig hierhin weiter. Der Default greift im Compose-Netz über den Service-Namen `api` automatisch — nur setzen, wenn der API-Service umbenannt oder extern liegt. **`VITE_API_BASE_URL` gibt es seit ADR-0011 nicht mehr als Stack-Variable; der Wert ist fest `/api/v1`.** |

### Backend — SMTP / E-Mail-Verifikation

| Variable        | Pflicht | Default                    | Beschreibung                                                                                                                                                                                                                                                           |
| --------------- | ------- | -------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `SMTP_HOST`     | nein    | `mailpit`                  | SMTP-Server-Hostname. Default zeigt auf den lokalen Mailpit-Container. Für echten Mailversand: z. B. `smtp.eu.mailgun.org`, `smtp.fastmail.com`.                                                                                                                       |
| `SMTP_PORT`     | nein    | `1025`                     | SMTP-Port. Mailpit lauscht auf `1025` (kein TLS). Echter Provider meist `587` (STARTTLS) oder `465` (SMTPS). **Hinweis:** Backend-Default in `config.py` ist `587` — die Compose überschreibt das hier explizit auf `1025`, damit Mailpit out-of-the-box funktioniert. |
| `SMTP_USER`     | nein    | _leer_                     | Auth-User beim SMTP-Provider. Für Mailpit nicht nötig.                                                                                                                                                                                                                 |
| `SMTP_PASSWORD` | nein    | _leer_                     | Auth-Passwort. Für Mailpit nicht nötig.                                                                                                                                                                                                                                |
| `SMTP_FROM`     | nein    | `noreply@correlcore.local` | Absender-Adresse für Verifikations- und Reset-Mails. Für echten Versand auf eine validierte Domain umstellen.                                                                                                                                                          |

> Die Backend-Settings `SMTP_USE_TLS` (Default _auto_, siehe unten),
> `SMTP_TIMEOUT` (Default `10`), `EMAIL_VERIFICATION_TTL_HOURS`
> (Default `24`, ADR-0004) und `FRONTEND_BASE_URL` (Default
> `http://localhost:5173`) sind in der Compose nicht expliziert — die
> Backend-Defaults reichen für den User-Test.
>
> **`SMTP_USE_TLS` ist seit PR #94 ein Tri-State (`true` / `false` /
> _unset_) mit smartem Default:** Bleibt die Variable leer, schaltet das
> Backend STARTTLS automatisch nur dann ein, wenn `SMTP_USER` einen
> nicht-leeren Wert hat. Heuristik dahinter: "Auth gesetzt = echter
> Relay = STARTTLS", "keine Auth = Dev-Catcher wie Mailpit/MailHog =
> plain". Damit funktioniert die Default-`.env` ohne weitere Eingriffe
> sowohl mit Mailpit (`SMTP_USER=` leer) als auch mit einem echten
> Provider (`SMTP_USER=<key>` gesetzt). Explizit `SMTP_USE_TLS=true`
> oder `SMTP_USE_TLS=false` setzen überschreibt die Heuristik immer.
>
> Auch `FRONTEND_BASE_URL` solltest du spätestens dann auf den Tailnet-
> Hostnamen ändern (`http://correlcore.<tailnet>.ts.net:3010` o.ä.), wenn
> du echte Verifikations-Mails verschicken willst — sonst zeigt der Link
> in der Mail auf `localhost:5173`.
>
> Wenn Mailversand ausfaellt und User ihre Adresse nie verifizieren,
> blockieren diese Accounts die Adresse nicht dauerhaft: der optionale
> `worker`-Service loescht unverified Accounts nach
> `UNVERIFIED_CLEANUP_DAYS` Tagen (Default `7`) automatisch.

### Optional — GlitchTip (Profile `monitoring`)

| Variable               | Pflicht\*\* | Default | Beschreibung                                                                                                                                                                                                                                      |
| ---------------------- | ----------- | ------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `GLITCHTIP_SECRET_KEY` | ja\*\*      | _leer_  | Django-Secret für GlitchTip (separat von `SECRET_KEY` der CorrelCore-API). Mindestens 50 Zeichen empfohlen. Generieren: `python -c 'import secrets; print(secrets.token_urlsafe(48))'`. \*\*Pflicht nur, wenn das Profile `monitoring` aktiv ist. |

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
APP_DB_PASSWORD=...           # python -c 'import secrets; print(secrets.token_urlsafe(24))'
REDIS_PASSWORD=...            # python -c 'import secrets; print(secrets.token_urlsafe(24))'
```

`TAILSCALE_IP` und `CORS_ORIGINS` zusätzlich anpassen, wenn der Stack im
Tailnet erreichbar sein soll (sonst nur localhost).

## Tailscale-Bind

Setze `TAILSCALE_IP=$(tailscale ip -4)` in der `.env`. Dann binden web und
mailpit nur auf das Tailnet-Interface — kein WAN-Exposure.

| Service | Host-Port (Default)      | Zugriff im Tailnet                       |
| ------- | ------------------------ | ---------------------------------------- |
| Web     | `${WEB_HOST_PORT:-3010}` | `http://<tailscale-ip>:<WEB_HOST_PORT>`  |
| API     | _kein Host-Port_         | nur intern (`http://api:8000`, ADR-0011) |
| Mailpit | 8025                     | `http://<tailscale-ip>:8025`             |

**Seit ADR-0011 hat die API kein Host-Port-Mapping mehr.** Der Web-Container
proxyt `/api/*` serverseitig an `INTERNAL_API_URL` (Default `http://api:8000`)
über das interne Compose-Netz. Damit ist die API auch im Tailnet nicht
mehr direkt ansprechbar — ein Sicherheitsplus, weil es genau eine externe
Origin (Web auf `WEB_HOST_PORT`) gibt. Für API-Healthchecks von außen den
Umweg über Web nehmen: `http://<tailscale-ip>:<WEB_HOST_PORT>/api/v1/health`.

Postgres und Redis sind ohnehin nur stack-intern erreichbar.

### Host-Port-Konflikt: Web auf 3000

Der Dockhand-Default nutzt `WEB_HOST_PORT=3010`, damit typische Host-
Konflikte auf 3000 (z. B. Grafana oder ein anderes Web-UI) vermieden
werden. Falls 3010 auf dem Host ebenfalls belegt ist, `WEB_HOST_PORT` in
der `.env` weiter ausweichen — z. B. `WEB_HOST_PORT=3011`.
Container-interner Port bleibt fix 3000.

Wenn du `WEB_HOST_PORT` änderst, denke an `FRONTEND_BASE_URL` (wird in
Verifikations-Mails als Link-Präfix verwendet). `CORS_ORIGINS` ist seit
ADR-0011 unkritisch geworden (Same-Origin durch den Web-Proxy), sollte
der Vollständigkeit halber aber mitgezogen werden.

> **Hinweis zu alten `.env`-Dateien:** `API_HOST_PORT` und
> `VITE_API_BASE_URL` werden vom aktuellen `compose.yaml` nicht mehr
> ausgewertet und können gelöscht werden — leere Reste stören aber nicht.

## Migrations

Der `migrate`-Container läuft einmalig vor `api`/`worker` und führt
`alembic upgrade head` aus. Idempotent — Re-Deploys triggern automatisch
neue Migrations.

In der Dockhand-Container-Liste erscheint `correlcore-migrate` nach
erfolgreichem Run als **Exited (0)** — das ist gewollt, kein Fehler.

## Profiles in Dockhand

`compose.yaml` definiert zwei Profile:

| Profile      | Service     | Zweck                                      |
| ------------ | ----------- | ------------------------------------------ |
| `monitoring` | `glitchtip` | Error-Tracking-Web-UI auf Port 8080        |
| `worker`     | `worker`    | M2-Cleanup-Worker fuer unverified Accounts |

Aktivierung:

- **Variante A (Git-Stack):** Stack-Detail → **Profiles to enable** Feld →
  z. B. `monitoring` eintragen → Re-Deploy.
- **Variante B (CLI):** `docker compose --profile monitoring up -d`.

GlitchTip-Erst-Bootstrap nach erstem Up:

```bash
docker exec -it correlcore-glitchtip ./manage.py migrate
docker exec -it correlcore-glitchtip ./manage.py createsuperuser
```

## Update auf neuen Image-Tag

Dockhand integriert Vulnerability-Scanning beim Update (Grype + Trivy):
ein neues Image wird zu einem temporären Tag gepullt und nur deployed
wenn der CVE-Count nicht steigt.

```bash
# .env — pin a release, not an old sha-* forever
IMAGE_TAG=v1.0.8
```

Im Dockhand-UI: Stack-Detail → **Re-pull images** → **Redeploy**.

Nach dem Redeploy prüfen, welches Build wirklich läuft:

```bash
curl -sS http://127.0.0.1:${WEB_HOST_PORT:-3010}/api/v1/health/live
docker ps --format '{{.Names}} {{.Image}}' | grep correlcore
```

`image_tag` / `git_commit` müssen zum gewünschten Pin passen. Ein alter
`IMAGE_TAG=sha-…` erklärt „Bug ist auf main schon gefixt, bei mir noch da“.

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

Consolidated backup, restic, and restore procedure:
[`docs/selfhost/INSTALL.md`](../../docs/selfhost/INSTALL.md) §Backup.

```bash
# Postgres-Dump
docker exec correlcore-postgres pg_dump -U correlcore correlcore \
  | gzip > correlcore-$(date +%F).sql.gz

# Volumes (alternativ, vollständig)
docker run --rm -v correlcore_postgres_data:/data -v "$PWD":/backup \
  alpine tar czf /backup/postgres-data-$(date +%F).tar.gz -C /data .
```

`ENCRYPTION_KEY` gehört NICHT in den DB-Dump — zusätzlich getrennt sichern.

## Unterschiede zu den anderen Compose-Varianten

| Punkt              | user-test (CLI)        | Dockge                     | Dockhand                            |
| ------------------ | ---------------------- | -------------------------- | ----------------------------------- |
| Top-level `name:`  | `correlcore-test`      | _kein_ (nimmt Verzeichnis) | `correlcore` (Dockhand respektiert) |
| Container-Präfix   | `correlcore-test-*`    | `correlcore-*`             | `correlcore-*`                      |
| `pull_policy`      | `always`               | `always`                   | `always` (api/migrate/worker/web)   |
| Profiles           | `monitoring`, `worker` | _auskommentiert_           | `monitoring`, `worker` (UI-Feld)    |
| Logging-Limits     | _default_              | _default_                  | `json-file` 10 MB × 3 (per Anchor)  |
| Volume-Namen       | compose-default        | explizit (`correlcore_*`)  | explizit (`correlcore_*`)           |
| Network-Name       | `internal`             | `correlcore`               | `correlcore`                        |
| Git-Sync supported | nein                   | nein                       | ja (Webhook-Auto-Deploy)            |

Funktional identisch — gleiche GHCR-Images, gleiche Services, gleiche
Healthchecks, gleicher Tailscale-IP-Bind.

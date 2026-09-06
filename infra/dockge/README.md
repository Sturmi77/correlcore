# CorrelCore — Dockge-Stack (User-Test)

Drop-in für [Dockge](https://github.com/louislam/dockge). Identisch zum
`docker-compose.user-test.yml` in [`infra/docker/`](../docker/), aber für
die Dockge-Konvention (`compose.yaml` + `.env` pro Stack-Verzeichnis)
optimiert. Kein top-level `name:` — Dockge nimmt den Verzeichnisnamen
(`correlcore`) als Stack-Identifier.

## Setup

1. Verzeichnis im Dockge-Stacks-Pfad anlegen (z. B. `/opt/stacks/correlcore/`).
2. `compose.yaml`, `initdb/` und `.env.example` reinkopieren.
3. `cp .env.example .env` und alle leeren Variablen ausfüllen.
4. Dockge UI öffnen → Stack `correlcore` erscheint als _inactive_ → **Deploy**.

```bash
sudo mkdir -p /opt/stacks/correlcore
sudo cp compose.yaml .env.example /opt/stacks/correlcore/
sudo cp -r initdb /opt/stacks/correlcore/
cd /opt/stacks/correlcore
sudo cp .env.example .env
sudo $EDITOR .env   # Secrets generieren (siehe Snippets in der Datei)
# → Dockge-UI: Deploy
```

## Secrets generieren

```bash
# SECRET_KEY
python3 -c 'import secrets; print(secrets.token_urlsafe(48))'

# ENCRYPTION_KEY (Fernet)
python3 -c 'from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())'

# POSTGRES_PASSWORD / APP_DB_PASSWORD / REDIS_PASSWORD
python3 -c 'import secrets; print(secrets.token_urlsafe(24))'
```

> **WICHTIG:** `ENCRYPTION_KEY` sicher backuppen. Geht der Key verloren,
> sind alle verschlüsselten Felder unentschlüsselbar.

## Tailscale-Bind

Setze `TAILSCALE_IP=$(tailscale ip -4)` in der `.env`. Dann binden api/web/
mailpit nur auf das Tailnet-Interface — kein WAN-Exposure.

| Service | Host-Port (Default)      | Zugriff im Tailnet                                  |
| ------- | ------------------------ | --------------------------------------------------- |
| Web     | `${WEB_HOST_PORT:-3000}` | `http://<tailscale-ip>:<WEB_HOST_PORT>`             |
| API     | `${API_HOST_PORT:-8210}` | `http://<tailscale-ip>:<API_HOST_PORT>/health/live` |
| Mailpit | 8025                     | `http://<tailscale-ip>:8025`                        |

> Host-Ports sind über `API_HOST_PORT` (Default `8210`) und `WEB_HOST_PORT`
> (Default `3000`) in der `.env` konfigurierbar — falls auf dem Host bereits
> ein anderer Selfhosted-Dienst diese Ports belegt (z.B. Paperless auf 8000).
> Beim Ändern von `WEB_HOST_PORT`: `CORS_ORIGINS` entsprechend nachziehen.

Postgres und Redis sind nur stack-intern erreichbar (kein Port-Mapping).

## Migrations

Der `migrate`-Container läuft einmalig vor `api`/`worker` und führt
`alembic upgrade head` aus. Idempotent — Re-Deploys triggern automatisch
neue Migrations.

`migrate` nutzt `POSTGRES_USER` als Schema-Owner. API und Worker verwenden
`APP_DB_USER=correlcore_app`, eine eingeschränkte Runtime-Rolle. Das
`initdb/`-Script legt diese Rolle beim ersten Postgres-Volume-Start an;
Migration 012 erteilt Rechte und erzwingt Row-Level-Security auf User-Daten.

## Optional aktivieren

- **Analytics-Worker** (Insights, Cleanup, wöchentlicher Digest) startet mit dem
  Default-Stack — kein `COMPOSE_PROFILES=worker` nötig (#818). Der Worker startet
  `supercronic` und braucht ein **Image ≥ v1.5.0**.
- **GlitchTip** (Error-Tracking) ist in diesem Stack **nicht enthalten** —
  anders als bei quickstart/user-test gibt es hier keinen GlitchTip-Service.
  Wer Error-Tracking braucht, nimmt den `user-test`- oder `quickstart`-Stack
  (Profil `monitoring`).

## Update auf neuen Image-Tag

```bash
# Variante A: in .env auf neuen Tag setzen, dann im Dockge-UI "Update"
IMAGE_TAG=v1.7.0

# Variante B: bei IMAGE_TAG=latest reicht Re-Deploy → pull_policy: always
```

> **Worker braucht ein Image ≥ v1.5.0.** Der `worker`-Service startet
> `supercronic` (Cron-basierter Analytics-Trigger, #757), das erst ab den
> 1.5-Images gebaut ist. Mit einem älteren Pin (`v0.3.0` o. ä.) crash-loopt der
> Worker.

## Backup

```bash
# Postgres-Dump
docker exec correlcore-postgres pg_dump -U correlcore correlcore \
  | gzip > correlcore-$(date +%F).sql.gz

# Volumes (alternative, vollständig)
docker run --rm -v correlcore_postgres_data:/data -v "$PWD":/backup \
  alpine tar czf /backup/postgres-data-$(date +%F).tar.gz -C /data .
```

`ENCRYPTION_KEY` gehört NICHT in den DB-Dump — zusätzlich getrennt sichern.

## Unterschiede zu `infra/docker/docker-compose.user-test.yml`

| Punkt             | user-test compose   | Dockge compose               |
| ----------------- | ------------------- | ---------------------------- |
| Top-level `name:` | `correlcore-test`   | _kein_ (Dockge nutzt Ordner) |
| Container-Präfix  | `correlcore-test-*` | `correlcore-*`               |
| Volume-Namen      | compose-default     | explizit (`correlcore_*`)    |
| GlitchTip         | Profil `monitoring` | _nicht enthalten_            |
| Analytics-Worker  | always on           | always on                    |
| Network-Name      | `internal`          | `correlcore`                 |

Gleiche Images, gleiche Healthchecks. Beide Stacks werden aus derselben
kanonischen Quelle generiert (siehe [`COMPOSE_STACKS.md`](../../docs/selfhost/COMPOSE_STACKS.md)).

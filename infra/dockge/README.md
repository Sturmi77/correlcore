# MoodSync — Dockge-Stack (User-Test)

Drop-in für [Dockge](https://github.com/louislam/dockge). Identisch zum
`docker-compose.user-test.yml` in [`infra/docker/`](../docker/), aber für
die Dockge-Konvention (`compose.yaml` + `.env` pro Stack-Verzeichnis)
optimiert. Kein top-level `name:` — Dockge nimmt den Verzeichnisnamen
(`moodsync`) als Stack-Identifier.

## Setup

1. Verzeichnis im Dockge-Stacks-Pfad anlegen (z. B. `/opt/stacks/moodsync/`).
2. `compose.yaml` und `.env.example` reinkopieren.
3. `cp .env.example .env` und alle leeren Variablen ausfüllen.
4. Dockge UI öffnen → Stack `moodsync` erscheint als _inactive_ → **Deploy**.

```bash
sudo mkdir -p /opt/stacks/moodsync
sudo cp compose.yaml .env.example /opt/stacks/moodsync/
cd /opt/stacks/moodsync
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

# POSTGRES_PASSWORD / REDIS_PASSWORD
python3 -c 'import secrets; print(secrets.token_urlsafe(24))'
```

> **WICHTIG:** `ENCRYPTION_KEY` sicher backuppen. Geht der Key verloren,
> sind alle verschlüsselten Felder unentschlüsselbar.

## Tailscale-Bind

Setze `TAILSCALE_IP=$(tailscale ip -4)` in der `.env`. Dann binden api/web/
mailpit nur auf das Tailnet-Interface — kein WAN-Exposure.

| Service | Port | Zugriff im Tailnet                       |
| ------- | ---- | ---------------------------------------- |
| Web     | 3000 | `http://<tailscale-ip>:3000`             |
| API     | 8000 | `http://<tailscale-ip>:8000/health/live` |
| Mailpit | 8025 | `http://<tailscale-ip>:8025`             |

Postgres und Redis sind nur stack-intern erreichbar (kein Port-Mapping).

## Migrations

Der `migrate`-Container läuft einmalig vor `api`/`worker` und führt
`alembic upgrade head` aus. Idempotent — Re-Deploys triggern automatisch
neue Migrations.

## Optional aktivieren

In `compose.yaml` sind zwei Service-Blöcke auskommentiert:

- **GlitchTip** (Error-Tracking, Web-UI Port 8080)
  Block einkommentieren + `GLITCHTIP_SECRET_KEY` setzen, dann nach erstem
  Up:
  ```bash
  docker exec -it moodsync-glitchtip ./manage.py migrate
  docker exec -it moodsync-glitchtip ./manage.py createsuperuser
  ```
- **Analytics-Worker** (M2+)
  Erst aktivieren wenn `app/workers/analytics.py` implementiert ist —
  Code existiert noch nicht (CrashLoop sonst).

## Update auf neuen Image-Tag

```bash
# Variante A: in .env auf neuen Tag setzen, dann im Dockge-UI "Update"
IMAGE_TAG=v0.3.0

# Variante B: bei IMAGE_TAG=latest reicht Re-Deploy → pull_policy: always
```

## Backup

```bash
# Postgres-Dump
docker exec moodsync-postgres pg_dump -U moodsync moodsync \
  | gzip > moodsync-$(date +%F).sql.gz

# Volumes (alternative, vollständig)
docker run --rm -v moodsync_postgres_data:/data -v "$PWD":/backup \
  alpine tar czf /backup/postgres-data-$(date +%F).tar.gz -C /data .
```

`ENCRYPTION_KEY` gehört NICHT in den DB-Dump — zusätzlich getrennt sichern.

## Unterschiede zu `infra/docker/docker-compose.user-test.yml`

| Punkt             | user-test compose      | Dockge compose                                             |
| ----------------- | ---------------------- | ---------------------------------------------------------- |
| Top-level `name:` | `moodsync-test`        | _kein_ (Dockge nutzt Ordner)                               |
| Container-Präfix  | `moodsync-test-*`      | `moodsync-*`                                               |
| Volume-Namen      | compose-default        | explizit (`moodsync_*`)                                    |
| Profiles          | `monitoring`, `worker` | _entfernt_ — Blöcke kommentiert (Dockge ignoriert Profile) |
| Network-Name      | `internal`             | `moodsync`                                                 |

Funktional identisch — gleiche Images, gleiche Services, gleiche Healthchecks.

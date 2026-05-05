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

> Bei `IMAGE_TAG=latest` reicht ein Redeploy — es wird automatisch das
> neueste main-Image gezogen.

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
| `pull_policy`      | `always`               | `always`                   | _entfernt_ (Dockhand managt Pulls) |
| Profiles           | `monitoring`, `worker` | _auskommentiert_           | `monitoring`, `worker` (UI-Feld)   |
| Logging-Limits     | _default_              | _default_                  | `json-file` 10 MB × 3 (per Anchor) |
| Volume-Namen       | compose-default        | explizit (`moodsync_*`)    | explizit (`moodsync_*`)            |
| Network-Name       | `internal`             | `moodsync`                 | `moodsync`                         |
| Git-Sync supported | nein                   | nein                       | ja (Webhook-Auto-Deploy)           |

Funktional identisch — gleiche GHCR-Images, gleiche Services, gleiche
Healthchecks, gleicher Tailscale-IP-Bind.

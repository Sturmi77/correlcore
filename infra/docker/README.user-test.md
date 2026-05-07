# MoodSync — User-Test-Deployment

Compose-Stack für den **ersten User-Test** nach abgeschlossenem M1.
Zielumgebung: Tailscale-internes Netz (Homelab, Synology, Mini-PC).

> **Nicht für Produktion.** Für öffentliches Deployment mit Domain +
> Letsencrypt → `docker-compose.yml` (Production-Stack).

---

## Was läuft mit?

| Service     | Zweck                                                 | Profile      |
| ----------- | ----------------------------------------------------- | ------------ |
| `migrate`   | Alembic-Migrations (Init-Container, einmalig)         | _always_     |
| `api`       | FastAPI-Backend (`ghcr.io/sturmi77/moodsync-api`)     | _always_     |
| `web`       | SvelteKit-Frontend (`ghcr.io/sturmi77/moodsync-web`)  | _always_     |
| `postgres`  | PostgreSQL 16 + pgvector                              | _always_     |
| `redis`     | Token-Store + Rate-Limit-State                        | _always_     |
| `mailpit`   | Lokaler SMTP-Catcher für Verifizierungs-Mails         | _always_     |
| `glitchtip` | Error-Tracking (Web-UI auf Port 8080)                 | `monitoring` |
| `worker`    | Analytics-Worker (M2+, Code noch nicht implementiert) | `worker`     |

**Bewusst NICHT enthalten:** MinIO (Foto-Upload kommt erst in M3+) und
Traefik (kein Letsencrypt im internen Tailnet).

---

## 1. Voraussetzungen

- Docker ≥ 24 + Compose-Plugin
- Tailscale läuft auf dem Host (`tailscale status` zeigt Verbindung)
- Tailnet-IP des Hosts kennen: `tailscale ip -4`
- Optional: MagicDNS-Hostname (z. B. `moodsync-test.tail-scale.ts.net`)

---

## 2. Setup

```bash
cd infra/docker
cp .env.user-test.example .env
```

`.env` ausfüllen — siehe Kommentare in `.env.user-test.example`. Pflicht:

```bash
# Secrets generieren
python -c 'from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())'   # ENCRYPTION_KEY
python -c 'import secrets; print(secrets.token_urlsafe(48))'                                # SECRET_KEY
python -c 'import secrets; print(secrets.token_urlsafe(24))'                                # POSTGRES_PASSWORD
python -c 'import secrets; print(secrets.token_urlsafe(24))'                                # REDIS_PASSWORD

# Tailnet-IP eintragen
tailscale ip -4
```

> **ENCRYPTION_KEY ist kritisch.** Verlust = alle verschlüsselten Felder
> (E-Mails, ggf. Notes) sind nicht wiederherstellbar. Sicher backuppen
> (Bitwarden, Vaultwarden, verschlüsseltes Archiv).

`CORS_ORIGINS` auf den Hostname setzen, unter dem das Web-Frontend
erreichbar sein wird, z. B.:

```env
CORS_ORIGINS=http://moodsync-test.tail-scale.ts.net:3000,http://100.101.102.103:3000
```

---

## 3. Start

```bash
docker compose -f docker-compose.user-test.yml up -d
docker compose -f docker-compose.user-test.yml logs -f api
```

Healthcheck-Status:

```bash
docker compose -f docker-compose.user-test.yml ps
```

Alles `healthy`? Dann:

- **App:** `http://<TAILSCALE_IP>:<WEB_HOST_PORT>` (Default-Port `3000`)
- **API-Docs:** `http://<TAILSCALE_IP>:<API_HOST_PORT>/api/docs` (Default-Port `8210`) _(nur wenn `APP_ENV=staging` und Debug an)_
- **Mailpit:** `http://<TAILSCALE_IP>:8025`

> `API_HOST_PORT` und `WEB_HOST_PORT` sind in der `.env` konfigurierbar —
> nützlich, wenn auf dem Host bereits ein anderer Selfhosted-Dienst auf 8000
> oder 3000 lauscht (z.B. Paperless = 8000). Beim Ändern von `WEB_HOST_PORT`:
> `CORS_ORIGINS` entsprechend nachziehen.

---

## 4. Optionale Profile

### GlitchTip aktivieren

```bash
docker compose -f docker-compose.user-test.yml --profile monitoring up -d

# Beim ersten Start GlitchTip-Schema migrieren:
docker compose -f docker-compose.user-test.yml exec glitchtip ./manage.py migrate
docker compose -f docker-compose.user-test.yml exec glitchtip ./manage.py createsuperuser
```

Web-UI: `http://<TAILSCALE_IP>:8080`

### Worker — erst ab M2 sinnvoll

Der Container in `--profile worker` startet aktuell mit
`ModuleNotFoundError`, weil `app/workers/analytics.py` noch nicht
implementiert ist. Bitte erst aktivieren wenn der Worker-Code gemerged
wurde.

---

## 5. Updates einspielen

```bash
# Neueste Images von GHCR ziehen
docker compose -f docker-compose.user-test.yml pull

# Recreate (migrate läuft automatisch falls neue Migrations dabei)
docker compose -f docker-compose.user-test.yml up -d
```

Image-Tags pinnen statt `latest` zu nutzen:

```env
IMAGE_TAG=v0.2.0
# oder
IMAGE_TAG=sha-abc1234
```

---

## 6. Backup

Nur Postgres-Volume und der `ENCRYPTION_KEY` aus `.env` sind
persistenz-relevant. Beispiel-Dump:

```bash
docker compose -f docker-compose.user-test.yml exec postgres \
  pg_dump -U moodsync moodsync | gzip > moodsync-$(date +%F).sql.gz
```

Restore:

```bash
gunzip -c moodsync-2026-05-05.sql.gz | \
  docker compose -f docker-compose.user-test.yml exec -T postgres \
  psql -U moodsync moodsync
```

---

## 7. Troubleshooting

| Problem                             | Ursache / Fix                                                                                                             |
| ----------------------------------- | ------------------------------------------------------------------------------------------------------------------------- |
| `migrate` exited mit Code 1         | DB-Connection prüfen — meist `POSTGRES_PASSWORD` enthält `@` oder `/` (DSN-Konflikt). Anderes Passwort generieren.        |
| `api` healthcheck schlägt fehl      | `docker compose ... logs api` — meist fehlt `ENCRYPTION_KEY` oder ist kein gültiger Fernet-Key.                           |
| Verifikations-Mails kommen nicht an | Mailpit-UI öffnen (`:8025`). Wenn auch dort leer: SMTP-Config in `.env` prüfen, `SMTP_HOST=mailpit` und `SMTP_PORT=1025`. |
| Web zeigt CORS-Fehler beim Login    | `CORS_ORIGINS` muss exakt den Origin enthalten, von dem das Frontend kommt — inkl. Schema und Port.                       |
| Aus dem Tailnet nicht erreichbar    | `TAILSCALE_IP` in `.env` zeigt auf 127.0.0.1? Auf Tailnet-IP setzen oder `tailscale serve --bg` für Reverse-Proxy nutzen. |
| `:latest` zieht alte Version        | `docker compose ... pull` erzwingt aktuellsten Stand. Alternativ Tag pinnen (`IMAGE_TAG=sha-…`).                          |

---

## 8. Stack stoppen

```bash
# Stoppen, Volumes behalten
docker compose -f docker-compose.user-test.yml down

# Stoppen + Daten weg (Vorsicht!)
docker compose -f docker-compose.user-test.yml down -v
```

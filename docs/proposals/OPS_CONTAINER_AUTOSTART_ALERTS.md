# ops: container autostart hardening + downtime / crash notifications

> Ready-to-paste GitHub issue body (ops / feature_request style).
> Labels: `enhancement` (optional: ops)
> Milestone: Post-M9 / Ops-Backlog

---

## Feature-Beschreibung

Selfhost-/Hosted-Stack soll nach Reboot und Crash zuverlässig wieder hochkommen. Maintainer sollen benachrichtigt werden, wenn ein Container nicht startet, abstürzt oder längere Zeit unhealthy bleibt.

## Problem / Motivation

In [`infra/docker/docker-compose.yml`](../../infra/docker/docker-compose.yml) (sowie quickstart/user-test/Dockhand) steht bereits `restart: unless-stopped` und Healthchecks für Core-Services (`api`, `web`, `postgres`, `redis`, …). Das deckt **Prozess-Exit** ab, aber:

- Docker startet bei **unhealthy** (Prozess läuft, Service tot) **nicht** automatisch neu.
- Es gibt **keine** Availability-Alerts: GlitchTip (Profil `monitoring`) erfasst App-Exceptions, nicht Container-Lifecycle.
- `docker-compose.ops.yml` / Uptime Kuma sind in DESIGN / [ADR-0007](../adr/0007-healthchecks-and-logging.md) / M9 als Post-M9 geplant, aber **nicht im Repo**.
- Host-Autostart (Docker-Daemon nach Reboot) ist undokumentiert; Worker / Traefik / socket-proxy ohne Healthcheck.

## Vorgeschlagene Lösung

Slim path laut ADR-0007 — **kein** Prometheus/Alertmanager für Selfhost:

1. **Autostart absichern (Docs + Compose-Audit)**
   - `restart: unless-stopped` für alle long-lived Services verifizieren.
   - In [`docs/selfhost/INSTALL.md`](../selfhost/INSTALL.md) / Runbook: Docker enable-on-boot (`systemctl enable docker`), Compose-Stack-Persistenz (systemd / Dockge / Dockhand) dokumentieren.
   - Optional: `willfarrell/autoheal` im Ops-Profil → Restart bei `unhealthy`.

2. **Ops-Compose einführen:** neues `infra/docker/docker-compose.ops.yml` (oder Compose-Profil `ops`) mit **Uptime Kuma** (selfhosted, DSGVO-fit):
   - Monitore: `GET /api/v1/health/ready` (nicht nur `/live`), Web-Root, optional Postgres/Redis TCP, ggf. Worker-Heartbeat sobald vorhanden.
   - Alerts: **E-Mail** über bestehendes SMTP und/oder **Webhook / ntfy**.
   - Traefik-Route oder Tailscale-only Exposure für Kuma-UI dokumentieren.

3. **Failed-start / Crash abdecken**
   - Kuma: Down nach Retries → Notify.
   - Optional: Docker-Event-Watcher oder Host-Cron für Services ohne HTTP (Worker), falls Kuma-Lücken bleiben.

4. **Healthcheck-Lücken (Follow-up im selben Issue oder Child)**
   - Worker file-based/heartbeat Probe (ADR-0007).
   - GlitchTip-Healthcheck in quickstart/Dockhand angleichen.

### Umsetzungsplan

Compose-Audit + INSTALL-Autostart-Docs → `docker-compose.ops.yml` + Uptime-Kuma-Defaults → Alert-Kanäle (SMTP/ntfy) dokumentieren → optional Autoheal → Worker-Healthcheck Follow-up → Smoke im Runbook.

```text
Host reboot → Docker daemon enabled → restart: unless-stopped
  → Compose healthchecks → optional autoheal
  → Uptime Kuma (/health/ready) → Email / ntfy on down
```

## Alternativen

- Nur externes Uptime Kuma / Healthchecks.io ohne Repo-Compose — schneller Workaround, nicht „im Stack“.
- Prometheus + Alertmanager — bewusst deferred (ADR-0007).
- Nur GlitchTip erweitern — falsches Signal (App vs. Container).

## Milestone

Post-M9 / Ops-Backlog (analog M10.2/M11 ops-Issues)

## Datenschutz-Impact

Selfhosted Monitore; Alert-Kanäle ohne Drittanbieter-Pflicht. Keine Nutzer-Gesundheitsdaten in Alerts (nur Service-Status).

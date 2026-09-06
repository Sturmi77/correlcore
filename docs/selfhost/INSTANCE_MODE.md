# Instance mode — hosted vs. self-host (landing CTA)

CorrelCore ships **one** web bundle that serves both a self-hosted deployment
and the managed SaaS (correlcore.com). Which primary call-to-action the
anonymous landing page shows is decided **at runtime** from a small public
descriptor the backend serves — not from a build-time flag, so operators never
need a separate build per mode.

## How it works

On boot the web client fetches a public, dependency-free endpoint:

```
GET /api/v1/instance  →  { "mode": "selfhost" | "hosted",
                           "registration_enabled": true | false,
                           "version": "1.7.1" }
```

The values come from configuration the backend already owns:

| Env variable           | Default    | Meaning                                                        |
| ---------------------- | ---------- | -------------------------------------------------------------- |
| `DEPLOYMENT_MODE`      | `selfhost` | `selfhost` or `hosted` (managed SaaS). Drives badge wording.   |
| `REGISTRATION_ENABLED` | `true`     | Whether anonymous visitors may self-register on this instance. |
| `APP_VERSION`          | image tag  | Reported as `version`; also shown in the landing badge.        |

The endpoint is public by design — the anonymous landing must read it before
login. It exposes only these non-sensitive deployment facts.

## What the landing does

| Backend reports                                          | Primary CTA                            | Badge                      |
| -------------------------------------------------------- | -------------------------------------- | -------------------------- |
| `mode=hosted`                                            | **Create account** → `/auth/register`  | `Hosted · v<version>`      |
| `mode=selfhost`, `registration_enabled=true` _(default)_ | **Create account** → `/auth/register`  | `Self-hosted · v<version>` |
| `mode=selfhost`, `registration_enabled=false`            | **Self-host** → docs                   | `Self-hosted · v<version>` |
| descriptor unreachable / no backend                      | **Self-host** → docs _(safe fallback)_ | `Self-hosted · v<bundled>` |

- **Log in** is always present, in every mode. The login page links to
  registration, so instance owners can always reach it.
- **Logged-in users never see the landing** — the marketing view is the
  anonymous state only. The mode affects the "not signed in" case exclusively.
- If the descriptor cannot be loaded, the landing falls back to the calm
  self-host CTA rather than a dead "Create account" button.

## Per role

### Operator of the managed SaaS (correlcore.com)

Set once, then nothing else:

```dotenv
DEPLOYMENT_MODE=hosted
REGISTRATION_ENABLED=true
```

Anonymous visitors get the marketing landing with **Create account** as the
primary action, registering directly on correlcore.com. Same artifact as
self-host — only this env differs.

### Self-hoster (own instance)

Do **nothing** by default: the instance is `selfhost` with registration open,
so anonymous visitors to your instance see **Create account** and register **on
your instance**.

To keep the instance private, close self-registration:

```dotenv
REGISTRATION_ENABLED=false
```

The primary CTA then becomes **Self-host** (→ docs) and self-registration is
off — enforced server-side: `POST /api/v1/auth/register` returns the same
enumeration-safe `202` **without creating an account** or sending mail. You
still sign in via **Log in** (create users server-side / via an invite flow as
appropriate).

### User of the hosted correlcore.com instance

Lands on correlcore.com → sees marketing + **Create account** → registers →
uses the app. Returning users click **Log in**; once signed in the landing is
replaced by the app home. They never need to know about "hosted vs self-host".

## Edge case: hosted invite-only

A `hosted` deployment with `REGISTRATION_ENABLED=false` still shows **Create
account** today (hosted implies signup is the intended action). For a closed
beta a "waitlist / login only" variant would fit better — tracked as a P2
refinement, not a blocker.

## Verify

```bash
curl -s https://your-domain.tld/api/v1/instance
# {"mode":"selfhost","registration_enabled":true,"version":"1.7.1"}
```

Change `DEPLOYMENT_MODE` / `REGISTRATION_ENABLED` in `.env`, restart the `api`
service, and reload the landing — the CTA and badge follow immediately, with no
rebuild.

# ADR-0015 - Developer-View fuer Versionsidentifikation

## Status

Akzeptiert (2026-05-10)

## Kontext

Im Selfhost-Deployment ist die Frage "Welche GitHub-Version laeuft wirklich?"
nicht allein ueber `:latest` beantwortbar. Ein Host kann ein altes gecachtes
Image weiterverwenden, ein Compose-Stack kann einen anderen Tag deployen, und
der echte OCI/RepoDigest entsteht erst nach Push/Pull. Gleichzeitig soll die
Diagnose-Ansicht keine neue Sicherheitsflaeche durch einen Docker-Socket im
API-Container oeffnen.

## Entscheidung

CorrelCore erhaelt eine default-off Developer-View:

- Backend: `GET /api/v1/dev/info`, nur aktiv bei `DEV_VIEW_ENABLED=true`, nur
  fuer authentifizierte und verifizierte User.
- GitHub-Version: `GIT_COMMIT`, `GIT_BRANCH` und `BUILD_TIME` werden beim
  API-Image-Build per Build-Args eingebettet.
- Container-Artefakt: `IMAGE_TAG` und optional `IMAGE_DIGEST` kommen zur
  Laufzeit aus Compose/Dockhand/Dockge. `IMAGE_DIGEST` bleibt `null`, wenn das
  Deployment keinen echten RepoDigest setzt.
- Frontend: `/dev` zeigt GitHub-Commit, Image-Tag und Image-Digest prominent,
  verlinkt Commits auf GitHub, bietet Copy-Buttons und aktualisiert alle 30 s.
- Kein Docker-Socket-Mount im API-Container.

## Konsequenzen

`git_commit` ist die verbindliche Antwort auf "welche GitHub-Version?". Der
optionale `image_digest` ist die Antwort auf "welches exakte Container-Artefakt?"
und muss vom Deployment nach Pull/Deploy gesetzt werden, z. B. aus
`docker inspect`. Fuer reproduzierbare Deployments wird `IMAGE_TAG=sha-<short>`
empfohlen; der Digest kann zusaetzlich gesetzt werden, wenn die Plattform ihn
zuverlaessig bereitstellt.

Falls spaeter eine automatische Runtime-Digest-Erkennung gewuenscht wird,
braucht sie ein separates Security-Review/ADR, weil Docker-Socket-Zugriff im
Container zu hohe Privilegien haette.

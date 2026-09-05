# CorrelCore Web — SvelteKit (Node-Adapter)
# Multi-Stage Build, non-root, Production-ready.
#
# Build context: Repo-Root (wegen pnpm workspace + lockfile)
#   docker build -f apps/web/Dockerfile -t correlcore-web .

# ---- Build stage ----
FROM node:26-alpine AS builder

WORKDIR /repo

# CI=true übergeht pnpm-Interactive-Prompts (z. B. confirmModulesPurge), die
# in non-TTY-Containern zu ERR_PNPM_ABORTED_REMOVE_MODULES_DIR_NO_TTY führen.
# GitHub-Actions setzt CI=true im Runner-Env, vererbt das aber nicht in den
# Buildx-Container — deshalb hier explizit.
ENV CI=true

# pnpm via corepack
RUN corepack enable

# Lockfile + Workspace-Manifeste zuerst (Layer-Cache)
COPY package.json pnpm-lock.yaml pnpm-workspace.yaml .npmrc* ./
COPY apps/web/package.json apps/web/package.json
# @correlcore/web depends on the workspace package @correlcore/api-types
# (issue #778); its manifest must be present so the filtered frozen install can
# resolve the workspace graph.
COPY packages/api-types/package.json packages/api-types/package.json

# Deps installieren (frozen — reproducible)
RUN pnpm install --frozen-lockfile --filter @correlcore/web...

# Quellen
COPY apps/web/ apps/web/
# api-types sources (generated OpenAPI types) needed for the web typecheck/build.
COPY packages/api-types/ packages/api-types/

# Build (Vite + SvelteKit Node-Adapter)
#
# VITE_API_BASE_URL is a build-time constant baked into the JS bundle. Since
# ADR-0011 the only supported value is `/api/v1` (relative). The web
# container forwards `/api/*` to the API at runtime via
# `apps/web/src/hooks.server.ts` (INTERNAL_API_URL, default `http://api:8000`).
# Override at runtime, never at build time.
ARG VITE_API_BASE_URL=/api/v1
ENV VITE_API_BASE_URL=${VITE_API_BASE_URL}

WORKDIR /repo/apps/web
RUN pnpm build

# Prod-Deps als eigenständiges Deploy-Verzeichnis (pnpm deploy --legacy).
# apps/web/node_modules enthält Workspace-Symlinks auf /repo/node_modules/.pnpm;
# die brechen im Runtime-Image, weil nur apps/web/node_modules kopiert wurde
# (ERR_MODULE_NOT_FOUND für @sentry/node). deploy legt .pnpm als Geschwister
# unter node_modules/ ab — Symlinks bleiben im Container auflösbar.
WORKDIR /repo
RUN pnpm deploy --filter @correlcore/web --prod --legacy /repo/deploy

# ---- Runtime stage ----
FROM node:26-alpine AS runtime

WORKDIR /app

# Non-root User (Alpine: addgroup/adduser)
RUN addgroup -S correlcore && adduser -S -G correlcore correlcore

# Build-Output + Prod-Deps kopieren
# SvelteKit adapter-node erzeugt /build mit eigenem package.json + Server
COPY --from=builder --chown=correlcore:correlcore /repo/apps/web/build ./build
COPY --from=builder --chown=correlcore:correlcore /repo/apps/web/package.json ./package.json
COPY --from=builder --chown=correlcore:correlcore /repo/deploy/node_modules ./node_modules

ENV NODE_ENV=production
ENV HOST=0.0.0.0
ENV PORT=3000
ENV BODY_SIZE_LIMIT=5M

USER correlcore

EXPOSE 3000

# adapter-node Server
CMD ["node", "build/index.js"]

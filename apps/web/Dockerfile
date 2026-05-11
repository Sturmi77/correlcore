# CorrelCore Web — SvelteKit (Node-Adapter)
# Multi-Stage Build, non-root, Production-ready.
#
# Build context: Repo-Root (wegen pnpm workspace + lockfile)
#   docker build -f apps/web/Dockerfile -t correlcore-web .

# ---- Build stage ----
FROM node:22-alpine AS builder

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

# Deps installieren (frozen — reproducible)
RUN pnpm install --frozen-lockfile --filter @correlcore/web...

# Quellen
COPY apps/web/ apps/web/

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

# Prod-Deps separat installieren (weniger fragil als `pnpm prune --prod`,
# das in CI-Containern ohne TTY mit "confirmModulesPurge"-Prompt hängt).
#
# --ignore-scripts: der `prepare`-Hook in apps/web/package.json ruft
# `svelte-kit sync` auf — das würde @sveltejs/kit erfordern, das aber als
# devDependency bei --prod nicht installiert wird (sh: svelte-kit: not found).
# Für das Production-Image wird `prepare` ohnehin nicht gebraucht: der Build
# ist im vorigen Step bereits durchgelaufen.
WORKDIR /repo
RUN pnpm install --prod --frozen-lockfile --ignore-scripts --filter @correlcore/web...

# ---- Runtime stage ----
FROM node:22-alpine AS runtime

WORKDIR /app

# Non-root User (Alpine: addgroup/adduser)
RUN addgroup -S correlcore && adduser -S -G correlcore correlcore

# Build-Output + Prod-Deps kopieren
# SvelteKit adapter-node erzeugt /build mit eigenem package.json + Server
COPY --from=builder --chown=correlcore:correlcore /repo/apps/web/build ./build
COPY --from=builder --chown=correlcore:correlcore /repo/apps/web/package.json ./package.json
COPY --from=builder --chown=correlcore:correlcore /repo/apps/web/node_modules ./node_modules

ENV NODE_ENV=production
ENV HOST=0.0.0.0
ENV PORT=3000
ENV BODY_SIZE_LIMIT=5M

USER correlcore

EXPOSE 3000

# adapter-node Server
CMD ["node", "build/index.js"]

# MoodSync Web — SvelteKit (Node-Adapter)
# Multi-Stage Build, non-root, Production-ready.
#
# Build context: Repo-Root (wegen pnpm workspace + lockfile)
#   docker build -f apps/web/Dockerfile -t moodsync-web .

# ---- Build stage ----
FROM node:22-alpine AS builder

WORKDIR /repo

# pnpm via corepack
RUN corepack enable

# Lockfile + Workspace-Manifeste zuerst (Layer-Cache)
COPY package.json pnpm-lock.yaml pnpm-workspace.yaml .npmrc* ./
COPY apps/web/package.json apps/web/package.json

# Deps installieren (frozen — reproducible)
RUN pnpm install --frozen-lockfile --filter @moodsync/web...

# Quellen
COPY apps/web/ apps/web/

# Build (Vite + SvelteKit Node-Adapter)
ARG VITE_API_BASE_URL=/api/v1
ENV VITE_API_BASE_URL=${VITE_API_BASE_URL}

WORKDIR /repo/apps/web
RUN pnpm build && pnpm prune --prod

# ---- Runtime stage ----
FROM node:22-alpine AS runtime

WORKDIR /app

# Non-root User (Alpine: addgroup/adduser)
RUN addgroup -S moodsync && adduser -S -G moodsync moodsync

# Build-Output + Prod-Deps kopieren
# SvelteKit adapter-node erzeugt /build mit eigenem package.json + Server
COPY --from=builder --chown=moodsync:moodsync /repo/apps/web/build ./build
COPY --from=builder --chown=moodsync:moodsync /repo/apps/web/package.json ./package.json
COPY --from=builder --chown=moodsync:moodsync /repo/apps/web/node_modules ./node_modules

ENV NODE_ENV=production
ENV HOST=0.0.0.0
ENV PORT=3000
ENV BODY_SIZE_LIMIT=5M

USER moodsync

EXPOSE 3000

# adapter-node Server
CMD ["node", "build/index.js"]

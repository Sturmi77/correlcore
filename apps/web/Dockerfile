# MoodSync Web — SvelteKit (Node-Adapter)
# Multi-Stage Build, non-root, Production-ready.
#
# Build context: Repo-Root (wegen pnpm workspace + lockfile)
#   docker build -f apps/web/Dockerfile -t moodsync-web .

# ─────────────────────────────────────────────────────────────────────────
# Stage 1: deps (Prod-Deps für die Runtime)
# ─────────────────────────────────────────────────────────────────────────
# Separater Stage statt 'prune --prod' nach dem Build:
# - prune/install --prod nach vollem Install kippt mit
#   ERR_PNPM_ABORTED_REMOVE_MODULES_DIR_NO_TTY (auch mit CI=true).
# - 'prepare'-Hook (svelte-kit sync) braucht devDependencies, die im
#   --prod-Modus nicht da sind → 'svelte-kit: not found'.
# Lösung: Prod-Install in Isolation ohne prepare-Scripts.
FROM node:22-alpine AS deps

WORKDIR /repo
ENV CI=true
RUN corepack enable

COPY package.json pnpm-lock.yaml pnpm-workspace.yaml .npmrc* ./
COPY apps/web/package.json apps/web/package.json

# --ignore-scripts überspringt 'prepare' (svelte-kit sync braucht devDeps).
# --prod installiert nur dependencies, keine devDependencies.
RUN pnpm install --prod --frozen-lockfile --ignore-scripts \
      --filter @moodsync/web...

# ─────────────────────────────────────────────────────────────────────────
# Stage 2: builder (Build mit allen Deps)
# ─────────────────────────────────────────────────────────────────────────
FROM node:22-alpine AS builder

WORKDIR /repo
ENV CI=true
RUN corepack enable

COPY package.json pnpm-lock.yaml pnpm-workspace.yaml .npmrc* ./
COPY apps/web/package.json apps/web/package.json

RUN pnpm install --frozen-lockfile --filter @moodsync/web...

COPY apps/web/ apps/web/

ARG VITE_API_BASE_URL=/api/v1
ENV VITE_API_BASE_URL=${VITE_API_BASE_URL}

WORKDIR /repo/apps/web
RUN pnpm build

# ─────────────────────────────────────────────────────────────────────────
# Stage 3: runtime
# ─────────────────────────────────────────────────────────────────────────
FROM node:22-alpine AS runtime

WORKDIR /app

# Non-root User
RUN addgroup -S moodsync && adduser -S -G moodsync moodsync

# SvelteKit adapter-node erzeugt /build mit eigenem Server.
COPY --from=builder --chown=moodsync:moodsync /repo/apps/web/build ./build
COPY --from=builder --chown=moodsync:moodsync /repo/apps/web/package.json ./package.json
# node_modules aus dem deps-Stage (nur Prod-Deps, keine devDeps).
COPY --from=deps --chown=moodsync:moodsync /repo/apps/web/node_modules ./node_modules

ENV NODE_ENV=production
ENV HOST=0.0.0.0
ENV PORT=3000
ENV BODY_SIZE_LIMIT=5M

USER moodsync

EXPOSE 3000

CMD ["node", "build/index.js"]

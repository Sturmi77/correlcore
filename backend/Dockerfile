# ---- Build stage ----
FROM python:3.12-slim AS builder

WORKDIR /app

# Install uv for fast dependency resolution
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Copy dependency manifests + README (Hatchling liest readme = "README.md" beim
# editable install — ohne diese Datei: OSError: Readme file does not exist).
# uv.lock für reproducible Builds; pyproject.toml zuerst für Layer-Caching.
COPY pyproject.toml uv.lock README.md ./

# Source mit-kopieren VOR dem editable install. Hatchling braucht den
# `app/`-Package zum Build-Zeitpunkt, sonst landet nur die Dependencies in
# der venv und der Package selbst ist nicht importierbar (alembic-Run
# scheitert dann mit ModuleNotFoundError: No module named 'app').
COPY app/ app/

# Install deps + Package into /app/.venv
# --no-dev: Production-Image enthält nur Runtime-Deps (ruff, mypy, pytest etc.
# bleiben draußen → kleineres Image, kleinere Angriffsfläche).
RUN uv venv .venv && \
    uv pip install --python .venv/bin/python -e ".[analytics]"

# ---- Supercronic stage (#757) ----
# Fetches the static supercronic binary once, pinned + checksum-verified, so
# the runtime stage never needs curl/apt (smaller image, smaller attack
# surface). supercronic (MIT, https://github.com/aptible/supercronic) drives
# the worker's nightly `--once` invocation from #757: unlike the previous
# asyncio-sleep loop in a `restart: unless-stopped` container, a crash inside
# one nightly job no longer takes the whole scheduler down with it — the
# container/process stays up and simply waits for the next scheduled tick.
FROM python:3.12-slim AS supercronic
ARG SUPERCRONIC_VERSION=v0.2.49
ARG SUPERCRONIC_SHA1SUM=e63c11a9726b775a6a11801e81af4f3fb926aa68
ARG SUPERCRONIC_URL=https://github.com/aptible/supercronic/releases/download/${SUPERCRONIC_VERSION}/supercronic-linux-amd64
RUN apt-get update \
    && apt-get install -y --no-install-recommends curl ca-certificates \
    && rm -rf /var/lib/apt/lists/* \
    && curl -fsSLo /tmp/supercronic "${SUPERCRONIC_URL}" \
    && echo "${SUPERCRONIC_SHA1SUM}  /tmp/supercronic" | sha1sum -c - \
    && chmod +x /tmp/supercronic

# ---- Runtime stage ----
FROM python:3.12-slim AS runtime

WORKDIR /app

ARG GIT_COMMIT=unknown
ARG GIT_BRANCH=unknown
ARG BUILD_TIME=

# Non-root user for security
RUN groupadd -r correlcore && useradd -r -g correlcore correlcore

# procps provides pgrep, used by the worker container's HEALTHCHECK (#757)
# to report supercronic process liveness as a secondary/complementary signal
# to GET /worker/status (the primary "did the job actually run" signal, #756).
RUN apt-get update \
    && apt-get install -y --no-install-recommends procps \
    && rm -rf /var/lib/apt/lists/*

# Copy venv from builder
COPY --from=builder /app/.venv .venv
ENV PATH="/app/.venv/bin:$PATH"
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV GIT_COMMIT=${GIT_COMMIT}
ENV GIT_BRANCH=${GIT_BRANCH}
ENV BUILD_TIME=${BUILD_TIME}

# Copy source
COPY app/ app/
COPY migrations/ migrations/
COPY scripts/ scripts/
COPY migrations/alembic.ini alembic.ini
COPY crontab/ crontab/
COPY --from=supercronic /tmp/supercronic /usr/local/bin/supercronic

USER correlcore

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')"

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

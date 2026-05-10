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
    uv pip install --python .venv/bin/python -e .

# ---- Runtime stage ----
FROM python:3.12-slim AS runtime

WORKDIR /app

ARG GIT_COMMIT=unknown
ARG GIT_BRANCH=unknown
ARG BUILD_TIME=

# Non-root user for security
RUN groupadd -r moodsync && useradd -r -g moodsync moodsync

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
COPY migrations/alembic.ini alembic.ini

USER moodsync

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')"

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

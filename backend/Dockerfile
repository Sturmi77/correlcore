# ---- Build stage ----
FROM python:3.12-slim AS builder

WORKDIR /app

# Install uv for fast dependency resolution
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Copy dependency manifests + README (Hatchling liest readme = "README.md" beim
# editable install — ohne diese Datei: OSError: Readme file does not exist).
# uv.lock für reproducible Builds; pyproject.toml zuerst für Layer-Caching.
COPY pyproject.toml uv.lock README.md ./

# Install deps into /app/.venv
# --no-dev: Production-Image enthält nur Runtime-Deps (ruff, mypy, pytest etc.
# bleiben draußen → kleineres Image, kleinere Angriffsfläche).
RUN uv venv .venv && \
    uv pip install --python .venv/bin/python -e .

# ---- Runtime stage ----
FROM python:3.12-slim AS runtime

WORKDIR /app

# Non-root user for security
RUN groupadd -r moodsync && useradd -r -g moodsync moodsync

# Copy venv from builder
COPY --from=builder /app/.venv .venv
ENV PATH="/app/.venv/bin:$PATH"
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Copy source
COPY app/ app/
COPY migrations/ migrations/
COPY migrations/alembic.ini alembic.ini

USER moodsync

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')"

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

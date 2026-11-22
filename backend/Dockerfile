# Build context must be the repository root (see docker-compose.yml).
FROM ghcr.io/astral-sh/uv:0.13.9@sha256:d3b601f0c7b118bc1753febf7c41cc80981df678445e0254284eecf84db79a7d AS uv
FROM python:3.14-slim@sha256:9aaa474097d094040649f2162a627c0049b408f52138d980916788d80f04802f AS builder

COPY --from=uv /uv /uvx /bin/
WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY packages/internnexus-core ./packages/internnexus-core
COPY backend/ ./backend/

# Install exactly the production dependency graph recorded in uv.lock.
ENV UV_PROJECT_ENVIRONMENT=/opt/venv
RUN cd backend && uv sync --frozen --no-dev --no-editable

FROM python:3.14-slim@sha256:9aaa474097d094040649f2162a627c0049b408f52138d980916788d80f04802f AS runtime

ARG VCS_REF=unknown
LABEL org.opencontainers.image.revision=$VCS_REF

RUN apt-get update && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/* \
    && groupadd --system --gid 1000 appuser \
    && useradd --system --uid 1000 --gid appuser --create-home appuser

WORKDIR /app
COPY --from=builder /opt/venv /opt/venv
COPY --from=builder --chown=appuser:appuser /app/backend /app/backend

ENV PATH=/opt/venv/bin:$PATH \
    PYTHONPATH=/app/backend
USER appuser
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

# Backend Dockerfile
# Build context must be repository root (see docker-compose.yml).
FROM python:3.12-slim

WORKDIR /app

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy backend project
COPY backend/ ./backend/

# Install backend project
RUN uv pip install --system --no-cache ./backend

# Make the local source tree importable for the namespace package layout.
ENV PYTHONPATH=/app/backend

# Drop runtime privileges after dependencies are installed.
RUN groupadd --system --gid 1000 appuser \
    && useradd --system --uid 1000 --gid appuser --create-home appuser \
    && chown -R appuser:appuser /app
USER appuser

# Expose port
EXPOSE 8000

# Run the application
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
